#!/usr/bin/env python3
"""Agent framework: audit and event logging (auditable, non-bypassable by agent)."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("agent.audit")

AUDIT_LOG_PATH = Path("agent/logs/audit.jsonl")
AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class AuditLogger:
    """Writes immutable audit entries. Agent must NOT be able to delete or modify past entries."""

    def __init__(self, log_path: Path = AUDIT_LOG_PATH):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, details: Dict[str, Any] = None):
        entry = {
            "timestamp_utc": time.time(),
            "event": event,
            "details": details or {},
        }
        # Append line-delimited JSON for durability
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        logger.info(f"AUDIT: {event}")

    def read_recent(self, n: int = 20) -> List[Dict]:
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").strip().split("\n")
        entries = []
        for line in lines[-n:]:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
        return entries

    def verify_integrity(self) -> Dict[str, Any]:
        # Phase 4 must enforce cryptographic integrity checks; Phase 3 defines interface
        recent = self.read_recent(10)
        return {
            "audit_file_exists": self.log_path.exists(),
            "entry_count": len(recent) if recent else 0,
            "integrity_check": "Phase 4 must implement cryptographic verification (hash chain / signature)",
            "tamper_protection": "Agent must not have write access to audit file during execution",
        }
