"""LLM-powered question tailoring with static fallback.

Generates tailored questions from analysis results by asking an LLM to
customize questions from the static bank. Falls back to static questions
on any failure -- never blocks the user.
"""

from __future__ import annotations

import json
import logging
import os

from .question_bank import get_static_questions

logger = logging.getLogger(__name__)


async def generate_questions(analysis_result: dict) -> tuple[list[dict], str]:
    """Generate tailored questions based on analysis results.

    Uses LLM to customize questions from the static bank based on the
    specific code patterns found during analysis. Falls back to static
    questions on any failure.

    Args:
        analysis_result: The analysis result dict containing app_type,
            call_sites, and summary.

    Returns:
        Tuple of (questions list, generation_source string).
        generation_source is "llm" or "static_fallback".
    """
    app_type_info = analysis_result.get("app_type", {})
    app_type = app_type_info.get("type", "general")

    # Check for API key -- if missing, fall back immediately (never block user)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("No ANTHROPIC_API_KEY configured, using static question bank")
        return get_static_questions(app_type), "static_fallback"

    try:
        return await _generate_with_llm(analysis_result, app_type, api_key)
    except Exception as exc:
        logger.error("LLM question generation failed, falling back to static: %s", exc)
        return get_static_questions(app_type), "static_fallback"


async def _generate_with_llm(
    analysis_result: dict, app_type: str, api_key: str
) -> tuple[list[dict], str]:
    """Generate questions using the Anthropic API.

    Args:
        analysis_result: Full analysis result.
        app_type: Classified app type string.
        api_key: Anthropic API key.

    Returns:
        Tuple of (tailored questions, "llm").
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    # Build context from analysis
    call_sites = analysis_result.get("call_sites", [])
    frameworks = list({cs.get("framework", "unknown") for cs in call_sites})
    call_site_count = len(call_sites)

    # Extract prompt snippets (truncate to 500 chars each)
    prompt_snippets = []
    for cs in call_sites[:5]:  # Limit to first 5 call sites
        for prompt in cs.get("prompts", []):
            content = prompt.get("content", "")
            if content:
                prompt_snippets.append(content[:500])

    # Get static bank for this app type as reference
    static_questions = get_static_questions(app_type)

    system_prompt = """You are a question generation assistant for an LLM eval builder tool.
Given analysis results from scanning a developer's codebase, select and customize questions
from the provided question bank. Return a JSON array of question objects.

Rules:
1. Select 5-8 questions from the bank that are most relevant to the detected patterns.
2. Customize the question text to reference the developer's specific code patterns (frameworks, prompt patterns).
3. You may add 1-2 NEW questions if the analysis reveals gaps not covered by the bank.
4. Keep the same object structure: id, text, category, type, options, default, placeholder, context_hint.
5. Ensure all four categories are represented: quality_criteria, failure_concerns, domain_specifics, expected_behaviors.
6. Return ONLY a valid JSON array -- no markdown, no explanation."""

    user_prompt = f"""Analysis Results:
- App Type: {app_type} (confidence: {analysis_result.get('app_type', {}).get('confidence', 0)})
- Frameworks detected: {', '.join(frameworks) if frameworks else 'none detected'}
- Number of LLM call sites: {call_site_count}
- Prompt snippets (first 500 chars each):
{chr(10).join(f'  - {s}' for s in prompt_snippets[:3]) if prompt_snippets else '  (no prompts extracted)'}

Question Bank for {app_type}:
{json.dumps(static_questions, indent=2)}

Generate 5-8 tailored questions as a JSON array."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Parse response
    response_text = message.content[0].text
    questions = json.loads(response_text)

    if not isinstance(questions, list):
        raise ValueError("LLM response is not a JSON array")

    # Validate each question has required fields
    required_fields = {"id", "text", "category", "type"}
    validated = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        if not required_fields.issubset(q.keys()):
            continue
        # Ensure defaults exist
        q.setdefault("options", None)
        q.setdefault("default", "")
        q.setdefault("placeholder", None)
        q.setdefault("context_hint", None)
        validated.append(q)

    # Clamp to 5-8 questions
    if len(validated) < 5:
        # Supplement with static questions not already included
        existing_ids = {q["id"] for q in validated}
        for sq in static_questions:
            if sq["id"] not in existing_ids:
                validated.append(sq)
                if len(validated) >= 6:
                    break
    elif len(validated) > 8:
        validated = validated[:8]

    if len(validated) < 5:
        # Still not enough -- fall back entirely
        raise ValueError(f"Only {len(validated)} valid questions after supplementing")

    return validated, "llm"
