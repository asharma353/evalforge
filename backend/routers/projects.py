import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException

from schemas import AnalyzeRequest, ScanRequest, ScanResponse
from services.analyzer.engine import run_analysis
from services.file_scanner import scan_directory
from services.sse import sse_manager

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


@router.post("/analyze", status_code=202)
async def analyze_project(request: AnalyzeRequest):
    """Start background analysis of a project's LLM call sites.

    Accepts a project path and list of file paths to analyze.
    Returns 202 immediately; analysis progress and results are delivered
    via SSE events (analysis_progress, analysis_complete, analysis_error).

    Args:
        request: AnalyzeRequest with project_path and file_paths.

    Returns:
        202 Accepted with status message.
    """
    project_path = Path(request.project_path)

    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project path does not exist: {request.project_path}",
        )

    if not project_path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Project path is not a directory: {request.project_path}",
        )

    if not request.file_paths:
        raise HTTPException(
            status_code=400,
            detail="file_paths must be non-empty",
        )

    async def _run_with_error_handling():
        try:
            await run_analysis(request.project_path, request.file_paths)
        except Exception as exc:
            await sse_manager.send_event(
                "analysis_error",
                {
                    "error": str(exc),
                    "detail": "Analysis pipeline failed. Check server logs for details.",
                },
            )

    asyncio.create_task(_run_with_error_handling())

    return {
        "status": "analyzing",
        "message": "Analysis started. Listen to SSE for progress.",
    }
