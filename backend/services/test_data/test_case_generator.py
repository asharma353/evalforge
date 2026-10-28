"""Test case generator from dimensional analysis.

Converts variation dimensions into structured tuples (combinations of dimension values)
and naturalizes them into test cases with input, expected_behavior, and failure_mode_id.

Two-step process:
1. Tuple generation: sample varied combinations ensuring coverage of all dimension values
2. Naturalization: convert tuples to natural language test cases via LLM or static fallback
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import random

logger = logging.getLogger(__name__)


def _sample_tuples(dimensions: list[dict], count: int) -> list[dict]:
    """Sample varied tuples from dimension values.

    Avoids exponential enumeration. Ensures each dimension value appears
    at least once across the sampled tuples.

    Args:
        dimensions: List of dimension dicts with name and values.
        count: Target number of tuples to generate.

    Returns:
        List of dicts mapping dimension name -> selected value.
    """
    if not dimensions:
        return [{}] * max(count, 1)

    # Ensure each value in each dimension appears at least once
    # by creating "coverage tuples" first, then filling with random sampling
    tuples: list[dict] = []

    # Step 1: Create coverage tuples by cycling through values per dimension
    max_values = max(len(d["values"]) for d in dimensions)
    for i in range(max_values):
        t = {}
        for dim in dimensions:
            values = dim["values"]
            t[dim["name"]] = values[i % len(values)]
        tuples.append(t)

    # Step 2: Fill remaining slots with random combinations
    rng = random.Random(42)  # Deterministic for reproducibility
    while len(tuples) < count:
        t = {}
        for dim in dimensions:
            t[dim["name"]] = rng.choice(dim["values"])
        # Avoid exact duplicates
        if t not in tuples:
            tuples.append(t)
        elif len(tuples) >= count:
            # Fallback: allow duplicates if we can't fill without them
            tuples.append(t)

    return tuples[:count]


def _static_naturalize(
    tuple_combo: dict, failure_mode: dict, intent_model: dict
) -> dict:
    """Produce a static (non-LLM) test case from a dimension tuple.

    Args:
        tuple_combo: Dict mapping dimension name -> value.
        failure_mode: Failure mode dict.
        intent_model: Intent model dict.

    Returns:
        Test case dict with input, expected_behavior, failure_mode_id.
    """
    failure_mode_id = failure_mode.get("id", "unknown")
    failure_name = failure_mode.get("name", "Failure")
    domain = intent_model.get("domain_context", "general")

    # Build input as a readable description of the dimension values
    dim_parts = [f"{k.replace('_', ' ')}: {v}" for k, v in tuple_combo.items()]
    input_text = f"[{failure_name}] {domain} scenario with {', '.join(dim_parts)}"

    # Generic expected behavior
    expected = (
        f"The response should not trigger the '{failure_name}' failure mode. "
        "It should be complete, accurate, and appropriate for the context."
    )

    return {
        "input": input_text,
        "expected_behavior": expected,
        "failure_mode_id": failure_mode_id,
    }


def _llm_naturalize_batch(
    tuples: list[dict],
    failure_mode: dict,
    intent_model: dict,
    api_key: str,
) -> list[dict]:
    """Naturalize a batch of tuples into test cases via LLM.

    Args:
        tuples: List of dimension tuple dicts.
        failure_mode: Failure mode being targeted.
        intent_model: Full intent model dict.
        api_key: Anthropic API key.

    Returns:
        List of test case dicts with input, expected_behavior, failure_mode_id.
        Falls back to static naturalization for any tuple that fails.
    """
    import anthropic

    from services.llm import EFFORT, MAX_TOKENS, MODEL, response_text

    failure_mode_id = failure_mode.get("id", "unknown")
    failure_name = failure_mode.get("name", "")
    failure_description = failure_mode.get("description", "")
    domain = intent_model.get("domain_context", "general")
    app_type = intent_model.get("app_type", "general")

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """You are an expert at creating test cases for LLM application evaluation.
Given a failure mode and dimension tuples, create realistic test cases.

For each tuple, return a JSON object with:
- input: a realistic LLM app input matching the dimension combination (1-2 sentences)
- expected_behavior: what a passing evaluation looks like (1-2 sentences)

Return ONLY a valid JSON array of objects, one per tuple, in the same order.
No markdown, no explanation, just the JSON array."""

    tuples_text = json.dumps(tuples, indent=2)

    user_prompt = f"""Failure mode: {failure_name}
Description: {failure_description}
App type: {app_type}
Domain context: {domain}

Create a realistic test case for each of these dimension tuples:
{tuples_text}

Each test case's input should be a realistic user query or scenario that exercises
the dimension values. The expected_behavior should describe what a correct (non-failing)
response looks like for this failure mode."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        output_config={"effort": EFFORT},
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    llm_cases = json.loads(response_text(message))

    if not isinstance(llm_cases, list):
        raise ValueError("LLM returned non-list response")

    results = []
    for i, case in enumerate(llm_cases):
        if not isinstance(case, dict):
            results.append(_static_naturalize(tuples[i], failure_mode, intent_model))
            continue
        if "input" not in case or "expected_behavior" not in case:
            results.append(_static_naturalize(tuples[i], failure_mode, intent_model))
            continue
        results.append(
            {
                "input": case["input"],
                "expected_behavior": case["expected_behavior"],
                "failure_mode_id": failure_mode_id,
            }
        )

    # If LLM returned fewer cases than expected, pad with static fallback
    while len(results) < len(tuples):
        idx = len(results)
        results.append(_static_naturalize(tuples[idx], failure_mode, intent_model))

    return results


def generate_test_cases(
    intent_model: dict,
    failure_mode: dict,
    dimensions: list[dict],
    count: int = 12,
) -> list[dict]:
    """Generate test cases from dimensions for a specific failure mode.

    Returns list of dicts: {input: str, expected_behavior: str, failure_mode_id: str}
    count: target number of test cases (actual may vary slightly, target 10-15 range).

    Args:
        intent_model: Intent model dict with app_type, domain_context, etc.
        failure_mode: Failure mode dict with id, name, description, evaluator_type, etc.
        dimensions: List of dimension dicts with name, values, description.
        count: Target number of test cases to generate (10-15 recommended).

    Returns:
        List of test case dicts with input, expected_behavior, failure_mode_id.
    """
    # Clamp count to sensible range
    count = max(3, min(count, 15))

    # Step 1: Generate dimension tuples
    tuples = _sample_tuples(dimensions, count)

    # Step 2: Naturalize tuples into test cases
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info(
            "No ANTHROPIC_API_KEY configured, using static naturalization for %s",
            failure_mode.get("id", "unknown"),
        )
        return [
            _static_naturalize(t, failure_mode, intent_model) for t in tuples
        ]

    try:
        return _llm_naturalize_batch(tuples, failure_mode, intent_model, api_key)
    except Exception as exc:
        logger.error(
            "LLM naturalization failed for %s, using static fallback: %s",
            failure_mode.get("id", "unknown"),
            exc,
        )
        return [
            _static_naturalize(t, failure_mode, intent_model) for t in tuples
        ]
