"""Main orchestrator for Mozi.

Coordinates task execution across different workers based on
task category and complexity.
"""

from __future__ import annotations

import uuid
from typing import Any

from mozi.orchestrator.category import Category, CategoryRouter
from mozi.orchestrator.quality import QualityChecker, QualityLevel, QualityResult
from mozi.orchestrator.reviewer import Reviewer, ReviewResult
from mozi.orchestrator.state import (
    Decision,
    DecisionType,
    OrchestratorState,
    StateStore,
    TodoItem,
    TodoStatus,
)
from mozi.orchestrator.workers.coder import CoderWorker
from mozi.orchestrator.workers.explorer import ExplorerWorker
from mozi.orchestrator.workers.planner import PlannerWorker


class Orchestrator:
    """Main orchestrator for task execution.

    Coordinates the execution of tasks by:
    1. Categorizing the task based on complexity
    2. Planning the execution strategy
    3. Routing to appropriate workers
    4. Managing state throughout execution
    5. Performing quality checks
    6. Reviewing and approving results
    """

    def __init__(
        self,
        storage_path: str | None = None,
        quality_threshold: float = 80.0,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            storage_path: Optional path for state storage.
            quality_threshold: Minimum quality score for approval.
        """
        self._state_store = StateStore(storage_path)
        self._category_router = CategoryRouter()
        self._quality_checker = QualityChecker()
        self._reviewer = Reviewer()

        self._explorer = ExplorerWorker()
        self._planner = PlannerWorker()
        self._coder = CoderWorker()

        self._quality_threshold = quality_threshold
        self._current_state: OrchestratorState | None = None

    async def execute(
        self,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a task from start to finish.

        Args:
            task_description: Description of the task to execute.
            context: Optional execution context.

        Returns:
            Execution result with status and outputs.
        """
        context = context or {}
        session_id = context.get("session_id", str(uuid.uuid4()))

        state = OrchestratorState(
            session_id=session_id,
            task_description=task_description,
        )
        self._current_state = state
        self._state_store.save_state(state)

        category = self._category_router.route(task_description, context)
        state.category = category.value

        self._save_decision(
            session_id,
            DecisionType.TASK_APPROACH,
            f"Categorized task as {category.value}",
            ["quick", "deep", "strategic"],
            category.value,
        )

        if category == Category.QUICK:
            return await self._execute_quick(session_id, task_description, context)
        elif category == Category.DEEP:
            return await self._execute_deep(session_id, task_description, context)
        else:
            return await self._execute_strategic(session_id, task_description, context)

    async def _execute_quick(
        self,
        session_id: str,
        task_description: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a quick task.

        Args:
            session_id: Session identifier.
            task_description: Task description.
            context: Execution context.

        Returns:
            Execution result.
        """
        todo = TodoItem(
            id=f"{session_id}-1",
            description=task_description,
            priority=3,
            status=TodoStatus.IN_PROGRESS,
            worker="coder",
        )
        self._state_store.add_todo(session_id, todo)

        file_path = context.get("file_path")
        result: dict[str, Any] = {}
        if file_path:
            result = await self._coder.execute(todo, context)
            if result.get("status") == "success":
                self._state_store.complete_todo(session_id, todo.id, result)
                status = "completed"
            else:
                self._state_store.update_todo(
                    session_id, todo.id, TodoStatus.FAILED, error=str(result)
                )
                status = "failed"
        else:
            result = {"message": "Quick task completed"}
            self._state_store.complete_todo(session_id, todo.id, result)
            status = "completed"

        return {
            "status": status,
            "session_id": session_id,
            "category": "quick",
            "result": result,
        }

    async def _execute_deep(
        self,
        session_id: str,
        task_description: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a deep (multi-step) task.

        Args:
            session_id: Session identifier.
            task_description: Task description.
            context: Execution context.

        Returns:
            Execution result.
        """
        plan_result = await self._planner.generate_todo_list(
            task_description,
            category="deep",
            constraints={"session_id": session_id},
        )
        todos_data = plan_result.get("todos", [])

        todos: list[TodoItem] = []
        for t_data in todos_data:
            todo = TodoItem(
                id=t_data["id"],
                description=t_data["description"],
                priority=t_data.get("priority", 3),
                worker=t_data.get("worker"),
            )
            self._state_store.add_todo(session_id, todo)
            todos.append(todo)

        results: list[dict[str, Any]] = []
        for todo in todos:
            todo.status = TodoStatus.IN_PROGRESS
            if self._current_state is not None:
                self._current_state.todos.append(todo)
                self._state_store.save_state(self._current_state)

            if "analyze" in todo.description.lower():
                result = await self._explorer.execute(todo, context)
            elif "plan" in todo.description.lower():
                result = await self._planner.execute(todo, context)
            else:
                result = await self._coder.execute(todo, context)

            if result.get("status") == "success":
                self._state_store.complete_todo(session_id, todo.id, result)
            else:
                self._state_store.update_todo(
                    session_id, todo.id, TodoStatus.FAILED, error=str(result)
                )

            results.append({"todo_id": todo.id, "result": result})

        return {
            "status": "completed",
            "session_id": session_id,
            "category": "deep",
            "results": results,
        }

    async def _execute_strategic(
        self,
        session_id: str,
        task_description: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a strategic (high-impact) task.

        Args:
            session_id: Session identifier.
            task_description: Task description.
            context: Execution context.

        Returns:
            Execution result.
        """
        research_todo = TodoItem(
            id=f"{session_id}-research",
            description=f"Research: {task_description}",
            priority=5,
            worker="explorer",
        )
        self._state_store.add_todo(session_id, research_todo)

        research_result = await self._explorer.execute(
            research_todo,
            {"action": "explore_structure", "path": context.get("path", ".")},
        )

        if research_result.get("status") == "success":
            self._state_store.complete_todo(session_id, research_todo.id, research_result)
        else:
            self._state_store.update_todo(
                session_id,
                research_todo.id,
                TodoStatus.FAILED,
                error=str(research_result),
            )
            return {
                "status": "failed",
                "session_id": session_id,
                "category": "strategic",
                "result": research_result,
            }

        plan_result = await self._planner.generate_todo_list(
            task_description,
            category="strategic",
            constraints={"session_id": session_id},
        )

        todos_data = plan_result.get("todos", [])
        results: list[dict[str, Any]] = []
        todos: list[TodoItem] = []

        for t_data in todos_data:
            todo = TodoItem(
                id=t_data["id"],
                description=t_data["description"],
                priority=t_data.get("priority", 3),
                worker=t_data.get("worker"),
            )
            self._state_store.add_todo(session_id, todo)
            todos.append(todo)

        for todo in todos:
            todo.status = TodoStatus.IN_PROGRESS
            if self._current_state is not None:
                self._current_state.todos.append(todo)
                self._state_store.save_state(self._current_state)

            if "research" in todo.description.lower():
                result = await self._explorer.execute(todo, context)
            elif "design" in todo.description.lower() or "plan" in todo.description.lower():
                result = await self._planner.execute(todo, context)
            else:
                result = await self._coder.execute(todo, context)

            if result.get("status") == "success":
                self._state_store.complete_todo(session_id, todo.id, result)
            else:
                self._state_store.update_todo(
                    session_id, todo.id, TodoStatus.FAILED, error=str(result)
                )

            results.append({"todo_id": todo.id, "result": result})

            quality_result = await self._check_quality(result)
            if not quality_result.is_acceptable:
                self._state_store.update_todo(
                    session_id,
                    todo.id,
                    TodoStatus.BLOCKED,
                    error=f"Quality check failed: {quality_result.score}",
                )

        return {
            "status": "completed",
            "session_id": session_id,
            "category": "strategic",
            "results": results,
        }

    async def _check_quality(self, content: Any) -> QualityResult:
        """Check quality of content.

        Args:
            content: Content to check.

        Returns:
            Quality check result.
        """
        if isinstance(content, str):
            return await self._quality_checker.check(content)
        elif isinstance(content, dict):
            content_str = str(content)
            return await self._quality_checker.check(content_str)
        else:
            return QualityResult(
                level=QualityLevel.ACCEPTABLE,
                score=50.0,
                issues=[],
            )

    def _save_decision(
        self,
        session_id: str,
        decision_type: DecisionType,
        reasoning: str,
        alternatives: list[str],
        chosen: str,
    ) -> None:
        """Save a decision to state.

        Args:
            session_id: Session identifier.
            decision_type: Type of decision.
            reasoning: Why this decision was made.
            alternatives: Options considered.
            chosen: Chosen option.
        """
        decision = Decision(
            id=str(uuid.uuid4()),
            decision_type=decision_type,
            reasoning=reasoning,
            alternatives=alternatives,
            chosen=chosen,
        )
        try:
            self._state_store.add_decision(session_id, decision)
        except FileNotFoundError:
            pass

    async def review(
        self,
        session_id: str,
        diff: str,
    ) -> ReviewResult:
        """Review changes for a session.

        Args:
            session_id: Session to review.
            diff: Diff to review.

        Returns:
            Review result.
        """
        return await self._reviewer.review(diff, {"session_id": session_id})

    async def get_state(self, session_id: str) -> OrchestratorState:
        """Get the state for a session.

        Args:
            session_id: Session identifier.

        Returns:
            The session state.
        """
        return self._state_store.load_state(session_id)

    def get_current_state(self) -> OrchestratorState | None:
        """Get the current orchestrator state."""
        return self._current_state
