"""Planner worker for Mozi orchestrator.

Responsible for task planning, todo list generation,
and task decomposition for complex tasks.
"""

from __future__ import annotations

import uuid
from typing import Any

from mozi.orchestrator.state import TodoItem, TodoStatus


class PlannerWorker:
    """Worker that plans and decomposes tasks.

    Responsible for:
    - Generating todo lists from task descriptions
    - Decomposing complex tasks into smaller steps
    - Prioritizing tasks based on dependencies
    """

    def __init__(self) -> None:
        """Initialize the planner worker."""
        self._generated_todos: list[TodoItem] = []

    async def execute(
        self,
        todo: TodoItem,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute the planner task.

        Args:
            todo: The todo item to process.
            context: Optional context information.

        Returns:
            Execution result with generated todos or plan.
        """
        context = context or {}
        action = context.get("action", "generate_todo_list")

        if action == "generate_todo_list":
            return await self.generate_todo_list(
                context.get("task_description", ""),
                context.get("category", "quick"),
                context.get("constraints", {}),
            )
        elif action == "decompose_task":
            return await self.decompose_task(
                context.get("task", ""),
                context.get("depth", 2),
            )
        elif action == "prioritize":
            return await self.prioritize_todos(
                context.get("todos", []),
            )
        else:
            return {"status": "unknown_action", "action": action}

    async def generate_todo_list(
        self,
        task_description: str,
        category: str = "quick",
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a todo list from task description.

        Args:
            task_description: Description of the task.
            category: Task category (quick/deep/strategic).
            constraints: Optional constraints for the task.

        Returns:
            Generated todo list with subtasks.
        """
        constraints = constraints or {}
        todos: list[dict[str, Any]] = []
        session_id = constraints.get("session_id", str(uuid.uuid4()))

        if category == "quick":
            todos = [
                {
                    "id": f"{session_id}-1",
                    "description": task_description,
                    "priority": 3,
                    "status": "pending",
                }
            ]
        elif category == "deep":
            todos = self._generate_deep_todos(task_description, session_id)
        elif category == "strategic":
            todos = self._generate_strategic_todos(task_description, session_id)
        else:
            todos = [
                {
                    "id": f"{session_id}-1",
                    "description": task_description,
                    "priority": 3,
                    "status": "pending",
                }
            ]

        todo_items = [
            TodoItem(
                id=t["id"],
                description=t["description"],
                priority=t.get("priority", 3),
                status=TodoStatus.PENDING,
                worker=t.get("worker"),
            )
            for t in todos
        ]

        self._generated_todos = todo_items

        return {
            "status": "success",
            "category": category,
            "todos": [t.to_dict() for t in todo_items],
            "count": len(todo_items),
        }

    async def decompose_task(
        self,
        task: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Decompose a complex task into smaller subtasks.

        Args:
            task: The task to decompose.
            depth: Decomposition depth (how many levels deep).

        Returns:
            Decomposed task structure.
        """
        if depth <= 0:
            return {
                "status": "success",
                "task": task,
                "subtasks": [],
                "depth": 0,
            }

        subtasks = self._create_subtasks(task, depth)
        result: dict[str, Any] = {
            "status": "success",
            "task": task,
            "subtasks": subtasks,
            "depth": depth,
        }

        if depth > 1:
            for subtask in subtasks:
                if isinstance(subtask, dict) and "task" in subtask:
                    subtask["subtasks"] = self._create_subtasks(subtask["task"], depth - 1)

        return result

    async def prioritize_todos(
        self,
        todos: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Prioritize a list of todos based on dependencies and priority.

        Args:
            todos: List of todo items to prioritize.

        Returns:
            Prioritized todo list.
        """
        todo_items = []
        for t in todos:
            if isinstance(t, dict):
                todo_items.append(TodoItem.from_dict(t) if "id" in t else TodoItem(**t))
            else:
                todo_items.append(t)

        prioritized = sorted(
            todo_items,
            key=lambda t: (t.priority, t.created_at),
            reverse=True,
        )

        return {
            "status": "success",
            "todos": [t.to_dict() for t in prioritized],
            "count": len(prioritized),
        }

    def _generate_deep_todos(
        self,
        task_description: str,
        session_id: str,
    ) -> list[dict[str, Any]]:
        """Generate todos for a deep (multi-step) task."""
        base_priority = 3
        return [
            {
                "id": f"{session_id}-1",
                "description": f"Analyze: {task_description}",
                "priority": base_priority + 1,
                "status": "pending",
            },
            {
                "id": f"{session_id}-2",
                "description": f"Plan: {task_description}",
                "priority": base_priority,
                "status": "pending",
                "depends_on": [f"{session_id}-1"],
            },
            {
                "id": f"{session_id}-3",
                "description": f"Implement: {task_description}",
                "priority": base_priority,
                "status": "pending",
                "depends_on": [f"{session_id}-2"],
            },
            {
                "id": f"{session_id}-4",
                "description": f"Verify: {task_description}",
                "priority": base_priority - 1,
                "status": "pending",
                "depends_on": [f"{session_id}-3"],
            },
        ]

    def _generate_strategic_todos(
        self,
        task_description: str,
        session_id: str,
    ) -> list[dict[str, Any]]:
        """Generate todos for a strategic (high-impact) task."""
        base_priority = 4
        return [
            {
                "id": f"{session_id}-1",
                "description": f"Research: {task_description}",
                "priority": base_priority + 1,
                "status": "pending",
            },
            {
                "id": f"{session_id}-2",
                "description": f"Design: {task_description}",
                "priority": base_priority,
                "status": "pending",
                "depends_on": [f"{session_id}-1"],
            },
            {
                "id": f"{session_id}-3",
                "description": f"Prototype: {task_description}",
                "priority": base_priority,
                "status": "pending",
                "depends_on": [f"{session_id}-2"],
            },
            {
                "id": f"{session_id}-4",
                "description": f"Implement: {task_description}",
                "priority": base_priority - 1,
                "status": "pending",
                "depends_on": [f"{session_id}-3"],
            },
            {
                "id": f"{session_id}-5",
                "description": f"Test: {task_description}",
                "priority": base_priority - 1,
                "status": "pending",
                "depends_on": [f"{session_id}-4"],
            },
            {
                "id": f"{session_id}-6",
                "description": f"Review: {task_description}",
                "priority": base_priority - 2,
                "status": "pending",
                "depends_on": [f"{session_id}-5"],
            },
        ]

    def _create_subtasks(
        self,
        task: str,
        depth: int,
    ) -> list[dict[str, Any]]:
        """Create subtasks for a given task."""
        if depth <= 1:
            return []

        subtask_count = 3 if depth > 2 else 2

        subtasks = []
        prefixes = ["Analyze", "Design", "Implement", "Test", "Review", "Deploy"]

        for i in range(min(subtask_count, len(prefixes))):
            subtasks.append(
                {
                    "id": f"{uuid.uuid4().hex[:8]}",
                    "task": f"{prefixes[i]}: {task}",
                    "order": i + 1,
                }
            )

        return subtasks

    def get_generated_todos(self) -> list[TodoItem]:
        """Get todos generated in the last operation."""
        return self._generated_todos
