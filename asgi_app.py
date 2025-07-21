"""
ASGI application for Yargı MCP Server

This module provides ASGI/HTTP access to the Yargı MCP server,
allowing it to be deployed as a web service with FastAPI wrapper
for Stripe webhook integration.

Usage:
    uvicorn asgi_app:app --host 0.0.0.0 --port 8000
"""

import os
import time
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from starlette.requests import Request as StarletteRequest

# Import the MCP app creator function
from mcp_server_main import create_app

# Import Stripe webhook router
from stripe_webhook import router as stripe_router

# Import simplified MCP Auth HTTP adapter
from mcp_auth_http_simple import router as mcp_auth_router

# OAuth configuration from environment variables
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://accounts.yargimcp.com")
BASE_URL = os.getenv("BASE_URL", "https://yargimcp.com")

# Setup logging
logger = logging.getLogger(__name__)

# Configure CORS and Auth middleware
cors_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Import FastMCP Bearer Auth Provider
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.auth.providers.bearer import RSAKeyPair

# Clerk JWT configuration for Bearer token validation
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://accounts.yargimcp.com")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")

# Configure Bearer token authentication
bearer_auth = None
if CLERK_SECRET_KEY and CLERK_ISSUER:
    # Production: Use Clerk JWKS endpoint for token validation
    bearer_auth = BearerAuthProvider(
        jwks_uri=f"{CLERK_ISSUER}/.well-known/jwks.json",
        issuer=CLERK_ISSUER,
        algorithm="RS256",
        audience=None,  # Disable audience validation - Clerk uses different audience format
        required_scopes=[]  # Disable scope validation - Clerk JWT has ['read', 'search']
    )
    logger.info(f"Bearer auth configured with Clerk JWKS: {CLERK_ISSUER}/.well-known/jwks.json")
else:
    # Development: Generate RSA key pair for testing
    logger.warning("No Clerk credentials found - using development RSA key pair")
    dev_key_pair = RSAKeyPair.generate()
    bearer_auth = BearerAuthProvider(
        public_key=dev_key_pair.public_key,
        issuer="https://dev.yargimcp.com",
        audience="dev-mcp-server",
        required_scopes=["yargi.read"]
    )
    
    # Generate a test token for development
    dev_token = dev_key_pair.create_token(
        subject="dev-user",
        issuer="https://dev.yargimcp.com",
        audience="dev-mcp-server",
        scopes=["yargi.read", "yargi.search"],
        expires_in_seconds=3600 * 24  # 24 hours for development
    )
    logger.info(f"Development Bearer token: {dev_token}")

custom_middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Session-ID"],
    ),
]

# Create MCP app with Bearer authentication
mcp_server = create_app(auth=bearer_auth)

# Add Starlette middleware to FastAPI (not MCP)
# MCP already has Bearer auth, no need for additional middleware on MCP level

# Create MCP Starlette sub-application with root path - mount will add /mcp prefix
mcp_app = mcp_server.http_app(path="/")

# Configure JSON encoder for proper Turkish character support
import json
from fastapi.responses import JSONResponse

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

# Create FastAPI wrapper application
app = FastAPI(
    title="Yargı MCP Server",
    description="MCP server for Turkish legal databases with OAuth authentication",
    version="0.1.0",
    middleware=custom_middleware,
    default_response_class=UTF8JSONResponse  # Use UTF-8 JSON encoder
)

# Add Stripe webhook router to FastAPI
app.include_router(stripe_router, prefix="/api")

# Add MCP Auth HTTP adapter to FastAPI (handles OAuth endpoints)
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
    return JSONResponse({
        "status": "healthy",
        "service": "Yargı MCP Server",
        "version": "0.1.0",
        "tools_count": len(mcp_server._tool_manager._tools),
        "auth_enabled": os.getenv("ENABLE_AUTH", "false").lower() == "true"
    })

# Add explicit redirect for /mcp to /mcp/ with method preservation
@app.api_route("/mcp", methods=["GET", "POST", "HEAD", "OPTIONS"])
async def redirect_to_slash(request: Request):
    """Redirect /mcp to /mcp/ preserving HTTP method with 308"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/mcp/", status_code=308)

# Mount MCP app at /mcp/ with trailing slash
app.mount("/mcp/", mcp_app)

# Set the lifespan context after mounting
app.router.lifespan_context = mcp_app.lifespan


# SSE transport deprecated - removed

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
# MCP Auth Toolkit expects this to be under /mcp/.well-known/oauth-authorization-server
@app.get("/mcp/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    """OAuth 2.0 Authorization Server Metadata proxy to Clerk - MCP Auth Toolkit standard location"""
    return JSONResponse({
        "issuer": BASE_URL,
        "authorization_endpoint": "https://yargimcp.com/mcp-callback",
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
    })

# Claude AI MCP specific endpoint format
@app.get("/.well-known/oauth-authorization-server/mcp")
async def oauth_authorization_server_mcp_suffix():
    """OAuth 2.0 Authorization Server Metadata - Claude AI MCP specific format"""
    return JSONResponse({
        "issuer": BASE_URL,
        "authorization_endpoint": "https://yargimcp.com/mcp-callback",
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
    })

@app.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_protected_resource_mcp_suffix():
    """OAuth 2.0 Protected Resource Metadata - Claude AI MCP specific format"""
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

# Keep root level for compatibility with some MCP clients
@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_root():
    """OAuth 2.0 Authorization Server Metadata proxy to Clerk - root level for compatibility"""
    return JSONResponse({
        "issuer": BASE_URL,
        "authorization_endpoint": "https://yargimcp.com/mcp-callback",
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
    })

# Note: GET /mcp is handled by the mounted MCP app itself
# This prevents 405 Method Not Allowed errors on POST requests

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

# Note: JWT token validation is now handled entirely by Clerk
# All authentication flows use Clerk JWT tokens directly

async def validate_clerk_session(request: Request, clerk_token: str = None) -> str:
    """Validate Clerk session from cookies or JWT token and return user_id"""
    logger.info(f"Validating Clerk session - token provided: {bool(clerk_token)}")
    
    try:
        # Try to import Clerk SDK
        from clerk_backend_api import Clerk
        clerk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))
        
        # Try JWT token first (from URL parameter)
        if clerk_token:
            logger.info("Validating Clerk JWT token from URL parameter")
            try:
                # Extract session_id from JWT token and verify with Clerk
                import jwt
                decoded_token = jwt.decode(clerk_token, options={"verify_signature": False})
                session_id = decoded_token.get("sid")  # Use standard JWT 'sid' claim
                
                if session_id:
                    # Verify with Clerk using session_id
                    session = clerk.sessions.verify(session_id=session_id, token=clerk_token)
                    user_id = session.user_id if session else None
                    
                    if user_id:
                        logger.info(f"JWT token validation successful - user_id: {user_id}")
                        return user_id
                    else:
                        logger.error("JWT token validation failed - no user_id in session")
                else:
                    logger.error("No session_id found in JWT token")
            except Exception as e:
                logger.error(f"JWT token validation failed: {str(e)}")
                # Fall through to cookie validation
        
        # Fallback to cookie validation
        logger.info("Attempting cookie-based session validation")
        clerk_session = request.cookies.get("__session")
        if not clerk_session:
            logger.error("No Clerk session cookie found")
            raise HTTPException(status_code=401, detail="No Clerk session found")
        
        # Validate session with Clerk
        session = clerk.sessions.verify_session(clerk_session)
        logger.info(f"Cookie session validation successful - user_id: {session.user_id}")
        return session.user_id
        
    except ImportError:
        # Fallback for development without Clerk SDK
        logger.warning("Clerk SDK not available - using development fallback")
        return "dev_user_123"
    except Exception as e:
        logger.error(f"Session validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Session validation failed: {str(e)}")

# MCP OAuth Callback Endpoint
@app.get("/auth/mcp-callback")
async def mcp_oauth_callback(request: Request, clerk_token: str = Query(None)):
    """Handle OAuth callback for MCP token generation"""
    logger.info(f"MCP OAuth callback - clerk_token provided: {bool(clerk_token)}")
    
    try:
        # Validate Clerk session with JWT token support
        user_id = await validate_clerk_session(request, clerk_token)
        logger.info(f"User authenticated successfully - user_id: {user_id}")
        
        # Use the Clerk JWT token directly (no need to generate custom token)
        logger.info("User authenticated successfully via Clerk")
        
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
        logger.error(f"MCP OAuth callback failed: {e.detail}")
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
        logger.error(f"Unexpected error in MCP OAuth callback: {str(e)}")
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
        user_id = await validate_clerk_session(request)
        
        return JSONResponse({
            "message": "Use your Clerk JWT token directly with Bearer authentication",
            "token_type": "Bearer",
            "scope": "yargi.read",
            "user_id": user_id,
            "instructions": "Include 'Authorization: Bearer YOUR_CLERK_JWT_TOKEN' in your requests"
        })
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": "invalid_request", "error_description": e.detail}
        )

# Note: Only HTTP transport supported - SSE transport deprecated

# Export for uvicorn
__all__ = ["app"]