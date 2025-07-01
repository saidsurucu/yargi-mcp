"""
OAuth Authentication Router for FastAPI
Handles OAuth flow with Clerk and Google
"""

import os
import secrets
import logging
from typing import Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Response, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.responses import Response as StarletteResponse
from clerk_backend_api import Clerk, SDKError, authenticate_request, AuthenticateRequestOptions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")

# Initialize Clerk client conditionally
clerk_secret = os.getenv("CLERK_SECRET_KEY")
clerk_publishable = os.getenv("CLERK_PUBLISHABLE_KEY")
clerk_domain = os.getenv("CLERK_DOMAIN")  # e.g., "artistic-swan-81"
clerk_issuer = os.getenv("CLERK_ISSUER", f"https://{clerk_domain}.clerk.accounts.dev" if clerk_domain else "https://artistic-swan-81.clerk.accounts.dev")
base_url = os.getenv("BASE_URL", "https://yargi-mcp.fly.dev")
clerk_frontend_url = os.getenv("CLERK_FRONTEND_URL", "http://localhost:3000")
redirect_url = os.getenv("CLERK_OAUTH_REDIRECT_URL", f"{base_url}/auth/callback")
enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"

# Only require Clerk credentials if auth is enabled
if enable_auth and not clerk_secret:
    raise ValueError("CLERK_SECRET_KEY environment variable is required when ENABLE_AUTH=true")

# Initialize Clerk client only if auth is enabled
clerk = None
if enable_auth and clerk_secret:
    clerk = Clerk(bearer_auth=clerk_secret)


@router.get("/login")
async def oauth_login(request: Request, redirect_uri: Optional[str] = None):
    """
    Initiate OAuth login flow with Clerk.
    
    This endpoint redirects to Clerk's OAuth authorization URL.
    After user authorizes, they'll be redirected back to /auth/callback
    """
    # Store the original redirect URI in session/state
    state = secrets.token_urlsafe(32)
    
    # Build Clerk OAuth URL
    # Note: Clerk handles the OAuth flow internally, we just need to redirect to Clerk's sign-in
    final_redirect = redirect_uri or redirect_url
    
    # For ChatGPT, ensure the redirect URL is properly encoded
    if "chatgpt.com" in (final_redirect or ""):
        final_redirect = "https://chatgpt.com/connector_platform_oauth_redirect"
    
    clerk_oauth_params = {
        "redirect_url": final_redirect,
    }
    
    # For Clerk test environment, redirect to our own OAuth endpoint
    # which will handle the Clerk OAuth flow properly
    
    # Check if this is a development/test environment
    is_test_env = clerk_publishable and clerk_publishable.startswith('pk_test_')
    
    if is_test_env:
        # Use our server's OAuth flow for test environment
        oauth_url = f"{base_url}/auth/clerk-oauth?{urlencode(clerk_oauth_params)}"
    else:
        # Production Clerk hosted sign-in
        domain = clerk_domain or clerk_publishable.split('_')[1] if clerk_publishable else "localhost"
        clerk_sign_in_url = f"https://{domain}.clerk.accounts.dev/sign-in"
        oauth_url = f"{clerk_sign_in_url}?{urlencode(clerk_oauth_params)}"
    
    logger.info(f"Redirecting to Clerk OAuth: {oauth_url}")
    
    return RedirectResponse(url=oauth_url)


@router.get("/clerk-oauth")
async def clerk_oauth_handler(request: Request, redirect_url: Optional[str] = None):
    """
    Handle Clerk OAuth flow for test environment.
    
    This endpoint creates a mock OAuth flow that simulates Clerk's behavior
    but works around the 404 issues in test environment.
    """
    # For development/testing, create a simulated OAuth flow
    # In production, this would integrate with Clerk's actual OAuth endpoints
    
    # Generate a mock authorization code
    auth_code = secrets.token_urlsafe(32)
    state = secrets.token_urlsafe(16)
    
    # For ChatGPT, redirect back with the authorization code
    if redirect_url and "chatgpt.com" in redirect_url:
        callback_url = f"{redirect_url}?code={auth_code}&state={state}"
        return RedirectResponse(url=callback_url)
    
    # For other clients, show a simple OAuth consent page
    return JSONResponse({
        "message": "OAuth Authorization Required",
        "authorization_url": f"/auth/callback?code={auth_code}&state={state}",
        "redirect_url": redirect_url or "http://localhost:3000",
        "note": "This is a development OAuth flow. In production, use Clerk's hosted OAuth."
    })


@router.get("/callback")
@router.post("/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    grant_type: Optional[str] = Query(None),
    redirect_uri: Optional[str] = Query(None)
):
    """
    Handle OAuth callback from Clerk.
    
    This endpoint receives the authorization code from Clerk
    and exchanges it for an access token.
    """
    # Handle POST requests with form data
    if request.method == "POST":
        try:
            form_data = await request.form()
            code = code or form_data.get("code")
            grant_type = grant_type or form_data.get("grant_type")
            redirect_uri = redirect_uri or form_data.get("redirect_uri")
            state = state or form_data.get("state")
        except Exception:
            pass  # Continue with query parameters
    
    if error:
        logger.error(f"OAuth error: {error} - {error_description}")
        return JSONResponse(
            status_code=400,
            content={"error": error, "description": error_description}
        )
        
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
        
    try:
        # For development/test environment, create a mock access token
        # In production, this would exchange code with Clerk for real tokens
        
        # Generate a development access token (JWT-like structure)
        import time
        import json
        import base64
        
        # Mock JWT payload for development
        jwt_payload = {
            "sub": "dev_user_123",
            "iss": clerk_issuer,
            "aud": base_url,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour
            "email": "dev@example.com",
            "given_name": "Dev",
            "family_name": "User",
            "sid": "dev_session_123",
            "metadata": {"plan": "free"}
        }
        
        # Create a simple base64 encoded "token" for development
        token_data = base64.b64encode(json.dumps(jwt_payload).encode()).decode()
        session_token = f"dev_token_{token_data}"
        
        # Check if this is a token exchange request (POST with grant_type)
        if request.method == "POST" and grant_type == "authorization_code":
            # OAuth 2.1 token response
            return JSONResponse(content={
                "access_token": session_token,
                "token_type": "Bearer", 
                "expires_in": 3600,
                "refresh_token": f"refresh_{secrets.token_urlsafe(32)}",
                "scope": "read search"
            })
        
        # Check if this is a ChatGPT callback
        original_redirect = redirect_uri or redirect_url
        if "chatgpt.com" in (original_redirect or ""):
            # For ChatGPT, we need to redirect back with the authorization code
            # ChatGPT expects the authorization code to continue the OAuth flow
            return RedirectResponse(
                url=f"{original_redirect}?code={code}&state={state or ''}"
            )
        
        # Return the session token to the client for other clients
        # In a real app, you might:
        # 1. Set this as an HTTP-only cookie
        # 2. Redirect to the frontend with the token
        # 3. Store in a secure session store
        
        response = JSONResponse(content={
            "status": "success",
            "message": "Authentication successful",
            "session_token": session_token,
            "redirect_url": clerk_frontend_url
        })
        
        # Optionally set as cookie
        response.set_cookie(
            key="mcp_session",
            value=session_token,
            httponly=True,
            secure=True,  # Use HTTPS in production
            samesite="lax",
            max_age=86400  # 24 hours
        )
        
        return response
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    Logout user by clearing session.
    """
    # Clear session cookie
    response.delete_cookie("mcp_session")
    
    # If using Clerk session tokens, revoke them here
    # You might also want to call Clerk's signOut endpoint
    
    return JSONResponse(content={
        "status": "success",
        "message": "Logged out successfully"
    })


@router.get("/user")
async def get_current_user(request: Request):
    """
    Get current authenticated user information using Clerk SDK.
    
    This endpoint validates the token and returns user info using authenticate_request.
    """
    # Check if auth is disabled
    if not enable_auth:
        return JSONResponse(content={
            "auth_disabled": True,
            "message": "Authentication is disabled (ENABLE_AUTH=false)",
            "id": "dev_user",
            "email": "dev@example.com",
            "authenticated": False,
            "development_mode": True
        })
        
    # Check if Clerk is not initialized
    if not clerk:
        raise HTTPException(status_code=500, detail="Authentication service not available")
    
    # Check for Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        # Also check for session cookie as fallback
        session_token = request.cookies.get("mcp_session")
        if not session_token:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
    try:
        # Use Clerk SDK to validate the request
        host = request.url.host if hasattr(request.url, 'host') else 'localhost'
        
        request_state = clerk.authenticate_request(
            request,
            AuthenticateRequestOptions(
                accepts_token=['session', 'oauth_token'],
                authorized_parties=[host, 'localhost', '127.0.0.1']
            )
        )
        
        if not request_state.is_signed_in:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
            
        # Extract user info from JWT payload
        payload = request_state.payload
        user_info = {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "first_name": payload.get("given_name"),
            "last_name": payload.get("family_name"),
            "metadata": payload.get("metadata", {}),
            "plan": payload.get("metadata", {}).get("plan", "free"),
            "session_id": payload.get("sid"),
            "org_id": payload.get("org_id"),
            "org_role": payload.get("org_role"),
            "authenticated": True,
            "iat": payload.get("iat"),
            "exp": payload.get("exp")
        }
        
        return JSONResponse(content=user_info)
        
    except SDKError as e:
        logger.error(f"Clerk SDK error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")
    except Exception as e:
        logger.error(f"Error fetching user info: {e}")
        raise HTTPException(status_code=401, detail="Invalid session")


@router.get("/google/login")
async def google_oauth_login(request: Request):
    """
    Initiate Google OAuth login through Clerk.
    
    Clerk handles the OAuth provider connections,
    so we redirect to Clerk's sign-in with Google specified.
    """
    # Build Clerk sign-in URL with Google as the provider
    domain = clerk_domain or clerk_publishable.split('_')[1] if clerk_publishable else "localhost"
    google_oauth_url = f"https://{domain}.clerk.accounts.dev/sign-in#/?strategy=oauth_google"
    
    return RedirectResponse(url=google_oauth_url)


@router.post("/register")
async def dynamic_client_registration(request: Request):
    """
    OAuth 2.0 Dynamic Client Registration (RFC 7591) - MCP Spec SHOULD support.
    
    For development/testing, returns a static client configuration.
    In production, this would integrate with Clerk's client management.
    """
    try:
        # In a real implementation, you would:
        # 1. Validate the request
        # 2. Register the client with Clerk
        # 3. Return proper client credentials
        
        # For now, return a development client configuration
        return JSONResponse(content={
            "client_id": "yargi-mcp-dynamic-client",
            "client_secret": "dev-client-secret-123",
            "client_id_issued_at": 1625097600,
            "client_secret_expires_at": 0,  # Never expires for development
            "redirect_uris": [
                "https://chatgpt.com/connector_platform_oauth_redirect",
                "https://chatgpt.com/auth/callback",
                "http://localhost:3000/auth/callback"
            ],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "read search openid profile email",
            "token_endpoint_auth_method": "client_secret_basic"
        })
        
    except Exception as e:
        logger.error(f"Dynamic client registration error: {e}")
        raise HTTPException(status_code=400, detail="Invalid client registration request")


@router.get("/session/validate")
async def validate_session(request: Request):
    """
    Validate if the current session is active using Clerk SDK.
    
    Used by clients to check auth status.
    """
    auth_header = request.headers.get("Authorization", "")
    session_token = request.cookies.get("mcp_session")
    
    if not auth_header.startswith("Bearer ") and not session_token:
        return JSONResponse(content={"valid": False})
        
    try:
        # Use Clerk SDK to validate the request
        host = request.url.host if hasattr(request.url, 'host') else 'localhost'
        
        request_state = clerk.authenticate_request(
            request,
            AuthenticateRequestOptions(
                accepts_token=['session', 'oauth_token'],
                authorized_parties=[host, 'localhost', '127.0.0.1']
            )
        )
        
        if request_state.is_signed_in and request_state.payload:
            # Get expiration time from JWT payload
            exp_timestamp = request_state.payload.get("exp")
            expires_at = datetime.utcfromtimestamp(exp_timestamp).isoformat() if exp_timestamp else None
            
            return JSONResponse(content={
                "valid": True,
                "user_id": request_state.payload.get("sub"),
                "session_id": request_state.payload.get("sid"),
                "expires_at": expires_at,
                "org_id": request_state.payload.get("org_id"),
                "org_role": request_state.payload.get("org_role")
            })
        else:
            return JSONResponse(content={
                "valid": False,
                "reason": getattr(request_state, 'reason', 'Unknown')
            })
            
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return JSONResponse(content={"valid": False, "error": str(e)})