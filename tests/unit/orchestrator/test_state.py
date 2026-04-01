"""Tests for the state module."""

from __future__ import annotations

import tempfile

import pytest

from mozi.orchestrator.state import (
    Decision,
    DecisionType,
    OrchestratorState,
    StateStore,
    TodoItem,
    TodoStatus,
)


class TestTodoStatus:
    """Tests for TodoStatus enum."""

    def test_status_values(self) -> None:
        """Test TodoStatus values."""
        assert TodoStatus.PENDING.value == "pending"
        assert TodoStatus.IN_PROGRESS.value == "in_progress"
        assert TodoStatus.COMPLETED.value == "completed"
        assert TodoStatus.FAILED.value == "failed"
        assert TodoStatus.BLOCKED.value == "blocked"


class TestTodoItem:
    """Tests for TodoItem dataclass."""

    def test_create_with_defaults(self) -> None:
        """Test creating TodoItem with defaults."""
        todo = TodoItem(id="1", description="Test task")
        assert todo.id == "1"
        assert todo.description == "Test task"
        assert todo.status == TodoStatus.PENDING
        assert todo.priority == 3
        assert todo.worker is None
        assert todo.result is None
        assert todo.error is None

    def test_create_with_all_fields(self) -> None:
        """Test creating TodoItem with all fields."""
        todo = TodoItem(
            id="1",
            description="Test task",
            status=TodoStatus.IN_PROGRESS,
            priority=5,
            worker="coder",
        )
        assert todo.status == TodoStatus.IN_PROGRESS
        assert todo.priority == 5
        assert todo.worker == "coder"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        todo = TodoItem(id="1", description="Test", priority=4)
        result = todo.to_dict()
        assert result["id"] == "1"
        assert result["description"] == "Test"
        assert result["priority"] == 4
        assert result["status"] == "pending"

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "id": "1",
            "description": "Test",
            "status": "in_progress",
            "priority": 5,
        }
        todo = TodoItem.from_dict(data)
        assert todo.id == "1"
        assert todo.status == TodoStatus.IN_PROGRESS
        assert todo.priority == 5


class TestDecisionType:
    """Tests for DecisionType enum."""

    def test_type_values(self) -> None:
        """Test DecisionType values."""
        assert DecisionType.TASK_APPROACH.value == "task_approach"
        assert DecisionType.RESOURCE_ALLOCATION.value == "resource_allocation"
        assert DecisionType.STRATEGY_CHANGE.value == "strategy_change"


class TestDecision:
    """Tests for Decision dataclass."""

    def test_create_decision(self) -> None:
        """Test creating a Decision."""
        decision = Decision(
            id="1",
            decision_type=DecisionType.TASK_APPROACH,
            reasoning="This is the best approach",
            alternatives=["Option A", "Option B"],
            chosen="Option A",
        )
        assert decision.id == "1"
        assert decision.decision_type == DecisionType.TASK_APPROACH
        assert decision.chosen == "Option A"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        decision = Decision(
            id="1",
            decision_type=DecisionType.STRATEGY_CHANGE,
            reasoning="Change needed",
            alternatives=["A", "B"],
            chosen="A",
        )
        result = decision.to_dict()
        assert result["id"] == "1"
        assert result["decision_type"] == "strategy_change"
        assert result["chosen"] == "A"


class TestOrchestratorState:
    """Tests for OrchestratorState dataclass."""

    def test_create_state(self) -> None:
        """Test creating OrchestratorState."""
        state = OrchestratorState(
            session_id="session-1",
            task_description="Build feature",
        )
        assert state.session_id == "session-1"
        assert state.task_description == "Build feature"
        assert state.category == "quick"
        assert state.todos == []
        assert state.decisions == []

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        state = OrchestratorState(
            session_id="session-1",
            task_description="Build feature",
            category="deep",
        )
        result = state.to_dict()
        assert result["session_id"] == "session-1"
        assert result["category"] == "deep"
        assert "todos" in result
        assert "decisions" in result

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "session_id": "session-1",
            "task_description": "Build feature",
            "category": "strategic",
            "todos": [],
            "decisions": [],
        }
        state = OrchestratorState.from_dict(data)
        assert state.session_id == "session-1"
        assert state.category == "strategic"


class TestStateStore:
    """Tests for StateStore."""

    def test_save_and_load_state(self) -> None:
        """Test saving and loading state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(tmpdir)
            state = OrchestratorState(
                session_id="test-session",
                task_description="Test task",
            )
            store.save_state(state)

            loaded = store.load_state("test-session")
            assert loaded.session_id == "test-session"
            assert loaded.task_description == "Test task"

    def test_load_nonexistent_raises(self) -> None:
        """Test loading nonexistent session raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(tmpdir)
            with pytest.raises(FileNotFoundError):
                store.load_state("nonexistent")

    def test_update_todo(self) -> None:
        """Test updating a todo item."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(tmpdir)
            state = OrchestratorState(
                session_id="test-session",
                task_description="Test",
            )
            todo = TodoItem(id="todo-1", description="Test todo")
            state.todos.append(todo)
            store.save_state(state)

            updated = store.update_todo(
                "test-session",
                "todo-1",
                TodoStatus.COMPLETED,
                result={"output": "done"},
            )
            assert updated.status == TodoStatus.COMPLETED
            assert updated.result == {"output": "done"}

    def test_complete_todo(self) -> None:
        """Test completing a todo item."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(tmpdir)
            state = OrchestratorState(
                session_id="test-session",
                task_description="Test",
            )
            todo = TodoItem(id="todo-1", description="Test todo")
            state.todos.append(todo)
            store.save_state(state)

            completed = store.complete_todo("test-session", "todo-1", {"done": True})
            assert completed.status == TodoStatus.COMPLETED
            assert completed.completed_at is not None

    def test_delete_state(self) -> None:
        """Test deleting a state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = StateStore(tmpdir)
            state = OrchestratorState(session_id="test-session", task_description="Test")
            store.save_state(state)

            store.delete_state("test-session")

            with pytest.raises(FileNotFoundError):
                store.load_state("test-session")
