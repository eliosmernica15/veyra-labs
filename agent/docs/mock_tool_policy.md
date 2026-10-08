# Agent Framework — Mock/Stub Policy (Phase 3)

## Why mocks/stubs are required in Phase 3
The agent framework architecture (loop, registry, permissions, audit, validation) must be tested independently of real autonomous execution. Real autonomous file/command execution requires Phase 4 security controls. All mock/stub implementations must be clearly labeled (`is_mock=True`) so no confusion exists about their capabilities.

## Mock Tool Definitions (`agent/core/mock_tools.py`)
- `MOCK_READ_FILE`: `is_mock=True`, `permission_required="restricted"`, description explicitly says "MOCK/STUB: ... Does NOT perform real file access in Phase 3."
- `MOCK_LIST_DIR`: same.
- `MOCK_SEARCH_PROJECT`: same.
- `MOCK_RUN_TEST`: same.
- `MOCK_EDIT_FILE`: same, `permission_required="standard"`.

## Execution Behavior
- `AgentLoop.execute_action()` always returns `mock_execution_note`.
- `AgentLoop.verify_result()` checks `mock_execution_note` and confirms `no_real_execution_performed`.
- `AgentTask.audit_log` records every proposal, authorization, execution, and verification event.

## What must change in Phase 4
Before enabling real execution:
1. Replace mock/stub tool implementations with real, restricted implementations.
2. Ensure `AgentLoop.execute_action()` calls real (restricted) tool implementations instead of returning mock results.
3. Enforce workspace boundaries (`AgentContext.workspace_boundaries`) in every real file/command operation.
4. Ensure `AgentLoop.verify_result()` validates actual results (not mock results).
5. Confirm audit integrity (cryptographic verification) is active.
6. Confirm agent cannot disable its own safeguards (`AGENT_AUTONOMOUS_EXECUTION` protected).

## What must NOT change
- Mock/stub definitions (`ALL_MOCK_TOOLS`) must remain as clearly labeled mock implementations, not presented as real execution.
- If mock/stub tools are removed in Phase 4, they must be replaced by equivalent real restricted implementations, not deleted without replacement.
- All `is_mock=True` labels must remain accurate (True = mock/stub; False = real restricted execution).
