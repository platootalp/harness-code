"""
TaskOutputTool - Read output from a background task.

This tool retrieves the output of a running or completed background task.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "TaskOutput"


class TaskOutputTool:
    """Read output from a background task.

    Retrieves the output of a running or completed background task.
    Can block waiting for task completion or return immediately.

    Attributes:
        name: The tool's unique identifier.
        aliases: Backward-compatible aliases.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = ["AgentOutputTool", "BashOutputTool"]
    search_hint: str | None = "read output/logs from a background task"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Read output from a background task"

    @property
    def prompt_text(self) -> str:
        return (
            "Retrieve output from a running or completed background task. "
            "Takes a task_id parameter identifying the task. "
            "Returns the task output along with status information. "
            "Use block=true (default) to wait for task completion. "
            "Use block=false for non-blocking check of current status."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to get output from",
                },
                "block": {
                    "type": "boolean",
                    "description": "Whether to wait for completion (default: true)",
                    "default": True,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Max wait time in ms (default: 30000)",
                    "default": 30000,
                },
            },
            "required": ["task_id"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "retrieval_status": {
                    "type": "string",
                    "enum": ["success", "timeout", "not_ready"],
                },
                "task": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "task_type": {"type": "string"},
                        "status": {"type": "string"},
                        "description": {"type": "string"},
                        "output": {"type": "string"},
                        "exitCode": {"type": "integer", "nullable": True},
                        "error": {"type": "string"},
                    },
                    "nullable": True,
                },
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "Task Output"

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return self.is_read_only(input)

    def is_read_only(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        return str(input.get("task_id", ""))

    def render_tool_use_message(self, input: Any) -> str | None:
        return None

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        retrieval_status = content.get("retrieval_status", "success")
        task = content.get("task")

        if not task:
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": "Task not found",
            }

        if retrieval_status == "timeout":
            content_str = f"Task timed out. Status: {task.get('status', 'unknown')}"
        elif retrieval_status == "not_ready":
            content_str = f"Task still running. Status: {task.get('status', 'unknown')}"
        else:
            content_str = task.get("output", "")

        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": content_str,
        }

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        task_id = args.get("task_id")
        block = args.get("block", True)
        timeout_ms = args.get("timeout", 30000)

        if not task_id:
            raise ValueError("Missing required parameter: task_id")

        get_app_state = context.get_app_state
        if get_app_state is None:
            return {
                "data": {
                    "retrieval_status": "success",
                    "task": None,
                },
            }

        app_state = get_app_state()
        tasks = getattr(app_state, "tasks", {})
        task = tasks.get(task_id)

        if not task:
            return {
                "data": {
                    "retrieval_status": "success",
                    "task": None,
                },
            }

        task_type = getattr(task, "type", "")
        task_status = getattr(task, "status", "")
        description = getattr(task, "description", "")

        # Get output from task
        task_output = getattr(task, "output", None)
        if task_output is None:
            task_output = ""

        exit_code = getattr(task, "exit_code", None)
        error = getattr(task, "error", None)

        result_task = {
            "task_id": task_id,
            "task_type": task_type,
            "status": task_status,
            "description": description,
            "output": str(task_output) if task_output else "",
            "exitCode": exit_code,
            "error": error,
        }

        # Non-blocking: return current state
        if not block:
            if task_status not in ("running", "pending"):
                return {
                    "data": {
                        "retrieval_status": "success",
                        "task": result_task,
                    },
                }
            return {
                "data": {
                    "retrieval_status": "not_ready",
                    "task": result_task,
                },
            }

        # Blocking: wait for completion with timeout
        import asyncio
        from datetime import UTC, datetime

        start_time = datetime.now(UTC)
        abort_controller = context.abort_controller

        while True:
            elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            if elapsed_ms >= timeout_ms:
                # Timeout - refresh task state
                current_app_state = get_app_state()
                current_tasks = getattr(current_app_state, "tasks", {})
                current_task = current_tasks.get(task_id)
                if current_task:
                    result_task["status"] = getattr(current_task, "status", "")
                return {
                    "data": {
                        "retrieval_status": "timeout",
                        "task": result_task,
                    },
                }

            # Check abort signal
            if abort_controller:
                try:
                    if hasattr(abort_controller, "signal") and abort_controller.signal.aborted:
                        break
                except Exception:
                    pass

            current_app_state = get_app_state()
            current_tasks = getattr(current_app_state, "tasks", {})
            current_task = current_tasks.get(task_id)
            if not current_task:
                break

            current_status = getattr(current_task, "status", "")
            if current_status not in ("running", "pending"):
                result_task["status"] = current_status
                result_task["output"] = str(getattr(current_task, "output", ""))
                result_task["exitCode"] = getattr(current_task, "exit_code", None)
                result_task["error"] = getattr(current_task, "error", None)
                return {
                    "data": {
                        "retrieval_status": "success",
                        "task": result_task,
                    },
                }

            # Brief sleep before polling again
            await asyncio.sleep(0.1)

        return {
            "data": {
                "retrieval_status": "success",
                "task": result_task,
            },
        }
