"""
MCP server middleware for OAuth authentication and authorization
"""

import functools
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from fastmcp import FastMCP
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    FastMCP = None
    logger.warning("FastMCP not available, some features will be disabled")

from .oauth import OAuthProvider
from .policy import PolicyEngine


@dataclass
class AuthContext:
    """Authentication context passed to MCP tools"""

    user_id: str
    scopes: list[str]
    claims: dict[str, Any]
    token: str


class MCPAuthMiddleware:
    """Authentication middleware for MCP servers"""

    def __init__(self, oauth_provider: OAuthProvider, policy_engine: PolicyEngine):
        self.oauth_provider = oauth_provider
        self.policy_engine = policy_engine

    def authenticate_request(self, authorization_header: str) -> AuthContext | None:
        """Extract and validate auth token from request"""

        if not authorization_header:
            logger.debug("No authorization header provided")
            return None

        if not authorization_header.startswith("Bearer "):
            logger.debug("Authorization header does not start with 'Bearer '")
            return None

        token = authorization_header[7:]  # Remove 'Bearer ' prefix

        token_info = self.oauth_provider.introspect_token(token)

        if not token_info.get("active"):
            logger.warning("Token is not active")
            return None

        logger.debug(f"Authenticated user: {token_info.get('sub', 'unknown')}")

        return AuthContext(
            user_id=token_info.get("sub", "unknown"),
            scopes=token_info.get("mcp_tool_scopes", []),
            claims=token_info,
            token=token,
        )

    def authorize_tool_call(
        self, tool_name: str, auth_context: AuthContext
    ) -> tuple[bool, str | None]:
        """Check if user can call the specified tool"""

        return self.policy_engine.authorize_tool_call(
            tool_name=tool_name,
            user_scopes=auth_context.scopes,
            user_claims=auth_context.claims,
        )


def auth_required(
    oauth_provider: OAuthProvider,
    policy_engine: PolicyEngine,
    tool_name: str | None = None,
):
    """
    Decorator to require authentication for MCP tool functions

    Usage:
        @auth_required(oauth_provider, policy_engine, "search_yargitay")
        def my_tool_function(context: AuthContext, ...):
            pass
    """

    def decorator(func: Callable) -> Callable:
        middleware = MCPAuthMiddleware(oauth_provider, policy_engine)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract authorization header from kwargs
            auth_header = kwargs.pop("authorization", None)
            
            # Also check in args if it's a Request object
            if not auth_header and args:
                for arg in args:
                    if hasattr(arg, 'headers'):
                        auth_header = arg.headers.get("Authorization")
                        break

            if not auth_header:
                logger.warning(f"No authorization header for tool '{tool_name or func.__name__}'")
                raise PermissionError("Authorization header required")

            auth_context = middleware.authenticate_request(auth_header)

            if not auth_context:
                logger.warning(f"Authentication failed for tool '{tool_name or func.__name__}'")
                raise PermissionError("Invalid or expired token")

            actual_tool_name = tool_name or func.__name__

            authorized, reason = middleware.authorize_tool_call(
                actual_tool_name, auth_context
            )

            if not authorized:
                logger.warning(f"Authorization failed for tool '{actual_tool_name}': {reason}")
                raise PermissionError(f"Access denied: {reason}")

            # Add auth context to function call
            return await func(auth_context, *args, **kwargs)

        return wrapper

    return decorator


class FastMCPAuthWrapper:
    """Wrapper for FastMCP servers to add authentication"""

    def __init__(
        self,
        mcp_server: "FastMCP",
        oauth_provider: OAuthProvider,
        policy_engine: PolicyEngine,
    ):
        if not FASTMCP_AVAILABLE:
            raise ImportError("FastMCP is required for FastMCPAuthWrapper")
            
        self.mcp_server = mcp_server
        self.middleware = MCPAuthMiddleware(oauth_provider, policy_engine)
        self.oauth_provider = oauth_provider
        logger.info("Initializing FastMCP authentication wrapper")
        self._wrap_tools()

    def _wrap_tools(self):
        """Wrap all existing tools with auth middleware"""

        # Try different FastMCP tool storage locations
        tool_registry = None
        
        if hasattr(self.mcp_server, '_tools'):
            tool_registry = self.mcp_server._tools
        elif hasattr(self.mcp_server, 'tools'):
            tool_registry = self.mcp_server.tools
        elif hasattr(self.mcp_server, '_tool_registry'):
            tool_registry = self.mcp_server._tool_registry
        elif hasattr(self.mcp_server, '_handlers') and hasattr(self.mcp_server._handlers, 'tools'):
            tool_registry = self.mcp_server._handlers.tools
        
        if not tool_registry:
            logger.warning("FastMCP server tool registry not found, tools will not be automatically wrapped")
            logger.debug(f"Available server attributes: {dir(self.mcp_server)}")
            return

        logger.debug(f"Found tool registry with {len(tool_registry)} tools")
        original_tools = dict(tool_registry)
        wrapped_count = 0

        for tool_name, tool_func in original_tools.items():
            try:
                wrapped_func = self._create_auth_wrapper(tool_name, tool_func)
                tool_registry[tool_name] = wrapped_func
                wrapped_count += 1
                logger.debug(f"Wrapped tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to wrap tool {tool_name}: {e}")

        logger.info(f"Successfully wrapped {wrapped_count} tools with authentication")

    def _create_auth_wrapper(self, tool_name: str, original_func: Callable) -> Callable:
        """Create auth wrapper for a specific tool"""

        @functools.wraps(original_func)
        async def auth_wrapper(*args, **kwargs):
            # Extract authorization from various sources
            auth_header = None
            
            # Check kwargs first
            auth_header = kwargs.pop("authorization", None)
            
            # Check if first argument is a Request object
            if not auth_header and args:
                first_arg = args[0]
                if hasattr(first_arg, 'headers'):
                    auth_header = first_arg.headers.get("Authorization")

            if not auth_header:
                logger.warning(f"No authorization header for tool '{tool_name}'")
                raise PermissionError("Authorization required")

            auth_context = self.middleware.authenticate_request(auth_header)

            if not auth_context:
                logger.warning(f"Authentication failed for tool '{tool_name}'")
                raise PermissionError("Invalid token")

            authorized, reason = self.middleware.authorize_tool_call(
                tool_name, auth_context
            )

            if not authorized:
                logger.warning(f"Authorization failed for tool '{tool_name}': {reason}")
                raise PermissionError(f"Access denied: {reason}")

            # Add auth context to kwargs
            kwargs["auth_context"] = auth_context
            logger.debug(f"Calling tool '{tool_name}' for user {auth_context.user_id}")
            
            return await original_func(*args, **kwargs)

        return auth_wrapper

    def add_oauth_endpoints(self):
        """Add OAuth endpoints to the MCP server"""

        @self.mcp_server.tool(
            description="Initiate OAuth 2.1 authorization flow with PKCE",
            annotations={"readOnlyHint": True, "idempotentHint": False}
        )
        async def oauth_authorize(redirect_uri: str, scopes: Optional[str] = None):
            """OAuth authorization endpoint"""
            scope_list = scopes.split(" ") if scopes else None
            auth_url, pkce = self.oauth_provider.generate_authorization_url(
                redirect_uri=redirect_uri, scopes=scope_list
            )
            logger.info(f"Generated authorization URL for redirect_uri: {redirect_uri}")
            return {
                "authorization_url": auth_url,
                "code_verifier": pkce.verifier,  # For PKCE flow
                "code_challenge": pkce.challenge,
                "instructions": "Use the authorization_url to complete OAuth flow, then exchange the returned code using oauth_token tool"
            }

        @self.mcp_server.tool(
            description="Exchange OAuth authorization code for access token",
            annotations={"readOnlyHint": False, "idempotentHint": False}
        )
        async def oauth_token(
            code: str,
            state: str,
            redirect_uri: str
        ):
            """OAuth token exchange endpoint"""
            try:
                result = await self.oauth_provider.exchange_code_for_token(
                    code=code, state=state, redirect_uri=redirect_uri
                )
                logger.info("Successfully exchanged authorization code for token")
                return result
            except Exception as e:
                logger.error(f"Token exchange failed: {e}")
                raise

        @self.mcp_server.tool(
            description="Validate and introspect OAuth access token",
            annotations={"readOnlyHint": True, "idempotentHint": True}
        )
        async def oauth_introspect(token: str):
            """Token introspection endpoint"""
            result = self.oauth_provider.introspect_token(token)
            logger.debug(f"Token introspection: active={result.get('active', False)}")
            return result

        @self.mcp_server.tool(
            description="Revoke OAuth access token",
            annotations={"readOnlyHint": False, "idempotentHint": False}
        )
        async def oauth_revoke(token: str):
            """Token revocation endpoint"""
            success = self.oauth_provider.revoke_token(token)
            logger.info(f"Token revocation: success={success}")
            return {"revoked": success}

        @self.mcp_server.tool(
            description="Get list of tools available to authenticated user",
            annotations={"readOnlyHint": True, "idempotentHint": True}
        )
        async def oauth_user_tools(authorization: str):
            """Get user's allowed tools based on scopes"""
            auth_context = self.middleware.authenticate_request(authorization)
            if not auth_context:
                raise PermissionError("Invalid token")
            
            allowed_patterns = self.middleware.policy_engine.get_allowed_tools(auth_context.scopes)
            
            return {
                "user_id": auth_context.user_id,
                "scopes": auth_context.scopes,
                "allowed_tool_patterns": allowed_patterns,
                "message": "Use these patterns to determine which tools you can access"
            }

        logger.info("Added OAuth endpoints: oauth_authorize, oauth_token, oauth_introspect, oauth_revoke, oauth_user_tools")