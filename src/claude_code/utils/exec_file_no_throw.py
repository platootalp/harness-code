"""
Execute file no-throw utilities.

Migrated from TypeScript exec utilities.
"""

from __future__ import annotations

import asyncio
import subprocess
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


ExecResult = dict[str, Any]


def exec_file_no_throw(
    file: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    env: dict | None = None,
) -> ExecResult:
    """Execute a file, returning exit code and output.

    Args:
        file: Path to executable
        args: Command line arguments
        cwd: Working directory
        env: Environment variables

    Returns:
        Dict with 'code', 'stdout', 'stderr' keys.
    """
    try:
        result = subprocess.run(
            [file] + (args or []),
            capture_output=True,
            text=True,
            cwd=cwd,
            env=env,
            timeout=30,
        )
        return {"code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"code": 1, "stdout": "", "stderr": str(e)}


async def exec_file_no_throw_async(
    file: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    env: dict | None = None,
) -> ExecResult:
    """Async version of exec_file_no_throw.

    Runs the synchronous subprocess call in a thread pool to avoid blocking.

    Args:
        file: Path to executable
        args: Command line arguments
        cwd: Working directory
        env: Environment variables

    Returns:
        Dict with 'code', 'stdout', 'stderr' keys.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: exec_file_no_throw(file, args, cwd, env)
    )
