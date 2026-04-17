"""
Tests for task models.
"""

from __future__ import annotations

import pytest

from claude_code.models.task import (
    Task,
    TaskStatus,
    TaskType,
    generate_task_id,
    is_terminal_task_status,
)


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self) -> None:
        """Test that TaskStatus enum has expected values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_from_string(self) -> None:
        """Test creating TaskStatus from string value."""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("running") == TaskStatus.RUNNING
        assert TaskStatus("completed") == TaskStatus.COMPLETED
        assert TaskStatus("failed") == TaskStatus.FAILED
        assert TaskStatus("cancelled") == TaskStatus.CANCELLED


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_type_values(self) -> None:
        """Test that TaskType enum has expected values."""
        assert TaskType.USER_REQUEST.value == "user_request"
        assert TaskType.SUB_AGENT.value == "sub_agent"
        assert TaskType.BACKGROUND.value == "background"
        assert TaskType.CRON.value == "cron"

    def test_task_type_from_string(self) -> None:
        """Test creating TaskType from string value."""
        assert TaskType("user_request") == TaskType.USER_REQUEST
        assert TaskType("sub_agent") == TaskType.SUB_AGENT
        assert TaskType("background") == TaskType.BACKGROUND
        assert TaskType("cron") == TaskType.CRON


class TestIsTerminalTaskStatus:
    """Tests for is_terminal_task_status helper."""

    def test_terminal_statuses(self) -> None:
        """Test that completed, failed, and cancelled are terminal."""
        assert is_terminal_task_status(TaskStatus.COMPLETED) is True
        assert is_terminal_task_status(TaskStatus.FAILED) is True
        assert is_terminal_task_status(TaskStatus.CANCELLED) is True

    def test_non_terminal_statuses(self) -> None:
        """Test that pending and running are not terminal."""
        assert is_terminal_task_status(TaskStatus.PENDING) is False
        assert is_terminal_task_status(TaskStatus.RUNNING) is False


class TestGenerateTaskId:
    """Tests for generate_task_id function."""

    def test_generates_correct_prefix(self) -> None:
        """Test that task IDs have correct type-specific prefixes."""
        assert generate_task_id(TaskType.USER_REQUEST).startswith("u")
        assert generate_task_id(TaskType.SUB_AGENT).startswith("s")
        assert generate_task_id(TaskType.BACKGROUND).startswith("b")
        assert generate_task_id(TaskType.CRON).startswith("c")

    def test_id_length(self) -> None:
        """Test that generated IDs have correct length."""
        task_id = generate_task_id(TaskType.USER_REQUEST)
        assert len(task_id) == 9  # 1 prefix + 8 random chars

    def test_ids_are_unique(self) -> None:
        """Test that generated IDs are unique."""
        ids = [generate_task_id(TaskType.USER_REQUEST) for _ in range(100)]
        assert len(set(ids)) == 100

    def test_id_uses_valid_alphabet(self) -> None:
        """Test that generated IDs use only valid alphabet characters."""
        task_id = generate_task_id(TaskType.USER_REQUEST)
        # Skip prefix, check rest
        suffix = task_id[1:]
        valid_chars = set("0123456789abcdefghijklmnopqrstuvwxyz")
        assert all(c in valid_chars for c in suffix)


class TestTask:
    """Tests for Task dataclass."""

    def test_create_basic(self) -> None:
        """Test creating a basic task."""
        task = Task(
            id="task_1",
            type=TaskType.USER_REQUEST,
            input={"prompt": "Hello"},
        )
        assert task.id == "task_1"
        assert task.type == TaskType.USER_REQUEST
        assert task.status == TaskStatus.PENDING
        assert task.input == {"prompt": "Hello"}
        assert task.output is None
        assert task.error is None

    def test_create_with_all_fields(self) -> None:
        """Test creating task with all fields specified."""
        task = Task(
            id="task_2",
            type=TaskType.SUB_AGENT,
            status=TaskStatus.RUNNING,
            input={"prompt": "Run analysis"},
            output=None,
            error=None,
            created_at=1000,
            updated_at=2000,
            metadata={"priority": "high"},
        )
        assert task.id == "task_2"
        assert task.type == TaskType.SUB_AGENT
        assert task.status == TaskStatus.RUNNING
        assert task.input == {"prompt": "Run analysis"}
        assert task.output is None
        assert task.error is None
        assert task.created_at == 1000
        assert task.updated_at == 2000
        assert task.metadata == {"priority": "high"}

    def test_create_completed_task(self) -> None:
        """Test creating a completed task with output."""
        task = Task(
            id="task_3",
            type=TaskType.BACKGROUND,
            status=TaskStatus.COMPLETED,
            input={"task": "process data"},
            output={"result": "done", "count": 42},
        )
        assert task.id == "task_3"
        assert task.status == TaskStatus.COMPLETED
        assert task.output == {"result": "done", "count": 42}

    def test_create_failed_task(self) -> None:
        """Test creating a failed task with error."""
        task = Task(
            id="task_4",
            type=TaskType.CRON,
            status=TaskStatus.FAILED,
            input={"cron_expr": "0 * * * *"},
            error="Timeout exceeded",
        )
        assert task.id == "task_4"
        assert task.status == TaskStatus.FAILED
        assert task.error == "Timeout exceeded"

    def test_create_cancelled_task(self) -> None:
        """Test creating a cancelled task."""
        task = Task(
            id="task_5",
            type=TaskType.USER_REQUEST,
            status=TaskStatus.CANCELLED,
            input={"command": "cancel me"},
        )
        assert task.id == "task_5"
        assert task.status == TaskStatus.CANCELLED

    def test_to_dict_basic(self) -> None:
        """Test converting basic task to dict."""
        task = Task(
            id="task_1",
            type=TaskType.USER_REQUEST,
            input={"prompt": "Hello"},
        )
        result = task.to_dict()
        assert result["id"] == "task_1"
        assert result["type"] == "user_request"
        assert result["status"] == "pending"
        assert result["input"] == {"prompt": "Hello"}
        assert result["output"] is None
        assert result["error"] is None
        assert result["created_at"] > 0
        assert result["updated_at"] > 0
        assert result["metadata"] == {}

    def test_to_dict_with_enums(self) -> None:
        """Test that to_dict serializes enums as strings."""
        task = Task(
            id="task_1",
            type=TaskType.SUB_AGENT,
            status=TaskStatus.FAILED,
        )
        result = task.to_dict()
        assert result["type"] == "sub_agent"
        assert result["status"] == "failed"

    def test_to_dict_full(self) -> None:
        """Test converting full task to dict."""
        task = Task(
            id="task_1",
            type=TaskType.BACKGROUND,
            status=TaskStatus.COMPLETED,
            input={"task": "backup"},
            output={"files_backed_up": 100},
            error=None,
            created_at=1000,
            updated_at=3000,
            metadata={"author": "system"},
        )
        result = task.to_dict()
        assert result == {
            "id": "task_1",
            "type": "background",
            "status": "completed",
            "input": {"task": "backup"},
            "output": {"files_backed_up": 100},
            "error": None,
            "created_at": 1000,
            "updated_at": 3000,
            "metadata": {"author": "system"},
        }

    def test_from_dict_basic(self) -> None:
        """Test creating task from basic dict."""
        data = {
            "id": "task_1",
            "type": "user_request",
            "status": "pending",
        }
        task = Task.from_dict(data)
        assert task.id == "task_1"
        assert task.type == TaskType.USER_REQUEST
        assert task.status == TaskStatus.PENDING

    def test_from_dict_with_input(self) -> None:
        """Test creating task from dict with input."""
        data = {
            "id": "task_1",
            "type": "sub_agent",
            "input": {"prompt": "Analyze this"},
        }
        task = Task.from_dict(data)
        assert task.input == {"prompt": "Analyze this"}

    def test_from_dict_with_all_fields(self) -> None:
        """Test creating task from dict with all fields."""
        data = {
            "id": "task_1",
            "type": "background",
            "status": "running",
            "input": {"task": "cleanup"},
            "output": None,
            "error": None,
            "created_at": 1000,
            "updated_at": 2000,
            "metadata": {"key": "value"},
        }
        task = Task.from_dict(data)
        assert task.id == "task_1"
        assert task.type == TaskType.BACKGROUND
        assert task.status == TaskStatus.RUNNING
        assert task.input == {"task": "cleanup"}
        assert task.output is None
        assert task.metadata == {"key": "value"}

    def test_from_dict_minimal(self) -> None:
        """Test creating task from dict with minimal data."""
        data = {"id": "task_1"}
        task = Task.from_dict(data)
        assert task.id == "task_1"
        assert task.type == TaskType.USER_REQUEST  # default
        assert task.status == TaskStatus.PENDING  # default

    def test_from_dict_role_as_enum(self) -> None:
        """Test creating task from dict with type/status already as enums."""
        data = {
            "id": "task_1",
            "type": TaskType.CRON,
            "status": TaskStatus.FAILED,
        }
        task = Task.from_dict(data)
        assert task.type == TaskType.CRON
        assert task.status == TaskStatus.FAILED

    def test_from_dict_all_task_types(self) -> None:
        """Test creating tasks from dict with all task types."""
        for type_str in ["user_request", "sub_agent", "background", "cron"]:
            data = {"id": "task_1", "type": type_str}
            task = Task.from_dict(data)
            assert task.type.value == type_str

    def test_from_dict_all_task_statuses(self) -> None:
        """Test creating tasks from dict with all task statuses."""
        for status_str in ["pending", "running", "completed", "failed", "cancelled"]:
            data = {"id": "task_1", "status": status_str}
            task = Task.from_dict(data)
            assert task.status.value == status_str

    def test_roundtrip_basic(self) -> None:
        """Test roundtrip serialization for basic task."""
        original = Task(
            id="task_1",
            type=TaskType.USER_REQUEST,
            input={"prompt": "Say hello"},
        )
        restored = Task.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.status == original.status
        assert restored.input == original.input

    def test_roundtrip_full(self) -> None:
        """Test roundtrip serialization for full task."""
        original = Task(
            id="task_1",
            type=TaskType.SUB_AGENT,
            status=TaskStatus.COMPLETED,
            input={"prompt": "Process data"},
            output={"processed": 1000, "skipped": 5},
            error=None,
            created_at=1000,
            updated_at=3000,
            metadata={"priority": "high", "tags": ["analytics"]},
        )
        restored = Task.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.status == original.status
        assert restored.input == original.input
        assert restored.output == original.output
        assert restored.error == original.error
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at
        assert restored.metadata == original.metadata

    def test_roundtrip_failed_task(self) -> None:
        """Test roundtrip serialization for failed task."""
        original = Task(
            id="task_2",
            type=TaskType.CRON,
            status=TaskStatus.FAILED,
            input={"cron_expr": "0 0 * * *"},
            output=None,
            error="Command not found",
            created_at=500,
            updated_at=1500,
            metadata={"retry_count": 3},
        )
        restored = Task.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.status == original.status
        assert restored.output == original.output
        assert restored.error == original.error
        assert restored.metadata == original.metadata
