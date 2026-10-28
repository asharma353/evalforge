"""Dimension extractor for test data generation.

Extracts variation dimensions from an intent model and failure mode, providing
axes along which test cases should vary. Uses static templates as baseline and
optionally augments with LLM-derived dimensions. Always falls back to static
on any exception or missing API key.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static dimension templates per evaluator type
# ---------------------------------------------------------------------------

_ASSERTION_DIMENSIONS: list[dict] = [
    {
        "name": "input_length",
        "values": ["short", "medium", "long"],
        "description": "Length of the input to the LLM application",
    },
    {
        "name": "edge_case_present",
        "values": ["yes", "no"],
        "description": "Whether the input contains an edge case or boundary condition",
    },
    {
        "name": "expected_format_violation",
        "values": ["yes", "no"],
        "description": "Whether the input is likely to trigger a format violation",
    },
]

_REGEX_DIMENSIONS: list[dict] = [
    {
        "name": "response_content",
        "values": ["in-scope", "borderline", "out-of-scope"],
        "description": "How the response content relates to the defined scope",
    },
    {
        "name": "formality",
        "values": ["formal", "casual", "technical"],
        "description": "The tone and formality level of the interaction",
    },
    {
        "name": "input_length",
        "values": ["short", "medium", "long"],
        "description": "Length of the input to the LLM application",
    },
]

_LLM_JUDGE_DIMENSIONS: list[dict] = [
    {
        "name": "context_quality",
        "values": ["grounded", "partially-grounded", "ungrounded"],
        "description": "How well the response is grounded in available context",
    },
    {
        "name": "user_intent",
        "values": ["clear", "ambiguous"],
        "description": "How clearly the user's intent is expressed in the input",
    },
    {
        "name": "response_style",
        "values": ["direct", "verbose", "evasive"],
        "description": "The stylistic approach of the model response",
    },
]

_EVALUATOR_TYPE_DIMENSIONS: dict[str, list[dict]] = {
    "assertion": _ASSERTION_DIMENSIONS,
    "regex": _REGEX_DIMENSIONS,
    "llm_judge": _LLM_JUDGE_DIMENSIONS,
}

# Default dimensions when evaluator type is unknown
_DEFAULT_DIMENSIONS: list[dict] = [
    {
        "name": "input_complexity",
        "values": ["simple", "moderate", "complex"],
        "description": "Complexity level of the input query",
    },
    {
        "name": "expected_output_quality",
        "values": ["high", "medium", "low"],
        "description": "Expected quality level of the model output",
    },
]


def extract_dimensions(intent_model: dict, failure_mode: dict) -> list[dict]:
    """Extract variation dimensions for test case generation.

    Returns list of dicts: {name: str, values: list[str], description: str}
    Uses static templates as baseline; attempts LLM augmentation (silently falls back).

    Args:
        intent_model: Intent model dict with app_type, domain_context, etc.
        failure_mode: Failure mode dict with id, name, description, evaluator_type, etc.

    Returns:
        List of dimension dicts, each with name, values, and description.
        Capped at 5 dimensions total.
    """
    evaluator_type = failure_mode.get("evaluator_type", "")
    base_dims = list(
        _EVALUATOR_TYPE_DIMENSIONS.get(evaluator_type, _DEFAULT_DIMENSIONS)
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info(
            "No ANTHROPIC_API_KEY configured, using static dimensions for %s",
            failure_mode.get("id", "unknown"),
        )
        return base_dims[:5]

    try:
        augmented = _augment_with_llm(intent_model, failure_mode, base_dims, api_key)
        return augmented[:5]
    except Exception as exc:
        logger.error(
            "LLM dimension augmentation failed for %s, using static: %s",
            failure_mode.get("id", "unknown"),
            exc,
        )
        return base_dims[:5]


def _augment_with_llm(
    intent_model: dict,
    failure_mode: dict,
    base_dims: list[dict],
    api_key: str,
) -> list[dict]:
    """Augment static dimensions with LLM-derived ones specific to the failure mode.

    Args:
        intent_model: Full intent model dict.
        failure_mode: Failure mode dict being targeted.
        base_dims: Already-computed static dimensions to use as base.
        api_key: Anthropic API key.

    Returns:
        Combined list of dimensions, capped at 5 total.
    """
    import anthropic

    from services.llm import EFFORT, MAX_TOKENS, MODEL, response_text

    domain_context = intent_model.get("domain_context", "")
    failure_description = failure_mode.get("description", "")
    failure_name = failure_mode.get("name", "")
    existing_names = {d["name"] for d in base_dims}

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """You are an expert in LLM evaluation and test case design.
Given a failure mode and application domain context, identify 2-3 additional variation
dimensions that would produce diverse and meaningful test cases for this specific failure.

Return ONLY a valid JSON array of dimension objects with these exact fields:
- name: snake_case dimension name (unique, not in the existing list)
- values: list of 3-4 distinct string values for this dimension
- description: what this dimension varies

Return an empty array [] if no additional dimensions are needed.
Return ONLY the JSON array, no markdown, no explanation."""

    user_prompt = f"""Failure mode: {failure_name}
Description: {failure_description}
Domain context: {domain_context}

Existing dimension names (do NOT duplicate):
{json.dumps(sorted(existing_names), indent=2)}

Identify 2-3 additional variation dimensions specific to this failure mode and domain."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        output_config={"effort": EFFORT},
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    additional_dims = json.loads(response_text(message))

    if not isinstance(additional_dims, list):
        return base_dims

    combined = list(base_dims)
    for dim in additional_dims:
        if not isinstance(dim, dict):
            continue
        if "name" not in dim or "values" not in dim:
            continue
        if not isinstance(dim.get("values"), list) or len(dim["values"]) < 2:
            continue
        if dim["name"] in existing_names:
            continue
        if not dim.get("description"):
            dim["description"] = f"Variation in {dim['name'].replace('_', ' ')}"
        combined.append(dim)
        existing_names.add(dim["name"])
        if len(combined) >= 5:
            break

    return combined
