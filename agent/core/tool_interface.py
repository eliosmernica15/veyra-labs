#!/usr/bin/env python3
"""Agent framework: tool interface with strict input/output schemas."""
from __future__ import annotations

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json


@dataclass
class ToolSchema:
    tool_name: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema style
    output_schema: Dict[str, Any]
    permission_required: str = "restricted"  # Phase 4 permission enforcement
    timeout_seconds: float = 60.0
    is_mock: bool = False  # MUST be False for real execution; True for framework testing only
    allowed_workspace_paths: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "description": self.description,
            "is_mock": self.is_mock,
            "permission_required": self.permission_required,
            "timeout_seconds": self.timeout_seconds,
            "allowed_workspace_paths": self.allowed_workspace_paths,
            "input_schema_keys": list(self.input_schema.get("properties", {}).keys()) if isinstance(self.input_schema, dict) else [],
            "output_schema_keys": list(self.output_schema.get("properties", {}).keys()) if isinstance(self.output_schema, dict) else [],
        }


@dataclass
class ToolCall:
    call_id: str
    tool_name: str
    input_data: Dict[str, Any]
    proposed_by_agent: bool = True  # Must be explicitly set; framework requires this distinction
    authorized: bool = False
    executed: bool = False
    result: Optional[Any] = None
    error: Optional[str] = None
    audit_trail: List[Dict[str, Any]] = None
    timestamp_proposed: float = 0.0
    timestamp_authorized: float = 0.0
    timestamp_executed: float = 0.0
    timestamp_verified: float = 0.0

    def __post_init__(self):
        if self.audit_trail is None:
            self.audit_trail = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "proposed_by_agent": self.proposed_by_agent,
            "authorized": self.authorized,
            "executed": self.executed,
            "has_result": self.result is not None,
            "error": self.error,
            "audit_entries": len(self.audit_trail),
        }
