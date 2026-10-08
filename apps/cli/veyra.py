#!/usr/bin/env python3
"""Veyra CLI — Python-only command-line agent (no TypeScript)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def status():
    import requests
    try:
        r = requests.get("http://localhost:8000/api/health", timeout=2)
        health = r.json() if r.status_code == 200 else {"status": "down"}
        print(f"Backend status: {health.get('status', 'unknown')}")
        r2 = requests.get("http://localhost:8000/api/system", timeout=2)
        sys_info = r2.json() if r2.status_code == 200 else {}
        print(f"Platform: {sys_info.get('platform', 'unknown')}")
        print(f"PyTorch: {sys_info.get('pytorch_version', 'not loaded')}")
        print(f"CUDA: {sys_info.get('cuda_available', False)}")
    except Exception as exc:
        print(f"Backend unreachable ({exc}). Start backend first: python -m services.api.main")


def list_models():
    import requests
    try:
        r = requests.get("http://localhost:8000/api/checkpoints", timeout=3)
        data = r.json() if r.status_code == 200 else {}
        checkpoints = data.get("checkpoints", [])
        print(f"Available checkpoints ({len(checkpoints)}):")
        for cp in checkpoints:
            print(f"  - {cp.get('path')} (step={cp.get('step')})")
    except Exception as exc:
        print(f"Error: {exc}")


def chat(args):
    import requests
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
        r = requests.post("http://localhost:8000/api/generate", json=payload, timeout=30)
        if r.status_code == 200:
            result = r.json()
            print(f"Checkpoint: {result.get('checkpoint')}")
            print(f"Output: {result.get('output')}")
        else:
            print(f"Generate failed ({r.status_code}): {r.text}")
    except Exception as exc:
        print(f"Request error: {exc}")


def train_cmd(args):
    from ml.training.train_loop import train
    result_path, model, losses = train(
        data_path=args.data,
        steps=args.steps,
        batch_size=args.batch_size,
        lr=args.lr,
        resume_from=args.resume,
    )
    print(f"Training complete. Checkpoint: {result_path}")
    print(f"Final losses (last 3): {losses[-3:] if len(losses) >= 3 else losses}")


def eval_cmd(args):
    import requests
    try:
        r = requests.post("http://localhost:8000/api/evaluate", timeout=60)
        result = r.json() if r.status_code == 200 else {}
        print(f"Perplexity: {result.get('perplexity', 'N/A')}")
        print(f"Avg loss: {result.get('avg_loss', 'N/A')}")
        print(f"Checkpoint load equivalence: {result.get('checkpoint_load_equivalence')}")
    except Exception as exc:
        print(f"Error: {exc}")


def config_cmd(args):
    print("Veyra configuration (from .env / defaults):")
    import dotenv
    dotenv.load_dotenv()
    for k in ["VEYRA_COMPANY_NAME", "VEYRA_PLATFORM_NAME", "VEYRA_STUDIO_NAME",
              "VEYRA_DEFAULT_MODEL", "VEYRA_MODEL_DIM", "VEYRA_MODEL_LAYERS"]:
        print(f"  {k}={os.getenv(k, 'not set')}")


def main():
    parser = argparse.ArgumentParser(prog="veyra", description="Veyra CLI")
    parser.add_argument("--version", action="version", version="veyra 0.1.0")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show backend status").set_defaults(func=lambda args: status())
    sub.add_parser("models", help="List available models/checkpoints").add_parser("list", dest="models_sub")
    # Fix: actually wire commands properly
    status_p = sub.add_parser("status", help="Show backend and system status")
    status_p.set_defaults(func=lambda args: status())

    list_p = sub.add_parser("models", help="List checkpoints")
    list_p.add_argument("list", nargs="?", const=True)
    # Actually define properly:
    # Redefine cleanly
    pass


if __name__ == "__main__":
    # Redefine cleanly without previous conflicts
    parser = argparse.ArgumentParser(prog="veyra", description="Veyra CLI")
    parser.add_argument("--version", action="version", version="veyra 0.1.0")
    sub = parser.add_subparsers(dest="command")

    p_status = sub.add_parser("status", help="Backend status")
    p_status.set_defaults(func=lambda args: status())

    p_models = sub.add_parser("models", help="Checkpoints")
    p_models_sub = p_models.add_subparsers(dest="models_subcmd")
    p_models_sub.add_parser("list", help="List checkpoints").set_defaults(func=lambda args: list_models())
    p_models_sub.add_parser("inspect", help="Inspect a model").set_defaults(func=lambda args: print("Inspect not fully implemented in Phase 1"))

    p_train = sub.add_parser("train", help="Start training")
    p_train.add_argument("--steps", type=int, default=50)
    p_train.add_argument("--batch-size", type=int, default=4)
    p_train.add_argument("--lr", type=float, default=1e-3)
    p_train.add_argument("--data", type=Path, default=Path("datasets/processed/train.pkl"))
    p_train.add_argument("--resume", type=Path, default=None)
    p_train.set_defaults(func=lambda args: train_cmd(args))

    p_chat = sub.add_parser("chat", help="Chat with model")
    p_chat.add_argument("--prompt", type=str, default="Hello")
    p_chat.add_argument("--max-new-tokens", type=int, default=20)
    p_chat.add_argument("--temperature", type=float, default=1.0)
    p_chat.add_argument("--top-k", type=int, default=50)
    p_chat.add_argument("--top-p", type=float, default=0.9)
    p_chat.add_argument("--seed", type=int, default=None)
    p_chat.set_defaults(func=lambda args: chat(args))

    p_eval = sub.add_parser("eval", help="Evaluate model")
    p_eval.set_defaults(func=lambda args: eval_cmd(args))

    p_config = sub.add_parser("config", help="Show config")
    p_config.set_defaults(func=lambda args: config_cmd(args))

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    args.func(args)
