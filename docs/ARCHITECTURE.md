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
