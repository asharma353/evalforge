from pathlib import Path

from fastapi import APIRouter, HTTPException

from schemas import ScanRequest, ScanResponse
from services.file_scanner import scan_directory

router = APIRouter()


@router.post("/scan", response_model=ScanResponse)
async def scan_project(request: ScanRequest):
    """Accept a folder path and return a filtered file tree."""
    project_path = Path(request.path)

    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Path does not exist: {request.path}",
        )

    if not project_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {request.path}",
        )

    file_tree, total_files, supported_files = scan_directory(request.path)

    if supported_files == 0:
        raise HTTPException(
            status_code=400,
            detail="No supported files found in the provided directory.",
        )

    return ScanResponse(
        project_name=request.project_name,
        root_path=request.path,
        file_tree=file_tree,
        total_files=total_files,
        supported_files=supported_files,
    )
