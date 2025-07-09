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

# Import the fully configured MCP app with all tools
from mcp_server_main import app as mcp_server

# Import Stripe webhook router
from stripe_webhook import router as stripe_router

# Import MCP Auth HTTP adapter
from mcp_auth_http_adapter import router as mcp_auth_router

# OAuth configuration from environment variables
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "https://accounts.yargimcp.com")
BASE_URL = os.getenv("BASE_URL", "https://yargimcp.com")

# Setup logging
logger = logging.getLogger(__name__)

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

# Create FastAPI wrapper application with MCP lifespan
app = FastAPI(
    title="Yargı MCP Server",
    description="MCP server for Turkish legal databases with OAuth authentication",
    version="0.1.0",
    middleware=custom_middleware,
    lifespan=mcp_app.lifespan  # Only HTTP app lifespan
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

# MCP app handled via custom route handlers - mounting removed

# Add custom route to handle /mcp requests and forward to mounted app
@app.api_route("/mcp", methods=["GET", "POST", "DELETE", "OPTIONS"])
@app.api_route("/mcp/", methods=["GET", "POST", "DELETE", "OPTIONS"])
async def mcp_protocol_handler(request: Request):
    """Handle MCP protocol requests by forwarding to mounted app"""
    
    # Handle GET requests for SSE stream establishment
    if request.method == "GET":
        accept_header = request.headers.get("Accept", "")
        if "text/event-stream" in accept_header:
            # GET requests for SSE don't require session ID validation
            # Continue with JWT validation and SSE stream establishment
            pass
        else:
            # Return 405 Method Not Allowed for non-SSE GET requests
            from starlette.responses import Response
            return Response(
                status_code=405,
                headers={"Allow": "POST, DELETE"},
                content="Method Not Allowed: GET requests require Accept: text/event-stream header"
            )
    
    # Handle DELETE requests for session termination
    if request.method == "DELETE":
        logger.info("DELETE request received for session termination")
        # For session termination, we just return 200 OK
        # The actual session cleanup is handled by the underlying MCP transport
        from starlette.responses import Response
        return Response(
            status_code=200,
            content="Session terminated successfully"
        )
    
    # Optional: Validate Clerk Bearer JWT tokens for direct API access
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            # Validate Clerk JWT token using correct imports
            from clerk_backend_api.security.verifytoken import verify_token
            from clerk_backend_api.security.types import VerifyTokenOptions
            
            # Create verification options
            options = VerifyTokenOptions(
                secret_key=os.getenv("CLERK_SECRET_KEY"),
                api_url="https://api.clerk.com",
                api_version="v1",
                audience=None  # Skip audience validation to avoid issues
            )
            
            # Validate Clerk JWT token directly
            jwt_claims = verify_token(token, options)
            user_id = jwt_claims.get("sub")
            
            if user_id:
                # Extract user information from JWT payload
                user_email = jwt_claims.get('email')  # Primary identifier
                user_name = jwt_claims.get('name')
                user_plan = jwt_claims.get('plan', 'free')  # Default to free plan
                scopes = jwt_claims.get('scopes', ['yargi.read'])
                
                # Use email as primary user identifier if available
                user_id = user_email or user_id
                
                logger.info(f"Clerk JWT token validated successfully")
                logger.info(f"User: {user_email}")
                logger.info(f"Plan: {user_plan}")
                logger.info(f"Scopes: {scopes}")
                
                # Add user info to request state
                request.state.user_id = user_id
                request.state.user_email = user_email
                request.state.user_name = user_name
                request.state.user_plan = user_plan
                request.state.token_scopes = scopes
            else:
                logger.warning(f"Clerk JWT token validation failed - no user_id in claims")
                user_id = None
        except Exception as e:
            logger.warning(f"Clerk Bearer token validation failed: {str(e)}")
            # Don't fail here - let MCP Auth Toolkit handle it
            pass
    
    # Forward the request to the mounted MCP app
    async def receive():
        return await request.receive()
    
    # Create new scope for the mounted app
    scope = request.scope.copy()
    scope["path"] = "/"  # Root path for mounted app
    scope["path_info"] = "/"
    
    # Capture the response
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


# SSE transport deprecated - removed


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
        "transport": ["http"],
        "authentication_required": True,
        "authentication": {
            "type": "oauth2",
            "authorization_url": "https://yargimcp.com/sign-in?redirect_url=https://api.yargimcp.com/auth/mcp-callback",
            "token_url": f"{BASE_URL}/auth/mcp-token",
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
                "Accept: application/json",
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
                # Verify JWT token with Clerk
                jwt_claims = clerk.jwt_templates.verify_token(clerk_token)
                user_id = jwt_claims.get("sub")
                if user_id:
                    logger.info(f"JWT token validation successful - user_id: {user_id}")
                    return user_id
                else:
                    logger.error("JWT token validation failed - no user_id in claims")
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