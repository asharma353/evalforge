"""Failure mode extraction for eval generation.

Provides a static failure mode bank for common LLM app types, and an
LLM-powered extractor that augments static modes with intent-model-specific
ones. Follows the static fallback pattern -- never raises, always returns
modes even without an API key.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static failure mode bank
# ---------------------------------------------------------------------------

_AGENT_MODES: list[dict] = [
    {
        "id": "agent_tool_hallucination",
        "name": "Tool Hallucination",
        "description": "Agent calls a tool that doesn't exist or with incorrect / fabricated arguments",
        "evaluator_type": "assertion",
        "app_type": "agent",
        "severity": "high",
    },
    {
        "id": "agent_loop_detection",
        "name": "Infinite Tool-Call Loop",
        "description": "Agent enters an infinite tool-call loop (same tool called >3x without forward progress)",
        "evaluator_type": "assertion",
        "app_type": "agent",
        "severity": "high",
    },
    {
        "id": "agent_off_task",
        "name": "Off-Task Response",
        "description": "Agent response does not address the user's original request",
        "evaluator_type": "llm_judge",
        "app_type": "agent",
        "severity": "medium",
    },
    {
        "id": "agent_missing_tool_call",
        "name": "Missing Required Tool Call",
        "description": "Agent provides a final answer without using any tool when the task clearly requires tool use",
        "evaluator_type": "assertion",
        "app_type": "agent",
        "severity": "medium",
    },
    {
        "id": "agent_unsafe_action",
        "name": "Unsafe Action Without Confirmation",
        "description": "Agent takes an action that could be destructive or irreversible without requesting user confirmation",
        "evaluator_type": "llm_judge",
        "app_type": "agent",
        "severity": "high",
    },
]

_CHATBOT_MODES: list[dict] = [
    {
        "id": "chatbot_hallucination",
        "name": "Hallucination",
        "description": "Response contains factual claims not supported by the provided context",
        "evaluator_type": "llm_judge",
        "app_type": "chatbot",
        "severity": "high",
    },
    {
        "id": "chatbot_persona_break",
        "name": "Persona Break",
        "description": "Response violates the bot's defined persona, tone, or character guidelines",
        "evaluator_type": "llm_judge",
        "app_type": "chatbot",
        "severity": "medium",
    },
    {
        "id": "chatbot_off_topic",
        "name": "Off-Topic Response",
        "description": "Response drifts into topics outside the defined scope of the chatbot",
        "evaluator_type": "regex",
        "app_type": "chatbot",
        "severity": "medium",
    },
    {
        "id": "chatbot_repetition",
        "name": "Repetitive Response",
        "description": "Response repeats the same information already provided in a previous turn",
        "evaluator_type": "assertion",
        "app_type": "chatbot",
        "severity": "low",
    },
    {
        "id": "chatbot_incomplete_response",
        "name": "Incomplete Response",
        "description": "Response fails to address all parts of a multi-part question",
        "evaluator_type": "llm_judge",
        "app_type": "chatbot",
        "severity": "medium",
    },
]

_RAG_MODES: list[dict] = [
    {
        "id": "rag_hallucination",
        "name": "RAG Hallucination",
        "description": "Answer contains claims not grounded in the retrieved context",
        "evaluator_type": "llm_judge",
        "app_type": "rag",
        "severity": "high",
    },
    {
        "id": "rag_irrelevant_retrieval",
        "name": "Irrelevant Retrieval",
        "description": "Retrieved chunks have no semantic overlap with the query",
        "evaluator_type": "assertion",
        "app_type": "rag",
        "severity": "medium",
    },
]

_DOCUMENT_PROCESSING_MODES: list[dict] = [
    {
        "id": "doc_extraction_error",
        "name": "Extraction Error",
        "description": "Required fields are missing from the extraction output",
        "evaluator_type": "assertion",
        "app_type": "document_processing",
        "severity": "high",
    },
    {
        "id": "doc_format_violation",
        "name": "Format Violation",
        "description": "Output does not conform to the expected schema or format",
        "evaluator_type": "regex",
        "app_type": "document_processing",
        "severity": "medium",
    },
]

# General baseline modes always included regardless of app type
_GENERAL_MODES: list[dict] = [
    {
        "id": "general_empty_response",
        "name": "Empty Response",
        "description": "Model returns an empty or whitespace-only response",
        "evaluator_type": "assertion",
        "app_type": "general",
        "severity": "high",
    },
    {
        "id": "general_error_leak",
        "name": "Error Leak",
        "description": "Response contains Python tracebacks, error messages, or stack traces",
        "evaluator_type": "regex",
        "app_type": "general",
        "severity": "high",
    },
]

_APP_TYPE_MODES: dict[str, list[dict]] = {
    "agent": _AGENT_MODES,
    "chatbot": _CHATBOT_MODES,
    "rag": _RAG_MODES,
    "document_processing": _DOCUMENT_PROCESSING_MODES,
}


def _get_static_modes(app_type: str) -> list[dict]:
    """Return static failure modes for the given app type plus general baseline."""
    type_modes = _APP_TYPE_MODES.get(app_type, [])
    return list(type_modes) + list(_GENERAL_MODES)


def get_failure_modes(intent_model: dict) -> list[dict]:
    """Return failure modes for the given intent model.

    Always includes general baseline modes. Adds app-type-specific modes.
    Attempts LLM augmentation with failure_concerns from intent model;
    falls back silently to static-only list on any exception.

    Args:
        intent_model: Intent model dict with at minimum 'app_type' key.
            Optionally 'failure_concerns' and 'generation_hints' are used
            for LLM augmentation.

    Returns:
        List of FailureMode-compatible dicts (id, name, description,
        evaluator_type, app_type, severity).
    """
    app_type = intent_model.get("app_type", "general")
    static_modes = _get_static_modes(app_type)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("No ANTHROPIC_API_KEY configured, using static failure mode bank")
        return static_modes

    try:
        augmented = _augment_with_llm(intent_model, static_modes, api_key)
        return augmented
    except Exception as exc:
        logger.error("LLM failure mode augmentation failed, using static bank: %s", exc)
        return static_modes


def _augment_with_llm(
    intent_model: dict, static_modes: list[dict], api_key: str
) -> list[dict]:
    """Augment static failure modes with LLM-identified ones from the intent model.

    Args:
        intent_model: Full intent model dict.
        static_modes: Already-computed static modes to use as base.
        api_key: Anthropic API key.

    Returns:
        List of failure mode dicts, capped at 8 total.
    """
    import anthropic

    from services.llm import EFFORT, MAX_TOKENS, MODEL, response_text

    failure_concerns = intent_model.get("failure_concerns", [])
    generation_hints = intent_model.get("generation_hints", {})
    app_type = intent_model.get("app_type", "general")

    if not failure_concerns:
        return static_modes

    client = anthropic.Anthropic(api_key=api_key)

    existing_ids = {m["id"] for m in static_modes}

    system_prompt = """You are an expert in LLM evaluation and testing. Given an intent model
for an LLM application, identify 1-2 additional specific failure modes that are NOT already
covered by the provided static list.

Return ONLY a valid JSON array of failure mode objects with these exact fields:
- id: snake_case identifier, unique (avoid ids already in the static list)
- name: short human-readable name
- description: what this failure mode means and how it manifests
- evaluator_type: one of "assertion", "regex", or "llm_judge"
  (prefer assertion/regex for objective checks, llm_judge only for subjective qualities)
- app_type: the app type string
- severity: one of "high", "medium", "low"

Return an empty array [] if no additional modes are needed beyond the static list.
Return ONLY the JSON array, no markdown, no explanation."""

    user_prompt = f"""App type: {app_type}

Failure concerns from developer:
{json.dumps(failure_concerns, indent=2)}

Generation hints:
{json.dumps(generation_hints, indent=2)}

Existing static failure mode IDs (do NOT duplicate these):
{json.dumps(sorted(existing_ids), indent=2)}

Identify 1-2 additional failure modes specific to this application's concerns."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        output_config={"effort": EFFORT},
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    additional_modes = json.loads(response_text(message))

    if not isinstance(additional_modes, list):
        return static_modes

    valid_fields = {"id", "name", "description", "evaluator_type", "app_type", "severity"}
    valid_evaluator_types = {"assertion", "regex", "llm_judge"}
    valid_severities = {"high", "medium", "low"}

    combined = list(static_modes)
    for mode in additional_modes:
        if not isinstance(mode, dict):
            continue
        if not valid_fields.issubset(mode.keys()):
            continue
        if mode["evaluator_type"] not in valid_evaluator_types:
            continue
        if mode["severity"] not in valid_severities:
            continue
        if mode["id"] in existing_ids:
            continue
        combined.append(mode)
        existing_ids.add(mode["id"])
        if len(combined) >= 8:
            break

    return combined
