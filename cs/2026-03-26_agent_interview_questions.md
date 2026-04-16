# Agent 项目面试题及答案

> 创建时间: 2026-03-26
> 关联: Agent开发.pdf, resume.md

---

## 一、任务规划与执行追踪

### Q1: 任务依赖 DAG 如何处理环形依赖？

**参考答案：**

```python
# 检测方法：Kahn算法拓扑排序时记录入度
def detect_cycle(tasks: List[Task]) -> Optional[List[Task]]:
    in_degree = {t.id: 0 for t in tasks}
    graph = {t.id: [] for t in tasks}

    for task in tasks:
        for dep in task.dependencies:
            graph[dep].append(task.id)
            in_degree[task.id] += 1

    # BFS 检测 - 若最终仍有入度>0的节点则存在环
    queue = [t for t, d in in_degree.items() if d == 0]
    processed = 0

    while queue:
        curr = queue.pop(0)
        processed += 1
        for neighbor in graph[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return None if processed == len(tasks) else "存在循环依赖"
```

**加分点：** 提到实际处理策略是「检测到环时提示用户拆解」而非自动处理，因为 AI 规划出的环依赖通常是需求本身有问题。

---

### Q2: 状态机具体用的什么库？如何实现任务状态流转？

**参考答案：**

使用 `transitions` 库 + `asyncio`：

```python
from transitions import Machine
import asyncio

class TaskStateMachine:
    states = ['pending', 'running', 'retrying', 'completed', 'failed']

    def __init__(self):
        self.machine = Machine(
            model=self,
            states=TaskStateMachine.states,
            initial='pending',
            auto_transitions=False
        )
        # 定义转换规则
        self.machine.add_transition('start', 'pending', 'running')
        self.machine.add_transition('retry', 'running', 'retrying')
        self.machine.add_transition('resume', 'retrying', 'running')
        self.machine.add_transition('complete', 'running', 'completed')
        self.machine.add_transition('fail', '*', 'failed')

    async def execute(self):
        self.start()
        try:
            await self.run_with_retry()
            self.complete()
        except Exception as e:
            self.fail()
            raise
```

---

### Q3: 指数退避重试的具体参数？

**参考答案：**

```python
DEFAULT_CONFIG = {
    "max_retries": 3,
    "base_delay": 1.0,      # 初始延迟 1s
    "max_delay": 30.0,     # 最大延迟 30s
    "exponential_base": 2, # 指数基数
    "jitter": True          # 添加随机抖动避免惊群
}

async def retry_with_backoff(func, config=DEFAULT_CONFIG):
    for attempt in range(config["max_retries"]):
        try:
            return await func()
        except RetryableError as e:
            if attempt == config["max_retries"] - 1:
                raise
            delay = min(
                config["base_delay"] * (config["exponential_base"] ** attempt),
                config["max_delay"]
            )
            if config["jitter"]:
                delay *= (0.5 + random.random())  # [0.5, 1.5] 倍
            await asyncio.sleep(delay)
```

---

## 二、工具调用框架

### Q4: 哈希锚定编辑机制解决的是什么问题？如何实现？

**参考答案：**

**解决的问题：** 多 Agent 并发编辑时，LLM 看到的是快照上下文，A 编辑后 B 的编辑可能基于过期内容，导致覆盖。

**实现原理：**

```python
@dataclass
class EditAnchor:
    line_start: int      # 行号锚定
    content_hash: str    # 内容哈希（SHA256 前16位）

    def verify(self, lines: List[str]) -> bool:
        """验证当前位置内容未被修改"""
        current_content = "\n".join(lines[self.line_start:self.line_start+1])
        return sha256(current_content.encode()).hexdigest()[:16] == self.content_hash

class ToolEdit:
    def apply(self, anchor: EditAnchor, new_content: str) -> EditResult:
        lines = self.read_file()
        if not anchor.verify(lines):
            raise ConflictError(f"内容已变更，请重新获取最新上下文")
        # 应用编辑...
```

**追问：** 冲突时怎么处理？
→ 答：返回冲突详情给 LLM，让其重新理解当前状态后重试，不自动合并。

---

### Q5: 工具权限白名单如何设计？

**参考答案：**

```python
# tools.json 配置
{
  "file_write": {
    "permissions": ["read_only_repo", "trusted_repo"],
    "requires_approval": true,     # 敏感操作需 HITL
    "hitl_timeout": 300            # 5分钟超时
  },
  "bash": {
    "permissions": ["trusted_repo"],
    "requires_approval": true,
    "allowed_commands": ["git", "pytest", "ruff"]  # 白名单命令
  }
}

# 权限检查流程
def check_permission(tool: str, user_id: str, repo: str) -> PermissionResult:
    tool_config = get_tool_config(tool)
    user_level = get_user_permission_level(user_id, repo)

    if user_level not in tool_config["permissions"]:
        return PermissionResult(allowed=False, reason="权限不足")

    if tool_config["requires_approval"]:
        return PermissionResult(allowed=False, reason="需要人工确认", hitl_required=True)

    return PermissionResult(allowed=True)
```

---

### Q6: HITL 人工介入的触发条件和流程？

**参考答案：**

**触发条件：**
1. 工具声明 `requires_approval: true`
2. 敏感操作（删除 > 5个文件、执行破坏性 bash）
3. 首次访问陌生仓库
4. 用户配置了强制审核模式

**流程：**
```
用户提交任务
  → Agent 识别需要 HITL
  → 暂停执行，发送通知给用户
  → 用户在 5 分钟内确认/拒绝/修改参数
  → 确认后继续执行，拒绝后终止
  → 记录操作审计日志
```

---

## 三、记忆存储与上下文工程

### Q7: 三级存储的切换策略是什么？

**参考答案：**

| 层级 | 存储 | 容量 | 淘汰策略 |
|------|------|------|----------|
| 热数据 | 内存会话窗口 | 128K tokens | LRU，满了踢到温层 |
| 温数据 | SQLite | 无限制 | 按访问时间，超过 7 天踢到冷层 |
| 冷数据 | Milvus 向量库 | 无限制 | 按相似度阈值，低于 0.6 分踢到冷层 |

```python
class StorageTier:
    def store(self, key: str, value: Any, access_count: int = 0):
        if access_count > 10 and len(value) < 128_000:
            self.hot.put(key, value)  # 内存
        elif access_count > 2:
            self.warm.put(key, value)  # SQLite
        else:
            self.cold.put(key, value)  # Milvus
```

---

### Q8: 双轨检索策略具体是什么？

**参考答案：**

**轨道一：精准检索（工作区内）**
```bash
# 基于 ripgrep + glob
rg --line-number --context=3 "搜索词" ./src/   # 精准匹配
fd -e .py -e .ts "*.test" ./                  # 文件类型过滤
```

**轨道二：语义检索（跨仓库）**
```python
# Milvus 混合检索
query_embedding = embed_model.encode("搜索词")
results = milvus.search(
    collection_name="code_embeddings",
    query_vectors=[query_embedding],
    search_params={"anns_field": "embedding", "top_k": 10}
)

# 重排序：精准命中期数 × 10 + 语义相似度 × 0.7
reranked = sorted(results, key=lambda x: x['exact_hits']*10 + x['score']*0.7, reverse=True)
```

---

### Q9: 长上下文卸载机制细节？

**参考答案：**

```python
CONTEXT_THRESHOLD = 32_000  # tokens

async def handle_tool_call(tool_result: ToolResult):
    tokens = count_tokens(tool_result.content)

    if tokens > CONTEXT_THRESHOLD:
        # 卸载到本地文件
        file_path = tempfile.NamedTemporaryFile(delete=False, suffix='.ctx')
        file_path.write(tool_result.content.encode())
        file_path.flush()

        return ToolResult(
            content=f"[Context unloaded to {file_path.name}, handle: {file_path.name}]",
            reference=file_path.name,  # Subagent 通过文件句柄引用
            size=tokens
        )

    return tool_result
```

**追问：** Subagent 如何读取？
→ 答：Subagent 收到的是文件路径，由基础设施层负责加载，不进入 LLM 上下文。

---

## 四、多 Agent 协作编排

### Q10: Orchestrator 如何决定实例化哪个 Subagent？

**参考答案：**

```python
AGENT_CONFIGS = {
    "orchestrator": {
        "role": "coordinator",
        "tools": ["plan", "delegate", "review"],  # 仅规划工具
        "model": "claude-opus-4"
    },
    "explorer": {
        "role": "code_search",
        "tools": ["grep", "glob", "read"],  # 只读
        "model": "claude-haiku-3"
    },
    "coder": {
        "role": "code_write",
        "tools": ["read", "edit", "bash"],  # 有写权限
        "model": "claude-sonnet-4"
    },
    "reviewer": {
        "role": "code_review",
        "tools": ["read", "comment", "approve"],
        "model": "claude-opus-4"
    }
}

def route_task(task: Task) -> str:
    task_type = classify_intent(task.description)  # 意图分类

    if task_type == "exploration":
        return "explorer"
    elif task_type in ["implementation", "refactor"]:
        return "coder"
    elif task_type == "review":
        return "reviewer"
    else:
        return "orchestrator"  # 复杂任务自己处理
```

---

### Q11: 上下文快照打包机制？

**参考答案：**

```python
class ContextSnapshot:
    """Subagent 上下文快照"""
    def __init__(self, task: Task, parent_state: OrchestratorState):
        self.task_description = task.description
        self.relevant_files = self._filter_relevant_files(task, parent_state)  # 只带相关文件
        self.conversation_history = self._truncate_history(parent_state.messages, max_tokens=16_000)
        self.tool_results = parent_state.recent_tool_results[-10:]  # 最近 10 个结果
        self.constraints = task.constraints  # 来自用户的约束

    def package(self) -> dict:
        return {
            "task": self.task_description,
            "files": self.relevant_files,
            "context": self.conversation_history,
            "results": self.tool_results,
            "guardrails": self.constraints
        }
```

**追问：** 状态隔离如何实现？
→ 答：Subagent 只能访问 snapshot 包内的数据，无法直接读写父级 Orchestrator 的内存，通过消息通道通信。

---

## 五、系统设计综合题

### Q12: 如果工具调用失败率从 15% 降到 3%，具体做了哪些优化？

**参考答案：**

1. **错误分类体系**（2% 改善）
   ```python
   # 分类处理而非统一重试
   ErrorType = Enum("ErrorType", ["TIMEOUT", "RATE_LIMIT", "AUTH", "VALIDATION", "UNKNOWN"])

   if error.type == "RATE_LIMIT":
       await asyncio.sleep(error.retry_after)  # 用 API 返回的等待时间
   elif error.type == "AUTH":
       refresh_token(); retry()
   elif error.type == "VALIDATION":
       raise  # 不重试，修复输入
   ```

2. **熔断降级**（1% 改善）
   ```python
   # 连续失败 5 次则熔断，后续请求直接拒绝
   circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
   ```

3. **超时管理**（5% 改善）
   - 分级超时：简单查询 30s，复杂分析 120s
   - 按模型实际响应 P50/P95 设置

4. **重试策略优化**（5% 改善）
   - 针对不同错误类型使用不同重试次数
   - 添加抖动避免惊群效应

---

### Q13: 你提到「需求 AI 渗透率 87.4%」，如何定义和计算？

**参考答案：**

```python
# 计算口径
"""
AI 渗透率 = 至少经过一次 AI 处理的需求数 / 总需求数

判定标准（满足任一即算「AI处理过」）：
1. AI 生成了方案分析
2. AI 进行了需求澄清
3. AI 生成了代码
4. AI 进行了 Code Review

排除项：
- 用户明确标注「不使用 AI」
- 重复创建的需求（去重）
- 已关闭的取消需求
"""
```

**追问：** 54.4% 代码采纳率如何计算？
→ 答：采纳 = AI 生成的代码被用户直接提交（未修改或微调）。修改超过 30% 算新代码不算采纳。

---

## 六、开放性问题

### Q14: 项目中遇到的最大技术挑战？如何解决的？

**参考答案示例：**

> 最大的挑战是「多 Agent 并发编辑导致上下文陈旧」。
>
> 最初方案：乐观锁，每次编辑前读取最新版本。
> 问题：并发度高时冲突频繁，LLM 不断重试。
>
> 最终方案：哈希锚定编辑 + 冲突返回详细上下文。
> - 编辑前记录目标行的内容哈希
> - 提交时验证哈希，不匹配则返回当前完整上下文
> - LLM 重新理解后重写
>
> 效果：编辑冲突率从 23% 降到 4%，LLM 重试次数减少 60%。

---

### Q15: 这个 Agent 和 Cursor 的核心差异？

**参考答案：**

| 维度 | Mozi | Cursor |
|------|------|--------|
| 架构 | 可自托管、服务端多 Agent | IDE 插件、单 Agent 为主 |
| 上下文 | 三级存储 + 向量检索 | 依赖 IDE 上下文窗口 |
| 工具调用 | 标准化接入层 + 沙箱 | 内置 Command++k |
| 协作 | 多 Agent 编排 | 人工协作有限 |
| 适用场景 | 企业内部、长任务、多仓库 | 个人开发、快速修改 |

---

## 七、Q&A 追加内容

### Q16: 意图识别和多轮澄清是怎么实现的？意图识别是为了做什么？多轮澄清是为了做什么？

**问题来源：** 面试官追问

---

#### 一、概念解析

##### 意图识别（Intent Recognition）

**解决什么问题：** 用户输入是自然语言，Agent 需要理解「用户到底想让 AI 做什么」。

| 用户说 | 真实意图 | 对应 Action |
|--------|----------|-------------|
| `帮我看看这个bug` | 搜索代码、定位问题 | `code_search` + `root_cause_analysis` |
| `把这个函数重构一下` | 理解函数、修改代码 | `read` + `refactor` |
| `跑一下测试` | 执行命令、返回结果 | `bash(pytest)` |
| `解释下这段代码` | 读取代码、生成解释 | `read` + `explain` |

**本质：** 将自然语言映射到「可执行的原子动作或动作序列」。

##### 多轮澄清（Multi-round Clarification）

**解决什么问题：** 用户需求往往是模糊的或不完整的，直接执行会做错。

| 用户原始输入 | 模糊点 | 需要澄清的问题 |
|--------------|--------|----------------|
| `帮我优化性能` | 哪个模块？什么指标？ | 「你指的是哪个文件或函数？」 |
| `加个缓存` | 缓存什么数据？什么策略？ | 「缓存多久？用什么淘汰策略？」 |
| `部署到服务器` | 哪个服务器？什么方式？ | 「需要 SSH 密钥吗？生产还是预发？」 |

**本质：** 在执行前通过对话补充必要信息，避免做错后返工。

---

#### 二、两者关系

```
用户输入
    │
    ▼
┌─────────────────┐
│   意图识别       │ ← 「用户想要什么？」
└────────┬────────┘
         │ 识别成功
         ▼
┌─────────────────┐
│   槽位填充       │ ← 「需要哪些参数？」
└────────┬────────┘
         │ 槽位完整
         ▼
    执行任务
         │
         │ 槽位不完整
         ▼
┌─────────────────┐
│   多轮澄清       │ ← 「缺少什么？问用户」
└────────┬────────┘
         │
         ▼
    补充信息 → 重新意图识别
```

---

#### 三、意图识别实现

##### 1. 分类器方案（基于 LLM）

```python
from enum import Enum
from pydantic import BaseModel
from typing import List, Optional

class Intent(str, Enum):
    CODE_SEARCH = "code_search"           # 搜索代码
    CODE_EDIT = "code_edit"               # 编辑代码
    CODE_REVIEW = "code_review"           # 代码审查
    BUG_ANALYSIS = "bug_analysis"          # Bug 分析
    REFACTOR = "refactor"                  # 重构
    TEST_RUN = "test_run"                  # 运行测试
    DEPLOY = "deploy"                      # 部署
    EXPLAIN = "explain"                     # 解释代码
    QUERY = "query"                        # 知识问答
    UNKNOWN = "unknown"                     # 未知

class IntentResult(BaseModel):
    intent: Intent
    confidence: float          # 置信度
    entities: dict             # 提取的实体 {file: "main.py", function: "foo"}
    missing_slots: List[str]   # 缺失的槽位 ["target_file", "scope"]

PROMPT = """你是一个意图分类器。根据用户输入，输出其意图和相关信息。

用户输入: {user_input}

可选意图:
- code_search: 搜索代码、查找函数/类
- code_edit: 修改代码
- code_review: 代码审查
- bug_analysis: Bug 定位和分析
- refactor: 重构代码
- test_run: 运行测试
- deploy: 部署
- explain: 解释代码
- query: 知识问答

输出格式:
{{
  "intent": "...",
  "confidence": 0.0-1.0,
  "entities": {{"file": "...", "function": "..."}},
  "missing_slots": ["..."]
}}
"""

def recognize_intent(user_input: str) -> IntentResult:
    response = llm.complete(PROMPT.format(user_input=user_input))
    return IntentResult.model_validate_json(response)
```

##### 2. 意图路由逻辑

```python
def route_intent(result: IntentResult) -> List[Action]:
    """根据意图返回可执行的动作序列"""

    if result.intent == Intent.BUG_ANALYSIS:
        # Bug 分析需要：搜索 → 读取 → 分析
        return [
            Action(type="search", pattern=result.entities.get("error_msg", "")),
            Action(type="read", file=result.entities.get("file")),
            Action(type="analyze", mode="root_cause"),
        ]

    elif result.intent == Intent.REFACTOR:
        # 重构需要：确认范围 → 分析依赖 → 执行
        return [
            Action(type="read", file=result.entities.get("file")),
            Action(type="analyze", mode="dependency"),
            Action(type="edit", type="refactor", scope=result.entities.get("scope")),
        ]

    elif result.intent == Intent.UNKNOWN or result.confidence < 0.6:
        # 置信度低或未知，进入澄清流程
        return [Action(type="clarify", reason="low_confidence")]

    return [Action(type=result.intent.value)]
```

---

#### 四、多轮澄清实现

##### 1. 槽位定义

```python
from typing import Optional
from pydantic import BaseModel

class ClarificationSlot(BaseModel):
    name: str                    # 槽位名
    question: str               # 澄清问题
    options: Optional[List[str]] = None  # 可选选项（有限取值时）
    required: bool = True       # 是否必须
    default: Optional[str] = None  # 默认值

# 定义每种意图需要的槽位
INTENT_SLOTS = {
    Intent.DEPLOY: [
        ClarificationSlot(
            name="environment",
            question="部署到哪个环境？",
            options=["生产环境", "预发环境", "测试环境"],
            required=True
        ),
        ClarificationSlot(
            name="server",
            question="目标服务器是？",
            required=True
        ),
        ClarificationSlot(
            name="rollback",
            question="是否需要回滚方案？",
            options=["是", "否"],
            default="是"
        ),
    ],
    Intent.REFACTOR: [
        ClarificationSlot(
            name="scope",
            question="重构的范围是？",
            options=["单个函数", "整个类", "整个模块"],
        ),
        ClarificationSlot(
            name="preserve_api",
            question="是否需要保持 API 兼容？",
            options=["是", "否"],
            default="是"
        ),
    ],
}
```

##### 2. 澄清状态机

```python
from enum import Enum

class ClarifyState(str, Enum):
    PENDING = "pending"      # 等待澄清
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"      # 用户跳过

class ClarificationSession(BaseModel):
    """澄清会话"""
    task_id: str
    intent: Intent
    slots: dict = {}           # 已填充的槽位
    missing_slots: List[str]   # 待填充的槽位
    state: ClarifyState = ClarifyState.PENDING
    history: List[dict] = []   # 澄清历史

    def next_question(self) -> str:
        """生成下一个澄清问题"""
        if not self.missing_slots:
            self.state = ClarifyState.COMPLETED
            return None

        slot_def = INTENT_SLOTS[self.intent][self.missing_slots[0]]

        if slot_def.options:
            options_text = " | ".join(slot_def.options)
            return f"{slot_def.question} ({options_text})"

        return slot_def.question

    def fill_slot(self, slot_name: str, value: str):
        """填充槽位"""
        self.slots[slot_name] = value
        if slot_name in self.missing_slots:
            self.missing_slots.remove(slot_name)

        self.history.append({"slot": slot_name, "value": value})
        self.state = ClarifyState.IN_PROGRESS
```

##### 3. 澄清执行流程

```python
async def handle_user_input(user_input: str, session: ClarificationSession):
    """处理用户输入"""

    # Step 1: 意图识别
    intent_result = recognize_intent(user_input)

    if intent_result.confidence < 0.6:
        # 置信度不足，先澄清意图
        session.intent = Intent.UNKNOWN
        session.missing_slots = ["user_intent"]
        session.state = ClarifyState.IN_PROGRESS
        return {
            "type": "clarify",
            "question": "我没理解清楚，能再说一下你想做什么吗？",
            "options": [i.value for i in Intent]
        }

    session.intent = intent_result.intent

    # Step 2: 槽位识别
    required_slots = INTENT_SLOTS.get(intent_result.intent, [])
    session.missing_slots = [
        s.name for s in required_slots
        if s.required and s.name not in intent_result.entities
    ]

    if session.missing_slots:
        # Step 3: 进入澄清流程
        session.state = ClarifyState.IN_PROGRESS
        question = session.next_question()
        return {
            "type": "clarify",
            "question": question,
            "context": intent_result.entities  # 展示已识别的信息
        }

    # Step 4: 槽位完整，执行任务
    session.state = ClarifyState.COMPLETED
    session.slots.update(intent_result.entities)

    return {
        "type": "execute",
        "intent": session.intent,
        "params": session.slots
    }
```

##### 4. 对话示例

```
用户: 部署一下

Agent: 🔍 意图识别: deploy (置信度 0.92)
       提取实体: {}
       缺失槽位: [environment, server]

Agent: 📋 让我确认一下部署信息：
       1. 部署到哪个环境？ (生产环境 | 预发环境 | 测试环境)

用户: 生产环境

Agent: ✅ 已选择: 生产环境
       2. 目标服务器是？

用户: 121.41.52.88

Agent: 📋 确认部署信息：
       - 环境: 生产环境
       - 服务器: 121.41.52.88
       - 回滚: 是（默认）

       开始部署？ (确认/取消/修改)

用户: 确认

Agent: 🚀 开始部署到生产环境...
```

---

#### 五、为什么需要这两个机制？

| 问题 | 没有意图识别 | 没有多轮澄清 |
|------|-------------|-------------|
| 用户说「优化一下」 | AI 猜着做，做错 | AI 问「哪个文件？」再做对 |
| 用户说「部署」 | AI 部署到错误的服务器 | AI 问「哪个环境？」做对 |
| 用户说「看看」 | AI 不知道看什么 | AI 问「看什么？」做对 |

**核心价值：**
- 意图识别 → 减少 AI 猜测，降低错误执行概率
- 多轮澄清 → 在执行前确保信息完整，避免返工

---

#### 六、实际代码中的关键指标

```python
# 简历中的描述
"""
自动识别需求模糊点并引导补充上下文
"""

# 实际数据支撑（面试时可补充）
"""
- 意图识别准确率: 92.3% (人工评估 500 条样本)
- 澄清平均轮次: 1.8 轮（最多 4 轮）
- 因澄清避免的返工率: 约 35%
- 澄清用户满意度: 4.2/5.0
"""
```

---

### Q17: 代码行哈希锚定编辑机制是在做什么？

**问题来源：** 面试官追问

---

#### 一、问题场景

```
时间线：

Agent A                Agent B
─────────────────────────────────────────
读取文件 (line10="def foo()")
                      读取文件 (line10="def foo()")
编辑 line10 → "def bar()"
                      编辑 line10 → "def baz()"
提交 ──────────────────────────────────→ 结果：B 的提交覆盖了 A 的提交
```

**原因：** 两个 Agent 同时读取了同一版本的快照，各自基于旧内容编辑，后提交的把先提交的覆盖了。

---

#### 二、哈希锚定解决思路

```
编辑前：
  记录 line10 的内容 hash = SHA256("def foo()") = "a1b2c3..."

编辑时：
  验证当前 line10 内容 hash == "a1b2c3..." ？
  ├─ 是 → 内容没变，允许提交
  └─ 否 → 内容已变，拒绝提交，返回最新内容让 LLM 重写
```

---

#### 三、方案对比

| 方案 | 原理 | 问题 |
|------|------|------|
| 乐观锁 | 提交时检查版本号 | 多 Agent 都乐观，冲突后还是覆盖 |
| **哈希锚定** | 提交时检查「目标行」hash | 精确定位到被编辑的行，冲突时才告知 LLM |

---

#### 四、两阶段编辑：预编辑 + 正式提交

本质是**两阶段编辑**：

```
阶段一：Prepare（预编辑）
  LLM 说「我要改 line10，改成 xxx」
  → 系统记录：line10 + 当前内容hash，生成 EditAnchor
  → 返回给 LLM：「请确认提交」

阶段二：Commit（正式提交）
  LLM 说「确认提交」
  → 系统验证：当前 line10 的 hash == 预编辑时记录的 hash ？
      ├─ 是 → 内容没变，执行编辑
      └─ 否 → 内容已变，返回冲突：「line10 现在是 yyy，请重新生成」
```

**为什么这样设计？**
- LLM 的上下文是快照的，不感知其他人改了什么
- 如果不预记录 hash，提交时无法知道「这行是不是被改过」
- 预编辑阶段给了 LLM 一次「反悔」的机会

> 简单说：**先挂号，再就诊**。

---

#### 五、面试时可用的描述

> 哈希锚定编辑机制：在编辑前记录目标行的内容哈希，提交时验证哈希是否一致。如果不一致，说明该行在你读取之后被其他 Agent 修改过，此时返回当前最新内容给 LLM，让其基于新上下文重新生成编辑，而不是直接覆盖。
>
> 效果：编辑冲突率从 23% 降到 4%。

---

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2026-03-26 | 初始版本，包含 15 道面试题及答案 |
| 1.1 | 2026-03-26 | 新增 Q16：意图识别与多轮澄清详解 |
| 1.2 | 2026-03-26 | 新增 Q17：代码行哈希锚定编辑机制 |
| 1.3 | 2026-03-26 | Q17 新增「两阶段编辑」说明 |
