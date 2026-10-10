from __future__ import annotations

import hashlib
import pickle
import random
from pathlib import Path

import pytest
import torch
from tokenizers import Tokenizer, models, pre_tokenizers

from ml.models.transformer import Config, VeyraPrime
from ml.path_utils import portable_path_string, resolve_portable_path
from ml.training.train_loop import evaluate, train


def _samples() -> list[tuple[torch.Tensor, torch.Tensor]]:
    return [
        (torch.tensor([1, 2, 3, 4, 5, 6, 7, 8]), torch.tensor([2, 3, -1, -1, -1, -1, -1, -1])),
        (torch.tensor([2, 3, 4, 5, 6, 7, 8, 9]), torch.tensor([3, 4, 5, -1, -1, -1, -1, -1])),
        (torch.tensor([3, 4, 5, 6, 7, 8, 9, 10]), torch.tensor([4, -1, -1, -1, -1, -1, -1, -1])),
    ]


def _write_tokenizer(path: Path) -> str:
    vocabulary = {"[UNK]": 0, "</s>": 1, "<pad>": 2}
    vocabulary.update({f"token-{index}": index + 3 for index in range(13)})
    tokenizer = Tokenizer(models.WordLevel(vocabulary, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    tokenizer.save(str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_dataset(path: Path, split: str, documents: list[str],
                   tokenizer_path: Path, tokenizer_hash: str) -> None:
    payload = {
        "samples": _samples(),
        "split": split,
        "context_length": 8,
        "vocab_size": 16,
        "tokenizer_path": str(tokenizer_path),
        "tokenizer_sha256": tokenizer_hash,
        "manifest_sha256": f"{split}-manifest",
        "documents": [{"normalized_content_sha256": digest} for digest in documents],
    }
    with path.open("wb") as output:
        pickle.dump(payload, output)


def _write_checkpoint(
    path: Path,
    tokenizer_path: Path,
    tokenizer_hash: str,
    *,
    checkpoint_tokenizer_hash: str | None = None,
) -> VeyraPrime:
    config = Config(vocab_size=16, context_length=8, embed_dim=16,
                    num_layers=1, num_heads=2, hidden_dim=32, dropout=0.3)
    model = VeyraPrime(config)
    torch.save({
        "model_state_dict": model.state_dict(),
        "config": {
            "vocab_size": config.vocab_size,
            "context_length": config.context_length,
            "embed_dim": config.embed_dim,
            "num_layers": config.num_layers,
            "num_heads": config.num_heads,
            "hidden_dim": config.hidden_dim,
        },
        "tokenizer_path": str(tokenizer_path),
        "tokenizer_sha256": checkpoint_tokenizer_hash or tokenizer_hash,
    }, path)
    return model


def test_portable_paths_resolve_windows_separators_and_store_project_relative(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tokenizer_path = Path("datasets/processed/tokenizer.json")
    tokenizer_path.parent.mkdir(parents=True)
    tokenizer_path.write_text("tokenizer", encoding="utf-8")
    windows_style_path = r"datasets\processed\tokenizer.json"

    assert resolve_portable_path(windows_style_path).resolve() == tokenizer_path.resolve()
    assert portable_path_string(windows_style_path) == "datasets/processed/tokenizer.json"


def test_validation_uses_eval_mode_no_grad_and_preserves_weights_and_mode():
    model = VeyraPrime(Config(vocab_size=16, context_length=8, embed_dim=16,
                              num_layers=1, num_heads=2, hidden_dim=32, dropout=0.5))
    model.train()
    before = {name: value.detach().clone() for name, value in model.state_dict().items()}
    original_compute_loss = model.compute_loss
    observed_calls = 0

    def verify_eval_contract(batch):
        nonlocal observed_calls
        observed_calls += 1
        assert model.training is False
        assert torch.is_grad_enabled() is False
        return original_compute_loss(batch)

    model.compute_loss = verify_eval_contract
    loss = evaluate(model, _samples(), device=torch.device("cpu"), batch_size=1)

    assert loss > 0
    assert observed_calls == len(_samples())
    assert model.training is True
    assert all(torch.equal(before[name], after) for name, after in model.state_dict().items())


def test_validation_loss_is_weighted_by_nonignored_target_tokens():
    model = VeyraPrime(Config(vocab_size=16, context_length=8, embed_dim=16,
                              num_layers=1, num_heads=2, hidden_dim=32, dropout=0.4))
    samples = _samples()[:2]
    model.eval()
    with torch.no_grad():
        losses = [
            model.compute_loss((x.unsqueeze(0), y.unsqueeze(0))).item()
            for x, y in samples
        ]
    weights = [int((y != -1).sum().item()) for _, y in samples]
    expected = sum(loss * count for loss, count in zip(losses, weights)) / sum(weights)

    assert evaluate(model, samples, device=torch.device("cpu")) == pytest.approx(expected)


def test_train_counts_only_supervised_targets_validates_and_saves_exclusively(tmp_path, monkeypatch):
    train_path = tmp_path / "train.pkl"
    val_path = tmp_path / "val.pkl"
    tokenizer_path = tmp_path / "datasets" / "processed" / "tokenizer.json"
    tokenizer_path.parent.mkdir(parents=True)
    tokenizer_hash = _write_tokenizer(tokenizer_path)
    _write_dataset(train_path, "train", ["train-a", "train-b"], tokenizer_path, tokenizer_hash)
    _write_dataset(val_path, "val", ["val-a"], tokenizer_path, tokenizer_hash)
    checkpoint = tmp_path / "parent.pt"
    _write_checkpoint(checkpoint, tokenizer_path, tokenizer_hash)
    windows_style_tokenizer_path = r"datasets\processed\tokenizer.json"
    for dataset_path in (train_path, val_path):
        with dataset_path.open("rb") as source:
            dataset = pickle.load(source)
        dataset["tokenizer_path"] = windows_style_tokenizer_path
        with dataset_path.open("wb") as destination:
            pickle.dump(dataset, destination)
    checkpoint_state = torch.load(checkpoint, weights_only=True, map_location="cpu")
    checkpoint_state["tokenizer_path"] = windows_style_tokenizer_path
    torch.save(checkpoint_state, checkpoint)
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "candidate"
    monkeypatch.setattr("ml.training.train_loop.DEVICE", torch.device("cpu"))
    seed = 7
    batch_size = 2
    accumulation_steps = 2
    selection = random.Random(seed)
    expected_tokens = 0
    samples = _samples()
    for _ in range(batch_size * accumulation_steps):
        expected_tokens += int((samples[selection.randrange(len(samples))][1] != -1).sum().item())

    result_path, model, losses = train(
        model_path=checkpoint,
        data_path=train_path,
        output_dir=output_dir,
        val_data_path=val_path,
        steps=1,
        batch_size=batch_size,
        accumulation_steps=accumulation_steps,
        checkpoint_interval=1,
        validation_interval=1,
        lr=1e-3,
        seed=seed,
    )

    assert result_path == output_dir / "checkpoint_final.pt"
    assert (output_dir / "checkpoint_step_1.pt").is_file()
    assert len(losses) == 1
    assert model.training is True
    state = torch.load(result_path, weights_only=True, map_location="cpu")
    assert state["meaningful_tokens_seen"] == expected_tokens
    assert state["tokens_seen"] == expected_tokens
    assert state["parent_checkpoint"] == str(checkpoint)
    assert state["tokenizer_path"] == "datasets/processed/tokenizer.json"
    assert state["validation_losses"][0]["step"] == 1
    assert state["validation_losses"][0]["loss"] > 0
    assert state["validation_dataset_file_sha256"] == hashlib.sha256(val_path.read_bytes()).hexdigest()

    checkpoint_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        train(
            model_path=checkpoint,
            data_path=train_path,
            output_dir=output_dir,
            val_data_path=val_path,
            steps=1,
            batch_size=batch_size,
            checkpoint_interval=1,
            seed=seed,
        )
    assert hashlib.sha256(result_path.read_bytes()).hexdigest() == checkpoint_hash


def test_train_rejects_split_leakage_and_checkpoint_tokenizer_mismatch(tmp_path, monkeypatch):
    train_path = tmp_path / "train.pkl"
    val_path = tmp_path / "val.pkl"
    tokenizer_path = tmp_path / "tokenizer.json"
    tokenizer_hash = _write_tokenizer(tokenizer_path)
    _write_dataset(train_path, "train", ["overlap"], tokenizer_path, tokenizer_hash)
    _write_dataset(val_path, "val", ["overlap"], tokenizer_path, tokenizer_hash)
    checkpoint = tmp_path / "parent.pt"
    _write_checkpoint(checkpoint, tokenizer_path, tokenizer_hash)
    monkeypatch.setattr("ml.training.train_loop.DEVICE", torch.device("cpu"))

    with pytest.raises(ValueError, match="overlapping documents"):
        train(model_path=checkpoint, data_path=train_path, val_data_path=val_path,
              output_dir=tmp_path / "candidate", steps=1)

    _write_dataset(val_path, "val", ["held-out"], tokenizer_path, tokenizer_hash)
    mismatched_checkpoint = tmp_path / "mismatched.pt"
    another_tokenizer = tmp_path / "another-tokenizer.json"
    another_hash = _write_tokenizer(another_tokenizer)
    _write_checkpoint(mismatched_checkpoint, another_tokenizer, another_hash)
    with pytest.raises(ValueError, match="tokenizer path"):
        train(model_path=mismatched_checkpoint, data_path=train_path, val_data_path=val_path,
              output_dir=tmp_path / "candidate", steps=1)

    mismatched_hash_checkpoint = tmp_path / "mismatched-hash.pt"
    _write_checkpoint(
        mismatched_hash_checkpoint,
        tokenizer_path,
        tokenizer_hash,
        checkpoint_tokenizer_hash="not-the-tokenizer-hash",
    )
    with pytest.raises(ValueError, match="tokenizer hash"):
        train(model_path=mismatched_hash_checkpoint, data_path=train_path,
              val_data_path=val_path, output_dir=tmp_path / "candidate-hash", steps=1)
