#!/usr/bin/env python3
"""Agent framework: relevant file selection for tasks using workspace-bound signals."""
from __future__ import annotations

import os
from typing import List, Optional, Dict, Any

from agent.core.workspace_sandbox import WorkspaceSandbox
from agent.core.file_permissions import FilePermissionEnforcer


class RelevantFileSelector:
    """Select relevant files for a task without dumping the entire project."""

    def __init__(self, workspace_path: str = ".", allowed_subpaths: Optional[List[str]] = None):
        self.workspace_path = workspace_path
        self.sandbox = WorkspaceSandbox(
            workspace_roots=[workspace_path],
            allowed_subpaths=allowed_subpaths or [".", "tests/", "ml/", "agent/", "docs/", "services/", "apps/"],
        )
        self.permissions = FilePermissionEnforcer(permission_level="restricted", workspace_sandbox=self.sandbox)

    def select_by_path_relevance(self, task_description: str, max_results: int = 10) -> List[Dict[str, Any]]:
        keywords = [k.lower() for k in task_description.split() if len(k) > 2]
        candidates = []
        for sub in [".", "tests/", "agent/", "docs/", "services/"]:
            workspace_check = self.sandbox.resolve_path(sub)
            if not workspace_check.get("allowed"):
                continue
            sub_path = os.path.join(self.workspace_path, sub)
            if not os.path.exists(sub_path):
                continue
            for root, dirs, files in os.walk(sub_path):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", ".env")]
                for f in files:
                    if f.endswith((".py", ".json", ".md", ".txt", ".yaml", ".yml")):
                        rel = os.path.join(sub, f) if sub != "." else f
                        score = sum(1 for kw in keywords if kw in f.lower() or kw in rel.lower())
                        if score > 0:
                            candidates.append({"path": rel, "relevance_score": score, "reason": "keyword_match", "task_keyword": keywords})
                if len(candidates) >= max_results:
                    break
        # Sort by score, return top
        candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
        return candidates[:max_results]

    def select_by_recent_inspection(self, recent_files: List[str], max_results: int = 5) -> List[Dict[str, Any]]:
        # Filter recent files to workspace-allowed paths only
        allowed = []
        for f in recent_files:
            workspace_check = self.sandbox.resolve_path(f)
            if workspace_check.get("allowed") and workspace_check.get("within_subpath"):
                allowed.append({"path": f, "relevance_score": 1, "reason": "recently_inspected"})
        return allowed[:max_results]

    def select_by_git_changes(self, max_results: int = 10) -> List[Dict[str, Any]]:
        import subprocess
        import sys
        try:
            result = subprocess.run(
                [sys.executable, "-m", "git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                cwd=self.workspace_path,
            )
            files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            selected = []
            for f in files:
                workspace_check = self.sandbox.resolve_path(f)
                if workspace_check.get("allowed"):
                    selected.append({"path": f, "relevance_score": 2, "reason": "git_changed"})
                if len(selected) >= max_results:
                    break
            return selected
        except Exception:
            return []
