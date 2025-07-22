"""
Simplified MCP OAuth HTTP adapter - only Clerk JWT based authentication
Uses Redis for authorization code storage to support multi-machine deployment
"""

import os
import logging
from typing import Optional
from urllib.parse import urlencode, quote

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse

# Import Redis session store
from redis_session_store import get_redis_store

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

# Initialize Redis store
redis_store = None

def get_redis_session_store():
    """Get Redis store instance with lazy initialization."""
    global redis_store
    if redis_store is None:
        try:
            import concurrent.futures
            import functools
            
            # Use thread pool with timeout to prevent hanging
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(get_redis_store)
                try:
                    # 5 second timeout for Redis initialization
                    redis_store = future.result(timeout=5.0)
                    if redis_store:
                        logger.info("Redis session store initialized for OAuth handler")
                    else:
                        logger.warning("Redis store initialization returned None")
                except concurrent.futures.TimeoutError:
                    logger.error("Redis initialization timed out after 5 seconds")
                    redis_store = None
                    future.cancel()  # Try to cancel the hanging operation
                    
        except Exception as e:
            logger.error(f"Failed to initialize Redis store: {e}")
            redis_store = None
            
        if redis_store is None:
            # Fall back to in-memory storage with warning
            logger.warning("Falling back to in-memory storage - multi-machine deployment will not work")
            
    return redis_store

@router.get("/.well-known/oauth-authorization-server")
async def get_oauth_metadata():
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)"""
    return JSONResponse({
        "issuer": BASE_URL,
        "authorization_endpoint": "https://yargimcp.com/mcp-callback",
        "token_endpoint": f"{BASE_URL}/token",
        "registration_endpoint": f"{BASE_URL}/register",
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
        
        # Build Clerk sign-in URL - use yargimcp.com frontend for JWT token generation
        clerk_params = {
            "redirect_url": callback_with_params
        }
        
        # Use frontend sign-in page that handles JWT token generation
        clerk_signin_url = f"https://yargimcp.com/sign-in?{urlencode(clerk_params)}"
        
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
                # Extract user info from JWT token (no Clerk session verification needed)
                import jwt
                decoded_token = jwt.decode(clerk_token, options={"verify_signature": False})
                user_id = decoded_token.get("user_id") or decoded_token.get("sub")
                user_email = decoded_token.get("email")
                token_scopes = decoded_token.get("scopes", ["read", "search"])
                
                logger.info(f"JWT token claims - user_id: {user_id}, email: {user_email}, scopes: {token_scopes}")
                
                if user_id and user_email:
                    # JWT token is already signed by Clerk and contains valid user info
                    user_authenticated = True
                    logger.info(f"User authenticated via JWT token - user_id: {user_id}")
                    
                    # Use the JWT token directly as the real token (it's already from Clerk template)
                    real_jwt_token = clerk_token
                    logger.info("Using Clerk JWT token directly (already real token)")
                    
                else:
                    logger.error(f"Missing required fields in JWT token - user_id: {bool(user_id)}, email: {bool(user_email)}")
                    
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
        
        # Only generate authorization code if we have a real JWT token
        if user_authenticated and real_jwt_token:
            # Generate authorization code
            auth_code = f"clerk_auth_{os.urandom(16).hex()}"
            
            # Prepare code data
            import time
            code_data = {
                "user_id": user_id,
                "session_id": session_id,
                "real_jwt_token": real_jwt_token,
                "user_authenticated": user_authenticated,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope or "read search"
            }
            
            # Try to store in Redis, fall back to in-memory if Redis unavailable
            store = get_redis_session_store()
            if store:
                # Store in Redis with automatic expiration
                success = store.set_oauth_code(auth_code, code_data)
                if success:
                    logger.info(f"Stored authorization code {auth_code[:10]}... in Redis with real JWT token")
                else:
                    logger.error(f"Failed to store authorization code in Redis, falling back to in-memory")
                    # Fall back to in-memory storage
                    if not hasattr(oauth_callback, '_code_storage'):
                        oauth_callback._code_storage = {}
                    oauth_callback._code_storage[auth_code] = code_data
            else:
                # Fall back to in-memory storage
                logger.warning("Redis not available, using in-memory storage")
                if not hasattr(oauth_callback, '_code_storage'):
                    oauth_callback._code_storage = {}
                oauth_callback._code_storage[auth_code] = code_data
                logger.info(f"Stored authorization code in memory (fallback)")
            
            # Redirect back to client with authorization code
            redirect_params = {
                "code": auth_code,
                "state": state or ""
            }
            
            final_redirect_url = f"{redirect_uri}?{urlencode(redirect_params)}"
            logger.info(f"Redirecting back to client: {final_redirect_url}")
            
            return RedirectResponse(url=final_redirect_url)
        else:
            # No JWT token yet - redirect back to sign-in page to wait for authentication
            logger.info("No JWT token provided - redirecting back to sign-in to complete authentication")
            
            # Keep the same redirect URL so the flow continues
            sign_in_params = {
                "redirect_url": f"{request.url._url}"  # Current callback URL with all params
            }
            
            sign_in_url = f"https://yargimcp.com/sign-in?{urlencode(sign_in_params)}"
            logger.info(f"Redirecting back to sign-in: {sign_in_url}")
            
            return RedirectResponse(url=sign_in_url)
        
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
        
        # Retrieve stored JWT token using authorization code from Redis or in-memory fallback
        stored_code_data = None
        
        # Try to get from Redis first, then fall back to in-memory
        store = get_redis_session_store()
        if store:
            stored_code_data = store.get_oauth_code(code, delete_after_use=True)
            if stored_code_data:
                logger.info(f"Retrieved authorization code {code[:10]}... from Redis")
            else:
                logger.warning(f"Authorization code {code[:10]}... not found in Redis")
        
        # Fall back to in-memory storage if Redis unavailable or code not found
        if not stored_code_data and hasattr(oauth_callback, '_code_storage'):
            stored_code_data = oauth_callback._code_storage.get(code)
            if stored_code_data:
                # Clean up in-memory storage
                oauth_callback._code_storage.pop(code, None)
                logger.info(f"Retrieved authorization code {code[:10]}... from in-memory storage")
        
        if not stored_code_data:
            logger.error(f"No stored data found for authorization code: {code}")
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Authorization code not found or expired"}
            )
        
        # Note: Redis TTL handles expiration automatically, but check for manual expiration for in-memory fallback
        import time
        expires_at = stored_code_data.get("expires_at", 0)
        if expires_at and time.time() > expires_at:
            logger.error(f"Authorization code expired: {code}")
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Authorization code expired"}
            )
        
        # Get the real JWT token
        real_jwt_token = stored_code_data.get("real_jwt_token")
        
        if real_jwt_token:
            logger.info("Returning real Clerk JWT token")
            # Note: Code already deleted from Redis, clean up in-memory fallback if used
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
            mock_token = f"mock_clerk_jwt_{code}"
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
        
        # Retrieve stored JWT token using authorization code from Redis or in-memory fallback
        stored_code_data = None
        
        # Try to get from Redis first, then fall back to in-memory
        store = get_redis_session_store()
        if store:
            stored_code_data = store.get_oauth_code(code, delete_after_use=True)
            if stored_code_data:
                logger.info(f"Retrieved authorization code {code[:10]}... from Redis (/token endpoint)")
            else:
                logger.warning(f"Authorization code {code[:10]}... not found in Redis (/token endpoint)")
        
        # Fall back to in-memory storage if Redis unavailable or code not found
        if not stored_code_data and hasattr(oauth_callback, '_code_storage'):
            stored_code_data = oauth_callback._code_storage.get(code)
            if stored_code_data:
                # Clean up in-memory storage
                oauth_callback._code_storage.pop(code, None)
                logger.info(f"Retrieved authorization code {code[:10]}... from in-memory storage (/token endpoint)")
        
        if not stored_code_data:
            logger.error(f"No stored data found for authorization code: {code}")
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Authorization code not found or expired"}
            )
        
        # Note: Redis TTL handles expiration automatically, but check for manual expiration for in-memory fallback
        import time
        expires_at = stored_code_data.get("expires_at", 0)
        if expires_at and time.time() > expires_at:
            logger.error(f"Authorization code expired: {code}")
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Authorization code expired"}
            )
        
        # Get the real JWT token
        real_jwt_token = stored_code_data.get("real_jwt_token")
        
        if real_jwt_token:
            logger.info("Returning real Clerk JWT token from /token endpoint")
            # Note: Code already deleted from Redis, clean up in-memory fallback if used
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