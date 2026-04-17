"""
Cron tasks management - in-memory storage for scheduled cron jobs.

Migrated from TypeScript cron tasks utilities.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# In-memory storage for cron tasks
_cron_tasks: dict[str, dict] = {}


@dataclass
class CronTask:
    """A scheduled cron task."""
    id: str
    prompt: str
    cron_expression: str
    created_at: int
    next_run_ms: int
    recurring: bool = True
    durable: bool = False
    metadata: dict = field(default_factory=dict)


def list_all_cron_tasks() -> list[dict]:
    """List all registered cron tasks.

    Returns:
        List of cron task dictionaries
    """
    return list(_cron_tasks.values())


def add_cron_task(
    prompt: str,
    cron_expression: str,
    recurring: bool = True,
    durable: bool = False,
    metadata: dict | None = None,
) -> str:
    """Add a new cron task.

    Args:
        prompt: The prompt to execute
        cron_expression: Cron schedule expression
        recurring: Whether this is a recurring task
        durable: Whether to persist across sessions
        metadata: Additional metadata

    Returns:
        Task ID
    """
    task_id = f"cron_{int(time.time() * 1000)}"
    now_ms = int(datetime.now(UTC).timestamp() * 1000)

    # Calculate next run
    from .cron import next_cron_run_ms
    next_run = next_cron_run_ms(cron_expression, now_ms) or (now_ms + 60_000)

    task = CronTask(
        id=task_id,
        prompt=prompt,
        cron_expression=cron_expression,
        created_at=now_ms,
        next_run_ms=next_run,
        recurring=recurring,
        durable=durable,
        metadata=metadata or {},
    )

    _cron_tasks[task_id] = {
        "id": task.id,
        "prompt": task.prompt,
        "cron_expression": task.cron_expression,
        "created_at": task.created_at,
        "next_run_ms": task.next_run_ms,
        "recurring": task.recurring,
        "durable": task.durable,
        "metadata": task.metadata,
    }

    return task_id


def remove_cron_tasks(task_ids: list[str]) -> list[str]:
    """Remove cron tasks by ID.

    Args:
        task_ids: List of task IDs to remove

    Returns:
        List of successfully removed task IDs
    """
    removed = []
    for task_id in task_ids:
        if task_id in _cron_tasks:
            del _cron_tasks[task_id]
            removed.append(task_id)
    return removed


def get_cron_task(task_id: str) -> dict | None:
    """Get a cron task by ID.

    Args:
        task_id: Task ID

    Returns:
        Task dict or None if not found
    """
    return _cron_tasks.get(task_id)
