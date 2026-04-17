"""
Task type definitions for Claude Code.

This module defines the core task infrastructure including:
- TaskStatus: Enumeration of possible task states
- TaskType: Enumeration of possible task types
- is_terminal_task_status: Check if a status is terminal
- generate_task_id: Generate unique task IDs
- Task: Task data model
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

# =============================================================================
# Enums
# =============================================================================


class TaskStatus(StrEnum):
    """Possible states for a task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(StrEnum):
    """Types of tasks supported by Claude Code."""

    USER_REQUEST = "user_request"
    SUB_AGENT = "sub_agent"
    BACKGROUND = "background"
    CRON = "cron"


# =============================================================================
# Task ID Generation
# =============================================================================

# Task ID prefix mapping
_TASK_ID_PREFIXES: dict[TaskType, str] = {
    TaskType.USER_REQUEST: "u",
    TaskType.SUB_AGENT: "s",
    TaskType.BACKGROUND: "b",
    TaskType.CRON: "c",
}

# Case-insensitive-safe alphabet (digits + lowercase) for task IDs.
_TASK_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def _get_task_id_prefix(task_type: TaskType) -> str:
    """Get the prefix for a task ID based on task type."""
    return _TASK_ID_PREFIXES.get(task_type, "x")


def generate_task_id(task_type: TaskType) -> str:
    """Generate a unique task ID for the given task type.

    Args:
        task_type: The type of task to generate an ID for.

    Returns:
        A unique task ID string with a type-specific prefix.
    """
    prefix = _get_task_id_prefix(task_type)
    random_bytes = secrets.token_bytes(8)
    task_id = prefix
    for byte in random_bytes:
        task_id += _TASK_ID_ALPHABET[byte % len(_TASK_ID_ALPHABET)]
    return task_id


# =============================================================================
# Task Status Helpers
# =============================================================================


def is_terminal_task_status(status: TaskStatus) -> bool:
    """Check if a task status is terminal (no further transitions).

    Terminal statuses are completed, failed, and cancelled. This is used to guard
    against injecting messages into dead teammates, evicting finished tasks
    from AppState, and orphan-cleanup paths.

    Args:
        status: The task status to check.

    Returns:
        True if the status is terminal.
    """
    return status in (
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    )


# =============================================================================
# Task (Main Data Model)
# =============================================================================


@dataclass
class Task:
    """Task data model.

    Represents a unit of work that can be executed by Claude Code.
    Tasks have a type, status, input, output, and metadata.

    Attributes:
        id: Unique task identifier.
        type: The type of task.
        status: Current task status.
        input: Task input data.
        output: Task output data (set on completion).
        error: Error message (set on failure).
        created_at: Timestamp when task was created (milliseconds since epoch).
        updated_at: Timestamp when task was last updated (milliseconds since epoch).
        metadata: Additional task metadata.
    """

    id: str
    type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    input: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    error: str | None = None
    created_at: int = field(default_factory=lambda: int(datetime.now(UTC).timestamp() * 1000))
    updated_at: int = field(default_factory=lambda: int(datetime.now(UTC).timestamp() * 1000))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert task to a dictionary representation.

        Returns:
            Dictionary with all task fields, with enums serialized as strings.
        """
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, TaskType) else self.type,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "input": self.input,
            "output": self.output,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Create a Task instance from a dictionary.

        Args:
            data: Dictionary containing task fields.

        Returns:
            A new Task instance populated from the dictionary.
        """
        type_val = data.get("type", "user_request")
        if isinstance(type_val, str):
            type_val = TaskType(type_val)

        status_val = data.get("status", "pending")
        if isinstance(status_val, str):
            status_val = TaskStatus(status_val)

        return cls(
            id=data["id"],
            type=type_val,
            status=status_val,
            input=data.get("input", {}),
            output=data.get("output"),
            error=data.get("error"),
            created_at=data.get("created_at", 0),
            updated_at=data.get("updated_at", 0),
            metadata=data.get("metadata", {}),
        )
