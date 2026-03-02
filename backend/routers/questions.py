"""API router for guided question generation and answer submission.

Provides two endpoints:
  POST /generate — Generate tailored questions from analysis results.
  POST /submit   — Submit answers and build the intent model for eval generation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from schemas import (
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    IntentModelResponse,
    Question,
    SubmitAnswersRequest,
)
from services.questioner.generator import generate_questions
from services.questioner.intent_model import build_intent_model

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=GenerateQuestionsResponse)
async def generate_tailored_questions(request: GenerateQuestionsRequest):
    """Generate tailored questions based on analysis results.

    Uses LLM-powered question generation with automatic fallback to
    static question bank on any failure. Always returns questions.

    Args:
        request: Contains analysis_result dict from the analysis pipeline.

    Returns:
        GenerateQuestionsResponse with questions and generation_source.
    """
    try:
        questions, source = await generate_questions(request.analysis_result)
        return GenerateQuestionsResponse(
            questions=[Question(**q) for q in questions],
            generation_source=source,
        )
    except Exception as exc:
        # Last-resort fallback -- generator itself handles most errors,
        # but catch anything remaining (e.g., schema validation)
        logger.error("Question generation endpoint error: %s", exc)
        from services.questioner.question_bank import get_static_questions

        app_type = request.analysis_result.get("app_type", {}).get("type", "general")
        questions = get_static_questions(app_type)
        return GenerateQuestionsResponse(
            questions=[Question(**q) for q in questions],
            generation_source="static_fallback",
        )


@router.post("/submit", response_model=IntentModelResponse)
async def submit_answers(request: SubmitAnswersRequest):
    """Submit question answers and build the intent model.

    Combines analysis results with user answers (and defaults for skipped
    questions) to produce the structured intent model consumed by Phase 4
    eval generation.

    Args:
        request: Contains analysis_result, answers dict, and skipped list.

    Returns:
        IntentModelResponse with the complete intent model dict.
    """
    try:
        intent_model = build_intent_model(
            analysis_result=request.analysis_result,
            answers=request.answers,
            skipped=request.skipped,
            custom_qa=[pair.model_dump() for pair in request.custom_qa],  # QUES-04
        )
        return IntentModelResponse(intent_model=intent_model)
    except Exception as exc:
        logger.error("Intent model building failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build intent model: {str(exc)}",
        ) from exc
