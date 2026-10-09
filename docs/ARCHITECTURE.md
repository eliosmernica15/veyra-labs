# Phase 0 — Updated Architecture (Python-First, Single Language)

## Change from original plan
- **Previous:** React + Vite frontend (`apps/studio`), TypeScript CLI (`apps/cli`), shared TypeScript packages (`packages/shared-types`).
- **Updated:** Streamlit for Veyra Studio (Python-only), Python CLI, pure Python packages. No TypeScript, React, or Node.js for application logic.

## Confirmed stack
- Python 3.14.7 (primary and only application programming language)
- PyTorch for model/inference
- FastAPI + Uvicorn for backend API
- Streamlit for Veyra Studio interface
- SQLite for persistence
- Tokenizers (`tokenizers` 0.22.2 already installed)
- `pytest` for tests
- `pathlib` / `.env` for configuration
- **Phase 4 Security Architecture** (implemented in code): `agent/core/workspace_sandbox.py` (workspace isolation, path traversal protection), `agent/core/file_permissions.py` (explicit file operation permissions by level), `agent/core/terminal_security.py` (controlled command allowlist with executable/argument validation, timeout, output limits, audit), `agent/core/approval_system.py` (real approval gate with external authorization, auto-deny on expiry), `agent/core/audit_crypto.py` (cryptographic hash chain for audit integrity), `agent/core/prompt_injection.py` (filter/sanitize untrusted file/tool output before model input), `agent/core/safeguard_protection.py` (protect agent framework config/code from agent modification), `agent/core/secret_redaction.py` (redact secrets from audit/output; exclude `.env` from agent access), `agent/core/resource_limits.py` (max iterations, per-tool timeout, overall timeout, output/file size limits, cancellation support)
- **No InsForge** (prohibited). **No TypeScript/React/Node** (not in architecture). **No Docker/Kubernetes/cloud infrastructure** (not needed for Phase 4 local security architecture).
