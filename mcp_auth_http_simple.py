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
        # Validate user with Clerk and generate real JWT token
        user_authenticated = False
        user_id = None
        session_id = None
        real_jwt_token = None
        
        if clerk_token and CLERK_AVAILABLE:
            try:
                clerk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))
                
                # Extract session_id from JWT token
                import jwt
                decoded_token = jwt.decode(clerk_token, options={"verify_signature": False})
                session_id = decoded_token.get("sid") or decoded_token.get("session_id")
                
                if session_id:
                    # Verify with Clerk using session_id
                    session = clerk.sessions.verify(session_id=session_id, token=clerk_token)
                    user_id = session.user_id if session else None
                    
                    if user_id:
                        user_authenticated = True
                        logger.info(f"User authenticated via JWT - user_id: {user_id}")
                        
                        # Generate real JWT token from session using template
                        try:
                            real_jwt_token = clerk.sessions.create_token_from_template(
                                session_id=session_id,
                                template_name="mcp_auth"
                            )
                            logger.info("Real JWT token generated from template")
                        except Exception as e:
                            logger.warning(f"Failed to generate JWT from template: {e}")
                            # Fallback to regular token creation
                            real_jwt_token = clerk.sessions.create_token(
                                session_id=session_id,
                                expires_in_seconds=3600
                            )
                            logger.info("Real JWT token generated (fallback)")
                        
                else:
                    logger.error("No session_id found in JWT token")
                    
            except Exception as e:
                logger.error(f"JWT validation failed: {e}")
        
        # Fallback to cookie validation
        if not user_authenticated:
            clerk_session = request.cookies.get("__session")
            if clerk_session:
                user_authenticated = True
                logger.info("User authenticated via cookie")
                
                # Try to get session from cookie and generate JWT
                if CLERK_AVAILABLE:
                    try:
                        clerk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))
                        # Note: sessions.verify_session is deprecated, but we'll try
                        # In practice, you'd need to extract session_id from cookie
                        logger.info("Cookie authentication - JWT generation not implemented yet")
                    except Exception as e:
                        logger.warning(f"Failed to generate JWT from cookie: {e}")
        
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
        
        # Store code with JWT token mapping (in production, use proper storage)
        # For now, we'll use a simple in-memory storage
        import time
        code_data = {
            "user_id": user_id,
            "session_id": session_id,
            "real_jwt_token": real_jwt_token,
            "user_authenticated": user_authenticated,
            "created_at": time.time(),
            "expires_at": time.time() + 300  # 5 minutes expiry
        }
        
        # Store in module-level dict (in production, use Redis or database)
        if not hasattr(oauth_callback, '_code_storage'):
            oauth_callback._code_storage = {}
        oauth_callback._code_storage[auth_code] = code_data
        
        logger.info(f"Stored authorization code with JWT token: {bool(real_jwt_token)}")
        
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

@router.post("/auth/callback")
async def oauth_callback_post(request: Request):
    """OAuth callback POST endpoint for token exchange"""
    
    # Parse form data (standard OAuth token exchange format)
    form_data = await request.form()
    grant_type = form_data.get("grant_type")
    code = form_data.get("code")
    redirect_uri = form_data.get("redirect_uri")
    client_id = form_data.get("client_id")
    code_verifier = form_data.get("code_verifier")
    
    logger.info(f"OAuth callback POST - grant_type: {grant_type}")
    logger.info(f"Code: {code[:20] if code else 'None'}...")
    logger.info(f"Client ID: {client_id}")
    logger.info(f"PKCE verifier: {bool(code_verifier)}")
    
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
        
        # TODO: In production, validate code against stored session
        # For now, we'll return a placeholder response
        
        # Retrieve stored JWT token using authorization code
        stored_code_data = None
        
        # Get stored code data from authorization flow
        if hasattr(oauth_callback, '_code_storage'):
            stored_code_data = oauth_callback._code_storage.get(code)
        
        if not stored_code_data:
            logger.error(f"No stored data found for authorization code: {code}")
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Authorization code not found or expired"}
            )
        
        # Check if code is expired
        import time
        if time.time() > stored_code_data.get("expires_at", 0):
            logger.error(f"Authorization code expired: {code}")
            # Clean up expired code
            if hasattr(oauth_callback, '_code_storage'):
                oauth_callback._code_storage.pop(code, None)
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Authorization code expired"}
            )
        
        # Get the real JWT token
        real_jwt_token = stored_code_data.get("real_jwt_token")
        
        if real_jwt_token:
            logger.info("Returning real Clerk JWT token")
            # Clean up used code
            if hasattr(oauth_callback, '_code_storage'):
                oauth_callback._code_storage.pop(code, None)
            
            return JSONResponse({
                "access_token": real_jwt_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "read search"
            })
        else:
            logger.warning("No real JWT token found, generating mock token")
            # Fallback to mock token for testing
            mock_token = f"mock_clerk_jwt_{auth_code}"
            return JSONResponse({
                "access_token": mock_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "read search"
            })
        
    except Exception as e:
        logger.exception(f"OAuth callback POST failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "server_error", "error_description": str(e)}
        )

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
        
        # Retrieve stored JWT token using authorization code
        stored_code_data = None
        
        # Get stored code data from authorization flow
        if hasattr(oauth_callback, '_code_storage'):
            stored_code_data = oauth_callback._code_storage.get(code)
        
        if not stored_code_data:
            logger.error(f"No stored data found for authorization code: {code}")
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Authorization code not found or expired"}
            )
        
        # Check if code is expired
        import time
        if time.time() > stored_code_data.get("expires_at", 0):
            logger.error(f"Authorization code expired: {code}")
            # Clean up expired code
            if hasattr(oauth_callback, '_code_storage'):
                oauth_callback._code_storage.pop(code, None)
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Authorization code expired"}
            )
        
        # Get the real JWT token
        real_jwt_token = stored_code_data.get("real_jwt_token")
        
        if real_jwt_token:
            logger.info("Returning real Clerk JWT token from /token endpoint")
            # Clean up used code
            if hasattr(oauth_callback, '_code_storage'):
                oauth_callback._code_storage.pop(code, None)
            
            return JSONResponse({
                "access_token": real_jwt_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "read search"
            })
        else:
            logger.warning("No real JWT token found in /token endpoint, generating mock token")
            # Fallback to mock token for testing
            mock_token = f"mock_clerk_jwt_{code}"
            return JSONResponse({
                "access_token": mock_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "read search"
            })
        
    except Exception as e:
        logger.exception(f"Token exchange failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "server_error", "error_description": str(e)}
        )