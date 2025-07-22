"""
OAuth 2.1 + PKCE implementation for MCP servers with Clerk integration
"""

import base64
import hashlib
import secrets
import time
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
import jwt
from jwt.exceptions import PyJWTError, InvalidTokenError

from .storage import PersistentStorage

# Try to import Clerk SDK
try:
    from clerk_backend_api import Clerk
    CLERK_AVAILABLE = True
except ImportError:
    CLERK_AVAILABLE = False
    Clerk = None

logger = logging.getLogger(__name__)


@dataclass
class OAuthConfig:
    """OAuth provider configuration for Clerk"""

    client_id: str
    client_secret: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str | None = None
    issuer: str = "mcp-auth"
    scopes: list[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["mcp:tools:read", "mcp:tools:write"]


class PKCEChallenge:
    """PKCE challenge/verifier pair for OAuth 2.1"""

    def __init__(self):
        self.verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )

        challenge_bytes = hashlib.sha256(self.verifier.encode("utf-8")).digest()
        self.challenge = (
            base64.urlsafe_b64encode(challenge_bytes).decode("utf-8").rstrip("=")
        )


class OAuthProvider:
    """OAuth 2.1 provider with PKCE support and Clerk integration"""

    def __init__(self, config: OAuthConfig, jwt_secret: str):
        self.config = config
        self.jwt_secret = jwt_secret
        # Use persistent storage instead of memory
        self.storage = PersistentStorage()
        
        # Initialize Clerk SDK if available
        self.clerk = None
        if CLERK_AVAILABLE and config.client_secret:
            try:
                self.clerk = Clerk(bearer_auth=config.client_secret)
                logger.info("Clerk SDK initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Clerk SDK: {e}")
                
        logger.info("OAuth provider initialized with persistent storage")

    def generate_authorization_url(
        self,
        redirect_uri: str,
        state: str | None = None,
        scopes: list[str] | None = None,
    ) -> tuple[str, PKCEChallenge]:
        """Generate OAuth authorization URL with PKCE for Clerk"""

        pkce = PKCEChallenge()
        session_id = secrets.token_urlsafe(32)

        if state is None:
            state = secrets.token_urlsafe(16)

        if scopes is None:
            scopes = self.config.scopes

        # Store session data with expiration
        session_data = {
            "pkce_verifier": pkce.verifier,
            "state": state,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "created_at": time.time(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=10)).timestamp(),
        }
        self.storage.set_session(session_id, session_data)

        # Build Clerk OAuth URL
        # Check if this is a custom domain (sign-in endpoint)
        if self.config.authorization_endpoint.endswith('/sign-in'):
            # For custom domains, Clerk expects redirect_url parameter
            params = {
                "redirect_url": redirect_uri,
                "state": f"{state}:{session_id}",
            }
            auth_url = f"{self.config.authorization_endpoint}?{urlencode(params)}"
        else:
            # Standard OAuth flow with PKCE
            params = {
                "response_type": "code",
                "client_id": self.config.client_id,
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
                "state": f"{state}:{session_id}",  # Combine state with session ID
                "code_challenge": pkce.challenge,
                "code_challenge_method": "S256",
            }
            auth_url = f"{self.config.authorization_endpoint}?{urlencode(params)}"
        
        logger.info(f"Generated OAuth URL with session {session_id[:8]}...")
        logger.debug(f"Auth URL: {auth_url}")
        return auth_url, pkce

    async def exchange_code_for_token(
        self, code: str, state: str, redirect_uri: str
    ) -> dict[str, Any]:
        """Exchange authorization code for access token with Clerk"""

        try:
            original_state, session_id = state.split(":", 1)
        except ValueError as e:
            logger.error(f"Invalid state format: {state}")
            raise ValueError("Invalid state format") from e

        session = self.storage.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise ValueError("Invalid session")
        
        # Check session expiration
        if datetime.utcnow().timestamp() > session.get("expires_at", 0):
            self.storage.delete_session(session_id)
            logger.error(f"Session {session_id} expired")
            raise ValueError("Session expired")

        if session["state"] != original_state:
            logger.error(f"State mismatch: expected {session['state']}, got {original_state}")
            raise ValueError("State mismatch")

        if session["redirect_uri"] != redirect_uri:
            logger.error(f"Redirect URI mismatch: expected {session['redirect_uri']}, got {redirect_uri}")
            raise ValueError("Redirect URI mismatch")

        # Prepare token exchange request for Clerk
        token_data = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": session["pkce_verifier"],
        }

        logger.info(f"Exchanging code with Clerk for session {session_id[:8]}...")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_endpoint,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )

        if response.status_code != 200:
            logger.error(f"Clerk token exchange failed: {response.status_code} - {response.text}")
            raise ValueError(f"Token exchange failed: {response.text}")

        token_response = response.json()
        logger.info("Successfully exchanged code for Clerk token")

        # Create MCP-scoped JWT token
        access_token = self._create_mcp_token(
            session["scopes"], token_response.get("access_token"), session_id
        )

        # Store token for introspection
        token_id = secrets.token_urlsafe(16)
        token_data = {
            "access_token": access_token,
            "scopes": session["scopes"],
            "created_at": time.time(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            "session_id": session_id,
            "clerk_token": token_response.get("access_token"),
        }
        self.storage.set_token(token_id, token_data)

        # Clean up session
        self.storage.delete_session(session_id)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 3600,
            "scope": " ".join(session["scopes"]),
        }

    def validate_pkce(self, code_verifier: str, code_challenge: str) -> bool:
        """Validate PKCE code challenge (RFC 7636)"""
        # S256 method
        verifier_hash = hashlib.sha256(code_verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(verifier_hash).decode().rstrip('=')
        return expected_challenge == code_challenge

    def _create_mcp_token(
        self, scopes: list[str], upstream_token: str, session_id: str
    ) -> str:
        """Create MCP-scoped JWT token with Clerk token embedded"""

        now = int(time.time())
        payload = {
            "iss": self.config.issuer,
            "sub": session_id,
            "aud": "mcp-server",
            "iat": now,
            "exp": now + 3600,  # 1 hour expiration
            "mcp_tool_scopes": scopes,
            "upstream_token": upstream_token,
            "clerk_integration": True,
        }

        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    def introspect_token(self, token: str) -> dict[str, Any]:
        """Introspect and validate MCP token"""

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])

            # Check if token is expired
            if payload.get("exp", 0) < time.time():
                return {"active": False, "error": "token_expired"}

            return {
                "active": True,
                "sub": payload.get("sub"),
                "aud": payload.get("aud"),
                "iss": payload.get("iss"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat"),
                "mcp_tool_scopes": payload.get("mcp_tool_scopes", []),
                "upstream_token": payload.get("upstream_token"),
                "clerk_integration": payload.get("clerk_integration", False),
            }

        except PyJWTError as e:
            logger.warning(f"Token validation failed: {e}")
            return {"active": False, "error": "invalid_token"}

    def revoke_token(self, token: str) -> bool:
        """Revoke a token"""

        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            session_id = payload.get("sub")

            # Remove all tokens associated with this session
            all_tokens = self.storage.get_tokens()
            tokens_to_remove = [
                token_id
                for token_id, token_data in all_tokens.items()
                if token_data.get("session_id") == session_id
            ]

            for token_id in tokens_to_remove:
                self.storage.delete_token(token_id)

            logger.info(f"Revoked {len(tokens_to_remove)} tokens for session {session_id}")
            return True

        except InvalidTokenError as e:
            logger.warning(f"Token revocation failed: {e}")
            return False

    def cleanup_expired_sessions(self):
        """Clean up expired sessions and tokens"""
        # This is now handled automatically by persistent storage
        self.storage.cleanup_expired_sessions()
        logger.debug("Cleanup completed via persistent storage")