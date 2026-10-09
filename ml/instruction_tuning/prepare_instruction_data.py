#!/usr/bin/env python3
"""Prepare response-only supervised targets from a provenance-recorded JSONL file."""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import random
from datetime import date
from pathlib import Path
from typing import Any

import torch
from tokenizers import Tokenizer

IGNORE_INDEX = -1
REQUIRED_FIELDS = (
    "instruction", "response", "source", "source_url", "license", "license_url",
    "attribution", "rights_basis", "source_version", "acquisition_date", "target_provenance",
)
LICENSE_URLS = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0",
    "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0",
}


def _load_records(input_path: Path) -> tuple[list[dict[str, Any]], str, int, int]:
    raw = input_path.read_bytes()
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    input_record_count = 0
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        input_record_count += 1
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError(f"{input_path}:{line_number}: each JSONL row must be an object")
        missing = [field for field in REQUIRED_FIELDS if not isinstance(record.get(field), str) or not record[field].strip()]
        if missing:
            raise ValueError(f"{input_path}:{line_number}: missing non-empty fields: {', '.join(missing)}")
        if record.get("rights_verified") is not True:
            raise ValueError(f"{input_path}:{line_number}: rights_verified must be true after human review")
        license_id = record["license"].strip()
        expected_license_url = LICENSE_URLS.get(license_id)
        if expected_license_url is None or record["license_url"].rstrip("/") != expected_license_url:
            raise ValueError(f"{input_path}:{line_number}: unsupported license or mismatched license_url")
        if not record["source_url"].startswith("https://"):
            raise ValueError(f"{input_path}:{line_number}: source_url must be an HTTPS URL")
        try:
            date.fromisoformat(record["acquisition_date"])
        except ValueError as exc:
            raise ValueError(f"{input_path}:{line_number}: acquisition_date must be an ISO date") from exc
        if record["target_provenance"] not in {"human_authored", "source_excerpt"}:
            raise ValueError(
                f"{input_path}:{line_number}: target_provenance must be human_authored or source_excerpt"
            )
        normalized = (" ".join(record["instruction"].split()).casefold(),
                      " ".join(record["response"].split()).casefold())
        if normalized in seen:
            continue
        seen.add(normalized)
        records.append({
            **{field: record[field].strip() for field in REQUIRED_FIELDS},
            "rights_verified": True,
        })
    if len(records) < 3:
        raise ValueError("At least three unique instruction/response pairs are required for train/val/test splits")
    return records, hashlib.sha256(raw).hexdigest(), input_record_count, input_record_count - len(records)


def _encode_sample(
    tokenizer: Tokenizer,
    instruction: str,
    response: str,
    context_length: int,
    eos_token_id: int,
    pad_token_id: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    prefix = f"Instruction: {instruction}\nResponse:"
    response_start = len(prefix) + 1
    full_text = f"{prefix} {response}"
    encoding = tokenizer.encode(full_text, add_special_tokens=False)
    token_ids = list(encoding.ids)
    if not token_ids:
        raise ValueError("Tokenizer produced no tokens for an instruction/response pair")

    labels = [IGNORE_INDEX] * len(token_ids)
    for index, (_, end) in enumerate(encoding.offsets):
        if end > response_start:
            labels[index] = token_ids[index]
    token_ids.append(eos_token_id)
    labels.append(eos_token_id)

    if not any(label not in (IGNORE_INDEX, eos_token_id) for label in labels):
        raise ValueError("Response has no token targets after tokenization")
    if len(token_ids) - 1 > context_length:
        raise ValueError(
            f"Encoded instruction/response requires {len(token_ids) - 1} input tokens; "
            f"configured context length is {context_length}"
        )

    # Shift once here: x contains the prefix through the last response token,
    # while y at each position contains the following response token (or -1).
    x = token_ids[:-1]
    y = labels[1:]
    padding = context_length - len(x)
    x.extend([pad_token_id] * padding)
    y.extend([IGNORE_INDEX] * padding)
    return torch.tensor(x, dtype=torch.long), torch.tensor(y, dtype=torch.long)


def prepare(
    input_path: Path = Path("datasets/raw/instruction.jsonl"),
    output_path: Path = Path("datasets/processed/instruction_train.pkl"),
    *,
    tokenizer_path: Path = Path("datasets/processed/tokenizer_veyra004.json"),
    val_output_path: Path = Path("datasets/processed/instruction_val.pkl"),
    test_output_path: Path = Path("datasets/processed/instruction_test.pkl"),
    context_length: int = 512,
    seed: int = 42,
    val_fraction: float = 0.1,
    test_fraction: float = 0.1,
) -> tuple[Path, Path, Path]:
    if context_length < 2:
        raise ValueError("context_length must be at least 2")
    if not 0 < val_fraction < 1 or not 0 < test_fraction < 1 or val_fraction + test_fraction >= 1:
        raise ValueError("Validation and test fractions must be positive and sum to less than one")
    output_paths = (output_path, val_output_path, test_output_path)
    if len({path.resolve() for path in output_paths}) != 3:
        raise ValueError("Train, validation, and test output paths must be different")
    existing = [str(path) for path in output_paths if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing dataset file(s): {', '.join(existing)}")

    records, input_sha256, input_record_count, duplicate_record_count = _load_records(input_path)
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    eos_token_id = tokenizer.token_to_id("</s>")
    pad_token_id = tokenizer.token_to_id("<pad>")
    if eos_token_id is None or pad_token_id is None or eos_token_id == pad_token_id:
        raise ValueError("Tokenizer must define distinct </s> and <pad> token IDs")
    if max(eos_token_id, pad_token_id) >= tokenizer.get_vocab_size():
        raise ValueError("Tokenizer special token ID is outside its vocabulary")
    tokenizer_sha256 = hashlib.sha256(tokenizer_path.read_bytes()).hexdigest()

    by_instruction: dict[str, list[dict[str, str]]] = {}
    for record in records:
        key = " ".join(record["instruction"].split()).casefold()
        by_instruction.setdefault(key, []).append(record)
    groups = list(by_instruction.values())
    if len(groups) < 3:
        raise ValueError("At least three unique instructions are required to prevent prompt leakage across splits")
    random.Random(seed).shuffle(groups)
    test_count = max(1, round(len(groups) * test_fraction))
    val_count = max(1, round(len(groups) * val_fraction))
    if test_count + val_count >= len(groups):
        raise ValueError("Not enough unique instructions for non-empty train, validation, and test splits")
    splits = {
        "train": [record for group in groups[:len(groups) - val_count - test_count] for record in group],
        "val": [record for group in groups[len(groups) - val_count - test_count:len(groups) - test_count] for record in group],
        "test": [record for group in groups[len(groups) - test_count:] for record in group],
    }
    destinations = {"train": output_path, "val": val_output_path, "test": test_output_path}

    for split_name, split_records in splits.items():
        samples = [
            _encode_sample(tokenizer, record["instruction"], record["response"],
                           context_length, eos_token_id, pad_token_id)
            for record in split_records
        ]
        if not samples:
            raise ValueError(f"{split_name} split has no samples")
        dataset: dict[str, Any] = {
            "samples": samples,
            "tokenizer_path": str(tokenizer_path),
            "tokenizer_sha256": tokenizer_sha256,
            "tokenizer_vocab_size": tokenizer.get_vocab_size(),
            "vocab_size": tokenizer.get_vocab_size(),
            "eos_token_id": eos_token_id,
            "pad_token_id": pad_token_id,
            "context_length": context_length,
            "dataset_version": "response-mask-v1",
            "split": split_name,
            "held_out": split_name != "train",
            "label_ignore_index": IGNORE_INDEX,
            "target_policy": "response_tokens_and_eos_only",
            "seed": seed,
            "input_sha256": input_sha256,
            "record_count": len(split_records),
            "input_record_count": input_record_count,
            "duplicate_record_count": duplicate_record_count,
            "instruction_group_hashes": sorted({
                hashlib.sha256(" ".join(record["instruction"].split()).casefold().encode("utf-8")).hexdigest()
                for record in split_records
            }),
            "provenance": sorted({
                f"{record['source']} | {record['license']} | {record['target_provenance']}"
                for record in split_records
            }),
            "sources": sorted({
                json.dumps({
                    field: record[field]
                    for field in (
                        "source", "source_url", "license", "license_url", "attribution",
                        "rights_basis", "source_version", "acquisition_date",
                    )
                }, sort_keys=True)
                for record in split_records
            }),
        }
        destination = destinations[split_name]
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output_file:
            pickle.dump(dataset, output_file)
    return output_path, val_output_path, test_output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("datasets/raw/instruction.jsonl"))
    parser.add_argument("--tokenizer", type=Path, default=Path("datasets/processed/tokenizer_veyra004.json"))
    parser.add_argument("--train-output", type=Path, default=Path("datasets/processed/instruction_train.pkl"))
    parser.add_argument("--val-output", type=Path, default=Path("datasets/processed/instruction_val.pkl"))
    parser.add_argument("--test-output", type=Path, default=Path("datasets/processed/instruction_test.pkl"))
    parser.add_argument("--context-length", type=int, default=512)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    prepare(
        args.input,
        args.train_output,
        tokenizer_path=args.tokenizer,
        val_output_path=args.val_output,
        test_output_path=args.test_output,
        context_length=args.context_length,
        seed=args.seed,
    )
