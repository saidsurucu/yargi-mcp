"""
ASGI application for Yargı MCP Server

This module provides ASGI/HTTP access to the Yargı MCP server,
allowing it to be deployed as a web service.

Usage:
    uvicorn asgi_app:app --host 0.0.0.0 --port 8000
    
Or with custom transport:
    uvicorn asgi_app:sse_app --host 0.0.0.0 --port 8000
"""

import os
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

# Import the main MCP app
from mcp_factory import create_app

mcp_server = create_app()

# Add a health check endpoint
@mcp_server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring"""
    return JSONResponse({
        "status": "healthy",
        "service": "Yargı MCP Server",
        "version": "0.1.0",
        "tools_count": len(mcp_server._tool_manager._tools)
    })

@mcp_server.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    """Root endpoint with service information"""
    return JSONResponse({
        "service": "Yargı MCP Server",
        "description": "MCP server for Turkish legal databases",
        "endpoints": {
            "mcp": "/mcp/",
            "health": "/health",
            "status": "/status"
        },
        "supported_databases": [
            "Yargıtay (Court of Cassation)",
            "Danıştay (Council of State)", 
            "Emsal (Precedent)",
            "Uyuşmazlık Mahkemesi (Court of Jurisdictional Disputes)",
            "Anayasa Mahkemesi (Constitutional Court)",
            "Kamu İhale Kurulu (Public Procurement Authority)",
            "Rekabet Kurumu (Competition Authority)",
            "Bedesten API (Multiple courts)"
        ]
    })

@mcp_server.custom_route("/status", methods=["GET"])
async def status(request: Request) -> JSONResponse:
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
        "transport": "streamable_http"
    })

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

# Import Stripe webhook router
from stripe_webhook import router as stripe_router

# Create ASGI apps with different transports

# Recommended: Streamable HTTP transport
app = mcp_server.http_app(
    path="/mcp",
    middleware=custom_middleware
)

# Add Stripe webhook router
app.include_router(stripe_router, prefix="/api")

# Alternative: SSE transport (for compatibility)
sse_app = mcp_server.http_app(
    path="/sse", 
    transport="sse",
    middleware=custom_middleware
)

# Export for uvicorn
__all__ = ["app", "sse_app"]