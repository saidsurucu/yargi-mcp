"""
ASGI application for Yargı MCP Server (simple deployment variant).

This is a minimal ASGI application that can be run with:
    uvicorn app:app --host 0.0.0.0 --port 8000

The MCP server will be available at:
    http://localhost:8000/mcp/

For the FastAPI-wrapped variant with CORS and extra metadata routes,
see asgi_app.py instead.
"""

from starlette.responses import JSONResponse
from mcp_server_main import create_app

mcp = create_app()


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for monitoring services (Fly.io, Render, etc.)."""
    return JSONResponse({
        "status": "healthy",
        "service": "Yargı MCP Server",
        "version": "0.2.0",
    })


# Create ASGI app directly from FastMCP server
app = mcp.http_app()

# Endpoints:
# - /mcp/   - MCP server (Streamable HTTP transport, default FastMCP path)
# - /health - Health check for monitoring
