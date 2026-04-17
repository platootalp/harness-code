"""Cost command for Claude Code.

Shows the total cost and duration of the current session.

TypeScript equivalent: src/commands/cost/cost.ts
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


def _is_claude_ai_subscriber() -> bool:
    """Check if the user has a claude.ai subscription.

    Returns:
        True if subscribed.
    """
    return bool(os.environ.get("CLAUDE_AI_SUBSCRIBER"))


@dataclass
class CostCommand(BaseCommand):
    """Show the total cost and duration of the current session.

    TypeScript equivalent: src/commands/cost/cost.ts
    """

    name: str = "cost"
    description: str = "Show the total cost and duration of the current session"
    command_type: CommandType = CommandType.LOCAL
    source: str = "builtin"
    supports_non_interactive: bool = True

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name}
        # Hide if not a subscriber
        self.is_hidden = not _is_claude_ai_subscriber()

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the cost command."""
        # Get cost tracking info from context
        cost_state: dict[str, Any] | None = context.get("_cost_state")
        is_subscriber = context.get("_is_claude_ai_subscriber", False)
        user_type = context.get("_user_type", "user")

        if cost_state is None:
            return CommandResult(
                type="text",
                value="Cost tracking not available.",
            )

        total_cost = cost_state.get("total_cost", 0.0)
        total_input_tokens = cost_state.get("total_input_tokens", 0)
        total_output_tokens = cost_state.get("total_output_tokens", 0)
        is_using_overage = cost_state.get("is_using_overage", False)

        if is_subscriber:
            if is_using_overage:
                value = (
                    "You are currently using your overages to power your "
                    "Claude Code usage. We will automatically switch you back "
                    "to your subscription rate limits when they reset."
                )
            else:
                value = (
                    "You are currently using your subscription to power your "
                    "Claude Code usage."
                )
            if user_type == "ant":
                value += f"\n\n[ANT-ONLY] Showing cost anyway:\n{self._format_cost(total_cost, total_input_tokens, total_output_tokens)}"
        else:
            value = self._format_cost(total_cost, total_input_tokens, total_output_tokens)

        return CommandResult(type="text", value=value)

    def _format_cost(
        self,
        total_cost: float,
        total_input_tokens: int,
        total_output_tokens: int,
    ) -> str:
        """Format cost information as a string."""
        lines = [
            f"Total cost: ${total_cost:.4f}",
            f"Input tokens: {total_input_tokens:,}",
            f"Output tokens: {total_output_tokens:,}",
            f"Total tokens: {total_input_tokens + total_output_tokens:,}",
        ]
        return "\n".join(lines)
