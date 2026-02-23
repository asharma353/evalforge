"""File scanner service - placeholder for Task 2 implementation."""

from schemas import FileNode


def scan_directory(root_path: str) -> tuple[list[FileNode], int, int]:
    """Scan a directory and return filtered file tree.

    Returns:
        Tuple of (file_tree, total_files_scanned, supported_files_count)
    """
    raise NotImplementedError("scan_directory will be implemented in Task 2")
