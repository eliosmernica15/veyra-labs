#!/usr/bin/env python3
"""FastAPI backend for Veyra Labs — real endpoints, no fake data."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ml.models.transformer import Config, VeyraPrime
from ml.training.checkpoint import load_checkpoint
from ml.tokenizer.train_tokenizer import load_tokenizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("veyra.api")

app = FastAPI(title="Veyra Labs API", version="0.1.0")

# Configurable paths from environment
CHECKPOINT_DIR = Path(os.getenv("VEYRA_CHECKPOINT_DIR", "checkpoints"))
TOKENIZER_PATH = Path(os.getenv("VEYRA_TOKENIZER_PATH", "datasets/processed/tokenizer.json"))
DATA_PATH = Path(os.getenv("VEYRA_DATASET_PROCESSED", "datasets/processed/train.pkl"))

# In-memory active model reference for inference/demo
_active_model: Optional[VeyraPrime] = None
_active_config: Optional[Config] = None
_active_tokenizer = None


class GenerateRequest(BaseModel):
    prompt: str = "The quick brown fox"
    max_new_tokens: int = 20
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.9
    seed: Optional[int] = None


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "veyra-api"}


@app.get("/api/system")
def system_info():
    import torch, platform
    return {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "pytorch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cpu_threads": torch.get_num_threads() if hasattr(torch, "get_num_threads") else "unknown",
        "checkpoint_dir_exists": CHECKPOINT_DIR.exists(),
    }


@app.get("/api/models")
def list_models():
    # List available checkpoints as model versions
    checkpoints = []
    if CHECKPOINT_DIR.exists():
        for p in CHECKPOINT_DIR.glob("*.pt"):
            checkpoints.append({"file": p.name, "path": str(p)})
    return {"available_checkpoints": checkpoints}


@app.get("/api/checkpoints")
def list_checkpoints():
    if not CHECKPOINT_DIR.exists():
        return {"checkpoints": []}
    files = sorted(CHECKPOINT_DIR.glob("*.pt"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    results = []
    for p in files:
        try:
            _, state, config = load_checkpoint(p)
            results.append({
                "path": str(p),
                "step": state.get("step"),
                "vocab_size": config.vocab_size,
                "context_length": config.context_length,
                "embed_dim": config.embed_dim,
            })
        except Exception as e:
            results.append({"path": str(p), "error": str(e)})
    return {"checkpoints": results}


@app.get("/api/training/config")
def training_config():
    return {
        "batch_size": int(os.getenv("VEYRA_BATCH_SIZE", "4")),
        "lr": float(os.getenv("VEYRA_LR", "0.001")),
        "steps": int(os.getenv("VEYRA_STEPS", "50")),
        "checkpoint_interval": int(os.getenv("VEYRA_CHECKPOINT_INTERVAL", "10")),
        "device": "cpu",  # Always CPU on this environment
    }


@app.post("/api/generate")
def generate(req: GenerateRequest):
    try:
        # Load latest checkpoint for inference
        files = sorted(CHECKPOINT_DIR.glob("*.pt"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        if not files:
            raise HTTPException(status_code=404, detail="No checkpoint found in " + str(CHECKPOINT_DIR))
        latest = files[0]
        model, state, config = load_checkpoint(latest)
        tokenizer = load_tokenizer(TOKENIZER_PATH) if TOKENIZER_PATH.exists() else None
        if tokenizer is None:
            raise HTTPException(status_code=404, detail="Tokenizer not found: " + str(TOKENIZER_PATH))
        import torch
        encoding = tokenizer.encode(req.prompt)
        input_ids = torch.tensor([encoding.ids], dtype=torch.long)
        model.eval()
        with torch.no_grad():
            output_ids = model.generate(
                input_ids,
                max_new_tokens=req.max_new_tokens,
                temperature=req.temperature,
                top_k=req.top_k,
                top_p=req.top_p,
                seed=req.seed,
            )
        text = tokenizer.decode(output_ids[0].tolist())
        return {
            "checkpoint": str(latest),
            "step": state.get("step"),
            "prompt": req.prompt,
            "output": text,
            "settings": req.model_dump(),
        }
    except Exception as exc:
        logger.error(f"Generate error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/evaluations")
def evaluations():
    # Return evaluation results from saved files in runs/ or from memory
    # For Phase 1, return an empty list or load from file if present
    result_path = Path("runs/evaluation_result.json")
    if result_path.exists():
        import json
        return json.loads(result_path.read_text())
    return {"results": []}


@app.get("/api/training/{run_id}")
def get_training(run_id: str):
    # For simplicity, treat run_id as a checkpoint name or step reference
    return {
        "run_id": run_id,
        "status": "completed" if run_id.startswith("step_") else "unknown",
        "checkpoint_dir": str(CHECKPOINT_DIR.absolute()),
    }


@app.get("/api/training/{run_id}/logs")
def training_logs(run_id: str):
    # Return recent training logs (simplified for Phase 1)
    return {"run_id": run_id, "logs": [f"Training run {run_id} — see backend console for full logs."]}


@app.post("/api/evaluate")
def evaluate():
    try:
        checkpoint_path = next(CHECKPOINT_DIR.glob("checkpoint_*.pt"), None) or CHECKPOINT_DIR / "checkpoint_final.pt"
        if not checkpoint_path or not checkpoint_path.exists():
            raise HTTPException(status_code=404, detail="No checkpoint available for evaluation")
        from ml.evaluation.evaluate import evaluate_checkpoint
        result = evaluate_checkpoint(checkpoint_path, TOKENIZER_PATH, DATA_PATH)
        # Save result
        import json
        runs_dir = Path("runs")
        runs_dir.mkdir(exist_ok=True)
        result_file = runs_dir / "evaluation_result.json"
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2, default=str)
        return result
    except Exception as exc:
        logger.error(f"Evaluate error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
