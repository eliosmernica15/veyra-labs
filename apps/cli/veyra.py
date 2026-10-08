#!/usr/bin/env python3
"""Veyra CLI — expanded with inspection, diagnostics, config validation, and real backend connection."""
from __future__ import annotations

import argparse
import sys
import json
import os
import time
from pathlib import Path


# -------------------- Internal Utilities --------------------

def _load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except Exception:
        pass


def _get_backend(url: str = None):
    url = url or os.getenv("VEYRA_BACKEND_URL", "http://localhost:8000")
    import requests
    try:
        r = requests.get(f"{url}/api/health", timeout=3)
        return r.status_code == 200, url
    except Exception as exc:
        return False, str(exc)


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}m {secs:.1f}s"


# -------------------- Commands --------------------

def status():
    ok, info = _get_backend()
    _load_env()
    print("=== Veyra CLI — System Status ===")
    if ok:
        import requests
        url = info
        health = requests.get(f"{url}/api/health", timeout=2).json()
        sys_info = requests.get(f"{url}/api/system", timeout=2).json()
        print(f"Backend:  {health.get('status', 'unknown')} at {url}")
        print(f"Platform: {sys_info.get('platform', 'unknown')}")
        print(f"Python:   {sys_info.get('python_version', 'unknown')}")
        print(f"PyTorch:  {sys_info.get('pytorch_version', 'unknown')}")
        print(f"CUDA:     {sys_info.get('cuda_available', False)}")
        # Show latest checkpoint info from backend
        try:
            cp_r = requests.get(f"{url}/api/checkpoints", timeout=2)
            cps = cp_r.json().get("checkpoints", []) if cp_r.status_code == 200 else []
            if cps:
                latest = cps[0]
                print(f"Checkpoints: {len(cps)} available; latest step={latest.get('step', 'N/A')}")
            else:
                print("Checkpoints: none found")
        except Exception as exc:
            print(f"Checkpoints query failed: {exc}")
    else:
        print(f"Backend unreachable: {info}")
    # Local model info
    try:
        import torch
        print(f"Local torch: {torch.__version__}")
        print(f"Local CUDA available: {torch.cuda.is_available()}")
    except Exception:
        print("Local torch: not available")


def list_models(args):
    ok, info = _get_backend()
    if not ok:
        print(f"Backend unreachable ({info}). Cannot list remote checkpoints.")
        # Show local files
        checkpoint_dir = Path(os.getenv("VEYRA_CHECKPOINT_DIR", "checkpoints"))
        if checkpoint_dir.exists():
            files = sorted(checkpoint_dir.glob("*.pt"), key=lambda p: p.stat().st_mtime, reverse=True)
            print(f"Local checkpoints ({len(files)}):")
            for f in files:
                print(f"  - {f.name}")
        else:
            print("No local checkpoints directory found.")
        return
    import requests
    url = info
    try:
        r = requests.get(f"{url}/api/checkpoints", timeout=3)
        data = r.json() if r.status_code == 200 else {}
        checkpoints = data.get("checkpoints", [])
        print(f"Available checkpoints ({len(checkpoints)}) from backend:")
        for cp in checkpoints:
            step = cp.get("step", "N/A")
            vocab = cp.get("vocab_size", "N/A")
            path = cp.get("path", "unknown")
            error = cp.get("error")
            if error:
                print(f"  - {path.name if hasattr(path, 'name') else path} (ERROR: {error})")
            else:
                print(f"  - {path} (step={step}, vocab={vocab})")
    except Exception as exc:
        print(f"Request error: {exc}")


def inspect_model(args):
    checkpoint_path = args.checkpoint
    print("=== Checkpoint Inspection ===")
    print(f"File: {checkpoint_path}")
    if not checkpoint_path.exists():
        print(f"ERROR: Checkpoint not found: {checkpoint_path}")
        return
    try:
        import torch
        from ml.training.checkpoint import load_checkpoint
        from ml.models.transformer import Config
        import sys
        sys.path.insert(0, ".")
        # Load with known vocab from dataset or file metadata if available
        # For simplicity, load using the file's own vocab size
        state = torch.load(str(checkpoint_path), weights_only=False, map_location="cpu")
        vocab_size = state.get("vocab_size", state.get("config", {}).get("vocab_size", 4096))
        config = Config(vocab_size=vocab_size)
        # Apply saved config if present
        if "config" in state:
            for k, v in state["config"].items():
                if hasattr(config, k):
                    setattr(config, k, v)
        config.vocab_size = vocab_size
        import torch.nn as nn
        from ml.models.transformer import VeyraPrime
        model = VeyraPrime(config)
        model.load_state_dict(state["model_state_dict"])
        print(f"Architecture: decoder-only Transformer")
        print(f"Parameters (est.): {model.param_estimate_:,}")
        print(f"Vocab size: {config.vocab_size}")
        print(f"Context length: {config.context_length}")
        print(f"Layers: {config.num_layers}")
        print(f"Embed dim: {config.embed_dim}")
        print(f"Heads: {config.num_heads}")
        print(f"Hidden dim: {config.hidden_dim}")
        print(f"Checkpoint step: {state.get('step', 'N/A')}")
        print(f"Tokenizer path: {state.get('tokenizer_path', 'unknown')}")
        # Count actual weights
        total_params = sum(p.numel() for p in model.parameters())
        print(f"Actual parameter count: {total_params:,}")
        # Check compatibility with tokenizer
        tokenizer_path = state.get("tokenizer_path")
        if tokenizer_path and Path(str(tokenizer_path)).exists():
            print(f"Tokenizer file present: yes")
        else:
            print(f"Tokenizer file present: no (path: {tokenizer_path})")
    except Exception as exc:
        print(f"ERROR inspecting checkpoint: {exc}")


def chat(args):
    ok, info = _get_backend()
    if not ok:
        print(f"Backend unreachable ({info}). Try starting it: python -m services.api.main")
        return
    import requests
    url = info
    payload = {
        "prompt": args.prompt,
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_k": args.top_k,
        "top_p": args.top_p,
    }
    if args.seed is not None:
        payload["seed"] = args.seed
    try:
        r = requests.post(f"{url}/api/generate", json=payload, timeout=30)
        if r.status_code == 200:
            result = r.json()
            print(f"Checkpoint: {result.get('checkpoint', 'unknown')}")
            print(f"Model step: {result.get('step', 'unknown')}")
            print(f"Prompt: {result.get('prompt', '')}")
            print(f"Output: {result.get('output', '')}")
            print(f"Generation settings: temperature={args.temperature}, max_new_tokens={args.max_new_tokens}, seed={args.seed}")
        else:
            print(f"Generate failed ({r.status_code}): {r.text}")
    except Exception as exc:
        print(f"Request error: {exc}")


def train_cmd(args):
    try:
        from ml.training.train_loop import train
        result_path, model, losses = train(
            data_path=args.data,
            steps=args.steps,
            batch_size=args.batch_size,
            lr=args.lr,
            resume_from=args.resume,
        )
        print("=== Training Report ===")
        print(f"Checkpoint saved: {result_path}")
        if losses:
            print(f"Initial loss: {losses[0]:.4f}")
            print(f"Final loss: {losses[-1]:.4f}")
            print(f"Loss improvement: {losses[0] - losses[-1]:.4f}")
            print(f"Steps completed: {len(losses)}")
        # Show estimated model size
        import torch
        try:
            state = torch.load(str(result_path), weights_only=False, map_location="cpu")
            vocab_size = state.get("vocab_size", 4096)
            from ml.models.transformer import Config
            config = Config(vocab_size=vocab_size)
            if "config" in state:
                for k, v in state["config"].items():
                    if hasattr(config, k):
                        setattr(config, k, v)
            config.vocab_size = vocab_size
            from ml.models.transformer import VeyraPrime
            m = VeyraPrime(config)
            m.load_state_dict(state["model_state_dict"])
            print(f"Model vocab size: {vocab_size}")
            print(f"Estimated parameters: {m.param_estimate_:,}")
            print(f"Actual parameters: {sum(p.numel() for p in m.parameters()):,}")
        except Exception as exc:
            print(f"Could not inspect checkpoint size: {exc}")
    except Exception as exc:
        print(f"Training error: {exc}")
        import traceback
        traceback.print_exc()


def eval_cmd(args):
    try:
        import requests
        url = os.getenv("VEYRA_BACKEND_URL", "http://localhost:8000")
        r = requests.post(f"{url}/api/evaluate", timeout=60)
        if r.status_code == 200:
            result = r.json()
            print("=== Evaluation Results ===")
            for k, v in result.items():
                print(f"{k}: {v}")
        else:
            # Fallback to direct CLI evaluation
            import torch
            from ml.evaluation.evaluate import evaluate_checkpoint
            checkpoint_path = Path(os.getenv("VEYRA_CHECKPOINT_DIR", "checkpoints")) / "checkpoint_final.pt"
            tokenizer_path = Path(os.getenv("VEYRA_TOKENIZER_PATH", "datasets/processed/tokenizer.json"))
            data_path = Path(os.getenv("VEYRA_DATASET_PROCESSED", "datasets/processed/train.pkl"))
            if checkpoint_path.exists():
                result = evaluate_checkpoint(checkpoint_path, tokenizer_path, data_path)
                print("=== Direct CLI Evaluation ===")
                for k, v in result.items():
                    print(f"{k}: {v}")
            else:
                print(f"No checkpoint found at {checkpoint_path}")
    except Exception as exc:
        print(f"Evaluation error: {exc}")


def config_cmd(args):
    _load_env()
    from dotenv import load_dotenv
    load_dotenv(override=False)
    import os
    print("=== Veyra Configuration ===")
    fields = {
        "VEYRA_COMPANY_NAME": "Company",
        "VEYRA_PLATFORM_NAME": "Platform",
        "VEYRA_STUDIO_NAME": "Studio",
        "VEYRA_CLI_NAME": "CLI",
        "VEYRA_DEFAULT_MODEL": "Default Model",
        "VEYRA_CODING_MODEL": "Coding Model",
        "VEYRA_IMAGE_MODEL": "Image Model",
        "VEYRA_VIDEO_MODEL": "Video Model",
        "VEYRA_AUDIO_MODEL": "Audio Model",
        "VEYRA_RESEARCH_AGENT": "Research Agent",
        "VEYRA_BACKEND_URL": "Backend URL",
        "VEYRA_CHECKPOINT_DIR": "Checkpoint Dir",
        "VEYRA_DATASET_RAW": "Raw Dataset",
        "VEYRA_DATASET_PROCESSED": "Processed Dataset",
        "VEYRA_MODEL_DIM": "Embed Dim",
        "VEYRA_MODEL_LAYERS": "Layers",
        "VEYRA_MODEL_HEADS": "Heads",
        "VEYRA_MODEL_CONTEXT": "Context Length",
        "VEYRA_BATCH_SIZE": "Batch Size",
        "VEYRA_LR": "Learning Rate",
    }
    for k, label in fields.items():
        val = os.getenv(k, "(not set)")
        print(f"  {label}: {val}")
    # Show config files
    config_dir = Path(os.getenv("VEYRA_CONFIG_DIR", "configs"))
    if config_dir.exists():
        print("  Config directory contents:")
        for p in config_dir.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                print(f"    - {p}")


def dataset_info(args):
    print("=== Dataset Information ===")
    raw_path = Path(os.getenv("VEYRA_DATASET_RAW", "datasets/raw"))
    processed_path = Path(os.getenv("VEYRA_DATASET_PROCESSED", "datasets/processed"))
    # Check raw
    if raw_path.is_dir():
        files = list(raw_path.glob("*"))
        print(f"Raw directory: {raw_path}")
        for f in files:
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")[:200]
                    char_count = len(content)
                    word_approx = len(content.split())
                    print(f"  - {f.name}: {char_count} chars, ~{word_approx} words (~{len(content):.1f} KB)")
                    # Record provenance
                    print(f"      Source: {f.name} (local file; user-provided or synthetic for smoke test)")
                    print(f"      License/Status: Check user-provided source; synthetic text for smoke test only")
                except Exception as exc:
                    print(f"  - {f.name}: file read error ({exc})")
    else:
        print(f"Raw directory not found: {raw_path}")
    # Check processed
    if processed_path.is_dir():
        files = list(processed_path.glob("*"))
        print(f"Processed directory: {processed_path}")
        for f in files:
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                print(f"  - {f.name}: {f.stat().st_size} bytes (~{size_kb:.1f} KB)")


# -------------------- Main --------------------

def main():
    parser = argparse.ArgumentParser(prog="veyra", description="Veyra CLI — real model operations")
    parser.add_argument("--version", action="version", version="veyra 0.2.0 (Phase 2)")
    sub = parser.add_subparsers(dest="command")

    # Status
    sub.add_parser("status", help="Show backend and system status").set_defaults(func=lambda args: status())

    # Models
    p_models = sub.add_parser("models", help="List or inspect checkpoints")
    p_models_sub = p_models.add_subparsers(dest="models_subcmd")
    p_models_sub.add_parser("list", help="List checkpoints").set_defaults(func=lambda args: list_models(args))
    p_inspect = p_models_sub.add_parser("inspect", help="Inspect a checkpoint")
    p_inspect.add_argument("--checkpoint", type=Path, default=Path(os.getenv("VEYRA_CHECKPOINT_DIR", "checkpoints")) / "checkpoint_final.pt")
    p_inspect.set_defaults(func=lambda args: inspect_model(args))

    # Train
    p_train = sub.add_parser("train", help="Run a real training run")
    p_train.add_argument("--steps", type=int, default=50)
    p_train.add_argument("--batch-size", type=int, default=4)
    p_train.add_argument("--lr", type=float, default=1e-3)
    p_train.add_argument("--data", type=Path, default=Path(os.getenv("VEYRA_DATASET_PROCESSED", "datasets/processed/train.pkl")))
    p_train.add_argument("--resume", type=Path, default=None)
    p_train.set_defaults(func=lambda args: train_cmd(args))

    # Chat
    p_chat = sub.add_parser("chat", help="Generate text from a real checkpoint")
    p_chat.add_argument("--prompt", type=str, default="The quick brown fox")
    p_chat.add_argument("--max-new-tokens", type=int, default=20)
    p_chat.add_argument("--temperature", type=float, default=1.0)
    p_chat.add_argument("--top-k", type=int, default=50)
    p_chat.add_argument("--top-p", type=float, default=0.9)
    p_chat.add_argument("--seed", type=int, default=None)
    p_chat.set_defaults(func=lambda args: chat(args))

    # Evaluate
    p_eval = sub.add_parser("eval", help="Run evaluation suite")
    p_eval.set_defaults(func=lambda args: eval_cmd(args))

    # Config
    p_config = sub.add_parser("config", help="Show configurable settings")
    p_config.set_defaults(func=lambda args: config_cmd(args))

    # Dataset info (new)
    p_dataset = sub.add_parser("dataset", help="Show dataset info and provenance")
    p_dataset.set_defaults(func=lambda args: dataset_info(args))

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
