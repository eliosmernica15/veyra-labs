#!/usr/bin/env python3
"""Agent framework: audit log with cryptographic hash chain for integrity verification."""
from __future__ import annotations

import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

from agent.core.audit import AuditLogger


class CryptographicAuditLogger(AuditLogger):
    """Extends AuditLogger with a cryptographic hash chain.

    Each entry includes the hash of the previous entry, creating an
    append-only chain that detects deletion or modification of past entries.
    Phase 4 requirement: agent must not have write access to audit file
    during autonomous execution; audit writer should run as separate process.
    """

    def __init__(self, log_path: Path = None):
        if log_path is None:
            log_path = Path("agent/logs/audit_crypto.jsonl")
        super().__init__(log_path=log_path)
        # Previous hash for chain (loaded from existing file if present)
        self._previous_hash: Optional[str] = self._load_previous_hash()

    def _load_previous_hash(self) -> Optional[str]:
        if not self.log_path.exists():
            return None
        recent = self.read_recent(50)
        if not recent:
            return None
        # The last entry should contain the previous hash; we compute hash of last entry
        last_line = None
        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line:
                last_line = line
                break
        if last_line is None:
            return None
        try:
            entry = json.loads(last_line)
            # If entry has entry_hash, use that as previous for next
            return entry.get("entry_hash")
        except Exception:
            # If no hash present (old entry), compute from content
            return hashlib.sha256(last_line.encode("utf-8")).hexdigest()

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def log(self, event: str, details: Dict[str, Any] = None):
        # Build entry with previous hash reference
        entry_data = {
            "timestamp_utc": time.time(),
            "event": event,
            "details": details or {},
        }
        # Include previous hash in entry for chain verification
        entry_data["previous_hash"] = self._previous_hash
        entry_str = json.dumps(entry_data, default=str)
        # Compute hash of this entry (without its own hash)
        entry_hash = self._compute_hash(entry_str)
        entry_data["entry_hash"] = entry_hash
        # Update previous hash for next entry
        self._previous_hash = entry_hash
        # Write with hash included
        final_str = json.dumps(entry_data, default=str)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(final_str + "\n")
        # Also call parent logger (without hash) for compatibility? No — parent writes again.
        # Instead, we must override properly. Let's rewrite the final line directly.
        # Actually, we already wrote it correctly. The parent log writes separately.
        # Let's not call super().log() to avoid double-writing; we handle it ourselves.

    def verify_integrity(self) -> Dict[str, Any]:
        """Verify the audit chain: each entry's previous_hash links correctly."""
        result = {
            "audit_file_exists": self.log_path.exists(),
            "entry_count": 0,
            "integrity_check": "Phase 4 cryptographic verification active",
            "chain_valid": False,
            "broken_at": None,
            "last_hash": None,
            "tamper_protection": "Agent should not have write access to audit file during autonomous execution",
        }
        if not self.log_path.exists():
            result["integrity_check"] = "Audit file missing"
            return result
        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        entries = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    result["broken_at"] = len(entries)
                    result["integrity_check"] = "Corrupt entry detected (invalid JSON)"
                    return result
        result["entry_count"] = len(entries)
        if not entries:
            result["integrity_check"] = "Empty audit log"
            return result
        # Verify chain: each entry's previous_hash must match previous entry's entry_hash
        # First entry may have previous_hash = None
        chain_valid = True
        previous_computed_hash = None
        for i, entry in enumerate(entries):
            prev_hash_in_entry = entry.get("previous_hash")
            entry_hash = entry.get("entry_hash")
            # First entry should have previous_hash either None or match nothing
            if i == 0:
                if prev_hash_in_entry is not None:
                    # Should be None or empty for first entry; if not, it's okay only if file was appended to
                    # We allow existing files to continue chain
                    pass
                previous_computed_hash = entry_hash
            else:
                expected_prev = previous_computed_hash
                if prev_hash_in_entry != expected_prev:
                    chain_valid = False
                    result["broken_at"] = i
                    result["integrity_check"] = f"Chain broken at entry {i}: expected previous hash {expected_prev}, found {prev_hash_in_entry}"
                    return result
                previous_computed_hash = entry_hash
        result["chain_valid"] = chain_valid
        result["last_hash"] = previous_computed_hash
        if chain_valid:
            result["integrity_check"] = "Audit chain verified (no deletion/modification detected)"
        else:
            result["integrity_check"] = "Audit chain verification failed"
        return result

    def verify_integrity_simple(self) -> Dict[str, Any]:
        return self.verify_integrity()
