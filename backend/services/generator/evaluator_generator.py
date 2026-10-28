"""Evaluator code generator producing one check module per failure mode.

Each generated module defines a plain function::

    def check_<failure_mode_id>(response: str, context: dict | None = None) -> bool

returning True when the response passes (does NOT exhibit the failure mode).
The checks are not pytest tests themselves: the exported package's runner test
calls the user's app for each test case and feeds the response to the check.

Each generated file follows the cost hierarchy:
  1. Assertions (no external deps) -- preferred for objective checks
  2. Regex matching -- for pattern-based checks
  3. LLM-as-Judge -- only for subjective qualities that can't be checked otherwise
"""

from __future__ import annotations

import json
import logging
import os
import textwrap

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static stub templates (used when LLM is unavailable or fails)
# ---------------------------------------------------------------------------

_ASSERTION_STUB = '''\
# evaluator_type: assertion
"""
{description}

Pass example: {pass_example}
Fail example: {fail_example}
"""

METADATA = {{
    "failure_mode_id": "{id}",
    "name": "{name}",
    "description": "{description}",
    "evaluator_type": "assertion",
    "severity": "{severity}",
}}


def check_{id}(response: str, context: dict | None = None) -> bool:
    """
    Checks: {description}

    Returns True if the response passes, False if it exhibits the failure mode.

    Pass example: {pass_example}
    Fail example: {fail_example}
    """
    # TODO: Replace with specific logic for this failure mode
    return bool(response and response.strip())
'''

_REGEX_STUB = '''\
# evaluator_type: regex
"""
{description}

Pass example: {pass_example}
Fail example: {fail_example}
"""
import re

METADATA = {{
    "failure_mode_id": "{id}",
    "name": "{name}",
    "description": "{description}",
    "evaluator_type": "regex",
    "severity": "{severity}",
}}


def check_{id}(response: str, context: dict | None = None) -> bool:
    """
    Checks: {description}

    Returns True if the response passes, False if it exhibits the failure mode.

    Pass example: {pass_example}
    Fail example: {fail_example}
    """
    # TODO: Replace with the specific pattern for this failure mode
    pattern = r"(?i)(error|traceback|exception)"
    return re.search(pattern, response) is None
'''

_LLM_JUDGE_STUB = '''\
# evaluator_type: llm_judge
"""
{description}

Pass example: {pass_example}
Fail example: {fail_example}
"""
import anthropic
import json

METADATA = {{
    "failure_mode_id": "{id}",
    "name": "{name}",
    "description": "{description}",
    "evaluator_type": "llm_judge",
    "severity": "{severity}",
}}

JUDGE_PROMPT = """You are evaluating an LLM response for a specific failure mode.

Failure mode: {name}
Description: {description}

Response to evaluate:
{{response}}

Context (if available):
{{context}}

Evaluate whether the response exhibits this failure mode.
Return a JSON object with:
- "pass": true if the response does NOT exhibit the failure mode, false if it does
- "reason": brief explanation of your judgment

Return ONLY the JSON object, no other text."""


def check_{id}(response: str, context: dict | None = None) -> bool:
    """
    Checks: {description}

    Returns True if the response passes, False if it exhibits the failure mode.

    Pass example: {pass_example}
    Fail example: {fail_example}
    """
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=256,
        messages=[
            {{
                "role": "user",
                "content": JUDGE_PROMPT.format(
                    response=response,
                    context=json.dumps(context or {{}}),
                ),
            }}
        ],
    )
    result = json.loads(message.content[0].text)
    return bool(result.get("pass"))
'''

# Map from evaluator_type to stub template
_STUBS: dict[str, str] = {
    "assertion": _ASSERTION_STUB,
    "regex": _REGEX_STUB,
    "llm_judge": _LLM_JUDGE_STUB,
}

# ---------------------------------------------------------------------------
# Default pass/fail examples per known failure mode id
# ---------------------------------------------------------------------------

_DEFAULT_EXAMPLES: dict[str, tuple[str, str]] = {
    # (pass_example, fail_example)
    "agent_tool_hallucination": (
        "Agent calls search_web(query='latest news') with valid arguments",
        "Agent calls nonexistent_tool(data='foo') which is not in the tool list",
    ),
    "agent_loop_detection": (
        "Agent calls get_weather once, gets result, proceeds to final answer",
        "Agent calls get_weather 5 times in a row with identical arguments",
    ),
    "agent_off_task": (
        "User asks to book a flight; agent retrieves flight options",
        "User asks to book a flight; agent discusses the history of aviation",
    ),
    "agent_missing_tool_call": (
        "Agent calls calculate_total() and returns the computed result",
        "Agent says 'The total is 42' without ever calling calculate_total()",
    ),
    "agent_unsafe_action": (
        "Agent asks 'Are you sure you want to delete all records?' before deleting",
        "Agent immediately executes delete_all_records() without confirmation",
    ),
    "chatbot_hallucination": (
        "Response cites only information present in the provided context",
        "Response invents statistics not found anywhere in the context",
    ),
    "chatbot_persona_break": (
        "Customer service bot maintains a polite, professional tone throughout",
        "Pirate-themed bot responds 'Certainly! I'll help you.' instead of 'Arr, I'll help ye!'",
    ),
    "chatbot_off_topic": (
        "Cooking assistant responds with a pasta recipe when asked about pasta",
        "Cooking assistant discusses cryptocurrency trends when asked about pasta",
    ),
    "chatbot_repetition": (
        "Bot introduces new information in each turn of the conversation",
        "Bot repeats the same greeting and disclaimer in every single response",
    ),
    "chatbot_incomplete_response": (
        "Response addresses both parts: pricing AND delivery timeline",
        "Response only addresses pricing, ignoring the question about delivery",
    ),
    "rag_hallucination": (
        "Answer directly quotes or paraphrases the retrieved document chunks",
        "Answer states facts not found in any of the retrieved chunks",
    ),
    "rag_irrelevant_retrieval": (
        "Retrieved chunks contain the keyword 'quantum computing' matching the query",
        "Retrieved chunks are about cooking recipes when query is about quantum computing",
    ),
    "doc_extraction_error": (
        "Output JSON contains all required fields: name, date, amount",
        "Output JSON is missing the 'amount' field entirely",
    ),
    "doc_format_violation": (
        "Output matches expected JSON schema with all fields properly typed",
        "Output is a plain English sentence instead of the required JSON object",
    ),
    "general_empty_response": (
        "Response is 'The answer is 42.'",
        "Response is '' (empty string) or '   ' (only whitespace)",
    ),
    "general_error_leak": (
        "Response is 'I encountered an issue and cannot answer that right now.'",
        "Response contains 'Traceback (most recent call last): File app.py...'",
    ),
}

_GENERIC_PASS_EXAMPLE = "Response correctly handles the scenario without exhibiting this failure mode"
_GENERIC_FAIL_EXAMPLE = "Response exhibits this failure mode as described"


def get_evaluator_filename(failure_mode_id: str) -> str:
    """Return the check module filename: check_{failure_mode_id}.py"""
    return f"check_{failure_mode_id}.py"


def generate_evaluator(failure_mode: dict) -> str:
    """Generate check-function evaluator code for the given failure mode.

    Returns the full Python source code as a string.
    Chooses template based on failure_mode['evaluator_type'].

    Uses LLM to fill in specific logic when available; falls back to a
    well-commented stub with TODO markers on any failure.

    Args:
        failure_mode: Dict with at minimum: id, name, description,
            evaluator_type, app_type, severity.

    Returns:
        Python source code as a string, ready to save as a .py file.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _generate_with_llm(failure_mode, api_key)
        except Exception as exc:
            logger.error(
                "LLM evaluator generation failed for %s, using stub: %s",
                failure_mode.get("id"),
                exc,
            )

    return _generate_stub(failure_mode)


def _get_examples(failure_mode_id: str) -> tuple[str, str]:
    """Return (pass_example, fail_example) for the given failure mode id."""
    return _DEFAULT_EXAMPLES.get(failure_mode_id, (_GENERIC_PASS_EXAMPLE, _GENERIC_FAIL_EXAMPLE))


def _generate_stub(failure_mode: dict) -> str:
    """Generate a minimal stub evaluator with TODO placeholders."""
    fm_id = failure_mode.get("id", "unknown")
    evaluator_type = failure_mode.get("evaluator_type", "assertion")
    template = _STUBS.get(evaluator_type, _STUBS["assertion"])

    pass_example, fail_example = _get_examples(fm_id)

    return template.format(
        id=fm_id,
        name=failure_mode.get("name", fm_id.replace("_", " ").title()),
        description=failure_mode.get("description", "No description provided"),
        evaluator_type=evaluator_type,
        severity=failure_mode.get("severity", "medium"),
        pass_example=pass_example,
        fail_example=fail_example,
    )


def _generate_with_llm(failure_mode: dict, api_key: str) -> str:
    """Generate specific evaluator code using the Anthropic API.

    Args:
        failure_mode: Full failure mode dict.
        api_key: Anthropic API key.

    Returns:
        Complete Python source code as a string.
    """
    import anthropic

    fm_id = failure_mode.get("id", "unknown")
    evaluator_type = failure_mode.get("evaluator_type", "assertion")
    pass_example, fail_example = _get_examples(fm_id)

    # Build the stub as a starting reference so LLM knows the exact structure
    stub = _generate_stub(failure_mode)

    system_prompt = """You are an expert Python test engineer specializing in LLM evaluation.
Generate a complete, runnable Python check function for an LLM failure mode.

Requirements:
1. Start with `# evaluator_type: {type}` as the FIRST line
2. Include a module docstring with description + pass/fail examples
3. Include a METADATA dict with: failure_mode_id, name, description, evaluator_type, severity
4. Implement `def check_{id}(response: str, context: dict | None = None) -> bool:`
   - Return True if the response passes (does NOT exhibit the failure mode), False otherwise
   - Do not use assert statements and do not define any pytest tests or fixtures
   - `context` is the test case dict (keys: input, expected_behavior, failure_mode_id); it may be None
   - Docstring with pass/fail examples
   - For assertion type: plain Python comparisons, no external deps
   - For regex type: import re at top, use re.search/re.match
   - For llm_judge type: use anthropic SDK (claude-3-5-haiku-20241022, max_tokens=256)
     Return JSON with {"pass": bool, "reason": str}
5. The logic must be SPECIFIC to the failure mode described -- not generic
6. Return ONLY the Python source code, no markdown fences, no explanation"""

    user_prompt = f"""Generate a specific evaluator for this failure mode:

ID: {fm_id}
Name: {failure_mode.get('name', '')}
Description: {failure_mode.get('description', '')}
Evaluator type: {evaluator_type}
Severity: {failure_mode.get('severity', 'medium')}
App type: {failure_mode.get('app_type', 'general')}

Pass example: {pass_example}
Fail example: {fail_example}

Reference stub (replace TODO with real logic):
{stub}

Generate the complete, specific evaluator code."""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    code = message.content[0].text.strip()

    # Strip markdown code fences if present
    if code.startswith("```"):
        lines = code.split("\n")
        # Remove first line (```python or ```) and last line (```)
        code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # Validate required elements are present
    required_checks = [
        f"# evaluator_type: {evaluator_type}",
        "METADATA",
        f"def check_{fm_id}(",
    ]
    for check in required_checks:
        if check not in code:
            raise ValueError(f"LLM output missing required element: {check!r}")

    return code
