"""Tool registry."""
from __future__ import annotations

from .bash_tool import bash_tool
from .file_edit_tool import file_edit_tool
from .file_read_tool import file_read_tool
from .grep_tool import grep_tool


def get_all_base_tools() -> list:
    """Get all available tools."""
    return [
        bash_tool,
        file_read_tool,
        file_edit_tool,
        grep_tool,
    ]


def get_tools() -> list:
    """Get tools filtered by permission context."""
    return get_all_base_tools()


__all__ = ['get_all_base_tools', 'get_tools']
