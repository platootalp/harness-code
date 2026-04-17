"""Tests for the planner worker."""

from __future__ import annotations

import pytest

from mozi.orchestrator.state import TodoItem, TodoStatus
from mozi.orchestrator.workers.planner import PlannerWorker


@pytest.fixture
def planner() -> PlannerWorker:
    """Create a PlannerWorker instance."""
    return PlannerWorker()


@pytest.fixture
def sample_todo() -> TodoItem:
    """Create a sample todo item."""
    return TodoItem(
        id="test-1",
        description="Plan test",
        status=TodoStatus.PENDING,
    )


class TestPlannerWorker:
    """Tests for PlannerWorker."""

    @pytest.mark.asyncio
    async def test_execute_unknown_action(
        self, planner: PlannerWorker, sample_todo: TodoItem
    ) -> None:
        """Test execute with unknown action."""
        result = await planner.execute(sample_todo, {"action": "unknown"})
        assert result["status"] == "unknown_action"

    @pytest.mark.asyncio
    async def test_generate_todo_list_quick(self, planner: PlannerWorker) -> None:
        """Test generating todo list for quick task."""
        result = await planner.generate_todo_list("Fix typo", category="quick")
        assert result["status"] == "success"
        assert result["category"] == "quick"
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_generate_todo_list_deep(self, planner: PlannerWorker) -> None:
        """Test generating todo list for deep task."""
        result = await planner.generate_todo_list("Build feature", category="deep")
        assert result["status"] == "success"
        assert result["category"] == "deep"
        assert result["count"] == 4

    @pytest.mark.asyncio
    async def test_generate_todo_list_strategic(self, planner: PlannerWorker) -> None:
        """Test generating todo list for strategic task."""
        result = await planner.generate_todo_list("Design system", category="strategic")
        assert result["status"] == "success"
        assert result["category"] == "strategic"
        assert result["count"] == 6

    @pytest.mark.asyncio
    async def test_generate_todo_list_with_constraints(self, planner: PlannerWorker) -> None:
        """Test generating todo list with constraints."""
        result = await planner.generate_todo_list(
            "Build feature",
            category="quick",
            constraints={"session_id": "custom-session"},
        )
        assert result["status"] == "success"
        todos = result["todos"]
        assert all("custom-session" in t["id"] for t in todos)

    @pytest.mark.asyncio
    async def test_decompose_task_depth_0(self, planner: PlannerWorker) -> None:
        """Test decomposing task with depth 0."""
        result = await planner.decompose_task("Test task", depth=0)
        assert result["status"] == "success"
        assert result["depth"] == 0
        assert result["subtasks"] == []

    @pytest.mark.asyncio
    async def test_decompose_task_depth_1(self, planner: PlannerWorker) -> None:
        """Test decomposing task with depth 1."""
        result = await planner.decompose_task("Test task", depth=1)
        assert result["status"] == "success"
        assert result["subtasks"] == []

    @pytest.mark.asyncio
    async def test_decompose_task_depth_2(self, planner: PlannerWorker) -> None:
        """Test decomposing task with depth 2."""
        result = await planner.decompose_task("Test task", depth=2)
        assert result["status"] == "success"
        assert len(result["subtasks"]) >= 2

    @pytest.mark.asyncio
    async def test_prioritize_todos(self, planner: PlannerWorker) -> None:
        """Test prioritizing todos."""
        todos = [
            {"id": "1", "description": "Low priority", "priority": 1},
            {"id": "2", "description": "High priority", "priority": 5},
            {"id": "3", "description": "Medium priority", "priority": 3},
        ]
        result = await planner.prioritize_todos(todos)
        assert result["status"] == "success"
        prioritized = result["todos"]
        assert prioritized[0]["priority"] == 5
        assert prioritized[2]["priority"] == 1

    @pytest.mark.asyncio
    async def test_get_generated_todos(self, planner: PlannerWorker) -> None:
        """Test getting generated todos."""
        await planner.generate_todo_list("Test task", category="quick")
        todos = planner.get_generated_todos()
        assert len(todos) == 1
        assert todos[0].description == "Test task"
