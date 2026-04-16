# Orchestrator API

## Overview

The Orchestrator module coordinates task execution across workers and manages session complexity routing.

## Orchestrator

### Methods

#### `execute_task(task: str, session_id: str) -> TaskResult`

Executes a task within a session.

**Parameters:**
- `task` (str): Task description
- `session_id` (str): Session identifier

**Returns:**
- `TaskResult`: Task execution result

#### `route_to_worker(task: str, complexity: int) -> WorkerType`

Routes task to appropriate worker based on complexity.

**Parameters:**
- `task` (str): Task description
- `complexity` (int): Task complexity score (0-100)

**Returns:**
- `WorkerType`: The worker type to handle the task

## Complexity Levels

| Level | Score Range | Worker |
|-------|-------------|--------|
| SIMPLE | 0-40 | Explorer |
| MEDIUM | 41-70 | Planner |
| COMPLEX | 71-100 | Coder |

## Workers

### ExplorerWorker

Handles simple, exploratory tasks.

### PlannerWorker

Handles medium complexity planning tasks.

### CoderWorker

Handles complex coding tasks.

## Quality Assurance

### QualityChecker

Performs code quality checks.

### Methods

#### `check_syntax(code: str, language: str) -> QualityResult`

Checks code syntax.

#### `check_style(code: str) -> QualityResult`

Checks code style.

#### `check_security(code: str) -> QualityResult`

Checks for security issues.

## Usage Example

```python
from mozi.orchestrator import Orchestrator

orchestrator = Orchestrator()
result = await orchestrator.execute_task(
    task="Implement a login feature",
    session_id="session-123"
)
```
