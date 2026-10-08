#!/usr/bin/env python3
"""Agent framework: validation of tool inputs, outputs, and action results."""
from __future__ import annotations

from typing import Dict, Any, Optional
import json

from agent.core.agent_state import AgentTask, AgentStatus


class ActionValidator:
    """Validates proposed actions against schemas, checks for unexpected modifications, and verifies results."""

    def __init__(self):
        pass

    def validate_proposed_action(self, action: Dict[str, Any], allowed_commands: list) -> Dict[str, Any]:
        # Check description/scheme presence
        if "description" not in action:
            return {"valid": False, "reason": "Proposed action missing description"}
        # Check that no disallowed command is present
        details = action.get("details", {})
        if isinstance(details, dict) and "command" in details:
            cmd = details.get("command", "")
            if cmd not in allowed_commands:
                return {"valid": False, "reason": f"Command '{cmd}' not in allowed list: {allowed_commands}"}
        return {"valid": True, "reason": "Action proposal passes validation"}

    def validate_executed_result(self, result: Dict[str, Any], task: AgentTask) -> Dict[str, Any]:
        # Ensure no unauthorized modifications occurred
        # In Phase 3 framework (mock/stub only), verify that result indicates no real execution
        mock_only = result.get("mock_execution_note", None)
        if mock_only is not None:
            return {"valid": True, "reason": "Mock execution verified; no real autonomous execution occurred"}
        # If real execution occurred (Phase 4 future), additional checks must be enforced:
        # - workspace boundaries respected
        # - no path traversal
        # - output size within limits
        # - no secret redaction failures
        # - audit log complete
        # For Phase 3, any non-mock execution must fail validation
        return {"valid": False, "reason": "Real autonomous execution not permitted in Phase 3 framework (security disabled until Phase 4)"}

    def check_path_traversal(self, file_path: str, workspace: str = ".") -> bool:
        # Basic path traversal protection (Phase 4 must enforce fully)
        import os
        try:
            abs_path = os.path.abspath(file_path)
            abs_workspace = os.path.abspath(workspace)
            return abs_path.startswith(abs_workspace)
        except Exception:
            return False

    def check_output_size(self, content: str | bytes, max_bytes: int) -> bool:
        size = len(content) if isinstance(content, bytes) else len(str(content).encode("utf-8"))
        return size <= max_bytes
