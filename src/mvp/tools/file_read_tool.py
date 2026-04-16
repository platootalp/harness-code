"""FileRead tool - read files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .base import ToolContext, ToolResult, build_tool


@dataclass
class FileReadToolInput:
    file_path: str
    limit: int | None = None  # max lines


file_read_tool = build_tool({
    'name': 'FileRead',
    'input_schema': FileReadToolInput,
    'is_read_only': lambda _: True,
    'is_concurrency_safe': lambda _: True,
    'description': lambda inp: f"Read file: {inp.file_path}" if inp else "Read a file",

    'call': lambda inp, ctx: _read_file(inp, ctx),
})


def _read_file(inp: FileReadToolInput, ctx: ToolContext) -> ToolResult:
    """Read a file."""
    try:
        path = Path(ctx.cwd) / inp.file_path
        content = path.read_text()

        if inp.limit:
            lines = content.split('\n')[:inp.limit]
            content = '\n'.join(lines)

        return ToolResult(data={
            'content': content,
            'file_path': str(path),
            'size': len(content),
        })
    except FileNotFoundError:
        return ToolResult(data={'content': '', 'error': 'File not found'}, error='File not found')
    except Exception as e:
        return ToolResult(data={'content': '', 'error': str(e)}, error=str(e))
