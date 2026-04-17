"""Skills command for Claude Code.

List available skills.

TypeScript equivalent: src/commands/skills/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


# =============================================================================
# Skills Command
# =============================================================================


@dataclass
class SkillsCommand(BaseCommand):
    """List available skills.

    Displays all available skills that can be invoked via /<skill-name>.
    Skills provide specialized behaviors and tools for specific tasks.

    TypeScript equivalent: src/commands/skills/skills.tsx
    """

    name: str = "skills"
    aliases: list[str] = field(default_factory=list)
    description: str = "List available skills"
    argument_hint: str | None = None
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
        """Execute the skills command.

        Args:
            args: Optional filter for skills.
            context: Execution context.

        Returns:
            CommandResult with list of available skills.
        """
        # Get skill registry from context
        skill_registry: Any = context.get("skill_registry")
        filter_term = args.strip().lower() if args.strip() else ""

        lines = ["Available Skills", ""]

        if skill_registry is not None:
            # Use the skill registry
            try:
                all_skills = skill_registry.list_user_invocable()
            except Exception:
                all_skills = []
        else:
            # Fallback to skills from context
            all_skills = context.get("skills", [])

        # Group skills by source
        skills_by_source: dict[str, list[Any]] = {}
        for skill in all_skills:
            source = getattr(skill, "source", "unknown") or "unknown"
            if source not in skills_by_source:
                skills_by_source[source] = []
            skills_by_source[source].append(skill)

        # Apply filter if specified
        if filter_term:
            filtered: list[Any] = []
            for skill in all_skills:
                name = getattr(skill, "name", "") or ""
                desc = getattr(skill, "description", "") or ""
                if filter_term in name.lower() or filter_term in desc.lower():
                    filtered.append(skill)
            all_skills = filtered

        if not all_skills:
            if filter_term:
                return CommandResult(
                    type="text",
                    value=f"No skills found matching '{filter_term}'.",
                )
            return CommandResult(
                type="text",
                value=(
                    "No skills found.\n\n"
                    "Skills are defined in:\n"
                    "  .claude/skills/  (project skills)\n"
                    "  ~/.claude/skills/ (user skills)\n\n"
                    "Create a SKILL.md file to define a new skill."
                ),
            )

        # Format skills list
        for source, skills in sorted(skills_by_source.items()):
            source_label = self._format_source(source)
            lines.append(f"## {source_label}")

            for skill in sorted(skills, key=lambda s: getattr(s, "name", "") or ""):
                name = getattr(skill, "name", "unnamed") or "unnamed"
                desc = getattr(skill, "description", "") or ""
                arg_hint = getattr(skill, "argument_hint", None)

                # Apply filter
                if filter_term and filter_term not in name.lower() and filter_term not in desc.lower():
                    continue

                if arg_hint:
                    lines.append(f"  /{name} {arg_hint}")
                else:
                    lines.append(f"  /{name}")

                if desc:
                    lines.append(f"      {desc}")

            lines.append("")

        lines.extend([
            "-" * 40,
            "",
            "Use /<skill-name> to invoke a skill.",
            "Use /skills <search-term> to filter skills.",
        ])

        return CommandResult(type="text", value="\n".join(lines))

    def _format_source(self, source: str) -> str:
        """Format skill source for display.

        Args:
            source: Raw source identifier.

        Returns:
            Human-readable source label.
        """
        source_map = {
            "project": "Project Skills",
            "user": "User Skills",
            "builtin": "Built-in Skills",
            "plugin": "Plugin Skills",
        }
        return source_map.get(source, f"{source.title()} Skills")


# =============================================================================
# Registry
# =============================================================================


def get_all_commands() -> list[BaseCommand]:
    """Get all skills-related commands.

    Returns:
        List of skills command instances.
    """
    return [SkillsCommand()]


def register_builtin_commands(registry: Any) -> None:
    """Register skills commands with a command registry.

    Args:
        registry: Command registry with a register() method.
    """
    for cmd in get_all_commands():
        registry.register(cmd)
