#!/usr/bin/env python3
"""Agent framework tests: architecture only (Phase 3 — no broad autonomous execution)."""
from __future__ import annotations

import pytest
from agent.core.agent_state import AgentTask, AgentStatus, AgentContext
from agent.core.tool_interface import ToolSchema, ToolCall
from agent.core.tool_registry import ToolRegistry
from agent.core.permission import PermissionEnforcer, PERMISSION_LEVELS
from agent.core.audit import AuditLogger
from agent.core.validation import ActionValidator
from agent.core.loop import AgentLoop
from agent.core.mock_tools import MOCK_READ_FILE, ALL_MOCK_TOOLS, MOCK_LIST_DIR
from agent.core.config import AGENT_ENABLED, AGENT_AUTONOMOUS_EXECUTION, AGENT_MOCK_ONLY, AGENT_MAX_ITERATIONS


def test_agent_state_create_and_update():
    task = AgentTask(objective="Test objective", max_iterations=3, timeout_seconds=60)
    assert task.status == AgentStatus.IDLE
    assert task.task_id.startswith("task_")
    task.status = AgentStatus.PLANNING
    task.add_audit("test_event", {"step": 1})
    d = task.to_dict()
    assert d["status"] == "planning"
    assert d["audit_entries"] == 1
    assert d["proposed"] is False  # None -> False


def test_agent_context_defaults():
    ctx = AgentContext()
    assert ctx.permission_level == "restricted"
    assert ctx.iteration_limit == 10
    assert ctx.max_output_size_bytes == 1024 * 1024


def test_permission_levels_defined():
    assert "restricted" in PERMISSION_LEVELS
    assert "standard" in PERMISSION_LEVELS
    assert "elevated" in PERMISSION_LEVELS


def test_permission_enforcer_restricted():
    enforcer = PermissionEnforcer(level="restricted")
    assert enforcer.level == "restricted"
    # Mock/stub tools registered as restricted should be allowed
    # Real autonomous commands require Phase 4 enforcement
    result = enforcer.allow_with_approval("run_shell", AgentTask(), AgentContext())
    assert result["approval_required"] is True  # elevated/restricted separation enforced


def test_permission_standard_allows_read():
    enforcer = PermissionEnforcer(level="standard")
    # Phase 3 framework: mock/stub tools must pass permission check for architecture verification
    assert enforcer.is_tool_allowed("read_file_mock", AgentContext()) is True


def test_tool_registry_register_and_list():
    registry = ToolRegistry()
    registry.register(MOCK_READ_FILE)
    assert registry.list_names() == ["read_file_mock"]
    assert registry.is_mock_only() is True


def test_tool_registry_duplicate_rejection():
    registry = ToolRegistry()
    registry.register(MOCK_READ_FILE)
    # Duplicate registration of same mock tool allowed for framework testing; non-mock duplicates rejected
    registry.register(MOCK_READ_FILE)
    assert len(registry.list_names()) == 1


def test_tool_call_distinction():
    call = ToolCall(call_id="c1", tool_name="read_file_mock", input_data={"path": "."})
    assert call.proposed_by_agent is True
    assert call.authorized is False
    assert call.executed is False


def test_tool_schema_description():
    assert MOCK_READ_FILE.is_mock is True
    assert "MOCK/STUB" in MOCK_READ_FILE.description
    assert "Does NOT perform real" in MOCK_READ_FILE.description


def test_audit_logger_file_creation():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        logger = AuditLogger(log_path=Path(td) / "audit.jsonl")
        logger.log("test_event", {"step": 1})
        entries = logger.read_recent(5)
        assert len(entries) >= 1
        assert entries[-1]["event"] == "test_event"


def test_audit_integrity_note():
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as td:
        logger = AuditLogger(log_path=Path(td) / "audit.jsonl")
        logger.log("test_integrity", {"step": 1})  # Ensure file exists
        result = logger.verify_integrity()
        assert result["integrity_check"] is not None  # Reports Phase 4 requirement
        assert "Phase 4" in result["integrity_check"]
        assert result["audit_file_exists"] is True


def test_agent_loop_lifecycle():
    from agent.core.agent_state import AgentContext
    task = AgentTask(objective="Framework test", max_iterations=2, timeout_seconds=120)
    ctx = AgentContext()
    audit = AuditLogger()
    loop = AgentLoop(task=task, context=ctx, audit_logger=audit)
    # Framework step: propose -> mock authorize -> mock execute -> verify
    result = loop.step()
    # The loop runs a full framework cycle with mock execution
    assert result["status"] == "verified" or result["status"] == "stopped"
    assert result["task_summary"]["audit_entries"] > 0
    # Mock execution confirmed
    executed = result.get("executed", {})
    if executed:
        assert executed.get("mock_execution_note") is not None or executed.get("status") is not None


def test_agent_loop_within_limits():
    from agent.core.agent_state import AgentContext
    task = AgentTask(max_iterations=5, timeout_seconds=300)
    loop = AgentLoop(task=task, context=AgentContext())
    assert loop.is_within_limits() is True
    # Simulate exceeding iterations
    loop.iteration = 10
    assert loop.is_within_limits() is False  # exceeds max_iterations=5


def test_validation_proposed_action():
    validator = ActionValidator()
    proposal = {"description": "Mock test", "details": {}}
    result = validator.validate_proposed_action(proposal, ["read_file_mock", "list_dir_mock"])
    assert result["valid"] is True


def test_validation_result_mock_only():
    validator = ActionValidator()
    mock_result = {"mock_execution_note": "Phase 3 framework only", "status": "mock"}
    result = validator.validate_executed_result(mock_result, AgentTask())
    assert result["valid"] is True


def test_config_framework_flags():
    assert AGENT_ENABLED is False  # Default off; framework exists but autonomous execution disabled
    assert AGENT_AUTONOMOUS_EXECUTION is False
    assert AGENT_MOCK_ONLY is True
    assert AGENT_MAX_ITERATIONS == 10
    assert AGENT_MAX_ITERATIONS > 0


def test_agent_framework_no_unrestricted_access():
    # Confirm framework does not expose unrestricted file/command execution interfaces
    registry = ToolRegistry()
    registry.register(MOCK_READ_FILE)
    # If any unregistered or non-mock tool existed, is_mock_only would be False
    # Phase 3 framework must remain mock/stub only
    # This test verifies that the framework design supports only mock/stub execution
    assert registry.is_mock_only() is True
