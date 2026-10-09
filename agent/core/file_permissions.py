#!/usr/bin/env python3
"""Agent framework: explicit file operation permissions checked by the tool layer."""
from __future__ import annotations

from typing import Optional, Dict, Any, List
from enum import Enum

from agent.core.workspace_sandbox import WorkspaceSandbox


class FileOperation(str, Enum):
    READ_FILE = "read_file"
    LIST_DIR = "list_dir"
    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"
    DELETE_FILE = "delete_file"
    RENAME_FILE = "rename_file"
    RUN_SHELL = "run_shell"
    READ_FILE_MOCK = "read_file_mock"


# Safe defaults: only read-only allowed at restricted level
PERMISSION_MAP = {
    "restricted": {
        FileOperation.READ_FILE: True,
        FileOperation.LIST_DIR: True,
        FileOperation.CREATE_FILE: False,
        FileOperation.MODIFY_FILE: False,
        FileOperation.DELETE_FILE: False,
        FileOperation.RENAME_FILE: False,
        FileOperation.RUN_SHELL: False,
        FileOperation.READ_FILE_MOCK: True,
    },
    "standard": {
        FileOperation.READ_FILE: True,
        FileOperation.LIST_DIR: True,
        FileOperation.CREATE_FILE: True,
        FileOperation.MODIFY_FILE: True,
        FileOperation.DELETE_FILE: False,
        FileOperation.RENAME_FILE: False,
        FileOperation.RUN_SHELL: False,
        FileOperation.READ_FILE_MOCK: True,
    },
    "elevated": {
        FileOperation.READ_FILE: True,
        FileOperation.LIST_DIR: True,
        FileOperation.CREATE_FILE: True,
        FileOperation.MODIFY_FILE: True,
        FileOperation.DELETE_FILE: True,
        FileOperation.RENAME_FILE: True,
        FileOperation.RUN_SHELL: True,
        FileOperation.READ_FILE_MOCK: True,
    },
}


class FilePermissionEnforcer:
    """Explicit file-level permission enforcement independent of model behavior.

    Every file operation request passes through this enforcer. The authorization
    layer (not the model) decides whether the operation is permitted.
    """

    def __init__(self, permission_level: str = "restricted", workspace_sandbox: Optional[WorkspaceSandbox] = None):
        if permission_level not in PERMISSION_MAP:
            raise ValueError(f"Unknown permission level: {permission_level}")
        self.permission_level = permission_level
        self.sandbox = workspace_sandbox or WorkspaceSandbox()
        # Store explicit authorization for high-impact operations (must be set externally)
        self._explicit_approvals: Dict[str, bool] = {}

    def is_operation_allowed(self, operation: FileOperation, path: Optional[str] = None) -> bool:
        level_perm = PERMISSION_MAP[self.permission_level]
        if operation not in level_perm:
            return False
        # If operation is a file operation with a path, enforce workspace
        if path is not None and operation not in (FileOperation.RUN_SHELL,):
            allowed_path = self.sandbox.is_path_allowed(path)
            if not allowed_path:
                return False
        return level_perm.get(operation, False)

    def check_read(self, path: str) -> Dict[str, Any]:
        allowed = self.is_operation_allowed(FileOperation.READ_FILE, path)
        workspace_check = self.sandbox.resolve_path(path) if allowed else {"allowed": False, "error": "Operation not permitted at this permission level"}
        return {
            "operation": "read_file",
            "path": path,
            "allowed": allowed,
            "permission_level": self.permission_level,
            "workspace_check": workspace_check,
        }

    def check_list(self, path: str) -> Dict[str, Any]:
        allowed = self.is_operation_allowed(FileOperation.LIST_DIR, path)
        workspace_check = self.sandbox.resolve_path(path) if allowed else {"allowed": False, "error": "Operation not permitted at this permission level"}
        return {
            "operation": "list_dir",
            "path": path,
            "allowed": allowed,
            "permission_level": self.permission_level,
            "workspace_check": workspace_check,
        }

    def check_create(self, path: str, requires_approval: bool = False) -> Dict[str, Any]:
        allowed_op = self.is_operation_allowed(FileOperation.CREATE_FILE, path)
        # Explicit external approval can override restricted base permission for high-impact actions
        explicit_approval = self._explicit_approvals.get("create_file", False) is True
        approval_granted = not requires_approval or (explicit_approval is True)
        # Workspace check always required
        workspace_check = self.sandbox.resolve_path(path) if (allowed_op or explicit_approval) else {"allowed": False, "error": "Operation not permitted at this permission level and no explicit approval"}
        # If explicit approval granted, allow workspace-validated operations
        final_allowed = (allowed_op and approval_granted) or (explicit_approval and workspace_check.get("allowed", False))
        return {
            "operation": "create_file",
            "path": path,
            "allowed": final_allowed,
            "approval_required": requires_approval,
            "approval_granted": approval_granted,
            "permission_level": self.permission_level,
            "workspace_check": workspace_check,
        }

    def check_modify(self, path: str, requires_approval: bool = False) -> Dict[str, Any]:
        allowed = self.is_operation_allowed(FileOperation.MODIFY_FILE, path)
        approval_granted = not requires_approval or (self._explicit_approvals.get("modify_file", False) is True)
        if not allowed:
            approval_granted = False
        workspace_check = self.sandbox.resolve_path(path) if allowed else {"allowed": False, "error": "Operation not permitted at this permission level"}
        return {
            "operation": "modify_file",
            "path": path,
            "allowed": allowed and approval_granted,
            "approval_required": requires_approval,
            "approval_granted": approval_granted,
            "permission_level": self.permission_level,
            "workspace_check": workspace_check,
        }

    def check_delete(self, path: str, requires_approval: bool = True) -> Dict[str, Any]:
        allowed = self.is_operation_allowed(FileOperation.DELETE_FILE, path)
        approval_granted = self._explicit_approvals.get("delete_file", False) is True
        if not allowed or not approval_granted:
            allowed = False
        workspace_check = self.sandbox.resolve_path(path) if allowed else {"allowed": False, "error": "Operation not permitted at this permission level"}
        return {
            "operation": "delete_file",
            "path": path,
            "allowed": allowed,
            "approval_required": requires_approval,
            "approval_granted": approval_granted,
            "permission_level": self.permission_level,
            "workspace_check": workspace_check,
        }

    def check_rename(self, path: str, new_path: str, requires_approval: bool = True) -> Dict[str, Any]:
        allowed_op = self.is_operation_allowed(FileOperation.RENAME_FILE, path)
        # Check new path workspace validity
        workspace_new = self.sandbox.resolve_path(new_path)
        workspace_check = workspace_new if allowed_op else {"allowed": False, "error": "Operation not permitted at this permission level"}
        approval_granted = self._explicit_approvals.get("rename_file", False) is True
        allowed = allowed_op and (workspace_new.get("allowed", False) if isinstance(workspace_new, dict) else allowed_op) and approval_granted
        return {
            "operation": "rename_file",
            "path": path,
            "new_path": new_path,
            "allowed": allowed,
            "approval_required": requires_approval,
            "approval_granted": approval_granted,
            "permission_level": self.permission_level,
            "workspace_check": workspace_check,
        }

    def set_explicit_approval(self, operation_key: str, granted: bool = True):
        """Explicit approval mechanism — must come from user, not model."""
        self._explicit_approvals[operation_key] = granted

    def clear_approvals(self):
        self._explicit_approvals.clear()
