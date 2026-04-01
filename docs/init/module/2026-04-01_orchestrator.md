# Orchestrator 模块结构文档

> 版本: 1.0.0
> 更新日期: 2026-04-01
> 状态: 已完成

## 1. 概述

Orchestrator 是 Mozi 架构的核心编排层，负责接收用户任务、分析复杂度、路由到合适的处理策略，并协调多个 Worker 完成复杂任务。

### 1.1 核心职责

- **任务路由**: 根据任务复杂度将任务分类为 QUICK / DEEP / STRATEGIC
- **状态管理**: 维护任务的完整生命周期状态
- **质量把控**: 对代码进行语法、风格、复杂度、安全检查
- **代码审查**: 检测代码中的危险模式和潜在问题
- **Worker 协调**: 调度 CoderWorker、ExplorerWorker、PlannerWorker 执行具体任务

---

## 2. 目录结构

```
mozi/orchestrator/
├── __init__.py           # 模块公共 API 导出
├── orchestrator.py       # 主 Orchestrator 类
├── category.py          # 任务分类与复杂度分析
├── quality.py            # 质量检查
├── reviewer.py           # 代码审查
├── state.py              # 状态管理
├── integration.py        # 与其他 Mozi 模块集成
├── core/                 # 核心组件（预留）
└── workers/             # 专业 Worker
    ├── __init__.py
    ├── coder.py          # 代码编辑
    ├── explorer.py       # 代码库探索
    └── planner.py        # 任务规划
```

---

## 3. 组件详解

### 3.1 Orchestrator（主编排器）

**文件**: `orchestrator.py`

主协调器，管理任务执行的完整生命周期。

**核心方法**:

| 方法 | 说明 |
|------|------|
| `execute(task_description, context)` | 主入口，执行任务 |
| `_execute_quick()` | 快速路径：简单任务直接执行 |
| `_execute_deep()` | 深度路径：中等复杂度任务多步骤执行 |
| `_execute_strategic()` | 战略路径：复杂任务需要规划 |
| `_check_quality()` | 质量检查 |
| `review()` | 代码审查 |
| `get_state()` | 获取任务状态 |

**执行流程**:

```
execute()
  └── CategoryRouter.route() → Category
        ├── QUICK → _execute_quick()
        │            └── CoderWorker.execute()
        ├── DEEP → _execute_deep()
        │            └── PlannerWorker.generate_todo_list()
        │            └── 循环执行: ExplorerWorker / PlannerWorker / CoderWorker
        └── STRATEGIC → _execute_strategic()
                         └── ExplorerWorker (research)
                         └── PlannerWorker (generate todos)
                         └── 循环 + QualityChecker
```

### 3.2 CategoryRouter（任务分类器）

**文件**: `category.py`

根据任务描述和上下文计算复杂度，决定处理策略。

**复杂度阈值**:

| 类别 | 分数范围 | 处理策略 |
|------|----------|----------|
| QUICK | ≤ 40 | 简单任务，直接执行 |
| DEEP | 40-70 | 中等复杂度，多步骤执行 |
| STRATEGIC | > 70 | 复杂任务，需要规划研究 |

**复杂度评分因素**:

| 因素 | 加分 |
|------|------|
| 描述长度 > 500 字符 | +20 |
| 描述长度 > 200 字符 | +10 |
| `requires_planning` 上下文 | +25 |
| `multi_step` 上下文 | +20 |
| `file_operations` 上下文 | +10 |
| `code_review` 上下文 | +15 |
| `testing` 上下文 | +10 |

### 3.3 QualityChecker（质量检查器）

**文件**: `quality.py`

对代码进行多维度质量检查。

**检查类型**:

| 检查类型 | 说明 |
|----------|------|
| SYNTAX | 语法检查 |
| STYLE | 风格检查（行长度、函数长度） |
| COMPLEXITY | 圈复杂度检查 |
| COVERAGE | 测试覆盖率检查 |
| SECURITY | 安全扫描 |
| DOCUMENTATION | 文档检查 |

**安全模式检测**:

- `eval()`, `exec()`, `__import__()`
- `pickle.loads()`
- `shutil.rmtree()`
- `os.system()`
- `shell=True`
- 硬编码密码、API 密钥

**默认阈值**:

```python
{
    "complexity": 15.0,
    "coverage": 80.0,
    "max_line_length": 100,
    "max_function_length": 50,
}
```

### 3.4 Reviewer（代码审查器）

**文件**: `reviewer.py`

对代码变更进行审查，检测危险模式。

**审查状态**: PENDING → IN_PROGRESS → APPROVED / CHANGES_REQUESTED / REJECTED

**危险模式检测**:

- `eval()`, `exec()`, 通配符导入
- `print()` 语句
- TODO/FIXME 注释
- 裸 except 子句

### 3.5 StateStore（状态存储）

**文件**: `state.py`

管理 OrchestratorState 的持久化。

**存储位置**: `~/.mozi/state/{session_id}.json`

**核心数据结构**:

```python
@dataclass
class OrchestratorState:
    session_id: str
    task_description: str
    category: str          # "quick" | "deep" | "strategic"
    todos: list[TodoItem]
    decisions: list[Decision]
    context_snapshot: dict
    created_at: datetime
    updated_at: datetime
    metadata: dict

@dataclass
class TodoItem:
    id: str
    description: str
    status: TodoStatus     # PENDING | IN_PROGRESS | COMPLETED | FAILED | BLOCKED
    priority: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    worker: str | None     # "coder" | "explorer" | "planner"
    result: dict | None
    error: str | None

@dataclass
class Decision:
    id: str
    decision_type: DecisionType
    reasoning: str
    alternatives: list[str]
    chosen: str
    timestamp: datetime
    context: dict | None
```

---

## 4. Worker 组件

### 4.1 CoderWorker

**文件**: `workers/coder.py`

负责代码编辑操作。

| 方法 | 说明 |
|------|------|
| `execute(todo, context)` | 执行代码编辑任务 |
| `apply_diff(file_path, diff, dry_run)` | 应用 diff |
| `validate_change(file_path, change)` | 验证变更 |
| `create_file(file_path, content)` | 创建文件 |

### 4.2 ExplorerWorker

**文件**: `workers/explorer.py`

负责代码库探索和信息收集。

| 方法 | 说明 |
|------|------|
| `execute(todo, context)` | 执行探索任务 |
| `search_codebase(query, path, file_patterns)` | 搜索代码库 |
| `get_file_info(file_path)` | 获取文件信息 |
| `explore_structure(path, max_depth)` | 探索目录结构 |

### 4.3 PlannerWorker

**文件**: `workers/planner.py`

负责任务规划和分解。

| 方法 | 说明 |
|------|------|
| `execute(todo, context)` | 执行规划任务 |
| `generate_todo_list(task, category, constraints)` | 生成待办列表 |
| `decompose_task(task, depth)` | 分解任务 |
| `prioritize_todos(todos)` | 排序待办 |

**按类别生成的 Todo 模板**:

*DEEP (4 步)*:
1. Analyze: {task}
2. Plan: {task}
3. Implement: {task}
4. Verify: {task}

*STRATEGIC (6 步)*:
1. Research: {task}
2. Design: {task}
3. Prototype: {task}
4. Implement: {task}
5. Test: {task}
6. Review: {task}

---

## 5. 集成层

### 5.1 OrchestratorIntegration

**文件**: `integration.py`

连接 Orchestrator 与其他 Mozi 模块。

**依赖模块**:

- SessionManager - 会话管理
- ContextBuilder - 上下文构建
- MemoryRetriever - 记忆检索
- ModelService - 模型服务
- BaseEventBus - 事件总线

**发布事件**:

| 事件 | 说明 |
|------|------|
| `orchestrator.task_started` | 任务开始 |
| `orchestrator.task_completed` | 任务完成 |
| `orchestrator.task_failed` | 任务失败 |
| `orchestrator.state_changed` | 状态变更 |
| `orchestrator.worker_started` | Worker 开始 |
| `orchestrator.worker_completed` | Worker 完成 |
| `orchestrator.context_built` | 上下文构建 |
| `orchestrator.memory_retrieved` | 记忆检索 |

---

## 6. 公共 API

```python
# Category
from mozi.orchestrator import Category, CategoryRouter, ComplexityScore

# State
from mozi.orchestrator import (
    Decision, DecisionType, OrchestratorState,
    StateStore, TodoItem, TodoStatus
)

# Workers
from mozi.orchestrator import CoderWorker, ExplorerWorker, PlannerWorker

# Quality
from mozi.orchestrator import (
    CheckType, QualityChecker, QualityIssue,
    QualityLevel, QualityResult
)

# Reviewer
from mozi.orchestrator import (
    ReviewComment, ReviewCommentType, ReviewResult,
    ReviewStatus, Reviewer
)

# Main
from mozi.orchestrator import Orchestrator, OrchestratorError
```

---

## 7. 异常层次

```
MoziError
└── OrchestratorError
    ├── TaskRoutingError    # 任务路由失败
    └── WorkerExecutionError # Worker 执行失败
```

---

## 8. 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-04-01 | 初始文档 |
