from __future__ import annotations

from pydantic import BaseModel


class ScanRequest(BaseModel):
    path: str
    project_name: str


class FileNode(BaseModel):
    name: str
    path: str  # relative to project root
    is_dir: bool
    children: list[FileNode] | None = None
    extension: str | None = None


class ScanResponse(BaseModel):
    project_name: str
    root_path: str
    file_tree: list[FileNode]
    total_files: int
    supported_files: int
