#!/usr/bin/env python3
"""Agent framework: workspace sandbox with strict path resolution and boundary enforcement."""
from __future__ import annotations

import os
import pathlib
from typing import List, Optional, Dict, Any, Set


class WorkspaceSandbox:
    """Strict workspace boundary enforcement for agent file operations.

    The agent must never receive unrestricted filesystem access. All paths
    are resolved to canonical absolute paths before access and must remain
    within the explicitly authorized workspace roots.
    """

    def __init__(
        self,
        workspace_roots: Optional[List[str]] = None,
        allowed_subpaths: Optional[List[str]] = None,
        allow_symlinks: bool = False,
    ):
        # Default safe workspace: current directory with explicit subpaths
        self.workspace_roots: List[pathlib.Path] = []
        if workspace_roots is None:
            workspace_roots = ["."]
        for root in workspace_roots:
            resolved = self._resolve_root(str(root))
            if resolved is not None:
                self.workspace_roots.append(resolved)
        # Default safe subpaths within workspace (restrict to project directories)
        self.allowed_subpaths: Set[str] = set()
        if allowed_subpaths is None:
            allowed_subpaths = [
                ".",
                "ml/",
                "datasets/",
                "configs/",
                "tests/",
                "agent/",
                "docs/",
                "services/",
                "apps/",
            ]
        for sub in allowed_subpaths:
            sub = sub.rstrip("/")
            if sub == ".":
                sub = "."
            self.allowed_subpaths.add(sub)
        self.allow_symlinks = allow_symlinks

    def _resolve_root(self, root_path: str) -> Optional[pathlib.Path]:
        try:
            path = pathlib.Path(root_path)
            if not path.exists():
                # If root doesn't exist yet, resolve its parent directory
                parent = path.parent.resolve()
                if parent.exists():
                    return parent
                # Fallback: resolve absolute of string
                return pathlib.Path(os.path.abspath(str(path))).resolve()
            return path.resolve()
        except Exception:
            return None

    def _canonical_path(self, file_path: str, base_workspace: Optional[pathlib.Path] = None) -> Optional[pathlib.Path]:
        if base_workspace is not None:
            target = (base_workspace / file_path).resolve()
        else:
            # Relative to first workspace root
            if not self.workspace_roots:
                return None
            target = (self.workspace_roots[0] / file_path).resolve()
        return target

    def resolve_path(self, file_path: str, workspace_base: Optional[str] = None) -> Dict[str, Any]:
        """Resolve a file path and check workspace boundary compliance.

        Returns a dict with:
        - resolved_path (str): canonical absolute path
        - allowed (bool): whether path is within workspace
        - within_subpath (bool): whether path is within allowed subpaths
        - symlink_detected (bool): whether path traversal involved symlinks
        - error (str or None): error message if disallowed
        """
        result = {
            "resolved_path": None,
            "allowed": False,
            "within_subpath": False,
            "symlink_detected": False,
            "error": None,
        }
        # Reject absolute paths that try to escape the workspace
        if file_path.startswith("/") or file_path.startswith("\\"):
            # Only allow absolute paths that resolve inside workspace
            try:
                abs_target = pathlib.Path(file_path).resolve()
                allowed_roots = [str(r) for r in self.workspace_roots]
                in_root = any(str(abs_target).startswith(str(r)) for r in self.workspace_roots)
                if not in_root:
                    result["error"] = f"Absolute path outside workspace: {file_path} (resolved: {abs_target})"
                    return result
                result["resolved_path"] = str(abs_target)
                result["allowed"] = True
                result["symlink_detected"] = not self.allow_symlinks and (abs_target.exists() and os.path.islink(str(abs_target)))
                result["within_subpath"] = self._check_subpath(str(abs_target), str(abs_target))
                return result
            except Exception as exc:
                result["error"] = f"Failed to resolve absolute path: {file_path}: {exc}"
                return result

        # Resolve relative to workspace
        base = None
        if workspace_base is not None:
            base_path = pathlib.Path(workspace_base)
            if base_path.exists():
                base = base_path.resolve()
            else:
                base = self.workspace_roots[0] if self.workspace_roots else None
        else:
            base = self.workspace_roots[0] if self.workspace_roots else None

        if base is None:
            result["error"] = "No workspace base available for resolution"
            return result

        try:
            target = (base / file_path).resolve()
        except Exception as exc:
            result["error"] = f"Failed to resolve path '{file_path}' from workspace '{base}': {exc}"
            return result

        # Check symlink detection (if permitted, still note it)
        try:
            symlink_detected = False
            # If symlinks not allowed, inspect intermediate components
            if not self.allow_symlinks:
                # Check if any parent component is a symlink
                for parent in target.parents:
                    if parent.exists() and parent.is_symlink():
                        symlink_detected = True
                        break
            else:
                # Even if allowed, detect for audit
                for parent in target.parents:
                    if parent.exists() and parent.is_symlink():
                        symlink_detected = True
                        break
        except Exception:
            symlink_detected = False

        result["resolved_path"] = str(target)
        result["symlink_detected"] = symlink_detected

        # Check workspace root containment
        in_root = False
        for root in self.workspace_roots:
            root_str = str(root)
            target_str = str(target)
            # Ensure target is either the root or within it
            try:
                rel = os.path.relpath(str(target), root_str)
                if rel != ".." and not rel.startswith("..") and rel != "." or rel == ".":
                    # relpath returns ".." if outside; if not starting with "..", inside
                    if rel.startswith(".."):
                        continue
                    in_root = True
                    break
            except ValueError:
                continue
        result["allowed"] = in_root
        if not in_root:
            result["error"] = f"Path traversal attempt blocked: '{file_path}' resolves to '{target}' which is outside authorized workspace roots."
            return result

        # Check allowed subpaths
        result["within_subpath"] = self._check_subpath(str(target), file_path)
        if not result["within_subpath"]:
            result["error"] = f"Path '{file_path}' (resolved: {target}) not within allowed subpaths."
            result["allowed"] = False  # Not allowed if outside subpaths
        return result

    def _check_subpath(self, resolved_path: str, original_path: str) -> bool:
        # Check that the resolved path is within one of the allowed subpaths
        if not self.allowed_subpaths:
            return True
        if "." in self.allowed_subpaths:
            return True
        # Get workspace root (first root) for relative comparison
        workspace_root = str(self.workspace_roots[0]) if self.workspace_roots else "."
        try:
            # Compute relative path from workspace root to resolved file
            rel_path = os.path.relpath(resolved_path, workspace_root)
            # Check if relative path starts with any allowed subpath
            # Example: allowed "tests/" -> rel_path "tests/test_agent.py" allowed
            # Example: allowed "ml/" -> rel_path "ml/models/test.py" allowed
            rel_normalized = rel_path.replace(os.sep, "/").rstrip("/")
            for sub in self.allowed_subpaths:
                sub = sub.rstrip("/")
                sub_normalized = sub.replace(os.sep, "/")
                # File is within subpath if relative path equals subpath or starts with subpath + "/"
                if rel_normalized == sub_normalized or rel_normalized.startswith(sub_normalized + "/"):
                    return True
            return False
        except Exception:
            return False

    def is_path_allowed(self, file_path: str, workspace_base: Optional[str] = None) -> bool:
        result = self.resolve_path(file_path, workspace_base)
        return result["allowed"] and result["within_subpath"] and (result["error"] is None)

    def get_workspace_roots(self) -> List[str]:
        return [str(r) for r in self.workspace_roots]
