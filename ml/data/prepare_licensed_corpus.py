#!/usr/bin/env python3
"""Build reproducible, provenance-preserving train/validation/test text datasets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import random
import re
import tempfile
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

import torch
from tokenizers import Tokenizer

SUPPORTED_LICENSES = {"CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "Public-Domain"}
SPLITS = ("train", "val", "test")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_documents(
    manifest_path: Path,
) -> tuple[list[dict[str, Any]], str, int, list[dict[str, Any]], str, str]:
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest.decode("utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("documents"), list):
        raise ValueError("Manifest must be an object containing a documents list")

    documents: list[dict[str, Any]] = []
    seen_content: set[str] = set()
    excluded_documents: list[dict[str, Any]] = []
    root = manifest_path.parent.resolve()
    acquisition_date = manifest.get("acquisition_date")
    try:
        date.fromisoformat(acquisition_date)
    except (TypeError, ValueError) as exc:
        raise ValueError("Manifest must record acquisition_date as an ISO date") from exc
    dataset_version = manifest.get("dataset_version")
    if not isinstance(dataset_version, str) or not dataset_version.strip():
        raise ValueError("Manifest must record a non-empty dataset_version")
    for index, entry in enumerate(manifest["documents"]):
        if not isinstance(entry, dict):
            raise ValueError(f"Manifest document {index} must be an object")
        required = (
            "path", "title", "source_url", "license", "license_url",
            "license_evidence_url", "attribution", "source_version", "rights_basis",
        )
        missing = [key for key in required if not isinstance(entry.get(key), str) or not entry[key].strip()]
        if missing:
            raise ValueError(f"Manifest document {index} is missing: {', '.join(missing)}")
        license_id = entry["license"].strip()
        if license_id not in SUPPORTED_LICENSES:
            raise ValueError(f"Unsupported license {license_id!r} for document {index}")
        for url_field in ("source_url", "license_url", "license_evidence_url"):
            if not entry[url_field].startswith("https://"):
                raise ValueError(f"Document {index} {url_field} must be an HTTPS URL")
        if entry.get("rights_verified") is not True:
            raise ValueError(f"Document {index} must have rights_verified=true after human review")
        if license_id == "CC0-1.0" and entry["license_url"].rstrip("/") != "https://creativecommons.org/publicdomain/zero/1.0":
            raise ValueError(f"Document {index} license_url does not match CC0-1.0")
        if license_id == "CC-BY-4.0" and entry["license_url"].rstrip("/") != "https://creativecommons.org/licenses/by/4.0":
            raise ValueError(f"Document {index} license_url does not match CC-BY-4.0")
        if license_id == "CC-BY-SA-4.0" and entry["license_url"].rstrip("/") != "https://creativecommons.org/licenses/by-sa/4.0":
            raise ValueError(f"Document {index} license_url does not match CC-BY-SA-4.0")
        if license_id == "Public-Domain" and not str(entry.get("jurisdiction", "")).strip():
            raise ValueError(f"Public-Domain document {index} must record its jurisdiction")

        source_path = (root / entry["path"]).resolve()
        if not source_path.is_relative_to(root):
            raise ValueError(f"Document path escapes the manifest directory: {entry['path']}")
        try:
            raw_text = source_path.read_bytes()
        except FileNotFoundError:
            excluded_documents.append({"path": entry["path"], "reason": "missing_source_file"})
            continue
        try:
            text = raw_text.decode("utf-8-sig")
        except UnicodeDecodeError:
            excluded_documents.append({
                "path": entry["path"],
                "reason": "invalid_utf8",
                "source_sha256": _sha256(raw_text),
            })
            continue
        text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n")).strip()
        if "\ufffd" in text or "\x00" in text or any(
            unicodedata.category(character) == "Cc" and character not in "\n\t"
            for character in text
        ):
            excluded_documents.append({
                "path": entry["path"],
                "reason": "replacement_null_or_control_character",
                "source_sha256": _sha256(raw_text),
            })
            continue
        if not text:
            excluded_documents.append({
                "path": entry["path"],
                "reason": "empty_after_cleaning",
                "source_sha256": _sha256(raw_text),
            })
            continue
        normalized = re.sub(r"\s+", " ", text).casefold()
        if len(normalized.split()) < 20:
            excluded_documents.append({
                "path": entry["path"],
                "reason": "fewer_than_20_words",
                "source_sha256": _sha256(raw_text),
            })
            continue
        content_hash = _sha256(normalized.encode("utf-8"))
        if content_hash in seen_content:
            excluded_documents.append({
                "path": entry["path"],
                "reason": "duplicate_normalized_content",
                "source_sha256": _sha256(raw_text),
                "normalized_content_sha256": content_hash,
            })
            continue
        seen_content.add(content_hash)
        documents.append({
            "text": text,
            "path": entry["path"],
            "title": entry["title"].strip(),
            "source_url": entry["source_url"].strip(),
            "license": license_id,
            "license_url": entry["license_url"].strip(),
            "license_evidence_url": entry["license_evidence_url"].strip(),
            "attribution": entry["attribution"].strip(),
            "rights_verified": True,
            "rights_basis": entry["rights_basis"].strip(),
            "source_version": entry["source_version"].strip(),
            "acquisition_date": acquisition_date,
            "jurisdiction": entry.get("jurisdiction"),
            "source_sha256": _sha256(raw_text),
            "normalized_content_sha256": content_hash,
            "word_count": len(text.split()),
            "nonempty_line_count": sum(bool(line.strip()) for line in text.splitlines()),
            "unique_nonempty_lines": len({
                re.sub(r"\s+", " ", line).casefold()
                for line in text.splitlines()
                if line.strip()
            }),
        })
    if len(documents) < 3:
        raise ValueError("At least three unique, rights-reviewed documents are required for disjoint splits")
    return (
        documents,
        _sha256(raw_manifest),
        sum(entry["reason"] == "duplicate_normalized_content" for entry in excluded_documents),
        excluded_documents,
        dataset_version.strip(),
        acquisition_date,
    )


def _make_samples(text: str, tokenizer: Tokenizer, context_length: int,
                  eos_token_id: int, pad_token_id: int) -> list[tuple[torch.Tensor, torch.Tensor]]:
    token_ids = tokenizer.encode(text, add_special_tokens=False).ids
    token_ids.append(eos_token_id)
    samples = []
    for start in range(0, len(token_ids) - 1, context_length):
        chunk = token_ids[start:start + context_length + 1]
        if len(chunk) < 2:
            continue
        x = chunk[:-1]
        y = chunk[1:]
        padding = context_length - len(x)
        x.extend([pad_token_id] * padding)
        y.extend([-1] * padding)
        samples.append((torch.tensor(x, dtype=torch.long), torch.tensor(y, dtype=torch.long)))
    return samples


def prepare_corpus(
    manifest_path: Path,
    tokenizer_path: Path,
    output_dir: Path,
    *,
    context_length: int = 512,
    seed: int = 42,
    val_fraction: float = 0.1,
    test_fraction: float = 0.1,
) -> dict[str, Path]:
    if context_length < 2:
        raise ValueError("context_length must be at least 2")
    if not 0 < val_fraction < 1 or not 0 < test_fraction < 1 or val_fraction + test_fraction >= 1:
        raise ValueError("Validation and test fractions must be positive and sum to less than one")
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing corpus output directory: {output_dir}")
    output_paths = {split: output_dir / f"{split}.pkl" for split in SPLITS}
    existing = [str(path) for path in output_paths.values() if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing dataset file(s): {', '.join(existing)}")

    (documents, manifest_sha256, duplicate_document_count, excluded_documents,
     dataset_version, acquisition_date) = _read_documents(manifest_path)
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    eos_token_id = tokenizer.token_to_id("</s>")
    pad_token_id = tokenizer.token_to_id("<pad>")
    if eos_token_id is None or pad_token_id is None or eos_token_id == pad_token_id:
        raise ValueError("Tokenizer must define distinct </s> and <pad> token IDs")

    random.Random(seed).shuffle(documents)
    test_count = max(1, round(len(documents) * test_fraction))
    val_count = max(1, round(len(documents) * val_fraction))
    if test_count + val_count >= len(documents):
        raise ValueError("Not enough unique documents for non-empty train, validation, and test splits")
    split_documents = {
        "train": documents[:len(documents) - val_count - test_count],
        "val": documents[len(documents) - val_count - test_count:len(documents) - test_count],
        "test": documents[len(documents) - test_count:],
    }

    tokenizer_sha256 = _sha256(tokenizer_path.read_bytes())
    split_payloads: dict[str, dict[str, Any]] = {}
    for split, split_docs in split_documents.items():
        samples = []
        token_counts = {}
        for document in split_docs:
            token_counts[document["normalized_content_sha256"]] = (
                len(tokenizer.encode(document["text"], add_special_tokens=False).ids) + 1
            )
            samples.extend(_make_samples(document["text"], tokenizer, context_length,
                                         eos_token_id, pad_token_id))
        if not samples:
            raise ValueError(f"{split} split produced no token samples")
        document_metadata = [
            {**{key: value for key, value in document.items() if key != "text"},
             "token_count": token_counts[document["normalized_content_sha256"]]}
            for document in split_docs
        ]
        metadata = {
            "samples": samples,
            "dataset_version": dataset_version,
            "split": split,
            "held_out": split != "train",
            "seed": seed,
            "acquisition_date": acquisition_date,
            "context_length": context_length,
            "tokenizer_path": str(tokenizer_path),
            "tokenizer_sha256": tokenizer_sha256,
            "tokenizer_vocab_size": tokenizer.get_vocab_size(),
            "vocab_size": tokenizer.get_vocab_size(),
            "manifest_path": str(manifest_path),
            "manifest_sha256": manifest_sha256,
            "cleaning_rules": [
                "decode UTF-8 with optional leading BOM",
                "normalize CRLF and CR to LF",
                "normalize Unicode to NFC",
                "trim leading and trailing whitespace",
                "reject replacement, NUL, and non-whitespace control characters",
                "exclude documents with fewer than 20 words",
            ],
            "deduplication_rule": "SHA-256 of whitespace-collapsed, case-folded Unicode content",
            "document_count": len(split_docs),
            "duplicate_document_count": duplicate_document_count,
            "excluded_document_count": len(excluded_documents),
            "excluded_documents": excluded_documents,
            "token_count": sum(token_counts.values()),
            "sample_count": len(samples),
            "documents": document_metadata,
            "label_ignore_index": -1,
        }
        split_payloads[split] = metadata

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.stage-", dir=output_dir.parent))
    try:
        for split, payload in split_payloads.items():
            with (staging_dir / f"{split}.pkl").open("xb") as output_file:
                pickle.dump(payload, output_file)
        os.rename(staging_dir, output_dir)
    except BaseException:
        for staged_file in staging_dir.iterdir():
            staged_file.unlink()
        staging_dir.rmdir()
        raise
    return output_paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, default=Path("datasets/processed/tokenizer_veyra004.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--context-length", type=int, default=512)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    prepare_corpus(args.manifest, args.tokenizer, args.output_dir,
                   context_length=args.context_length, seed=args.seed)
