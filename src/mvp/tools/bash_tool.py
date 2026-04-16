"""Bash tool - execute shell commands."""
from __future__ import annotations

import asyncio
import shlex
from dataclasses import dataclass

from .base import ToolContext, ToolResult, build_tool


@dataclass
class BashToolInput:
    command: str
    timeout: int = 30


def is_read_only_command(command: str) -> bool:
    """Check if a bash command is read-only."""
    readonly_commands = {
        'ls', 'cat', 'head', 'tail', 'grep', 'find', 'pwd', 'echo',
        'which', 'whoami', 'date', 'stat', 'diff', 'sort', 'uniq',
    }
    cmd = command.split()[0] if command.split() else ''
    return cmd in readonly_commands


bash_tool = build_tool({
    'name': 'Bash',
    'input_schema': BashToolInput,
    'is_read_only': lambda inp: is_read_only_command(inp.command) if inp else False,
    'is_concurrency_safe': lambda inp: is_read_only_command(inp.command) if inp else False,
    'description': lambda inp: f"Run shell command: {inp.command}" if inp else "Run shell command",

    'call': lambda inp, ctx: _execute_bash(inp, ctx),
})


async def _execute_bash(inp: BashToolInput, ctx: ToolContext) -> ToolResult:
    """Execute a bash command."""
    try:
        cmd = inp.command
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=ctx.cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=inp.timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(data={'stdout': '', 'stderr': 'Timeout', 'exit_code': -1})

        return ToolResult(data={
            'stdout': stdout.decode() if stdout else '',
            'stderr': stderr.decode() if stderr else '',
            'exit_code': proc.returncode or 0,
        })
    except Exception as e:
        return ToolResult(data={'stdout': '', 'stderr': str(e), 'exit_code': 1}, error=str(e))
