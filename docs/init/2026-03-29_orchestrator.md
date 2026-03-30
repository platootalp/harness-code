# Orchestrator 编排器设计文档

> **模板版本**: 2.0
> **创建日期**: 2026-03-29
> **最后更新**: 2026-03-30

---

## 1. 概述

### 1.1 核心定位

**Orchestrator 就是一个 Agent**，一个位于会话层级的 Agent。

它的特殊性在于：
- scope 是整个会话生命周期
- 它的"工具"包括其他 Agent

### 1.2 统一的工作流

所有 Agent 共享相同的工作循环：

```
Agent（工作循环）
    │
    ├──► 理解（Understand）
    │         解析输入，提取目标、实体、约束
    │
    ├──► 规划（Plan）
    │         决定如何执行，是否需要委托
    │
    ├──► 执行（Execute）
    │         调用工具 或 委托子Agent
    │
    └──► 评估（Evaluate）
              验证结果，决定下一步（继续/失败/完成）
```

### 1.3 层级差异只是 scope 不同

| 层级 | 名称 | scope |
|------|------|-------|
| 会话级 | Orchestrator Agent | 管理整个会话生命周期 |
| 任务级 | Task Agent | 执行单个具体任务 |
| 工具级 | 直接调用 | 执行单一操作 |

**委托的本质**：Agent 在 Execute 阶段调用子 Agent，子 Agent 遵循相同的工作循环。

### 1.4 设计原则

| 原则 | 说明 |
|------|------|
| 递归结构 | Agent 可以委托子 Agent，子 Agent 遵循相同工作流 |
| 结构化委托 | 用模板约束子 Agent 行为 |
| 证据驱动 | NO EVIDENCE = NOT COMPLETE |
| 自我恢复 | 失败后自动重试或升级 |

---

## 2. Agent 工作循环

### 2.1 理解（Understand）

解析输入，提取任务规约（TaskSpec）：

```python
class TaskSpec(BaseModel):
    """任务规约"""
    goal: str                           # 目标（原文）
    entities: dict[str, str]            # 实体：{file, func, language}
    constraints: list[str]               # 约束条件
    risk_level: RiskLevel               # LOW / MEDIUM / HIGH
    delegation_hint: str = ""            # 委托提示（如果需要）
```

### 2.2 规划（Plan）

决定如何执行：

```python
class Plan(BaseModel):
    """执行计划"""
    action: str                          # "execute" | "delegate" | "clarify" | "complete"
    agent_type: str | None               # 如果是 delegate，指定子Agent类型
    delegation_template: DelegationTemplate | None  # 委托模板
    reason: str                          # 决策理由
```

**规划决策**：

```
输入: TaskSpec
输出: Plan

if 目标不明确:
    → Plan(action="clarify")
elif 需要探索代码库:
    → Plan(action="delegate", agent_type="explorer")
elif 可以直接执行:
    → Plan(action="execute")
elif 完成:
    → Plan(action="complete")
```

### 2.3 执行（Execute）

根据 Plan 执行：

```python
async def execute(plan: Plan, context: dict) -> Result:
    if plan.action == "execute":
        return await execute_tools(context)
    elif plan.action == "delegate":
        return await delegate_to_agent(plan, context)
    elif plan.action == "clarify":
        return await ask_clarification(context)
```

### 2.4 评估（Evaluate）

验证结果，决定下一步：

```python
class Evaluation(BaseModel):
    success: bool
    evidence: dict                       # 证据
    next_action: str                    # "continue" | "retry" | "delegate" | "complete" | "fail"
    issues: list[str]                   # 发现的问题
```

---

## 3. 委托协议

### 3.1 委托模板

当 Agent 选择 delegate 时，使用模板约束子 Agent：

```python
class DelegationTemplate(BaseModel):
    """委托模板"""
    task: str                    # 任务描述
    expected_outcome: str         # 期望结果
    must_do: list[str]           # 必须做的事
    must_not_do: list[str]       # 禁止做的事
    context: dict                # 额外上下文
```

### 3.2 委托示例

```
委托给 ExplorerAgent:
  task: "探索 /src 目录下的代码结构，找出处理用户认证的模块"
  expected_outcome: "返回认证相关的文件列表和它们的主要职责"
  must_do: ["只读文件", "返回文件路径"]
  must_not_do: ["不要修改任何文件", "不要执行命令"]

委托给 ExecutorAgent:
  task: "在 auth.py 中添加 JWT 验证功能"
  expected_outcome: "auth.py 包含 validate_jwt 函数，可验证 JWT token"
  must_do: ["使用 pyjwt 库", "处理过期和无效 token"]
  must_not_do: ["不要删除现有代码", "不要修改其他文件"]
```

### 3.3 委托流程

```
Agent.execute()
    │
    ▼
Plan(action="delegate")
    │
    ▼
构建 DelegationTemplate
    │
    ▼
调用子 Agent.execute(template, context)
    │
    ▼
子 Agent 遵循相同工作循环
    │
    ▼
返回结果给父 Agent
    │
    ▼
Agent.evaluate() 结果
```

---

## 4. 失败恢复

### 4.1 失败分类

```python
class FailureType(Enum):
    EXECUTION_ERROR = "execution_error"     # 执行错误
    VERIFICATION_ERROR = "verification_error" # 验证错误
    TIMEOUT_ERROR = "timeout_error"         # 超时
    DELEGATION_ERROR = "delegation_error"    # 委托失败
```

### 4.2 恢复策略

| 失败类型 | 策略 |
|----------|------|
| EXECUTION_ERROR | 重试（最多2次）→ 仍失败则升级 |
| VERIFICATION_ERROR | 修复后重试（最多1次）→ 仍失败则澄清 |
| TIMEOUT_ERROR | 重试（最多1次）→ 仍失败则拆分任务 |
| DELEGATION_ERROR | 重试委托或更换 Agent 类型 |

### 4.3 升级路径

```
失败次数超过阈值
    │
    ▼
升级到更专业的 Agent
    │
    ▼
如果所有 Agent 都失败
    │
    ▼
返回用户，请求澄清或人工介入
```

---

## 5. 验证机制

### 5.1 证据收集

每个 Agent 执行后必须收集证据：

```python
class Evidence(BaseModel):
    """证据"""
    action_taken: str                   # 执行的动作
    files_read: list[str]               # 读取的文件
    files_modified: list[str]           # 修改的文件
    files_created: list[str]            # 创建的文件
    commands_executed: list[str]         # 执行的命令
    output: str                         # 输出
    model_messages: list[str]           # LLM 消息
```

### 5.2 验证规则

**NO EVIDENCE = NOT COMPLETE**

```python
def evaluate(result: Result) -> Evaluation:
    evidence = result.evidence

    if not evidence:
        return Evaluation(success=False, next_action="fail", issues=["No evidence provided"])

    if evidence.files_modified and not verify_syntax(evidence.files_modified):
        return Evaluation(success=False, next_action="retry", issues=["Syntax error"])

    if evidence.files_modified and not verify_lint(evidence.files_modified):
        return Evaluation(success=False, next_action="retry", issues=["Lint error"])

    return Evaluation(success=True, next_action="complete")
```

---

## 6. 会话级 Agent

### 6.1 Orchestrator 的特殊性

Orchestrator 是一个会话级 Agent：

```python
class Orchestrator:
    """会话级 Agent"""

    async def run(self, session_id: str):
        """工作循环"""
        while True:
            # 理解
            user_input = await self.get_user_input(session_id)
            task_spec = await self.understand(user_input)

            # 规划
            plan = await self.plan(task_spec)

            # 执行
            if plan.action == "delegate":
                result = await self.delegate(plan)
            else:
                result = await self.execute(plan)

            # 评估
            evaluation = await self.evaluate(result)

            if evaluation.next_action == "complete":
                await self.notify_user(result)
            elif evaluation.next_action == "fail":
                await self.handle_failure(evaluation)
```

### 6.2 与任务级 Agent 的区别

| 方面 | 会话级 Agent | 任务级 Agent |
|------|-------------|-------------|
| scope | 整个会话 | 单次任务 |
| 工具 | 其他 Agent、工具 | 主要是工具 |
| 记忆 | 长期记忆 | 任务上下文 |
| 生命周期 | 会话期间 | 任务完成 |

---

## 7. 数据模型

### 7.1 核心数据模型

```python
class TaskSpec(BaseModel):
    """任务规约"""
    goal: str
    entities: dict[str, str]
    constraints: list[str]
    risk_level: RiskLevel
    delegation_hint: str = ""


class Plan(BaseModel):
    """执行计划"""
    action: str
    agent_type: str | None
    delegation_template: DelegationTemplate | None
    reason: str


class Result(BaseModel):
    """执行结果"""
    success: bool
    data: dict
    evidence: Evidence
    error: str | None


class Evaluation(BaseModel):
    """评估结果"""
    success: bool
    evidence: dict
    next_action: str
    issues: list[str]


class Evidence(BaseModel):
    """证据"""
    action_taken: str
    files_read: list[str] = []
    files_modified: list[str] = []
    files_created: list[str] = []
    commands_executed: list[str] = []
    output: str = ""


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FailureType(Enum):
    EXECUTION_ERROR = "execution_error"
    VERIFICATION_ERROR = "verification_error"
    TIMEOUT_ERROR = "timeout_error"
    DELEGATION_ERROR = "delegation_error"
```

---

## 8. 模块结构

```
mozi/orchestrator/
    __init__.py
    agent.py                    # Agent 基类和通用工作循环
    orchestrator.py             # Orchestrator（会话级 Agent）
    delegation.py               # 委托协议和模板
    recovery.py                 # 失败恢复
    verification.py             # 验证机制
```

---

## 9. 与旧设计对比

| 旧设计 | 新设计 |
|--------|--------|
| 四阶段流程（理解→探索→执行→验证） | 统一工作循环（理解→规划→执行→评估） |
| Orchestrator 是控制平面 | Orchestrator 是会话级 Agent |
| 专业代理（ExploreAgent等） | 统一 Agent + 委托模板 |
| 复杂度路由 | 规划决策 |
| 复杂度评分 | 风险等级 |

---

_版本: 2.0_
_更新日期: 2026-03-30_
