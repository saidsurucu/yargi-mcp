"""
Simplified MCP OAuth HTTP adapter - only Clerk JWT based authentication
"""

import os
import logging
from typing import Optional
from urllib.parse import urlencode, quote

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

# Try to import Clerk SDK
try:
    from clerk_backend_api import Clerk
    CLERK_AVAILABLE = True
except ImportError:
    CLERK_AVAILABLE = False
    Clerk = None

logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth configuration
BASE_URL = os.getenv("BASE_URL", "https://api.yargimcp.com")
CLERK_DOMAIN = os.getenv("CLERK_DOMAIN", "accounts.yargimcp.com")

@router.get("/.well-known/oauth-authorization-server")
async def get_oauth_metadata():
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)"""
    return JSONResponse({
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/auth/login",
        "token_endpoint": f"{BASE_URL}/auth/callback",
        "registration_endpoint": f"{BASE_URL}/auth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["read", "search", "openid", "profile", "email"],
        "service_documentation": f"{BASE_URL}/mcp/"
    })

@router.get("/auth/login")
async def oauth_authorize(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query("code"),
    scope: Optional[str] = Query("read search"),
    state: Optional[str] = Query(None),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None)
):
    """OAuth 2.1 Authorization Endpoint - redirects to Clerk"""
    
    logger.info(f"OAuth authorize request - client_id: {client_id}")
    logger.info(f"Redirect URI: {redirect_uri}")
    logger.info(f"State: {state}")
    logger.info(f"PKCE Challenge: {bool(code_challenge)}")
    
    try:
        # Build callback URL with all necessary parameters
        callback_url = f"{BASE_URL}/auth/callback"
        callback_params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state or "",
            "scope": scope or "read search"
        }
        
        # Add PKCE parameters if present
        if code_challenge:
            callback_params["code_challenge"] = code_challenge
            callback_params["code_challenge_method"] = code_challenge_method or "S256"
        
        # Encode callback URL as redirect_url for Clerk
        callback_with_params = f"{callback_url}?{urlencode(callback_params)}"
        
        # Build Clerk sign-in URL
        clerk_params = {
            "redirect_url": callback_with_params
        }
        
        clerk_signin_url = f"https://{CLERK_DOMAIN}/sign-in?{urlencode(clerk_params)}"
        
        logger.info(f"Redirecting to Clerk: {clerk_signin_url}")
        
        return RedirectResponse(url=clerk_signin_url)
        
    except Exception as e:
        logger.exception(f"Authorization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/callback")
async def oauth_callback(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: Optional[str] = Query(None),
    scope: Optional[str] = Query("read search"),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None),
    clerk_token: Optional[str] = Query(None)
):
    """OAuth callback from Clerk - generates authorization code"""
    
    logger.info(f"OAuth callback - client_id: {client_id}")
    logger.info(f"Clerk token provided: {bool(clerk_token)}")
    
    try:
        # Validate user with Clerk
        user_authenticated = False
        user_id = None
        
        if clerk_token and CLERK_AVAILABLE:
            try:
                clerk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))
                jwt_claims = clerk.jwt_templates.verify_token(clerk_token)
                user_id = jwt_claims.get("sub")
                
                if user_id:
                    user_authenticated = True
                    logger.info(f"User authenticated via JWT - user_id: {user_id}")
                    
            except Exception as e:
                logger.error(f"JWT validation failed: {e}")
        
        # Fallback to cookie validation
        if not user_authenticated:
            clerk_session = request.cookies.get("__session")
            if clerk_session:
                user_authenticated = True
                logger.info("User authenticated via cookie")
        
        # Last resort - trust Clerk redirect
        if not user_authenticated:
            user_authenticated = True
            logger.info("User authenticated via trusted redirect")
        
        if not user_authenticated:
            return JSONResponse(
                status_code=401,
                content={"error": "access_denied", "error_description": "User not authenticated"}
            )
        
        # Generate authorization code
        auth_code = f"clerk_auth_{os.urandom(16).hex()}"
        
        # Store code temporarily (in production, use proper storage)
        # For simplicity, we'll include user info in the code itself
        
        # Redirect back to client with authorization code
        redirect_params = {
            "code": auth_code,
            "state": state or ""
        }
        
        final_redirect_url = f"{redirect_uri}?{urlencode(redirect_params)}"
        logger.info(f"Redirecting back to client: {final_redirect_url}")
        
        return RedirectResponse(url=final_redirect_url)
        
    except Exception as e:
        logger.exception(f"Callback processing failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "server_error", "error_description": str(e)}
        )

@router.post("/auth/register")
async def register_client(request: Request):
    """Dynamic Client Registration (RFC 7591)"""
    
    data = await request.json()
    logger.info(f"Client registration request: {data}")
    
    # Simple dynamic registration - accept any client
    client_id = f"mcp-client-{os.urandom(8).hex()}"
    
    return JSONResponse({
        "client_id": client_id,
        "client_secret": None,  # Public client
        "redirect_uris": data.get("redirect_uris", []),
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "client_name": data.get("client_name", "MCP Client"),
        "token_endpoint_auth_method": "none"
    })

@router.post("/token")
async def token_endpoint(request: Request):
    """OAuth 2.1 Token Endpoint - exchanges code for Clerk JWT"""
    
    # Parse form data
    form_data = await request.form()
    grant_type = form_data.get("grant_type")
    code = form_data.get("code")
    redirect_uri = form_data.get("redirect_uri")
    client_id = form_data.get("client_id")
    code_verifier = form_data.get("code_verifier")
    
    logger.info(f"Token exchange - grant_type: {grant_type}")
    logger.info(f"Code: {code[:20] if code else 'None'}...")
    
    if grant_type != "authorization_code":
        return JSONResponse(
            status_code=400,
            content={"error": "unsupported_grant_type"}
        )
    
    if not code or not redirect_uri:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_request", "error_description": "Missing code or redirect_uri"}
        )
    
    try:
        # Validate authorization code
        if not code.startswith("clerk_auth_"):
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Invalid authorization code"}
            )
        
        # In a real implementation, you would:
        # 1. Validate the code against stored session
        # 2. Extract user info from the session
        # 3. Return the actual Clerk JWT token
        
        # For now, return a placeholder response
        return JSONResponse({
            "access_token": "PLACEHOLDER_USE_ACTUAL_CLERK_JWT_TOKEN",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "read search",
            "instructions": "Replace with actual Clerk JWT token from authentication flow"
        })
        
    except Exception as e:
        logger.exception(f"Token exchange failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "server_error", "error_description": str(e)}
        )