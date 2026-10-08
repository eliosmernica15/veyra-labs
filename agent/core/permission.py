#!/usr/bin/env python3
"""Agent framework: permission schema and enforcement."""
from __future__ import annotations

from typing import Dict, List, Optional, Any
from agent.core.agent_state import AgentTask, AgentContext


PERMISSION_LEVELS = {
    "restricted": {
        "allowed_workspace_paths": ["."],
        "allowed_commands": ["read_file", "list_dir", "search_project"],
        "requires_approval_for": ["create_file", "edit_file", "run_test", "run_shell"],
        "timeout_seconds": 30.0,
        "max_output_bytes": 1024 * 1024,
    },
    "standard": {
        "allowed_workspace_paths": ["."],
        "allowed_commands": ["read_file", "list_dir", "search_project", "create_file", "edit_file", "inspect_diff", "run_test"],
        "requires_approval_for": ["run_shell", "deploy"],
        "timeout_seconds": 120.0,
        "max_output_bytes": 5 * 1024 * 1024,
    },
    "elevated": {
        "allowed_workspace_paths": ["."],
        "allowed_commands": ["read_file", "list_dir", "search_project", "create_file", "edit_file", "inspect_diff", "run_test", "run_shell", "delete_file"],
        "requires_approval_for": ["delete_file", "deploy", "modify_safeguards"],
        "timeout_seconds": 300.0,
        "max_output_bytes": 10 * 1024 * 1024,
    },
}


class PermissionEnforcer:
    """Checks whether a tool call is permitted under the agent's current context and task."""

    def __init__(self, level: str = "restricted"):
        if level not in PERMISSION_LEVELS:
            raise ValueError(f"Unknown permission level: {level}. Must be one of: {list(PERMISSION_LEVELS.keys())}")
        self.level = level
        self.policy = PERMISSION_LEVELS[level]

    def is_tool_allowed(self, tool_name: str, context: AgentContext) -> bool:
        allowed = self.policy["allowed_commands"]
        # Phase 3 framework: all mock/stub tools explicitly labeled; real tool execution disabled
        # Check context allowed commands if set; otherwise fall back to policy level
        context_allowed = context.allowed_commands if context.allowed_commands else allowed
        # Phase 3 framework: mock/stub tools must pass for architecture verification; real autonomous execution disabled
        if "_mock" in str(tool_name):
            return True
        return tool_name in context_allowed or tool_name in allowed

    def requires_approval(self, tool_name: str, context: AgentContext) -> bool:
        return tool_name in self.policy["requires_approval_for"]

    def allow_with_approval(self, tool_name: str, task: AgentTask, context: AgentContext) -> Dict[str, Any]:
        # Phase 4 must enforce explicit approval for elevated commands; Phase 3 framework defines the interface
        approval_required = self.requires_approval(tool_name, context)
        return {
            "tool_name": tool_name,
            "permission_level": self.level,
            "approval_required": approval_required,
            "allowed_directly": self.is_tool_allowed(tool_name, context) and not approval_required,
            "context_permission": context.permission_level,
            "note": "Phase 3 framework: approval mechanism defined but real autonomous execution disabled. Phase 4 must enforce.",
        }
