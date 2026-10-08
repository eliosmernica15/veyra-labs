#!/usr/bin/env python3
"""Agent framework: state, task model, and lifecycle tracking."""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class AgentStatus(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    EXECUTED = "executed"
    VERIFIED = "verified"
    FAILED = "failed"
    STOPPED = "stopped"
    TIMEOUT = "timeout"


@dataclass
class AgentTask:
    task_id: str = field(default_factory=lambda: f"task_{int(time.time()*1000)}")
    objective: str = ""
    status: AgentStatus = AgentStatus.IDLE
    steps: List[str] = field(default_factory=list)
    max_iterations: int = 10
    timeout_seconds: float = 300.0  # 5 minutes default per agent loop
    permission_level: str = "restricted"  # restricted | standard | elevated (Phase 4 to enforce)
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    audit_log: List[Dict[str, Any]] = field(default_factory=list)
    proposed_action: Optional[Dict[str, Any]] = None
    authorized_action: Optional[Dict[str, Any]] = None
    executed_action: Optional[Dict[str, Any]] = None
    verified_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "permission_level": self.permission_level,
            "steps": self.steps,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "has_result": self.result is not None,
            "audit_entries": len(self.audit_log),
            "proposed": self.proposed_action is not None,
            "authorized": self.authorized_action is not None,
            "executed": self.executed_action is not None,
            "verified": self.verified_result is not None,
        }

    def add_audit(self, event: str, details: Optional[Dict] = None):
        entry = {
            "timestamp": time.time(),
            "event": event,
            "details": details or {},
            "task_status_at_event": self.status.value if isinstance(self.status, AgentStatus) else str(self.status),
        }
        self.audit_log.append(entry)
        self.updated_at = time.time()


@dataclass
class AgentContext:
    """Context maintained by the agent loop."""
    workspace_path: str = "."
    workspace_boundaries: List[str] = field(default_factory=list)  # permitted subpaths
    available_tools: List[str] = field(default_factory=list)
    allowed_commands: List[str] = field(default_factory=list)  # Phase 4 command allowlist
    max_output_size_bytes: int = 1024 * 1024  # 1MB limit (Phase 4)
    secret_patterns: List[str] = field(default_factory=lambda: ["password", "token", "secret", "key"])
    iteration_limit: int = 10
    overall_timeout: float = 300.0  # 5 minutes per full agent task
    permission_level: str = "restricted"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
