"""File scanner service with .gitignore support and type filtering."""

import os
from pathlib import Path

import pathspec

from schemas import FileNode

# Extensions and filenames considered "supported" for code analysis
SUPPORTED_EXTENSIONS: set[str] = {
    ".py",
    ".ts",
    ".js",
    ".tsx",
    ".jsx",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".cfg",
    ".ini",
}

# Exact filenames (no extension match) that are supported
SUPPORTED_FILENAMES: set[str] = {
    ".env.example",
    ".gitignore",
    "Dockerfile",
    "Makefile",
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "tsconfig.json",
}

# Patterns always excluded regardless of .gitignore
DEFAULT_EXCLUDES: list[str] = [
    ".git/",
    "__pycache__/",
    "node_modules/",
    ".venv/",
    "venv/",
    ".env",
    "*.pyc",
    ".DS_Store",
]


def _load_gitignore(root_path: Path) -> pathspec.PathSpec | None:
    """Load .gitignore from project root if it exists."""
    gitignore_path = root_path / ".gitignore"
    if gitignore_path.is_file():
        try:
            lines = gitignore_path.read_text().splitlines()
            return pathspec.PathSpec.from_lines("gitwildmatch", lines)
        except (OSError, PermissionError):
            return None
    return None


def _is_supported_file(name: str) -> bool:
    """Check if a file is a supported type by extension or exact name."""
    if name in SUPPORTED_FILENAMES:
        return True
    _, ext = os.path.splitext(name)
    return ext.lower() in SUPPORTED_EXTENSIONS


def _is_default_excluded(rel_path: str, is_dir: bool) -> bool:
    """Check if a path matches default exclusion patterns."""
    default_spec = pathspec.PathSpec.from_lines("gitwildmatch", DEFAULT_EXCLUDES)
    # For directories, check both with and without trailing slash
    if is_dir:
        return default_spec.match_file(rel_path + "/") or default_spec.match_file(
            rel_path
        )
    return default_spec.match_file(rel_path)


def scan_directory(root_path: str) -> tuple[list[FileNode], int, int]:
    """Scan a directory and return a filtered file tree.

    Respects .gitignore rules and filters to supported file extensions only.
    Always excludes .git, __pycache__, node_modules, .venv, venv, .env, *.pyc, .DS_Store.

    Args:
        root_path: Absolute path to the project directory.

    Returns:
        Tuple of (file_tree, total_files_scanned, supported_files_count)
    """
    root = Path(root_path).resolve()
    gitignore_spec = _load_gitignore(root)

    total_files = 0
    supported_files = 0

    def _scan_dir(dir_path: Path) -> list[FileNode]:
        nonlocal total_files, supported_files

        children: list[FileNode] = []
        dirs: list[tuple[str, Path]] = []
        files: list[tuple[str, Path]] = []

        try:
            entries = sorted(dir_path.iterdir(), key=lambda e: e.name.lower())
        except (PermissionError, OSError):
            return []

        for entry in entries:
            rel_path = str(entry.relative_to(root))

            # Check default excludes
            if _is_default_excluded(rel_path, entry.is_dir()):
                continue

            # Check .gitignore
            if gitignore_spec is not None:
                if entry.is_dir():
                    if gitignore_spec.match_file(
                        rel_path + "/"
                    ) or gitignore_spec.match_file(rel_path):
                        continue
                else:
                    if gitignore_spec.match_file(rel_path):
                        continue

            if entry.is_dir():
                dirs.append((entry.name, entry))
            elif entry.is_file():
                files.append((entry.name, entry))

        # Process directories first (alphabetically)
        for name, entry in dirs:
            rel_path = str(entry.relative_to(root))
            sub_children = _scan_dir(entry)
            # Only include directories that contain at least one supported file
            if sub_children:
                children.append(
                    FileNode(
                        name=name,
                        path=rel_path,
                        is_dir=True,
                        children=sub_children,
                    )
                )

        # Process files (alphabetically)
        for name, entry in files:
            total_files += 1
            if _is_supported_file(name):
                supported_files += 1
                rel_path = str(entry.relative_to(root))
                _, ext = os.path.splitext(name)
                children.append(
                    FileNode(
                        name=name,
                        path=rel_path,
                        is_dir=False,
                        extension=ext if ext else None,
                    )
                )

        return children

    file_tree = _scan_dir(root)
    return file_tree, total_files, supported_files
