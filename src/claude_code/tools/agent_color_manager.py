"""
Agent color management utilities.

Manages the color assignment for standalone agents and teammates
in conversation sessions.

TypeScript equivalent: src/tools/AgentTool/agentColorManager.ts
"""

from __future__ import annotations

# Available agent colors that can be assigned to sessions
AGENT_COLORS: list[str] = [
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "pink",
    "cyan",
]

# Aliases that reset the color to default (gray)
RESET_ALIASES: frozenset[str] = frozenset([
    "default",
    "reset",
    "none",
    "gray",
    "grey",
])

# Default color when reset
DEFAULT_COLOR: str = "default"


def is_valid_color(color: str) -> bool:
    """Check if a color name is valid.

    Args:
        color: The color name to check.

    Returns:
        True if the color is valid.
    """
    return color.lower() in AGENT_COLORS


def is_reset_alias(color: str) -> bool:
    """Check if a color is a reset alias.

    Args:
        color: The color name to check.

    Returns:
        True if the color is a reset alias.
    """
    return color.lower() in RESET_ALIASES


def normalize_color(color: str) -> str | None:
    """Normalize a color input to a valid color or None.

    Args:
        color: The color name to normalize.

    Returns:
        The normalized color name, or None if it's a reset alias.
    """
    color_lower = color.lower()
    if is_reset_alias(color_lower):
        return None
    if is_valid_color(color_lower):
        return color_lower
    return None
