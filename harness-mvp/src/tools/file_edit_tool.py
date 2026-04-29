"""FileEdit tool - edit files."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .base import ToolContext, ToolResult, build_tool


@dataclass
class FileEditToolInput:
    file_path: str
    old_string: str
    new_string: str


file_edit_tool = build_tool({
    'name': 'FileEdit',
    'input_schema': FileEditToolInput,
    'is_read_only': lambda _: False,
    'is_destructive': lambda _: False,
    'description': lambda inp: f"Edit file: {inp.file_path}" if inp else "Edit a file",

    'call': lambda inp, ctx: _edit_file(inp, ctx),
})


def _edit_file(inp: FileEditToolInput, ctx: ToolContext) -> ToolResult:
    """Edit a file by replacing old_string with new_string."""
    try:
        path = Path(ctx.cwd) / inp.file_path
        content = path.read_text()

        if inp.old_string not in content:
            return ToolResult(
                data={'edited': False, 'error': 'old_string not found in file'},
                error='old_string not found in file'
            )

        new_content = content.replace(inp.old_string, inp.new_string, 1)
        path.write_text(new_content)

        return ToolResult(data={
            'edited': True,
            'file_path': str(path),
            'message': f"Replaced {inp.old_string!r} with {inp.new_string!r}",
        })
    except FileNotFoundError:
        return ToolResult(data={'edited': False, 'error': 'File not found'}, error='File not found')
    except Exception as e:
        return ToolResult(data={'edited': False, 'error': str(e)}, error=str(e))
