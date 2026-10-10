from __future__ import annotations

from pathlib import Path


def resolve_portable_path(path: str | Path) -> Path:
    """Resolve a stored path that may use separators from another platform."""
    raw_path = str(path)
    native_path = Path(raw_path)
    if native_path.exists():
        return native_path
    portable_path = Path(raw_path.replace("\\", "/"))
    if portable_path.exists():
        return portable_path
    return native_path


def portable_path_string(path: str | Path) -> str:
    """Store paths relative to the project when possible, using POSIX separators."""
    resolved_path = resolve_portable_path(path).resolve()
    try:
        return resolved_path.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved_path.as_posix()
