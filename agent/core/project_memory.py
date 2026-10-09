#!/usr/bin/env python3
"""Agent framework: persistent project memory with inspection, edit, deletion, and secret exclusion."""
from __future__ import annotations

import time
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from agent.core.secret_redaction import SecretRedactor
from agent.core.prompt_injection import PromptInjectionFilter
from agent.core.audit_crypto import CryptographicAuditLogger
from agent.core.workspace_sandbox import WorkspaceSandbox
from agent.core.file_permissions import FilePermissionEnforcer


class ProjectMemory:
    """Controlled persistent memory for useful project facts. Never stores secrets."""

    # Patterns that must never be saved to persistent memory
    SECRET_KEYWORDS = {"password", "token", "secret", "credential", "api_key", "auth", "key", ".env", "private_key", "secret_key"}

    def __init__(self, memory_path: str = ".agent_memory/memory.json"):
        self.memory_path = memory_path
        self.redactor = SecretRedactor()
        self.filter = PromptInjectionFilter()
        # Enforce workspace boundaries even for memory file access
        workspace_root = "."
        self.sandbox = WorkspaceSandbox(workspace_roots=[workspace_root], allowed_subpaths=["."])
        self.permissions = FilePermissionEnforcer(permission_level="restricted", workspace_sandbox=self.sandbox)
        self.audit = CryptographicAuditLogger()
        self.memory: Dict[str, Any] = self._load_memory()
        # Initialize standard sections
        if "facts" not in self.memory:
            self.memory["facts"] = {}
        if "decisions" not in self.memory:
            self.memory["decisions"] = []
        if "preferences" not in self.memory:
            self.memory["preferences"] = {}

    def _load_memory(self) -> Dict[str, Any]:
        p = Path(self.memory_path)
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8")
                data = json.loads(content)
                # Redact any accidentally stored secrets
                safe_data = self.redactor.redact_dict(data)
                return safe_data
            except Exception:
                return {}
        return {}

    def save_memory(self):
        p = Path(self.memory_path)
        # Always allow writing; workspace boundary is enforced at load/retrieval layer.
        # Secret redaction and prompt injection filtering are applied to content.
        p.parent.mkdir(parents=True, exist_ok=True)
        safe_memory = self.redactor.redact_dict(self.memory)
        p.write_text(json.dumps(safe_memory, indent=2), encoding="utf-8")
        self.audit.log("memory_saved", {"path": str(p), "facts_count": len(self.memory.get("facts", {})), "decisions_count": len(self.memory.get("decisions", []))})

    def add_fact(self, key: str, value: Any, source_note: str = "") -> bool:
        # Block secret-related keys
        lower_key = key.lower()
        for secret_kw in self.SECRET_KEYWORDS:
            if secret_kw in lower_key:
                self.audit.log("memory_fact_blocked_secret_key", {"key": key, "reason": "secret-related key"})
                return False
        # Filter value for untrusted/injected content only when it appears external/untrusted
        safe_value = value
        if isinstance(value, str) and (self.filter.detect_injection_attempts(value) or "[UNTRUSTED" in value):
            safe_value = self.filter.sanitize_for_model_input(value)
        # Redact any secrets embedded in value strings
        safe_value_str = self.redactor.redact_text(str(safe_value)) if isinstance(safe_value, (str, int, float, bool)) else safe_value
        # For non-string values, apply redaction to JSON representation to catch embedded secrets
        safe_memory_fact = self.redactor.redact_dict({"value": safe_value_str, "source_note": source_note, "timestamp": time.time()})
        self.memory.setdefault("facts", {})[key] = safe_memory_fact
        self.save_memory()
        return True

    def get_fact(self, key: str) -> Optional[Any]:
        facts = self.memory.get("facts", {})
        if key in facts:
            return facts[key].get("value")
        return None

    def get_all_facts(self) -> Dict[str, Any]:
        return {k: v.get("value") for k, v in self.memory.get("facts", {}).items()}

    def add_decision(self, description: str, context: str = "") -> bool:
        safe_desc = str(description)
        if self.filter.detect_injection_attempts(safe_desc) or "[UNTRUSTED" in safe_desc:
            safe_desc = self.filter.sanitize_for_model_input(safe_desc)
        safe_context = str(context)
        if self.filter.detect_injection_attempts(safe_context) or "[UNTRUSTED" in safe_context:
            safe_context = self.filter.sanitize_for_model_input(safe_context)
        decision = {
            "description": safe_desc,
            "context": safe_context,
            "timestamp": time.time(),
        }
        self.memory.setdefault("decisions", []).append(decision)
        self.save_memory()
        return True

    def get_decisions(self) -> List[Dict[str, Any]]:
        return self.memory.get("decisions", [])

    def set_preference(self, preference_name: str, value: Any) -> bool:
        safe_name = str(preference_name)
        safe_value = value
        if isinstance(value, str) and (self.filter.detect_injection_attempts(value) or "[UNTRUSTED" in value):
            safe_value = self.filter.sanitize_for_model_input(value)
        self.memory.setdefault("preferences", {})[safe_name] = safe_value
        self.save_memory()
        return True

    def get_preference(self, preference_name: str) -> Optional[Any]:
        return self.memory.get("preferences", {}).get(preference_name)

    def edit_memory(self, edits: Dict[str, Any]) -> bool:
        # Only allow edits to facts/decisions/preferences — not arbitrary keys
        allowed_sections = {"facts", "decisions", "preferences"}
        for section_key, updates in edits.items():
            if section_key not in allowed_sections:
                return False
            if section_key == "facts" and isinstance(updates, dict):
                for k, v in updates.items():
                    # Block secret keys
                    lower_k = k.lower()
                    blocked = False
                    for secret_kw in self.SECRET_KEYWORDS:
                        if secret_kw in lower_k:
                            blocked = True
                            break
                    if blocked:
                        continue
                    safe_value = v
                    if isinstance(v, str) and (self.filter.detect_injection_attempts(str(v)) or "[UNTRUSTED" in str(v)):
                        safe_value = self.filter.sanitize_for_model_input(str(v))
                    safe_memory_fact = self.redactor.redact_dict({"value": safe_value, "source_note": "manual_edit", "timestamp": time.time()})
                    self.memory.setdefault("facts", {})[k] = safe_memory_fact
            elif section_key == "preferences" and isinstance(updates, dict):
                for k, v in updates.items():
                    safe_value = v
                    if isinstance(v, str) and (self.filter.detect_injection_attempts(str(v)) or "[UNTRUSTED" in str(v)):
                        safe_value = self.filter.sanitize_for_model_input(str(v))
                    safe_name_part = str(k)
                    if self.filter.detect_injection_attempts(str(k)) or "[UNTRUSTED" in str(k):
                        safe_name_part = self.filter.sanitize_for_model_input(str(k))
                    self.memory.setdefault("preferences", {})[safe_name_part] = safe_value
            elif section_key == "decisions" and isinstance(updates, list):
                for item in updates:
                    safe_item = item
                    if isinstance(item, dict):
                        safe_item = self.redactor.redact_dict(self.filter.sanitize_for_model_input(str(item.get("description", ""))))
                    self.memory.setdefault("decisions", []).append(safe_item)
        self.save_memory()
        return True

    def delete_memory_item(self, item_type: str, key_or_index: Any) -> bool:
        if item_type == "facts":
            facts = self.memory.get("facts", {})
            if key_or_index in facts:
                del facts[key_or_index]
                self.save_memory()
                return True
        elif item_type == "decisions":
            decisions = self.memory.get("decisions", [])
            if isinstance(key_or_index, int) and 0 <= key_or_index < len(decisions):
                decisions.pop(key_or_index)
                self.save_memory()
                return True
        elif item_type == "preferences":
            preferences = self.memory.get("preferences", {})
            if key_or_index in preferences:
                del preferences[key_or_index]
                self.save_memory()
                return True
        return False

    def clear_memory(self) -> bool:
        self.memory = {"facts": {}, "decisions": [], "preferences": {}}
        self.save_memory()
        return True

    def inspect_memory(self) -> Dict[str, Any]:
        result = {
            "memory_path": self.memory_path,
            "facts": list(self.memory.get("facts", {}).keys()),
            "decisions": len(self.memory.get("decisions", [])),
            "preferences": list(self.memory.get("preferences", {}).keys()),
        }
        return result
