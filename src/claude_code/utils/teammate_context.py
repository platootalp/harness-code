"""
Teammate context utilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# Context storage
_context: dict = {}


def get_teammate_context() -> dict:
    """Get the current teammate context."""
    return _context


def set_teammate_context(context: dict) -> None:
    """Set the current teammate context."""
    global _context
    _context = context


def is_team_lead() -> bool:
    """Check if current agent is team lead."""
    return _context.get("role") == "team-lead" or _context.get("is_lead", False)


def get_current_agent_id() -> str | None:
    """Get current agent ID."""
    return _context.get("agent_id")
