"""Export API router.

Exposes POST /export (mounted at /api/projects/export by main.py).
Builds an in-memory zip of the eval suite from the most recent generation
result and returns it as a StreamingResponse.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.generation import _generation_results
from services.export.package_builder import build_export_zip

router = APIRouter()


class ExportRequest(BaseModel):
    """Selection filter for the export endpoint."""

    enabled_evaluator_ids: list[str]
    enabled_test_case_indices: list[int]


@router.post("/export")
async def export_eval_package(request: ExportRequest):
    """Build and return a zip of the selected eval suite.

    Reads the most recent generation result from *_generation_results*,
    applies the caller's selection filter, and returns the zip as a
    ``StreamingResponse`` with ``Content-Disposition: attachment``.

    If no generation results exist, returns a JSON body with
    ``status: no_results`` instead of a zip.

    Args:
        request: ExportRequest containing enabled_evaluator_ids and
            enabled_test_case_indices.

    Returns:
        StreamingResponse (application/zip) or JSON error dict.
    """
    if not _generation_results:
        return {
            "status": "no_results",
            "message": "No generation results available. Please run generation first.",
        }

    most_recent_key = max(_generation_results.keys())
    result = _generation_results[most_recent_key]

    buffer = build_export_zip(
        failure_modes=result.get("failure_modes", []),
        evaluators=result.get("evaluators", []),
        test_cases=result.get("test_cases", []),
        enabled_evaluator_ids=request.enabled_evaluator_ids,
        enabled_test_case_indices=request.enabled_test_case_indices,
    )

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=eval_suite.zip"},
    )
