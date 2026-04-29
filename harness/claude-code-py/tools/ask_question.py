"""
AskUserQuestionTool - Ask the user a question.

This tool asks the user a question and returns their answer.
Supports multiple question types (single-select, multi-select) with optional previews.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "AskUserQuestion"


class AskUserQuestionTool:
    """Ask the user a question.

    Asks the user a question and returns their answer. Supports multiple
    question types (single-select, multi-select) with optional previews.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "ask the user a question with multiple choice options"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Ask the user a question with multiple choice options"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to ask the user a question. "
            "Provide the question text and up to 4 options. "
            "Use multiSelect=true for questions where multiple answers are allowed. "
            "The user's answer will be returned as the tool result."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question text",
                            },
                            "header": {
                                "type": "string",
                                "description": "Short label displayed as a chip/tag",
                            },
                            "options": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {
                                            "type": "string",
                                            "description": "Display text for this option",
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Explanation of what this option means",
                                        },
                                        "preview": {
                                            "type": "string",
                                            "description": "Optional preview content for visual comparison",
                                        },
                                    },
                                    "required": ["label", "description"],
                                },
                                "minItems": 2,
                                "maxItems": 4,
                            },
                            "multiSelect": {
                                "type": "boolean",
                                "description": "Allow multiple answers",
                            },
                        },
                        "required": ["question", "header", "options"],
                    },
                    "minItems": 1,
                    "maxItems": 4,
                },
            },
            "required": ["questions"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "answers": {
                    "type": "object",
                    "description": "Answers keyed by question text",
                },
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "Ask"

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def requires_user_interaction(self) -> bool:
        return True

    def render_tool_use_message(self, input: Any) -> str | None:
        questions = input.get("questions", [])
        if questions:
            return f"Asking user: {questions[0].get('question', '')}"
        return "Asking user a question"

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        answers = content.get("answers", {})
        if not answers:
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": "No answer provided",
            }

        lines = []
        for question, answer in answers.items():
            lines.append(f"Q: {question}\nA: {answer}")

        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": "\n".join(lines),
        }

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        questions = args.get("questions", [])

        # Call the elicitation handler if available
        handle_elicitation = context.handle_elicitation
        if handle_elicitation:
            try:
                result = await handle_elicitation(questions)
                return {"data": {"answers": result}}
            except Exception:
                pass

        # Return placeholder if no elicitation handler
        return {
            "data": {
                "answers": {},
            },
        }
