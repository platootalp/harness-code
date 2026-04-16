"""Agents command for Claude Code.

Manage agent configurations.

TypeScript equivalent: src/commands/agents/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


# =============================================================================
# Agents Command
# =============================================================================


@dataclass
class AgentsCommand(BaseCommand):
    """Manage agent configurations.

    Displays available agent configurations and allows switching between them.
    Agents define system prompts and behaviors for specialized tasks.

    TypeScript equivalent: src/commands/agents/agents.tsx
    """

    name: str = "agents"
    aliases: list[str] = field(default_factory=list)
    description: str = "Manage agent configurations"
    argument_hint: str | None = "[agent-name]"
    command_type: CommandType = CommandType.LOCAL_JSX
    availability: list[str] = field(default_factory=lambda: [Availability.ALL.value])
    source: str = "builtin"

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the agents command.

        Args:
            args: Optional agent name to switch to.
            context: Execution context.

        Returns:
            CommandResult with agent information.
        """
        # Get agent definitions from context
        agent_definitions: list[dict[str, Any]] = context.get("agent_definitions", [])
        current_agent: str | None = context.get("current_agent")

        # Get current model
        repl_state: Any = context.get("_repl_state")
        if repl_state is not None and hasattr(repl_state, "session"):
            current_model = getattr(repl_state.session, "model", None)
        else:
            current_model = None

        lines = ["Available Agents", ""]

        # Define built-in agents
        builtin_agents = [
            {
                "name": "default",
                "description": "Default Claude behavior for general assistance",
                "source": "built-in",
            },
            {
                "name": "coder",
                "description": "Specialized for software development tasks",
                "source": "built-in",
            },
            {
                "name": "reviewer",
                "description": "Code review and analysis specialist",
                "source": "built-in",
            },
            {
                "name": "architect",
                "description": "System design and architecture planning",
                "source": "built-in",
            },
        ]

        # Merge with context agents
        all_agents: dict[str, dict[str, Any]] = {}
        for agent in builtin_agents:
            all_agents[agent["name"]] = agent

        for agent_def in agent_definitions:
            name = agent_def.get("name", "unknown")
            if name not in all_agents:
                all_agents[name] = agent_def

        if not all_agents:
            return CommandResult(
                type="text",
                value=(
                    "No agent configurations found.\n\n"
                    "Agents can be defined in:\n"
                    "  .claude/settings.json  (project agents)\n"
                    "  ~/.claude/settings.json (user agents)\n\n"
                    "Example agent definition:\n"
                    '  { "agents": { "myagent": { "description": "...", "system-prompt": "..." } } }'
                ),
            )

        # Show current agent
        if current_agent:
            lines.append(f"Current agent: {current_agent}")
            lines.append("")

        # Group agents by source
        by_source: dict[str, list[dict[str, Any]]] = {}
        for _name, agent in all_agents.items():
            source = agent.get("source", "unknown")
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(agent)

        # Format list
        for source, agents in sorted(by_source.items()):
            source_label = self._format_source(source)
            lines.append(f"## {source_label}")

            for agent in sorted(agents, key=lambda a: a.get("name", "")):
                name = agent.get("name", "unknown")
                desc = agent.get("description", "")
                is_current = name == current_agent

                marker = " * " if is_current else "   "
                lines.append(f"  {marker}/agent {name}")

                if desc:
                    lines.append(f"       {desc}")

                # Show model if specified
                model = agent.get("model")
                if model:
                    lines.append(f"       Model: {model}")

            lines.append("")

        lines.extend([
            "-" * 40,
            "",
            "Usage:",
            "  /agents            - List all agents",
            "  /agents <name>     - Switch to an agent",
            "",
            f"Current model: {current_model or 'default'}",
        ])

        return CommandResult(type="text", value="\n".join(lines))

    def _format_source(self, source: str) -> str:
        """Format agent source for display.

        Args:
            source: Raw source identifier.

        Returns:
            Human-readable source label.
        """
        source_map = {
            "built-in": "Built-in Agents",
            "projectSettings": "Project Agents",
            "userSettings": "User Agents",
            "localSettings": "Local Agents",
            "plugin": "Plugin Agents",
            "policySettings": "Policy Agents",
        }
        return source_map.get(source, f"{source.title()} Agents")


# =============================================================================
# Registry
# =============================================================================


def get_all_commands() -> list[BaseCommand]:
    """Get all agents-related commands.

    Returns:
        List of agents command instances.
    """
    return [AgentsCommand()]


def register_builtin_commands(registry: Any) -> None:
    """Register agents commands with a command registry.

    Args:
        registry: Command registry with a register() method.
    """
    for cmd in get_all_commands():
        registry.register(cmd)
