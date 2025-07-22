"""
Starlette integration example for Yargı MCP Server

This module demonstrates how to integrate the Yargı MCP server
with a Starlette application, including authentication middleware
and custom routing.

Usage:
    uvicorn starlette_app:app --host 0.0.0.0 --port 8000
"""

import os
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.authentication import (
    AuthenticationBackend, AuthCredentials, SimpleUser, AuthenticationError
)

# Import the main MCP app
from mcp_server_main import app as mcp_server

# Simple token authentication backend
class TokenAuthBackend(AuthenticationBackend):
    async def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        expected_token = os.getenv("API_TOKEN")
        
        # Skip auth for health check and public endpoints
        if request.url.path in ["/health", "/", "/login"]:
            return None
            
        if not expected_token:
            # No token configured, allow all
            return AuthCredentials(["authenticated"]), SimpleUser("anonymous")
            
        if not auth_header:
            raise AuthenticationError("Authorization header required")
            
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise AuthenticationError("Invalid authentication scheme")
                
            if token != expected_token:
                raise AuthenticationError("Invalid token")
                
            return AuthCredentials(["authenticated"]), SimpleUser("user")
        except ValueError:
            raise AuthenticationError("Invalid authorization header format")

# Homepage
async def homepage(request: Request):
    return JSONResponse({
        "service": "Yargı MCP Server",
        "version": "0.1.0",
        "endpoints": {
            "mcp": "/mcp-server/mcp/",
            "api": "/api/",
            "health": "/health"
        }
    })

# API info endpoint
async def api_info(request: Request):
    if not request.user.is_authenticated:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
        
    return JSONResponse({
        "authenticated_as": request.user.display_name,
        "available_tools": len(mcp_server._tool_manager._tools),
        "databases": [
            "Yargıtay", "Danıştay", "Emsal", "Uyuşmazlık",
            "Anayasa", "KIK", "Rekabet", "Bedesten"
        ]
    })

# Health check
async def health_check(request: Request):
    return JSONResponse({
        "status": "healthy",
        "service": "Yargı MCP Server"
    })

# Login example (returns token for demo)
async def login(request: Request):
    token = os.getenv("API_TOKEN", "demo-token")
    return JSONResponse({
        "message": "Use this token in Authorization header",
        "example": f"Authorization: Bearer {token}",
        "note": "Set API_TOKEN environment variable to change token"
    })

# Create MCP ASGI app
mcp_app = mcp_server.http_app(path='/mcp')

# Configure middleware
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
    Middleware(AuthenticationMiddleware, backend=TokenAuthBackend()),
]

# Create routes
routes = [
    Route("/", homepage),
    Route("/health", health_check),
    Route("/login", login),
    Route("/api/info", api_info),
    Mount("/mcp-server", app=mcp_app),
]

# Create Starlette app
app = Starlette(
    routes=routes,
    middleware=middleware,
    lifespan=mcp_app.lifespan
)

# Nested mount example
def create_nested_app():
    """Example of nested mounting for complex routing structures"""
    
    # Create inner app with MCP
    inner_app = Starlette(
        routes=[Mount("/services", app=mcp_app)],
        middleware=middleware
    )
    
    # Create outer app
    outer_app = Starlette(
        routes=[
            Route("/", homepage),
            Mount("/v1", app=inner_app),
        ],
        lifespan=mcp_app.lifespan
    )
    
    # MCP would be available at /v1/services/mcp/
    return outer_app

# Export both apps
nested_app = create_nested_app()

if __name__ == "__main__":
    import uvicorn
    print("Starting Starlette app with authentication...")
    print("Set API_TOKEN environment variable to enable authentication")
    print("Example: API_TOKEN=secret-token python starlette_app.py")
    uvicorn.run(app, host="0.0.0.0", port=8000)