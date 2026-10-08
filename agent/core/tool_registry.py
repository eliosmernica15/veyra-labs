#!/usr/bin/env python3
"""Agent framework: tool registry that holds tool definitions and verifies compatibility."""
from __future__ import annotations

from typing import Dict, List, Optional, Any
from agent.core.tool_interface import ToolSchema


class ToolRegistry:
    """Central registry of available tools. All tools must be explicitly registered; no implicit execution."""
    def __init__(self):
        self._tools: Dict[str, ToolSchema] = {}

    def register(self, schema: ToolSchema):
        if not isinstance(schema, ToolSchema):
            raise TypeError("Only ToolSchema instances may be registered.")
        # Prevent duplicate registration unless explicitly allowed
        if schema.tool_name in self._tools:
            existing = self._tools[schema.tool_name]
            # If both are mocks, allow override for framework testing; otherwise reject
            if not (schema.is_mock and existing.is_mock):
                raise ValueError(f"Tool '{schema.tool_name}' already registered (existing: mock={existing.is_mock}, new: mock={schema.is_mock})")
        self._tools[schema.tool_name] = schema

    def get(self, name: str) -> Optional[ToolSchema]:
        return self._tools.get(name)

    def list_names(self) -> List[str]:
        return list(self._tools.keys())

    def is_mock_only(self) -> bool:
        return all(s.is_mock for s in self._tools.values())

    def describe_all(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._tools.values()]

    def validate_registration_completeness(self) -> Dict[str, Any]:
        # Framework-level sanity check: at least one tool must be registered for any useful agent loop
        # Phase 3 framework does NOT require this to be non-empty (design only), but it reports status
        return {
            "registered_tools": len(self._tools),
            "all_mocks": self.is_mock_only(),
            "names": self.list_names(),
            "ready_for_real_execution": not self.is_mock_only() and len(self._tools) > 0,
        }
