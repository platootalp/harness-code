"""
StructuredOutputTool - Return final response as structured JSON.

Migrated from src/tools/SyntheticOutputTool/SyntheticOutputTool.ts.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from ..models.tool import (
    BaseTool,
    ToolResult,
    ToolUseContext,
    ValidationResult,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name
# =============================================================================

SYNTHETIC_OUTPUT_TOOL_NAME = "StructuredOutput"


# =============================================================================
# StructuredOutputTool
# =============================================================================


class StructuredOutputTool(BaseTool):
    """Tool for returning structured output in the requested format.

    This tool validates input against a JSON schema and returns the input
    as structured output. It is used primarily for non-interactive SDK/CLI
    workflows where structured data needs to be returned.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "return the final response as structured JSON"
    should_defer: bool = False
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = True

    @property
    def name(self) -> str:
        return SYNTHETIC_OUTPUT_TOOL_NAME

    @property
    def description_text(self) -> str:
        return "Return structured output in the requested format"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to return your final response in the requested "
            "structured format. You MUST call this tool exactly once at the "
            "end of your response to provide the structured output."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        """Input schema - passthrough (empty object)."""
        return {"type": "object", "properties": {}}

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "string": {
                    "type": "string",
                    "description": "Structured output tool result",
                },
                "structured_output": {
                    "type": "object",
                    "description": "The structured output data",
                },
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "StructuredOutput"

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def is_open_world(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        if not input:
            return ""
        try:
            return json.dumps(input)
        except (TypeError, ValueError):
            return str(input)

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """StructuredOutput does not need validation."""
        return True

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[Any]:
        """Execute the structured output tool.

        This tool just validates and returns the input as structured output.

        Args:
            args: Tool input (passthrough).
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with structured_output containing the input data.
        """
        return ToolResult(
            data={
                "string": "Structured output provided successfully",
                "structured_output": args,
            }
        )

    def map_tool_result_to_tool_result_block_param(
        self,
        content: dict[str, Any],
        tool_use_id: str,
    ) -> dict[str, Any]:
        """Map structured output tool result to tool result block param."""
        # Extract the string content from the result
        content_str = content.get("string", "")
        if not content_str:
            # Fallback: try to format the structured output
            structured = content.get("structured_output", {})
            try:
                content_str = json.dumps(structured)
            except (TypeError, ValueError):
                content_str = str(structured)

        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": content_str,
        }
