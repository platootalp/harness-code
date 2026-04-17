"""SkillTool - Skill wrapper as a Tool for LLM invocation.

Corresponds to TypeScript's SkillTool in src/tools/SkillTool/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .definition import SkillDefinition, ToolUseContext
from .executor import SkillExecutor

if TYPE_CHECKING:
    from ..models.message import ContentBlock


# =============================================================================
# Skill Tool Result
# =============================================================================


@dataclass
class SkillToolResult:
    """Result from SkillTool execution."""

    skill_name: str
    content: str
    success: bool = True
    error: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_content_blocks(self) -> list[ContentBlock]:
        """Convert result to content blocks for LLM consumption.

        Returns:
            List of content blocks.
        """
        if self.error:
            return [
                {  # type: ignore[list-item]
                    "type": "text",
                    "text": f"Skill '{self.skill_name}' error: {self.error}",
                }
            ]
        return [{"type": "text", "text": self.content}]  # type: ignore[list-item]


# =============================================================================
# Skill Tool
# =============================================================================


@dataclass
class SkillTool:
    """Skill wrapper as a Tool for LLM invocation.

    Wraps a SkillDefinition as a tool that the LLM can call directly.
    Input schema follows the SkillTool interface from TypeScript.

    Corresponds to TypeScript's SkillTool class in src/tools/SkillTool/.

    Example input schema:
        {
            "skill": "brainstorm",
            "args": "feature ideas for a new API"
        }
    """

    skill: SkillDefinition
    executor: SkillExecutor | None = None

    @property
    def name(self) -> str:
        """Tool name (matches skill name)."""
        return self.skill.name

    @property
    def description(self) -> str:
        """Tool description for typeahead and documentation."""
        base = self.skill.description or f"Execute the {self.skill.name} skill"
        if self.skill.argument_hint:
            return f"{base} {self.skill.argument_hint}"
        return base

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON schema for tool input.

        Returns:
            Tool input schema dict.
        """
        properties: dict[str, Any] = {
            "skill": {
                "type": "string",
                "description": f"The skill name. E.g., '{self.skill.name}'",
            },
        }

        if self.skill.argument_hint:
            properties["args"] = {
                "type": "string",
                "description": f"Arguments for the skill. {self.skill.argument_hint}",
            }

        return {
            "type": "object",
            "properties": properties,
            "required": ["skill"],
        }

    def get_schema(self) -> dict[str, Any]:
        """Get the full tool schema for LLM consumption.

        Returns:
            Tool schema dict with name, description, and input_schema.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    @property
    def aliases(self) -> list[str]:
        """Alternative names for this tool."""
        return list(self.skill.aliases)

    @property
    def always_load(self) -> bool:
        """Whether this tool should always be loaded."""
        return False

    async def execute(
        self,
        args: dict[str, Any],
        context: ToolUseContext | None = None,
    ) -> SkillToolResult:
        """Execute the skill with given arguments.

        Args:
            args: Tool arguments containing 'skill' and optional 'args'.
            context: Optional execution context.

        Returns:
            SkillToolResult with output content.
        """
        if context is None:
            context = ToolUseContext()

        skill_name = args.get("skill", self.skill.name)
        skill_args = args.get("args", "")

        # Use this skill or look up by name
        if skill_name == self.skill.name:
            skill = self.skill
        else:
            # Try to find by name (requires registry access)
            from .registry import get_global_registry

            skill = get_global_registry().get(skill_name)  # type: ignore[assignment]
            if skill is None:
                return SkillToolResult(
                    skill_name=skill_name,
                    content="",
                    success=False,
                    error=f"Skill not found: {skill_name}",
                )

        # Get executor
        executor = self.executor
        if executor is None:
            from .executor import get_global_executor

            executor = get_global_executor()

        # Execute
        try:
            result = await executor.execute(
                skill,
                {"skill_args": skill_args},
                context,
            )

            # Convert content blocks to text
            content_parts = []
            for block in result.content:
                if isinstance(block, dict):
                    content_parts.append(block.get("text", ""))
                elif hasattr(block, "text"):
                    content_parts.append(block.text)
                else:
                    content_parts.append(str(block))

            return SkillToolResult(
                skill_name=skill.name,
                content="\n".join(content_parts),
                success=result.error is None,
                error=result.error,
                tool_calls=[
                    {"name": tc.name, "args": tc.arguments}
                    for tc in result.tool_calls
                ],
                duration_ms=result.duration_ms,
            )

        except Exception as e:
            return SkillToolResult(
                skill_name=skill.name,
                content="",
                success=False,
                error=str(e),
            )

    def execute_sync(
        self,
        args: dict[str, Any],
        context: ToolUseContext | None = None,
    ) -> SkillToolResult:
        """Synchronous execute (runs async executor).

        Args:
            args: Tool arguments.
            context: Optional execution context.

        Returns:
            SkillToolResult with output content.
        """
        import asyncio

        return asyncio.run(self.execute(args, context))

    def __repr__(self) -> str:
        """String representation."""
        return f"SkillTool({self.name})"


# =============================================================================
# Skill Tool Factory
# =============================================================================


def create_skill_tool(
    skill: SkillDefinition,
    executor: SkillExecutor | None = None,
) -> SkillTool:
    """Create a SkillTool wrapper for a skill.

    Args:
        skill: The skill definition to wrap.
        executor: Optional skill executor.

    Returns:
        SkillTool instance.
    """
    return SkillTool(skill=skill, executor=executor)


def create_skill_tools_from_registry(
    registry: Any,
    executor: SkillExecutor | None = None,
) -> list[SkillTool]:
    """Create SkillTool instances for all skills in a registry.

    Args:
        registry: Skill registry to create tools from.
        executor: Optional skill executor.

    Returns:
        List of SkillTool instances.
    """
    tools: list[SkillTool] = []
    for skill in registry.list_user_invocable():
        tools.append(SkillTool(skill=skill, executor=executor))
    return tools
