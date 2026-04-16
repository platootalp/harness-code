"""Context command for Claude Code.

Show context usage information.

TypeScript equivalent: src/commands/context/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Availability, BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


# =============================================================================
# Context Command
# =============================================================================


@dataclass
class ContextCommand(BaseCommand):
    """Show context usage information.

    Displays a breakdown of context token usage by category,
    including messages, tools, skills, and system prompts.

    In interactive mode, shows a colored grid visualization.
    In non-interactive mode, shows a markdown table.

    TypeScript equivalent: src/commands/context/
    """

    name: str = "context"
    aliases: list[str] = field(default_factory=list)
    description: str = "Show context usage information"
    argument_hint: str | None = None
    command_type: CommandType = CommandType.LOCAL  # Falls back to text in non-interactive
    availability: list[str] = field(default_factory=lambda: [Availability.ALL.value])
    supports_non_interactive: bool = True  # Falls back to text mode
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the context command."""
        # Get context data from context
        context_data: dict[str, Any] = context.get("context_data", {})

        # Gather context data
        messages: list[Any] = context.get("messages", [])
        model: str = context.get("model", "unknown")
        mcp_tools: list[Any] = context.get("mcp_tools", [])
        skills: list[Any] = context.get("active_skills", [])
        memory_files: list[str] = context.get("memory_files", [])

        # Calculate basic stats
        message_count = len(messages)
        message_chars = sum(
            self._get_text_length(msg) for msg in messages
        )
        # Rough estimate: ~4 chars per token
        estimated_tokens = message_chars // 4 if message_chars > 0 else 0

        # Get context limits from data
        max_tokens = context_data.get("max_tokens", 200000)  # Default to 200k

        lines = ["## Context Usage", ""]
        lines.append(f"**Model:** {model}")
        lines.append(f"**Estimated tokens:** ~{estimated_tokens:,}")
        lines.append(f"**Max context:** {max_tokens:,} tokens")

        if message_count > 0 and max_tokens > 0:
            percentage = (estimated_tokens / max_tokens) * 100
            lines.append(f"**Usage:** {percentage:.1f}%")

        lines.append("")

        # Category breakdown
        lines.append("### Estimated Usage by Category")
        lines.append("")
        lines.append("| Category | Est. Tokens | Percentage |")
        lines.append("|----------|-------------|------------|")

        categories = self._build_categories(
            messages, mcp_tools, skills, memory_files, estimated_tokens
        )

        for cat in categories:
            pct = cat["percentage"]
            lines.append(
                f"| {cat['name']} | ~{cat['tokens']:,} | {pct:.1f}% |"
            )

        lines.append("")

        # MCP tools
        if mcp_tools:
            lines.append("### MCP Tools")
            lines.append("")
            lines.append("| Tool | Server |")
            lines.append("|------|--------|")
            for tool in mcp_tools:
                tool_name = getattr(tool, "name", "unknown")
                server = getattr(tool, "server", "unknown")
                lines.append(f"| {tool_name} | {server} |")
            lines.append("")

        # Active skills
        if skills:
            lines.append("### Active Skills")
            lines.append("")
            for skill in skills:
                name = getattr(skill, "name", "unknown")
                desc = getattr(skill, "description", "")
                lines.append(f"- **{name}**: {desc}")
            lines.append("")

        # Memory files
        if memory_files:
            lines.append("### Memory Files")
            lines.append("")
            for mem_file in memory_files:
                lines.append(f"- {mem_file}")
            lines.append("")

        # Additional info
        lines.append("---")
        lines.append("")
        lines.append(
            "Note: Token estimates are approximate. "
            "Actual usage depends on model tokenization."
        )

        return CommandResult(type="text", value="\n".join(lines))

    def _get_text_length(self, msg: Any) -> int:
        """Get the text length of a message."""
        if hasattr(msg, "content_blocks") and msg.content_blocks:
            length = 0
            for block in msg.content_blocks:
                if hasattr(block, "text") and block.text:
                    length += len(block.text)
            return length

        if hasattr(msg, "get"):
            # Dict-like access for backwards compatibility
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        return len(block.get("text", ""))
            elif isinstance(content, str):
                return len(content)

        if hasattr(msg, "text"):
            return len(getattr(msg, "text", ""))

        return 0

    def _build_categories(
        self,
        messages: list[Any],
        mcp_tools: list[Any],
        skills: list[Any],
        memory_files: list[str],
        total_tokens: int,
    ) -> list[dict[str, Any]]:
        """Build context category breakdown."""
        categories: list[dict[str, Any]] = []

        # Messages
        msg_chars = sum(self._get_text_length(m) for m in messages)
        msg_tokens = msg_chars // 4 if msg_chars > 0 else 0
        categories.append({
            "name": "Messages",
            "tokens": msg_tokens,
            "percentage": (msg_tokens / total_tokens * 100) if total_tokens > 0 else 0,
        })

        # MCP tools
        mcp_tokens = len(mcp_tools) * 50  # Rough estimate per tool
        categories.append({
            "name": "MCP Tools",
            "tokens": mcp_tokens,
            "percentage": (mcp_tokens / total_tokens * 100) if total_tokens > 0 else 0,
        })

        # Skills
        skill_tokens = len(skills) * 100  # Rough estimate per skill
        categories.append({
            "name": "Skills",
            "tokens": skill_tokens,
            "percentage": (skill_tokens / total_tokens * 100) if total_tokens > 0 else 0,
        })

        # Memory
        mem_tokens = sum(len(f) for f in memory_files) // 4
        categories.append({
            "name": "Memory",
            "tokens": mem_tokens,
            "percentage": (mem_tokens / total_tokens * 100) if total_tokens > 0 else 0,
        })

        # System prompt
        sys_tokens = 500  # Estimated system prompt size
        categories.append({
            "name": "System Prompt",
            "tokens": sys_tokens,
            "percentage": (sys_tokens / total_tokens * 100) if total_tokens > 0 else 0,
        })

        # Filter out zero-token categories
        return [c for c in categories if c["tokens"] > 0]


# =============================================================================
# Registry
# =============================================================================


def get_all_commands() -> list[BaseCommand]:
    """Get all context-related commands."""
    return [ContextCommand()]


def register_builtin_commands(registry: Any) -> None:
    """Register context commands with a command registry."""
    for cmd in get_all_commands():
        registry.register(cmd)
