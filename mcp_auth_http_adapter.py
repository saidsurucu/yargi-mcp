"""
HTTP adapter for MCP Auth Toolkit OAuth endpoints
Exposes MCP OAuth tools as HTTP endpoints for Claude.ai integration
"""

import os
import logging
from typing import Optional
from urllib.parse import urlencode
from datetime import datetime

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth configuration
BASE_URL = os.getenv("BASE_URL", "https://yargimcp.com")


@router.get("/.well-known/oauth-authorization-server")
async def get_oauth_metadata():
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)"""
    return JSONResponse({
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/authorize",
        "token_endpoint": f"{BASE_URL}/token",
        "registration_endpoint": f"{BASE_URL}/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["mcp:tools:read", "mcp:tools:write", "openid", "profile", "email"]
    })


@router.get("/.well-known/oauth-protected-resource")
async def get_protected_resource_metadata():
    """OAuth Protected Resource Metadata (RFC 9728)"""
    return JSONResponse({
        "resource": BASE_URL,
        "authorization_servers": [BASE_URL],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["mcp:tools:read", "mcp:tools:write"],
        "resource_documentation": f"{BASE_URL}/docs"
    })


@router.get("/authorize")
async def authorize_endpoint(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query("S256"),
    state: Optional[str] = Query(None),
    scope: Optional[str] = Query(None)
):
    """OAuth 2.1 Authorization Endpoint - Redirects to MCP Auth tool"""
    
    logger.info(f"OAuth authorize request - client_id: {client_id}, redirect_uri: {redirect_uri}")
    
    # Import here to avoid circular imports
    try:
        from mcp_server_main import app as mcp_app
        from mcp_auth_factory import get_oauth_provider
        
        # Get OAuth provider from MCP app
        oauth_provider = get_oauth_provider(mcp_app)
        if not oauth_provider:
            logger.error("OAuth provider not available in MCP app")
            raise HTTPException(status_code=500, detail="OAuth provider not configured")
        
        # Generate authorization URL using MCP Auth Toolkit
        auth_url, pkce = oauth_provider.generate_authorization_url(
            redirect_uri=redirect_uri,
            state=state,
            scopes=scope.split(" ") if scope else None
        )
        
        logger.info(f"Generated auth URL: {auth_url[:100]}...")
        
        # Redirect to Clerk OAuth
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        logger.exception(f"Authorization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/callback")
async def oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None)
):
    """Handle OAuth callback from Clerk"""
    
    logger.info(f"OAuth callback - code: {code[:20] if code else 'None'}..., state: {state[:20] if state else 'None'}...")
    
    if error:
        logger.error(f"OAuth error: {error} - {error_description}")
        return JSONResponse(
            status_code=400,
            content={"error": error, "error_description": error_description}
        )
    
    if not code or not state:
        logger.error("Missing code or state in callback")
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_request", "error_description": "Missing code or state parameter"}
        )
    
    try:
        # Import here to avoid circular imports
        from mcp_server_main import app as mcp_app
        from mcp_auth_factory import get_oauth_provider
        
        # Get OAuth provider
        oauth_provider = get_oauth_provider(mcp_app)
        if not oauth_provider:
            raise HTTPException(status_code=500, detail="OAuth provider not configured")
        
        # Parse state to get original client state and session ID
        try:
            original_state, session_id = state.split(":", 1)
        except ValueError:
            logger.error(f"Invalid state format: {state}")
            raise HTTPException(status_code=400, detail="Invalid state format")
        
        # Get session data from storage
        session = oauth_provider.storage.get_session(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=400, detail="Invalid session")
        
        # Exchange code for token with Clerk
        token_result = await oauth_provider.exchange_code_for_token(
            code=code,
            state=state,
            redirect_uri=session["redirect_uri"]
        )
        
        # Build redirect URL back to Claude with authorization code
        # The "code" here is our session ID that Claude will exchange for a token
        redirect_params = {
            "code": session_id,
            "state": original_state
        }
        
        redirect_url = f"{session['redirect_uri']}?{urlencode(redirect_params)}"
        logger.info(f"Redirecting back to Claude: {redirect_url}")
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.exception(f"Callback processing failed: {e}")
        # Try to redirect back with error
        if session and "redirect_uri" in session:
            error_params = {
                "error": "server_error",
                "error_description": str(e),
                "state": original_state if 'original_state' in locals() else state
            }
            error_url = f"{session['redirect_uri']}?{urlencode(error_params)}"
            return RedirectResponse(url=error_url)
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "server_error", "error_description": str(e)}
            )


@router.post("/register")
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
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "client_name": data.get("client_name", "MCP Client"),
        "token_endpoint_auth_method": "none",
        "client_id_issued_at": int(datetime.now().timestamp())
    })


@router.post("/token")
async def token_endpoint(request: Request):
    """OAuth 2.1 Token Endpoint"""
    
    # Parse form data
    form_data = await request.form()
    grant_type = form_data.get("grant_type")
    code = form_data.get("code")
    redirect_uri = form_data.get("redirect_uri")
    client_id = form_data.get("client_id")
    code_verifier = form_data.get("code_verifier")
    
    logger.info(f"Token exchange - grant_type: {grant_type}, code: {code[:20] if code else 'None'}...")
    
    if grant_type != "authorization_code":
        return JSONResponse(
            status_code=400,
            content={"error": "unsupported_grant_type"}
        )
    
    try:
        # Import here to avoid circular imports
        from mcp_server_main import app as mcp_app
        from mcp_auth_factory import get_oauth_provider
        
        # Get OAuth provider
        oauth_provider = get_oauth_provider(mcp_app)
        if not oauth_provider:
            raise HTTPException(status_code=500, detail="OAuth provider not configured")
        
        # The "code" is actually our session ID
        session_id = code
        session = oauth_provider.storage.get_session(session_id)
        
        if not session:
            logger.error(f"Session {session_id} not found for token exchange")
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Invalid authorization code"}
            )
        
        # Validate PKCE
        if "pkce_verifier" in session:
            # Session has the verifier stored, validate it matches
            if code_verifier != session["pkce_verifier"]:
                logger.error("PKCE verifier mismatch")
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_grant", "error_description": "Invalid code verifier"}
                )
        else:
            logger.warning("No PKCE verifier in session, skipping validation")
        
        # Create JWT token
        access_token = oauth_provider._create_mcp_token(
            session["scopes"], 
            session.get("clerk_token", ""), 
            session_id
        )
        
        # Clean up session
        oauth_provider.storage.delete_session(session_id)
        
        return JSONResponse({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": " ".join(session["scopes"])
        })
        
    except Exception as e:
        logger.exception(f"Token exchange failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "server_error", "error_description": str(e)}
        )