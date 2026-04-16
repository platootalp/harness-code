"""State management for Mozi orchestrator.

Provides data classes for task tracking, decision recording,
and state persistence for the orchestrator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class TodoStatus(Enum):
    """Status of a todo item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class DecisionType(Enum):
    """Type of decision made by orchestrator."""

    TASK_APPROACH = "task_approach"
    RESOURCE_ALLOCATION = "resource_allocation"
    STRATEGY_CHANGE = "strategy_change"
    TASK_DECOMPOSITION = "task_decomposition"
    QUALITY_THRESHOLD = "quality_threshold"


@dataclass
class TodoItem:
    """Represents a single task item in the todo list.

    Attributes:
        id: Unique identifier for the todo item.
        description: Description of the task.
        status: Current status of the task.
        priority: Priority level (1-5, higher is more important).
        created_at: When the todo was created.
        updated_at: When the todo was last updated.
        completed_at: When the todo was completed (if applicable).
        worker: Name of the worker assigned to this todo.
        result: Result of the task execution.
        error: Error message if task failed.
    """

    id: str
    description: str
    status: TodoStatus = TodoStatus.PENDING
    priority: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    worker: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "worker": self.worker,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TodoItem:
        """Create from dictionary."""
        data = data.copy()
        data["status"] = TodoStatus(data.get("status", "pending"))
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**data)


@dataclass
class Decision:
    """Represents a decision made by the orchestrator.

    Attributes:
        id: Unique identifier for the decision.
        decision_type: Type of decision.
        reasoning: Why this decision was made.
        alternatives: Alternative options considered.
        chosen: The chosen option.
        timestamp: When the decision was made.
    """

    id: str
    decision_type: DecisionType
    reasoning: str
    alternatives: list[str]
    chosen: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "decision_type": self.decision_type.value,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
            "chosen": self.chosen,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Decision:
        """Create from dictionary."""
        data = data.copy()
        data["decision_type"] = DecisionType(data.get("decision_type", "task_approach"))
        if data.get("timestamp"):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class OrchestratorState:
    """Represents the current state of the orchestrator.

    Attributes:
        session_id: Unique session identifier.
        task_description: Original task description.
        category: Task category (quick/deep/strategic).
        todos: List of todo items.
        decisions: List of decisions made.
        context_snapshot: Snapshot of context at this state.
        created_at: When the state was created.
        updated_at: When the state was last updated.
        metadata: Additional metadata.
    """

    session_id: str
    task_description: str
    category: str = "quick"
    todos: list[TodoItem] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    context_snapshot: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "task_description": self.task_description,
            "category": self.category,
            "todos": [t.to_dict() for t in self.todos],
            "decisions": [d.to_dict() for d in self.decisions],
            "context_snapshot": self.context_snapshot,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrchestratorState:
        """Create from dictionary."""
        data = data.copy()
        data["todos"] = [TodoItem.from_dict(t) for t in data.get("todos", [])]
        data["decisions"] = [Decision.from_dict(d) for d in data.get("decisions", [])]
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class StateStore:
    """Manages persistence of orchestrator state.

    Provides methods to save, load, and manage orchestrator state
    across sessions.
    """

    def __init__(self, storage_path: Path | str | None = None) -> None:
        """Initialize the state store.

        Args:
            storage_path: Path to store state files. Defaults to ~/.mozi/state/
        """
        if storage_path is None:
            home = Path.home()
            storage_path = home / ".mozi" / "state"
        self._storage_path = Path(storage_path)
        self._current_state: OrchestratorState | None = None

    def save_state(self, state: OrchestratorState) -> None:
        """Save orchestrator state to storage.

        Args:
            state: The state to save.
        """
        self._storage_path.mkdir(parents=True, exist_ok=True)
        state.updated_at = datetime.now(UTC)
        file_path = self._storage_path / f"{state.session_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
        self._current_state = state

    def load_state(self, session_id: str) -> OrchestratorState:
        """Load orchestrator state from storage.

        Args:
            session_id: The session ID to load.

        Returns:
            The loaded state.

        Raises:
            FileNotFoundError: If session state doesn't exist.
        """
        file_path = self._storage_path / f"{session_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"State for session {session_id} not found")
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        self._current_state = OrchestratorState.from_dict(data)
        return self._current_state

    def update_todo(
        self,
        session_id: str,
        todo_id: str,
        status: TodoStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> TodoItem:
        """Update a todo item's status.

        Args:
            session_id: The session ID.
            todo_id: The todo item ID.
            status: New status.
            result: Optional result data.
            error: Optional error message.

        Returns:
            The updated todo item.

        Raises:
            FileNotFoundError: If session or todo not found.
            ValueError: If todo_id not found in session.
        """
        state = self.load_state(session_id)
        todo = None
        for t in state.todos:
            if t.id == todo_id:
                todo = t
                break
        if todo is None:
            raise ValueError(f"Todo {todo_id} not found in session {session_id}")
        todo.status = status
        todo.updated_at = datetime.now(UTC)
        if result is not None:
            todo.result = result
        if error is not None:
            todo.error = error
        if status == TodoStatus.COMPLETED:
            todo.completed_at = datetime.now(UTC)
        self.save_state(state)
        return todo

    def complete_todo(
        self,
        session_id: str,
        todo_id: str,
        result: dict[str, Any] | None = None,
    ) -> TodoItem:
        """Mark a todo item as completed.

        Args:
            session_id: The session ID.
            todo_id: The todo item ID.
            result: Optional result data.

        Returns:
            The completed todo item.
        """
        return self.update_todo(session_id, todo_id, TodoStatus.COMPLETED, result=result)

    def add_todo(self, session_id: str, todo: TodoItem) -> TodoItem:
        """Add a new todo item to a session.

        Args:
            session_id: The session ID.
            todo: The todo item to add.

        Returns:
            The added todo item.
        """
        state = self.load_state(session_id)
        state.todos.append(todo)
        self.save_state(state)
        return todo

    def add_decision(self, session_id: str, decision: Decision) -> Decision:
        """Add a new decision to a session.

        Args:
            session_id: The session ID.
            decision: The decision to add.

        Returns:
            The added decision.
        """
        state = self.load_state(session_id)
        state.decisions.append(decision)
        self.save_state(state)
        return decision

    def get_current_state(self) -> OrchestratorState | None:
        """Get the current cached state."""
        return self._current_state

    def delete_state(self, session_id: str) -> None:
        """Delete a session state.

        Args:
            session_id: The session ID to delete.
        """
        file_path = self._storage_path / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()
        if self._current_state and self._current_state.session_id == session_id:
            self._current_state = None
