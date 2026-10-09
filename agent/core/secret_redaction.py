#!/usr/bin/env python3
"""Agent framework: secret pattern detection and redaction from audit/output."""
from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
import os


# Default secret patterns — common credential indicators
DEFAULT_SECRET_PATTERNS = [
    r"password\s*[=:]\s*['\"]?[a-zA-Z0-9_!@#$%^&*()\-+=]{4,}['\"]?",
    r"password\s+[a-zA-Z0-9_!@#$%^&*()\-+=]{4,}\b",
    r"(?:secret|token|credential|auth)\s*[=:]\s*['\"]?[a-zA-Z0-9_!@#$%^&*()\-+=]{4,}['\"]?",
    r"(?:secret|token|credential|auth)\s+[a-zA-Z0-9_!@#$%^&*()\-+=]{4,}\b",
    r"secret[a-zA-Z0-9_!@#$%^&*()\-+=]{1,}\b",
    r"token[a-zA-Z0-9_!@#$%^&*()\-+=]{4,}\b",
    r"api_key\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{8,}['\"]?",
    r"apikey\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{8,}['\"]?",
    r"key\s*[=:]\s*['\"]?[a-zA-Z0-9_\-]{8,}['\"]?",
    r"credential[s]?\s*[=:]\s*['\"]?[a-zA-Z0-9_!@#$%^&*()\-+=]{4,}['\"]?",
    r"auth\s*[=:]\s*['\"]?[a-zA-Z0-9_!@#$%^&*()\-+=]{4,}['\"]?",
]

# More aggressive patterns for redaction of potential secrets
AGGRESSIVE_PATTERNS = [
    r"[a-zA-Z0-9_!@#$%^&*()\-+=]{16,}",  # Long random-looking strings
]


class SecretRedactor:
    """Redacts potential secrets from output and audit logs."""

    def __init__(self, patterns: Optional[List[str]] = None):
        self.patterns = patterns or DEFAULT_SECRET_PATTERNS
        self.compiled = [re.compile(p, re.IGNORECASE) for p in self.patterns]
        # Secret-bearing files that must not be exposed to model by default
        self.secret_files = {".env", ".env.local", ".env.production", ".secrets", "secrets.json", "credentials.json", ".netrc"}

    def is_secret_file(self, file_path: str) -> bool:
        basename = os.path.basename(file_path)
        if basename in self.secret_files:
            return True
        for secret_file in self.secret_files:
            if file_path.endswith(secret_file):
                return True
        return False

    def redact_text(self, text: str) -> str:
        """Redact patterns from text, replacing with [REDACTED]."""
        result = text
        for pattern in self.compiled:
            result = pattern.sub("[REDACTED]", result)
        return result

    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact values from a dictionary."""
        redacted = {}
        for key, value in data.items():
            # Always redact values of known secret keys
            key_lower = str(key).lower()
            if any(s in key_lower for s in ["password", "token", "secret", "credential", "api_key", "apikey", "auth", "key"]):
                # Don't expose value regardless of pattern match
                redacted[key] = "[REDACTED]"
            elif isinstance(value, str):
                redacted[key] = self.redact_text(value)
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [self.redact_text(str(item)) if isinstance(item, str) else (self.redact_dict(item) if isinstance(item, dict) else item) for item in value]
            else:
                # For non-string, non-dict values, convert to string and redact
                redacted[key] = self.redact_text(str(value))
        return redacted

    def check_for_secrets_in_text(self, text: str) -> List[str]:
        found = []
        for pattern in self.compiled:
            matches = pattern.findall(text)
            if matches:
                found.extend([f"pattern_match: {m}" for m in matches])
        # Deduplicate
        return list(set(found[:10]))  # Limit to first 10 detections
