"""
Path utilities for Manatrix.

Provides security functions for path validation, workspace management,
and safe file operations.
"""

import os
import re
from pathlib import Path
from typing import Optional, Union


# Workspace root configuration
_workspace_root: Optional[Path] = None


def get_workspace_root() -> Path:
    """
    Get the current workspace root directory.

    Returns:
        Path to the workspace root
    """
    global _workspace_root

    if _workspace_root is None:
        _workspace_root = Path.cwd()

    return _workspace_root


def set_workspace_root(path: Union[str, Path]) -> None:
    """
    Set the workspace root directory.

    Args:
        path: New workspace root path

    Note:
        Setting workspace root limits file access to paths within
        the workspace for security purposes (path traversal protection).
    """
    global _workspace_root

    path = Path(path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Workspace path does not exist: {path}")

    if not path.is_dir():
        raise NotADirectoryError(f"Workspace path is not a directory: {path}")

    _workspace_root = path


def ensure_safe_path(
    file_path: Union[str, Path],
    workspace_root: Optional[Path] = None,
    allow_absolute: bool = True
) -> Path:
    """
    Ensure a file path is safe (within workspace bounds).

    Args:
        file_path: Path to validate
        workspace_root: Workspace root to check against (uses global if None)
        allow_absolute: Whether to allow absolute paths outside workspace

    Returns:
        Resolved safe path

    Raises:
        ValueError: If path is unsafe (path traversal attempt)
        PermissionError: If path is outside workspace

    Example:
        >>> safe_path = ensure_safe_path("../etc/passwd")
        # Raises ValueError
    """
    file_path = Path(file_path)

    # Get workspace root
    if workspace_root is None:
        workspace_root = get_workspace_root()

    # Normalize the path
    try:
        resolved = file_path.resolve()
    except (OSError, RuntimeError):
        # On resolve error, try relative
        resolved = (workspace_root / file_path).resolve()

    # Check if path is within workspace
    workspace = workspace_root.resolve()
    try:
        resolved.relative_to(workspace)
        return resolved
    except ValueError:
        # Path traversal detected
        if allow_absolute:
            # Allow absolute paths outside workspace (with warning)
            return resolved
        else:
            raise ValueError(
                f"Path traversal detected: {file_path} resolves to {resolved}, "
                f"which is outside workspace {workspace}"
            )


def is_safe_path(
    file_path: Union[str, Path],
    workspace_root: Optional[Path] = None
) -> bool:
    """
    Check if a file path is safe (within workspace bounds).

    Args:
        file_path: Path to check
        workspace_root: Workspace root to check against

    Returns:
        True if path is safe, False otherwise

    Example:
        >>> if is_safe_path(user_input):
        ...     open_file(user_input)
    """
    try:
        ensure_safe_path(file_path, workspace_root, allow_absolute=False)
        return True
    except (ValueError, PermissionError):
        return False


def get_safe_path_components(
    file_path: Union[str, Path],
    max_depth: int = 10
) -> list[str]:
    """
    Get safe path components (no '..' or absolute paths).

    Args:
        file_path: Path to process
        max_depth: Maximum allowed path depth

    Returns:
        List of safe path components

    Example:
        >>> components = get_safe_path_components("/workspace/../etc/passwd")
        >>> print(components)  # ['workspace']
    """
    file_path = Path(file_path)
    parts = []

    for part in file_path.parts:
        # Skip absolute path markers
        if part in ("/", "\\"):
            continue

        # Skip parent directory references
        if part == "..":
            if parts:
                parts.pop()
            continue

        # Skip current directory references
        if part == ".":
            continue

        parts.append(part)

        # Check depth
        if len(parts) > max_depth:
            raise ValueError(f"Path depth exceeds maximum: {max_depth}")

    return parts


def normalize_path(path: Union[str, Path]) -> str:
    """
    Normalize a path for consistent handling across platforms.

    Args:
        path: Path to normalize

    Returns:
        Normalized path string

    Example:
        >>> normalize_path("./foo/bar/../baz")
        'foo/baz'
    """
    path = Path(path)

    # Convert to forward slashes
    parts = get_safe_path_components(path)

    return "/".join(parts) if parts else ""


def safe_join(*paths: Union[str, Path]) -> Path:
    """
    Safely join path components.

    Args:
        *paths: Path components to join

    Returns:
        Joined path

    Example:
        >>> safe_path = safe_join("workspace", "data", "file.txt")
    """
    if not paths:
        return Path()

    # Start with first path
    result = Path(paths[0])

    # Join remaining paths safely
    for p in paths[1:]:
        p = Path(p)

        # Check for absolute paths in subsequent components
        if p.is_absolute():
            raise ValueError(f"Cannot join absolute path: {p}")

        result = result / p

    return result


def get_relative_path(
    path: Union[str, Path],
    base: Union[str, Path] = None
) -> Path:
    """
    Get relative path from base directory.

    Args:
        path: Target path
        base: Base directory (uses workspace if None)

    Returns:
        Relative path

    Example:
        >>> rel = get_relative_path("/workspace/data/file.txt")
        'data/file.txt'
    """
    if base is None:
        base = get_workspace_root()

    path = Path(path).resolve()
    base = Path(base).resolve()

    try:
        return path.relative_to(base)
    except ValueError:
        # Not relative, return original
        return path


def list_safe_directory(
    directory: Union[str, Path],
    pattern: Optional[str] = None,
    recursive: bool = False
) -> list[Path]:
    """
    List files in a directory safely.

    Args:
        directory: Directory to list
        pattern: Glob pattern to filter files
        recursive: Whether to search recursively

    Returns:
        List of safe file paths

    Example:
        >>> files = list_safe_directory("data", "*.txt")
        >>> files = list_safe_directory("data", recursive=True)
    """
    directory = ensure_safe_path(directory)

    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    if recursive:
        if pattern:
            return list(directory.rglob(pattern))
        else:
            return [p for p in directory.rglob("*") if p.is_file()]
    else:
        if pattern:
            return list(directory.glob(pattern))
        else:
            return [p for p in directory.iterdir() if p.is_file()]


# File size constants
BYTE = 1
KB = 1024 * BYTE
MB = 1024 * KB
GB = 1024 * MB


def format_file_size(size: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size: File size in bytes

    Returns:
        Formatted size string

    Example:
        >>> format_file_size(1024)
        '1.00 KB'
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} PB"


def get_file_info(path: Union[str, Path]) -> dict:
    """
    Get file information safely.

    Args:
        path: Path to file

    Returns:
        Dictionary with file info (size, mtime, is_dir, etc.)
    """
    path = ensure_safe_path(path)

    stat = path.stat()

    return {
        "name": path.name,
        "path": str(path),
        "size": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "modified": stat.st_mtime,
        "is_dir": path.is_dir(),
        "is_file": path.is_file(),
        "extension": path.suffix,
    }