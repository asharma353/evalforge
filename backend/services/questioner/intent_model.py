"""Intent model builder combining analysis results with user answers.

Produces the structured intent model that Phase 4 (eval generation)
consumes to generate tailored evaluators.
"""

from __future__ import annotations

import logging

from .question_bank import get_static_questions

logger = logging.getLogger(__name__)

# Category mapping: question ID prefix -> category
_CATEGORY_KEYWORDS = {
    "quality": "quality_criteria",
    "faithfulness": "quality_criteria",
    "accuracy": "quality_criteria",
    "output_quality": "quality_criteria",
    "response_quality": "quality_criteria",
    "extraction_accuracy": "quality_criteria",
    "output_format": "quality_criteria",
    "tone": "quality_criteria",
    "task_completion": "quality_criteria",
    "tool_usage": "quality_criteria",
    "failure": "failure_concerns",
    "error": "failure_concerns",
    "safety": "failure_concerns",
    "stale": "failure_concerns",
    "off_topic": "failure_concerns",
    "hallucination": "failure_concerns",
    "loop": "failure_concerns",
    "boundary": "failure_concerns",
    "malformed": "failure_concerns",
    "data_loss": "failure_concerns",
    "domain": "domain_specifics",
    "use_case": "domain_specifics",
    "document_types": "domain_specifics",
    "domain_tools": "domain_specifics",
    "domain_type": "domain_specifics",
    "format": "expected_behaviors",
    "expected": "expected_behaviors",
    "latency": "expected_behaviors",
    "steps": "expected_behaviors",
    "reporting": "expected_behaviors",
    "conversation_length": "expected_behaviors",
    "multilingual": "expected_behaviors",
    "throughput": "expected_behaviors",
    "consistency": "expected_behaviors",
    "citation": "expected_behaviors",
    "response_format": "expected_behaviors",
}


def _infer_category(question_id: str) -> str:
    """Infer category from question ID using keyword matching.

    Args:
        question_id: The question's unique identifier.

    Returns:
        The inferred category string.
    """
    # Check each keyword against the question ID
    for keyword, category in _CATEGORY_KEYWORDS.items():
        if keyword in question_id:
            return category
    return "domain_specifics"  # safe default


def _get_question_defaults(app_type: str) -> dict[str, str | list[str]]:
    """Build a mapping of question ID to default value for the given app type.

    Args:
        app_type: The classified application type.

    Returns:
        Dict mapping question IDs to their default values.
    """
    questions = get_static_questions(app_type)
    return {q["id"]: q["default"] for q in questions}


def build_intent_model(
    analysis_result: dict,
    answers: dict[str, str | list[str]],
    skipped: list[str],
    custom_qa: list[dict] | None = None,
) -> dict:
    """Build the intent model from analysis results and user answers.

    Combines code analysis with user-provided answers about their quality
    criteria, failure concerns, domain specifics, and expected behaviors
    to produce a structured intent model for eval generation.

    For skipped questions, sensible defaults from the question bank are used.

    Custom Q&A pairs (QUES-04) are merged into domain_context, allowing
    developers to inject domain knowledge the analysis did not capture.

    Args:
        analysis_result: The analysis result dict from the analysis pipeline.
        answers: Dict mapping question IDs to answer values.
        skipped: List of question IDs that were skipped.
        custom_qa: Optional list of dicts with 'question' and 'answer' keys
            representing free-form developer-provided domain knowledge.

    Returns:
        Dict conforming to IntentModel schema.
    """
    # Extract from analysis_result
    app_type_info = analysis_result.get("app_type", {})
    app_type = app_type_info.get("type", "general")
    app_type_confidence = app_type_info.get("confidence", 0.0)

    call_sites = analysis_result.get("call_sites", [])
    frameworks = list({cs.get("framework", "unknown") for cs in call_sites})
    call_site_count = len(call_sites)

    # Build prompt summary
    prompt_summary = []
    for cs in call_sites:
        for prompt in cs.get("prompts", []):
            prompt_summary.append({
                "role": prompt.get("role", "unknown"),
                "content_preview": prompt.get("content", "")[:200],
                "is_dynamic": prompt.get("is_dynamic", False),
            })

    # Get defaults for skipped questions
    defaults = _get_question_defaults(app_type)

    # Merge answers with defaults for skipped
    effective_answers = dict(answers)
    for qid in skipped:
        if qid not in effective_answers:
            effective_answers[qid] = defaults.get(qid, "")

    # Categorize answers
    quality_criteria: list[str] = []
    failure_concerns: list[str] = []
    domain_context_parts: list[str] = []
    expected_behaviors: list[dict] = []

    for qid, answer in effective_answers.items():
        category = _infer_category(qid)
        answer_str = answer if isinstance(answer, str) else ", ".join(answer)

        if category == "quality_criteria":
            quality_criteria.append(answer_str)
        elif category == "failure_concerns":
            failure_concerns.append(answer_str)
        elif category == "domain_specifics":
            domain_context_parts.append(answer_str)
        elif category == "expected_behaviors":
            expected_behaviors.append({
                "question_id": qid,
                "behavior": answer_str,
            })

    # Ensure we have at least something in each category
    if not quality_criteria:
        quality_criteria.append("Output is accurate and relevant")
    if not failure_concerns:
        failure_concerns.append("Handle errors gracefully")

    # Merge custom Q&A into domain context (QUES-04)
    if custom_qa:
        custom_parts = [
            f"Q: {pair['question']} A: {pair['answer']}"
            for pair in custom_qa
            if pair.get("question", "").strip() and pair.get("answer", "").strip()
        ]
        if custom_parts:
            domain_context_parts.extend(custom_parts)

    domain_context = "; ".join(domain_context_parts) if domain_context_parts else "General purpose"

    # Build generation hints based on framework-specific patterns
    generation_hints: dict = {
        "frameworks": frameworks,
        "has_streaming": any(
            "stream" in cs.get("method", "").lower() for cs in call_sites
        ),
        "has_tool_use": any(
            "tool" in cs.get("method", "").lower()
            or "function" in cs.get("method", "").lower()
            for cs in call_sites
        ),
        "prompt_count": len(prompt_summary),
        "has_system_prompts": any(
            p.get("role") == "system" for p in prompt_summary
        ),
        "has_dynamic_prompts": any(
            p.get("is_dynamic", False) for p in prompt_summary
        ),
    }

    intent_model = {
        "app_type": app_type,
        "app_type_confidence": app_type_confidence,
        "frameworks": frameworks,
        "call_site_count": call_site_count,
        "prompt_summary": prompt_summary,
        "quality_criteria": quality_criteria,
        "failure_concerns": failure_concerns,
        "domain_context": domain_context,
        "expected_behaviors": expected_behaviors,
        "skipped_questions": skipped,
        "generation_hints": generation_hints,
    }

    # Validate through Pydantic
    from schemas import IntentModel
    validated = IntentModel(**intent_model)

    return validated.model_dump()
