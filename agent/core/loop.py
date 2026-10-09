#!/usr/bin/env python3
"""Agent framework: loop with limits, timeouts, and safe termination."""
from __future__ import annotations

import time
import logging
from typing import Optional, Dict, Any, List

from agent.core.task_state import MultiStepTaskState, TaskState
from agent.core.project_memory import ProjectMemory
from agent.core.audit_crypto import CryptographicAuditLogger
from agent.core.agent_state import AgentTask, AgentStatus, AgentContext
from agent.core.audit import AuditLogger
from agent.core.permission import PermissionEnforcer, PERMISSION_LEVELS
from agent.core.approval_system import ApprovalSystem
from agent.core.resource_limits import ResourceLimits

# Phase 5 real execution imports (restricted, not autonomous)
try:
    from agent.core.real_file_tools import RealFileTools
    REAL_FILE_TOOLS_AVAILABLE = True
except ImportError:
    REAL_FILE_TOOLS_AVAILABLE = False

logger = logging.getLogger("agent.loop")


class AgentLoop:
    """Controls the agent execution cycle. Does NOT execute real tools in Phase 3 (framework only)."""

    def __init__(self, task: AgentTask, context: AgentContext, audit_logger: Optional[AuditLogger] = None, workspace_path: str = ".", permission_level: Optional[str] = None):
        self.task = task
        self.context = context
        self.audit = audit_logger or AuditLogger()
        self.enforcer = PermissionEnforcer(level=permission_level or task.permission_level)
        self.approval_system = ApprovalSystem()
        self.resource_limits = ResourceLimits(
            max_iterations=task.max_iterations,
            per_tool_timeout=30.0,
            overall_task_timeout=task.timeout_seconds,
            max_output_bytes=context.max_output_size_bytes,
        )
        self.start_time = time.time()
        self.iteration = 0
        self.workspace_path = workspace_path
        self.task_state = MultiStepTaskState(task_id=task.task_id, objective=task.objective)
        self.task_state.transition_to(TaskState.RECEIVED, "Task initialized")
        if hasattr(task, "multi_step_state") and task.multi_step_state:
            self.task_state.recover_from_state({"current_state": task.multi_step_state, "states_history": task.state_history})
        self.project_memory = ProjectMemory(memory_path=f".agent_memory/{task.task_id}_memory.json")
        self.real_file_tools = None
        # Phase 5 real restricted execution (not autonomous)
        if not task.mock_only and REAL_FILE_TOOLS_AVAILABLE:
            try:
                audit_for_real = CryptographicAuditLogger() if audit_logger is None else audit_logger
                self.real_file_tools = RealFileTools(
                    workspace_path=workspace_path,
                    permission_level=permission_level or task.permission_level,
                    audit_logger=audit_for_real,
                )
            except Exception:
                self.real_file_tools = None

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
        self.task_state.transition_to(TaskState.PLANNING, "Action proposed")
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
        self.task_state.transition_to(TaskState.EXECUTING, f"Authorized: {note}")
        return {"status": "authorized", "action": self.task.authorized_action}

    def execute_action(self, mock_only: bool = True) -> Dict[str, Any]:
        action = self.task.authorized_action or self.task.proposed_action
        if action is None:
            return {"status": "error", "message": "No authorized action to execute"}
        self.task.status = AgentStatus.EXECUTING
        self.task.add_audit("execute_start", {"action_description": action.get("description", "unknown")})
        self.task_state.transition_to(TaskState.EXECUTING, "Execution started")

        # Phase 5 real restricted execution (not autonomous) — only when mock disabled
        if mock_only or (self.task.mock_only is not False and mock_only is not False):
            # If mock_only is explicitly False and framework config allows real execution, use real
            pass  # Continue to real execution check below
        else:
            # Real execution: must have authorization and security checks
            if not self.task.authorized_action or not self.task.proposed_action:
                result = {
                    "executed": False,
                    "executed_action": action,
                    "mock_execution_note": "No authorization found; execution blocked.",
                    "permission_level": self.task.permission_level,
                    "iteration": self.iteration,
                }
                self.audit.log("execute_blocked", {"reason": "No authorization", "action": action.get("description", "unknown")})
                self.task.result = result
                self.task.add_audit("execute_complete", {"mock_only": True, "result_summary": "Blocked (no authorization)"})
                self.task.status = AgentStatus.EXECUTED
                return result

        # Real restricted execution (Phase 5)
        if not mock_only and not self.task.mock_only and REAL_FILE_TOOLS_AVAILABLE and self.real_file_tools is not None:
            # Check resource limits before execution
            if not self.resource_limits.is_within_limits():
                result = {
                    "executed": False,
                    "executed_action": action,
                    "status": "timeout_or_limit",
                    "message": "Agent loop exceeded time or iteration limit.",
                    "permission_level": self.task.permission_level,
                    "iteration": self.iteration,
                    "mock_execution_note": None,
                }
                self.task.result = result
                self.task.add_audit("execute_blocked", {"reason": "Resource limit exceeded", "action": action.get("description", "unknown")})
                self.task.status = AgentStatus.TIMEOUT if (time.time() - self.start_time) >= self.task.timeout_seconds else AgentStatus.STOPPED
                return result

            # Propose action must have a real tool call
            action_description = action.get("description", "")
            details = action.get("details", {})
            # Real execution through real_file_tools for supported operations
            executed_result = None
            if "read_file" in action_description or (isinstance(details, dict) and details.get("command") == "read_file"):
                path = details.get("path", ".")
                executed_result = self.real_file_tools.read_file(path)
            elif "list_dir" in action_description or (isinstance(details, dict) and details.get("command") == "list_directory"):
                path = details.get("path", ".")
                executed_result = self.real_file_tools.list_directory(path)
            elif "search" in action_description or (isinstance(details, dict) and details.get("command") == "search_files"):
                workspace = details.get("workspace", ".")
                pattern = details.get("pattern", "")
                executed_result = self.real_file_tools.search_files(workspace, pattern)
            elif "create_file" in action_description or (isinstance(details, dict) and details.get("command") == "create_file"):
                path = details.get("path", "")
                content = details.get("content", "")
                # Approval required for create (high-impact workspace write)
                approval_granted = self.permissions.is_tool_allowed("create_file", self.context) and self.approval_system.is_approved(action.get("approval_id", "create_default"))
                executed_result = self.real_file_tools.create_file(path, content, requires_approval=not approval_granted)
            elif "edit_file" in action_description or (isinstance(details, dict) and details.get("command") == "edit_file"):
                path = details.get("path", "")
                old_text = details.get("old_text", "")
                new_text = details.get("new_text", "")
                approval_granted = self.permissions.is_tool_allowed("edit_file", self.context) and self.approval_system.is_approved(action.get("approval_id", "edit_default"))
                executed_result = self.real_file_tools.edit_file(path, old_text, new_text, requires_approval=not approval_granted)
            else:
                # Unsupported real action: return blocked
                executed_result = {
                    "executed": False,
                    "status": "unsupported",
                    "message": f"Real execution not supported for action: {action_description}",
                    "allowed": False,
                }

            # Build result from real execution or mock
            if executed_result is not None:
                # If real execution succeeded and result has real data
                is_real_result = executed_result.get("status") == "success" or executed_result.get("content") is not None
                result = {
                    "executed": is_real_result,
                    "executed_action": action,
                    "execution_result": executed_result,
                    "mock_execution_note": None,
                    "permission_level": self.task.permission_level,
                    "iteration": self.iteration,
                    "real_execution": is_real_result,
                }
                self.task.executed_action = action
                self.task.result = result
                self.audit.log("execute_complete", {
                    "real_execution": is_real_result,
                    "result_summary": executed_result.get("status", "unknown"),
                    "permission_level": self.task.permission_level,
                    "audit_entries_before": len(self.task.audit_log),
                })
            else:
                # Fall back to mock for unsupported actions
                result = {
                    "executed": False,
                    "executed_action": action,
                    "mock_execution_note": "Phase 5 real restricted execution: action not supported by real tool layer; blocked.",
                    "permission_level": self.task.permission_level,
                    "iteration": self.iteration,
                    "real_execution": False,
                }
                self.audit.log("execute_complete", {"mock_only": True, "result_summary": "Mock (unsupported real action)"})
            self.task.status = AgentStatus.EXECUTED
            return result
        else:
            # Mock-only execution (default for Phase 3 framework verification; Phase 5 uses real when mock_only=False)
            result = {
                "executed": False,
                "executed_action": action,
                "mock_execution_note": "Phase 5: mock execution (AGENT_MOCK_ONLY may be False but no authorization for real execution; real restricted execution requires authorization and supported action).",
                "permission_level": self.task.permission_level,
                "iteration": self.iteration,
            }
            self.task.result = result
            self.task.add_audit("execute_complete", {"mock_only": mock_only, "result_summary": "Mock execution (Phase 3/5 framework)"})
            self.task.status = AgentStatus.EXECUTED
            return result

    def verify_result(self, expected_result_description: Optional[str] = None) -> Dict[str, Any]:
        if self.task.result is None:
            return {"status": "verification_failed", "reason": "No execution result to verify"}
        events = [e["event"] for e in self.task.audit_log]
        required_sequence = ["propose_action", "authorize_granted", "execute_start", "execute_complete"]
        missing = [e for e in required_sequence if e not in events]
        # Phase 5 real verification: check whether result indicates actual execution
        result_data = self.task.result or {}
        real_execution_occurred = result_data.get("real_execution", False)
        real_result_available = result_data.get("execution_result") is not None and isinstance(result_data.get("execution_result"), dict)
        execution_status = result_data.get("execution_result", {}).get("status") if isinstance(result_data.get("execution_result"), dict) else None
        real_success = execution_status == "success" if execution_status else False
        # Verify that if real execution was claimed, audit shows it and result is real (not mock-only with fake claim)
        mock_only_claimed = result_data.get("mock_execution_note") is not None
        verified_real = False
        if real_execution_occurred:
            verified_real = (
                not mock_only_claimed
                and real_result_available
                and len(events) >= len(required_sequence)
            )
        # If mock-only, verify is true if sequence complete and safeguards intact
        verification = {
            "verified": (len(missing) == 0) and ((verified_real) or (not real_execution_occurred and self.task.status == AgentStatus.EXECUTED)),
            "missing_events": missing,
            "audit_entries": len(self.task.audit_log),
            "iteration_at_completion": self.iteration,
            "expected_result_description": expected_result_description,
            "verified_result": {
                "execution_was_real": verified_real and real_execution_occurred,
                "execution_was_mock_only": mock_only_claimed,
                "audit_complete": len(missing) == 0,
                "safeguards_intact": len(missing) == 0,
                "real_success": real_success,
                "execution_status": execution_status,
                "real_execution_occurred": real_execution_occurred,
                "result_data_keys": list(result_data.keys()) if isinstance(result_data, dict) else [],
            },
        }
        self.task.verified_result = verification["verified_result"]
        self.task.status = AgentStatus.VERIFIED if verification["verified"] else AgentStatus.FAILED
        self.task.add_audit("verify_result", verification)
        final_state = TaskState.COMPLETED if verification["verified"] else TaskState.FAILED
        self.task_state.transition_to(final_state, f"Verification: verified={verification['verified']}")
        self.task.multi_step_state = self.task_state.current_state.value
        self.task.state_history = [e["to_state"] for e in self.task_state.states_history]
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
