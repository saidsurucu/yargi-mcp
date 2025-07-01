"""
Factory for creating FastMCP app with MCP Auth Toolkit integration
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from fastmcp import FastMCP
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    FastMCP = None

from mcp_auth import (
    OAuthProvider, 
    PolicyEngine, 
    FastMCPAuthWrapper,
    create_default_policies
)
from mcp_auth.clerk_config import create_mcp_server_config


def create_auth_enabled_app(app_name: str = "Yargı MCP Server") -> FastMCP:
    """Create FastMCP app with authentication enabled"""
    
    if not FASTMCP_AVAILABLE:
        raise ImportError("FastMCP is required for authenticated MCP server")
    
    logger.info("Creating FastMCP app with MCP Auth Toolkit integration")
    
    # Create base FastMCP app
    app = FastMCP(app_name)
    
    # Check if authentication is enabled
    auth_enabled = os.getenv("ENABLE_AUTH", "true").lower() == "true"
    
    if not auth_enabled:
        logger.info("Authentication disabled, returning basic FastMCP app")
        return app
    
    try:
        # Get configuration
        logger.info("Getting MCP server configuration...")
        config = create_mcp_server_config()
        logger.info("Configuration loaded successfully")
        
        # Create OAuth provider with Clerk config
        logger.info("Creating OAuth provider...")
        oauth_provider = OAuthProvider(
            config=config["oauth_config"],
            jwt_secret=config["jwt_secret"]
        )
        logger.info("OAuth provider created successfully")
        
        # Create policy engine for Turkish legal database
        policy_engine = create_default_policies()
        
        # Store auth components for later wrapping (after tools are defined)
        app._oauth_provider = oauth_provider
        app._policy_engine = policy_engine
        app._auth_config = config
        
        # Add OAuth endpoints immediately
        @app.tool(
            description="Initiate OAuth 2.1 authorization flow with PKCE",
            annotations={"readOnlyHint": True, "idempotentHint": False}
        )
        async def oauth_authorize(redirect_uri: str, scopes: str = None):
            """OAuth authorization endpoint"""
            scope_list = scopes.split(" ") if scopes else ["mcp:tools:read", "mcp:tools:write"]
            auth_url, pkce = oauth_provider.generate_authorization_url(
                redirect_uri=redirect_uri, scopes=scope_list
            )
            logger.info(f"Generated authorization URL for redirect_uri: {redirect_uri}")
            return {
                "authorization_url": auth_url,
                "code_verifier": pkce.verifier,
                "code_challenge": pkce.challenge,
                "instructions": "Use the authorization_url to complete OAuth flow, then exchange the returned code using oauth_token tool"
            }

        @app.tool(
            description="Exchange OAuth authorization code for access token",
            annotations={"readOnlyHint": False, "idempotentHint": False}
        )
        async def oauth_token(code: str, state: str, redirect_uri: str):
            """OAuth token exchange endpoint"""
            try:
                result = await oauth_provider.exchange_code_for_token(
                    code=code, state=state, redirect_uri=redirect_uri
                )
                logger.info("Successfully exchanged authorization code for token")
                return result
            except Exception as e:
                logger.error(f"Token exchange failed: {e}")
                raise

        @app.tool(
            description="Validate and introspect OAuth access token",
            annotations={"readOnlyHint": True, "idempotentHint": True}
        )
        async def oauth_introspect(token: str):
            """Token introspection endpoint"""
            result = oauth_provider.introspect_token(token)
            logger.debug(f"Token introspection: active={result.get('active', False)}")
            return result

        @app.tool(
            description="Revoke OAuth access token",
            annotations={"readOnlyHint": False, "idempotentHint": False}
        )
        async def oauth_revoke(token: str):
            """Token revocation endpoint"""
            success = oauth_provider.revoke_token(token)
            logger.info(f"Token revocation: success={success}")
            return {"revoked": success}
        
        logger.info("Successfully created authenticated FastMCP app")
        
    except Exception as e:
        logger.error(f"Failed to create authenticated app: {e}")
        logger.info("Falling back to non-authenticated FastMCP app")
        # Return basic app if auth setup fails
        return app
    
    return app


def create_app() -> FastMCP:
    """Create FastMCP app (backwards compatible with mcp_factory.py)"""
    return create_auth_enabled_app()


def get_auth_wrapper(app: FastMCP) -> Optional[FastMCPAuthWrapper]:
    """Get auth wrapper from app if available"""
    return getattr(app, '_auth_wrapper', None)


def get_oauth_provider(app: FastMCP) -> Optional[OAuthProvider]:
    """Get OAuth provider from app if available"""
    return getattr(app, '_oauth_provider', None)


def get_policy_engine(app: FastMCP) -> Optional[PolicyEngine]:
    """Get policy engine from app if available"""
    return getattr(app, '_policy_engine', None)


def is_auth_enabled(app: FastMCP) -> bool:
    """Check if authentication is enabled for the app"""
    return hasattr(app, '_oauth_provider') or hasattr(app, '_auth_wrapper')


def enable_tool_authentication(app: FastMCP):
    """Enable authentication on all existing tools (call after tools are defined)"""
    if not is_auth_enabled(app):
        logger.debug("Authentication not enabled, skipping tool authentication")
        return
    
    oauth_provider = get_oauth_provider(app)
    policy_engine = get_policy_engine(app)
    
    if not oauth_provider or not policy_engine:
        logger.warning("OAuth provider or policy engine not available")
        return
    
    try:
        # Create auth wrapper and wrap tools
        auth_wrapper = FastMCPAuthWrapper(
            mcp_server=app,
            oauth_provider=oauth_provider,
            policy_engine=policy_engine
        )
        
        # Store wrapper for reference
        app._auth_wrapper = auth_wrapper
        
        logger.info("Tool authentication enabled successfully")
        
    except Exception as e:
        logger.error(f"Failed to enable tool authentication: {e}")


def cleanup_auth_sessions(app: FastMCP):
    """Clean up expired auth sessions and tokens"""
    oauth_provider = get_oauth_provider(app)
    if oauth_provider:
        oauth_provider.cleanup_expired_sessions()
        logger.debug("Cleaned up expired OAuth sessions")