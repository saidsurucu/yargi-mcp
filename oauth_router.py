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
from clerk_backend_api import Clerk, SDKError, authenticate_request, AuthenticateRequestOptions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")

# Initialize Clerk client conditionally
clerk_secret = os.getenv("CLERK_SECRET_KEY")
clerk_publishable = os.getenv("CLERK_PUBLISHABLE_KEY")
clerk_domain = os.getenv("CLERK_DOMAIN")  # e.g., "artistic-swan-81"
clerk_frontend_url = os.getenv("CLERK_FRONTEND_URL", "http://localhost:3000")
redirect_url = os.getenv("CLERK_OAUTH_REDIRECT_URL", "http://localhost:8000/auth/callback")
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
    clerk_oauth_params = {
        "redirect_url": redirect_uri or redirect_url,
    }
    
    # For Clerk, we typically use their hosted sign-in page
    # or the Clerk.js frontend SDK
    # Use explicit domain if provided, otherwise extract from publishable key
    domain = clerk_domain or clerk_publishable.split('_')[1] if clerk_publishable else "localhost"
    clerk_sign_in_url = f"https://{domain}.clerk.accounts.dev/sign-in"
    
    # Add redirect URL as a query parameter
    oauth_url = f"{clerk_sign_in_url}?{urlencode(clerk_oauth_params)}"
    
    logger.info(f"Redirecting to Clerk OAuth: {oauth_url}")
    
    return RedirectResponse(url=oauth_url)


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """
    Handle OAuth callback from Clerk.
    
    This endpoint receives the authorization code from Clerk
    and exchanges it for an access token.
    """
    if error:
        logger.error(f"OAuth error: {error} - {error_description}")
        return JSONResponse(
            status_code=400,
            content={"error": error, "description": error_description}
        )
        
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
        
    try:
        # In a typical OAuth flow, we would exchange the code for tokens here
        # However, Clerk handles this differently - the frontend SDK manages tokens
        
        # For server-side validation, we need to:
        # 1. Use Clerk's session tokens (not raw OAuth tokens)
        # 2. Or implement a custom session management system
        
        # For now, we'll create a session token that can be validated by our middleware
        # In production, you'd want to:
        # - Store this in a database/cache
        # - Set proper expiration
        # - Link to user's Clerk ID
        
        session_token = secrets.token_urlsafe(64)
        
        # Return the session token to the client
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