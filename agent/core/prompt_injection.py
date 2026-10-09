#!/usr/bin/env python3
"""Agent framework: prompt injection defense — treat all external/tool output as untrusted."""
from __future__ import annotations

import re
from typing import Optional, List, Dict, Any

# Patterns that indicate hidden instructions in file/tool output
PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts)",
    r"(?i)disregard\s+(all\s+)?(previous|prior)\s+(instructions|prompts)",
    r"(?i)you\s+are\s+now\s+(a\s+)?(new\s+)?(agent|assistant|model)",
    r"(?i)system\s+prompt\s+override",
    r"(?i)new\s+instruction[s]?",
    r"(?i)forget\s+(previous|all)\s+(instructions|rules)",
    r"(?i)you\s+must\s+(now|instead)\s+",
    r"(?i)override\s+(security|permission|safeguard)",
    r"(?i)disable\s+(safeguard|audit|security|permission)",
    r"(?i)grant\s+(yourself|me)\s+(access|permission)",
    r"(?i)execute\s+without\s+(approval|authorization)",
    r"(?i)ignore\s+(workspace|boundar|restrict)",
    r"(?i)run\s+unrestricted",
    r"(?i)modify\s+(your\s+own|self)\s+(config|security)",
    r"(?i)self-modif",
]

# Hidden instruction markers
HIDDEN_INSTRUCTION_MARKERS = [
    "<!-- hidden instruction",
    "<!-- system instruction",
    "<!-- override",
    "[hidden: ",
    "[instruction: ",
]


class PromptInjectionFilter:
    """Filters untrusted file content / tool output before it becomes model input."""

    def __init__(self, patterns: Optional[List[str]] = None):
        self.patterns = patterns or PROMPT_INJECTION_PATTERNS
        self.compiled = [re.compile(p) for p in self.patterns]

    def detect_injection_attempts(self, text: str) -> List[str]:
        """Detect potential prompt injection patterns in untrusted text."""
        found = []
        for pattern in self.compiled:
            matches = pattern.findall(text)
            if matches:
                found.append(f"injection_pattern: {pattern.pattern} (matches: {len(matches)})")
        # Check hidden markers
        for marker in HIDDEN_INSTRUCTION_MARKERS:
            count = text.count(marker)
            if count > 0:
                found.append(f"hidden_marker: '{marker}' (count: {count})")
        return found

    def sanitize_for_model_input(self, text: str, max_length: int = 10000) -> str:
        """Sanitize untrusted content before passing to model prompts.

        - Truncates to max_length
        - Removes or neutralizes hidden instruction markers
        - Adds a clear prefix identifying content as untrusted
        """
        # Truncate
        truncated = text[:max_length]
        # Neutralize hidden markers
        for marker in HIDDEN_INSTRUCTION_MARKERS:
            truncated = truncated.replace(marker, "[NEUTRALIZED]")
        # Replace newlines in hidden instructions to break multi-line injection
        # Replace any line that looks like an instruction attempt with a placeholder
        lines = truncated.splitlines()
        sanitized_lines = []
        for line in lines:
            line_lower = line.lower()
            # If line contains strong injection keywords, replace the line content
            if any(p.pattern in line for p in self.compiled):
                # Check if the pattern actually matches
                for p in self.compiled:
                    if p.search(line):
                        sanitized_lines.append("[UNTRUSTED_CONTENT_FILTERED]")
                        break
                else:
                    sanitized_lines.append(line)
            else:
                sanitized_lines.append(line)
        sanitized = "\n".join(sanitized_lines)
        # Add explicit untrusted label
        result = f"[UNTRUSTED_EXTERNAL_CONTENT_BEGIN]\n{sanitized}\n[UNTRUSTED_EXTERNAL_CONTENT_END]"
        return result

    def is_safe_for_model_input(self, text: str) -> bool:
        attempts = self.detect_injection_attempts(text)
        return len(attempts) == 0

    def check_file_before_reading_for_model(self, file_path: str) -> Dict[str, Any]:
        # This function demonstrates that file content must be treated as untrusted
        # It does not actually read the file (would be real operation); it reports policy.
        return {
            "file_path": file_path,
            "treatment": "untrusted",
            "must_filter": True,
            "must_sanitize_before_model_input": True,
            "hidden_instruction_check_required": True,
        }
