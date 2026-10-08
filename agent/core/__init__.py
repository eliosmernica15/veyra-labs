#!/usr/bin/env python3
"""Agent framework package — architecture only in Phase 3."""
from agent.core.agent_state import AgentTask, AgentStatus, AgentContext
from agent.core.tool_interface import ToolSchema, ToolCall
from agent.core.tool_registry import ToolRegistry
from agent.core.permission import PermissionEnforcer, PERMISSION_LEVELS
from agent.core.audit import AuditLogger
from agent.core.validation import ActionValidator
from agent.core.loop import AgentLoop
from agent.core.mock_tools import ALL_MOCK_TOOLS, MOCK_READ_FILE, MOCK_LIST_DIR
from agent.core.config import AGENT_ENABLED, AGENT_AUTONOMOUS_EXECUTION, AGENT_MOCK_ONLY

__version__ = "0.1.0"
__phase__ = "3"
