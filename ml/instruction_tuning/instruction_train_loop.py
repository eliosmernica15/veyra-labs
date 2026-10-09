#!/usr/bin/env python3
"""Local CPU instruction fine-tuning using response-masked next-token targets."""
from __future__ import annotations

import argparse
import hashlib
import logging
import pickle
import time
from pathlib import Path

import torch
from torch.optim import AdamW

from ml.models.transformer import Config, VeyraPrime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("veyra.instruction")
DEVICE = torch.device("cpu")


def _load_dataset(path: Path, *, expected_split: str, vocab_size: int, context_length: int):
    with path.open("rb") as data_file:
        dataset = pickle.load(data_file)
    if dataset.get("split") != expected_split:
        raise ValueError(f"{path} must declare split={expected_split!r}")
    if dataset.get("label_ignore_index") != -1:
        raise ValueError(f"{path} must use -1 for ignored target labels")
    if dataset.get("tokenizer_vocab_size") != vocab_size:
        raise ValueError(f"{path} tokenizer vocabulary does not match checkpoint ({vocab_size})")
    if dataset.get("context_length") != context_length:
        raise ValueError(f"{path} context length does not match checkpoint ({context_length})")
    eos_token_id = dataset.get("eos_token_id")
    if not isinstance(eos_token_id, int) or not 0 <= eos_token_id < vocab_size:
        raise ValueError(f"{path} has an invalid EOS token ID")
    samples = dataset.get("samples")
    if not samples:
        raise ValueError(f"{path} contains no samples")
    for index, sample in enumerate(samples):
        if not isinstance(sample, (tuple, list)) or len(sample) != 2:
            raise ValueError(f"{path} sample {index} must be an (input, target) pair")
        x, y = sample
        if not isinstance(x, torch.Tensor) or not isinstance(y, torch.Tensor):
            raise ValueError(f"{path} sample {index} must contain tensors")
        if x.ndim != 1 or y.ndim != 1 or x.shape != y.shape or x.numel() != context_length:
            raise ValueError(f"{path} sample {index} must have matching 1D tensors of length {context_length}")
        if not torch.any((y != -1) & (y != eos_token_id)):
            raise ValueError(f"{path} sample {index} has no supervised non-EOS response targets")
        if torch.any((x < 0) | (x >= vocab_size)) or torch.any((y != -1) & ((y < 0) | (y >= vocab_size))):
            raise ValueError(f"{path} sample {index} contains token IDs outside the checkpoint vocabulary")
    return dataset


def train_instruct(
    checkpoint_path: Path = Path("checkpoints/veyra004_pretrain_v5/checkpoint_final.pt"),
    data_path: Path = Path("datasets/processed/instruction_train.pkl"),
    val_path: Path = Path("datasets/processed/instruction_val.pkl"),
    output_dir: Path = Path("checkpoints/veyra004_instruction_candidate"),
    steps: int = 15,
    batch_size: int = 2,
    lr: float = 5e-4,
    weight_decay: float = 0.01,
    grad_clip: float = 1.0,
    checkpoint_interval: int = 5,
    seed: int = 42,
):
    if steps <= 0 or batch_size <= 0 or checkpoint_interval <= 0:
        raise ValueError("steps, batch_size, and checkpoint_interval must be positive")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite existing instruction candidate files in {output_dir}")
    if grad_clip <= 0:
        raise ValueError("grad_clip must be positive")

    torch.manual_seed(seed)
    state = torch.load(str(checkpoint_path), weights_only=True, map_location="cpu")
    config_data = state.get("config")
    if not isinstance(config_data, dict):
        raise ValueError(f"Checkpoint {checkpoint_path} has no model configuration")
    config = Config(**{
        key: config_data[key]
        for key in ("vocab_size", "context_length", "embed_dim", "num_layers", "num_heads", "hidden_dim")
    })
    train_data = _load_dataset(data_path, expected_split="train",
                               vocab_size=config.vocab_size, context_length=config.context_length)
    val_data = _load_dataset(val_path, expected_split="val",
                             vocab_size=config.vocab_size, context_length=config.context_length)
    if train_data["tokenizer_path"] != val_data["tokenizer_path"]:
        raise ValueError("Training and validation datasets must use the same tokenizer")
    checkpoint_tokenizer = state.get("tokenizer_path")
    if not checkpoint_tokenizer or Path(checkpoint_tokenizer).resolve() != Path(train_data["tokenizer_path"]).resolve():
        raise ValueError("Instruction datasets must use the checkpoint's exact tokenizer")
    tokenizer_sha256 = hashlib.sha256(Path(train_data["tokenizer_path"]).read_bytes()).hexdigest()
    if train_data.get("tokenizer_sha256") != tokenizer_sha256 or val_data.get("tokenizer_sha256") != tokenizer_sha256:
        raise ValueError("Instruction dataset tokenizer hash does not match the current tokenizer file")
    if train_data["input_sha256"] != val_data["input_sha256"]:
        raise ValueError("Training and validation datasets must come from the same source file")
    if set(train_data["instruction_group_hashes"]) & set(val_data["instruction_group_hashes"]):
        raise ValueError("Training and validation splits contain the same instruction prompt")

    model = VeyraPrime(config)
    model.load_state_dict(state["model_state_dict"], strict=True)
    model.to(DEVICE)
    del state
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    train_samples = train_data["samples"]
    val_samples = val_data["samples"]
    output_dir.mkdir(parents=True, exist_ok=True)
    losses: list[float] = []
    val_losses: list[float] = []
    supervised_tokens_seen = 0
    start_time = time.time()
    model.train()

    for step in range(steps):
        indices = torch.randint(len(train_samples), (batch_size,)).tolist()
        x_batch = torch.stack([train_samples[index][0] for index in indices]).to(DEVICE)
        y_batch = torch.stack([train_samples[index][1] for index in indices]).to(DEVICE)
        optimizer.zero_grad(set_to_none=True)
        loss = model.compute_loss((x_batch, y_batch))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        optimizer.step()
        losses.append(float(loss.item()))
        supervised_tokens_seen += int((y_batch != -1).sum().item())
        logger.info("IT step %s/%s — loss %.6f — supervised tokens %s",
                    step + 1, steps, losses[-1], supervised_tokens_seen)

        if (step + 1) % 5 == 0:
            model.eval()
            with torch.no_grad():
                val_losses.append(float(torch.stack([
                    model.compute_loss((sample[0].unsqueeze(0), sample[1].unsqueeze(0)))
                    for sample in val_samples
                ]).mean().item()))
            model.train()
            logger.info("Validation step %s — loss %.6f", step + 1, val_losses[-1])

        if (step + 1) % checkpoint_interval == 0:
            _save_candidate(output_dir / f"instruction_step_{step + 1}.pt", model, optimizer, config,
                            step + 1, train_data, losses, val_losses, supervised_tokens_seen, start_time, seed)

    final_path = output_dir / "instruction_final.pt"
    _save_candidate(final_path, model, optimizer, config, steps, train_data,
                    losses, val_losses, supervised_tokens_seen, start_time, seed)
    return final_path, model, losses, val_losses


def _save_candidate(path, model, optimizer, config, step, train_data, losses, val_losses,
                    supervised_tokens_seen, start_time, seed):
    state = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "step": step,
        "optimizer_steps": step,
        "supervised_tokens_seen": supervised_tokens_seen,
        "config": {
            "vocab_size": config.vocab_size,
            "context_length": config.context_length,
            "embed_dim": config.embed_dim,
            "num_layers": config.num_layers,
            "num_heads": config.num_heads,
            "hidden_dim": config.hidden_dim,
        },
        "tokenizer_path": train_data["tokenizer_path"],
        "dataset_version": train_data["dataset_version"],
        "dataset_input_sha256": train_data["input_sha256"],
        "seed": seed,
        "model_id": "Veyra-004-IT-candidate",
        "parent_checkpoint": "veyra004_pretrain_v5",
        "training_config": {"optimizer": "AdamW", "lr": optimizer.param_groups[0]["lr"],
                            "device": "cpu", "loss_mask": "response_tokens_and_eos_only"},
        "losses": losses,
        "val_losses": val_losses,
        "wall_time_s": time.time() - start_time,
    }
    with path.open("xb") as output_file:
        torch.save(state, output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=Path("checkpoints/veyra004_pretrain_v5/checkpoint_final.pt"))
    parser.add_argument("--data", type=Path, default=Path("datasets/processed/instruction_train.pkl"))
    parser.add_argument("--val", type=Path, default=Path("datasets/processed/instruction_val.pkl"))
    parser.add_argument("--output-dir", type=Path, default=Path("checkpoints/veyra004_instruction_candidate"))
    parser.add_argument("--steps", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--checkpoint-interval", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    train_instruct(
        checkpoint_path=args.checkpoint,
        data_path=args.data,
        val_path=args.val,
        output_dir=args.output_dir,
        steps=args.steps,
        batch_size=args.batch_size,
        lr=args.lr,
        checkpoint_interval=args.checkpoint_interval,
        seed=args.seed,
    )
