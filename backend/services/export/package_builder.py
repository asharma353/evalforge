"""Export package builder — assembles an in-memory zip of a runnable Python eval suite.

The generated zip has this structure::

    eval_suite/
        __init__.py
        app_adapter.py                  (run_app stub the user fills in)
        conftest.py
        test_evals.py                   (runner: run_app -> check per test case)
        pyproject.toml
        README.md
        config.json
        evaluators/
            __init__.py
            check_<failure_mode_id>.py  (one per selected evaluator)
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

        # 7. app_adapter.py and the runner test that uses it
        zf.writestr("eval_suite/app_adapter.py", _build_app_adapter())
        zf.writestr("eval_suite/test_evals.py", _build_runner())

        # 8. pyproject.toml
        zf.writestr("eval_suite/pyproject.toml", _build_pyproject(has_llm_judge))

        # 9. README.md
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


def _build_app_adapter() -> str:
    """Return the contents of app_adapter.py: a run_app stub the user implements."""
    return '''\
"""Connect the eval suite to your LLM application.

Implement ``run_app`` so it sends one test-case input to your app and returns
the app's final text response. The runner in test_evals.py calls it once per
test case and passes the response to the matching evaluator.

Example::

    from my_app import answer_question

    def run_app(user_input: str) -> str:
        return answer_question(user_input)
"""

from __future__ import annotations


def run_app(user_input: str) -> str:
    """Send *user_input* to your LLM app and return its response text."""
    raise NotImplementedError(
        "run_app() in eval_suite/app_adapter.py is not implemented yet. "
        "Edit it to call your LLM app with the test case input and return "
        "the response text, then re-run pytest."
    )
'''


def _build_runner() -> str:
    """Return the contents of test_evals.py: one pytest case per test case."""
    return '''\
"""Run every test case through your app and check the response.

For each case in test_data/test_cases.json, ``run_app`` from app_adapter.py
turns the case's input into a response, and the matching
``check_<failure_mode_id>`` function in evaluators/ decides pass or fail.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from . import app_adapter

HERE = Path(__file__).parent


def _load_checks() -> dict[str, Callable[..., bool]]:
    """Map failure_mode_id to its check function, one per evaluators/check_*.py."""
    checks = {}
    for path in sorted((HERE / "evaluators").glob("check_*.py")):
        module = importlib.import_module(f".evaluators.{path.stem}", __package__)
        checks[path.stem.removeprefix("check_")] = getattr(module, path.stem)
    return checks


def _load_cases(checks: dict[str, Callable[..., bool]]) -> list[dict]:
    """Return the test cases whose failure mode has an evaluator."""
    with (HERE / "test_data" / "test_cases.json").open() as fh:
        cases = json.load(fh)
    return [case for case in cases if case.get("failure_mode_id") in checks]


def _case_ids(cases: list[dict]) -> list[str]:
    """Readable test ids like ``general_error_leak-3``."""
    seen: dict[str, int] = {}
    ids = []
    for case in cases:
        fm_id = case["failure_mode_id"]
        seen[fm_id] = seen.get(fm_id, 0) + 1
        ids.append(f"{fm_id}-{seen[fm_id]}")
    return ids


CHECKS = _load_checks()
CASES = _load_cases(CHECKS)


@pytest.mark.parametrize("case", CASES, ids=_case_ids(CASES))
def test_failure_mode(case: dict) -> None:
    try:
        response = app_adapter.run_app(case["input"])
    except NotImplementedError as exc:
        pytest.exit(str(exc), returncode=pytest.ExitCode.USAGE_ERROR)

    assert isinstance(response, str), (
        f"run_app() must return a str, got {type(response).__name__}"
    )

    check = CHECKS[case["failure_mode_id"]]
    assert check(response, case), (
        f"{case[\'failure_mode_id\']} failed\\n"
        f"  input:    {case[\'input\']!r}\\n"
        f"  expected: {case.get(\'expected_behavior\', \'\')}\\n"
        f"  response: {response!r}"
    )
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

# The suite is run in place, not imported as an installed package, so
# `pip install -e .` only needs to install the dependencies above.
[tool.hatch.build.targets.wheel]
bypass-selection = true
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

From the folder that contains `eval_suite/`, install the dependencies:

```bash
pip install -e eval_suite
```
{api_key_section}
## Connect Your App

Open `app_adapter.py` and implement `run_app(user_input) -> str` so it sends one
test case input to your LLM app and returns the response text. Until you do,
the suite stops with a message pointing you there.

## Running Evaluations

From the folder that contains `eval_suite/`, run every test case:

```bash
pytest eval_suite -v
```

Run the cases for a single failure mode:

```bash
pytest eval_suite -v -k <failure_mode_id>
```

Each test case's `input` is sent through `run_app`, and the response is passed to
`check_<failure_mode_id>(response, context)` in `evaluators/`, where `context` is
the test case dict. A check returns `True` when the response passes.

## Project Structure

```
eval_suite/
    __init__.py          Package marker
    app_adapter.py       run_app() hook: connect your LLM app here
    test_evals.py        Runner: run_app -> check for every test case
    conftest.py          Pytest fixtures (test_cases, test_cases_for)
    pyproject.toml       Project metadata and dependencies
    config.json          Failure mode configuration
    evaluators/          One check function per failure mode
        __init__.py
        check_*.py
    test_data/
        test_cases.json  Generated test cases
```

## Failure Modes

{failure_modes_table}
"""
