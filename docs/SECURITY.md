# Security — Veyra Labs (Phase 4)

## Phase 4 Security Architecture Implemented

Phase 4 implements enforced security controls in code, not only documentation.
Autonomous execution remains disabled (`AGENT_AUTONOMOUS_EXECUTION=False`).
No broad autonomous agent execution enabled.

---

## 1. Workspace Sandbox (`agent/core/workspace_sandbox.py`)

- **Explicit workspace roots**: `.` (current directory) with configurable roots.
- **Path normalization**: All file paths resolved to canonical absolute paths before access.
- **Path traversal prevention**: `resolve_path()` rejects `..` traversal that resolves outside workspace.
- **Absolute path restriction**: Absolute paths (e.g., `/etc/passwd`) blocked unless within workspace.
- **Subpath enforcement**: `allowed_subpaths` (`ml/`, `tests/`, `datasets/`, etc.) enforced independently of workspace root.
- **Symlink detection**: `symlink_detected` reported; symlinks not permitted unless explicitly allowed (`allow_symlinks=False` by default).
- **Configurable through config/environment**: Workspace and allowed subpaths configurable.

---

## 2. File Permissions (`agent/core/file_permissions.py`)

Explicit permissions checked by the tool layer (not by model behavior):

- `read_file`
- `list_dir`
- `create_file`
- `modify_file`
- `delete_file`
- `rename_file`

Permission levels:
- `restricted`: read-only (`read_file`, `list_dir`); no create/modify/delete.
- `standard`: read + create + modify; delete requires approval.
- `elevated`: full access but `delete_file`, `rename_file` require explicit user approval.

**Approval mechanism** (`set_explicit_approval()`): must be set by user/external mechanism, not by the agent itself. High-impact operations (`delete_file`, `rename_file`) never execute without explicit approval.

---

## 3. Terminal Command Security (`agent/core/terminal_security.py`)

Controlled command-execution subsystem with restrictive policy:

- **Allowlist** (`ALLOWED_COMMANDS`): `python`, `pytest`, `cat`, `ls`, `pwd`, `echo`, `grep`, `head`, `git`. No unrestricted shell access.
- **Executable validation**: Only commands in allowlist permitted; unknown executables blocked.
- **Argument validation**: Flags checked against allowed lists; argument counts limited (`max_args`); dangerous argument patterns blocked.
- **Python subcommand restriction**: `python -c` expressions checked for `os.system`, `subprocess.run`, `eval(`, `exec(`, etc.
- **Workspace restriction**: Commands executed with `cwd=self.workspace`.
- **Timeout**: `timeout_seconds` enforced; process killed on timeout (`process.kill()`).
- **Output limits**: `max_output_bytes` enforced; stdout/stderr truncated.
- **Exit code capture**: `exit_code` captured for audit.
- **Audit logging**: Every execution (allowed, blocked, timeout) logged.
- **No simple blacklist**: Security enforced by policy (allowed commands + argument validation + workspace), not by blacklisting strings.

---

## 4. Approval System (`agent/core/approval_system.py`)

- **Explicit permission levels**: `restricted` (safe/read-only), `standard` (workspace-write), `elevated` (high-impact).
- **High-impact approval gate**: `approve_action()` requires external/user authorization (`approved_by: str`). The agent cannot approve its own actions.
- **Expiration**: `approval_timeout_seconds` (default 300); expired approvals auto-denied (`auto_deny_expired()`).
- **Protection from agent modification**: `approval_system.py` does not expose self-approval; `is_approved()` checks external state.

---

## 5. Audit Logging (`agent/core/audit_crypto.py`)

- **Cryptographic hash chain**: Each audit entry includes `previous_hash` (hash of previous entry) and `entry_hash` (hash of current entry content). Chain breaks detectable.
- **Immutable audit entries**: Append-only `.jsonl`; `verify_integrity()` verifies chain continuity.
- **Audit integrity verification**: Reports `chain_valid`, `broken_at`, `last_hash`. No modification or deletion of past entries undetectable.
- **No secrets in audit**: Audit writer must apply `SecretRedactor` before writing.

---

## 6. Prompt Injection Defenses (`agent/core/prompt_injection.py`)

- **Untrusted data treatment**: All file/tool output treated as untrusted; never passes directly to model prompts without filtering.
- **Injection detection**: `PromptInjectionFilter.detect_injection_attempts()` checks for hidden instructions (`ignore previous instructions`, `disable safeguards`, `modify your own config`, etc.).
- **Hidden instruction markers**: `<!-- hidden instruction`, `[hidden:`, etc. detected and neutralized.
- **Sanitization**: `sanitize_for_model_input()` adds `[UNTRUSTED_EXTERNAL_CONTENT_BEGIN/END]` labels; filters injection patterns; neutralizes hidden markers.
- **Policy independence**: File permissions and workspace enforcement do not inspect file content for authorization decisions. Malicious instructions inside files cannot override security policy.
- **Tests demonstrate**: `test_malicious_file_content_cannot_override_policy()` verifies that malicious file instructions do not disable permission enforcement.

---

## 7. Self-Protection / Safeguard Protection (`agent/core/safeguard_protection.py`)

- **Protected files**: `agent/core/config.py`, `permission.py`, `workspace_sandbox.py`, `terminal_security.py`, `approval_system.py`, `secret_redaction.py`, `prompt_injection.py`, `audit_crypto.py`, `.env`, `.env.example`.
- **Write protection check**: `check_write_permission()` returns `allowed: False` for protected paths. Agent must not be able to modify its own security configuration.
- **Config protection advisory**: `protect_config_from_agent_modification()` confirms `AGENT_AUTONOMOUS_EXECUTION` must remain `False`; recommends OS-level read-only enforcement and separate user/process for autonomous execution.
- **No agent modification of safeguards**: `AGENT_AUTONOMOUS_EXECUTION`, `AGENT_MOCK_ONLY`, `AGENT_ENABLED`, `permission_level` protected.

---

## 8. Secret Handling (`agent/core/secret_redaction.py`)

- **Secret patterns**: `password`, `token`, `secret`, `credential`, `api_key`, `auth`, `key`, etc.
- **Secret-bearing files excluded from agent access**: `.env`, `.env.local`, `.env.production`, `.secrets`, `secrets.json`, `credentials.json`, `.netrc`.
- **Redaction applied to audit logs**: `redact_dict()` replaces secret key values with `[REDACTED]`; `redact_text()` removes potential secrets from output.
- **No hardcoded credentials**: `.env.example` must remain free of real secrets.

---

## 9. Resource Limits (`agent/core/resource_limits.py`)

- **Maximum iterations**: `max_iterations` (default 10) enforced by `AgentLoop`.
- **Per-tool timeout**: `timeout_seconds` (default 30) enforced in `TerminalCommandEnforcer` (`process.kill()` on timeout).
- **Overall task timeout**: `timeout_seconds` enforced; `is_within_time_limit()` returns False when exceeded.
- **Maximum output size**: `max_output_bytes` enforced; output truncated with `[TRUNCATED]` note.
- **File size limits**: `max_file_size_bytes` (default 10MB) enforced by `check_file_size()`.
- **Cancellation support**: `ResourceLimits.cancel()`; `is_cancelled()` checked.
- **Subprocess protection**: `TerminalCommandEnforcer.execute()` uses `subprocess.Popen()` with `shell=False`; no uncontrolled spawning.

---

## 10. Real Security Tests (`agent/tests/test_security.py`)

54 security tests covering:
- Workspace boundary enforcement (resolution, traversal, absolute path, symlink, subpath)
- File permissions (read, create denied, approval mechanism, delete requires approval)
- Terminal command security (dangerous blocked, safe allowed, unknown executable blocked)
- Approval system (pending, granted, denied, expired, auto-deny, agent cannot self-approve)
- Audit integrity (log creation, chain verification, tamper detection)
- Prompt injection defense (detection, safe content, hidden markers, sanitization, file untrusted treatment, malicious content cannot override policy)
- Safeguard protection (config protected, protected paths list, advisory)
- Secret redaction (file detection, pattern redaction, dict redaction, audit redaction)
- Resource limits (iteration, time, output size, file size, cancellation)
- Integration (full security flow works together)
- Real control verification (autonomous execution disabled, mock-only active, workspace configurable, permission default restricted)

---

## Intentionally Disabled / Not Enabled in Phase 4

- **Broad autonomous agent execution**: `AGENT_AUTONOMOUS_EXECUTION = False` remains.
- **Real autonomous file/command execution**: `AgentLoop.execute_action()` returns mock results; real restricted execution requires Phase 5+ integration.
- **Cryptographic audit writer as separate process/user**: Documented as required (`agent/docs/security_prerequisites.md`); process-level isolation is advisory, not enforced by code alone.
- **Full process isolation**: OS-level sandboxing (separate user/container) recommended but not implemented locally.
- **Real external authorization service**: Approval mechanism requires external/user input; no external authorization API integrated.
- **Dataset expansion to larger public source**: Defer until after Phase 4 security confirmed.

---

## Phase 4 Verification

```bash
PYTHONPATH="." python -m pytest agent/tests/test_security.py -v
# 54 passed
PYTHONPATH="." python -c "from agent.core.config import AGENT_AUTONOMOUS_EXECUTION; print('Autonomous execution:', AGENT_AUTONOMOUS_EXECUTION)"
# -> False (must remain False)
```
