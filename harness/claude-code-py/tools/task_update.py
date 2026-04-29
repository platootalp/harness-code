"""
TaskUpdateTool - Update a task's properties.

This tool allows updating a task's subject, description, status, owner,
blocking relationships, and metadata.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "TaskUpdate"


class TaskUpdateTool:
    """Update a task's properties.

    Allows updating the task's subject, description, activeForm, status,
    owner, addBlocks, addBlockedBy, and metadata fields.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "update a task"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Update a task's properties"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to update a task's properties. "
            "You can update the subject, description, status, owner, "
            "add blocks relationships, or merge metadata. "
            "Use 'deleted' as the status value to delete a task."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "taskId": {
                    "type": "string",
                    "description": "The ID of the task to update",
                },
                "subject": {
                    "type": "string",
                    "description": "New subject for the task",
                },
                "description": {
                    "type": "string",
                    "description": "New description for the task",
                },
                "activeForm": {
                    "type": "string",
                    "description": (
                        "Present continuous form shown in spinner "
                        "when in_progress (e.g., 'Running tests')"
                    ),
                },
                "status": {
                    "type": "string",
                    "description": "New status for the task (pending, in_progress, completed, failed, cancelled, deleted)",
                },
                "addBlocks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Task IDs that this task blocks",
                },
                "addBlockedBy": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Task IDs that block this task",
                },
                "owner": {
                    "type": "string",
                    "description": "New owner for the task",
                },
                "metadata": {
                    "type": "object",
                    "description": (
                        "Metadata keys to merge into the task. "
                        "Set a key to null to delete it."
                    ),
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
                "success": {"type": "boolean"},
                "taskId": {"type": "string"},
                "updatedFields": {"type": "array", "items": {"type": "string"}},
                "error": {"type": "string"},
                "statusChange": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                    },
                },
                "verificationNudgeNeeded": {"type": "boolean"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "TaskUpdate"

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        parts = [input.get("taskId", "")]
        if input.get("status"):
            parts.append(input["status"])
        if input.get("subject"):
            parts.append(input["subject"])
        return " ".join(parts)

    def render_tool_use_message(self, input: Any) -> str | None:
        return None

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        success = content.get("success", False)
        task_id = content.get("taskId", "")
        error = content.get("error")

        if not success:
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": error or f"Task #{task_id} not found",
            }

        updated_fields = content.get("updatedFields", [])
        result_content = f"Updated task #{task_id} {', '.join(updated_fields)}"

        status_change = content.get("statusChange")
        if status_change and status_change.get("to") == "completed":
            result_content += (
                "\n\nTask completed. Call TaskList now to find your next "
                "available task or see if your work unblocked others."
            )

        verification_nudge = content.get("verificationNudgeNeeded")
        if verification_nudge:
            result_content += (
                "\n\nNOTE: You just closed out 3+ tasks and none of them was "
                "a verification step. Before writing your final summary, "
                "spawn the verification agent."
            )

        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": result_content,
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
        subject = args.get("subject")
        description = args.get("description")
        active_form = args.get("activeForm")
        status = args.get("status")
        owner = args.get("owner")
        args.get("addBlocks")
        args.get("addBlockedBy")
        metadata = args.get("metadata")

        get_app_state = context.get_app_state
        set_app_state = context.set_app_state

        if get_app_state is None or set_app_state is None:
            return {
                "data": {
                    "success": False,
                    "taskId": task_id,
                    "updatedFields": [],
                    "error": "Cannot access app state",
                },
            }

        app_state = get_app_state()
        tasks = getattr(app_state, "tasks", {})

        task = tasks.get(task_id)
        if not task:
            return {
                "data": {
                    "success": False,
                    "taskId": task_id,
                    "updatedFields": [],
                    "error": "Task not found",
                },
            }

        updated_fields: list[str] = []
        updates: dict[str, Any] = {}

        existing_subject = getattr(task, "subject", "")
        existing_description = getattr(task, "description", "")
        existing_active_form = getattr(task, "activeForm", "")
        existing_owner = getattr(task, "owner", None)
        existing_status = getattr(task, "status", "")
        existing_metadata = getattr(task, "metadata", {})

        # Handle deletion
        if status == "deleted":
            # Remove task from state
            def _delete_task(prev: Any) -> Any:
                if prev is None:
                    return None
                tasks_dict = getattr(prev, "tasks", {})
                if task_id in tasks_dict:
                    new_tasks = dict(tasks_dict)
                    del new_tasks[task_id]
                    return {**vars(prev), "tasks": new_tasks}
                return prev

            set_app_state(_delete_task)
            return {
                "data": {
                    "success": True,
                    "taskId": task_id,
                    "updatedFields": ["deleted"],
                    "statusChange": {"from": existing_status, "to": "deleted"},
                },
            }

        # Update basic fields
        if subject is not None and subject != existing_subject:
            updates["subject"] = subject
            updated_fields.append("subject")

        if description is not None and description != existing_description:
            updates["description"] = description
            updated_fields.append("description")

        if active_form is not None and active_form != existing_active_form:
            updates["activeForm"] = active_form
            updated_fields.append("activeForm")

        if owner is not None and owner != existing_owner:
            updates["owner"] = owner
            updated_fields.append("owner")

        if metadata is not None:
            merged = {**existing_metadata}
            for key, value in metadata.items():
                if value is None:
                    merged.pop(key, None)
                else:
                    merged[key] = value
            updates["metadata"] = merged
            updated_fields.append("metadata")

        if status is not None and status != existing_status:
            updates["status"] = status
            updated_fields.append("status")

        # Apply updates to task
        if updates:
            def _apply_updates(prev: Any) -> Any:
                if prev is None:
                    return None
                tasks_dict = getattr(prev, "tasks", {})
                if task_id not in tasks_dict:
                    return prev
                new_tasks = dict(tasks_dict)
                existing_task = new_tasks[task_id]
                for key, value in updates.items():
                    setattr(existing_task, key, value)
                return prev

            set_app_state(_apply_updates)

        return {
            "data": {
                "success": True,
                "taskId": task_id,
                "updatedFields": updated_fields,
                "statusChange": (
                    {"from": existing_status, "to": updates.get("status", existing_status)}
                    if "status" in updates
                    else None
                ),
            },
        }
