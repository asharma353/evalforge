"""End-to-end tests for the exported eval suite.

Each test builds the zip exactly as the export endpoint does, extracts it to a
temp dir, and runs pytest on it in a subprocess, the way a user would.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from services.export.package_builder import build_export_zip
from services.generator.evaluator_generator import (
    generate_evaluator,
    get_evaluator_filename,
)

# One assertion and one regex evaluator; both stubs run without an API key.
FAILURE_MODES = [
    {
        "id": "general_empty_response",
        "name": "Empty Response",
        "description": "Response is empty or whitespace only",
        "evaluator_type": "assertion",
        "app_type": "general",
        "severity": "high",
    },
    {
        "id": "general_error_leak",
        "name": "Error Leak",
        "description": "Response contains Python tracebacks or error messages",
        "evaluator_type": "regex",
        "app_type": "general",
        "severity": "high",
    },
]

TEST_CASES = [
    {"input": f"question {i}", "expected_behavior": "A helpful answer", "failure_mode_id": mode["id"]}
    for mode in FAILURE_MODES
    for i in range(2)
]


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    """Force the static stub evaluators so tests are offline and deterministic."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture
def suite_dir(tmp_path: Path) -> Path:
    """Build the export zip, extract it into tmp_path, and return tmp_path."""
    evaluators = [
        {
            "failure_mode_id": mode["id"],
            "filename": get_evaluator_filename(mode["id"]),
            "evaluator_type": mode["evaluator_type"],
            "code": generate_evaluator(mode),
            "description": mode["description"],
        }
        for mode in FAILURE_MODES
    ]
    buffer = build_export_zip(
        failure_modes=FAILURE_MODES,
        evaluators=evaluators,
        test_cases=TEST_CASES,
        enabled_evaluator_ids=[mode["id"] for mode in FAILURE_MODES],
        enabled_test_case_indices=list(range(len(TEST_CASES))),
    )
    with zipfile.ZipFile(buffer) as zf:
        zf.extractall(tmp_path)
    return tmp_path


def write_adapter(suite_dir: Path, response: str) -> None:
    """Replace the run_app stub with one that always returns *response*."""
    (suite_dir / "eval_suite" / "app_adapter.py").write_text(
        f"def run_app(user_input: str) -> str:\n    return {response!r}\n"
    )


def run_pytest(suite_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run the README command against the extracted suite."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", "eval_suite", "-v", "-p", "no:cacheprovider"],
        cwd=suite_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_suite_passes_with_filled_in_adapter(suite_dir: Path):
    write_adapter(suite_dir, "Here is a helpful answer.")

    result = run_pytest(suite_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "4 passed" in result.stdout


def test_suite_fails_when_response_exhibits_failure_mode(suite_dir: Path):
    write_adapter(suite_dir, "Traceback (most recent call last): boom")

    result = run_pytest(suite_dir)

    assert result.returncode == pytest.ExitCode.TESTS_FAILED, result.stdout + result.stderr
    assert "general_error_leak failed" in result.stdout
    assert "2 failed, 2 passed" in result.stdout


def test_suite_stops_with_message_when_adapter_not_filled_in(suite_dir: Path):
    result = run_pytest(suite_dir)

    assert result.returncode == pytest.ExitCode.USAGE_ERROR, result.stdout + result.stderr
    assert "run_app() in eval_suite/app_adapter.py is not implemented yet" in result.stdout


@pytest.mark.parametrize("evaluator_type", ["assertion", "regex", "llm_judge"])
def test_stub_defines_check_function_not_pytest_test(evaluator_type: str):
    code = generate_evaluator({"id": "sample_mode", "evaluator_type": evaluator_type})

    functions = {
        node.name for node in ast.walk(ast.parse(code)) if isinstance(node, ast.FunctionDef)
    }
    assert functions == {"check_sample_mode"}
    assert get_evaluator_filename("sample_mode") == "check_sample_mode.py"
