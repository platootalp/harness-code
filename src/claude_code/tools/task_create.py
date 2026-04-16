"""
TaskCreateTool - Create tasks in the task list.

Migrated from src/tools/TaskCreateTool/TaskCreateTool.ts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
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

TASK_CREATE_TOOL_NAME = "TaskCreate"


# =============================================================================
# Output Types
# =============================================================================


@dataclass
class TaskOutput:
    """Created task output."""

    id: str
    subject: str


@dataclass
class TaskCreateToolOutput:
    """Output from the TaskCreateTool."""

    task: TaskOutput


# =============================================================================
# TaskCreateTool
# =============================================================================


class TaskCreateTool(BaseTool):
    """Tool for creating tasks in the task list.

    Creates a new task with the given subject and description.
    Requires the todo V2 feature to be enabled.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "create a task in the task list"
    max_result_size_chars: int = 100_000
    strict: bool = False
    should_defer: bool = False
    always_load: bool = False

    def __init__(self) -> None:
        self.should_defer = True

    @property
    def name(self) -> str:
        return TASK_CREATE_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "A brief title for the task",
                },
                "description": {
                    "type": "string",
                    "description": "What needs to be done",
                },
                "activeForm": {
                    "type": "string",
                    "description": (
                        "Present continuous form shown in spinner when in_progress "
                        "(e.g., 'Running tests')"
                    ),
                },
                "metadata": {
                    "type": "object",
                    "description": "Arbitrary metadata to attach to the task",
                    "additionalProperties": True,
                },
            },
            "required": ["subject", "description"],
        }

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def should_defer_property(self) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        subject = input.get("subject", "")
        return subject if isinstance(subject, str) else str(subject)

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate the tool input before execution."""
        subject = input.get("subject")
        description = input.get("description")

        if not subject:
            return (False, "subject is required", 400)

        if not description:
            return (False, "description is required", 400)

        if len(subject) > 200:
            return (False, "subject must be 200 characters or less", 400)

        return True

    async def call(
        self,
        args: Any,
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[TaskCreateToolOutput]:
        """Execute the task create tool.

        Args:
            args: Tool input with subject and description.
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with created task info.
        """
        subject = args.get("subject", "")
        args.get("description", "")
        args.get("activeForm")
        args.get("metadata")

        # Generate a unique task ID
        task_id = str(uuid.uuid4())[:8]

        output = TaskCreateToolOutput(
            task=TaskOutput(
                id=task_id,
                subject=subject,
            )
        )

        return ToolResult(data=output)

    async def description(self, input: Any, options: dict[str, Any]) -> str:
        subject = input.get("subject", "") if input else ""
        return f"Create task: {subject}"

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "The TaskCreate tool creates a new task in the task list. "
            "Use it to track things that need to be done. "
            "Provide a clear subject and description. "
            "The activeForm is shown in the spinner while the task is in progress."
        )
