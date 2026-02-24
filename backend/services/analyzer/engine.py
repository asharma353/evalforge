"""Analysis pipeline orchestrator with SSE progress streaming.

Two-pass pipeline:
  Pass 1 (Parsing + Detection): Parse each file and detect LLM call sites.
  Pass 2 (Extraction + Classification): Extract prompts and classify app type.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TypedDict

from services.sse import sse_manager

from .app_classifier import AppTypeResult, classify_app_type
from .call_detector import CallSite, detect_call_sites
from .prompt_extractor import extract_prompts


class AnalysisResult(TypedDict):
    """Complete analysis result returned by run_analysis."""

    call_sites: list[dict]      # CallSite dicts with prompts attached
    app_type: AppTypeResult
    summary: dict               # total_files_analyzed, files_with_calls, total_call_sites


async def run_analysis(project_path: str, file_paths: list[str]) -> AnalysisResult:
    """Run the two-pass code analysis pipeline with SSE progress streaming.

    Pass 1: Parse each file and detect LLM call sites. Streams analysis_progress
            events with stage="parsing" after each file.

    Pass 2: Extract prompts from each call site and classify app type. Streams
            analysis_progress events with stage="analyzing" after each call site.

    Final: Streams analysis_complete event with the full result payload.

    Args:
        project_path: Root path of the project.
        file_paths: List of file paths to analyze (relative or absolute).

    Returns:
        AnalysisResult with call_sites, app_type, and summary.
    """
    total_files = len(file_paths)
    all_call_sites: list[CallSite] = []
    file_contents: dict[str, str] = {}
    files_with_calls: set[str] = set()

    # Pass 1: Parse + Detect
    for i, file_path in enumerate(file_paths):
        # Read file content
        full_path = Path(project_path) / file_path if not Path(file_path).is_absolute() else Path(file_path)
        try:
            source_code = full_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            source_code = ""

        if source_code:
            file_contents[file_path] = source_code
            # Detect call sites in this file
            sites = detect_call_sites(project_path, file_path, source_code)
            if sites:
                all_call_sites.extend(sites)
                files_with_calls.add(file_path)

        # Stream progress after each file
        await sse_manager.send_event(
            "analysis_progress",
            {
                "stage": "parsing",
                "current": i + 1,
                "total": total_files,
                "detail": f"Parsing {file_path}",
            },
        )

    # Pass 2: Extract prompts
    total_call_sites = len(all_call_sites)
    enriched_call_sites: list[dict] = []

    for i, site in enumerate(all_call_sites):
        file_path = site["file_path"]
        source_code = file_contents.get(file_path, "")

        # Extract prompts from this call site
        prompts = extract_prompts(site, source_code)

        # Attach prompts to the call site dict
        enriched = dict(site)
        enriched["prompts"] = [dict(p) for p in prompts]
        enriched_call_sites.append(enriched)

        # Stream progress after each call site
        await sse_manager.send_event(
            "analysis_progress",
            {
                "stage": "analyzing",
                "current": i + 1,
                "total": max(total_call_sites, 1),
                "detail": f"Extracting prompts from {file_path} ({site['framework']}:{site['method']})",
            },
        )

    # Classify app type from all signals
    app_type = classify_app_type(all_call_sites, file_contents)

    # Build summary
    summary = {
        "total_files_analyzed": total_files,
        "files_with_calls": len(files_with_calls),
        "total_call_sites": total_call_sites,
    }

    result = AnalysisResult(
        call_sites=enriched_call_sites,
        app_type=app_type,
        summary=summary,
    )

    # Stream the complete event with full payload (MUST be last)
    await sse_manager.send_event(
        "analysis_complete",
        {
            "call_sites": enriched_call_sites,
            "app_type": dict(app_type),
            "summary": summary,
        },
    )

    return result
