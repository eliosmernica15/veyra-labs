#!/usr/bin/env python3
"""Agent framework: safeguard protection — agent must not modify its own security policy."""
from __future__ import annotations

import os
import pathlib
from typing import List, Optional, Dict, Any


# Protected configuration files and directories that must remain read-only to agent
PROTECTED_FILES = [
    ".env",
    ".env.example",
    "agent/core/config.py",
    "agent/core/permission.py",
    "agent/core/workspace_sandbox.py",
    "agent/core/file_permissions.py",
    "agent/core/terminal_security.py",
    "agent/core/approval_system.py",
    "agent/core/secret_redaction.py",
    "agent/core/prompt_injection.py",
    "agent/core/safeguard_protection.py",
]

PROTECTED_CONFIG_KEYS = [
    "AGENT_AUTONOMOUS_EXECUTION",
    "AGENT_MOCK_ONLY",
    "AGENT_ENABLED",
    "AGENT_AUDIT_ENABLED",
    "AGENT_MAX_ITERATIONS",
    "AGENT_TIMEOUT_SECONDS",
    "AGENT_PERMISSION_LEVEL",
]


class SafeguardProtection:
    """Protects agent framework security controls from agent modification."""

    def __init__(self, protected_paths: Optional[List[str]] = None):
        self.protected_paths = protected_paths or PROTECTED_FILES
        # Ensure paths are absolute for comparison
        self._resolved_protected = set()
        for p in self.protected_paths:
            try:
                self._resolved_protected.add(str(pathlib.Path(p).resolve()))
            except Exception:
                pass

    def is_path_protected(self, file_path: str) -> bool:
        try:
            resolved = str(pathlib.Path(file_path).resolve())
            return resolved in self._resolved_protected
        except Exception:
            # If resolution fails, treat as protected for safety
            basename = os.path.basename(file_path)
            for protected in self.protected_paths:
                if protected.endswith(basename):
                    return True
            return False

    def check_write_permission(self, file_path: str) -> Dict[str, Any]:
        """Check whether an agent file write operation should be blocked."""
        protected = self.is_path_protected(file_path)
        return {
            "file_path": file_path,
            "protected": protected,
            "allowed": not protected,
            "reason": "File is protected security/safeguard configuration" if protected else "File not in protected list",
        }

    def protect_config_from_agent_modification(self, config_path: str = "agent/core/config.py") -> Dict[str, Any]:
        """Verify that agent framework config flags are protected.

        Phase 4 requires that the agent cannot disable its own safeguards.
        This is a design-level check; full process-level isolation requires
        separate user/process for autonomous execution (not implemented here).
        """
        result = {
            "protected_config_path": config_path,
            "config_exists": os.path.exists(config_path),
            "read_only_recommended": True,
            "agent_can_modify_config": False,
            "note": "Agent framework safeguards must be protected at process/file-system level; agent must not have write access to these files.",
        }
        if os.path.exists(config_path):
            # Check that file exists; recommend making it read-only at OS level
            # This is advisory — actual OS-level protection requires separate process/user
            result["advisory"] = "Make agent/core/config.py read-only for agent process; consider separate user for autonomous execution."
        else:
            result["advisory"] = f"Config file {config_path} not found; verify installation."
        return result

    def get_protected_paths(self) -> List[str]:
        return list(self.protected_paths)
