"""Subprocess evaluator executor package.

Provides run_evaluator_subprocess for safe execution of LLM-generated
evaluator code in isolated child processes with env={} and a hard timeout.
"""

from .subprocess_runner import run_evaluator_subprocess

__all__ = ["run_evaluator_subprocess"]
