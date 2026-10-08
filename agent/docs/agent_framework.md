# Agent Framework — Phase 3 Architecture (No Broad Autonomy)

## What this framework does (Phase 3)
- Defines agent state/task model (`AgentTask`).
- Defines agent loop (`AgentLoop`) with limits and timeouts.
- Defines tool interface (`ToolSchema`, `ToolCall`) with strict input/output schemas.
- Defines tool registry (`ToolRegistry`) that requires explicit registration.
- Defines permission checks (`PermissionEnforcer`) with configurable levels.
- Defines audit logging (`AuditLogger`) that records all events.
- Defines validation (`ActionValidator`) for proposed actions and results.
- Provides mock/stub tools (`mock_tools.py`) clearly labeled (`is_mock=True`).

## What is DISABLED (required for Phase 4 security)
- `AGENT_AUTONOMOUS_EXECUTION` is `False` by default (`agent/core/config.py`).
- Real file read/edit/test/shell execution is NOT performed by the framework loop (`AgentLoop.execute_action()` returns mock results only).
- Broad workspace access is NOT granted (`AgentContext.workspace_boundaries` must be explicitly set in Phase 4).
- No command allowlist is enforced by the loop itself (Phase 4 must add full command restriction before enabling terminal execution).
- Audit log does NOT have cryptographic integrity verification yet (`audit.verify_integrity()` reports this clearly and requires Phase 4 implementation).

## Why mock/stub tools are required in Phase 3
The framework architecture must be tested independently of real autonomous execution. All mock/stub implementations (`MOCK_READ_FILE`, `MOCK_LIST_DIR`, etc.) have `is_mock=True`. They must never be presented as real file/command execution. Real execution requires Phase 4 security controls (workspace boundaries, path traversal protection, command allowlisting, timeouts, audit integrity, safe defaults, prompt injection defense).

## How the agent loop works (design only — no real autonomous execution in Phase 3)
1. `AgentLoop.step()` proposes an action (`AgentStatus.PROPOSED`).
2. Authorization is required (`AgentStatus.AUTHORIZED`) — Phase 4 must enforce this.
3. Execution (`AgentStatus.EXECUTED`) in Phase 3 is mock-only; `AgentLoop.execute_action()` explicitly records `mock_execution_note`.
4. Verification (`AgentStatus.VERIFIED`) checks audit continuity and confirms no real execution occurred.
5. The loop stops when limits are reached (`AgentStatus.TIMEOUT` or `AgentStatus.STOPPED`).

## Security prerequisites before enabling real autonomous execution (Phase 4)
- Workspace boundaries (`AgentContext.workspace_boundaries`) must restrict file access.
- Path traversal protection (`ActionValidator.check_path_traversal()`) must be fully enforced.
- Command allowlisting (`AgentContext.allowed_commands`) must restrict terminal commands.
- Secret redaction (`AgentContext.secret_patterns`) must be fully applied.
- Audit integrity (`AuditLogger.verify_integrity()`) must implement cryptographic verification (hash chain / signatures).
- Agent must not be able to disable its own safeguards (`AGENT_AUTONOMOUS_EXECUTION` protected).
- Prompt injection defense for untrusted file content and tool output must be implemented.
- High-impact actions must require explicit human approval (`PermissionEnforcer.allow_with_approval()`).

## Configuration (configurable names preserved from `.env.example`)
- `VEYRA_COMPANY_NAME`: company name (`Veyra Labs` default)
- `VEYRA_DEFAULT_MODEL`: model name (`Veyra Prime` default)
- `VEYRA_CODING_MODEL`: coding model name (`Veyra Code`)
- `VEYRA_IMAGE_MODEL`: image model (`Veyra Vision`)
- `VEYRA_VIDEO_MODEL`: video model (`Veyra Motion`)
- `VEYRA_AUDIO_MODEL`: audio model (`Veyra Voice`)
- `VEYRA_RESEARCH_AGENT`: research agent (`Veyra Research`)
- `VEYRA_AGENT_ENABLED`: framework enabled flag (`false` by default; framework exists but autonomous execution disabled)
- `VEYRA_AGENT_MAX_ITERATIONS`: loop limit (`10`)
- `VEYRA_AGENT_TIMEOUT_SECONDS`: loop timeout (`300`)
- `VEYRA_AGENT_PERMISSION_LEVEL`: `restricted` (Phase 4 configurable)
