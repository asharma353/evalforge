"""Export package builder — assembles an in-memory zip of a runnable Python eval suite.

The generated zip has this structure::

    eval_suite/
        __init__.py
        conftest.py
        pyproject.toml
        README.md
        config.json
        evaluators/
            __init__.py
            test_<failure_mode_id>.py   (one per selected evaluator)
        test_data/
            test_cases.json
"""

from __future__ import annotations

import io
import json
import zipfile


def build_export_zip(
    failure_modes: list[dict],
    evaluators: list[dict],
    test_cases: list[dict],
    enabled_evaluator_ids: list[str],
    enabled_test_case_indices: list[int],
) -> io.BytesIO:
    """Build an in-memory zip file containing the full eval suite.

    Args:
        failure_modes: All failure modes from the generation result.
        evaluators: All evaluator dicts from the generation result.
        test_cases: All test case dicts from the generation result.
        enabled_evaluator_ids: Failure-mode IDs whose evaluators to include.
        enabled_test_case_indices: Zero-based indices into *test_cases* to include.

    Returns:
        A ``BytesIO`` buffer seeked to position 0 containing the ZIP_DEFLATED zip.
    """
    # --- Filter to selected items ------------------------------------------------
    selected_evaluators = [
        e for e in evaluators if e["failure_mode_id"] in enabled_evaluator_ids
    ]
    selected_test_cases = [
        tc for i, tc in enumerate(test_cases) if i in enabled_test_case_indices
    ]
    selected_failure_modes = [
        m for m in failure_modes if m["id"] in enabled_evaluator_ids
    ]

    # Detect whether any selected evaluator is an llm_judge (affects deps)
    has_llm_judge = any(
        e.get("evaluator_type") == "llm_judge" for e in selected_evaluators
    )

    # --- Build zip in memory -----------------------------------------------------
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. eval_suite/__init__.py
        zf.writestr("eval_suite/__init__.py", '"""Generated eval suite."""\n')

        # 2. eval_suite/evaluators/__init__.py
        zf.writestr("eval_suite/evaluators/__init__.py", '"""Evaluator modules."""\n')

        # 3. Evaluator files
        for evaluator in selected_evaluators:
            path = f"eval_suite/evaluators/{evaluator['filename']}"
            zf.writestr(path, evaluator["code"])

        # 4. test_data/test_cases.json
        zf.writestr(
            "eval_suite/test_data/test_cases.json",
            json.dumps(selected_test_cases, indent=2),
        )

        # 5. config.json
        config = {
            "failure_modes": [
                {
                    "id": m["id"],
                    "name": m["name"],
                    "description": m["description"],
                    "severity": m.get("severity", "medium"),
                    "evaluator_type": m.get("evaluator_type", "assertion"),
                }
                for m in selected_failure_modes
            ]
        }
        zf.writestr("eval_suite/config.json", json.dumps(config, indent=2))

        # 6. conftest.py
        zf.writestr("eval_suite/conftest.py", _build_conftest())

        # 7. pyproject.toml
        zf.writestr("eval_suite/pyproject.toml", _build_pyproject(has_llm_judge))

        # 8. README.md
        zf.writestr(
            "eval_suite/README.md",
            _build_readme(selected_failure_modes, has_llm_judge),
        )

    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_conftest() -> str:
    """Return the contents of conftest.py with standard pytest fixtures."""
    return '''\
"""Pytest configuration and fixtures for the generated eval suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_cases() -> list[dict]:
    """Load all test cases from test_data/test_cases.json."""
    data_path = Path(__file__).parent / "test_data" / "test_cases.json"
    with data_path.open() as fh:
        return json.load(fh)


@pytest.fixture
def test_cases_for(test_cases):
    """Return a factory that filters test cases by failure_mode_id.

    Usage::

        def test_something(test_cases_for):
            cases = test_cases_for("my_failure_mode_id")
    """
    def _filter(failure_mode_id: str) -> list[dict]:
        return [tc for tc in test_cases if tc.get("failure_mode_id") == failure_mode_id]

    return _filter
'''


def _build_pyproject(has_llm_judge: bool) -> str:
    """Return pyproject.toml content, conditionally including anthropic dependency."""
    anthropic_line = (
        '    "anthropic>=0.83.0",'
        if has_llm_judge
        else '    # "anthropic>=0.83.0",  # Uncomment if using LLM judge evaluators'
    )
    return f'''\
[project]
name = "eval-suite"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pytest>=8.0.0",
{anthropic_line}
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''


def _build_readme(failure_modes: list[dict], has_llm_judge: bool) -> str:
    """Return README.md content with setup instructions and failure modes table."""
    api_key_section = ""
    if has_llm_judge:
        api_key_section = """\

## API Key Setup

Some evaluators use Claude as an LLM judge. You must export your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

"""

    # Build failure modes table
    table_rows = "\n".join(
        f"| {m['name']} | {m.get('evaluator_type', 'assertion')} | {m.get('severity', 'medium')} | {m['description']} |"
        for m in failure_modes
    )
    failure_modes_table = f"""\
| Name | Type | Severity | Description |
|------|------|----------|-------------|
{table_rows}
"""

    return f"""\
# Eval Suite

A generated eval suite targeting the failure modes identified for your LLM application.

## Setup

```bash
pip install -e .
```
{api_key_section}
## Running Evaluations

Run all evaluators:

```bash
pytest eval_suite/evaluators/ -v
```

Run a specific evaluator:

```bash
pytest eval_suite/evaluators/test_<failure_mode>.py -v
```

## Project Structure

```
eval_suite/
    __init__.py          Package marker
    conftest.py          Pytest fixtures (test_cases, test_cases_for)
    pyproject.toml       Project metadata and dependencies
    config.json          Failure mode configuration
    evaluators/          One test file per failure mode
        __init__.py
        test_*.py
    test_data/
        test_cases.json  Generated test cases
```

## Failure Modes

{failure_modes_table}
"""
