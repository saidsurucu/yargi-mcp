"""
OAuth Middleware for FastMCP Server
Handles Clerk OAuth token validation and user context
"""

import os
import logging
from typing import Optional, Dict, Any
from fastmcp.server.middleware import Middleware, MiddlewareContext
from clerk_backend_api import Clerk, SDKError, authenticate_request, AuthenticateRequestOptions
from mcp import McpError
from mcp.types import ErrorData

logger = logging.getLogger(__name__)


class ClerkOAuthMiddleware(Middleware):
    """
    Middleware that validates OAuth tokens via Clerk API and adds user context.
    
    This middleware intercepts MCP requests over HTTP transport and validates
    OAuth access tokens provided in the Authorization header.
    """
    
    def __init__(self):
        """Initialize the middleware with Clerk client."""
        self.enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"
        self.clerk_secret = os.getenv("CLERK_SECRET_KEY")
        
        # Only require Clerk credentials if auth is enabled
        if self.enable_auth and not self.clerk_secret:
            raise ValueError("CLERK_SECRET_KEY environment variable is required when ENABLE_AUTH=true")
            
        # Initialize Clerk client only if auth is enabled
        self.clerk = None
        if self.enable_auth and self.clerk_secret:
            self.clerk = Clerk(bearer_auth=self.clerk_secret)
        
    async def on_request(self, context: MiddlewareContext, call_next):
        """
        Validate OAuth token on every request.
        
        For HTTP transport:
        1. Extract OAuth token from Authorization header
        2. Validate token with Clerk API
        3. Add user info to context
        4. Check user permissions/plan
        """
        # Skip auth if disabled
        if not self.enable_auth:
            return await call_next(context)
            
        # Check if this is an HTTP transport request
        if not hasattr(context, 'fastmcp_context') or not context.fastmcp_context:
            # Non-HTTP transport (e.g., stdio), skip auth
            return await call_next(context)
            
        # Try to get the request object from context
        request = getattr(context.fastmcp_context, 'request', None)
        if not request:
            # No HTTP request object, likely stdio transport
            return await call_next(context)
            
        # Check for Authorization header (Clerk SDK will handle token extraction)
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise McpError(ErrorData(
                code=-32001,
                message="Missing or invalid Authorization header. Expected: Bearer <token>"
            ))
        
        # Validate token and get user info using Clerk SDK
        if not self.clerk:
            raise McpError(ErrorData(
                code=-32001,
                message="Authentication service not available"
            ))
            
        user_info = self._validate_oauth_token(request)
        if not user_info:
            raise McpError(ErrorData(
                code=-32001,
                message="Invalid or expired OAuth token"
            ))
            
        # Add user info to context for downstream use
        context.user_info = user_info
        
        # Check user permissions/plan
        if not self._check_user_permissions(user_info):
            raise McpError(ErrorData(
                code=-32002,
                message="Insufficient permissions. Upgrade your plan for access."
            ))
            
        logger.info(f"Authenticated user: {user_info.get('id')} ({user_info.get('email')})")
        
        # Continue with the request
        return await call_next(context)
        
    def _validate_oauth_token(self, request) -> Optional[Dict[str, Any]]:
        """
        Validate OAuth token using Clerk SDK's authenticate_request method.
        
        Returns user info if token is valid, None otherwise.
        """
        try:
            # Get the host for authorized parties
            host = request.url.host if hasattr(request.url, 'host') else 'localhost'
            
            # Use Clerk SDK's authenticate_request method
            request_state = self.clerk.authenticate_request(
                request,
                AuthenticateRequestOptions(
                    # Accept both session tokens and OAuth tokens
                    accepts_token=['session', 'oauth_token'],
                    authorized_parties=[host, 'localhost', '127.0.0.1']
                )
            )
            
            if request_state.is_signed_in and request_state.payload:
                payload = request_state.payload
                
                # Extract user information from JWT payload
                return {
                    "id": payload.get("sub"),  # Subject (user ID)
                    "email": payload.get("email"),
                    "first_name": payload.get("given_name"),
                    "last_name": payload.get("family_name"),
                    "metadata": payload.get("metadata", {}),
                    "plan": payload.get("metadata", {}).get("plan", "free"),
                    "session_id": payload.get("sid"),  # Session ID
                    "org_id": payload.get("org_id"),   # Organization ID (if any)
                    "org_role": payload.get("org_role"), # Organization role (if any)
                    "iat": payload.get("iat"),  # Issued at
                    "exp": payload.get("exp"),  # Expires at
                }
            else:
                logger.warning(f"Token validation failed: {request_state.reason if hasattr(request_state, 'reason') else 'Unknown reason'}")
                return None
                
        except SDKError as e:
            logger.error(f"Clerk SDK error validating token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating OAuth token: {e}")
            return None
            
    def _check_user_permissions(self, user_info: Dict[str, Any]) -> bool:
        """
        Check if user has necessary permissions based on their plan.
        
        This is where you can implement role-based access control.
        """
        # Get user's plan from metadata
        user_plan = user_info.get("plan", "free")
        
        # For now, allow all authenticated users
        # You can implement more sophisticated permission checks here
        # For example:
        # - Free users: limited to X requests per day
        # - Pro users: full access
        # - Enterprise: priority access + higher limits
        
        return True  # Allow all authenticated users for now
        
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Additional validation for tool calls.
        
        Can be used to implement tool-specific permissions.
        """
        # Check if user has access to this specific tool
        if hasattr(context, 'user_info'):
            tool_name = context.message.name if hasattr(context.message, 'name') else None
            user_plan = context.user_info.get('plan', 'free')
            
            # Example: Restrict certain tools to paid users
            premium_tools = ["advanced_analysis", "bulk_export"]
            if tool_name in premium_tools and user_plan == 'free':
                raise McpError(ErrorData(
                    code=-32002,
                    message=f"Tool '{tool_name}' requires a Pro plan or higher"
                ))
                
        return await call_next(context)