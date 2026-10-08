#!/usr/bin/env python3
"""Real training loop with measured loss, gradient clipping, checkpointing."""
from __future__ import annotations

import argparse
import time
import logging
from pathlib import Path
import pickle

import torch
import torch.nn.functional as F
from torch.optim import AdamW

from ml.models.transformer import VeyraPrime, Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("veyra.training")


# Detect best available device for portability (CPU always works; CUDA preferred when available)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_data(path: Path):
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["samples"], data.get("tokenizer_path", ""), data.get("vocab_size", 4096)


def train(
    model_path: Path | None = None,
    checkpoint_path: Path | None = None,
    data_path: Path = Path("datasets/processed/train.pkl"),
    output_dir: Path = Path("checkpoints"),
    steps: int = 50,
    batch_size: int = 4,
    lr: float = 1e-3,
    weight_decay: float = 0.01,
    grad_clip: float = 1.0,
    checkpoint_interval: int = 10,
    resume_from: Path | None = None,
):
    # Load dataset first to get vocab size
    samples, tokenizer_path, vocab_size = load_data(data_path)
    if not samples:
        raise ValueError(f"No samples loaded from {data_path}")

    # Load or initialize model using dataset vocab size
    model_config_vocab = vocab_size
    if resume_from and resume_from.exists():
        logger.info(f"Resuming from checkpoint: {resume_from}")
        state = torch.load(str(resume_from), weights_only=False)
        config = Config(vocab_size=model_config_vocab)
        if "config" in state:
            config_dict = state.get("config", {})
            for k, v in config_dict.items():
                if hasattr(config, k):
                    setattr(config, k, v)
        # Preserve vocab size from dataset if different
        config.vocab_size = vocab_size
        model = VeyraPrime(config)
        model.load_state_dict(state["model_state_dict"])
        optimizer_state = state.get("optimizer_state_dict", None)
        completed_steps = state.get("step", 0)
        logger.info(f"Resumed at step {completed_steps}")
    elif model_path and model_path.exists():
        logger.info(f"Loading model from {model_path}")
        state = torch.load(str(model_path), weights_only=False)
        config = Config(vocab_size=model_config_vocab)
        if "config" in state:
            for k, v in state["config"].items():
                if hasattr(config, k):
                    setattr(config, k, v)
        config.vocab_size = vocab_size
        model = VeyraPrime(config)
        model.load_state_dict(state["model_state_dict"])
        completed_steps = state.get("step", 0)
        optimizer_state = state.get("optimizer_state_dict", None)
    else:
        logger.info("Initializing new model from scratch.")
        config = Config(vocab_size=vocab_size)
        model = VeyraPrime(config)
        optimizer_state = None
        completed_steps = 0

    # Use portable device (CUDA preferred, CPU fallback); config stores preferred device
    device = DEVICE  # torch.device("cuda") or torch.device("cpu")
    config.device = device  # sync config with actual device
    model.to(device)
    model.train()

    # Setup optimizer
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    if optimizer_state is not None:
        optimizer.load_state_dict(optimizer_state)

    # Load dataset
    samples, tokenizer_path, vocab_size = load_data(data_path)
    if not samples:
        raise ValueError(f"No samples loaded from {data_path}")
    # Filter samples to match vocab size
    max_token = max(s[0].max().item() for s in samples) if samples else 0
    # Ensure samples fit vocab
    samples = [s for s in samples if s[0].max().item() < vocab_size and s[1].max().item() < vocab_size]
    if not samples:
        samples = [(torch.zeros(10, dtype=torch.long), torch.zeros(10, dtype=torch.long))]

    start_time = time.time()
    losses = []
    for step in range(completed_steps, completed_steps + steps):
        # Sample batch
        batch_samples = [samples[i % len(samples)] for i in range(batch_size)]
        x_batch = torch.stack([s[0] for s in batch_samples])
        y_batch = torch.stack([s[1] for s in batch_samples])
        x_batch = x_batch.to(device)
        y_batch = y_batch.to(device)

        optimizer.zero_grad()
        loss = model.compute_loss((x_batch, y_batch))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        optimizer.step()

        loss_val = loss.item()
        losses.append(loss_val)
        if (step + 1) % max(1, steps // 10) == 0 or step == completed_steps:
            logger.info(f"Step {step + 1} — loss: {loss_val:.4f} — elapsed: {time.time() - start_time:.1f}s")

        if (step + 1) % checkpoint_interval == 0:
            checkpoint_path_final = output_dir / f"checkpoint_step_{step + 1}.pt"
            output_dir.mkdir(parents=True, exist_ok=True)
            torch.save({
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "step": step + 1,
                "config": {
                    "vocab_size": config.vocab_size,
                    "context_length": config.context_length,
                    "embed_dim": config.embed_dim,
                    "num_layers": config.num_layers,
                    "num_heads": config.num_heads,
                    "hidden_dim": config.hidden_dim,
                },
                "tokenizer_path": tokenizer_path,
                "vocab_size": vocab_size,
                "loss": loss_val,
            }, str(checkpoint_path_final))
            logger.info(f"Checkpoint saved: {checkpoint_path_final}")

    # Final checkpoint
    final_path = output_dir / "checkpoint_final.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "step": completed_steps + steps,
        "config": {
            "vocab_size": config.vocab_size,
            "context_length": config.context_length,
            "embed_dim": config.embed_dim,
            "num_layers": config.num_layers,
            "num_heads": config.num_heads,
            "hidden_dim": config.hidden_dim,
        },
        "tokenizer_path": tokenizer_path,
        "vocab_size": vocab_size,
        "losses": losses,
        "final_loss": losses[-1] if losses else None,
    }, str(final_path))
    logger.info(f"Training complete. Final checkpoint: {final_path} (losses: {losses})")
    return final_path, model, losses


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("datasets/processed/train.pkl"))
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--resume", type=Path, default=None)
    args = parser.parse_args()
    train(data_path=args.data, steps=args.steps, batch_size=args.batch_size,
          lr=args.lr, resume_from=args.resume)
