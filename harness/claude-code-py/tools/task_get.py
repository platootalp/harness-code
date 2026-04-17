"""
TaskGetTool - Retrieve a task by ID.

This tool fetches and returns details for a specific task from the task list.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "TaskGet"


class TaskGetTool:
    """Retrieve a task by its ID.

    This tool fetches and returns the details of a specific task from the task list,
    including its subject, description, status, and blocking relationships.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "retrieve a task by ID"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Retrieve a task by its ID from the task list"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to retrieve details about a specific task by its ID. "
            "The tool returns the task's subject, description, status, and blocking relationships. "
            "Returns null if the task is not found."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "taskId": {
                    "type": "string",
                    "description": "The ID of the task to retrieve",
                },
            },
            "required": ["taskId"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {"type": "string"},
                        "blocks": {"type": "array", "items": {"type": "string"}},
                        "blockedBy": {"type": "array", "items": {"type": "string"}},
                    },
                    "nullable": True,
                },
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "TaskGet"

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
        task = content.get("task")
        if not task:
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": "Task not found",
            }

        lines = [
            f"Task #{task['id']}: {task['subject']}",
            f"Status: {task['status']}",
            f"Description: {task['description']}",
        ]

        blocked_by = task.get("blockedBy", [])
        if blocked_by:
            lines.append(f"Blocked by: {', '.join(f'#{x}' for x in blocked_by)}")

        blocks = task.get("blocks", [])
        if blocks:
            lines.append(f"Blocks: {', '.join(f'#{x}' for x in blocks)}")

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
        task_id = args.get("taskId")

        # Get app state to find task
        get_app_state = context.get_app_state
        if get_app_state is None:
            return {
                "data": {
                    "task": None,
                },
            }

        app_state = get_app_state()
        tasks = getattr(app_state, "tasks", {})

        task = tasks.get(task_id)
        if not task:
            return {
                "data": {
                    "task": None,
                },
            }

        return {
            "data": {
                "task": {
                    "id": getattr(task, "id", task_id),
                    "subject": getattr(task, "subject", ""),
                    "description": getattr(task, "description", ""),
                    "status": getattr(task, "status", ""),
                    "blocks": getattr(task, "blocks", []),
                    "blockedBy": getattr(task, "blockedBy", []),
                },
            },
        }
