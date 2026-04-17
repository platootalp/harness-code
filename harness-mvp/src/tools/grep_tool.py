"""GrepTool - search code."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .base import ToolContext, ToolResult, build_tool


@dataclass
class GrepToolInput:
    pattern: str
    path: str = '.'
    case_sensitive: bool = True
    context: int = 0


grep_tool = build_tool({
    'name': 'Grep',
    'input_schema': GrepToolInput,
    'is_read_only': lambda _: True,
    'is_concurrency_safe': lambda _: True,
    'description': lambda inp: f"Search for: {inp.pattern}" if inp else "Search code",

    'call': lambda inp, ctx: _grep(inp, ctx),
})


def _grep(inp: GrepToolInput, ctx: ToolContext) -> ToolResult:
    """Search for a pattern in files."""
    try:
        args = ['grep', '-n']

        if not inp.case_sensitive:
            args.append('-i')

        if inp.context > 0:
            args.extend(['-C', str(inp.context)])

        args.append(inp.pattern)
        args.append(inp.path)

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            cwd=ctx.cwd,
        )

        return ToolResult(data={
            'matches': result.stdout,
            'exit_code': result.returncode,
            'pattern': inp.pattern,
            'path': inp.path,
        })
    except Exception as e:
        return ToolResult(data={'matches': '', 'error': str(e)}, error=str(e))
