#!/usr/bin/env python3
"""Real training loop with measured loss, gradient clipping, checkpointing."""
from __future__ import annotations

import argparse
import hashlib
import time
import logging
from pathlib import Path
import pickle
import random
from typing import Any

import torch
from tokenizers import Tokenizer
from torch.optim import AdamW

from ml.models.transformer import VeyraPrime, Config
from ml.path_utils import portable_path_string, resolve_portable_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("veyra.training")


# Detect best available device for portability (CPU always works; CUDA preferred when available)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_data(path: Path):
    data = _read_dataset(path)
    return data["samples"], data.get("tokenizer_path", ""), data.get("vocab_size", 4096)


def _validate_samples(
    samples: list[Any],
    *,
    path: Path,
    vocab_size: int,
    context_length: int,
) -> None:
    if not samples:
        raise ValueError(f"No samples loaded from {path}")
    for index, sample in enumerate(samples):
        if not isinstance(sample, (tuple, list)) or len(sample) != 2:
            raise ValueError(f"{path} sample {index} must be an (input, target) pair")
        x, y = sample
        if not isinstance(x, torch.Tensor) or not isinstance(y, torch.Tensor):
            raise ValueError(f"{path} sample {index} must contain tensors")
        if x.ndim != 1 or y.ndim != 1 or x.shape != y.shape:
            raise ValueError(f"{path} sample {index} inputs and targets must be matching 1D tensors")
        if not 0 < x.numel() <= context_length:
            raise ValueError(f"{path} sample {index} length must be in [1, {context_length}]")
        if torch.any((x < 0) | (x >= vocab_size)):
            raise ValueError(f"{path} sample {index} has input IDs outside the vocabulary")
        if torch.any((y != -1) & ((y < 0) | (y >= vocab_size))):
            raise ValueError(f"{path} sample {index} has invalid target IDs")
        if not torch.any(y != -1):
            raise ValueError(f"{path} sample {index} has no supervised targets")


def evaluate(
    model: VeyraPrime,
    samples: list[Any],
    *,
    device: torch.device | None = None,
    batch_size: int = 8,
) -> float:
    """Return token-weighted validation loss without changing weights or final train/eval mode."""
    if not samples:
        raise ValueError("Validation dataset contains no samples")
    if batch_size <= 0:
        raise ValueError("Validation batch_size must be positive")
    was_training = model.training
    model.eval()
    weighted_loss = 0.0
    supervised_tokens = 0
    try:
        with torch.no_grad():
            for offset in range(0, len(samples), batch_size):
                batch = samples[offset:offset + batch_size]
                batch_x = torch.stack([sample[0] for sample in batch])
                batch_y = torch.stack([sample[1] for sample in batch])
                target_count = int((batch_y != -1).sum().item())
                if target_count == 0:
                    continue
                if device is not None:
                    batch_x = batch_x.to(device)
                    batch_y = batch_y.to(device)
                loss = model.compute_loss((batch_x, batch_y))
                weighted_loss += float(loss.item()) * target_count
                supervised_tokens += target_count
    finally:
        model.train(was_training)
    if supervised_tokens == 0:
        raise ValueError("Validation dataset contains no supervised target tokens")
    return weighted_loss / supervised_tokens


def _save_checkpoint_exclusive(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as checkpoint_file:
        torch.save(state, checkpoint_file)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    accumulation_steps: int = 1,
    mixed_precision: bool = False,
    resume_from: Path | None = None,
    val_data_path: Path | None = None,
    validation_interval: int = 10,
    seed: int = 42,
):
    if checkpoint_path is not None:
        if model_path is not None or resume_from is not None:
            raise ValueError("checkpoint_path cannot be combined with model_path or resume_from")
        model_path = checkpoint_path
    if steps <= 0 or batch_size <= 0 or checkpoint_interval <= 0 or accumulation_steps <= 0:
        raise ValueError("steps, batch_size, checkpoint_interval, and accumulation_steps must be positive")
    if validation_interval <= 0:
        raise ValueError("validation_interval must be positive")
    if lr <= 0 or grad_clip <= 0:
        raise ValueError("lr and grad_clip must be positive")
    if model_path is not None and resume_from is not None:
        raise ValueError("Specify either model_path or resume_from, not both")
    for requested_checkpoint in (model_path, resume_from):
        if requested_checkpoint is not None and not requested_checkpoint.is_file():
            raise FileNotFoundError(f"Requested checkpoint does not exist: {requested_checkpoint}")

    torch.manual_seed(seed)
    tokens_seen = 0
    total_optimizer_steps = 0
    losses: list[float] = []
    val_losses: list[dict[str, float | int]] = []
    training_data = _read_dataset(data_path)
    samples = training_data["samples"]
    tokenizer_path = training_data.get("tokenizer_path", "")
    vocab_size = training_data.get("vocab_size", 4096)
    config_hint = training_data.get("context_length", 128)
    if not isinstance(vocab_size, int) or vocab_size <= 0:
        raise ValueError(f"{data_path} has an invalid vocab_size")
    if not isinstance(config_hint, int) or config_hint <= 0:
        raise ValueError(f"{data_path} has an invalid context_length")
    _validate_samples(samples, path=data_path, vocab_size=vocab_size, context_length=config_hint)

    validation_data = None
    validation_samples = None
    if val_data_path is not None:
        if val_data_path.resolve() == data_path.resolve():
            raise ValueError("Training and validation datasets must be different files")
        validation_data = _read_dataset(val_data_path)
        validation_samples = validation_data["samples"]
        if validation_data.get("vocab_size", 4096) != vocab_size:
            raise ValueError("Training and validation vocabularies must match")
        validation_tokenizer_path = validation_data.get("tokenizer_path")
        validation_tokenizer_hash = validation_data.get("tokenizer_sha256")
        training_tokenizer_hash = training_data.get("tokenizer_sha256")
        if not tokenizer_path or not validation_tokenizer_path:
            raise ValueError("Training and validation datasets must record tokenizer paths")
        if (
            resolve_portable_path(validation_tokenizer_path).resolve()
            != resolve_portable_path(tokenizer_path).resolve()
        ):
            raise ValueError("Training and validation datasets must use the same tokenizer")
        if not training_tokenizer_hash or not validation_tokenizer_hash:
            raise ValueError("Training and validation datasets must record tokenizer hashes")
        if validation_tokenizer_hash != training_tokenizer_hash:
            raise ValueError("Training and validation tokenizer hashes must match")
        if training_data.get("split") not in (None, "train") or validation_data.get("split") not in (None, "val"):
            raise ValueError("Training and validation datasets must declare train and val splits")
        training_documents = {
            document.get("normalized_content_sha256")
            for document in training_data.get("documents", [])
        }
        validation_documents = {
            document.get("normalized_content_sha256")
            for document in validation_data.get("documents", [])
        }
        training_documents.discard(None)
        validation_documents.discard(None)
        if training_documents & validation_documents:
            raise ValueError("Training and validation datasets contain overlapping documents")
        if not validation_samples:
            raise ValueError(f"No validation samples loaded from {val_data_path}")

    # Load or initialize model using dataset vocab size
    if resume_from is not None:
        logger.info(f"Resuming from checkpoint: {resume_from}")
        state = torch.load(str(resume_from), weights_only=True, map_location="cpu")
        config = _config_from_checkpoint(state, vocab_size, config_hint)
        _validate_checkpoint_tokenizer(state, tokenizer_path, training_data, vocab_size)
        model = VeyraPrime(config)
        model.load_state_dict(state["model_state_dict"], strict=True)
        optimizer_state = state.get("optimizer_state_dict", None)
        completed_steps = state.get("step", 0)
        tokens_seen = state.get("meaningful_tokens_seen", 0)
        total_optimizer_steps = state.get("optimizer_steps", 0)
        losses = state.get("losses", []) if state.get("losses") is not None else []
        val_losses = state.get("validation_losses", []) if state.get("validation_losses") is not None else []
        logger.info(f"Resumed at step {completed_steps}, tokens {tokens_seen}, optimizer_steps {total_optimizer_steps}")
    elif model_path is not None:
        logger.info(f"Loading model from {model_path}")
        state = torch.load(str(model_path), weights_only=True, map_location="cpu")
        config = _config_from_checkpoint(state, vocab_size, config_hint)
        _validate_checkpoint_tokenizer(state, tokenizer_path, training_data, vocab_size)
        model = VeyraPrime(config)
        model.load_state_dict(state["model_state_dict"], strict=True)
        optimizer_state = None
        completed_steps = 0
    else:
        logger.info("Initializing new model from scratch.")
        config = Config(vocab_size=vocab_size, context_length=config_hint)
        model = VeyraPrime(config)
        optimizer_state = None
        completed_steps = 0

    if config.vocab_size != vocab_size:
        raise ValueError("Checkpoint and training dataset vocabularies do not match")
    if config.context_length != config_hint:
        raise ValueError("Checkpoint and training dataset context lengths do not match")
    _validate_samples(samples, path=data_path, vocab_size=config.vocab_size,
                      context_length=config.context_length)
    if validation_data is not None:
        if validation_data.get("context_length", config.context_length) != config.context_length:
            raise ValueError("Validation context length does not match the checkpoint")
        _validate_samples(validation_samples, path=val_data_path, vocab_size=config.vocab_size,
                          context_length=config.context_length)

    final_path = output_dir / "checkpoint_final.pt"
    interval_steps = list(range(
        ((completed_steps // checkpoint_interval) + 1) * checkpoint_interval,
        completed_steps + steps + 1,
        checkpoint_interval,
    ))
    checkpoint_paths = [output_dir / f"checkpoint_step_{step}.pt" for step in interval_steps]
    collisions = [path for path in [*checkpoint_paths, final_path] if path.exists()]
    if collisions:
        raise FileExistsError(
            "Refusing to overwrite checkpoint(s): " + ", ".join(str(path) for path in collisions)
        )
    train_file_sha256 = _sha256_file(data_path)
    validation_file_sha256 = _sha256_file(val_data_path) if val_data_path is not None else None

    # Use portable device (CUDA preferred, CPU fallback); config stores preferred device
    device = DEVICE  # torch.device("cuda") or torch.device("cpu")
    config.device = device  # sync config with actual device
    model.to(device)
    model.train()

    # Setup optimizer
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    if optimizer_state is not None:
        optimizer.load_state_dict(optimizer_state)
    scaler = torch.amp.GradScaler("cuda") if (mixed_precision and torch.cuda.is_available()) else None
    use_amp = mixed_precision and torch.cuda.is_available()
    logger.info("Mixed precision %s.", "enabled" if use_amp else "disabled")

    start_time = time.time()
    rng = random.Random(seed)
    for step in range(completed_steps, completed_steps + steps):
        microbatches: list[tuple[torch.Tensor, torch.Tensor, int]] = []
        for _ in range(accumulation_steps):
            indices = [rng.randrange(len(samples)) for _ in range(batch_size)]
            batch_samples = [samples[index] for index in indices]
            x_batch = torch.stack([s[0] for s in batch_samples])
            y_batch = torch.stack([s[1] for s in batch_samples])
            target_count = int((y_batch != -1).sum().item())
            if target_count == 0:
                raise ValueError("Training batch contains no supervised target tokens")
            microbatches.append((x_batch.to(device), y_batch.to(device), target_count))
        step_target_count = sum(item[2] for item in microbatches)
        optimizer.zero_grad(set_to_none=True)
        loss_total = 0.0
        for x_batch, y_batch, target_count in microbatches:
            if use_amp:
                with torch.amp.autocast("cuda"):
                    loss = model.compute_loss((x_batch, y_batch))
                scaler.scale(loss * (target_count / step_target_count)).backward()
            else:
                loss = model.compute_loss((x_batch, y_batch))
                (loss * (target_count / step_target_count)).backward()
            loss_total += float(loss.item()) * target_count
        if use_amp:
            scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        if use_amp:
            scaler.step(optimizer)
            scaler.update()
        else:
            optimizer.step()
        total_optimizer_steps += 1
        loss_val = loss_total / step_target_count
        losses.append(loss_val)
        tokens_seen += step_target_count
        global_step = step + 1
        validation_loss = None
        if validation_samples is not None and global_step % validation_interval == 0:
            validation_loss = evaluate(model, validation_samples, device=device)
            val_losses.append({"step": global_step, "loss": validation_loss})
        if (step + 1) % max(1, steps // 10) == 0 or step == completed_steps:
            elapsed = time.time() - start_time
            logger.info(
                f"Step {global_step} - loss: {loss_val:.4f} - validation: "
                f"{validation_loss if validation_loss is not None else 'not scheduled'} "
                f"- supervised_tokens_seen: {tokens_seen} "
                f"- optimizer_steps: {total_optimizer_steps} - elapsed: {elapsed:.1f}s"
            )

        if (step + 1) % checkpoint_interval == 0:
            checkpoint_path_final = output_dir / f"checkpoint_step_{global_step}.pt"
            _save_checkpoint_exclusive(checkpoint_path_final, _checkpoint_state(
                model, optimizer, config, global_step, total_optimizer_steps, tokens_seen,
                tokenizer_path, vocab_size, losses, val_losses, training_data, validation_data,
                train_file_sha256, validation_file_sha256, loss_val, use_amp, device,
                start_time, accumulation_steps, seed, resume_from or model_path,
            ))
            logger.info(f"Checkpoint saved: {checkpoint_path_final}")

    final_step = completed_steps + steps
    _save_checkpoint_exclusive(final_path, _checkpoint_state(
        model, optimizer, config, final_step, total_optimizer_steps, tokens_seen,
        tokenizer_path, vocab_size, losses, val_losses, training_data, validation_data,
        train_file_sha256, validation_file_sha256, losses[-1], use_amp, device,
        start_time, accumulation_steps, seed, resume_from or model_path,
    ))
    logger.info(f"Training complete. Final checkpoint: {final_path} (losses: {len(losses)}, supervised tokens: {tokens_seen}, optimizer_steps: {total_optimizer_steps})")
    return final_path, model, losses


def _read_dataset(path: Path) -> dict[str, Any]:
    with path.open("rb") as data_file:
        dataset = pickle.load(data_file)
    if not isinstance(dataset, dict) or not isinstance(dataset.get("samples"), list):
        raise ValueError(f"{path} must contain a dictionary with a samples list")
    return dataset


def _config_from_checkpoint(state: dict[str, Any], vocab_size: int, context_length: int) -> Config:
    config_data = state.get("config")
    if not isinstance(config_data, dict):
        raise ValueError("Checkpoint has no model configuration")
    config = Config(**{
        key: config_data[key]
        for key in ("vocab_size", "context_length", "embed_dim", "num_layers", "num_heads", "hidden_dim")
        if key in config_data
    })
    if config.vocab_size != vocab_size:
        raise ValueError("Checkpoint and dataset vocabularies do not match")
    if config.context_length != context_length:
        raise ValueError("Checkpoint and dataset context lengths do not match")
    return config


def _validate_checkpoint_tokenizer(
    state: dict[str, Any],
    tokenizer_path: str,
    dataset: dict[str, Any],
    vocab_size: int,
) -> None:
    checkpoint_tokenizer = state.get("tokenizer_path")
    if checkpoint_tokenizer and tokenizer_path:
        if (
            resolve_portable_path(checkpoint_tokenizer).resolve()
            != resolve_portable_path(tokenizer_path).resolve()
        ):
            raise ValueError("Checkpoint tokenizer path does not match the training dataset")
    checkpoint_hash = state.get("tokenizer_sha256")
    dataset_hash = dataset.get("tokenizer_sha256")
    if checkpoint_hash and dataset_hash and checkpoint_hash != dataset_hash:
        raise ValueError("Checkpoint tokenizer hash does not match the training dataset")
    if tokenizer_path:
        tokenizer_file = resolve_portable_path(tokenizer_path)
        actual_hash = _sha256_file(tokenizer_file)
        if dataset_hash and actual_hash != dataset_hash:
            raise ValueError("Training dataset tokenizer hash does not match the tokenizer file")
        if checkpoint_hash and actual_hash != checkpoint_hash:
            raise ValueError("Checkpoint tokenizer hash does not match the tokenizer file")
        tokenizer = Tokenizer.from_file(str(tokenizer_file))
        if tokenizer.get_vocab_size() != vocab_size:
            raise ValueError("Tokenizer vocabulary does not match the training dataset")


def _checkpoint_state(
    model: VeyraPrime,
    optimizer: AdamW,
    config: Config,
    step: int,
    optimizer_steps: int,
    meaningful_tokens_seen: int,
    tokenizer_path: str,
    vocab_size: int,
    losses: list[float],
    validation_losses: list[dict[str, float | int]],
    training_data: dict[str, Any],
    validation_data: dict[str, Any] | None,
    training_file_sha256: str,
    validation_file_sha256: str | None,
    loss: float,
    mixed_precision: bool,
    device: torch.device,
    start_time: float,
    accumulation_steps: int,
    seed: int,
    parent_checkpoint: Path | None,
) -> dict[str, Any]:
    return {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "step": step,
        "optimizer_steps": optimizer_steps,
        "tokens_seen": meaningful_tokens_seen,
        "meaningful_tokens_seen": meaningful_tokens_seen,
        "config": {
            "vocab_size": config.vocab_size,
            "context_length": config.context_length,
            "embed_dim": config.embed_dim,
            "num_layers": config.num_layers,
            "num_heads": config.num_heads,
            "hidden_dim": config.hidden_dim,
        },
        "tokenizer_path": portable_path_string(tokenizer_path),
        "tokenizer_sha256": training_data.get("tokenizer_sha256"),
        "vocab_size": vocab_size,
        "dataset_version": training_data.get("dataset_version"),
        "dataset_manifest_sha256": training_data.get("manifest_sha256"),
        "dataset_file_sha256": training_file_sha256,
        "validation_dataset_manifest_sha256": (
            validation_data.get("manifest_sha256") if validation_data else None
        ),
        "validation_dataset_file_sha256": validation_file_sha256,
        "losses": losses,
        "validation_losses": validation_losses,
        "loss": loss,
        "accumulation_steps": accumulation_steps,
        "mixed_precision": mixed_precision,
        "seed": seed,
        "parent_checkpoint": str(parent_checkpoint) if parent_checkpoint else None,
        "hardware_info": {
            "device": str(device),
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "wall_time_s": time.time() - start_time,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("datasets/processed/train.pkl"))
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--resume", type=Path, default=None)
    parser.add_argument("--accumulation-steps", type=int, default=1)
    parser.add_argument("--mixed-precision", action="store_true", default=False)
    args = parser.parse_args()
    train(
        data_path=args.data, steps=args.steps, batch_size=args.batch_size,
        lr=args.lr, resume_from=args.resume,
        accumulation_steps=args.accumulation_steps,
        mixed_precision=args.mixed_precision,
    )
