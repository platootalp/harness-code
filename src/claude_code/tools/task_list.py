"""
TaskListTool - List all tasks.

This tool returns a list of all tasks from the task list.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "TaskList"


class TaskListTool:
    """List all tasks from the task list.

    Returns all tasks with their id, subject, status, owner, and blocking relationships.
    Completed tasks that are resolved (all blockers done) are excluded from blockedBy.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "list all tasks"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "List all tasks from the task list"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to list all tasks from the task list. "
            "Each task includes its ID, subject, status, owner, and blocking relationships. "
            "Tasks with completed blockers are shown without the blocked indicator."
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
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "subject": {"type": "string"},
                            "status": {"type": "string"},
                            "owner": {"type": "string"},
                            "blockedBy": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "TaskList"

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
        tasks = content.get("tasks", [])
        if not tasks:
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": "No tasks found",
            }

        lines = []
        for task in tasks:
            owner = task.get("owner")
            owner_str = f" ({owner})" if owner else ""
            blocked_by = task.get("blockedBy", [])
            blocked_str = (
                f" [blocked by {', '.join(f'#{x}' for x in blocked_by)}]"
                if blocked_by
                else ""
            )
            lines.append(
                f"#{task['id']} [{task['status']}] {task['subject']}{owner_str}{blocked_str}"
            )

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
        get_app_state = context.get_app_state
        if get_app_state is None:
            return {"data": {"tasks": []}}

        app_state = get_app_state()
        tasks_dict = getattr(app_state, "tasks", {})

        # Convert tasks dict to list
        all_tasks = []
        for task_id, task in tasks_dict.items():
            # Skip internal tasks
            metadata = getattr(task, "metadata", {})
            if metadata.get("_internal"):
                continue

            all_tasks.append({
                "id": getattr(task, "id", task_id),
                "subject": getattr(task, "subject", ""),
                "status": getattr(task, "status", ""),
                "owner": getattr(task, "owner", None),
                "blockedBy": getattr(task, "blockedBy", []),
            })

        # Build set of resolved task IDs
        resolved_ids = {t["id"] for t in all_tasks if t["status"] == "completed"}

        # Filter blockedBy to exclude resolved tasks
        for task in all_tasks:
            task["blockedBy"] = [
                bid for bid in task["blockedBy"] if bid not in resolved_ids
            ]

        return {"data": {"tasks": all_tasks}}
