"""Help command - display available commands."""
from __future__ import annotations

help_command = {
    'name': 'help',
    'description': 'Show this help message',
    'command_type': 'local',

    'execute': lambda args, ctx: _show_help(args, ctx),
}


def _show_help(args: str, ctx) -> str:
    """Show help message."""
    from . import get_commands

    commands = get_commands()

    lines = [
        "Available commands:",
        "",
    ]

    for cmd in commands:
        lines.append(f"  /{cmd['name']} - {cmd['description']}")

    lines.extend([
        "",
        "Tools:",
        "  Bash <command> - Execute shell command",
        "  FileRead <path> - Read a file",
        "  FileEdit <path> <old> <new> - Edit a file",
        "  Grep <pattern> - Search for pattern",
    ])

    return '\n'.join(lines)
