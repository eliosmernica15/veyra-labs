#!/usr/bin/env python3
"""Agent framework: project understanding layer that builds a structured workspace representation."""
from __future__ import annotations

import os
import pathlib
from typing import Dict, Any, List, Optional

from agent.core.workspace_sandbox import WorkspaceSandbox
from agent.core.file_permissions import FilePermissionEnforcer
from agent.core.secret_redaction import SecretRedactor
from agent.core.prompt_injection import PromptInjectionFilter


class ProjectUnderstanding:
    """Builds and maintains a structured representation of the workspace."""

    def __init__(self, workspace_path: str = ".", allowed_subpaths: Optional[List[str]] = None):
        self.workspace_path = workspace_path
        self.sandbox = WorkspaceSandbox(
            workspace_roots=[workspace_path],
            allowed_subpaths=allowed_subpaths or [".", "tests/", "ml/", "datasets/", "agent/", "docs/", "services/", "apps/"],
        )
        self.permissions = FilePermissionEnforcer(permission_level="restricted", workspace_sandbox=self.sandbox)
        self.redactor = SecretRedactor()
        self.filter = PromptInjectionFilter()
        self.understanding: Dict[str, Any] = {}

    def discover_project_root(self) -> Optional[str]:
        # Project root is the workspace root
        workspace_result = self.sandbox.resolve_path(".")
        if workspace_result.get("allowed"):
            return str(pathlib.Path(self.workspace_path).resolve())
        return None

    def discover_important_directories(self, max_dirs: int = 20) -> List[Dict[str, Any]]:
        root = pathlib.Path(self.workspace_path)
        if not root.exists():
            return []
        dirs = []
        for entry in root.iterdir():
            if entry.is_dir() and not entry.name.startswith(".") and entry.name not in ("__pycache__", "node_modules", ".git", "venv", ".env"):
                dirs.append({"name": entry.name, "path": str(entry), "is_directory": True})
            if len(dirs) >= max_dirs:
                break
        return dirs

    def discover_source_files(self, max_files: int = 30) -> List[str]:
        root = pathlib.Path(self.workspace_path)
        sources = []
        # Only scan permitted subpaths to avoid unrestricted filesystem access
        allowed_subpaths = [".", "agent/", "tests/", "services/", "docs/"]
        for sub in allowed_subpaths:
            sub_path = root / sub
            if not sub_path.exists() or not sub_path.is_dir():
                continue
            workspace_check = self.sandbox.resolve_path(sub)
            if not workspace_check.get("allowed"):
                continue
            for entry in sub_path.rglob("*"):
                if entry.is_file() and entry.suffix in (".py", ".json", ".md", ".txt", ".yaml", ".yml"):
                    sources.append(str(entry.relative_to(root)))
                if len(sources) >= max_files:
                    return sources
        return sources

    def discover_test_files(self, max_tests: int = 20) -> List[str]:
        root = pathlib.Path(self.workspace_path)
        tests = []
        test_path = root / "tests"
        if test_path.exists() and test_path.is_dir():
            workspace_check = self.sandbox.resolve_path("tests/")
            if workspace_check.get("allowed"):
                for entry in test_path.rglob("*"):
                    if entry.is_file() and (entry.name.startswith("test_") or entry.name.endswith("_test.py")):
                        tests.append(str(entry.relative_to(root)))
                    if len(tests) >= max_tests:
                        break
        return tests

    def discover_config_files(self) -> List[str]:
        root = pathlib.Path(self.workspace_path)
        configs = []
        protected = self.permissions.is_operation_allowed  # Not directly; use safeguard protection
        # Look for common config/manifests without exposing protected files
        candidates = [
            "package.json", "setup.py", "pyproject.toml", "requirements.txt",
            ".env.example", ".gitignore", "README.md",
        ]
        for name in candidates:
            p = root / name
            if p.exists() and p.is_file():
                # Skip protected secret files (.env, .secrets, etc.)
                if name in (".env", ".env.local", ".env.production", ".secrets", ".netrc"):
                    continue
                configs.append(str(p.relative_to(root)))
        return configs

    def discover_documentation(self) -> List[str]:
        root = pathlib.Path(self.workspace_path)
        docs = []
        docs_path = root / "docs"
        if docs_path.exists() and docs_path.is_dir():
            workspace_check = self.sandbox.resolve_path("docs/")
            if workspace_check.get("allowed"):
                for entry in docs_path.rglob("*"):
                    if entry.is_file() and entry.suffix == ".md":
                        docs.append(str(entry.relative_to(root)))
        return docs

    def discover_git_state(self) -> Dict[str, Any]:
        import subprocess
        import sys
        try:
            result = subprocess.run(
                [sys.executable, "-m", "git", "status", "--short"],
                capture_output=True,
                text=True,
                cwd=self.workspace_path,
            )
            return {
                "git_available": result.returncode in (0, 128),  # 128 if not a git repo
                "status_output": result.stdout,
                "modified_files": [line for line in result.stdout.splitlines() if line],
                "modified_count": len([line for line in result.stdout.splitlines() if line]),
            }
        except Exception:
            return {"git_available": False, "status_output": "", "modified_files": [], "modified_count": 0}

    def discover_entry_points(self) -> List[str]:
        root = pathlib.Path(self.workspace_path)
        entries = []
        candidates = [
            "main.py", "cli.py", "app.py", "run.py", "start.py",
            "tests/demo_phase5/demo_manual_phase5.py",
        ]
        for c in candidates:
            p = root / c
            if p.exists() and p.is_file():
                entries.append(str(p.relative_to(root)))
        return entries

    def build_summary(self) -> Dict[str, Any]:
        self.understanding = {
            "workspace_path": self.workspace_path,
            "project_root": self.discover_project_root(),
            "directories": self.discover_important_directories(),
            "source_files": self.discover_source_files(),
            "test_files": self.discover_test_files(),
            "config_files": self.discover_config_files(),
            "documentation": self.discover_documentation(),
            "entry_points": self.discover_entry_points(),
            "git_state": self.discover_git_state(),
            "permission_level": self.permissions.permission_level,
            "workspace_allowed_subpaths": [".", "tests/", "ml/", "datasets/", "agent/", "docs/", "services/", "apps/"],
        }
        return self.understanding

    def refresh_summary(self) -> Dict[str, Any]:
        return self.build_summary()
