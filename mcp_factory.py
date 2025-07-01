import os
from functools import lru_cache
from fastmcp import FastMCP
from fastmcp.server.auth import BearerAuthProvider
from oauth_middleware import ClerkOAuthMiddleware

@lru_cache
def create_app() -> FastMCP:
    """Return a FastMCP instance; OAuth authentication when ENABLE_AUTH=true."""
    # Base app configuration
    app_config = {
        "instructions": "MCP server for TR legal databases (Yargitay, Danistay, Emsal, Uyusmazlik, Anayasa-Norm, Anayasa-Bireysel, KIK, Sayistay, Rekabet).",
        "dependencies": ["httpx", "beautifulsoup4", "markitdown", "pydantic", "aiohttp", "playwright"]
    }
    
    if os.getenv("ENABLE_AUTH", "false").lower() != "true":
        # Development mode - no authentication
        app = FastMCP(
            name="Yargı MCP – DEV",
            **app_config
        )
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