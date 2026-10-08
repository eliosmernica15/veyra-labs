# Security — Veyra Labs (Phase 1)

## Boundaries
- Workspace: `datasets/`, `ml/`, `checkpoints/`, `runs/`
- No arbitrary filesystem access through API endpoints.
- No arbitrary command execution through endpoints.
- Secret redaction: backend logs must not expose API keys or tokens (none configured yet).

## Permissions
- Training operates on pre-approved dataset files.
- Checkpoints are saved to `checkpoints/`; no external uploads allowed.
- Inference loads only local `.pt` checkpoints validated by `load_checkpoint()`.

## Safe defaults
- Default `device` is CPU (no CUDA assumption).
- No remote model download or hidden third-party dependency.

Note: Full sandboxing (command allowlists, workspace isolation, audit trail) is slated for Phase 4 and is not yet implemented.
