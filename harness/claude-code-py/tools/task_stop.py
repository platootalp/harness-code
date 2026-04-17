"""
TaskStopTool - Stop a running background task.

This tool stops a running background task by its ID.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "TaskStop"


class TaskStopTool:
    """Stop a running background task.

    Stops a running task identified by its task_id. Supports the deprecated
    shell_id parameter for backward compatibility.

    Attributes:
        name: The tool's unique identifier.
        aliases: Backward-compatible alias names.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = ["KillShell"]
    search_hint: str | None = "kill a running background task"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Stop a running background task by ID"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to stop a running background task by its ID. "
            "The task must be in a running state. "
            "Returns the task ID, type, and command that was stopped."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The ID of the background task to stop",
                },
                "shell_id": {
                    "type": "string",
                    "description": "Deprecated: use task_id instead",
                },
            },
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "task_id": {"type": "string"},
                "task_type": {"type": "string"},
                "command": {"type": "string"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "Stop Task"

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        return input.get("task_id") or input.get("shell_id") or ""

    def validate_input(self, input: Any, context: ToolUseContext) -> tuple[bool, str, int] | bool:
        task_id = input.get("task_id") or input.get("shell_id")
        if not task_id:
            return (False, "Missing required parameter: task_id", 1)

        get_app_state = context.get_app_state
        if get_app_state is None:
            return (False, "Cannot access app state", 1)

        app_state = get_app_state()
        tasks = getattr(app_state, "tasks", {})
        task = tasks.get(task_id)

        if not task:
            return (False, f"No task found with ID: {task_id}", 1)

        task_status = getattr(task, "status", "")
        if task_status != "running":
            return (False, f"Task {task_id} is not running (status: {task_status})", 3)

        return True

    def render_tool_use_message(self, input: Any) -> str | None:
        return None

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        import json

        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": json.dumps(content),
        }

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        task_id = args.get("task_id") or args.get("shell_id")

        if not task_id:
            raise ValueError("Missing required parameter: task_id")

        get_app_state = context.get_app_state
        set_app_state = context.set_app_state
        abort_controller = context.abort_controller

        app_state = get_app_state() if get_app_state else None
        tasks = getattr(app_state, "tasks", {}) if app_state else {}
        task = tasks.get(task_id)

        if not task:
            return {
                "data": {
                    "message": f"No task found with ID: {task_id}",
                    "task_id": task_id,
                    "task_type": "",
                    "command": "",
                },
            }

        task_type = getattr(task, "type", "")
        description = getattr(task, "description", "")

        # Mark task as cancelled
        if set_app_state:
            def _cancel_task(prev: Any) -> Any:
                if prev is None:
                    return None
                tasks_dict = getattr(prev, "tasks", {})
                if task_id not in tasks_dict:
                    return prev
                new_tasks = dict(tasks_dict)
                existing_task = new_tasks[task_id]
                existing_task.status = "cancelled"
                return prev

            set_app_state(_cancel_task)

        # Signal abort if controller exists
        if abort_controller:
            with contextlib.suppress(Exception):
                abort_controller.abort()  # type: ignore[attr-defined]

        return {
            "data": {
                "message": f"Successfully stopped task: {task_id} ({description})",
                "task_id": task_id,
                "task_type": task_type,
                "command": description,
            },
        }
