"""Command registry."""
from __future__ import annotations

from typing import Callable, Awaitable

from .commit_cmd import commit_command
from .help_cmd import help_command


COMMANDS: list[dict] = [
    help_command,
    commit_command,
]


def get_commands() -> list[dict]:
    return COMMANDS


def find_command(name: str) -> dict | None:
    for cmd in COMMANDS:
        if cmd['name'] == name:
            return cmd
        if 'aliases' in cmd and name in cmd['aliases']:
            return cmd
    return None


__all__ = ['get_commands', 'find_command']
