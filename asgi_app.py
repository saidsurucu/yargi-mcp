"""
ASGI application for Yargı MCP Server

This module provides ASGI/HTTP access to the Yargı MCP server,
allowing it to be deployed as a web service with FastAPI wrapper
for Stripe webhook integration.

Usage:
    uvicorn asgi_app:app --host 0.0.0.0 --port 8000
"""

import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

# Import the fully configured MCP app with all tools
from mcp_server_main import app as mcp_server

# Import Stripe webhook router
from stripe_webhook import router as stripe_router

# Import MCP Auth HTTP adapter
from mcp_auth_http_adapter import router as mcp_auth_router

# OAuth configuration from environment variables
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://accounts.yargimcp.com")
BASE_URL = os.getenv("BASE_URL", "https://yargimcp.com")

# Configure CORS middleware
cors_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    ),
]

# Create MCP Starlette sub-application first
mcp_app = mcp_server.http_app(
    path="/",
    middleware=custom_middleware
)

# Create FastAPI wrapper application with MCP app's lifespan
app = FastAPI(
    title="Yargı MCP Server",
    description="MCP server for Turkish legal databases with OAuth authentication",
    version="0.1.0",
    middleware=custom_middleware,
    lifespan=mcp_app.lifespan  # Critical: Get lifespan from mcp_app, not mcp_server
)

# Add Stripe webhook router to FastAPI
app.include_router(stripe_router, prefix="/api")

# Add MCP Auth HTTP adapter to FastAPI (replaces old OAuth router)
app.include_router(mcp_auth_router)

# Custom 401 exception handler for MCP spec compliance
@app.exception_handler(401)
async def custom_401_handler(request: Request, exc: HTTPException):
    """Custom 401 handler that adds WWW-Authenticate header as required by MCP spec"""
    response = await http_exception_handler(request, exc)
    
    # Add WWW-Authenticate header pointing to protected resource metadata
    # as required by RFC 9728 Section 5.1 and MCP Authorization spec
    response.headers["WWW-Authenticate"] = (
        'Bearer '
        'error="invalid_token", '
        'error_description="The access token is missing or invalid", '
        f'resource="{BASE_URL}/.well-known/oauth-protected-resource"'
    )
    
    return response

# Mount MCP app as sub-application
app.mount("/mcp", mcp_app)

# Add POST handler for /mcp to forward to mounted app
@app.post("/mcp")
async def mcp_post_handler(request: Request):
    """Forward POST /mcp requests to mounted MCP app"""
    # Forward to the mounted app by calling it directly
    async def receive():
        return await request.receive()
    
    # Create a new scope for the mounted app
    scope = request.scope.copy()
    scope["path"] = "/"  # Root path for the mounted app
    scope["path_info"] = "/"
    
    # Capture response
    response_parts = {"status": 200, "headers": [], "body": b""}
    
    async def send(message):
        if message["type"] == "http.response.start":
            response_parts["status"] = message["status"]
            response_parts["headers"] = message["headers"]
        elif message["type"] == "http.response.body":
            response_parts["body"] += message.get("body", b"")
    
    # Call the mounted MCP app
    await mcp_app(scope, receive, send)
    
    # Return the response
    from starlette.responses import Response
    
    # Convert ASGI headers to dict
    headers = {}
    for name, value in response_parts["headers"]:
        headers[name.decode()] = value.decode()
    
    return Response(
        content=response_parts["body"],
        status_code=response_parts["status"],
        headers=headers
    )


# FastAPI health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return JSONResponse({
        "status": "healthy",
        "service": "Yargı MCP Server",
        "version": "0.1.0",
        "tools_count": len(mcp_server._tool_manager._tools),
        "auth_enabled": os.getenv("ENABLE_AUTH", "false").lower() == "true"
    })

# FastAPI root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return JSONResponse({
        "service": "Yargı MCP Server",
        "description": "MCP server for Turkish legal databases with OAuth authentication",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health",
            "status": "/status",
            "stripe_webhook": "/api/stripe/webhook",
            "oauth_login": "/auth/login",
            "oauth_callback": "/auth/callback",
            "oauth_google": "/auth/google/login",
            "user_info": "/auth/user"
        },
        "supported_databases": [
            "Yargıtay (Court of Cassation)",
            "Danıştay (Council of State)", 
            "Emsal (Precedent)",
            "Uyuşmazlık Mahkemesi (Court of Jurisdictional Disputes)",
            "Anayasa Mahkemesi (Constitutional Court)",
            "Kamu İhale Kurulu (Public Procurement Authority)",
            "Rekabet Kurumu (Competition Authority)",
            "Sayıştay (Court of Accounts)",
            "Bedesten API (Multiple courts)"
        ],
        "authentication": {
            "enabled": os.getenv("ENABLE_AUTH", "false").lower() == "true",
            "type": "OAuth 2.0 via Clerk",
            "issuer": os.getenv("CLERK_ISSUER", "https://clerk.accounts.dev"),
            "providers": ["google"],
            "flow": "authorization_code"
        }
    })

# OAuth 2.0 Authorization Server Metadata proxy (for MCP clients that can't reach Clerk directly)
@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    """OAuth 2.0 Authorization Server Metadata proxy to Clerk"""
    return JSONResponse({
        "issuer": CLERK_ISSUER,
        "authorization_endpoint": f"{BASE_URL}/auth/login",
        "token_endpoint": f"{BASE_URL}/auth/callback", 
        "jwks_uri": f"{CLERK_ISSUER}/.well-known/jwks.json",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "none"],
        "scopes_supported": ["read", "search", "openid", "profile", "email"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "claims_supported": ["sub", "iss", "aud", "exp", "iat", "email", "name"],
        "code_challenge_methods_supported": ["S256"],
        "service_documentation": f"{BASE_URL}/mcp",
        "registration_endpoint": f"{BASE_URL}/auth/register",
        "resource_documentation": f"{BASE_URL}/mcp"
    })

# MCP endpoint info for GET requests (ChatGPT compatibility)
@app.get("/mcp")
async def mcp_info():
    """MCP endpoint information for discovery"""
    return JSONResponse({
        "mcp_server": True,
        "name": "Yargı MCP Server",
        "version": "0.1.0",
        "description": "MCP server for Turkish legal databases",
        "protocol": "mcp/1.0",
        "transport": "http",
        "authentication_required": True,
        "authentication": {
            "type": "oauth2",
            "authorization_url": f"{BASE_URL}/auth/login",
            "token_url": f"{BASE_URL}/auth/callback",
            "scopes": ["read", "search"],
            "provider": "clerk"
        },
        "endpoints": {
            "mcp_protocol": "/mcp",
            "discovery": "/mcp/discovery",
            "well_known": "/.well-known/mcp",
            "health": "/health",
            "oauth_login": "/auth/login"
        },
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": False
        },
        "tools_count": len(mcp_server._tool_manager._tools),
        "usage": {
            "note": "This is an MCP server. Use POST to /mcp/ with proper MCP protocol headers.",
            "headers_required": [
                "Content-Type: application/json",
                "Accept: application/json, text/event-stream",
                "Authorization: Bearer <token>",
                "X-Session-ID: <session-id>"
            ]
        }
    })

# OAuth 2.0 Protected Resource Metadata (RFC 9728) - MCP Spec Required
@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource():
    """OAuth 2.0 Protected Resource Metadata as required by MCP spec"""
    return JSONResponse({
        "resource": BASE_URL,
        "authorization_servers": [
            BASE_URL
        ],
        "scopes_supported": ["read", "search"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{BASE_URL}/mcp",
        "resource_policy_uri": f"{BASE_URL}/privacy"
    })

# Standard well-known discovery endpoint
@app.get("/.well-known/mcp")
async def well_known_mcp():
    """Standard MCP discovery endpoint"""
    return JSONResponse({
        "mcp_server": {
            "name": "Yargı MCP Server",
            "version": "0.1.0",
            "endpoint": f"{BASE_URL}/mcp",
            "authentication": {
                "type": "oauth2",
                "authorization_url": f"{BASE_URL}/auth/login",
                "scopes": ["read", "search"]
            },
            "capabilities": ["tools", "resources"],
            "tools_count": len(mcp_server._tool_manager._tools)
        }
    })

# MCP Discovery endpoint for ChatGPT integration
@app.get("/mcp/discovery")
async def mcp_discovery():
    """MCP Discovery endpoint for ChatGPT and other MCP clients"""
    return JSONResponse({
        "name": "Yargı MCP Server",
        "description": "MCP server for Turkish legal databases",
        "version": "0.1.0",
        "protocol": "mcp",
        "transport": "http",
        "endpoint": "/mcp",
        "authentication": {
            "type": "oauth2",
            "authorization_url": "/auth/login",
            "token_url": "/auth/callback",
            "scopes": ["read", "search"],
            "provider": "clerk"
        },
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": False
        },
        "tools_count": len(mcp_server._tool_manager._tools),
        "contact": {
            "url": BASE_URL,
            "email": "support@yargi-mcp.dev"
        }
    })

# FastAPI status endpoint
@app.get("/status")
async def status():
    """Status endpoint with detailed information"""
    tools = []
    for tool in mcp_server._tool_manager._tools.values():
        tools.append({
            "name": tool.name,
            "description": tool.description[:100] + "..." if len(tool.description) > 100 else tool.description
        })
    
    return JSONResponse({
        "status": "operational",
        "tools": tools,
        "total_tools": len(tools),
        "transport": "streamable_http",
        "architecture": "FastAPI wrapper + MCP Starlette sub-app",
        "auth_status": "enabled" if os.getenv("ENABLE_AUTH", "false").lower() == "true" else "disabled"
    })

# Alternative: SSE transport (for compatibility)
sse_app = mcp_server.http_app(
    path="/sse", 
    transport="sse",
    middleware=custom_middleware
)

# Export for uvicorn
__all__ = ["app", "sse_app"]