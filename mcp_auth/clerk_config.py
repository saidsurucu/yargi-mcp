"""
Clerk OAuth configuration for MCP Auth Toolkit
"""

import os
import logging
from .oauth import OAuthConfig

logger = logging.getLogger(__name__)


def create_clerk_oauth_config() -> OAuthConfig:
    """Create OAuth configuration for Clerk integration"""
    
    # Get Clerk configuration from environment
    clerk_domain = os.getenv("CLERK_DOMAIN", "accounts.yargimcp.com")
    clerk_publishable_key = os.getenv("CLERK_PUBLISHABLE_KEY")
    clerk_secret_key = os.getenv("CLERK_SECRET_KEY")
    
    if not clerk_publishable_key or not clerk_secret_key:
        raise ValueError("CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY are required")
    
    # Determine if custom domain or standard Clerk domain
    if '.' in clerk_domain and not clerk_domain.endswith('.accounts.dev'):
        # Custom domain like accounts.yargimcp.com
        base_url = f"https://{clerk_domain}"
        issuer = f"https://{clerk_domain}"
    else:
        # Standard Clerk subdomain
        base_url = f"https://{clerk_domain}.accounts.dev"
        issuer = f"https://{clerk_domain}.accounts.dev"
    
    config = OAuthConfig(
        client_id=clerk_publishable_key,
        client_secret=clerk_secret_key,
        authorization_endpoint=f"{base_url}/oauth/authorize",
        token_endpoint=f"{base_url}/oauth/token",
        jwks_uri=f"{base_url}/.well-known/jwks.json",
        issuer=issuer,
        scopes=["mcp:tools:read", "mcp:tools:write", "openid", "profile", "email"]
    )
    
    logger.info(f"Created Clerk OAuth config for domain: {clerk_domain}")
    logger.debug(f"Authorization endpoint: {config.authorization_endpoint}")
    logger.debug(f"Token endpoint: {config.token_endpoint}")
    
    return config


def get_jwt_secret() -> str:
    """Get JWT secret for token signing"""
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    
    if not jwt_secret:
        raise ValueError("JWT_SECRET_KEY environment variable is required")
    
    return jwt_secret


def create_mcp_server_config():
    """Create complete MCP server configuration for Clerk integration"""
    
    try:
        oauth_config = create_clerk_oauth_config()
        jwt_secret = get_jwt_secret()
        
        return {
            "oauth_config": oauth_config,
            "jwt_secret": jwt_secret,
            "base_url": os.getenv("BASE_URL", "https://yargi-mcp.fly.dev"),
            "auth_enabled": os.getenv("ENABLE_AUTH", "true").lower() == "true"
        }
        
    except Exception as e:
        logger.error(f"Failed to create MCP server config: {e}")
        raise