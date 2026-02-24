"""Generation API router with SSE streaming.

Exposes POST /generate (mounted at /api/projects/generate by main.py).
Orchestrates the full generation pipeline and streams progress events via SSE.

Streaming event sequence:
1. failure_mode_found: one event per failure mode
2. evaluator_complete: one event per generated evaluator
3. test_data_complete: one event after all test data is generated
4. generation_complete: final event with full result summary
"""

import asyncio
import time

from fastapi import APIRouter

from services.generator.failure_modes import get_failure_modes
from services.generator.evaluator_generator import generate_evaluator, get_evaluator_filename
from services.test_data.dimension_extractor import extract_dimensions
from services.test_data.test_case_generator import generate_test_cases
from services.sse import sse_manager
from schemas import (
    FailureMode,
    EvaluatorFile,
    GenerationResult,
    GenerationProgress,
    GenerateRequest,
    TestCase,
    TestDataResult,
)

router = APIRouter()

# Module-level store for most recent generation results (keyed by timestamp)
_generation_results: dict[str, dict] = {}


async def run_generation(intent_model: dict) -> None:
    """Run the full generation pipeline and stream progress via SSE.

    Streams events to SSE in this order:
    1. failure_mode_found for each failure mode
    2. evaluator_complete for each generated evaluator
    3. test_data_complete after all test cases are generated
    4. generation_complete with full result summary

    Args:
        intent_model: Intent model dict from the frontend.
    """
    try:
        # Stage 1: Get failure modes
        modes = get_failure_modes(intent_model)

        for mode in modes:
            await sse_manager.send_event(
                "generation_progress",
                {
                    "stage": "failure_mode_found",
                    "failure_mode": mode,
                },
            )

        # Stage 2: Generate evaluators for each failure mode
        evaluators: list[dict] = []
        generation_source = "static_fallback"

        for mode in modes:
            code = generate_evaluator(mode)
            filename = get_evaluator_filename(mode["id"])
            evaluator = {
                "failure_mode_id": mode["id"],
                "filename": filename,
                "evaluator_type": mode.get("evaluator_type", "assertion"),
                "code": code,
                "description": mode.get("description", ""),
            }
            evaluators.append(evaluator)

            # Stream a lightweight summary (no full code to keep event small)
            await sse_manager.send_event(
                "generation_progress",
                {
                    "stage": "evaluator_complete",
                    "evaluator": {
                        "filename": filename,
                        "failure_mode_id": mode["id"],
                        "evaluator_type": mode.get("evaluator_type", "assertion"),
                        "description": mode.get("description", ""),
                    },
                },
            )

        # Stage 3: Generate test data for each failure mode
        all_test_cases: list[dict] = []

        for mode in modes:
            dims = extract_dimensions(intent_model, mode)
            cases = generate_test_cases(intent_model, mode, dims, count=12)
            all_test_cases.extend(cases)

        await sse_manager.send_event(
            "generation_progress",
            {
                "stage": "test_data_complete",
                "test_case_count": len(all_test_cases),
            },
        )

        # Determine generation source based on whether LLM was used
        import os
        if os.environ.get("ANTHROPIC_API_KEY"):
            generation_source = "llm"

        # Build final result
        result = {
            "failure_modes": modes,
            "evaluators": evaluators,
            "generation_source": generation_source,
            "test_cases": all_test_cases,
        }

        # Store with timestamp key for later retrieval
        ts_key = str(int(time.time()))
        _generation_results[ts_key] = result
        # Keep only the 10 most recent results
        if len(_generation_results) > 10:
            oldest_key = min(_generation_results.keys())
            del _generation_results[oldest_key]

        # Stage 4: Final completion event
        await sse_manager.send_event(
            "generation_complete",
            {
                "failure_mode_count": len(modes),
                "evaluator_count": len(evaluators),
                "test_case_count": len(all_test_cases),
                "generation_source": generation_source,
            },
        )

    except Exception as exc:
        await sse_manager.send_event(
            "generation_error",
            {"error": str(exc)},
        )


@router.post("/generate", status_code=202)
async def generate(request: GenerateRequest):
    """Start the generation pipeline and stream progress via SSE.

    Accepts an intent_model dict, starts the full pipeline as a background
    task, and returns 202 immediately. Generation progress and results are
    delivered via SSE events at /api/sse.

    SSE event sequence:
    - generation_progress (stage: failure_mode_found) per failure mode
    - generation_progress (stage: evaluator_complete) per evaluator
    - generation_progress (stage: test_data_complete) once test data done
    - generation_complete with counts and source summary

    Args:
        request: GenerateRequest with intent_model dict.

    Returns:
        202 Accepted with status message.
    """
    asyncio.create_task(run_generation(request.intent_model))
    return {
        "status": "started",
        "message": "Generation started. Listen to SSE for progress.",
    }


@router.get("/generate/result")
async def get_generation_result():
    """Return the most recent generation result.

    Returns the last stored generation result from _generation_results.
    Used by Phase 5 export to retrieve the completed generation data.

    Returns:
        Most recent generation result dict, or 404 if no results exist.
    """
    if not _generation_results:
        return {"status": "no_results", "message": "No generation results available yet."}

    most_recent_key = max(_generation_results.keys())
    return {
        "status": "ok",
        "result": _generation_results[most_recent_key],
    }
