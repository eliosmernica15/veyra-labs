# Agent Framework Status — Phase 4 (What is Enabled / Disabled)

Phase 4 security/sandboxing is implemented. The following capabilities have been added or changed:

---

## Enabled in Phase 4 (Real Enforced Controls)

- `WorkspaceSandbox` — strict workspace boundary enforcement with path traversal protection, absolute path restriction, subpath enforcement, symlink detection.
- `FilePermissionEnforcer` — explicit file operation permissions (`read_file`, `create_file`, `modify_file`, `delete_file`, `rename_file`, `list_dir`) enforced by permission level (`restricted`/`standard`/`elevated`) and workspace sandbox.
- `TerminalCommandEnforcer` — controlled command execution with allowlist (`python`, `pytest`, `cat`, `ls`, `pwd`, `echo`, `grep`, `head`, `git`), executable validation, argument validation, workspace restriction, timeout enforcement, output limits, audit logging.
- `ApprovalSystem` — real approval mechanism (`approve_action()` requires `approved_by`). Agent cannot self-approve. Expired approvals auto-denied.
- `CryptographicAuditLogger` — audit chain (`previous_hash` + `entry_hash`) with `verify_integrity()` reporting `chain_valid`. Audit file append-only.
- `PromptInjectionFilter` — untrusted file/tool output filtered before model input; hidden instruction markers (`<!-- hidden instruction`, `[hidden: `) detected and neutralized. File content treated as untrusted data.
- `SafeguardProtection` — agent framework security files protected from agent modification (`agent/core/config.py`, `permission.py`, etc.). Agent cannot modify its own safeguards.
- `SecretRedactor` — secret patterns (`password`, `token`, `secret`, `key`, `credential`, `auth`) redacted from audit/output; `.env` and secret-bearing files excluded from agent access.
- `ResourceLimits` — max iterations, per-tool timeout, overall timeout, max output bytes, file size limits, cancellation support.
- `ActionValidator` — enhanced with full workspace/subpath enforcement; validates actions against schemas and workspace boundaries.

---

## Still Disabled / Not Enabled (Intentionally)

- `AgentLoop.execute_action()` — returns `mock_execution_note` only; **real autonomous file/command execution remains disabled** (`AGENT_AUTONOMOUS_EXECUTION = False`). Real restricted execution requires Phase 5+ integration (replacing mock/stub with restricted real implementations under full security enforcement).
- `AgentLoop.verify_result()` — verifies mock results; real verification of actual tool results requires real execution layer.
- Real unrestricted workspace/file access: workspace restricted to approved subpaths (`.` too broad for autonomous execution; must be restricted to `datasets/`, `ml/`, `tests/`, etc.).
- Unrestricted command execution: only allowlisted commands permitted (`ALLOWED_COMMANDS`). Dangerous commands blocked by policy.
- Cryptographic audit writer as separate user/process: advisory (`agent/docs/security_prerequisites.md`); OS-level isolation not enforced locally.
- Full process-level isolation for autonomous execution: requires separate OS user/container; advisory only.
- Real external authorization service: approval mechanism requires user input; no external authorization API integrated.
- Dataset expansion to larger public source: deferred until after Phase 4 security confirmed.
- Broad autonomous coding/research/development capabilities: agent framework architecture only; no autonomous coding agent enabled.

---

## Framework Flags (Verified)

```python
AGENT_ENABLED = True        # Framework exists
AGENT_AUTONOMOUS_EXECUTION = False   # Must remain False
AGENT_MOCK_ONLY = True      # Mock/stub execution only
AGENT_AUDIT_ENABLED = True
AGENT_MAX_ITERATIONS = 10
AGENT_TIMEOUT_SECONDS = 300
AGENT_PERMISSION_LEVEL = "restricted"
```

No unrestricted shell or filesystem autonomy exists. Mock/stub labels remain accurate (`is_mock=True`). Security prerequisites documented. Phase 4 security implemented in code.
