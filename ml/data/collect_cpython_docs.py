#!/usr/bin/env python3
"""Verify and extract documentation sources from a pinned CPython release archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

CPYTHON_COMMIT = "823f0323ee6ec1402088b73bce1a38473cac36dc"
CPYTHON_TAG = "v3.14.7"
ARCHIVE_URL = f"https://codeload.github.com/python/cpython/zip/{CPYTHON_COMMIT}"
TREE_URL = f"https://api.github.com/repos/python/cpython/git/trees/{CPYTHON_COMMIT}?recursive=1"
LICENSE_URL = "https://docs.python.org/3/license.html"
LICENSE_ID = "PSF-2.0"
LICENSE_TEXT_PATH = "Doc/license.rst"
LICENSE_EVIDENCE = (
    f"https://github.com/python/cpython/blob/{CPYTHON_COMMIT}/{LICENSE_TEXT_PATH}"
)
ATTRIBUTION = (
    "Python Software Foundation and CPython documentation contributors; "
    "retain the PSF License Version 2 and copyright notices from the source."
)
ROOT_PREFIX = f"cpython-{CPYTHON_COMMIT}/"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob_sha1(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


def collect_cpython_docs(
    archive_path: Path,
    tree_path: Path,
    output_root: Path,
) -> Path:
    if output_root.exists():
        raise FileExistsError(f"Refusing to overwrite existing source directory: {output_root}")

    tree_data = json.loads(tree_path.read_text(encoding="utf-8-sig"))
    if tree_data.get("truncated") is True:
        raise ValueError("Pinned upstream tree is truncated")
    tree_entries = {
        entry["path"]: entry["sha"]
        for entry in tree_data.get("tree", [])
        if entry.get("type") == "blob" and entry.get("path", "").startswith("Doc/")
        and entry.get("path", "").endswith(".rst")
    }
    if not tree_entries:
        raise ValueError("Pinned upstream tree contains no reStructuredText documentation")

    archive_sha256 = _sha256(archive_path)
    output_root.mkdir(parents=True)
    source_root = output_root / "sources"
    documents: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(archive_path) as archive:
            archive_names = set(archive.namelist())
            expected_root = ROOT_PREFIX
            if not any(name.startswith(expected_root) for name in archive_names):
                raise ValueError("Archive root does not match the pinned CPython commit")

            for relative_path, expected_git_sha in sorted(tree_entries.items()):
                archive_pathname = expected_root + relative_path
                try:
                    content = archive.read(archive_pathname)
                except KeyError as exc:
                    raise ValueError(f"Pinned documentation file missing from archive: {relative_path}") from exc
                if _git_blob_sha1(content) != expected_git_sha:
                    raise ValueError(f"Git blob verification failed for {relative_path}")
                try:
                    content.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ValueError(f"Documentation source is not UTF-8: {relative_path}") from exc

                destination = source_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as output:
                    output.write(content)
                documents.append({
                    "path": destination.relative_to(output_root).as_posix(),
                    "title": relative_path.removeprefix("Doc/"),
                    "source_url": f"https://github.com/python/cpython/blob/{CPYTHON_COMMIT}/{relative_path}",
                    "license": LICENSE_ID,
                    "license_url": LICENSE_URL,
                    "license_evidence_url": LICENSE_EVIDENCE,
                    "attribution": ATTRIBUTION,
                    "source_version": f"CPython {CPYTHON_TAG} ({CPYTHON_COMMIT})",
                    "rights_basis": (
                        "The pinned Doc/license.rst says Python software and documentation are "
                        "licensed under PSF License Version 2, which grants a worldwide, "
                        "royalty-free license to reproduce, prepare derivatives, distribute, "
                        "and otherwise use Python and associated documentation. Preserve the "
                        "PSF license and copyright notice. Documentation examples/recipes/code "
                        "are additionally dual-licensed under Zero-Clause BSD from 3.8.6."
                    ),
                    "rights_verified": True,
                    "jurisdiction": "Worldwide license grant in PSF License Version 2",
                    "source_git_blob_sha1": expected_git_sha,
                })
    except BaseException:
        if output_root.exists():
            for path in sorted(output_root.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            output_root.rmdir()
        raise

    manifest = {
        "dataset_version": f"cpython-docs-{CPYTHON_TAG}",
        "acquisition_date": date.today().isoformat(),
        "source_artifact": {
            "source_id": "python/cpython",
            "source_name": "CPython official source repository, documentation tree",
            "release_tag": CPYTHON_TAG,
            "commit": CPYTHON_COMMIT,
            "commit_timestamp": "2026-08-05T10:29:49Z",
            "archive_url": ARCHIVE_URL,
            "archive_sha256": archive_sha256,
            "tree_url": TREE_URL,
            "tree_sha256": _sha256(tree_path),
            "license": LICENSE_ID,
            "license_url": LICENSE_URL,
            "license_evidence_url": LICENSE_EVIDENCE,
            "license_text_path": LICENSE_TEXT_PATH,
            "attribution": ATTRIBUTION,
            "document_source_file_count": len(documents),
            "downloaded_on": date.today().isoformat(),
        },
        "documents": documents,
    }
    manifest_path = output_root / "manifest.json"
    with manifest_path.open("x", encoding="utf-8") as output:
        json.dump(manifest, output, indent=2, ensure_ascii=False, sort_keys=True)
        output.write("\n")
    return manifest_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--tree", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(collect_cpython_docs(args.archive, args.tree, args.output_root))
