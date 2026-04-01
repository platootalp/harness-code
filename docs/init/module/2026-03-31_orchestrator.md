# Orchestrator 编排层设计文档 v3.0

> **模板版本**: 3.0
> **创建日期**: 2026-03-31
> **参考**: oh-my-openagent (Sisyphus architecture)
> **状态**: 已批准

---

## 1. 概述

### 1.1 模块名称

Orchestrator（编排器）

### 1.2 职责

Orchestrator 是 Mozi AI Coding Agent 的核心编排层，负责：
- 持有智能决策大脑，实现 Thought → Decide → Delegate → Review 的 ReAct 循环
- 管理全局状态（TODO 列表、进度、决策历史）
- 委托 Context 模块构建上下文，按需分配给 Worker
- 调度执行组件池（Explorer/Planner/Coder/QualityChecker/Reviewer）
- 管理任务生命周期（COMPLEX 复杂度路由时）

### 1.3 核心能力

| 能力 | 说明 |
| ---- | ---- |
| Orchestrator-Worker 模式 | 编排器是智能大脑，Worker 是无状态执行者 |
| 核心 ReAct 循环 | Thought → Decide → Delegate → Review 循环 |
| 上下文管理 | 委托 Context 模块构建，按需分配给 Worker |
| 执行组件池 | Explorer/Planner/Coder + QualityChecker + Reviewer |
| Coder = ExecutionAgent | DEEP 任务时 Coder 包含完整的探索→规划→执行→验证流程 |
| 状态持久化 | TODO 列表、进度、决策历史支持断点续传 |

---

## 2. 核心问题与解决方案

### 2.1 上下文爆炸问题

**问题描述**：传统架构中，所有上下文信息都传递给单一 Agent，导致上下文膨胀难以控制。

**挑战**：信息泄露风险、Token 消耗不可控、Agent 难以聚焦当前任务。

**解决方案**：Orchestrator-Worker 模式 + 上下文隔离。只给 Worker 必要信息，Worker 返回摘要，用完即焚。

### 2.2 任务规划质量

**问题描述**：复杂任务需要合理的任务分解和执行计划。

**挑战**：LLM 规划的质量和一致性难以保证，粒度太粗或太细都会影响效率。

**解决方案**：Planner Worker 生成 TODO 列表，DecompositionValidator 验证分解有效性（完整性、原子性、独立性、可验证性）。

### 2.3 执行可靠性

**问题描述**：任务执行可能失败，需要有效的失败恢复和降级策略。

**挑战**：重试策略可能雪球效应，回滚机制需要正确清理副作用。

**解决方案**：RecoveryManager 实现多级恢复策略（Retry → Rollback → Degrade），QualityChecker 统一质量门禁。

### 2.4 Worker 复用与调度

**问题描述**：需要灵活的 Worker 调度策略，支持串行和并行执行。

**挑战**：同一 Worker 可能用于不同任务，需要避免状态污染。

**解决方案**：Worker 无状态设计，用完即焚。Orchestrator 根据 Category（QUICK/DEEP/STRATEGIC）决定调度策略。

---

## 3. 数据模型与状态机

### 3.1 核心类型定义

> **说明**：Orchestrator 使用 Task 模块定义的数据模型（Task、TaskResult、TaskStatus 等）。

### 3.2 状态机

#### 3.2.1 ReAct 循环状态机

```
┌─────────────────────────────────────────────────────────────┐
│                  编排器核心循环                               │
│                                                             │
│   ┌─────────┐      ┌─────────┐      ┌─────────┐            │
│   │ Thought │ ────▶│ Decide  │ ────▶│ Delegate│            │
│   │ 思考    │      │ 决策    │      │ 委托    │            │
│   └─────────┘      └─────────┘      └─────────┘            │
│        ▲                                  │                 │
│        │                                  ▼                 │
│   ┌─────────┐      ┌─────────┐      ┌─────────┐            │
│   │ Review  │ ◀────│ Receive │ ◀────│ Execute │            │
│   │ 审查    │      │ 接收    │      │ (Worker)│            │
│   └─────────┘      └─────────┘      └─────────┘            │
│        │                                                  │
│        ▼ (满意？)                                          │
│   ┌─────────┐                                             │
│   │  Update │                                             │
│   │  状态   │                                             │
│   └─────────┘                                             │
│        │                                                  │
│        ▼ (任务完成？)                                       │
│   ┌─────────┐                                             │
│   │  结束   │  或  继续下一轮                               │
│   └─────────┘                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2.2 Category 流水线状态

| Category | 预分析 | 全局规划 | 探索 | 任务规划 | 编码 | 质量检查 | 语义验收 |
|----------|--------|----------|------|----------|------|----------|-----------|
| **QUICK** | ✅ | ❌ | ⚠️ 轻量 | ❌ | ✅ | ⚠️ 可选 | ❌ |
| **DEEP** | ✅ | ❌ | ✅ | ✅ 显式 | ✅ | ✅ 强制 | ⚠️ 复杂 |
| **STRATEGIC** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 4. 模块结构

### 4.1 目录结构

```
mozi/orchestrator/
    __init__.py                  # 模块导出
    orchestrator.py              # Orchestrator 主类
    state.py                     # 全局状态管理
    category.py                  # Category 路由
    worker/                      # Worker 实现
        __init__.py
        explorer.py              # Explorer Worker
        planner.py               # Planner Worker
        coder.py                 # Coder Worker
    quality.py                   # QualityChecker
    reviewer.py                  # Reviewer
```

### 4.2 关键文件

| 文件 | 职责 |
| ---- | ---- |
| `orchestrator.py` | Orchestrator 主类，ReAct 循环实现 |
| `state.py` | 全局状态存储（TODO、进度、决策历史） |
| `category.py` | Category 路由（QUICK/DEEP/STRATEGIC） |
| `worker/explorer.py` | Explorer Worker，探索代码库 |
| `worker/planner.py` | Planner Worker，任务分解 |
| `worker/coder.py` | Coder Worker，代码执行 |
| `quality.py` | QualityChecker，质量门禁 |
| `reviewer.py` | Reviewer，语义验收 |

---

## 5. 接口、交互与流程

### 5.1 Orchestrator 主接口

```python
class Orchestrator:
    """编排器主类"""

    async def run(
        self,
        user_input: str,
        session_id: str,
    ) -> str:
        """
        执行 Orchestrator-Worker ReAct 循环

        Args:
            user_input: 用户输入
            session_id: 会话 ID

        Returns:
            最终响应结果
        """
        # 1. Thought: 分析当前状态
        # 2. Decide: 决定下一步
        # 3. Delegate: 委托 Worker
        # 4. Review: 审查结果
        # 5. Update: 更新状态
        # 循环直到任务完成
```

### 5.2 执行组件接口

| 组件 | 职责 | 特点 |
| ---- | ---- | ---- |
| **Explorer** | 探索代码库、搜索信息 | 无状态，只返回搜索结果 |
| **Planner** | 生成 TODO 列表、任务分解 | 无状态，只生成计划 |
| **Coder** | 编码执行、代码修改 | 无状态，只返回 diff |
| **QualityChecker** | 合并 Tester + Verifier：运行时测试 + 静态检查 | 统一质量门禁，代码缺陷拦截率 95%+ |
| **Reviewer** | 语义验收：需求对齐/最终交付评估 | 复杂任务触发，确保交付结果与原始意图对齐 |

### 5.3 上下文分配策略

```
┌─────────────────────────────────────────────────────────────┐
│                    上下文分配 (Context Allocation)             │
├─────────────────────────────────────────────────────────────┤
│  分配原则                                                      │
│  - Worker 只接收完成当前任务所需的最小上下文                    │
│  - 探索结果（给 Planner）                                    │
│  - 相关文件（给 Coder）                                       │
│  - TODO 列表状态（给 Coder）                                 │
├─────────────────────────────────────────────────────────────┤
│  返回处理                                                      │
│  - Worker 返回结果压缩摘要                                     │
│  - 结论归档到 State Store                                     │
│  - 详细过程不保留在主上下文                                    │
└─────────────────────────────────────────────────────────────┘
```

### 5.4 执行流程示例

以"实现支付宝支付功能"为例：

```
┌─────────────────────────────────────────────────────────────────┐
│  Round 1: 探索阶段                                               │
│  Thought: "我需要先了解现有支付模块的结构"                         │
│  Decide:  调用 Explorer Worker                                   │
│  Delegate: {query: "支付相关代码", scope: "src/payment"}        │
│  Receive:  [文件列表 + 关键函数签名]                              │
│  Review:  "信息足够，可以开始规划"                                 │
│  Update:  状态 → 探索完成                                        │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Round 2: 规划阶段                                               │
│  Thought: "需要生成 TODO 列表来管理复杂度"                         │
│  Decide:  调用 Planner Worker                                    │
│  Delegate: {context: 探索结果, goal: "实现支付宝支付"}             │
│  Receive:  [TODO.md: 5 个任务项]                                 │
│  Review:  "计划合理，开始执行"                                    │
│  Update:  状态 → TODO 列表已生成                                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Round 3-N: 执行循环 (每个 TODO 项一轮)                           │
│  Thought: "当前 TODO: 安装依赖"                                  │
│  Decide:  调用 Coder Worker                                      │
│  Delegate: {task: "安装 alipay-sdk", context: 当前文件}           │
│  Receive:  [diff + 安装日志]                                     │
│  Review:  "成功，标记 TODO 完成"                                   │
│  Update:  TODO[0] → ✅, 归档本轮上下文                            │
│  ─────────────────────────────────────────────────────────────  │
│  Thought: "当前 TODO: 创建 PaymentService"                       │
│  Decide:  调用 Coder Worker                                      │
│  ... (循环直到所有 TODO 完成)                                      │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  质量检查                                                        │
│  Thought: "自测通过，需要质量检查"                                │
│  Decide:  调用 QualityChecker                                    │
│  Delegate: {scope: "单元测试 + 静态检查 + 安全扫描"}              │
│  Receive:  [质量报告]                                            │
│  Review:  "通过，进入最终审查"                                    │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  最终审查                                                        │
│  Thought: "验证通过，进行最终交付审查"                            │
│  Decide:  调用 Reviewer                                          │
│  Receive:  [交付评估报告]                                        │
│  Review:  "通过，可以交付"                                        │
│  Update:  状态 → 任务完成                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 边界与契约

### 6.1 错误码定义

> **说明**：Orchestrator 模块的错误处理遵循统一异常体系。

| 错误码 | 错误类型 | 说明 |
| ------ | -------- | ---- |
| `ORCH_001` | OrchestratorError | 编排器内部错误 |
| `ORCH_002` | CategoryRoutingError | Category 路由失败 |
| `ORCH_003` | WorkerExecutionError | Worker 执行失败 |
| `ORCH_004` | QualityCheckError | 质量检查未通过 |
| `ORCH_005` | ReviewError | 语义验收失败 |
| `ORCH_006` | StateStoreError | 状态存储错误 |

### 6.2 API 契约

#### 6.2.1 Orchestrator.run()

**请求**：
```python
async def run(
    self,
    user_input: str,
    session_id: str,
) -> str
```

**响应**：
- `str`: 最终响应结果

**错误**：
- `ORCH_001`: 当编排器内部错误时抛出
- `ORCH_003`: 当所有 Worker 都执行失败时抛出

### 6.3 约束与限制

| 约束 | 限制值 | 说明 |
| ---- | ------ | ---- |
| 最大 ReAct 循环次数 | 100 | 防止无限循环 |
| Worker 执行超时 | 300 秒 | 可通过配置调整 |
| 单次委托最大上下文 | 4000 tokens | Worker 上下文限制 |
| 决策历史最大条数 | 50 | State Store 限制 |

---

## 7. 实现细节

### 7.1 全局状态管理

```python
@dataclass
class OrchestratorState:
    """编排器全局状态"""
    session_id: str
    category: Category
    todo_list: list[TodoItem]
    completed_steps: list[str]
    decision_history: list[Decision]
    context_refs: dict[str, str]  # 上下文引用索引


class StateStore:
    """状态存储"""

    async def save_state(self, state: OrchestratorState) -> None: ...

    async def load_state(self, session_id: str) -> OrchestratorState | None: ...

    async def update_todo(self, session_id: str, todo: TodoItem) -> None: ...

    async def complete_todo(self, session_id: str, todo_id: str) -> None: ...
```

### 7.2 Category 路由

```python
class Category(Enum):
    """任务类别枚举"""
    QUICK = "quick"      # 快速任务
    DEEP = "deep"        # 深度任务
    STRATEGIC = "strategic"  # 战略任务


class CategoryRouter:
    """Category 路由器"""

    def route(self, user_input: str) -> Category:
        """根据用户输入路由到合适的 Category"""
        # 分析任务复杂度
        # QUICK: 简单文件操作、单次工具调用
        # DEEP: 多步骤任务、需要规划
        # STRATEGIC: 复杂多模块任务
```

### 7.3 Worker 执行

```python
class WorkerPool:
    """Worker 连接池"""

    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}

    async def execute(
        self,
        worker_type: str,
        context: WorkerContext,
    ) -> WorkerResult:
        """执行 Worker 任务"""
        worker = self._workers.get(worker_type)
        if not worker:
            raise WorkerExecutionError(f"Unknown worker type: {worker_type}")

        return await worker.execute(context)
```

---

## 8. 配置

> **说明**：本模块的配置项已汇总到 [Config 模块设计文档](./2026-03-29_config.md)。

---

## 9. 度量指标

| 指标名称 | 类型 | 说明 |
| -------- | ---- | ---- |
| `orchestrator_run_total` | Counter | Orchestrator 运行总次数 |
| `orchestrator_run_duration_seconds` | Histogram | 运行耗时分布 |
| `react_loop_iterations` | Histogram | ReAct 循环迭代次数分布 |
| `worker_execute_total` | Counter | Worker 执行总次数（按类型） |
| `worker_execute_duration_seconds` | Histogram | Worker 执行耗时分布 |
| `category_distribution` | Counter | Category 分布统计 |
| `quality_check_pass_rate` | Gauge | 质量检查通过率 |
| `task_completion_rate` | Gauge | 任务完成率 |

---

## 10. 参考

- **oh-my-openagent (Sisyphus architecture)**：参考架构
- **错误处理**：遵循统一异常体系，见 [error_handling.md](./2026-03-29_error_handling.md)
- **测试策略**：见 [testing.md](./2026-03-29_testing.md)
- **相关模块**：Context、[Task](./2026-03-29_task.md)、[Model](./2026-03-29_model.md)

---

## 变更记录

| 版本 | 日期 | 变更内容 |
| ---- | ---- | -------- |
| 3.0 | 2026-03-31 | 重构为模板 v3.0 结构：新增 §6 边界与契约、§9 度量指标；调整章节编号 |
| 3.2 | 2026-03-31 | Manager-Worker 模式更名为 Orchestrator-Worker 模式 |
| 3.1 | 2026-03-31 | 移除复杂度体系映射，QUICK/DEEP/STRATEGIC 为唯一路由体系 |
| 3.0 | 2026-03-31 | 初始版本 |

_版本: 3.0_
_更新日期: 2026-03-31_
