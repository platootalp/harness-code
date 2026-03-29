# Orchestrator 编排器设计文档

## 1. 概述

### 1.1 核心定位

Orchestrator 是 Mozi 的**控制平面**，位于委托层级顶端。它的职责是：

> 拦截用户消息 → 理解任务 → 委托子代理 → 验证结果

**不是**：直接执行任务、管理文件、调用工具

### 1.2 设计参考

参考 [Sisyphus 编排器](https://zread.ai/code-yeongyu/oh-my-opencode/10-sisyphus-the-orchestrator-agent) 的设计理念：
- 五阶段工作流
- 委托给专业子代理
- NO EVIDENCE = NOT COMPLETE
- 失败恢复机制

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| 自适应流程 | 根据任务特征动态决定是否需要某些阶段 |
| 结构化委托 | 用模板约束子代理行为 |
| 智能恢复 | 分类失败 → 策略重试 → 必要时咨询 Oracle |
| 混合验证 | 自动验证 + 用户确认 |

---

## 2. 四阶段流程

```
┌─────────────────────────────────────────────────────────────┐
│                        用户消息                               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段1: 意图理解 (Intent Understanding)        【必须】       │
│  - 解析用户输入为 TaskSpec                                   │
│  - 提取目标、实体、约束、风险等级                              │
│  - 判断是否需要澄清                                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段2: 探索 (Exploration)                      【自适应】     │
│  - 如果任务涉及未知代码/项目结构 → 委托 ExploreAgent          │
│  - 如果任务目标明确 → 跳过此阶段                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段3: 实现 (Implementation)                  【必须】       │
│  - 委托 ExecutorAgent，带结构化模板                          │
│  - TASK / EXPECTED OUTCOME / MUST DO / MUST NOT DO          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  阶段4: 验证 (Verification)                   【必须】        │
│  - 证据收集：修改的文件、执行的命令、输出结果                  │
│  - 用户确认：展示结果，用户确认是否完成                        │
│  - 失败 → 触发智能恢复                                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        返回结果                               │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 阶段1: 意图理解

解析用户输入为 TaskSpec，不做意图分类。

```python
class TaskSpec(BaseModel):
    """任务规约"""
    goal: str                           # 用户目标（原文）
    entities: dict[str, str]            # 实体：{file: "auth.py", func: "validate"}
    constraints: list[str]               # 约束条件
    risk_level: RiskLevel               # LOW / MEDIUM / HIGH
    requires_exploration: bool          # 是否需要探索（初步判断）
    requires_clarification: bool        # 是否需要澄清
    clarification_questions: list[str]   # 澄清问题


class RiskLevel(Enum):
    LOW = "low"      # 只读操作
    MEDIUM = "medium"  # 修改文件
    HIGH = "high"    # 删除、批量操作
```

### 2.2 阶段2: 探索（自适应）

是否需要探索由 TaskSpec 解析阶段由 LLM 直接判断，不是关键词匹配。

**判断依据**（LLM 解析时直接输出）：

| 判断 | requires_exploration = True | requires_exploration = False |
|------|----------------------------|------------------------------|
| 目标明确性 | 任务涉及未知代码/项目结构 | 用户指定了明确的目标 |
| 实体完整性 | 实体不完整，需要先了解 | 实体完整，无需额外探索 |
| 上下文依赖 | 需要先了解代码库才能执行 | 可以直接执行 |

**示例**：

| 用户输入 | requires_exploration |
|----------|---------------------|
| "帮我写一个快速排序" | False（目标明确，无需探索） |
| "检查 auth.py 里的 validate 函数" | False（目标文件明确） |
| "帮我看看这个项目用了什么技术栈" | True（涉及未知代码库结构） |
| "在项目里搜索所有用到 auth 的地方" | False（搜索工具可以直接执行） |
| "帮我优化一下性能" | True（目标不明确，需要先探索） |

**TaskSpec 解析 Prompt**：

```
解析用户输入，提取任务规约：

goal: 用户目标（原文）
entities: 提取的实体 {file, func, language, ...}
constraints: 约束条件
risk_level: LOW / MEDIUM / HIGH

requires_exploration: 是否需要探索代码库才能执行？
- 如果任务涉及"项目结构"、"技术栈"、"未知代码" → True
- 如果用户指定了明确的目标文件/函数，且不需要了解额外上下文 → False

requires_clarification: 是否需要澄清？
- 如果目标不明确、实体不完整 → True
```

### 2.3 阶段3: 实现

委托 ExecutorAgent，带结构化模板。

### 2.4 阶段4: 验证

证据收集 + 自动验证 + 用户确认。

---

## 3. 代理体系

### 3.1 代理架构（混合模式）

```
                    ┌──────────────────┐
                    │  Orchestrator    │
                    │  （编排器）       │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
   ┌────────────┐    ┌────────────┐    ┌────────────┐
   │  Explore   │    │  Executor  │    │   Oracle   │
   │   Agent    │    │   Agent    │    │   Agent    │
   │  (专业)    │    │  (专业)    │    │  (专业)    │
   └────────────┘    └────────────┘    └────────────┘
```

### 3.2 专业代理

| 代理 | 职责 | 使用场景 |
|------|------|----------|
| **ExploreAgent** | 搜索、探索代码库 | 任务涉及未知代码/项目结构 |
| **ExecutorAgent** | 执行具体任务 | 任务目标明确，需要修改/生成代码 |
| **OracleAgent** | 咨询、反思、诊断 | 失败后需要分析原因 |

### 3.3 通用 Agent

- **行为由模板决定**：TASK / EXPECTED OUTCOME / MUST DO / MUST NOT DO
- **无状态**：每次委托都是新实例
- **通过 EventBus 通信**

---

## 4. 委托协议

### 4.1 委托模板

```python
class DelegationTemplate(BaseModel):
    """委托模板"""
    task: str                    # 任务描述
    expected_outcome: str         # 期望结果
    must_do: list[str]           # 必须做的事
    must_not_do: list[str]       # 禁止做的事
    context: dict                # 额外上下文
```

### 4.2 委托示例

```
委托给 ExploreAgent:
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

---

### 4.3 澄清流程

```
用户输入
    │
    ▼
TaskSpec 解析
    │
    ├──► requires_clarification = False ──► 继续下一阶段
    │
    └──► requires_clarification = True
              │
              ▼
         发送澄清问题给用户
              │
              ▼
         等待用户回复（最多2次）
              │
              ▼
         更新 TaskSpec.entities
              │
              ├──► 仍需澄清 ──► 再次发送问题
              │
              └──► 澄清完成 ──► 继续下一阶段
```

**澄清接口**：

```python
class ClarificationManager:
    """澄清管理器"""

    async def ask(
        self,
        session_id: str,
        questions: list[str],
    ) -> None:
        """
        向用户发送澄清问题
        """

    async def process_answers(
        self,
        session_id: str,
        answers: dict[str, str],
    ) -> TaskSpec:
        """
        处理用户澄清回复，更新 TaskSpec
        - 最多澄清 2 次
        - 超过则停止，请求用户重新描述任务
        """
```

---

## 5. 智能恢复机制

### 5.1 失败分类

```python
class FailureType(Enum):
    """失败类型"""
    EXECUTION_ERROR = "execution_error"     # 执行错误（代码异常）
    VERIFICATION_ERROR = "verification_error" # 验证错误（结果不符合预期）
    TIMEOUT_ERROR = "timeout_error"         # 超时错误
    INTENT_ERROR = "intent_error"            # 意图理解错误
```

### 5.2 恢复策略

| 失败类型 | 策略1 | 策略2 |
|----------|-------|-------|
| EXECUTION_ERROR | 重试（最多2次） | Oracle 分析 |
| VERIFICATION_ERROR | 修改后重试（最多1次） | 请求澄清 |
| TIMEOUT_ERROR | 重试（最多1次） | 拆分任务 |
| INTENT_ERROR | 请求澄清（最多2次） | 停止 |

### 5.3 恢复流程

```
执行失败
    │
    ▼
分析失败类型
    │
    ├──► EXECUTION_ERROR ──► 重试（最多2次）
    │                              │
    │                              ├──► 成功 ──► 继续
    │                              └──► 仍失败 ──► Oracle 分析
    │
    ├──► VERIFICATION_ERROR ──► 委托 ExecutorAgent 修改（最多1次）
    │                                │  Orchestrator 提供失败原因和期望
    │                                ├──► 成功 ──► 继续
    │                                └──► 仍失败 ──► 请求澄清
    │
    ├──► TIMEOUT_ERROR ──► 重试（最多1次）
    │                          │
    │                          ├──► 成功 ──► 继续
    │                          └──► 仍失败 ──► 拆分任务
    │
    └──► INTENT_ERROR ──► 请求澄清（最多2次）
                              │
                              ├──► 成功 ──► 重新执行
                              └──► 仍失败 ──► 停止，报告用户
```

### 5.4 回滚机制

回滚用于高风险操作前的安全保护。

**检查点格式**：

```python
class Checkpoint(BaseModel):
    """检查点"""
    id: str
    session_id: str
    created_at: datetime
    files: dict[str, str]  # file_path -> content hash (SHA256)
```

**回滚策略**：

| 风险等级 | 检查点时机 | 回滚粒度 |
|----------|------------|----------|
| LOW | 不需要 | - |
| MEDIUM | 执行前 | 仅修改的文件 |
| HIGH | 执行前 | 所有相关文件 |

**回滚管理器**：

```python
class RollbackManager:
    """回滚管理器"""

    async def save_checkpoint(
        self,
        session_id: str,
        files: list[str],
    ) -> str:
        """
        保存检查点
        - 对指定文件计算 hash 并记录
        - 返回 checkpoint_id
        """
        checkpoint_id = generate_uuid()
        file_hashes = {
            f: compute_file_hash(f) for f in files
        }
        await self.storage.save(checkpoint_id, Checkpoint(
            id=checkpoint_id,
            session_id=session_id,
            created_at=datetime.now(),
            files=file_hashes,
        ))
        return checkpoint_id

    async def rollback(self, checkpoint_id: str) -> list[str]:
        """
        回滚到检查点
        - 对比当前文件 hash 与检查点
        - 恢复不一致的文件
        - 返回恢复的文件列表
        """
        checkpoint = await self.storage.load(checkpoint_id)
        restored = []
        for path, expected_hash in checkpoint.files.items():
            current_hash = compute_file_hash(path)
            if current_hash != expected_hash:
                # 从 Git 或备份恢复文件
                await self.restore_file(path)
                restored.append(path)
        return restored

    async def cleanup(self, checkpoint_id: str) -> None:
        """清理检查点"""
        await self.storage.delete(checkpoint_id)
```

---

## 6. 验证机制

### 6.1 验证职责划分

| 验证类型 | 执行者 | 说明 |
|----------|--------|------|
| 自验证 | ExecutorAgent | 执行过程中进行语法检查、lint、测试 |
| 证据收集 | ExecutorAgent | 收集修改的文件、执行的命令等证据 |
| 结果确认 | Orchestrator | 验证阶段展示证据，用户确认 |
| 用户确认 | 用户 | 最终确认任务是否完成 |

### 6.2 验证流程

```
执行完成（ExecutorAgent）
    │
    ▼
┌─────────────────────────────────────┐
│ ExecutorAgent 自验证（执行中）         │
│ - 语法检查                           │
│ - lint 检查                          │
│ - 测试验证（如果有）                   │
└─────────────────────────────────────┘
    │
    ▼
收集证据（ExecutorAgent）
    │
    ├──► 修改的文件列表
    ├──► 执行的操作列表
    ├──► 自验证结果
    └──► 相关日志
    │
    ▼
展示证据（Orchestrator）
    │
    ├──► 展示证据和自验证结果
    ├──► 询问："任务完成了吗？"
    └──► 用户确认 / 拒绝
    │
    ├──► 确认 ──► 成功返回
    └──► 拒绝 ──► 进入智能恢复（VERIFICATION_ERROR）
```

### 6.3 证据收集

```python
class EvidenceCollector:
    """证据收集器"""

    async def collect(self, execution_result: dict) -> dict:
        """收集执行证据"""
        return {
            "files_read": execution_result.get("files_read", []),
            "files_modified": execution_result.get("files_modified", []),
            "files_created": execution_result.get("files_created", []),
            "commands_executed": execution_result.get("commands", []),
            "output": execution_result.get("output", ""),
            "model_messages": execution_result.get("messages", []),
        }
```

### 6.4 验证模板

```
任务: {task}
期望结果: {expected_outcome}

执行证据:
- 修改的文件: {files_modified}
- 执行的命令: {commands}
- 输出: {output}

请验证:
1. 任务是否完成？
2. 结果是否符合期望？
3. 是否有遗留问题？

回复格式:
- 完成: YES/NO
- 原因: <简短说明>
- 遗留问题: <如有>
```

---

## 7. 超时配置

### 7.1 超时配置项

```python
class OrchestratorConfig(BaseModel):
    """编排器配置"""

    # 各阶段超时（秒）
    intent_timeout_seconds: int = 30
    exploration_timeout_seconds: int = 60
    execution_timeout_seconds: int = 300
    verification_timeout_seconds: int = 60

    # 澄清配置
    clarification_max_retries: int = 2
    clarification_timeout_seconds: int = 300

    # 恢复配置
    execution_max_retries: int = 2
    verification_max_retries: int = 1

    # 会话配置
    max_session_minutes: int = 30
```

### 7.2 默认超时值

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| intent_timeout_seconds | 30s | 意图理解阶段 |
| exploration_timeout_seconds | 60s | 探索阶段 |
| execution_timeout_seconds | 300s | 执行阶段 |
| verification_timeout_seconds | 60s | 验证阶段 |
| clarification_max_retries | 2 | 最大澄清次数 |
| max_session_minutes | 30min | 会话最大时长 |

---

## 8. 接口设计

### 10.1 核心数据模型

```python
class VerificationResult(BaseModel):
    """验证结果"""
    success: bool
    evidence: dict[str, Any]           # 证据
    auto_verified: bool                 # 是否通过自动验证
    user_confirmed: bool                # 用户是否确认
    issues: list[str]                   # 发现的问题


class OrchestrationResult(BaseModel):
    """编排结果"""
    success: bool
    task_spec: TaskSpec
    exploration_result: Optional[dict]  # 探索结果（如有）
    execution_result: Optional[dict]    # 执行结果（如有）
    verification: VerificationResult
    error: Optional[str]
```

### 10.2 核心接口

```python
class Orchestrator(ABC):
    """编排器接口"""

    async def process(
        self,
        user_input: str,
        session_id: str,
    ) -> OrchestrationResult:
        """
        处理用户输入，执行自适应四阶段流程
        """

    async def clarify(
        self,
        session_id: str,
        answers: dict[str, str],
    ) -> OrchestrationResult:
        """
        处理澄清回复
        """


class Agent(ABC):
    """代理接口"""

    async def execute(
        self,
        template: DelegationTemplate,
        context: dict,
    ) -> dict:
        """
        执行委托任务
        """
```

---

## 9. 模块结构

```
mozi/orchestrator/
    __init__.py
    orchestrator.py              # 主编排器入口
    agent/
        __init__.py
        base.py                  # Agent 基类定义
        explore.py               # ExploreAgent
        executor.py              # ExecutorAgent
        oracle.py                # OracleAgent
    core/
        __init__.py
        task_spec.py             # 任务规约解析器
        explorer.py              # 探索决策器
        recovery.py              # 智能恢复管理器
        verifier.py              # 验证器
    session/
        __init__.py
        manager.py               # 会话管理器
        context.py               # 上下文构建器
        rollback.py             # 回滚管理器
```

---

## 10. 事件流

```
user_message ──► Orchestrator.process()
                        │
                        ▼
                   TaskSpec 解析
                        │
                        ├──► requires_clarification ──► 澄清循环
                        │
                        ▼
                   阶段1完成: 意图理解
                        │
                        ▼
                   should_explore() ──► True ──► ExploreAgent
                        │                              │
                        │                              ▼
                        │                         探索结果
                        │                              │
                        ▼                              │
                   阶段2完成: 探索                      │
                        │                              │
                        ▼                              │
                   ExecutorAgent                       │
                        │                              │
                        ▼                              │
                   阶段3完成: 实现                      │
                        │                              │
                        ▼                              │
                   验证结果 + 用户确认                   │
                        │                              │
                        ▼                              │
                   成功/失败 ──► 失败 ──► OracleAgent
                                              │
                                              ▼
                                         智能恢复
```

---

## 11. 与旧设计对比

| 旧设计 | 新设计 |
|--------|--------|
| 意图分类（穷举枚举） | 任务规约（不做分类） |
| 复杂度路由（SIMPLE/MEDIUM/COMPLEX） | 自适应阶段（是否需要探索） |
| 复杂度评分（固定阈值 40/70） | 风险等级（LOW/MEDIUM/HIGH） |
| 意图识别器 | 任务规约解析器 |
| 路由决策器 | 探索决策器 + 委托协议 |

---

_版本: 1.2_
_更新日期: 2026-03-29_
_设计参考: Sisyphus Orchestrator (oh-my-opencode)_
