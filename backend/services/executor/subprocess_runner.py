"""Subprocess-isolated evaluator runner with timeout and empty environment.

Executes Python code strings in a child process with:
- env={}: No inherited server secrets (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)
- asyncio.wait_for + proc.communicate(): Hard timeout without pipe deadlock
- proc.kill() + await proc.wait(): Clean zombie prevention on timeout

IMPORTANT — proc.communicate() vs proc.wait():
Always use proc.communicate() when stdout/stderr are PIPE. Using proc.wait()
risks a pipe-buffer deadlock if the subprocess writes >64KB to stdout/stderr.
communicate() drains both pipes concurrently while waiting for exit.

IMPORTANT — uvloop env={} caveat:
uvloop < 0.17.0 treated env={} as env=None (inheriting everything). This was
fixed in v0.17.0. This project uses uvicorn[standard] which pins a recent
uvloop. Verified safe in verify step below.

IMPORTANT — macOS env={} caveat:
On macOS, the kernel injects a small number of system locale variables
(__CF_USER_TEXT_ENCODING, LC_CTYPE) at the exec() level, even when env={}
is passed. These are harmless locale settings — NOT server secrets. The
security goal (no ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.) is fully achieved.
On Linux, env={} truly results in an empty environment.
"""

from __future__ import annotations

import asyncio
import logging
import sys

logger = logging.getLogger(__name__)


async def run_evaluator_subprocess(
    code: str,
    timeout: float = 10.0,
) -> dict:
    """Execute a Python code string in a subprocess-isolated child process.

    The child process has an empty environment (env={}) so it cannot access
    server secrets. It is killed and a structured error is returned if the
    timeout expires.

    Args:
        code: Python source code to execute, passed via `python -c`.
        timeout: Maximum seconds to wait before killing the process.
                 Defaults to 10.0 seconds.

    Returns:
        One of three structured dicts:
        - {"status": "ok", "stdout": str, "stderr": str}
        - {"status": "error", "returncode": int, "stderr": str}
        - {"status": "timeout", "error": str}
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={},  # Empty environment — no inherited secrets or PATH
        )

        # Use communicate() NOT wait() to avoid pipe-buffer deadlock
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            logger.warning(
                "Evaluator subprocess exited with code %d: %s",
                proc.returncode,
                stderr[:500],
            )
            return {
                "status": "error",
                "returncode": proc.returncode,
                "stderr": stderr,
            }

        return {"status": "ok", "stdout": stdout, "stderr": stderr}

    except asyncio.TimeoutError:
        # Kill the process and wait for it to avoid zombie entries
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass  # Already exited between timeout and kill
        logger.warning("Evaluator subprocess exceeded %.1f second timeout", timeout)
        return {
            "status": "timeout",
            "error": f"Evaluator exceeded {timeout}s timeout",
        }
