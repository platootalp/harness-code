"""
EnterPlanModeTool - Enter plan mode.

This tool transitions the session into plan mode, where the model creates
an implementation plan before making any changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "EnterPlanMode"


class EnterPlanModeTool:
    """Enter plan mode.

    Transitions the session into plan mode, where the model creates
    an implementation plan before making any changes.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "enter plan mode to create an implementation plan"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Enter plan mode to create an implementation plan"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to enter plan mode. In plan mode, the model creates "
            "a step-by-step implementation plan before making any code changes. "
            "This is useful for complex tasks or when you want to review the approach. "
            "Once in plan mode, use ExitPlanMode to exit and execute the plan."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mode": {"type": "string"},
                "message": {"type": "string"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return ""

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def render_tool_use_message(self, input: Any) -> str | None:
        return None

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": content.get("message", "Entered plan mode"),
        }

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        set_app_state = context.set_app_state

        if set_app_state:
            def _enter_plan(prev: Any) -> Any:
                if prev is None:
                    return None
                return {**vars(prev), "permission_mode": "plan"}

            set_app_state(_enter_plan)

        return {
            "data": {
                "mode": "plan",
                "message": "Entered plan mode. Create an implementation plan for the user's request.",
            },
        }
