# Agent Framework — Security Prerequisites Before Phase 4

Phase 3 framework defines interfaces and structures. Before any autonomous execution is enabled, Phase 4 must implement the following controls.

## Phase 4 Status: IMPLEMENTED (Enforced in Code)

All 9 prerequisites from Phase 3 have been implemented as real security controls:

1. **Workspace Boundaries Enforcement** (`agent/core/workspace_sandbox.py`): `AgentContext.workspace_boundaries` enforced by `WorkspaceSandbox.resolve_path()`. Canonical path resolution rejects paths outside permitted subpaths (`.` too broad; must be restricted to approved directories: `ml/`, `tests/`, `datasets/`, etc.).

2. **Path Traversal Protection** (`agent/core/workspace_sandbox.py`): Full canonical path resolution with `os.path.abspath()` and `pathlib.Path.resolve()`. Any proposed file path that resolves outside `workspace_path` is rejected before authorization. `..` traversal blocked.

3. **Command Restrictions** (`agent/core/terminal_security.py`, `agent/core/file_permissions.py`): `AgentContext.allowed_commands` strictly enforced by `TerminalCommandEnforcer`. Command allowlisting is non-bypassable (no `_mock` bypass for real commands). Agent cannot modify allowed list (`allowed_commands` not writable by agent framework design).

4. **Secret Redaction** (`agent/core/secret_redaction.py`): `AgentContext.secret_patterns` (`password`, `token`, `secret`, `key`, `credential`, `auth`) applied to audit logs and output. `redact_dict()` replaces secret key values with `[REDACTED]`. `.env` and secret-bearing files excluded from agent access by default (`SecretRedactor.secret_files`).

5. **Audit Integrity** (`agent/core/audit_crypto.py`): `AuditLogger.verify_integrity()` implements cryptographic hash chain (`previous_hash` + `entry_hash`). Chain breaks detectable (`chain_valid`, `broken_at`). Audit writer must run as separate process/user for full isolation (advisory; process-level isolation requires OS-level enforcement beyond this phase).

6. **High-Impact Action Approval** (`agent/core/approval_system.py`): `PermissionEnforcer.allow_with_approval()` now backed by `ApprovalSystem` with real approval mechanism (`approve_action()` requires `approved_by: str`, `note`). `elevated` commands (`delete_file`, `run_shell`, `deploy`) never execute without explicit authorization. Agent cannot self-approve (`approve_action()` requires external user; `is_approved()` checks external state).

7. **Timeout and Enforcement** (`agent/core/resource_limits.py`, `agent/core/loop.py`): `AgentTask.timeout_seconds` enforced by `ResourceLimits.is_within_time_limit()`; `AgentLoop.is_within_limits()` enforces both iterations and timeout. `TerminalCommandEnforcer` enforces hard termination (`process.kill()`) when timeout exceeded. `AgentContext.max_output_size_bytes` enforced (`ResourceLimits.check_output_size()`); output truncated with `[TRUNCATED]`.

8. **Prompt Injection Defense** (`agent/core/prompt_injection.py`): Untrusted file/tool output treated as untrusted data (not privileged instructions). `PromptInjectionFilter.detect_injection_attempts()` detects hidden instructions (`ignore previous instructions`, `disable safeguards`, `modify your own config`, etc.). `sanitize_for_model_input()` adds `[UNTRUSTED_EXTERNAL_CONTENT_BEGIN/END]` labels and neutralizes markers. Tests verify malicious file instructions cannot override permission policy (`test_malicious_file_content_cannot_override_policy`).

9. **Agent Safeguard Protection** (`agent/core/safeguard_protection.py`): Agent cannot modify `AGENT_AUTONOMOUS_EXECUTION`, `AGENT_MOCK_ONLY`, `AGENT_ENABLED`, `AGENT_PERMISSION_LEVEL`, or audit/security configuration. `SafeguardProtection.check_write_permission()` blocks writes to protected files (`agent/core/config.py`, `permission.py`, etc.). Read-only advisory provided for OS-level enforcement.

---

## Phase 4 Verification (Actual Commands)

```bash
# Confirm framework flags
PYTHONPATH="." python -c "from agent.core.config import AGENT_ENABLED, AGENT_AUTONOMOUS_EXECUTION, AGENT_MOCK_ONLY; print(AGENT_ENABLED, AGENT_AUTONOMOUS_EXECUTION, AGENT_MOCK_ONLY)"
# -> True False True (autonomous execution disabled; mock-only active; framework enabled)

# Confirm workspace sandbox enforces subpaths
PYTHONPATH="." python -c "
from agent.core.workspace_sandbox import WorkspaceSandbox
sandbox = WorkspaceSandbox(workspace_roots=['.'], allowed_subpaths=['tests/'])
print('tests/test_agent.py:', sandbox.resolve_path('tests/test_agent.py'))
print('agent/core/config.py:', sandbox.resolve_path('agent/core/config.py'))
"
# -> tests/test_agent.py allowed; agent/core/config.py blocked (not in allowed subpaths)

# Confirm terminal security allowlist
PYTHONPATH="." python -c "
from agent.core.terminal_security import ALLOWED_COMMANDS
print('Allowed commands:', list(ALLOWED_COMMANDS.keys()))
"
# -> ['python', 'pytest', 'cat', 'ls', 'pwd', 'echo', 'grep', 'head', 'git']

# Confirm approval mechanism requires external user
PYTHONPATH="." python -c "
from agent.core.approval_system import ApprovalSystem
approval = ApprovalSystem()
approval.request_approval('test_1', 'delete', 'elevated', 'test')
print('Self-approved?', approval.is_approved('test_1'))
"
# -> False (agent cannot approve its own action)

# Confirm audit chain verification
PYTHONPATH="." python -c "
from agent.core.audit_crypto import CryptographicAuditLogger
import tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as td:
    logger = CryptographicAuditLogger(log_path=Path(td)/'audit.jsonl')
    logger.log('test', {'step': 1})
    print('Chain:', logger.verify_integrity()['chain_valid'])
"
# -> True (audit chain verified)
```
