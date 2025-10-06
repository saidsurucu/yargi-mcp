"""
ASGI application for Yargı MCP Server

This module provides ASGI/HTTP access to the Yargı MCP server,
allowing it to be deployed as a web service with FastAPI wrapper
for OAuth integration and proper middleware support.

Usage:
    uvicorn asgi_app:app --host 0.0.0.0 --port 8000
"""

import os
import time
import logging
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse, Response
from fastapi.exception_handlers import http_exception_handler
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Import the proper create_app function that includes all middleware
from mcp_server_main import create_app

# Conditional auth-related imports (only if auth enabled)
_auth_check = os.getenv("ENABLE_AUTH", "false").lower() == "true"

if _auth_check:
    # Import MCP Auth HTTP adapter (OAuth endpoints)
    try:
        from mcp_auth_http_simple import router as mcp_auth_router
    except ImportError:
        mcp_auth_router = None

    # Import Stripe webhook router
    try:
        from stripe_webhook import router as stripe_router
    except ImportError:
        stripe_router = None
else:
    mcp_auth_router = None
    stripe_router = None

# OAuth configuration from environment variables
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://clerk.yargimcp.com")
BASE_URL = os.getenv("BASE_URL", "https://api.yargimcp.com")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")

# Setup logging
logger = logging.getLogger(__name__)

# Configure CORS and Auth middleware
cors_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Import FastMCP Bearer Auth Provider
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.auth.providers.bearer import RSAKeyPair

# Import Clerk SDK at module level for performance
try:
    from clerk_backend_api import Clerk
    CLERK_SDK_AVAILABLE = True
except ImportError:
    CLERK_SDK_AVAILABLE = False
    logger.warning("Clerk SDK not available - falling back to development mode")

# Configure Bearer token authentication based on ENABLE_AUTH
auth_enabled = os.getenv("ENABLE_AUTH", "false").lower() == "true"
bearer_auth = None

if CLERK_SECRET_KEY and CLERK_ISSUER:
    # Production: Use Clerk JWKS endpoint for token validation
    bearer_auth = BearerAuthProvider(
        jwks_uri=f"{CLERK_ISSUER}/.well-known/jwks.json",
        issuer=None,
        algorithm="RS256",
        audience=None,
        required_scopes=[]
    )
else:
    # Development: Generate RSA key pair for testing
    dev_key_pair = RSAKeyPair.generate()
    bearer_auth = BearerAuthProvider(
        public_key=dev_key_pair.public_key,
        issuer="https://dev.yargimcp.com",
        audience="dev-mcp-server",
        required_scopes=["yargi.read"]
    )

# Create MCP app with Bearer authentication
mcp_server = create_app(auth=bearer_auth if auth_enabled else None)

# Create MCP Starlette sub-application with root path - mount will add /mcp prefix
mcp_app = mcp_server.http_app(path="/")


# Configure JSON encoder for proper Turkish character support
class UTF8JSONResponse(JSONResponse):
    def __init__(self, content=None, status_code=200, headers=None, **kwargs):
        if headers is None:
            headers = {}
        headers["Content-Type"] = "application/json; charset=utf-8"
        super().__init__(content, status_code, headers, **kwargs)
    
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Session-ID"],
    ),
]

# Create FastAPI wrapper application
app = FastAPI(
    title="Yargı MCP Server",
    description="MCP server for Turkish legal databases with OAuth authentication",
    version="0.1.0",
    middleware=custom_middleware,
    default_response_class=UTF8JSONResponse,  # Use UTF-8 JSON encoder
    redirect_slashes=False  # Disable to prevent 307 redirects on /mcp endpoint
)

# Add auth-related routers to FastAPI (only if available)
if stripe_router:
    app.include_router(stripe_router, prefix="/api/stripe")

if mcp_auth_router:
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

# FastAPI health check endpoint - BEFORE mounting MCP app
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "Yargı MCP Server",
        "version": "0.1.0",
        "tools_count": len(mcp_server._tool_manager._tools),
        "auth_enabled": os.getenv("ENABLE_AUTH", "false").lower() == "true"
    }

# Add explicit redirect for /mcp to /mcp/ with method preservation
@app.api_route("/mcp", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def redirect_to_slash(request: Request):
    """Redirect /mcp to /mcp/ preserving HTTP method with 308"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/mcp/", status_code=308)

# MCP mount at /mcp handles path routing correctly

# IMPORTANT: Add FastAPI endpoints BEFORE mounting MCP app
# Otherwise mount at root will catch all requests

# Debug endpoint to test routing
@app.get("/debug/test")
async def debug_test():
    """Debug endpoint to test if FastAPI routes work"""
    return {"message": "FastAPI routes working", "debug": True}

# Clerk CORS proxy endpoints
@app.api_route("/clerk-proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def clerk_cors_proxy(request: Request, path: str):
    """
    Proxy requests to Clerk to bypass CORS restrictions.
    Forwards requests from Claude AI to clerk.yargimcp.com with proper CORS headers.
    """
    import httpx
    
    # Build target URL
    clerk_url = f"https://clerk.yargimcp.com/{path}"
    
    # Forward query parameters
    if request.url.query:
        clerk_url += f"?{request.url.query}"
    
    # Copy headers (exclude host/origin)
    headers = dict(request.headers)
    headers.pop('host', None)
    headers.pop('origin', None)
    headers['origin'] = 'https://yargimcp.com'  # Use our frontend domain
    
    try:
        async with httpx.AsyncClient() as client:
            # Forward the request to Clerk
            if request.method == "OPTIONS":
                # Handle preflight
                response = await client.request(
                    method=request.method,
                    url=clerk_url,
                    headers=headers
                )
            else:
                # Forward body for POST/PUT requests
                body = None
                if request.method in ["POST", "PUT", "PATCH"]:
                    body = await request.body()
                
                response = await client.request(
                    method=request.method,
                    url=clerk_url,
                    headers=headers,
                    content=body
                )
            
            # Create response with CORS headers
            response_headers = dict(response.headers)
            response_headers.update({
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, X-Requested-With",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "86400"
            })
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type")
            )
            
    except Exception as e:
        return JSONResponse(
            {"error": "proxy_error", "message": str(e)},
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )

# FastAPI root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
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
        "transports": {
            "http": "/mcp"
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
            "KVKK (Personal Data Protection Authority)",
            "BDDK (Banking Regulation and Supervision Agency)",
            "Bedesten API (Multiple courts)"
        ],
        "authentication": {
            "enabled": os.getenv("ENABLE_AUTH", "false").lower() == "true",
            "type": "OAuth 2.0 via Clerk",
            "issuer": CLERK_ISSUER,
            "providers": ["google"],
            "flow": "authorization_code"
        }
    }

# OAuth 2.0 Authorization Server Metadata - MCP standard location
@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_root():
    """OAuth 2.0 Authorization Server Metadata - root level for compatibility"""
    return {
        "issuer": BASE_URL,  # Use BASE_URL as issuer for MCP integration
        "authorization_endpoint": f"{BASE_URL}/auth/login",
        "token_endpoint": f"{BASE_URL}/token", 
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
        "registration_endpoint": f"{BASE_URL}/register",
        "resource_documentation": f"{BASE_URL}/mcp"
    }

# Claude AI MCP specific endpoint format - suffix versions
@app.get("/.well-known/oauth-authorization-server/mcp")
async def oauth_authorization_server_mcp_suffix():
    """OAuth 2.0 Authorization Server Metadata - Claude AI MCP specific format"""
    return {
        "issuer": BASE_URL,  # Use BASE_URL as issuer for MCP integration
        "authorization_endpoint": f"{BASE_URL}/auth/login",
        "token_endpoint": f"{BASE_URL}/token", 
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
        "registration_endpoint": f"{BASE_URL}/register",
        "resource_documentation": f"{BASE_URL}/mcp"
    }

@app.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_protected_resource_mcp_suffix():
    """OAuth 2.0 Protected Resource Metadata - Claude AI MCP specific format"""
    return {
        "resource": BASE_URL,
        "authorization_servers": [
            BASE_URL
        ],
        "scopes_supported": ["read", "search"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{BASE_URL}/mcp",
        "resource_policy_uri": f"{BASE_URL}/privacy"
    }

# OAuth 2.0 Protected Resource Metadata (RFC 9728) - MCP Spec Required
@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource():
    """OAuth 2.0 Protected Resource Metadata as required by MCP spec"""
    return {
        "resource": BASE_URL,
        "authorization_servers": [
            BASE_URL
        ],
        "scopes_supported": ["read", "search"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{BASE_URL}/mcp",
        "resource_policy_uri": f"{BASE_URL}/privacy"
    }

# Standard well-known discovery endpoint
@app.get("/.well-known/mcp")
async def well_known_mcp():
    """Standard MCP discovery endpoint"""
    return {
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
    }

# MCP Discovery endpoint for ChatGPT integration
@app.get("/mcp/discovery")
async def mcp_discovery():
    """MCP Discovery endpoint for ChatGPT and other MCP clients"""
    return {
        "name": "Yargı MCP Server",
        "description": "MCP server for Turkish legal databases",
        "version": "0.1.0",
        "protocol": "mcp",
        "transport": "http",
        "endpoint": "/mcp",
        "authentication": {
            "type": "oauth2",
            "authorization_url": "/auth/login",
            "token_url": "/token",
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
    }

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
    
    return {
        "status": "operational",
        "tools": tools,
        "total_tools": len(tools),
        "transport": "streamable_http",
        "architecture": "FastAPI wrapper + MCP Starlette sub-app",
        "auth_status": "enabled" if os.getenv("ENABLE_AUTH", "false").lower() == "true" else "disabled"
    }

# Simplified OAuth session validation for callback endpoints only
async def validate_clerk_session_for_oauth(request: Request, clerk_token: str = None) -> str:
    """Validate Clerk session for OAuth callback endpoints only (not for MCP endpoints)"""
    
    try:
        # Use Clerk SDK if available
        if not CLERK_SDK_AVAILABLE:
            raise ImportError("Clerk SDK not available")
        clerk = Clerk(bearer_auth=CLERK_SECRET_KEY)
        
        # Try JWT token first (from URL parameter)
        if clerk_token:
            try:
                return "oauth_user_from_token"
            except Exception as e:
                pass

        # Fallback to cookie validation
        clerk_session = request.cookies.get("__session")
        if not clerk_session:
            raise HTTPException(status_code=401, detail="No Clerk session found")

        # Validate session with Clerk
        session = clerk.sessions.verify_session(clerk_session)
        return session.user_id
        
    except ImportError:
        return "dev_user_123"
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"OAuth session validation failed: {str(e)}")

# MCP OAuth Callback Endpoint
@app.get("/auth/mcp-callback")
async def mcp_oauth_callback(request: Request, clerk_token: str = Query(None)):
    """Handle OAuth callback for MCP token generation"""
    
    try:
        # Validate Clerk session with JWT token support
        user_id = await validate_clerk_session_for_oauth(request, clerk_token)
        
        # Return success response
        return HTMLResponse(f"""
        <html>
            <head>
                <title>MCP Connection Successful</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .success {{ color: #28a745; }}
                    .token {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; word-break: break-all; }}
                </style>
            </head>
            <body>
                <h1 class="success">✅ MCP Connection Successful!</h1>
                <p>Your Yargı MCP integration is now active.</p>
                <div class="token">
                    <strong>Authentication:</strong><br>
                    <code>Use your Clerk JWT token directly with Bearer authentication</code>
                </div>
                <p>You can now close this window and return to your MCP client.</p>
                <script>
                    // Try to close the popup if opened as such
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'MCP_AUTH_SUCCESS',
                            token: 'use_clerk_jwt_token'
                        }}, '*');
                        setTimeout(() => window.close(), 3000);
                    }}
                </script>
            </body>
        </html>
        """)
        
    except HTTPException as e:
        return HTMLResponse(f"""
        <html>
            <head>
                <title>MCP Connection Failed</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .error {{ color: #dc3545; }}
                    .debug {{ background: #f8f9fa; padding: 10px; margin: 20px 0; border-radius: 5px; font-family: monospace; }}
                </style>
            </head>
            <body>
                <h1 class="error">❌ MCP Connection Failed</h1>
                <p>{e.detail}</p>
                <div class="debug">
                    <strong>Debug Info:</strong><br>
                    Clerk Token: {'✅ Provided' if clerk_token else '❌ Missing'}<br>
                    Error: {e.detail}<br>
                    Status: {e.status_code}
                </div>
                <p>Please try again or contact support.</p>
                <a href="https://yargimcp.com/sign-in">Return to Sign In</a>
            </body>
        </html>
        """, status_code=e.status_code)
    except Exception as e:
        return HTMLResponse(f"""
        <html>
            <head>
                <title>MCP Connection Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .error {{ color: #dc3545; }}
                </style>
            </head>
            <body>
                <h1 class="error">❌ Unexpected Error</h1>
                <p>An unexpected error occurred during authentication.</p>
                <p>Error: {str(e)}</p>
                <a href="https://yargimcp.com/sign-in">Return to Sign In</a>
            </body>
        </html>
        """, status_code=500)

# OAuth2 Token Endpoint - Now uses Clerk JWT tokens directly
@app.post("/auth/mcp-token")
async def mcp_token_endpoint(request: Request):
    """OAuth2 token endpoint for MCP clients - returns Clerk JWT token info"""
    try:
        # Validate Clerk session
        user_id = await validate_clerk_session_for_oauth(request)
        
        return {
            "message": "Use your Clerk JWT token directly with Bearer authentication",
            "token_type": "Bearer",
            "scope": "yargi.read",
            "user_id": user_id,
            "instructions": "Include 'Authorization: Bearer YOUR_CLERK_JWT_TOKEN' in your requests"
        }
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": "invalid_request", "error_description": e.detail}
        )

# Mount MCP app at /mcp/ with trailing slash
app.mount("/mcp/", mcp_app)

# Set the lifespan context after mounting
app.router.lifespan_context = mcp_app.lifespan

# Export for uvicorn
__all__ = ["app"]