from __future__ import annotations

from datetime import date
import json
import pickle
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import torch
from tokenizers import Tokenizer

from ml.data.prepare_licensed_corpus import prepare_corpus
from ml.inference.generate import generate_text
from ml.instruction_tuning.prepare_instruction_data import _encode_sample, prepare
from ml.instruction_tuning.instruction_train_loop import train_instruct
from ml.models.transformer import Config, VeyraPrime
from services.api import main as api

TOKENIZER_PATH = Path("datasets/processed/tokenizer_veyra004.json")


def _instruction_record(index: int) -> dict[str, Any]:
    return {
        "instruction": f"Explain distinct topic {index}",
        "response": f"Topic {index} has a clear, independently authored explanation.",
        "source": "unit-test fixture authored in test",
        "source_url": "https://example.org/fixture",
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": "Test fixture author",
        "rights_basis": "Original text authored in this test",
        "source_version": "fixture-v1",
        "acquisition_date": date.today().isoformat(),
        "rights_verified": True,
        "target_provenance": "human_authored",
    }


def test_response_only_targets_are_shifted_once_and_padding_is_ignored():
    tokenizer = Tokenizer.from_file(str(TOKENIZER_PATH))
    eos = tokenizer.token_to_id("</s>")
    pad = tokenizer.token_to_id("<pad>")
    x, y = _encode_sample(tokenizer, "What is a test?", "A test checks behavior.", 64, eos, pad)

    prefix = "Instruction: What is a test?\nResponse:"
    encoding = tokenizer.encode(f"{prefix} A test checks behavior.", add_special_tokens=False)
    response_start = len(prefix) + 1
    response_targets = [
        token_id for token_id, (_, end) in zip(encoding.ids, encoding.offsets)
        if end > response_start
    ]
    assert len(x) == len(y) == 64
    y_values = y.tolist()
    assert y_values.count(eos) == 1
    assert y_values.count(-1) > 0
    assert all(token == -1 or 0 <= token < tokenizer.get_vocab_size() for token in y_values)
    active = [token for token in y_values if token != -1]
    assert active == response_targets + [eos]


def test_instruction_preparation_splits_unique_prompts_and_refuses_overwrite(tmp_path):
    source = tmp_path / "instructions.jsonl"
    rows = [_instruction_record(index) for index in range(8)]
    rows.append(rows[0])
    source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    train_path, val_path, test_path = (
        tmp_path / "train.pkl", tmp_path / "val.pkl", tmp_path / "test.pkl"
    )

    prepare(source, train_path, tokenizer_path=TOKENIZER_PATH, val_output_path=val_path,
            test_output_path=test_path, context_length=64)

    datasets = []
    for path, split in ((train_path, "train"), (val_path, "val"), (test_path, "test")):
        with path.open("rb") as data_file:
            dataset = pickle.load(data_file)
        assert dataset["split"] == split
        assert dataset["target_policy"] == "response_tokens_and_eos_only"
        assert dataset["sources"]
        assert dataset["input_record_count"] == 9
        assert dataset["duplicate_record_count"] == 1
        assert all(x.shape == y.shape == (64,) for x, y in dataset["samples"])
        datasets.append(dataset)
    assert len(datasets) == 3
    prompt_groups = [set(dataset["instruction_group_hashes"]) for dataset in datasets]
    assert not (prompt_groups[0] & prompt_groups[1] or
                prompt_groups[0] & prompt_groups[2] or
                prompt_groups[1] & prompt_groups[2])
    with pytest.raises(FileExistsError):
        prepare(source, train_path, tokenizer_path=TOKENIZER_PATH, val_output_path=val_path,
                test_output_path=test_path, context_length=64)


def test_instruction_preparation_rejects_unverified_or_nonhuman_targets(tmp_path):
    source = tmp_path / "instructions.jsonl"
    rows = [_instruction_record(index) for index in range(8)]
    rows[0]["rights_verified"] = False
    source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    with pytest.raises(ValueError, match="rights_verified must be true"):
        prepare(source, tmp_path / "train.pkl", tokenizer_path=TOKENIZER_PATH,
                val_output_path=tmp_path / "val.pkl", test_output_path=tmp_path / "test.pkl",
                context_length=64)

    rows[0]["rights_verified"] = True
    rows[0]["target_provenance"] = "external_model"
    source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="target_provenance"):
        prepare(source, tmp_path / "train.pkl", tokenizer_path=TOKENIZER_PATH,
                val_output_path=tmp_path / "val.pkl", test_output_path=tmp_path / "test.pkl",
                context_length=64)


def test_masked_instruction_training_loads_paired_checkpoint_and_saves_new_candidate(tmp_path):
    source = tmp_path / "instructions.jsonl"
    source.write_text(
        "".join(json.dumps(_instruction_record(index)) + "\n" for index in range(8)),
        encoding="utf-8",
    )
    train_path, val_path, test_path = (
        tmp_path / "train.pkl", tmp_path / "val.pkl", tmp_path / "test.pkl"
    )
    prepare(source, train_path, tokenizer_path=TOKENIZER_PATH, val_output_path=val_path,
            test_output_path=test_path, context_length=64)

    config = Config(vocab_size=4096, context_length=64, embed_dim=16,
                    num_layers=1, num_heads=2, hidden_dim=32)
    checkpoint_path = tmp_path / "base.pt"
    torch.save({
        "model_state_dict": VeyraPrime(config).state_dict(),
        "config": {
            "vocab_size": config.vocab_size,
            "context_length": config.context_length,
            "embed_dim": config.embed_dim,
            "num_layers": config.num_layers,
            "num_heads": config.num_heads,
            "hidden_dim": config.hidden_dim,
        },
        "tokenizer_path": str(TOKENIZER_PATH),
    }, checkpoint_path)

    output_dir = tmp_path / "candidate"
    final_path, _, losses, val_losses = train_instruct(
        checkpoint_path=checkpoint_path,
        data_path=train_path,
        val_path=val_path,
        output_dir=output_dir,
        steps=5,
        batch_size=2,
        checkpoint_interval=5,
        seed=9,
    )
    assert final_path.exists()
    assert (output_dir / "instruction_step_5.pt").exists()
    assert len(losses) == 5
    assert len(val_losses) == 1


def test_compute_loss_uses_only_aligned_non_ignored_targets_and_backpropagates():
    model = VeyraPrime(Config(vocab_size=32, context_length=8, embed_dim=16,
                              num_layers=1, num_heads=2, hidden_dim=32))
    model.eval()
    x = torch.tensor([[1, 2, 3, 4]])
    y = torch.tensor([[-1, 5, 6, -1]])
    logits = model(x)
    expected = torch.nn.functional.cross_entropy(logits[0, 1:3], y[0, 1:3])

    loss = model.compute_loss((x, y))
    assert torch.allclose(loss, expected)
    loss.backward()
    assert model.tok_embed.weight.grad is not None
    assert torch.count_nonzero(model.tok_embed.weight.grad).item() > 0

    with pytest.raises(ValueError, match="shapes must match"):
        model.compute_loss((x, y[:, :-1]))
    with pytest.raises(ValueError, match="non-ignored"):
        model.compute_loss((x, torch.full_like(x, -1)))


def test_generate_stops_at_eos(monkeypatch):
    model = VeyraPrime(Config(vocab_size=32, context_length=8, embed_dim=16,
                              num_layers=1, num_heads=2, hidden_dim=32))

    def eos_only_logits(idx):
        logits = torch.zeros((idx.shape[0], idx.shape[1], 32))
        logits[..., 0] = 20
        return logits

    monkeypatch.setattr(model, "forward", eos_only_logits)
    result = model.generate(torch.tensor([[2, 3]]), max_new_tokens=5, top_k=1,
                            eos_token_id=0, pad_token_id=1)
    assert result.tolist() == [[2, 3, 0]]


def test_generate_text_uses_checkpoint_tokenizer_without_prompt_eos(monkeypatch):
    tokenizer = Tokenizer.from_file(str(TOKENIZER_PATH))

    class CapturingModel:
        input_ids = None
        generation_options = None
        was_set_to_eval = False

        def eval(self):
            self.was_set_to_eval = True

        def generate(self, input_ids, **options):
            self.input_ids = input_ids.clone()
            self.generation_options = options
            return input_ids

    model = CapturingModel()
    state = {"step": 100, "tokenizer_path": str(TOKENIZER_PATH)}
    config = SimpleNamespace(vocab_size=tokenizer.get_vocab_size(), context_length=512)
    monkeypatch.setattr("ml.inference.generate.load_checkpoint",
                        lambda _path: (model, state, config))
    monkeypatch.setattr("ml.inference.generate.load_tokenizer", lambda _path: tokenizer)

    generate_text(Path("checkpoint.pt"), prompt="hi how are you")

    expected_ids = tokenizer.encode("hi how are you", add_special_tokens=False).ids
    assert model.input_ids.tolist() == [expected_ids]
    assert model.generation_options["eos_token_id"] == tokenizer.token_to_id("</s>")
    assert model.generation_options["pad_token_id"] == tokenizer.token_to_id("<pad>")
    assert model.was_set_to_eval


def test_api_generation_uses_checkpoint_tokenizer_and_eos_handling(tmp_path, monkeypatch):
    tokenizer = Tokenizer.from_file(str(TOKENIZER_PATH))

    class CapturingModel:
        input_ids = None
        generation_options = None
        was_set_to_eval = False

        def eval(self):
            self.was_set_to_eval = True

        def generate(self, input_ids, **options):
            self.input_ids = input_ids.clone()
            self.generation_options = options
            return input_ids

    model = CapturingModel()
    config = SimpleNamespace(vocab_size=tokenizer.get_vocab_size(), context_length=512)
    checkpoint_file = tmp_path / "checkpoint_final.pt"
    checkpoint_file.touch()
    monkeypatch.setattr(api, "CHECKPOINT_DIR", tmp_path)
    monkeypatch.setattr(api, "load_checkpoint",
                        lambda _path: (model, {"step": 100, "tokenizer_path": str(TOKENIZER_PATH)}, config))
    monkeypatch.setattr(api, "load_tokenizer", lambda _path: tokenizer)
    monkeypatch.delenv("VEYRA_TOKENIZER_PATH", raising=False)

    result = api.generate(api.GenerateRequest(prompt="hi how are you"))

    expected_ids = tokenizer.encode("hi how are you", add_special_tokens=False).ids
    assert result["step"] == 100
    assert model.input_ids.tolist() == [expected_ids]
    assert model.generation_options["eos_token_id"] == tokenizer.token_to_id("</s>")
    assert model.generation_options["pad_token_id"] == tokenizer.token_to_id("<pad>")
    assert model.was_set_to_eval


def _licensed_document(index: int) -> str:
    return (
        f"Document {index} describes careful observation, clear reasoning, and evidence. "
        "Readers compare measurements, record results, and explain how conclusions follow "
        "from the facts that were gathered during the investigation. "
    ) * 3


def test_licensed_corpus_builds_disjoint_reproducible_splits(tmp_path):
    doc_dir = tmp_path / "documents"
    doc_dir.mkdir()
    entries = []
    for index in range(6):
        filename = f"doc-{index}.txt"
        (doc_dir / filename).write_text(_licensed_document(index), encoding="utf-8")
        entries.append({
            "path": f"documents/{filename}",
            "title": f"Fixture document {index}",
            "source_url": f"https://example.org/fixture/{index}",
            "license": "CC0-1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "license_evidence_url": f"https://example.org/fixture/{index}/license",
            "attribution": "Unit-test fixture",
            "source_version": "fixture-v1",
            "rights_basis": "Test-only fixture content",
            "rights_verified": True,
        })
    duplicate_entry = dict(entries[0])
    duplicate_entry["path"] = "documents/doc-0.txt"
    entries.append(duplicate_entry)
    short_entry = dict(entries[0])
    short_entry.update({"path": "documents/short.txt", "title": "Too short"})
    (doc_dir / "short.txt").write_text("Too short.", encoding="utf-8")
    entries.append(short_entry)
    malformed_entry = dict(entries[0])
    malformed_entry.update({"path": "documents/malformed.txt", "title": "Malformed UTF-8"})
    (doc_dir / "malformed.txt").write_bytes(b"\xff")
    entries.append(malformed_entry)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "dataset_version": "fixture-v1",
        "acquisition_date": date.today().isoformat(),
        "documents": entries,
    }), encoding="utf-8")
    outputs = prepare_corpus(manifest, TOKENIZER_PATH, tmp_path / "out",
                             context_length=32, seed=7)

    hashes = []
    first_run = {}
    for split in ("train", "val", "test"):
        with outputs[split].open("rb") as data_file:
            dataset = pickle.load(data_file)
        hashes.append({document["source_sha256"] for document in dataset["documents"]})
        first_run[split] = dataset
        assert dataset["split"] == split
        assert dataset["dataset_version"] == "fixture-v1"
        assert dataset["acquisition_date"] == date.today().isoformat()
        assert dataset["duplicate_document_count"] == 1
        assert dataset["excluded_document_count"] == 3
        assert {item["reason"] for item in dataset["excluded_documents"]} == {
            "duplicate_normalized_content", "fewer_than_20_words", "invalid_utf8",
        }
        assert dataset["samples"]
        assert all(document["rights_verified"] for document in dataset["documents"])
        assert all(document["token_count"] > 0 for document in dataset["documents"])
        assert all(document["source_sha256"] and document["license_url"]
                   and document["source_version"] for document in dataset["documents"])
        assert dataset["cleaning_rules"] and dataset["deduplication_rule"]
        assert all(x.shape == y.shape == (32,) for x, y in dataset["samples"])
    assert not (hashes[0] & hashes[1] or hashes[0] & hashes[2] or hashes[1] & hashes[2])
    repeated_outputs = prepare_corpus(manifest, TOKENIZER_PATH, tmp_path / "out_repeat",
                                      context_length=32, seed=7)
    for split, path in repeated_outputs.items():
        with path.open("rb") as data_file:
            repeated = pickle.load(data_file)
        assert [doc["source_sha256"] for doc in repeated["documents"]] == [
            doc["source_sha256"] for doc in first_run[split]["documents"]
        ]
        assert repeated["token_count"] == first_run[split]["token_count"]
        assert all(torch.equal(a[0], b[0]) and torch.equal(a[1], b[1])
                   for a, b in zip(repeated["samples"], first_run[split]["samples"]))
    with pytest.raises(FileExistsError):
        prepare_corpus(manifest, TOKENIZER_PATH, tmp_path / "out",
                       context_length=32, seed=7)


def test_licensed_corpus_rejects_unverified_rights(tmp_path):
    doc_dir = tmp_path / "documents"
    doc_dir.mkdir()
    entries = []
    for index in range(3):
        filename = f"doc-{index}.txt"
        (doc_dir / filename).write_text(_licensed_document(index), encoding="utf-8")
        entries.append({
            "path": f"documents/{filename}",
            "title": f"Fixture document {index}",
            "source_url": f"https://example.org/fixture/{index}",
            "license": "CC0-1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "license_evidence_url": f"https://example.org/fixture/{index}/license",
            "attribution": "Unit-test fixture",
            "source_version": "fixture-v1",
            "rights_basis": "Test-only fixture content",
            "rights_verified": False,
        })
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "dataset_version": "fixture-v1",
        "acquisition_date": date.today().isoformat(),
        "documents": entries,
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="rights_verified=true"):
        prepare_corpus(manifest, TOKENIZER_PATH, tmp_path / "out", context_length=32)


def test_licensed_corpus_rejects_mismatched_license_url(tmp_path):
    doc_dir = tmp_path / "documents"
    doc_dir.mkdir()
    entries = []
    for index in range(3):
        filename = f"doc-{index}.txt"
        (doc_dir / filename).write_text(_licensed_document(index), encoding="utf-8")
        entries.append({
            "path": f"documents/{filename}",
            "title": f"Fixture document {index}",
            "source_url": f"https://example.org/fixture/{index}",
            "license": "CC0-1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "license_evidence_url": f"https://example.org/fixture/{index}/license",
            "attribution": "Unit-test fixture",
            "source_version": "fixture-v1",
            "rights_basis": "Test-only fixture content",
            "rights_verified": True,
        })
    entries[0]["license_url"] = "https://example.org/unknown-license"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "dataset_version": "fixture-v1",
        "acquisition_date": date.today().isoformat(),
        "documents": entries,
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="does not match CC0-1.0"):
        prepare_corpus(manifest, TOKENIZER_PATH, tmp_path / "out", context_length=32)
