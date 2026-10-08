# API — Veyra Labs

Base URL (local): `http://localhost:8000`

## Endpoints

- `GET /api/health` — Service status
- `GET /api/system` — Hardware / environment info
- `GET /api/models` — Available checkpoints
- `GET /api/checkpoints` — Checkpoint list with metadata
- `GET /api/training/config` — Active training settings
- `POST /api/training/prepare-data` — Not implemented in Phase 1 (use CLI scripts directly)
- `POST /api/training/start` — Not implemented in Phase 1
- `GET /api/training/{run_id}` — Training run info
- `POST /api/training/{run_id}/cancel` — Not implemented in Phase 1
- `GET /api/training/{run_id}/logs` — Training log lines
- `POST /api/generate` — Text generation with checkpoint
- `POST /api/evaluate` — Run evaluation suite on latest checkpoint
- `GET /api/evaluations` — Stored evaluation results

Request/response formats are Pydantic-validated.
