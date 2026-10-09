#!/usr/bin/env python3
"""Local CPU instruction fine-tuning (Phase 10) — supervised, real optimization, $0."""
from __future__ import annotations
import time, logging, pickle, os
from pathlib import Path
import torch
from torch.optim import AdamW
import sys, time, logging, pickle, os
from pathlib import Path
sys.path.insert(0,'.')
from ml.models.transformer import VeyraPrime, Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("veyra.instruction")
DEVICE = torch.device("cpu")

def train_instruct(
    checkpoint_path: Path = Path("checkpoints/veyra001_smoke.pt"),
    data_path: Path = Path("datasets/processed/instruction_train.pkl"),
    val_path: Path = Path("datasets/processed/instruction_val.pkl"),
    output_dir: Path = Path("checkpoints/veyra001_it"),
    steps: int = 15,
    batch_size: int = 2,
    lr: float = 5e-4,
    weight_decay: float = 0.01,
    grad_clip: float = 1.0,
    checkpoint_interval: int = 5,
    resume_from: Path | None = None,
):
    # Load pretrained base (Veyra-001 smoke — verified 3.24M params, step 5)
    state = torch.load(str(checkpoint_path), weights_only=False, map_location="cpu")
    config = Config(vocab_size=state["config"]["vocab_size"],
                    context_length=state["config"]["context_length"],
                    embed_dim=state["config"]["embed_dim"],
                    num_layers=state["config"]["num_layers"],
                    num_heads=state["config"]["num_heads"],
                    hidden_dim=state["config"]["hidden_dim"])
    model = VeyraPrime(config)
    model.load_state_dict(state["model_state_dict"])
    model.to(DEVICE)
    model.train()

    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    optimizer.load_state_dict(state.get("optimizer_state_dict", optimizer.state_dict()))
    completed_steps = state.get("step", 0)

    # Load instruction data
    with open(data_path, "rb") as f:
        train_data = pickle.load(f)
    with open(val_path, "rb") as f:
        val_data = pickle.load(f)
    train_samples = train_data["samples"]
    val_samples = val_data["samples"]

    start_time = time.time()
    losses = []
    val_losses = []
    tokens_seen = state.get("tokens_seen", 0)
    total_optimizer_steps = state.get("optimizer_steps", 0)

    for step in range(completed_steps, completed_steps + steps):
        # Simple batch
        batch_samples = [train_samples[i % len(train_samples)] for i in range(batch_size)]
        x_batch = torch.stack([s[0] for s in batch_samples])
        y_batch = torch.stack([s[1] for s in batch_samples])
        x_batch = x_batch.to(DEVICE)
        y_batch = y_batch.to(DEVICE)

        optimizer.zero_grad()
        loss = model.compute_loss((x_batch, y_batch))
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        optimizer.step()

        losses.append(loss.item())
        tokens_seen += batch_size * x_batch.size(1)
        total_optimizer_steps += 1
        if (step + 1) % max(1, steps // 5) == 0 or step == completed_steps:
            elapsed = time.time() - start_time
            logger.info(f"IT Step {step+1} — loss: {loss.item():.4f} — tokens: {tokens_seen} — optimizer_steps: {total_optimizer_steps} — elapsed: {elapsed:.1f}s")

        # Validation every 5 steps (independent of training)
        if (step + 1) % 5 == 0:
            model.eval()
            val_loss_sum = 0.0
            val_n = 0
            with torch.no_grad():
                for s in val_samples[:min(4, len(val_samples))]:
                    x = s[0].unsqueeze(0).to(DEVICE)
                    y = s[1].unsqueeze(0).to(DEVICE)
                    val_loss_sum += model.compute_loss((x, y)).item()
                    val_n += 1
            avg_val = val_loss_sum / max(1, val_n)
            val_losses.append(avg_val)
            logger.info(f"Validation step {step+1} — val_loss: {avg_val:.4f}")
            model.train()

        # Checkpoint every 5 steps (frequent for session interruption)
        if (step + 1) % checkpoint_interval == 0:
            output_dir.mkdir(parents=True, exist_ok=True)
            cp_path = output_dir / f"instruction_step_{step+1}.pt"
            torch.save({
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "step": step + 1,
                "optimizer_steps": total_optimizer_steps,
                "tokens_seen": tokens_seen,
                "config": {"vocab_size": config.vocab_size, "context_length": config.context_length,
                           "embed_dim": config.embed_dim, "num_layers": config.num_layers,
                           "num_heads": config.num_heads, "hidden_dim": config.hidden_dim},
                "tokenizer_path": "datasets/processed/tokenizer_veyra001.json",
                "vocab_size": 200,
                "loss": losses[-1],
                "accumulation_steps": 1,
                "mixed_precision": False,
                "hardware_info": {"device": "cpu", "cuda_available": False, "cuda_device_name": None},
                "wall_time_s": time.time() - start_time,
                "model_id": "Veyra-001-IT",
                "model_version": "v1.0-phase10-it-2026-10-09",
                "experiment_id": "phase10-veyra001-it",
                "parent_checkpoint": "checkpoints/veyra001_smoke.pt",
                "instruction_template_version": "v1.0",
                "dataset_version": "veyra001-instruction-v1.0",
                "training_config": {"optimizer":"AdamW","lr":lr,"batch_size":batch_size,"accumulation_steps":1,"mixed_precision":False},
            }, str(cp_path))
            logger.info(f"Instruction checkpoint saved: {cp_path}")

    # Final IT checkpoint
    final_path = output_dir / "instruction_final.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "step": completed_steps + steps,
        "optimizer_steps": total_optimizer_steps,
        "tokens_seen": tokens_seen,
        "config": {"vocab_size": config.vocab_size, "context_length": config.context_length,
                   "embed_dim": config.embed_dim, "num_layers": config.num_layers,
                   "num_heads": config.num_heads, "hidden_dim": config.hidden_dim},
        "tokenizer_path": "datasets/processed/tokenizer_veyra001.json",
        "vocab_size": 200,
        "final_loss": losses[-1],
        "losses": losses,
        "val_losses": val_losses,
        "accumulation_steps": 1,
        "mixed_precision": False,
        "hardware_info": {"device":"cpu","cuda_available":False,"cuda_device_name":None},
        "wall_time_s": time.time() - start_time,
        "model_id": "Veyra-001-IT",
        "model_version": "v1.0-phase10-it-2026-10-09",
        "experiment_id": "phase10-veyra001-it",
        "parent_checkpoint": "checkpoints/veyra001_smoke.pt",
        "dataset_version": "veyra001-instruction-v1.0",
        "instruction_template_version": "v1.0",
    }, str(final_path))
    logger.info(f"Instruction tuning complete. Final: {final_path} (losses: {len(losses)}, val_evals: {len(val_losses)}, tokens: {tokens_seen}, optimizer_steps: {total_optimizer_steps})")
    return final_path, model, losses, val_losses


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=Path("checkpoints/veyra001_smoke.pt"))
    parser.add_argument("--data", type=Path, default=Path("datasets/processed/instruction_train.pkl"))
    parser.add_argument("--val", type=Path, default=Path("datasets/processed/instruction_val.pkl"))
    parser.add_argument("--output-dir", type=Path, default=Path("checkpoints/veyra001_it"))
    parser.add_argument("--steps", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--resume", type=Path, default=None)
    args = parser.parse_args()
    train_instruct(
        checkpoint_path=args.checkpoint, data_path=args.data, val_path=args.val,
        output_dir=args.output_dir, steps=args.steps, batch_size=args.batch_size, lr=args.lr,
        resume_from=args.resume,
    )
