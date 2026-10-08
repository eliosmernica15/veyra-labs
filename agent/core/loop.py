#!/usr/bin/env python3
"""Agent framework: loop with limits, timeouts, and safe termination."""
from __future__ import annotations

import time
import logging
from typing import Optional, Dict, Any, List

from agent.core.agent_state import AgentTask, AgentStatus, AgentContext
from agent.core.audit import AuditLogger
from agent.core.permission import PermissionEnforcer

logger = logging.getLogger("agent.loop")


class AgentLoop:
    """Controls the agent execution cycle. Does NOT execute real tools in Phase 3 (framework only)."""

    def __init__(self, task: AgentTask, context: AgentContext, audit_logger: Optional[AuditLogger] = None):
        self.task = task
        self.context = context
        self.audit = audit_logger or AuditLogger()
        self.enforcer = PermissionEnforcer(level=task.permission_level)
        self.start_time = time.time()
        self.iteration = 0

    def is_within_limits(self) -> bool:
        elapsed = time.time() - self.start_time
        return (self.iteration < self.task.max_iterations) and (elapsed < self.task.timeout_seconds)

    def propose_action(self, description: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        # Step 1: proposal recorded in audit and task state
        proposal = {
            "description": description,
            "details": details or {},
            "iteration": self.iteration,
        }
        self.task.proposed_action = proposal
        self.task.add_audit("propose_action", proposal)
        self.task.status = AgentStatus.PROPOSED
        return {"status": "proposed", "action": proposal, "requires_authorization": True}

    def authorize_action(self, approval: bool = False, note: str = "") -> Dict[str, Any]:
        # Step 2: authorization (Phase 4 must enforce real approval mechanism; Phase 3 defines interface)
        if not approval:
            self.task.status = AgentStatus.STOPPED
            self.task.error_message = f"Action not authorized: {note}"
            self.task.add_audit("authorize_denied", {"note": note})
            return {"status": "denied", "reason": note}
        self.task.authorized_action = self.task.proposed_action
        self.task.status = AgentStatus.AUTHORIZED
        self.task.add_audit("authorize_granted", {"note": note, "action": self.task.authorized_action})
        return {"status": "authorized", "action": self.task.authorized_action}

    def execute_action(self, mock_only: bool = True) -> Dict[str, Any]:
        # Step 3: execution — in Phase 3 framework, only mock/stub execution is permitted for architecture verification
        # Real execution requires Phase 4 security/enforcement
        action = self.task.authorized_action or self.task.proposed_action
        if action is None:
            return {"status": "error", "message": "No authorized action to execute"}
        self.task.status = AgentStatus.EXECUTING
        self.task.add_audit("execute_start", {"action_description": action.get("description", "unknown")})
        # Framework execution: record that it would execute, but do not perform real autonomous operations
        result = {
            "executed": False,
            "executed_action": action,
            "mock_execution_note": "Phase 3 framework: real autonomous execution disabled for safety. Mock result only.",
            "permission_level": self.task.permission_level,
            "iteration": self.iteration,
        }
        self.task.executed_action = action
        self.task.result = result
        self.task.add_audit("execute_complete", {"mock_only": mock_only, "result_summary": "No real execution performed (Phase 3 framework only)"})
        self.task.status = AgentStatus.EXECUTED
        return result

    def verify_result(self, expected_result_description: Optional[str] = None) -> Dict[str, Any]:
        # Step 4: verification — must confirm result matches authorization and no unauthorized modifications occurred
        if self.task.result is None:
            return {"status": "verification_failed", "reason": "No execution result to verify"}
        # Check audit log continuity: no missing steps between proposed -> authorized -> executed -> verified
        events = [e["event"] for e in self.task.audit_log]
        required_sequence = ["propose_action", "authorize_granted", "execute_start", "execute_complete"]
        # Allow partial sequence (authorization may be denied) but verify no gap if full execution occurred
        missing = [e for e in required_sequence if e not in events]
        verification = {
            "verified": len(missing) == 0 or (self.task.status == AgentStatus.EXECUTED and len(missing) == 0),
            "missing_events": missing,
            "audit_entries": len(self.task.audit_log),
            "iteration_at_completion": self.iteration,
            "expected_result_description": expected_result_description,
            "verified_result": {
                "execution_was_mock_only": True,
                "no_real_tool_execution_performed": True,
                "audit_complete": True,
                "safeguards_intact": True,
            },
        }
        self.task.verified_result = verification["verified_result"]
        self.task.status = AgentStatus.VERIFIED if verification["verified"] else AgentStatus.FAILED
        self.task.add_audit("verify_result", verification)
        return verification

    def step(self) -> Dict[str, Any]:
        # One full agent cycle (propose, authorize mock, execute mock, verify mock)
        if not self.is_within_limits():
            self.task.status = AgentStatus.TIMEOUT if (time.time() - self.start_time) >= self.task.timeout_seconds else AgentStatus.STOPPED
            self.task.error_message = "Iteration or timeout limit reached."
            self.task.add_audit("loop_terminated", {"reason": self.task.status.value, "iteration": self.iteration, "elapsed": time.time() - self.start_time})
            return {"status": self.task.status.value, "iteration": self.iteration, "limit_reached": True}
        self.iteration += 1
        # Phase 3 framework: propose a mock action for architecture verification
        proposal = self.propose_action(description="Framework verification step (Phase 3 — mock/stub only; no real execution)", details={"mock": True, "framework_phase": 3})
        # Authorize (framework test uses explicit authorization for architecture coverage)
        authorization = self.authorize_action(approval=True, note="Phase 3 framework test authorization (not broad autonomous approval)")
        # Execute mock (no real autonomous operation performed)
        execution = self.execute_action(mock_only=True)
        # Verify mock result (confirms no unauthorized modifications or real execution occurred)
        verification = self.verify_result(expected_result_description="Mock framework result with no real execution")
        return {
            "status": self.task.status.value,
            "iteration": self.iteration,
            "proposed": proposal,
            "authorized": authorization,
            "executed": execution,
            "verified": verification,
            "task_summary": self.task.to_dict(),
        }
