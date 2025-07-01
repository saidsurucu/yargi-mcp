import os
from functools import lru_cache
from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider

# Conditional import for OAuth middleware
try:
    from oauth_middleware import ClerkOAuthMiddleware
    OAUTH_AVAILABLE = True
except ImportError:
    # OAuth middleware not available - will disable OAuth features
    OAUTH_AVAILABLE = False
    ClerkOAuthMiddleware = None

@lru_cache
def create_app() -> FastMCP:
    """Return a FastMCP instance; OAuth authentication when ENABLE_AUTH=true."""
    # Base app configuration
    app_config = {
        "instructions": "MCP server for TR legal databases (Yargitay, Danistay, Emsal, Uyusmazlik, Anayasa-Norm, Anayasa-Bireysel, KIK, Sayistay, Rekabet).",
        "dependencies": ["httpx", "beautifulsoup4", "markitdown", "pydantic", "aiohttp", "playwright"]
    }
    
    enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    
    if not enable_auth or not OAUTH_AVAILABLE:
        # Development mode - no authentication
        # Either auth is disabled OR OAuth dependencies not available
        app = FastMCP(
            name="Yargı MCP – DEV",
            **app_config
        )
        
        if enable_auth and not OAUTH_AVAILABLE:
            print("Warning: OAuth authentication requested but dependencies not available.")
            print("Install with: uv pip install .[saas]")
    else:
        # Production mode - OAuth authentication via middleware
        app_config["instructions"] += " with OAuth authentication via Clerk."
        app = FastMCP(
            name="Yargı MCP – PROD",
            **app_config
        )
        
        # Add OAuth middleware instead of BearerAuthProvider
        app.add_middleware(ClerkOAuthMiddleware())
    
    return app