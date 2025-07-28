# token_manager.py - Persistent Token Management System
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

logger = logging.getLogger(__name__)

class PersistentTokenManager:
    """
    Production-ready token management with persistence
    """
    
    def __init__(self, 
                 storage_path: str = "/app/data/tokens.json",
                 key_path: str = "/app/data/jwt_key.pem",
                 token_expire_hours: int = 24):
        self.storage_path = Path(storage_path)
        self.key_path = Path(key_path)
        self.token_expire_hours = token_expire_hours
        
        # Ensure data directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize JWT key
        self.private_key = self._get_or_create_key()
        
        # Load existing tokens
        self.tokens: Dict[str, dict] = self._load_tokens()
        
        logger.info(f"TokenManager initialized with storage: {self.storage_path}")
    
    def _get_or_create_key(self):
        """Get existing JWT key or create new one"""
        try:
            if self.key_path.exists():
                with open(self.key_path, 'rb') as key_file:
                    private_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=None
                    )
                logger.info("Loaded existing JWT key")
                return private_key
            else:
                # Generate new key
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048
                )
                
                # Save key
                pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                with open(self.key_path, 'wb') as key_file:
                    key_file.write(pem)
                
                logger.info("Generated new JWT key")
                return private_key
                
        except Exception as e:
            logger.error(f"Error handling JWT key: {e}")
            # Fallback to in-memory key
            return rsa.generate_private_key(public_exponent=65537, key_size=2048)
    
    def _load_tokens(self) -> Dict[str, dict]:
        """Load tokens from persistent storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded {len(data)} tokens from storage")
                return data
        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
        return {}
    
    def _save_tokens(self):
        """Save tokens to persistent storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.tokens, f, indent=2, default=str)
            logger.debug("Tokens saved to storage")
        except Exception as e:
            logger.error(f"Error saving tokens: {e}")
    
    def generate_token(self, user_id: str, additional_claims: Dict[str, Any] = None) -> str:
        """Generate a new JWT token"""
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=self.token_expire_hours)
        
        payload = {
            "iss": "https://yargi-mcp.botfusions.com",
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "aud": "yargi-mcp-server",
            "scope": "yargi.read yargi.search"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        try:
            token = jwt.encode(payload, self.private_key, algorithm="RS256")
            
            # Store token info
            self.tokens[user_id] = {
                "token": token,
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "last_used": now.isoformat()
            }
            
            self._save_tokens()
            
            logger.info(f"Generated token for user {user_id}, expires at {expires_at}")
            return token
            
        except Exception as e:
            logger.error(f"Error generating token: {e}")
            raise
    
    def get_valid_token(self, user_id: str) -> Optional[str]:
        """Get valid token for user, generate new if expired"""
        if user_id not in self.tokens:
            logger.info(f"No token found for user {user_id}, generating new")
            return self.generate_token(user_id)
        
        token_data = self.tokens[user_id]
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        
        # Check if token is expired
        if datetime.utcnow() >= expires_at:
            logger.info(f"Token expired for user {user_id}, generating new")
            return self.generate_token(user_id)
        
        # Check if token needs refresh (less than 2 hours remaining)
        refresh_threshold = expires_at - timedelta(hours=2)
        if datetime.utcnow() >= refresh_threshold:
            logger.info(f"Token near expiry for user {user_id}, refreshing")
            return self.generate_token(user_id)
        
        # Update last used
        token_data["last_used"] = datetime.utcnow().isoformat()
        self._save_tokens()
        
        return token_data["token"]
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate and decode JWT token"""
        try:
            public_key = self.private_key.public_key()
            payload = jwt.decode(
                token, 
                public_key, 
                algorithms=["RS256"],
                audience="yargi-mcp-server"
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens from storage"""
        now = datetime.utcnow()
        expired_users = []
        
        for user_id, token_data in self.tokens.items():
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if now >= expires_at:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.tokens[user_id]
        
        if expired_users:
            self._save_tokens()
            logger.info(f"Cleaned up {len(expired_users)} expired tokens")
    
    def get_token_stats(self) -> Dict[str, Any]:
        """Get token statistics"""
        now = datetime.utcnow()
        active_count = 0
        expired_count = 0
        
        for token_data in self.tokens.values():
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if now < expires_at:
                active_count += 1
            else:
                expired_count += 1
        
        return {
            "total_tokens": len(self.tokens),
            "active_tokens": active_count,
            "expired_tokens": expired_count,
            "storage_path": str(self.storage_path),
            "last_cleanup": now.isoformat()
        }

# Global token manager instance
token_manager = PersistentTokenManager()

# Development helper function
def get_development_token(user_id: str = "dev-user") -> str:
    """Get a development token (for testing)"""
    return token_manager.get_valid_token(user_id)
