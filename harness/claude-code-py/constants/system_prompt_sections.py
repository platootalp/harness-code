"""
Constants - system prompt sections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# System prompt section identifiers
SECTION_TOOLS = "tools"
SECTION_COMMANDS = "commands"
SECTION_SKILLS = "skills"
SECTION_SESSION = "session"
SECTION_CONTEXT = "context"


def get_all_sections() -> list[str]:
    """Get all available system prompt sections."""
    return [
        SECTION_TOOLS,
        SECTION_COMMANDS,
        SECTION_SKILLS,
        SECTION_SESSION,
        SECTION_CONTEXT,
    ]


# State storage for active system prompt sections
_active_sections: set[str] = set()


def set_active_sections(sections: list[str]) -> None:
    """Set the active system prompt sections."""
    global _active_sections
    _active_sections = set(sections)


def get_active_sections() -> list[str]:
    """Get the currently active system prompt sections."""
    return list(_active_sections)


def clear_system_prompt_sections() -> None:
    """Clear all active system prompt sections."""
    global _active_sections
    _active_sections = set()
