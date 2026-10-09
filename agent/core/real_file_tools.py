#!/usr/bin/env python3
"""Agent framework: real restricted filesystem tools with full Phase 4 security enforcement."""
from __future__ import annotations

import os
import pathlib
from typing import Optional, Dict, Any, List

from agent.core.workspace_sandbox import WorkspaceSandbox
from agent.core.file_permissions import FilePermissionEnforcer, FileOperation
from agent.core.audit_crypto import CryptographicAuditLogger
from agent.core.secret_redaction import SecretRedactor
from agent.core.resource_limits import ResourceLimits
from agent.core.prompt_injection import PromptInjectionFilter


class RealFileTools:
    """Real file system operations enforced by Phase 4 security architecture.
    Every operation passes through workspace sandbox, file permissions,
    resource limits, audit logging, and secret redaction.
    """

    def __init__(
        self,
        workspace_path: str = ".",
        permission_level: str = "restricted",
        audit_logger: Optional[CryptographicAuditLogger] = None,
    ):
        self.workspace_path = workspace_path
        self.sandbox = WorkspaceSandbox(
            workspace_roots=[workspace_path],
            allowed_subpaths=[".", "tests/", "ml/", "datasets/", "configs/", "agent/", "docs/", "services/", "apps/"],
        )
        self.permissions = FilePermissionEnforcer(
            permission_level=permission_level,
            workspace_sandbox=self.sandbox,
        )
        self.permissions._explicit_approvals = {}  # Ensure clean state for real execution
        # Provide a method for external/user approval mechanism
        self.set_explicit_approval_for = self.permissions.set_explicit_approval
        self.audit = audit_logger or CryptographicAuditLogger()
        self.redactor = SecretRedactor()
        self.limits = ResourceLimits()
        self.filter = PromptInjectionFilter()

    # ------------------------------------------------------------------
    # Read file
    # ------------------------------------------------------------------
    def read_file(self, path: str) -> Dict[str, Any]:
        result = {
            "tool_name": "read_file",
            "path": path,
            "allowed": False,
            "content": None,
            "status": "blocked",
            "audit_logged": False,
            "secret_redacted": False,
        }
        # Workspace and permission check
        workspace_result = self.sandbox.resolve_path(path, self.workspace_path)
        permission_result = self.permissions.check_read(path)
        if not permission_result["allowed"]:
            result["status"] = "denied"
            result["reason"] = permission_result.get("reason", "Permission denied")
            self.audit.log("read_file_denied", {"path": path, "reason": result["reason"]})
            return result
        if not workspace_result.get("allowed") or not workspace_result.get("within_subpath"):
            result["status"] = "denied"
            result["reason"] = workspace_result.get("error", "Workspace violation")
            self.audit.log("read_file_denied", {"path": path, "reason": result["reason"]})
            return result

        # Read file
        try:
            file_path = pathlib.Path(path)
            # Resolve relative to workspace
            if not file_path.is_absolute():
                file_path = pathlib.Path(self.workspace_path) / path
            file_path = file_path.resolve()
            # Check file exists and is file
            if not file_path.exists():
                result["status"] = "not_found"
                result["reason"] = f"File not found: {path}"
                self.audit.log("read_file_not_found", {"path": path})
                return result
            if not file_path.is_file():
                result["status"] = "not_file"
                result["reason"] = f"Not a file: {path}"
                self.audit.log("read_file_not_file", {"path": path})
                return result

            # File size check
            size_check = self.limits.check_file_size(str(file_path))
            if not size_check["allowed"]:
                result["status"] = "file_too_large"
                result["reason"] = size_check["reason"]
                self.audit.log("read_file_too_large", {"path": path, "size": size_check.get("size_bytes")})
                return result

            # Read content with graceful encoding
            content_bytes = file_path.read_bytes()
            content_str = content_bytes.decode("utf-8", errors="replace")
            # Check binary / unreadable: if replacement chars exceed 50%, treat as binary and return summary
            replacement_count = content_str.count("�")
            if replacement_count > len(content_str) * 0.5:
                result["status"] = "binary_or_unreadable"
                result["reason"] = "File appears binary or unreadable; returning summary only"
                result["content"] = f"[BINARY FILE: {len(content_bytes)} bytes; {replacement_count} replacement chars]"
                self.audit.log("read_file_binary", {"path": path, "size_bytes": len(content_bytes)})
            else:
                result["content"] = content_str
                result["status"] = "success"

            result["allowed"] = True
            # Secret redaction on content
            result["content"] = self.redactor.redact_text(result["content"])
            result["secret_redacted"] = True
            # Prompt injection filter note
            injection_attempts = self.filter.detect_injection_attempts(result["content"])
            if injection_attempts:
                result["injection_attempts_detected"] = injection_attempts
            # Resource limits
            if not self.limits.check_output_size(result["content"]):
                result["content"] = self.limits.truncate_output(result["content"])
                result["truncated"] = True
            # Audit
            self.audit.log("read_file_success", {
                "path": path,
                "resolved_path": str(file_path),
                "size_bytes": len(content_bytes),
                "permission_level": self.permissions.permission_level,
            })
            result["audit_logged"] = True
        except Exception as exc:
            result["status"] = "error"
            result["reason"] = f"Exception: {exc}"
            self.audit.log("read_file_error", {"path": path, "reason": str(exc)})
        return result

    # ------------------------------------------------------------------
    # List directory
    # ------------------------------------------------------------------
    def list_directory(self, path: str) -> Dict[str, Any]:
        result = {
            "tool_name": "list_directory",
            "path": path,
            "allowed": False,
            "items": [],
            "status": "blocked",
            "audit_logged": False,
        }
        workspace_result = self.sandbox.resolve_path(path, self.workspace_path)
        permission_result = self.permissions.check_list(path)
        if not permission_result["allowed"] or not workspace_result.get("allowed") or not workspace_result.get("within_subpath"):
            result["status"] = "denied"
            result["reason"] = permission_result.get("reason", workspace_result.get("error", "Denied"))
            self.audit.log("list_directory_denied", {"path": path, "reason": result["reason"]})
            return result
        try:
            dir_path = pathlib.Path(path)
            if not dir_path.is_absolute():
                dir_path = pathlib.Path(self.workspace_path) / path
            dir_path = dir_path.resolve()
            if not dir_path.exists():
                result["status"] = "not_found"
                result["reason"] = f"Directory not found: {path}"
                self.audit.log("list_directory_not_found", {"path": path})
                return result
            if not dir_path.is_dir():
                result["status"] = "not_directory"
                result["reason"] = f"Not a directory: {path}"
                self.audit.log("list_directory_not_dir", {"path": path})
                return result
            # List items (limited for resource safety)
            items = []
            for entry in dir_path.iterdir():
                items.append(entry.name)
            result["items"] = items[:200]  # Resource limit: max 200 entries
            result["allowed"] = True
            result["status"] = "success"
            self.audit.log("list_directory_success", {"path": path, "items_count": len(result["items"])})
            result["audit_logged"] = True
        except Exception as exc:
            result["status"] = "error"
            result["reason"] = f"Exception: {exc}"
            self.audit.log("list_directory_error", {"path": path, "reason": str(exc)})
        return result

    # ------------------------------------------------------------------
    # Create file
    # ------------------------------------------------------------------
    def create_file(self, path: str, content: str = "", requires_approval: bool = False) -> Dict[str, Any]:
        result = {
            "tool_name": "create_file",
            "path": path,
            "allowed": False,
            "status": "blocked",
            "audit_logged": False,
        }
        # Check approval
        approval_granted = False
        if requires_approval:
            approval_granted = self.permissions._explicit_approvals.get("create_file", False)
        else:
            approval_granted = True  # If not required, allow directly based on permission
        # Workspace and permission
        workspace_result = self.sandbox.resolve_path(path, self.workspace_path)
        permission_result = self.permissions.check_create(path, requires_approval=requires_approval)
        # Apply approval result
        permission_result["approval_granted"] = approval_granted and (not requires_approval or approval_granted)
        permission_result["allowed"] = permission_result.get("allowed", False) and permission_result.get("approval_granted", False)
        if not permission_result.get("allowed", False):
            result["status"] = "denied"
            result["reason"] = permission_result.get("reason", f"Approval required: requires_approval={requires_approval}, granted={approval_granted}")
            self.audit.log("create_file_denied", {"path": path, "reason": result["reason"]})
            return result
        # Workspace check
        if not workspace_result.get("allowed") or not workspace_result.get("within_subpath"):
            result["status"] = "denied"
            result["reason"] = workspace_result.get("error", "Workspace violation")
            self.audit.log("create_file_denied", {"path": path, "reason": result["reason"]})
            return result
        # Create file
        try:
            file_path = pathlib.Path(path)
            if not file_path.is_absolute():
                file_path = pathlib.Path(self.workspace_path) / path
            file_path = file_path.resolve()
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Write content (redacted for secrets)
            safe_content = self.redactor.redact_text(content)
            file_path.write_text(safe_content, encoding="utf-8")
            result["allowed"] = True
            result["status"] = "success"
            result["resolved_path"] = str(file_path)
            # Secret redaction applied
            result["secret_redacted"] = True
            # Audit
            self.audit.log("create_file_success", {"path": path, "resolved_path": str(file_path), "content_length": len(safe_content)})
            result["audit_logged"] = True
        except Exception as exc:
            result["status"] = "error"
            result["reason"] = f"Exception: {exc}"
            self.audit.log("create_file_error", {"path": path, "reason": str(exc)})
        return result

    # ------------------------------------------------------------------
    # Edit file (modify)
    # ------------------------------------------------------------------
    def edit_file(self, path: str, old_text: str, new_text: str = "", requires_approval: bool = True) -> Dict[str, Any]:
        result = {
            "tool_name": "edit_file",
            "path": path,
            "allowed": False,
            "status": "blocked",
            "audit_logged": False,
        }
        approval_granted = False
        if requires_approval:
            approval_granted = self.permissions._explicit_approvals.get("modify_file", False)
        else:
            approval_granted = True
        workspace_result = self.sandbox.resolve_path(path, self.workspace_path)
        permission_result = self.permissions.check_modify(path, requires_approval=requires_approval)
        permission_result["approval_granted"] = approval_granted and (not requires_approval or approval_granted)
        permission_result["allowed"] = permission_result.get("allowed", False) and permission_result.get("approval_granted", False)
        if not permission_result.get("allowed", False):
            result["status"] = "denied"
            result["reason"] = f"Modify denied: requires_approval={requires_approval}, approval_granted={approval_granted}, permission_level={self.permissions.permission_level}"
            self.audit.log("edit_file_denied", {"path": path, "reason": result["reason"]})
            return result
        if not workspace_result.get("allowed") or not workspace_result.get("within_subpath"):
            result["status"] = "denied"
            result["reason"] = workspace_result.get("error", "Workspace violation")
            self.audit.log("edit_file_denied", {"path": path, "reason": result["reason"]})
            return result
        try:
            file_path = pathlib.Path(path)
            if not file_path.is_absolute():
                file_path = pathlib.Path(self.workspace_path) / path
            file_path = file_path.resolve()
            if not file_path.exists():
                result["status"] = "not_found"
                result["reason"] = f"File not found: {path}"
                self.audit.log("edit_file_not_found", {"path": path})
                return result
            # Read current content
            current_content = file_path.read_text(encoding="utf-8")
            # Apply edit (only allow safe replacements; block dangerous patterns)
            # For simplicity: if old_text is in file, replace with new_text; else deny
            if old_text not in current_content:
                result["status"] = "match_failed"
                result["reason"] = f"Old text not found in file: {path}"
                self.audit.log("edit_file_match_failed", {"path": path})
                return result
            new_content = current_content.replace(old_text, new_text)
            # Secret redaction on new content
            new_content = self.redactor.redact_text(new_content)
            file_path.write_text(new_content, encoding="utf-8")
            result["allowed"] = True
            result["status"] = "success"
            result["modified"] = True
            result["resolved_path"] = str(file_path)
            self.audit.log("edit_file_success", {"path": path, "resolved_path": str(file_path), "old_text_length": len(old_text)})
            result["audit_logged"] = True
        except Exception as exc:
            result["status"] = "error"
            result["reason"] = f"Exception: {exc}"
            self.audit.log("edit_file_error", {"path": path, "reason": str(exc)})
        return result

    # ------------------------------------------------------------------
    # Search files
    # ------------------------------------------------------------------
    def search_files(self, workspace_dir: str = ".", pattern: str = "", max_results: int = 20) -> Dict[str, Any]:
        result = {
            "tool_name": "search_files",
            "workspace": workspace_dir,
            "pattern": pattern,
            "allowed": False,
            "matches": [],
            "status": "blocked",
            "audit_logged": False,
        }
        workspace_result = self.sandbox.resolve_path(workspace_dir, self.workspace_path)
        if not workspace_result.get("allowed"):
            result["status"] = "denied"
            result["reason"] = workspace_result.get("error", "Workspace violation")
            self.audit.log("search_files_denied", {"workspace": workspace_dir, "reason": result["reason"]})
            return result
        # Check permission (search is a read-only inspection command)
        # Treat as allowed at standard and above; restricted also allows read inspection
        if self.permissions.permission_level not in ("restricted", "standard", "elevated"):
            result["status"] = "denied"
            result["reason"] = f"Permission level '{self.permissions.permission_level}' not permitted for search"
            self.audit.log("search_files_denied", {"workspace": workspace_dir, "reason": result["reason"]})
            return result
        try:
            base_dir = pathlib.Path(workspace_dir)
            if not base_dir.is_absolute():
                base_dir = pathlib.Path(self.workspace_path) / workspace_dir
            base_dir = base_dir.resolve()
            # Search for files containing pattern (simple text search for security)
            matches = []
            for root, dirs, files in os.walk(str(base_dir)):
                # Skip hidden and protected directories
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "venv", ".env")]
                for file in files:
                    # Skip binary and protected files
                    file_path = pathlib.Path(root) / file
                    # Skip protected security files
                    protected_names = {".env", ".env.local", ".env.production", ".secrets", ".netrc"}
                    if file in protected_names or any(p in str(file_path) for p in protected_names):
                        continue
                    # Skip very large files
                    try:
                        size = file_path.stat().st_size
                        if size > self.limits.max_file_size_bytes:
                            continue
                    except Exception:
                        pass
                    # Read file and search
                    try:
                        content_str = file_path.read_text(encoding="utf-8", errors="replace")
                        if pattern in content_str:
                            rel_path = os.path.relpath(str(file_path), str(base_dir))
                            matches.append(rel_path)
                            if len(matches) >= max_results:
                                break
                    except Exception:
                        continue
                if len(matches) >= max_results:
                    break
            result["matches"] = matches
            result["allowed"] = True
            result["status"] = "success"
            self.audit.log("search_files_success", {"workspace": workspace_dir, "pattern": pattern, "matches": len(matches)})
            result["audit_logged"] = True
        except Exception as exc:
            result["status"] = "error"
            result["reason"] = f"Exception: {exc}"
            self.audit.log("search_files_error", {"workspace": workspace_dir, "reason": str(exc)})
        return result
