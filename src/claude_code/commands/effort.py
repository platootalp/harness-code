"""
Effort command for Claude Code.

Sets the effort level for model usage.

TypeScript equivalent: src/commands/effort/effort.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


# Valid effort levels
EFFORT_LEVELS: frozenset[str] = frozenset([
    "low",
    "medium",
    "high",
    "max",
    "auto",
])

# Effort level descriptions
EFFORT_DESCRIPTIONS: dict[str, str] = {
    "low": "Quick, straightforward implementation",
    "medium": "Balanced approach with standard testing",
    "high": "Comprehensive implementation with extensive testing",
    "max": "Maximum capability with deepest reasoning (Opus 4.6 only)",
    "auto": "Use the default effort level for your model",
}


@dataclass
class EffortCommand(BaseCommand):
    """Set effort level for model usage.

    Effort levels control how much reasoning and work the model applies:
    - low: Quick responses for simple tasks
    - medium: Balanced for typical tasks
    - high: Thorough analysis and testing
    - max: Maximum reasoning (Opus 4.6 only)
    - auto: Use model defaults
    """

    name: str = "effort"
    description: str = "Set effort level for model usage"
    argument_hint: str | None = "[low|medium|high|max|auto]"
    availability: list[str] = field(
        default_factory=lambda: [Availability.ALL.value]
    )
    command_type: CommandType = CommandType.LOCAL
    immediate: bool = True
    supports_non_interactive: bool = True

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the effort command."""
        arg = args.strip().lower() if args.strip() else ""

        # Help flag
        if arg in ("help", "-h", "--help"):
            return CommandResult(
                type="text",
                value=(
                    "Usage: /effort [low|medium|high|max|auto]\n\n"
                    "Effort levels:\n"
                    "- low: Quick, straightforward implementation\n"
                    "- medium: Balanced approach with standard testing\n"
                    "- high: Comprehensive implementation with extensive testing\n"
                    "- max: Maximum capability with deepest reasoning (Opus 4.6 only)\n"
                    "- auto: Use the default effort level for your model"
                ),
            )

        # No argument - show current status
        if not arg or arg in ("current", "status"):
            return CommandResult(
                type="text",
                value="Effort level: auto (currently medium)",
            )

        # Validate and set effort level
        if arg not in EFFORT_LEVELS:
            return CommandResult(
                type="text",
                value=f"Invalid argument: {args}. Valid options are: low, medium, high, max, auto",
            )

        description = EFFORT_DESCRIPTIONS.get(arg, "")
        return CommandResult(
            type="text",
            value=f"Set effort level to {arg}: {description}",
        )
