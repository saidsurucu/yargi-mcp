"""
Redis Session Store for OAuth Authorization Codes and User Sessions

This module provides Redis-based storage for OAuth authorization codes and user sessions,
enabling multi-machine deployment support by replacing in-memory storage.

Uses Upstash Redis via REST API for serverless-friendly operation.
"""

import os
import json
import time
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    from upstash_redis import Redis
    UPSTASH_AVAILABLE = True
except ImportError:
    UPSTASH_AVAILABLE = False
    Redis = None

# Use standard Python exceptions for Redis connection errors
import socket
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout as RequestsTimeout

class RedisSessionStore:
    """
    Redis-based session store for OAuth flows and user sessions.
    
    Uses Upstash Redis REST API for connection-free operation suitable for
    multi-instance deployments on platforms like Fly.io.
    """
    
    def __init__(self):
        """Initialize Redis connection using environment variables."""
        if not UPSTASH_AVAILABLE:
            raise ImportError("upstash-redis package is required. Install with: pip install upstash-redis")
        
        # Initialize Upstash Redis client from environment with optimized connection settings
        try:
            # Get Upstash Redis configuration
            redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
            redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
            
            if not redis_url or not redis_token:
                raise ValueError("UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set")
            
            logger.info(f"Connecting to Upstash Redis at {redis_url[:30]}...")
            
            # Initialize with explicit configuration for better SSL handling
            self.redis = Redis(
                url=redis_url,
                token=redis_token
            )
            
            logger.info("Upstash Redis client created")
            
            # Skip connection test during initialization to prevent server hang
            # Connection will be tested during first actual operation
            logger.info("Redis client initialized - connection will be tested on first use")
                
        except Exception as e:
            logger.error(f"Failed to initialize Upstash Redis: {e}")
            raise
            
        # TTL values (in seconds)
        self.oauth_code_ttl = int(os.getenv("OAUTH_CODE_TTL", "600"))  # 10 minutes
        self.session_ttl = int(os.getenv("SESSION_TTL", "3600"))      # 1 hour
        
    def _serialize_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Convert data to Redis-compatible string format."""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                serialized[key] = json.dumps(value)
            elif isinstance(value, (int, float)):
                serialized[key] = str(value)
            elif isinstance(value, bool):
                serialized[key] = "true" if value else "false"
            else:
                serialized[key] = str(value)
        return serialized
    
    def _deserialize_data(self, data: Dict[str, str]) -> Dict[str, Any]:
        """Convert Redis string data back to original types."""
        if not data:
            return {}
            
        deserialized = {}
        for key, value in data.items():
            if not isinstance(value, str):
                deserialized[key] = value
                continue
                
            # Try to deserialize JSON
            if value.startswith(('[', '{')):
                try:
                    deserialized[key] = json.loads(value)
                    continue
                except json.JSONDecodeError:
                    pass
            
            # Try to convert numbers
            if value.isdigit():
                deserialized[key] = int(value)
                continue
                
            if value.replace('.', '').isdigit():
                try:
                    deserialized[key] = float(value)
                    continue
                except ValueError:
                    pass
            
            # Handle booleans
            if value in ("true", "false"):
                deserialized[key] = value == "true"
                continue
                
            # Keep as string
            deserialized[key] = value
            
        return deserialized
    
    # OAuth Authorization Code Methods
    
    def set_oauth_code(self, code: str, data: Dict[str, Any]) -> bool:
        """
        Store OAuth authorization code with automatic expiration.
        
        Args:
            code: Authorization code string
            data: Code data including user_id, client_id, etc.
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            key = f"oauth:code:{code}"
            
            # Add timestamp for debugging
            data_with_timestamp = data.copy()
            data_with_timestamp.update({
                "created_at": time.time(),
                "expires_at": time.time() + self.oauth_code_ttl
            })
            
            # Serialize and store - Upstash Redis doesn't support mapping parameter
            serialized_data = self._serialize_data(data_with_timestamp)
            
            # Use individual hset calls for each field with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Clear any existing data first
                    self.redis.delete(key)
                    
                    # Set all fields in a pipeline-like manner
                    for field, value in serialized_data.items():
                        self.redis.hset(key, field, value)
                    
                    # Set expiration
                    self.redis.expire(key, self.oauth_code_ttl)
                    
                    logger.info(f"Stored OAuth code {code[:10]}... with TTL {self.oauth_code_ttl}s (attempt {attempt + 1})")
                    return True
                    
                except (RequestsConnectionError, RequestsTimeout, OSError, socket.error) as e:
                    logger.warning(f"Redis connection error on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        raise  # Re-raise on final attempt
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    
        except Exception as e:
            logger.error(f"Failed to store OAuth code {code[:10]}... after {max_retries} attempts: {e}")
            return False
    
    def get_oauth_code(self, code: str, delete_after_use: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieve OAuth authorization code data.
        
        Args:
            code: Authorization code string
            delete_after_use: If True, delete the code after retrieval (one-time use)
            
        Returns:
            Code data dictionary or None if not found/expired
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                key = f"oauth:code:{code}"
                
                # Get all hash fields with retry
                data = self.redis.hgetall(key)
                
                if not data:
                    logger.warning(f"OAuth code {code[:10]}... not found or expired (attempt {attempt + 1})")
                    return None
                
                # Deserialize data
                deserialized_data = self._deserialize_data(data)
                
                # Check manual expiration (in case Redis TTL failed)
                expires_at = deserialized_data.get("expires_at", 0)
                if expires_at and time.time() > expires_at:
                    logger.warning(f"OAuth code {code[:10]}... manually expired")
                    try:
                        self.redis.delete(key)
                    except Exception as del_error:
                        logger.warning(f"Failed to delete expired code: {del_error}")
                    return None
                
                # Delete after use for security (one-time use)
                if delete_after_use:
                    try:
                        self.redis.delete(key)
                        logger.info(f"Retrieved and deleted OAuth code {code[:10]}... (attempt {attempt + 1})")
                    except Exception as del_error:
                        logger.warning(f"Failed to delete code after use: {del_error}")
                        # Continue anyway since we got the data
                else:
                    logger.info(f"Retrieved OAuth code {code[:10]}... (not deleted, attempt {attempt + 1})")
                
                return deserialized_data
                
            except (RequestsConnectionError, RequestsTimeout, OSError, socket.error) as e:
                logger.warning(f"Redis connection error on retrieval attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to retrieve OAuth code {code[:10]}... after {max_retries} attempts: {e}")
                    return None
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Failed to retrieve OAuth code {code[:10]}... on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(0.5 * (attempt + 1))
        
        return None
    
    # User Session Methods
    
    def set_session(self, session_id: str, user_data: Dict[str, Any]) -> bool:
        """
        Store user session data with sliding expiration.
        
        Args:
            session_id: Unique session identifier
            user_data: User session data (user_id, email, scopes, etc.)
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            key = f"session:{session_id}"
            
            # Add session metadata
            session_data = user_data.copy()
            session_data.update({
                "session_id": session_id,
                "created_at": time.time(),
                "last_accessed": time.time()
            })
            
            # Serialize and store - Upstash Redis doesn't support mapping parameter
            serialized_data = self._serialize_data(session_data)
            
            # Use individual hset calls for each field (Upstash compatibility)
            for field, value in serialized_data.items():
                self.redis.hset(key, field, value)
            self.redis.expire(key, self.session_ttl)
            
            logger.info(f"Stored session {session_id[:10]}... with TTL {self.session_ttl}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store session {session_id[:10]}...: {e}")
            return False
    
    def get_session(self, session_id: str, refresh_ttl: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieve user session data.
        
        Args:
            session_id: Session identifier
            refresh_ttl: If True, extend session TTL on access
            
        Returns:
            Session data dictionary or None if not found/expired
        """
        try:
            key = f"session:{session_id}"
            
            # Get session data
            data = self.redis.hgetall(key)
            
            if not data:
                logger.warning(f"Session {session_id[:10]}... not found or expired")
                return None
            
            # Deserialize data
            session_data = self._deserialize_data(data)
            
            # Update last accessed time and refresh TTL
            if refresh_ttl:
                session_data["last_accessed"] = time.time()
                self.redis.hset(key, "last_accessed", str(time.time()))
                self.redis.expire(key, self.session_ttl)
                logger.debug(f"Refreshed session {session_id[:10]}... TTL")
            
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve session {session_id[:10]}...: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete user session (logout).
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            key = f"session:{session_id}"
            result = self.redis.delete(key)
            
            if result:
                logger.info(f"Deleted session {session_id[:10]}...")
                return True
            else:
                logger.warning(f"Session {session_id[:10]}... not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete session {session_id[:10]}...: {e}")
            return False
    
    # Health Check Methods
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform Redis health check.
        
        Returns:
            Health status dictionary
        """
        try:
            # Test basic operations
            test_key = f"health:check:{int(time.time())}"
            test_value = {"timestamp": time.time(), "test": True}
            
            # Test set - Use individual hset calls for Upstash compatibility
            serialized_test = self._serialize_data(test_value)
            for field, value in serialized_test.items():
                self.redis.hset(test_key, field, value)
            
            # Test get
            retrieved = self.redis.hgetall(test_key)
            
            # Test delete
            self.redis.delete(test_key)
            
            return {
                "status": "healthy",
                "redis_connected": True,
                "operations_working": bool(retrieved),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "redis_connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis usage statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            # Get basic info (not all Upstash plans support INFO command)
            stats = {
                "oauth_codes_pattern": "oauth:code:*",
                "sessions_pattern": "session:*",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                # Try to get counts (may fail on some Upstash plans)
                oauth_keys = self.redis.keys("oauth:code:*")
                session_keys = self.redis.keys("session:*")
                
                stats.update({
                    "active_oauth_codes": len(oauth_keys) if oauth_keys else 0,
                    "active_sessions": len(session_keys) if session_keys else 0
                })
            except Exception as e:
                logger.warning(f"Could not get detailed stats: {e}")
                stats["warning"] = "Detailed stats not available on this Redis plan"
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

# Global instance for easy importing
redis_store = None

def get_redis_store() -> Optional[RedisSessionStore]:
    """
    Get global Redis store instance (singleton pattern).
    
    Returns:
        RedisSessionStore instance or None if initialization fails
    """
    global redis_store
    
    if redis_store is None:
        try:
            logger.info("Initializing Redis store...")
            redis_store = RedisSessionStore()
            logger.info("Redis store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis store: {e}")
            redis_store = None
    
    return redis_store

def init_redis_store() -> RedisSessionStore:
    """
    Initialize Redis store and perform health check.
    
    Returns:
        RedisSessionStore instance
        
    Raises:
        Exception if Redis is not available or unhealthy
    """
    store = get_redis_store()
    
    # Perform health check
    health = store.health_check()
    
    if health["status"] != "healthy":
        raise Exception(f"Redis health check failed: {health}")
    
    logger.info("Redis session store initialized and healthy")
    return store