# Agent ReAct 循环架构设计

**状态**: 已根据评审意见修订 v1.3
**日期**: 2026-04-03
**版本**: 1.3
**评审记录**:
- v1.1: 评审报告见 `2026-04-03-agent-react-architecture-review.md`
- v1.2: 合并 Reviewer 1 (P0-1~P0-5, P1-6~P1-8) 和 Reviewer 2 (4 Critical Issues, 5 Required Actions) 的反馈
- v1.3: 添加流式输出支持 (Streaming Output)，采用事件监听模式
  - P0-1: Agent.run() 添加 `_timeout_tracker.start()`
  - P0-2: Agent.run() 添加 `_token_tracker.consume()` 调用
  - P0-3: `__init__` 添加 `llm: LLMClient` 参数
  - P0-4: `orchestrator_run()` 添加 `sub_tasks: list[dict]` 参数
  - P0-5: `orchestrator_run()` 初始化 `pending_results: list[dict] = []`
  - P1-6: `_has_final_answer()` 实现真正的终止条件检查
  - P1-7: `_self_reflect()` 递增 `step_count` 防止无限循环
  - P1-8: 添加 `tools.to_llm_format()` 实现说明
  - R2-1: 重构 run() 循环，early return 前检查 `_should_terminate()`
  - R2-2: 修复 `memory_read` JSON Schema `default` 语法
  - R2-3: 补充 `spawn_mode` 语义和具体示例
  - R2-4: 状态图添加 Orchestrator 最终状态
  - R2-5: 添加错误消息流示例

---

## 1. 概述

### 1.1 核心概念

整个系统由**单一 Agent 模板**实例化出多个 Agent，每个 Agent 共享相同的 ReAct 循环实现，但通过配置实现差异化：

| 配置项 | 作用 |
|--------|------|
| System Prompt | 职责定义、行为约束、反思要求 |
| Tools | 可用工具集 |
| Output Structure | 输出格式约束 |
| Lifecycle | 生命周期策略 |

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator Agent                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  System: 任务分解、委托优先、结果聚合                          ││
│  │  Tools: create_agent, memory_read, knowledge_read           ││
│  │  Lifecycle: 会话级，运行直到会话结束                           ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                       │
│         ┌───────────────┼───────────────┐                      │
│         ▼               ▼               ▼                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ SubAgent 1  │  │ SubAgent 2  │  │ SubAgent N  │            │
│  │ ReAct Loop  │  │ ReAct Loop  │  │ ReAct Loop  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         │               │               │                      │
│         └───────────────┴───────────────┘                      │
│                          │                                       │
│              tool_result (摘要) 注入消息流                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent 模板

### 2.1 通用 ReAct 循环

```python
class Agent:
    """Agent 模板 - 通用 ReAct 循环实现"""

    # 类级别常量，限制 SubAgent 最大嵌套深度
    MAX_AGENT_DEPTH: ClassVar[int] = 1  # Orchestrator=0, SubAgent=1，不允许更深嵌套

    def __init__(
        self,
        llm: LLMClient,  # LLM 客户端实例
        system_prompt: str,
        tools: list[Tool],
        output_schema: dict,  # 输出格式约束
        lifecycle: LifecycleConfig,
        agent_depth: int = 0,  # 0=Orchestrator, 1+=SubAgent
        parent_agent_id: str | None = None,
    ):
        self.llm = llm  # P0-3: 必须通过构造函数传入，否则 NameError
        self.system_prompt = system_prompt
        self.tools = tools
        self.output_schema = output_schema
        self.lifecycle = lifecycle
        self.messages: list[Message] = []
        self.step_count = 0
        self.agent_depth = agent_depth
        self.parent_agent_id = parent_agent_id
        self.agent_id = self._generate_agent_id()
        self._token_tracker = TokenBudget(max_tokens=lifecycle.max_tokens)
        self._timeout_tracker = TimeoutTracker(timeout_seconds=lifecycle.timeout_seconds)

    async def run(self, initial_input: dict) -> dict:
        """执行 ReAct 循环"""
        # 将初始输入作为首条用户消息
        self.messages.append(Message(role="user", content=str(initial_input)))

        # P0-1: 启动超时跟踪器（必须在循环前启动，否则 is_expired() 永远返回 False）
        self._timeout_tracker.start()

        while not self._should_terminate():
            # 1. Think - LLM 生成思考和行动
            response = await self.llm.chat_complete(
                messages=self._build_messages(),
                tools=tools_to_llm_format(self.tools),  # P1-8: 见上方 tools_to_llm_format() 实现
                system=self.system_prompt,
            )

            # P0-2: 记录 token 消耗（必须调用，否则 TokenBudget 完全无效）
            self._token_tracker.consume(response.usage.total_tokens)

            # 2. 记录 Thought (显式)
            if response.content:
                self.messages.append(Message(role="assistant", content=response.content))

            # 3. 无工具调用 → 检查终止条件后再决定是否返回
            # R2-1: 防止 max_steps 超出后仍提前返回最终答案
            if not response.tool_calls:
                if self._should_terminate():
                    return self._format_final_response(None)
                return self._format_final_response(response.content)

            # 4. 执行工具调用
            for tool_call in response.tool_calls:
                result = await self._execute_tool(tool_call)
                # 注入 Observation
                self.messages.append(Message(
                    role="tool",
                    tool_results=[ToolResult(call_id=tool_call.id, output=result)]
                ))

            self.step_count += 1

            # 5. 失败检查 → 触发反思
            if self._has_errors():
                await self._self_reflect()

        return self._format_final_response(None)

    def _should_terminate(self) -> bool:
        """终止条件检查"""
        # 条件1: 达到最大步数
        if self.step_count >= self.lifecycle.max_steps:
            return True
        # 条件2: 资源耗尽
        if self._resource_exhausted():
            return True
        # 条件3: 已返回最终答案
        if self._has_final_answer():
            return True
        return False

    def _resource_exhausted(self) -> bool:
        """检查资源是否耗尽（token 预算或超时）"""
        return self._token_tracker.is_exhausted() or self._timeout_tracker.is_expired()

    def _has_errors(self) -> bool:
        """检查是否有工具执行错误

        错误判定标准：
        1. 工具抛出异常（tool_results 中有 error 字段）
        2. 工具返回 status: "error"
        """
        for msg in self.messages:
            if msg.role == "tool":
                for tool_result in msg.tool_results or []:
                    if hasattr(tool_result, 'error') and tool_result.error:
                        return True
                    output = tool_result.output
                    if isinstance(output, dict) and output.get("status") == "error":
                        return True
        return False

    def _has_final_answer(self) -> bool:
        """检查是否已返回最终答案

        检查最后一条 assistant 消息是否包含结构化的最终答案（如 subagent_summary 或 orchestrator_response）。
        若 LLM 返回了格式正确的最终答案，则终止循环。
        """
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                # 检查是否包含结构化最终答案类型
                if msg.content:
                    import json
                    try:
                        parsed = json.loads(msg.content)
                        if isinstance(parsed, dict) and parsed.get("type") in ("subagent_summary", "orchestrator_response"):
                            return True
                    except (json.JSONDecodeError, TypeError):
                        pass
                return False
        return False

    def _generate_agent_id(self) -> str:
        """生成唯一 Agent ID"""
        import uuid
        return f"agent_{uuid.uuid4().hex[:8]}"

    async def _self_reflect(self):
        """自我反思 - 仅在失败/错误时触发

        P1-7: 反思也算一步执行，必须递增 step_count 以防止无限反思循环。
        """
        self.step_count += 1  # P1-7: 必须递增，否则反思可能无限循环
        # System Prompt 中已包含反思要求
        # 此处注入反思提示到消息历史
        self.messages.append(Message(
            role="user",
            content="[Self-Reflection] 前面的步骤出现了错误或失败。"
                    "请分析问题所在，调整策略后继续执行。"
        ))

    async def run_streaming(
        self,
        initial_input: dict,
        event_emitter: EventEmitter | None = None,
    ) -> dict:
        """流式执行 ReAct 循环 - 通过事件监听器实时推送输出

        Args:
            initial_input: 初始输入
            event_emitter: 事件发射器，用于订阅流式事件。若为 None，则降级为普通 run() 行为。

        Yields:
            StreamEvent: 实时事件流
        """
        self.messages.append(Message(role="user", content=str(initial_input)))
        self._timeout_tracker.start()

        def emit_event(event_type: StreamEventType, data: Any) -> None:
            """辅助函数：发射事件"""
            if event_emitter:
                import time
                event_emitter.emit(StreamEvent(
                    event_type=event_type,
                    agent_id=self.agent_id,
                    step=self.step_count,
                    data=data,
                    timestamp=time.time(),
                ))

        while not self._should_terminate():
            # 1. Think - LLM 生成思考和行动（流式）
            response_content = ""
            tool_calls = []

            async for chunk in self.llm.chat_complete_streaming(
                messages=self._build_messages(),
                tools=tools_to_llm_format(self.tools),
                system=self.system_prompt,
            ):
                # 处理内容块
                if chunk.content:
                    response_content += chunk.content
                    emit_event(StreamEventType.THOUGHT, chunk.content)

                # 处理工具调用
                if chunk.tool_calls:
                    for tc in chunk.tool_calls:
                        if tc not in tool_calls:
                            tool_calls.append(tc)
                            emit_event(StreamEventType.TOOL_CALL_START, {
                                "tool_name": tc.name,
                                "tool_args": tc.arguments,
                            })

            # 记录 token 消耗
            if hasattr(chunk, 'usage') and chunk.usage:
                self._token_tracker.consume(chunk.usage.total_tokens)

            # 记录完整响应
            if response_content:
                self.messages.append(Message(role="assistant", content=response_content))

            emit_event(StreamEventType.STEP_COMPLETE, {"content": response_content})

            # 2. 无工具调用 → 检查终止条件后返回
            if not tool_calls:
                if self._should_terminate():
                    emit_event(StreamEventType.FINAL_RESULT, None)
                    return self._format_final_response(None)
                emit_event(StreamEventType.FINAL_RESULT, response_content)
                return self._format_final_response(response_content)

            # 3. 执行工具调用
            for tool_call in tool_calls:
                emit_event(StreamEventType.TOOL_CALL_START, {
                    "tool_name": tool_call.name,
                    "tool_args": tool_call.arguments,
                })

                result = await self._execute_tool(tool_call)

                emit_event(StreamEventType.TOOL_RESULT, result)
                self.messages.append(Message(
                    role="tool",
                    tool_results=[ToolResult(call_id=tool_call.id, output=result)]
                ))
                emit_event(StreamEventType.TOOL_CALL_END, {
                    "tool_name": tool_call.name,
                    "result": result,
                })

            self.step_count += 1

            # 4. 失败检查 → 触发反思
            if self._has_errors():
                emit_event(StreamEventType.ERROR, "Tool execution had errors")
                await self._self_reflect()
                emit_event(StreamEventType.REFLECTION, "Self-reflection triggered")

        emit_event(StreamEventType.FINAL_RESULT, None)
        return self._format_final_response(None)



def tools_to_llm_format(tools: list[Tool]) -> list[dict]:
    """将 ToolDefinition 列表转换为 LLM 所需的工具 schema 格式

    P1-8: 实现 tools.to_llm_format() — 将 ToolDefinition 转为 OpenAI/vendor 兼容的 tool schema。

    示例输入（ToolDefinition）:
        ToolDefinition(name="read_file", description="...", input_schema={...})

    示例输出（LLM tool format）:
        [{
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "...",
                "parameters": {...}
            }
        }]
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool.definition.name,
                "description": tool.definition.description,
                "parameters": tool.definition.input_schema,
            }
        }
        for tool in tools
    ]


**资源跟踪辅助类**:

```python
class TokenBudget:
    """Token 预算跟踪器"""

    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens
        self.used_tokens = 0

    def consume(self, tokens: int):
        """消耗 token"""
        self.used_tokens += tokens

    def is_exhausted(self) -> bool:
        """检查是否已耗尽"""
        return self.used_tokens >= self.max_tokens

    def remaining(self) -> int:
        """剩余可用 token"""
        return max(0, self.max_tokens - self.used_tokens)


class TimeoutTracker:
    """超时跟踪器"""

    def __init__(self, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        self.start_time: float | None = None

    def start(self):
        """启动计时"""
        import time
        self.start_time = time.monotonic()

    def is_expired(self) -> bool:
        """检查是否已超时"""
        if self.start_time is None:
            return False
        import time
        elapsed = time.monotonic() - self.start_time
        return elapsed >= self.timeout_seconds

    def reset(self):
        """重置计时器"""
        self.start_time = None
```

### 2.2 生命周期配置

```python
@dataclass
class LifecycleConfig:
    """Agent 生命周期配置"""

    max_steps: int = 20           # 最大 ReAct 步数
    max_tokens: int = 8000        # 最大 token 预算
    timeout_seconds: float = 300 # 超时时间
    auto_destroy: bool = True     # 完成时自动销毁
    spawn_mode: Literal["sync", "async"] = "async"  # spawn 模式

**spawn_mode 语义说明（R2-3 补充）**:

| 模式 | 行为 | 适用场景 | 示例 |
|------|------|----------|------|
| `"sync"` | 依次执行每个子任务，等待完成后再 spawn 下一个 | 子任务有依赖关系、需串行处理 | Orchestrator spawn coder 生成文档，再 spawn reviewer 审查（reviewer 需等文档生成） |
| `"async"` | 并行 spawn 所有子任务，`asyncio.gather()` 等待全部完成 | 子任务完全独立、无依赖 | 并行 spawn 3 个 researcher 同时分析不同模块 |

---

## 3. Agent 系统提示词模板

### 3.1 Orchestrator 系统提示词

```markdown
# Orchestrator Agent

## 角色
你是一个任务编排专家，负责分析任务、分解子任务、并通过 spawn 子 Agent 来委托执行。

## 核心职责

1. **任务分析**
   - 理解用户任务的目标和约束
   - 识别任务中的并行可能性

2. **任务分解**
   - 将复杂任务分解为可独立执行的子任务
   - 确定子任务的依赖关系和执行顺序

3. **委托执行**
   - 使用 `create_agent` 工具 spawn 合适的子 Agent
   - 为每个子 Agent 提供：
     - `task_goal`: 清晰的任务目标
     - `constraints`: 结果约束条件
     - `context`: 相关上下文信息

4. **结果聚合**
   - 收集各子 Agent 返回的摘要
   - 综合分析，形成最终结果

## 行为规则

- **只做委托**: 永远不要自己执行具体任务，只负责任务分解和结果聚合
- **并行优先**: 优先并行 spawn 多个可并行的子任务
- **工具简化**: 工具定义已在你的工具集中，`task_goal` 中无需重复工具说明
- **结构化返回**: 当不需要工具时，返回结构化 JSON 结果

## 可用工具

| 工具 | 说明 |
|------|------|
| `create_agent` | 创建子 Agent 执行特定任务 |
| `memory_read` | 从长期记忆库读取相关信息 |
| `knowledge_read` | 从知识库读取相关文档 |

## 输出格式

当任务完成（无需更多工具调用）时，返回以下 JSON 结构：

```json
{
  "type": "orchestrator_response",
  "final_result": "<综合结果描述>",
  "subtasks_completed": [
    {
      "task_goal": "<子任务目标>",
      "status": "success|partial|failed",
      "summary": "<结果摘要>"
    }
  ]
}
```

## ReAct 循环提示

你的思考过程：

```
Thought: <分析当前情况，决定下一步行动>
Action: <选择工具并执行，或返回最终结果>
Observation: <工具返回结果，注入消息历史>
```

- 每次工具调用后，等待 `tool_result` 观察结果
- 根据结果决定下一步：继续调用工具 或 返回最终答案
```

### 3.2 SubAgent 系统提示词模板

```markdown
# SubAgent

## 角色
你是一个任务执行专家，负责使用可用工具完成分配给你的具体任务。

## 核心职责

1. **任务执行**
   - 使用可用工具完成分配的任务目标
   - 记录执行过程中的思考和行动

2. **自我反思**
   - 遇到错误或失败时主动反思
   - 调整策略后重试

3. **结果摘要**
   - 完成执行后返回结构化摘要
   - 包含执行结果、步骤记录、反思总结

## 行为规则

- **使用工具**: 利用可用工具集完成任务
- **记录思考**: 在响应中明确说明你的 Thought
- **检查结果**: 每次工具调用后验证结果是否符合预期
- **错误恢复**: 遇到错误时分析原因并调整策略

## 反思机制

**触发条件**:
- 工具返回错误
- 工具执行结果与预期不符
- 步骤未能推进任务
- 达到预期结果前失败

**反思流程**:
```
1. 分析错误原因
2. 思考不同的解决策略
3. 调整方法后重试
4. 记录从错误中学到的教训
```

## 可用工具

工具集根据 `agent_type` 动态配置，可能包括：

| 工具 | 说明 |
|------|------|
| `read_file` | 读取文件内容 |
| `read_directory` | 列出目录内容 |
| `write_file` | 写入文件 |
| `execute_command` | 执行系统命令 |
| `search` | 搜索内容 |
| ... | 其他任务相关工具 |

## 输出格式

完成任务后（或达到终止条件），返回以下 JSON 结构：

```json
{
  "type": "subagent_summary",
  "status": "success|partial|failed",
  "result": "<执行结果描述>",
  "steps_taken": [
    {
      "step": <步骤序号>,
      "thought": "<思考过程>",
      "action": "<执行的行动>",
      "observation": "<观察到的结果>"
    }
  ],
  "lessons_learned": "<从反思中学到的教训（如果有）>"
}
```

## ReAct 循环提示

```
Thought: <分析当前情况，决定下一步>
Action: <选择合适的工具>
Observation: <工具返回的结果>
→ 如果失败: 进行自我反思后重试
→ 如果成功: 继续下一步或返回最终答案
```

## 终止条件

- 达到 `max_steps` 限制
- token 预算耗尽
- 已完成任务并返回结构化摘要
- 超时
```

### 3.3 系统提示词配置

| 配置项 | Orchestrator | SubAgent |
|--------|--------------|----------|
| **系统提示词** | 固定模板 | 基础模板 + 任务信息 |
| **工具集** | create_agent + 只读 | 完整工具集 |
| **生命周期** | 会话级 (auto_destroy=false) | 任务级 (auto_destroy=true) |
| **最大步数** | 50 | 20 |
| **Spawn 模式** | async | sync (等待完成) |

---

## 4. 工具定义

### 4.1 create_agent

```python
ToolDefinition(
    name="create_agent",
    description="""创建一个子 Agent 执行特定任务。
    Agent 执行完成后自动销毁，结果摘要作为工具返回。

    **注意**: SubAgent 不允许嵌套调用此工具创建更多 SubAgent。

    参数:
    - task_goal: 清晰描述的任务目标
    - agent_type: Agent 类型 (例如 "coder", "researcher", "writer")
    - constraints: 结果约束 (格式、长度、质量要求等)
    - context: 相关背景信息

    返回:
    结构化 JSON 摘要，包含执行结果和步骤
    """,
    input_schema={
        "type": "object",
        "required": ["task_goal", "agent_type"],
        "properties": {
            "task_goal": {"type": "string"},
            "agent_type": {"type": "string"},
            "constraints": {
                "type": "object",
                "properties": {
                    "format": {"type": "string"},
                    "max_length": {"type": "integer"},
                    "quality_requirements": {"type": "string"}
                }
            },
            "context": {"type": "string"}
        }
    },
    is_read_only=False,
    permission_required=PermissionLevel.REVIEW
)
```

### 4.2 上下文工具

```python
# memory_read - 读取记忆
ToolDefinition(
    name="memory_read",
    description="从长期记忆库读取相关信息",
    input_schema={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"}  # R2-2: 不在 schema 中放 default，default 由工具执行器处理
        }
    },
    is_read_only=True,
    permission_required=PermissionLevel.AUTO_ACCEPT
)

# knowledge_read - 读取知识库
ToolDefinition(
    name="knowledge_read",
    description="从知识库读取相关文档或信息",
    input_schema={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string"},
            "doc_type": {"type": "string", "enum": ["all", "docs", "specs", "code"]}
        }
    },
    is_read_only=True,
    permission_required=PermissionLevel.AUTO_ACCEPT
)
```

---

## 5. 消息流

### 5.1 Orchestrator 完整消息流

```
[User] -> "帮我分析这个代码库并生成文档"

[Orchestrator - ReAct Loop 1]
  Think: 需要先了解代码库结构，可以 spawn 一个 researcher
  Action: create_agent(task_goal="分析代码库结构", agent_type="researcher", context="...")
  Observation: Message(
    role="tool",
    tool_results=[ToolResult(
      call_id="call_abc123",
      output={
        "status": "success",
        "result": "代码库包含 3 个模块: auth, api, db",
        "steps_taken": [...]
      }
    )]
  )

[Orchestrator - ReAct Loop 2]
  Think: 已获取结构，现在 spawn coder 生成文档
  Action: create_agent(task_goal="生成 API 文档", agent_type="coder", context="代码库结构: ...")
  Observation: Message(
    role="tool",
    tool_results=[ToolResult(
      call_id="call_def456",
      output={
        "status": "success",
        "result": "API 文档已生成在 docs/api.md",
        "steps_taken": [...]
      }
    )]
  )

[Orchestrator]
  Think: 两个子任务都完成，聚合结果
  Action: 返回最终结果 (无工具调用)
  Final: {
    "type": "orchestrator_response",
    "final_result": "分析完成，文档已生成",
    "subtasks_completed": [...]
  }
```

### 5.2 SubAgent 完整消息流

```
[Orchestrator spawn] -> SubAgent

[SubAgent - ReAct Loop 1]
  System: SUBAGENT_BASE_PROMPT + 任务具体信息
  Think: 需要先读取代码库文件结构
  Action: read_directory(path="/src")
  Observation: ["auth/", "api/", "db/"]

[SubAgent - ReAct Loop 2]
  Think: 发现了 3 个目录，需要分析每个目录
  Action: read_file(path="/src/auth/README.md")
  Observation: "auth 模块提供用户认证功能..."

[SubAgent - ReAct Loop 3]
  Think: 继续分析其他模块
  Action: read_file(path="/src/api/README.md")
  Observation: "api 模块提供 REST API..."

[SubAgent]
  Think: 所有必要信息已收集
  Action: 返回最终摘要 (无工具调用)
  Final: {
    "type": "subagent_summary",
    "status": "success",
    "result": "代码库包含 3 个模块...",
    "steps_taken": [...]
  }

[自动销毁] -> tool_result 注入 Orchestrator 消息流
```

---

## 6. 终止条件

每个 Agent 的 ReAct 循环在满足以下任一条件时终止：

| 条件 | 说明 |
|------|------|
| `max_steps` 达到 | 防止无限循环 |
| 资源耗尽 | token 预算或超时 |
| 最终答案 | LLM 返回无 tool_calls 的响应 |

---

### 7.0 错误消息流示例（R2-5 补充）

以下是 Agent 系统中错误处理的完整消息流示例：

```
[SubAgent - Step 1]
  Think: 需要读取文件 /src/config.json
  Action: read_file(path="/src/config.json")
  Observation: Error: FileNotFoundError: [Errno 2] No such file or directory

[SubAgent - 错误检测]
  → _has_errors() 返回 True
  → _self_reflect() 触发：
    1. step_count += 1（防止无限循环）
    2. 注入反思消息：
       "[Self-Reflection] 前面的步骤出现了错误或失败。
        请分析问题所在，调整策略后继续执行。"

[SubAgent - Step 2]
  Think: 文件不存在，可能是路径错误。尝试 /config.json 或先读取目录
  Action: read_directory(path="/")
  Observation: ["src/", "docs/", "config.json"]

[SubAgent - Step 3]
  Think: 找到了，config.json 在根目录
  Action: read_file(path="/config.json")
  Observation: {"database": "postgresql://..."}

[SubAgent]
  Think: 成功获取配置，继续下一步
  → 返回 subagent_summary (包含 lessons_learned)
```

**错误传播**：若 SubAgent 执行失败，`spawn_subagent()` 捕获异常后返回错误结构，Orchestrator 通过 `aggregate_results()` 汇总为 `overall_status: "partial"`。

### 7.1 错误检测

### 7.1 错误检测

Agent 在以下情况触发自我反思：
- 工具返回错误
- 工具执行结果与预期不符
- 步骤未能推进任务

### 7.2 反思机制

反思通过 **System Prompt 实现**，无需单独调用：

```markdown
## 反思提示

当步骤出现错误或失败时：

1. **分析错误原因**
   - 工具返回了什么错误？
   - 预期结果是什么？
   - 实际结果是什么？

2. **思考不同策略**
   - 有其他工具可以实现同样目标吗？
   - 参数需要调整吗？
   - 是否需要先获取更多信息？

3. **调整后重试**
   - 应用新策略执行下一步
   - 验证结果是否改善

4. **记录教训**
   - 将错误原因和解决方案记录在 `lessons_learned` 字段
```

---

## 8. 实现要点

### 8.1 Agent 工厂

```python
class AgentFactory:
    """Agent 工厂 - 根据配置实例化 Agent"""

    # 嵌套深度限制
    MAX_AGENT_DEPTH: ClassVar[int] = 1  # Orchestrator=0, SubAgent=1，不允许更深嵌套

    @staticmethod
    def create(config: dict) -> Agent:
        tools = [ToolRegistry.get(name) for name in config["tools"]]
        return Agent(
            system_prompt=config["system_prompt"],
            tools=tools,
            output_schema=config["output_schema"],
            lifecycle=LifecycleConfig(**config["lifecycle"]),
            agent_depth=config.get("agent_depth", 0),
            parent_agent_id=config.get("parent_agent_id"),
        )

    @staticmethod
    def create_orchestrator() -> Agent:
        return AgentFactory.create(ORCHESTRATOR_CONFIG)

    @staticmethod
    def create_subagent(
        task_goal: str,
        agent_type: str,
        constraints: dict,
        context: str,
        parent_agent_id: str | None = None,
        parent_depth: int = 0,
    ) -> Agent:
        """创建 SubAgent

        Args:
            parent_depth: 父 Agent 的深度（Orchestrator=0）
            SubAgent 深度 = parent_depth + 1

        Raises:
            AgentNestingException: 如果深度超过 MAX_AGENT_DEPTH
        """
        subagent_depth = parent_depth + 1

        # 强制嵌套深度检查
        if subagent_depth > AgentFactory.MAX_AGENT_DEPTH:
            raise AgentNestingException(
                f"SubAgent nesting not allowed. Max depth is {AgentFactory.MAX_AGENT_DEPTH}, "
                f"attempted to create depth {subagent_depth}"
            )

        # 动态生成子 Agent 配置
        config = {
            "system_prompt": SUBAGENT_BASE_PROMPT + f"\n\n任务目标: {task_goal}\n约束: {constraints}\n上下文: {context}",
            "tools": DEFAULT_SUBAGENT_TOOLS[agent_type],  # 根据类型选择工具
            "output_schema": {"type": "subagent_summary"},
            "lifecycle": {
                "max_steps": 20,
                "auto_destroy": True,
                "spawn_mode": "sync"  # 子 agent 同步执行
            },
            "agent_depth": subagent_depth,
            "parent_agent_id": parent_agent_id,
        }
        return AgentFactory.create(config)


class AgentNestingException(Exception):
    """SubAgent 嵌套越界异常"""
    pass
```

### 8.2 并发执行

```python
async def orchestrator_run(orchestrator: Agent, input: dict, sub_tasks: list[dict]) -> dict:
    """Orchestrator 并发执行多个子任务

    Args:
        orchestrator: Orchestrator Agent 实例
        input: 初始输入
        sub_tasks: 子任务列表，每个 dict 包含 task_goal, agent_type, constraints, context
    """
    pending_tasks: list[asyncio.Task] = []
    pending_results: list[dict] = []  # P0-5: 必须初始化，否则同步模式下 append 报错
    spawn_mode = orchestrator.lifecycle.spawn_mode

    # 分析任务，并行 spawn 子任务
    for subtask in sub_tasks:
        if spawn_mode == "sync":
            # 同步模式：等待每个子任务完成再 spawn 下一个
            result = await spawn_subagent(subtask)
            pending_results.append(result)
        else:
            # 异步模式：并行 spawn 所有子任务
            task = asyncio.create_task(spawn_subagent(subtask))
            pending_tasks.append(task)

    # 等待所有子任务完成（仅 async 模式）
    if spawn_mode == "async":
        results = await asyncio.gather(*pending_tasks, return_exceptions=True)
    else:
        results = pending_results

    # 聚合结果
    return aggregate_results(results)


async def spawn_subagent(subtask: dict) -> dict:
    """Spawn 一个 SubAgent 并等待其完成

    根据 LifecycleConfig.spawn_mode 决定是同步等待还是异步执行
    """
    agent = AgentFactory.create_subagent(
        task_goal=subtask["task_goal"],
        agent_type=subtask["agent_type"],
        constraints=subtask.get("constraints", {}),
        context=subtask.get("context", ""),
        parent_agent_id=subtask.get("parent_agent_id"),
        parent_depth=subtask.get("parent_depth", 0),
    )

    # 启动超时跟踪
    agent._timeout_tracker.start()

    try:
        result = await agent.run(subtask["input"])
        return result
    finally:
        # 自动销毁
        if agent.lifecycle.auto_destroy:
            await agent.destroy()


async def aggregate_results(results: list) -> dict:
    """聚合多个 SubAgent 的执行结果"""
    # 汇总成功/失败状态
    successful = [r for r in results if not isinstance(r, Exception) and r.get("status") == "success"]
    failed = [r for r in results if isinstance(r, Exception) or r.get("status") == "failed"]

    return {
        "type": "orchestrator_response",
        "subtasks_completed": [
            {
                "task_goal": r.get("task_goal", "unknown"),
                "status": r.get("status", "unknown"),
                "summary": r.get("result", str(r))
            }
            for r in results
        ],
        "overall_status": "success" if len(failed) == 0 else "partial"
    }
```

---

## 9. 状态图

```
                    ┌─────────────────────────────────────┐
                    │            Orchestrator              │
                    │  ┌─────────────────────────────────┐ │
                    │  │     System: 编排 + 委托         │ │
                    │  │     Tools: create_agent + 只读  │ │
                    │  └─────────────────────────────────┘ │
                    │                                     │
                    │  ReAct Loop:                         │
                    │    Think → Action → Observation      │
                    │                                     │
                    │  终止条件满足 → 聚合结果 → 完成       │
                    └──────────────────┬──────────────────┘
                                       │
                    spawn(create_agent)│tool_result(摘要)
                                       ▼
                    ┌─────────────────────────────────────┐
                    │            SubAgent                 │
                    │  ┌─────────────────────────────────┐ │
                    │  │     System: 任务执行 + 反思    │ │
                    │  │     Tools: 完整工具集          │ │
                    │  └─────────────────────────────────┘ │
                    │                                     │
                    │  ReAct Loop:                        │
                    │    Think → Action → Observation     │
                    │         ↑         │                 │
                    │         └────err?─→ Self-Reflect   │
                    │                                     │
                    │  终止条件满足 → 摘要 → 自动销毁      │
                    └─────────────────────────────────────┘

  Orchestrator 最终状态: 完成（返回 orchestrator_response，auto_destroy=false 保留在内存）
  SubAgent 最终状态: 自动销毁（auto_destroy=true，摘要注入 Orchestrator 消息流）
```

### 11.5 流式输出使用示例

```python
import asyncio
from src.agent import Agent, EventEmitter, StreamEventType


async def main():
    # 创建事件发射器
    emitter = EventEmitter()

    # 定义事件处理器
    def on_thought(event):
        print(f"[Thought] {event.data}", end="", flush=True)

    def on_tool_call(event):
        print(f"\n[Tool] Calling {event.data['tool_name']} with {event.data['tool_args']}")

    def on_tool_result(event):
        print(f"[Result] {event.data}")

    def on_final_result(event):
        print(f"\n[Final] {event.data}")

    # 订阅事件
    emitter.on(StreamEventType.THOUGHT, on_thought)
    emitter.on(StreamEventType.TOOL_CALL_START, on_tool_call)
    emitter.on(StreamEventType.TOOL_RESULT, on_tool_result)
    emitter.on(StreamEventType.FINAL_RESULT, on_final_result)

    # 创建 Agent 并流式执行
    agent = AgentFactory.create_orchestrator()

    # 方式1: 使用 async for 遍历事件
    async for event in agent.run_streaming({"task": "分析代码库"}, emitter):
        pass  # 事件已在处理器中处理

    # 方式2: 直接获取最终结果（降级为非流式）
    result = await agent.run_streaming({"task": "分析代码库"}, event_emitter=None)


asyncio.run(main())
```

### 11.6 设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 事件模式 | EventEmitter + StreamEvent | 解耦事件源和订阅者，支持多订阅者 |
| 流式粒度 | token 级 (THOUGHT) + 工具调用级 | 足够细粒度，平衡实时性和可操作性 |
| 背压处理 | emit 后立即返回，不等待处理 | 避免阻塞事件流 |
| 降级策略 | event_emitter=None 时降级为 run() | 保持向后兼容 |
| 错误事件 | 独立 ERROR 事件 + 继续执行 | 不中断主循环，错误通过事件传播 |

---

## 10. 设计决策总结

| 决策点 | 选择 |
|--------|------|
| Agent 模板 | 单一模板，配置差异化 |
| Thought 记录 | 显式，消息历史中记录 |
| 反思机制 | System Prompt 实现，失败时触发 |
| 子 Agent 嵌套 | 不允许，MAX_AGENT_DEPTH=1 强制检查 |
| 嵌套深度传递 | 通过 `agent_depth` 和 `parent_agent_id` 上下文追踪 |
| Orchestrator 工具 | create_agent + 只读上下文工具 |
| 工具结果 | `Message(role="tool", tool_results=[ToolResult(...)])` 结构 |
| 摘要格式 | `subagent_summary` 结构化 JSON |
| 并发模式 | `spawn_mode: sync/async`，由 `spawn_subagent()` 实现 |
| 资源限制 | TokenBudget + TimeoutTracker 跟踪，`_resource_exhausted()` 检查 |
| 错误定义 | 工具异常 或 `status: "error"` |
| 终止条件 | max_steps OR 资源耗尽 OR 最终答案 |
| 流式输出 | `run_streaming()` + EventEmitter 事件监听模式 |
| 流式事件 | THOUGHT / TOOL_CALL_START / TOOL_RESULT / STEP_COMPLETE / FINAL_RESULT / ERROR / REFLECTION |

### 11.1 概述

当前 Agent 实现不支持流式输出，所有 LLM 响应必须等待完整生成后才能处理。添加流式输出后，用户可以在 LLM 逐 token 生成时实时获取输出，提升交互体验。

流式输出采用**事件监听模式**，通过订阅特定事件类型来接收实时更新。

### 11.2 事件类型

```python
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any


class StreamEventType(Enum):
    """流式事件类型"""
    THOUGHT = auto()          # 思考内容片段
    TOOL_CALL_START = auto()  # 工具调用开始
    TOOL_CALL_END = auto()    # 工具调用结束
    TOOL_RESULT = auto()       # 工具执行结果
    STEP_COMPLETE = auto()    # 步骤完成
    FINAL_RESULT = auto()     # 最终结果
    ERROR = auto()            # 错误发生
    REFLECTION = auto()       # 反思触发


@dataclass
class StreamEvent:
    """流式事件"""
    event_type: StreamEventType
    agent_id: str
    step: int
    data: Any  # 事件数据（类型依 event_type 而定）
    timestamp: float  # 事件时间戳


class EventEmitter:
    """简单事件发射器 - 支持事件订阅和广播"""

    def __init__(self):
        self._listeners: dict[StreamEventType, list[callable]] = {}

    def on(self, event_type: StreamEventType, callback: callable) -> None:
        """订阅事件

        Args:
            event_type: 要订阅的事件类型
            callback: 事件触发时的回调函数，签名为 (StreamEvent) -> None
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def off(self, event_type: StreamEventType, callback: callable) -> None:
        """取消订阅

        Args:
            event_type: 要取消订阅的事件类型
            callback: 之前订阅的回调函数
        """
        if event_type in self._listeners:
            self._listeners[event_type] = [
                cb for cb in self._listeners[event_type] if cb != callback
            ]

    def emit(self, event: StreamEvent) -> None:
        """发射事件

        Args:
            event: 要发射的事件
        """
        if event.event_type in self._listeners:
            for callback in self._listeners[event.event_type]:
                callback(event)

    def emit_to_all(self, event: StreamEvent) -> None:
        """发射事件到所有订阅者（包括未指定类型的全量监听者）"""
        for callbacks in self._listeners.values():
            for callback in callbacks:
                callback(event)


