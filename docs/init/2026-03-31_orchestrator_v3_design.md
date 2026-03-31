# Orchestrator 编排层设计文档 v3.0

> **模板版本**: 3.0
> **创建日期**: 2026-03-31
> **参考**: oh-my-openagent (Sisyphus architecture)
> **状态**: 已批准

---

## 1. 概述

### 1.1 设计目标

参考 oh-my-openagent 的 Sisyphus 架构，重新设计 Mozi 编排层，引入：
- Category-based routing（任务分类路由）
- Todo Enforcer（任务强制执行）
- Recursive Loop（递归优化循环）
- 专业化 Agent 体系（计划/探索/执行/验证/Review）

### 1.2 核心定位

**Orchestrator 是会话级 Agent**，其特殊性在于：
- scope 是整个会话生命周期
- 它的"工具"包括其他 Agent
- **主动驱动任务完成**，而非仅规划委托

### 1.3 与 v2.0 设计对比

| 方面 | v2.0 设计 | v3.0 设计 |
|------|-----------|-----------|
| 架构 | 统一工作循环 | OrchestratorAgent + Agents |
| 路由 | 规划决策（action: execute/delegate） | Category-based routing |
| 任务完成 | 依赖 Agent 自觉 | TodoEnforcer 强制监控 |
| 完成度 | 无递归优化 | RecursiveLoop 确保 100% |
| Agents | 统一 Agent + 委托模板 | Plan/Explore/Execute/Verify/Review 分工 |

---

## 2. 整体架构

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────┐
│         OrchestratorAgent（会话级）            │
│  - 驱动任务完成                              │
│  - 管理会话生命周期                          │
│  - 选择 Category 路由到 Agent                │
└─────────────────────────────────────────────┘
    │
    ├──► Category.QUICK → ExecutionAgent
    │
    ├──► Category.DEEP → ResearchAgent
    │
    └──► Category.STRATEGIC → PlanningAgent
```

---

## 3. Agent 体系

### 3.1 Agent 类型

| Agent | 层级 | 职责 | 模式 |
|-------|------|------|------|
| **OrchestratorAgent** | 会话级 | 统帅全局，路由决策，驱动任务完成 | 管理 |
| **ExecutionAgent** | 任务级 | 快速执行，无需规划 | Do |
| **ResearchAgent** | 任务级 | 探索执行，生成 TodoList | Plan → ReAct → Reflect |
| **PlanningAgent** | 任务级 | 战略规划，需用户确认 | Plan → 用户确认 → 执行 |
| **VerifyAgent** | 任务级 | 结果验证，质量检查 | Verify |
| **ReviewAgent** | 任务级 | 自我反思，持续优化 | Review |

### 3.2 层级差异

| 层级 | Agent | scope | 工具 |
|------|-------|-------|------|
| 会话级 | OrchestratorAgent | 整个会话 | Agents |
| 任务级 | 其他 Agents | 单次任务 | 工具 + 子任务委托 |

---

## 4. Category Routing

### 4.1 任务分类

| Category | 触发方式 | 场景 | 规划产出 | 用户确认 |
|----------|----------|------|----------|----------|
| **QUICK** | 自动 | 简单任务 | ❌ 无 | ❌ 无 |
| **DEEP** | 自动 | 常规复杂任务 | TodoList | ❌ 无 |
| **STRATEGIC** | 用户触发 `/plan` | 需要规划的任务 | Planning Doc | ✅ 需要 |

```python
class Category(Enum):
    """任务分类"""
    QUICK = "quick"           # 简单任务，无需规划，直接执行
    DEEP = "deep"            # 常规复杂任务，规划生成 TodoList
    STRATEGIC = "strategic"  # 用户触发，规划生成 Planning Doc，需确认
```

### 4.2 路由规则

```python
class CategoryRouter:
    """根据任务特征路由到对应 Agent"""

    def route(self, task: TaskSpec, user_intent: UserIntent) -> Category:
        """
        路由决策：
        - STRATEGIC: 用户主动触发 /plan 命令
        - QUICK: ≤10行改动，单文件，简单修改
        - DEEP: 其他复杂任务，规划生成 TodoList
        """
        # STRATEGIC 由用户显式触发
        if user_intent.is_planning_mode:
            return Category.STRATEGIC

        # 简单任务直接执行
        if self.is_simple_task(task):
            return Category.QUICK

        # 其他复杂任务走 DEEP
        return Category.DEEP

    def is_simple_task(self, task: TaskSpec) -> bool:
        """简单任务：代码改动 ≤10 行，单一文件"""
        return (
            task.estimated_lines <= 10
            and task.files_count == 1
            and task.risk_level == RiskLevel.LOW
        )
```

### 4.3 触发机制

```
用户输入
    │
    ├── /plan ──────────→ STRATEGIC（用户主动触发）
    │
    └── 普通输入 ───────→ QUICK / DEEP（自动判断）
```

### 4.4 路由示例

| 任务 | Category | 触发 | Agent |
|------|----------|------|-------|
| 修复拼写错误 | QUICK | 自动 | ExecutionAgent |
| 添加单文件功能 | QUICK | 自动 | ExecutionAgent |
| Bug 修复（多文件） | DEEP | 自动 | ResearchAgent |
| 代码重构（多模块） | DEEP | 自动 | ResearchAgent |
| 系统架构设计 | STRATEGIC | `/plan` 触发 | PlanningAgent |
| 技术选型决策 | STRATEGIC | `/plan` 触发 | PlanningAgent |

---

## 5. 工作流程

### 5.1 主循环

```
OrchestratorAgent.run(session_id)
    │
    ├──► Understand: 解析用户输入
    │
    ├──► Route: Category Routing
    │
    ├──► Execute: 委托给 Agent
    │
    ├──► Monitor: TodoEnforcer 后台监控
    │
    ├──► Refine: RecursiveLoop 递归优化
    │
    └──► Evaluate: 验证结果，决定完成/继续/失败
```

### 5.2 委托流程

```
OrchestratorAgent.execute()
    │
    ▼
构建 DelegationTemplate
    │
    ▼
根据 Category 选择 Agent
    │
    ├──► QUICK → ExecutionAgent
    ├──► DEEP → ResearchAgent
    └──► STRATEGIC → PlanningAgent
    │
    ▼
调用 Agent.execute(template, context)
    │
    ▼
TodoEnforcer.monitor()  # 后台并行监控
    │
    ▼
RecursiveLoop 递归优化直到 100% 完成
    │
    ▼
返回结果给 OrchestratorAgent
    │
    ▼
OrchestratorAgent.evaluate() 结果
```

---

## 6. Todo Enforcer

### 6.1 问题背景

任务被 Agent 接收后可能中途放弃（idle、超时、失败未重试）。

### 6.2 设计

```python
class TodoEnforcer:
    """确保任务不放弃"""

    def __init__(self, idle_timeout: timedelta = timedelta(minutes=5)):
        self.idle_timeout = idle_timeout
        self.task_states: dict[str, TaskState] = {}

    async def monitor(self, tasks: list[Task]):
        """监控所有进行中的任务"""
        for task in tasks:
            state = self.task_states.get(task.id)

            if state == TaskState.IDLE:
                if self.is_idle_too_long(task):
                    await self.rerun(task)
            elif state == TaskState.FAILED:
                await self.recover(task)

    async def rerun(self, task: Task):
        """重新激活 idle 任务"""
        task.retry_count += 1

        if task.retry_count > MAX_RETRIES:
            # 超过重试次数，升级处理
            await self.escalate(task)
        else:
            # 重新分配给原 Agent 或降级
            await self.reassign(task)

    async def escalate(self, task: Task):
        """升级任务：委托给更高级别 Agent"""
        if task.category == Category.QUICK:
            await self.reassign(task, Category.DEEP)
        elif task.category == Category.DEEP:
            await self.reassign(task, Category.STRATEGIC)
        else:
            # 无法升级，返回用户请求澄清
            await self.request_clarification(task)
```

### 6.3 状态机

```
TaskState:
    PENDING → ACTIVE → IDLE → (rerun) → ACTIVE
                ↓
              FAILED → (retry) → ACTIVE
                ↓
           (max retries) → ESCALATED / CLARIFICATION_NEEDED
```

---

## 7. Recursive Loop

### 7.1 问题背景

如何确保任务达到 100% 完成？单次执行可能遗漏部分需求。

### 7.2 设计

```python
class RecursiveLoop:
    """递归优化循环，确保 100% 完成"""

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations

    async def run(self, task: Task, context: dict) -> Result:
        """递归执行直到完成"""
        iteration = 0
        result = None

        while iteration < self.max_iterations:
            # 执行任务
            result = await self.execute_once(task, context, iteration)

            # 检查完成度
            completion = self.assess_completion(result)

            if completion >= 100:
                return result

            # 分析未完成部分
            remaining = self.analyze_remaining(task, result)

            # 如果没有剩余工作，结束
            if not remaining:
                return result

            # 更新任务为剩余部分
            task = remaining
            iteration += 1

        # 超过最大迭代次数，返回当前结果并标记
        return self.finalize_result(result, incomplete=True)

    async def execute_once(
        self, task: Task, context: dict, iteration: int
    ) -> Result:
        """单次执行"""
        # 根据 Category 选择执行 Agent
        agent = self.get_agent(task.category)
        return await agent.execute(task, context)

    def assess_completion(self, result: Result) -> float:
        """
        评估完成度（0-100）

        算法：
        1. 检查是否有执行错误（错误存在则完成度=0）
        2. 检查证据是否完整（无证据则不完整）
        3. 基于证据计算基础完成度
        4. 验证目标达成情况
        """
        evidence = result.evidence

        # 1. 执行错误检查
        if result.error:
            return 0.0

        # 2. 证据完整性检查
        if not evidence:
            return 0.0

        has_files_modified = bool(evidence.files_modified)
        has_output = bool(evidence.output)
        has_commands = bool(evidence.commands_executed)

        # 如果没有任何证据，完成度为 0
        if not (has_files_modified or has_output or has_commands):
            return 0.0

        # 3. 基础完成度计算（基于证据权重）
        # 注意：这里使用加权计算而非简单加分，更合理
        weights = {
            "files_modified": 0.5,  # 修改文件权重最高
            "output": 0.3,           # 有输出说明有执行
            "commands": 0.2,         # 命令执行是辅助证据
        }

        base_score = 0.0
        if has_files_modified:
            base_score += weights["files_modified"] * 100
        if has_output:
            base_score += weights["output"] * 100
        if has_commands:
            base_score += weights["commands"] * 100

        # 4. 目标达成验证（使用 expected_outcome 对比）
        # 注意：实际实现应使用 LLM 或结构化对比
        goal_achieved = self.check_goal_achieved(result)
        if not goal_achieved:
            # 未完全达成目标，降低完成度
            base_score *= 0.7

        return min(base_score, 100.0)

    def check_goal_achieved(self, result: Result) -> bool:
        """
        检查目标是否达成

        算法：
        1. 检查 result.success 标志
        2. 检查是否有实质性的文件修改或输出
        3. （未来：可使用 LLM 对比 expected_outcome）
        """
        if not result.success:
            return False

        evidence = result.evidence
        if not evidence:
            return False

        # 有文件修改或有意义的输出才算达成
        if evidence.files_modified:
            return True

        if evidence.output and len(evidence.output) > 10:
            return True

        return False

    def analyze_remaining(self, task: Task, result: Result) -> Task | None:
        """
        分析剩余工作

        算法：
        1. 如果完成度 >= 100%，返回 None（已完成）
        2. 如果完成度 >= 80%，视为实际完成，返回 None
        3. 否则，返回剩余任务供递归处理
        """
        completion = self.assess_completion(result)

        # 完成度阈值：达到 80% 即视为完成
        COMPLETION_THRESHOLD = 80.0

        if completion >= COMPLETION_THRESHOLD:
            return None  # 实际完成

        # 如果完成度过低且有错误，不继续递归
        if completion < 20.0 and result.error:
            return None

        # 构建剩余任务
        remaining_goal = f"继续完成未竟任务（当前完成度: {completion:.0f}%）"
        remaining_spec = TaskSpec(
            goal=remaining_goal,
            entities=task.spec.entities,
            constraints=task.spec.constraints,
            risk_level=task.spec.risk_level,
            estimated_lines=max(1, task.spec.estimated_lines // 2),
            files_count=max(1, task.spec.files_count),
        )

        return Task(
            id=f"{task.id}-remaining-{task.iterations}",
            spec=remaining_spec,
            category=task.category,
            state=TaskState.PENDING,
            iterations=task.iterations + 1,
        )
```

---

## 8. Agents 详细设计

### 8.1 OrchestratorAgent

```python
class OrchestratorAgent:
    """主编排 Agent（会话级）"""

    async def run(self, session_id: str):
        """主工作循环"""
        while True:
            # Understand: 解析用户输入
            task_spec = await self.understand(session_id)

            # Route: Category 路由
            category = self.route(task_spec, self.get_user_intent())

            # Execute: 委托给对应 Agent
            result = await self.delegate(category, task_spec)

            # Evaluate: 验证结果
            evaluation = await self.evaluate(result)

            if evaluation.next_action == "complete":
                await self.notify_user(result)
            elif evaluation.next_action == "fail":
                await self.handle_failure(evaluation)
```

**职责**：统帅全局，路由决策，驱动任务完成
**特点**：会话级，持续运行，管理整体进度

### 8.2 ExecutionAgent

```python
class ExecutionAgent:
    """执行 Agent"""

    async def execute(self, task: Task, context: dict) -> Result:
        # 1. 验证任务确实简单
        # 2. 直接执行工具调用
        # 3. 验证结果
        # 4. 返回结果
```

**职责**：≤10行改动、拼写修正、简单修改
**特点**：快速执行，无需规划，直接 Do

### 8.3 ResearchAgent

```python
class ResearchAgent:
    """研究 Agent"""

    async def execute(self, task: Task, context: dict) -> Result:
        # 1. 理解任务
        # 2. Plan → 生成 TodoList
        # 3. ReAct → 按 TodoList 执行
        # 4. Verify → 验证结果
        # 5. Reflect → 自我反思
        # 6. 返回结果
```

**职责**：多文件重构、代码探索、深度研究
**特点**：Plan + ReAct + Reflect 循环
**规划产出**：TodoList（内部使用，无需用户确认）

### 8.4 PlanningAgent

```python
class PlanningAgent:
    """规划 Agent"""

    async def execute(self, task: Task, context: dict) -> Result:
        # 1. 与用户澄清范围（如果需要）
        # 2. Plan → 生成 Planning Document
        # 3. 展示计划给用户
        # 4. 用户确认计划
        # 5. 分解为子任务委托 ResearchAgent
        # 6. 汇总结果
```

**职责**：架构设计、技术选型、复杂规划
**特点**：规划优先，需要用户确认
**规划产出**：Planning Document（需用户审阅确认）

### 8.5 VerifyAgent

```python
class VerifyAgent:
    """验证 Agent"""

    async def execute(self, task: Task, context: dict) -> Result:
        # 1. 检查语法正确性
        # 2. 检查 lint 通过
        # 3. 检查测试通过
        # 4. 返回验证结果
```

**职责**：结果验证，质量检查
**特点**：独立的验证阶段，确保输出质量

### 8.6 ReviewAgent

```python
class ReviewAgent:
    """Review Agent"""

    async def execute(self, task: Task, result: Result, context: dict) -> Result:
        # 1. 评估完成度
        # 2. 分析剩余工作
        # 3. 决定是否需要重试
        # 4. 返回优化建议
```

**职责**：自我反思，持续优化
**特点**：递归优化，确保 100% 完成

---

## 9. 数据模型

### 9.1 新增/修改的模型

```python
class Category(Enum):
    """任务分类"""
    QUICK = "quick"
    DEEP = "deep"
    STRATEGIC = "strategic"


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"       # 单文件、低影响、无副作用
    MEDIUM = "medium" # 多文件、中等影响、可回滚
    HIGH = "high"     # 架构变更、跨模块、高风险


class TaskSpec(BaseModel):
    """任务规约"""
    goal: str
    entities: dict[str, str]
    constraints: list[str]
    risk_level: RiskLevel
    delegation_hint: str = ""

    # 新增 v3.0 字段
    estimated_lines: int = 0
    files_count: int = 1
    requires_planning: bool = False
    requires_architecture_decision: bool = False


class DelegationTemplate(BaseModel):
    """委托模板"""
    task: str
    expected_outcome: str
    must_do: list[str]
    must_not_do: list[str]
    context: dict
    category: Category  # 新增：指定分类


class TaskState(Enum):
    """任务状态"""
    PENDING = "pending"
    ACTIVE = "active"
    IDLE = "idle"
    FAILED = "failed"
    ESCALATED = "escalated"
    CLARIFICATION_NEEDED = "clarification_needed"
    COMPLETED = "completed"


class Task(BaseModel):
    """任务"""
    id: str
    spec: TaskSpec
    category: Category
    state: TaskState = TaskState.PENDING
    retry_count: int = 0
    iterations: int = 0
    result: Result | None = None
```

### 9.2 模块结构

```
mozi/orchestrator/
    __init__.py
    orchestrator_agent.py     # 主编排 Agent（会话级）
    category_router.py        # Category 路由
    agents/
        __init__.py
        base.py              # Agent 基类
        execution_agent.py   # 执行 Agent
        research_agent.py     # 研究 Agent
        planning_agent.py     # 规划 Agent
        verify_agent.py       # 验证 Agent
        review_agent.py       # Review Agent
    todo_enforcer.py          # Todo 强制执行
    recursive_loop.py         # 递归优化循环
    delegation.py             # 委托协议
    recovery.py               # 失败恢复
```

---

## 10. 设计原则总结

| 原则 | 说明 |
|------|------|
| 主动驱动 | OrchestratorAgent 主动驱动任务完成 |
| 专业化分工 | Plan/Explore/Execute/Verify/Review 各司其职 |
| 路由自动化 | Category-based routing 自动选择 |
| 完成度保证 | ReviewAgent + RecursiveLoop 确保 100% |
| 任务不放弃 | TodoEnforcer 强制监控和恢复 |
| 证据驱动 | NO EVIDENCE = NOT COMPLETE |

---

## 10.1 用户故事与用例

### 10.1.1 用户故事

| ID | 用户 | 故事 |
|----|------|------|
| US-01 | 用户 | 我希望简单任务直接执行，无需等待 |
| US-02 | 用户 | 我希望复杂任务自动规划为 TodoList 并自主执行 |
| US-03 | 用户 | 我希望重要任务有详细规划并经我确认后再执行 |
| US-04 | 用户 | 我希望被中断的任务能被自动恢复 |
| US-05 | 用户 | 我希望系统能告诉我任务完成到了什么程度 |

### 10.1.2 关键用例

**UC-01: QUICK 任务执行**
```
场景: 用户要求修复拼写错误
输入: "fix typo in README.md"
触发: 自动
期望:
  1. CategoryRouter 识别为 QUICK
  2. ExecutionAgent 直接执行
  3. VerifyAgent 验证
  4. ReviewAgent 评估完成度
  5. 完成度 = 100%
```

**UC-02: DEEP 任务执行**
```
场景: 用户要求重构认证模块
输入: "refactor auth module to use JWT"
触发: 自动
期望:
  1. CategoryRouter 识别为 DEEP
  2. ResearchAgent Plan → TodoList
  3. ResearchAgent ReAct → 按 TodoList 执行
  4. VerifyAgent 验证
  5. ReviewAgent 评估完成度
```

**UC-03: STRATEGIC 任务执行**
```
场景: 用户要求设计微服务架构
输入: "/plan design microservice architecture for our app"
触发: /plan 命令
期望:
  1. PlanningAgent 生成 Planning Document
  2. 展示计划给用户审阅
  3. 用户确认方案
  4. 分解为子任务委托 ResearchAgent
  5. VerifyAgent + ReviewAgent 验证评估
```

---

## 11. 优先级与迭代范围

### 11.1 MoSCoW 优先级

| 优先级 | 内容 | 说明 |
|--------|------|------|
| **P0 (Must)** | OrchestratorAgent + CategoryRouter + ExecutionAgent | 核心框架，简单任务闭环 |
| **P1 (Should)** | ResearchAgent + PlanningAgent + VerifyAgent + TodoEnforcer | 重要功能，复杂任务支持 |
| **P2 (Could)** | ReviewAgent + RecursiveLoop 完整实现 | 增强功能，完成度保证 |
| **P3 (Won't)** | 多轮递归优化、复杂分析算法 | 未来探索，当前不做 |

### 11.2 迭代范围

| 迭代 | 内容 | 目标 |
|------|------|------|
| **Iter 1** | OrchestratorAgent + CategoryRouter + ExecutionAgent + VerifyAgent | 能够完成一个 QUICK 任务的全流程 |
| **Iter 2** | ResearchAgent + PlanningAgent | 支持 DEEP/STRATEGIC 任务 |
| **Iter 3** | ReviewAgent + TodoEnforcer + RecursiveLoop | 完成度保证和任务恢复 |

---

## 12. 验收标准

### 12.1 功能验收

| 功能 | 验收条件 | 验证方法 | 量化指标 |
|------|----------|----------|----------|
| OrchestratorAgent | 能接收用户输入并路由到对应 Agent | 单元测试 | 100% 路由成功 |
| CategoryRouter | QUICK/DEEP/STRATEGIC 路由正确 | 参数化测试 | ≥90% 路由准确 |
| ExecutionAgent | 能执行简单修改（≤10行） | E2E 测试 | 完成度 = 100% |
| ResearchAgent | 能执行多文件修改任务 | 集成测试 | 证据完整率 ≥80% |
| PlanningAgent | 能制定计划并委托子任务 | 场景测试 | 计划通过率 ≥80% |
| VerifyAgent | 能验证修改正确性 | 单元测试 | 验证准确率 ≥90% |
| ReviewAgent | 能评估完成度 | 评估测试 | 收敛率 ≥90% |
| TodoEnforcer | idle 任务能被重新激活 | 模拟测试 | 恢复率 ≥95% |

### 12.2 非功能需求

| 指标 | 要求 | 说明 |
|------|------|------|
| 响应时间 | 单次任务 < 30s | 不含用户交互等待 |
| 路由准确率 | > 90% | Category 路由正确性 |
| 任务完成率 | > 95% | TodoEnforcer 启用后 |
| 递归收敛 | ≤ 5 次迭代 | ReviewAgent 最大次数 |

---

## 13. 风险与依赖

### 13.1 风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Category 路由误判 | 任务分配错误 | 提供降级机制（升级到更高类别） |
| ReviewAgent 无限循环 | 资源耗尽 | max_iterations=5 硬限制 |
| TodoEnforcer 过度干预 | Agent 无法完成 | 只在 idle 超时后干预 |

### 13.2 依赖

| 依赖 | 来源模块 | 说明 |
|------|----------|------|
| Model Layer | `mozi/capabilities/model/` | LLM 调用能力（已完成） |
| Tool Layer | `mozi/capabilities/tools/` | 工具执行能力（已完成） |
| Session Layer | `mozi/session/` | 会话管理（已完成） |
| Context Layer | `mozi/context/` | 上下文传递（已完成） |

---

## 14. 假设与约束

### 14.1 假设

1. Agent 执行结果可通过 Evidence 量化
2. Category 路由在大多数场景下可准确判断
3. TodoEnforcer 的 idle_timeout=5min 是合理值

### 14.2 约束

1. 单个会话内 OrchestratorAgent 不重启
2. Agent 失败后最多重试 2 次
3. ReviewAgent 最大迭代 5 次

---

## 15. 不在范围内

以下功能当前版本不包含：

| 功能 | 原因 |
|------|------|
| 多 OrchestratorAgent 集群 | 单会话设计足够 |
| 复杂分析算法（如语义完成度评估） | P3 优先级 |
| Agent 自动学习/适应 | 未来探索 |

---

## 16. 与现有架构的关系

### 16.1 Category Routing vs 复杂度路由

**现有设计**（v2.0）：复杂度路由（SIMPLE ≤40 / MEDIUM 41-70 / COMPLEX >70）
- 用于决定是否需要分解任务

**v3.0 设计**：Category 路由（QUICK / DEEP / STRATEGIC）
- 用于决定委托给哪个 Agent

**关系**：两层路由
1. 第一层：复杂度路由（判断是否需要分解）
2. 第二层：Category 路由（决定 Agent 类型）

```
用户输入
    │
    ▼
复杂度路由 → 判断是否需要分解
    │
    ├──► 需要分解 → PlanningAgent 分解
    │
    └──► 不需要分解 → Category 路由
              │
              ├──► QUICK → ExecutionAgent
              ├──► DEEP → ResearchAgent
              └──► STRATEGIC → PlanningAgent
```

---

_版本: 3.0_
_更新日期: 2026-03-31_
