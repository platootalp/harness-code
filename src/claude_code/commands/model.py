"""Model command for Claude Code.

Shows or sets the current AI model for Claude Code.

TypeScript equivalent: src/commands/model/model.tsx, src/commands/model/index.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass

# Common info arguments
COMMON_INFO_ARGS: frozenset[str] = frozenset({"--version", "-v", "--info", "?"})

# Common help arguments
COMMON_HELP_ARGS: frozenset[str] = frozenset({"--help", "-h", "-?"})

# Known model aliases
MODEL_ALIASES: tuple[str, ...] = (
    "sonnet",
    "sonnet-4-7",
    "sonnet",
    "opus",
    "opus-4-6",
    "haiku",
    "haiku-4-3",
    "claude-opus-4-5",
    "claude-sonnet-4-7",
    "claude-haiku-4-3",
)


def is_known_alias(model: str) -> bool:
    """Check if a model name is a known alias.

    Args:
        model: Model name to check.

    Returns:
        True if the model is a known alias.
    """
    return model.lower().strip() in MODEL_ALIASES


def render_model_label(model: str | None) -> str:
    """Render a model name as a display label.

    Args:
        model: Model name or None.

    Returns:
        Display label for the model.
    """
    if model is None:
        return "claude-sonnet-4-7 (default)"
    return model


@dataclass
class ModelCommand(BaseCommand):
    """Show or set the current model.

    When called without arguments, opens the model selection menu.
    When called with a model name, switches to that model.
    When called with 'default', resets to the default model.

    TypeScript equivalent: src/commands/model/model.tsx, src/commands/model/index.ts
    """

    name: str = "model"
    description: str = "Set the AI model for Claude Code"
    argument_hint: str | None = "[model]"
    command_type: CommandType = CommandType.LOCAL_JSX
    source: str = "builtin"

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the model command."""
        trimmed_args = args.strip() if args.strip() else ""

        if trimmed_args in COMMON_INFO_ARGS:
            # Show current model info
            repl_state: dict[str, Any] | None = context.get("_repl_state")
            current_model = (
                repl_state.session.model
                if repl_state and hasattr(repl_state, "session")
                else None
            ) or "claude-sonnet-4-7"

            return CommandResult(
                type="jsx",
                value=None,
                node={
                    "type": "model",
                    "mode": "info",
                    "current_model": current_model,
                    "context": context,
                },
            )

        if trimmed_args in COMMON_HELP_ARGS:
            return CommandResult(
                type="text",
                value="Run /model to open the model selection menu, or /model [modelName] to set the model.",
            )

        if trimmed_args:
            # Setting a specific model
            return await self._set_model(trimmed_args, context)

        # No args - open model picker
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "model",
                "mode": "picker",
                "context": context,
            },
        )

    async def _set_model(
        self,
        model_arg: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Set the model to a specific value.

        Args:
            model_arg: The model name or 'default'.
            context: Execution context.

        Returns:
            CommandResult with result message.
        """
        repl_state: dict[str, Any] | None = context.get("_repl_state")

        if model_arg == "default":
            target_model: str | None = None
        else:
            target_model = model_arg
            # Validation would happen via API call
            # For now, accept as-is (API rejects invalid models at runtime)

        # Update the session model
        if repl_state and hasattr(repl_state, "session"):
            repl_state.session.model = target_model

        display_label = render_model_label(target_model)
        msg = f"Set model to {display_label}"

        return CommandResult(type="text", value=msg)
