# Phase 0 — Environment Report

## 1. Environment Summary

| Property | Value |
|---|---|
| OS | Windows 11 Pro 10.0.26300 (win32) |
| Python | 3.14.7 (64-bit, MSC v.1944) |
| Executable | `C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe` |
| Node.js | v24.11.0 |
| npm | 10.2.4 |
| Disk (C:) | 476 GB total, 211 GB free (~56% used) |
| RAM | 16 GB physical (2 × 8 GB), ~13.8 GB reported |
| CPU | AMD Ryzen 7 5700U with Radeon Graphics |
| GPU / CUDA | None detected. No `nvidia-smi`. No CUDA-capable GPU. |

## 2. Existing Dependencies (already installed)

- `fastapi` 0.142.4
- `uvicorn` 0.54.0
- `pydantic` 2.13.5 / `pydantic_core` 2.46.5 / `pydantic-settings` 2.15.0
- `numpy` 2.4.4
- `pytest` 9.0.2
- `tokenizers` 0.22.2
- `huggingface_hub` 1.4.1
- `fastapi-cli` 0.0.24, `fastapi-mail` 1.4.1, `fastapi-sso` 0.23.0

**Not installed:** `torch`, `transformers`, `safetensors`, `huggingface` (the SDK package; `huggingface_hub` is present but not `transformers`).

## 3. What the Machine Can Support

- Small CPU-only PyTorch training. A decoder-only Transformer of ~2M parameters with a modest vocabulary (~4k–8k tokens) and context length of 128–256 can be trained locally on the 16 GB RAM / 8-thread CPU.
- FastAPI backend with SQLite persistence.
- React + Vite frontend.
- Tokenizer training with `tokenizers` library (already installed).
- Checkpoint storage in `checkpoints/` (disk space is adequate; each checkpoint for a 2M-param model is ~8 MB).

## 4. What the Machine Cannot Reasonably Support

- Large-parameter language models (>50M parameters) on CPU in reasonable time.
- CUDA/GPU-accelerated training (no NVIDIA GPU present).
- Very large vocabulary (>50k) with long context (e.g., 4096) without significant memory/time overhead.
- Multi-hour full-scale pretraining experiments; only short smoke tests (a few hundred steps) are practical.
- Distributed/multi-GPU training.

## 5. Recommended Initial Model Configuration (Phase 1)

Given the CPU-only, 16 GB RAM environment:

- **Architecture:** Decoder-only Transformer.
- **Parameters:** ~2M (2,097,152).
- **Layers:** 4
- **Embedding dim:** 128
- **Attention heads:** 4
- **Context length:** 128
- **Vocabulary size:** 4,096 (BPE tokenizer trained from small public-domain text)
- **Batch size:** 4 (CPU-friendly)
- **Max training steps (smoke test):** 50–100
- **Checkpoint interval:** Every 10 steps for smoke testing.
- **Device:** `cpu` (default). If a CUDA-capable device is ever added, the code must detect it and prefer it.

This is an **experimental / smoke-test** configuration. The model will not produce meaningful general conversation or coding. It verifies the pipeline only.

## 6. Constraints

- **No CUDA:** All training and inference will run on CPU. Performance will be slow. A 100-step smoke test on 2M parameters may take 2–10 minutes depending on batch size and sequence length.
- **No persistent GPU memory:** Not applicable.
- **Windows paths:** File-path code must use `pathlib.Path` or `os.path.join` to remain cross-platform.
- **Python 3.14.7** is newer than 3.12; some packages may have compatibility issues. Monitor for warnings.
- **No existing Git repo:** Initialize one before committing.

## 7. Future Capabilities Requiring Additional Hardware

- Training models >50M parameters efficiently.
- Real-time inference for large contexts (>2048 tokens).
- Image-generation (Veyra Vision) — requires GPU + large VRAM.
- Video-generation (Veyra Motion) — requires substantial GPU + dataset infrastructure.
- Audio-generation (Veyra Voice) — can start CPU-only but benefits from GPU for larger experiments.
- Autonomous agent loops with frequent tool calls — mainly CPU-bound, but larger models benefit from GPU.

## 8. Recommended Phase 1 Setup

1. Initialize `torch` installation (`pip install torch`). Confirm CPU-only import.
2. Initialize `transformers` and `safetensors` if needed (optional for first phase; can use pure `torch.save`).
3. Create the repository structure per the master prompt.
4. Implement the Transformer in `ml/models/`.
5. Train tokenizer from a small public-domain dataset (`datasets/raw/` -> `datasets/processed/`).
6. Implement training loop (`ml/training/`) with real loss logging.
7. Implement checkpoint load/save (`ml/inference/`).
8. Build Veyra Studio frontend (`apps/studio/`) connecting to FastAPI backend (`services/api/`).
9. Run smoke tests (50 steps, save/load, generate).

---

*Report generated: 2026-10-08 (Windows 11, Python 3.14.7, CPU-only, 16 GB RAM).*
