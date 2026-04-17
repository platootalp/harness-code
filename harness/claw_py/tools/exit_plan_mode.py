"""
ExitPlanModeTool - Exit plan mode.

This tool exits plan mode. When approve=True, the plan is approved and execution
can proceed. When approve=False, the plan is rejected with optional feedback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "ExitPlanMode"


class ExitPlanModeTool:
    """Exit plan mode.

    Exits plan mode. When approve=True, the plan is approved and execution
    can proceed. When approve=False, the plan is rejected with optional feedback.

    Attributes:
        name: The tool's unique identifier.
        aliases: Backward-compatible alias names.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = ["ExitPlanModeV2"]
    search_hint: str | None = "exit plan mode and execute or reject the plan"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Exit plan mode and approve or reject the plan"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to exit plan mode. "
            "Set approve=true to approve the plan and begin execution. "
            "Set approve=false to reject the plan with optional feedback explaining what needs to change."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "allowedPrompts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string"},
                            "prompt": {"type": "string"},
                        },
                    },
                    "description": "Prompt-based permissions needed to implement the plan",
                },
            },
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "approved": {"type": "boolean"},
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

    def render_tool_use_message(self, input: Any) -> str | None:
        return None

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": content.get("message", "Exited plan mode"),
        }

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        args.get("allowedPrompts", [])

        set_app_state = context.set_app_state

        if set_app_state:
            def _exit_plan(prev: Any) -> Any:
                if prev is None:
                    return None
                return {**vars(prev), "permission_mode": "default"}

            set_app_state(_exit_plan)

        return {
            "data": {
                "approved": True,
                "mode": "default",
                "message": "Plan approved. Exiting plan mode and proceeding with implementation.",
            },
        }
