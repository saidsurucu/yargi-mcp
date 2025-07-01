"""
Authorization policy engine for MCP tools
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PolicyAction(Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class ToolPolicy:
    """Policy rule for MCP tool access"""

    tool_pattern: str  # regex pattern for tool names
    required_scopes: list[str]
    action: PolicyAction = PolicyAction.ALLOW
    conditions: dict[str, Any] | None = None

    def matches_tool(self, tool_name: str) -> bool:
        """Check if the policy applies to given tool"""
        return bool(re.match(self.tool_pattern, tool_name))

    def evaluate_scopes(self, user_scopes: list[str]) -> bool:
        """Check if user has required scopes"""
        return all(scope in user_scopes for scope in self.required_scopes)


class PolicyEngine:
    """Authorization policy engine for Turkish legal database tools"""

    def __init__(self):
        self.policies: list[ToolPolicy] = []
        self.default_action = PolicyAction.DENY

    def add_policy(self, policy: ToolPolicy):
        """Add a policy rule"""
        self.policies.append(policy)
        logger.debug(f"Added policy: {policy.tool_pattern} -> {policy.required_scopes}")

    def add_tool_scope_policy(
        self,
        tool_pattern: str,
        required_scopes: str | list[str],
        action: PolicyAction = PolicyAction.ALLOW,
    ):
        """Convenience method to add tool-scope policy"""
        if isinstance(required_scopes, str):
            required_scopes = [required_scopes]

        policy = ToolPolicy(
            tool_pattern=tool_pattern, required_scopes=required_scopes, action=action
        )
        self.add_policy(policy)

    def authorize_tool_call(
        self,
        tool_name: str,
        user_scopes: list[str],
        user_claims: dict[str, Any] | None = None,
    ) -> tuple[bool, str | None]:
        """
        Authorize a tool call

        Returns:
            (authorized: bool, reason: Optional[str])
        """

        logger.debug(f"Authorizing tool '{tool_name}' for user with scopes: {user_scopes}")

        matching_policies = [
            policy for policy in self.policies if policy.matches_tool(tool_name)
        ]

        if not matching_policies:
            if self.default_action == PolicyAction.ALLOW:
                logger.debug(f"No policies found for '{tool_name}', allowing by default")
                return True, None
            else:
                logger.warning(f"No policies found for '{tool_name}', denying by default")
                return False, f"No policy found for tool '{tool_name}', default deny"

        # Check for explicit deny policies first
        for policy in matching_policies:
            if policy.action == PolicyAction.DENY:
                if policy.evaluate_scopes(user_scopes):
                    logger.warning(f"Explicit deny policy matched for '{tool_name}'")
                    return False, f"Explicit deny policy for tool '{tool_name}'"

        # Check allow policies
        allow_policies = [
            p for p in matching_policies if p.action == PolicyAction.ALLOW
        ]

        if not allow_policies:
            logger.warning(f"No allow policies found for '{tool_name}'")
            return False, f"No allow policies found for tool '{tool_name}'"

        for policy in allow_policies:
            if policy.evaluate_scopes(user_scopes):
                if self._evaluate_conditions(policy.conditions, user_claims):
                    logger.debug(f"Authorization granted for '{tool_name}'")
                    return True, None

        logger.warning(f"Insufficient scopes for '{tool_name}'. Required: {[p.required_scopes for p in allow_policies]}, User has: {user_scopes}")
        return False, f"Insufficient scopes for tool '{tool_name}'"

    def _evaluate_conditions(
        self,
        conditions: dict[str, Any] | None,
        user_claims: dict[str, Any] | None,
    ) -> bool:
        """Evaluate additional policy conditions"""

        if not conditions:
            return True

        if not user_claims:
            logger.debug("No user claims provided, conditions evaluation failed")
            return False

        for key, expected_value in conditions.items():
            user_value = user_claims.get(key)

            if isinstance(expected_value, list):
                if user_value not in expected_value:
                    logger.debug(f"Condition failed: {key} = {user_value} not in {expected_value}")
                    return False
            elif user_value != expected_value:
                logger.debug(f"Condition failed: {key} = {user_value} != {expected_value}")
                return False

        return True

    def get_allowed_tools(self, user_scopes: list[str]) -> list[str]:
        """Get list of tool patterns user is allowed to call"""

        allowed_tools = []

        for policy in self.policies:
            if policy.action == PolicyAction.ALLOW and policy.evaluate_scopes(
                user_scopes
            ):
                allowed_tools.append(policy.tool_pattern)

        return allowed_tools


def create_turkish_legal_policies() -> PolicyEngine:
    """Create policy set for Turkish legal database MCP server"""

    engine = PolicyEngine()

    # Administrative tools (full access)
    engine.add_tool_scope_policy(".*", ["mcp:tools:admin"])

    # Search tools - require read access
    engine.add_tool_scope_policy("search.*", ["mcp:tools:read"])
    
    # Fetch/get document tools - require read access  
    engine.add_tool_scope_policy("get_.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("fetch.*", ["mcp:tools:read"])

    # Specific Turkish legal database tools
    engine.add_tool_scope_policy("search_yargitay.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_danistay.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_anayasa.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_rekabet.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_kik.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_emsal.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_uyusmazlik.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_sayistay.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_.*_bedesten", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_yerel_hukuk.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_istinaf_hukuk.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("search_kyb.*", ["mcp:tools:read"])

    # Document retrieval tools
    engine.add_tool_scope_policy("get_.*_document.*", ["mcp:tools:read"])
    engine.add_tool_scope_policy("get_.*_markdown", ["mcp:tools:read"])

    # Write operations (if any future tools need them)
    engine.add_tool_scope_policy("create_.*", ["mcp:tools:write"])
    engine.add_tool_scope_policy("update_.*", ["mcp:tools:write"]) 
    engine.add_tool_scope_policy("delete_.*", ["mcp:tools:write"])

    logger.info("Created Turkish legal database policy engine")
    return engine


def create_default_policies() -> PolicyEngine:
    """Create a default policy set for MCP servers (backwards compatibility)"""
    return create_turkish_legal_policies()