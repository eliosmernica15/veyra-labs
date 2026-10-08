# Agent Framework — Security Prerequisites Before Phase 4

Phase 3 framework defines interfaces and structures. Before any autonomous execution is enabled, Phase 4 must implement the following controls.

## Workspace Boundaries
- `AgentContext.workspace_boundaries` must be enforced by `ActionValidator.check_path_traversal()`.
- No file access outside permitted subpaths (`.` is too broad for autonomous execution; must be restricted to approved directories).

## Path Traversal Protection
- `ActionValidator.check_path_traversal()` is a stub interface. Phase 4 must implement full canonical path resolution and boundary enforcement.
- Any proposed file path that resolves outside `workspace_path` must be rejected before authorization.

## Command Restrictions
- `AgentContext.allowed_commands` must be strictly enforced. Phase 3 framework does not enforce this (loop executes mock results only).
- Command allowlisting must be non-bypassable by the agent (agent cannot modify its own allowed list).

## Secret Redaction
- `AgentContext.secret_patterns` defines patterns (`password`, `token`, `secret`, `key`).
- Phase 4 must enforce redaction in audit logs and output before any result reaches external interfaces.
- Audit log must NEVER contain unredacted secrets.

## Audit Integrity
- `AuditLogger.verify_integrity()` reports clearly: `"Phase 4 must implement cryptographic verification (hash chain / signature)"`.
- Phase 4 must add a hash chain or digital signature to audit entries so they cannot be deleted or altered.
- Agent must not have write access to audit file during autonomous execution (separate process/user for audit writer).

## High-Impact Action Approval
- `PermissionEnforcer.allow_with_approval()` defines the mechanism. Phase 4 must implement a real approval gate (e.g., user confirmation, time delay, or external authorization service) before any `elevated` or `requires_approval_for` tool call executes.
- `elevated` commands (e.g., `delete_file`, `run_shell`, `deploy`) must never execute without explicit authorization.

## Timeouts and Output Limits
- `AgentTask.timeout_seconds` (300 default) and `AgentLoop.is_within_limits()` enforce limits in framework.
- Phase 4 must implement hard termination (not graceful stop) when timeout is exceeded.
- `AgentContext.max_output_size_bytes` (1MB default for restricted, 10MB for elevated) must be enforced before any result is accepted.

## Safe Defaults
- Default `permission_level` is `restricted` (`agent/core/config.py`).
- Default `AGENT_AUTONOMOUS_EXECUTION` is `False`.
- Default `AGENT_MOCK_ONLY` is `True` (Phase 3 framework testing only).

## Prompt Injection Defense
- Untrusted file content and tool output must be treated as untrusted data (not privileged instructions).
- Phase 4 must implement prompt injection filtering (e.g., sanitize input before passing to model prompts; verify no hidden instructions in file content or command output).
- Agent must not allow file content or tool output to modify its own instructions, permissions, or safeguards.

## Agent Safeguard Protection
- Agent must not be able to modify or disable its own safeguards (`AGENT_AUTONOMOUS_EXECUTION`, `AGENT_MOCK_ONLY`, `permission_level`, `audit_enabled`).
- Phase 4 must enforce this at the process/file-system level (read-only access to agent framework code/config during execution).
