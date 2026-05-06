# 自学习循环设计

> 通过后台学习服务，将 Hermes 风格的运行时自改进能力集成到 OpenHarness 中。

## 概述

OpenHarness 目前提供有状态的 Agent 能力——工具、技能、记忆、多 Agent 协调——但缺少反馈驱动的学习能力。本设计新增一个**学习服务**（后台守护进程），异步处理 Agent 轮次事件，实现三种自改进机制：

1. **技能进化器** — 从复杂任务中提取并精炼可复用流程
2. **会话索引器** — 搜索历史会话，查找相关先例
3. **用户建模器** — 学习并持续整合用户偏好

## 架构：学习服务（后台守护进程）

```
┌──────────────────────────────────────────────────────────┐
│                    OpenHarness 引擎                       │
│                                                          │
│  ┌──────────┐    ┌──────────────────┐    ┌────────────┐ │
│  │  查询    │───▶│  PostTurn 钩子   │───▶│  事件总线  │ │
│  │  循环    │    │  (事件发射器)    │    │  (内存队列)│ │
│  └──────────┘    └──────────────────┘    └─────┬──────┘ │
└─────────────────────────────────────────────────┼────────┘
                                                  │ 异步推送
                                                  ▼
┌──────────────────────────────────────────────────────────┐
│                 学习服务（新增）                           │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  事件总线 → asyncio.Queue → 3个工作器               │ │
│  │                                                     │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │ │
│  │  │ 技能        │  │ 会话         │  │ 用户建模器 │ │ │
│  │  │ 进化器      │  │ 索引器       │  │            │ │ │
│  │  └──────┬──────┘  └──────┬───────┘  └──────┬─────┘ │ │
│  └─────────┼────────────────┼─────────────────┼───────┘ │
│            ▼                ▼                  ▼         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ skills/     │  │ sessions/    │  │ memory/ +      │ │
│  │ {category}/ │  │ search-index │  │ local_rules/   │ │
│  │ *.md        │  │ .db (FTS5)   │  │ (已有)         │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  定时调度器（沿用已有模式）                           │ │
│  │  • 技能整合：每 30 分钟                              │ │
│  │  • 用户模型整合：每 60 分钟                          │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 事件传输 | 内存 EventBus（asyncio.Queue） | 轻量、无外部依赖、零延迟推送 |
| 事件持久化 | 不单独持久化 | 学习是尽力而为；事件可从会话 JSON 重建 |
| 服务生命周期 | 与 compact 服务相同 | 由 CLI 启动，会话结束时终止 |
| 并发模型 | 3 个异步工作器，每个管道一个 | 独立处理，共享会话数据 |
| 失败模式 | 尽力而为 | 学习失败仅记录日志，绝不崩溃 Agent 循环 |

## 管道 1：技能进化器

从复杂任务中提取可复用流程，存储为分类 Markdown 技能文件。

### 数据流

```
轮次事件（工具结果、任务结果）
     │
     ▼
┌─────────────┐     触发条件（满足任一）：
│  提取器     │     • 复杂多工具任务完成
│  (LLM 调用) │     • 用户表达满意（"太好了！"、"完美"）
│             │     • 任务重试后在第 2+ 次成功
│  输出：     │     • 检测到重复模式（3+ 相似任务）
│  {          │
│    category,│     分类 → 技能子目录：
│    title,   │       debugging, refactoring, testing,
│    body     │       deployment, data-pipeline 等
│  }          │
└──────┬──────┘
       │
       ▼
┌─────────────┐     安全门控：
│  校验器     │     • 大小 <= 15KB
│             │     • 无泄露的密钥/凭证
│  • 大小检查 │     • 无破坏性命令
│  • 安全检查 │     • 去重：语义相似度 > 0.9 → 更新而非新建
│  • 去重检查 │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  写入器：skills/{category}/{slug}.md     │
│                                          │
│  格式：与已有技能相同                     │
│  （可选 frontmatter + markdown 正文）    │
└──────────────────────────────────────────┘
```

### 存储结构

```
skills/
├── debugging/
│   ├── trace-import-errors.md
│   └── fix-circular-deps.md
├── refactoring/
│   └── extract-utility-function.md
├── testing/
│   └── mock-external-apis.md
└── deployment/
    └── docker-healthcheck.md
```

### 去重策略

- mem0 后端可用时：通过 mem0 的 search API 使用嵌入相似度
- 仅 markdown 后端时：使用词元重叠（对标题 + 正文前 50 词做 Jaccard 相似度）
- 阈值：相似度 > 0.9 → 更新已有技能；< 0.9 → 创建新技能
- "重复模式（3+ 相似任务）" 由 SkillEvolver 在会话内统计工具使用模式检测（如相同 3+ 工具按序使用）

### 定时任务：技能整合（每 30 分钟）

- LLM 审查某分类下所有已学习技能
- 合并重叠技能
- 移除搜索中从未被引用的技能（衰减机制）
- 强制执行大小限制

## 管道 2：会话索引器

在已有会话 JSON 文件上构建 FTS5 搜索索引，实现跨会话对话召回。

### 数据流

```
已有：~/.openharness/data/sessions/{project}/
├── session-01115a368a66.json    ← 完整对话
├── session-0777c2fff49a.json    ← 完整对话
└── latest.json                  ← 当前会话

新增：search-index.db (FTS5)

┌──────────────────────────────────────┐
│  会话保存时：                         │
│  1. 从消息中提取文本                  │
│  2. 插入 FTS5 虚拟表                 │
│                                      │
│  查询时：                             │
│  1. FTS5 搜索 Top-K 消息             │
│  2. 从源会话 JSON 加载完整上下文      │
│  3. LLM 摘要相关上下文               │
│  4. 注入 QueryContext 作为            │
│     "past_conversation_context"       │
└──────────────────────────────────────┘
```

### FTS5 表结构

```sql
CREATE VIRTUAL TABLE messages USING fts5(
    session_id,
    msg_idx,
    role,
    content,
    timestamp,
    tokenize='porter'
);
```

### 索引位置

`~/.openharness/data/sessions/{project}/search-index.db`

### 集成点

在 `QueryEngine.submit_message()` 中，记忆预搜索之后：

```python
if session_index is not None:
    past_context = await session_index.search(
        user_message.text,
        max_results=5
    )
    # past_context: list of (session_id, msg_idx, snippet, relevance)
    # 由 LLM 摘要后注入 QueryContext
```

### 会话索引更新

挂载到已有 `save_session_snapshot()`——JSON 写入后，提取新增/更新的消息并 upsert 到 FTS5 索引。无需定时任务；事件驱动，随会话保存触发。

## 管道 3：用户建模器

从对话中学习用户偏好，合并到已有的记忆 + 个性化系统。无独立存储。

### 数据流

```
轮次事件（用户消息 + 修正）
     │
     ▼
┌──────────────┐     信号检测：
│  提取器      │     • 显式："我偏好 X"、"不要做 Y"
│  (LLM 调用)  │     • 隐式：用户撤销 Agent 操作
│              │     • 模式：用户总是以相同方式编辑输出
│  输出：      │     • 修正："不，我的意思是……"
│  偏好条目    │
└──────┬───────┘
       │
       ├─────────────────────────────────┐
       │                                 │
       ▼                                 ▼
┌──────────────┐              ┌──────────────────┐
│  记忆后端    │              │  个性化系统       │
│  (已有)      │              │  (已有)           │
│              │              │                  │
│  存储为：    │              │  local_rules/     │
│  memory_type │              │  ├── facts.json   │
│  = preference│              │  └── rules.md     │
│              │              │                  │
│  同时支持    │              │  新增事实类型：   │
│  markdown 和 │              │  • coding_style   │
│  mem0 后端   │              │  • workflow_pref  │
│              │              │  • review_pattern │
└──────────────┘              └──────────────────┘
```

### 通过记忆后端提取偏好

使用已有 `MemoryBackend.add()`，`memory_type="preference"`：

```python
await memory_backend.add(
    content="偏好所有函数签名加类型提示",
    title="类型提示偏好",
    memory_type="preference",
    metadata={"source": "implicit", "confidence": 0.8}
)
```

同时兼容 markdown 后端（创建 .md 文件）和 mem0 后端（带嵌入存储）。

### 新增个性化事实类型

扩展 `personalization/extractor.py`：

| 事实类型 | 信号 | 示例 |
|----------|------|------|
| `coding_style` | 用户持续以相同方式编辑 Agent 输出 | "总是添加类型提示" |
| `workflow_pref` | 用户重复某个多步骤模式 | "每个功能完成后提交" |
| `review_pattern` | 用户以特定方式纠正 Agent | "要求先写测试再实现" |

### 定时任务：用户模型整合（每 60 分钟）

- LLM 审查记忆中所有偏好条目
- 移除矛盾项（保留较新的）
- 合并重复项
- 将重复出现的模式提升为个性化规则

## LearningEvent 数据结构

```python
@dataclass
class LearningEvent:
    type: str                    # "turn_complete" | "session_save"
    session_id: str              # 当前会话 ID
    messages: list[dict]         # 本轮完整消息（用户 + 助手）
    tool_outcomes: list[dict]    # 本轮工具调用 + 结果
    usage: dict                  # Token 计数（输入/输出）
    timestamp: float             # Unix 时间戳

# 派生信号在工作器内部计算，不在事件上：
# - SkillEvolver._detect_satisfaction(messages) → bool
# - SkillEvolver._detect_retry(tool_outcomes) → bool
# - SkillEvolver._detect_complexity(tool_outcomes) → str
```

## 与已有代码的集成点

| 子系统 | 文件 | 变更 |
|--------|------|------|
| 查询引擎 | `engine/query_engine.py` | 轮次后添加 EventBus.push() + 轮次前添加 session_index.search() |
| 会话存储 | `services/session_storage.py` | save_session_snapshot() 时更新 FTS5 索引 |
| 记忆后端 | `memory/base.py` | 无变更——用户建模器通过已有 add() API 写入 |
| 个性化 | `personalization/extractor.py` | 新增事实类型：coding_style, workflow_pref, review_pattern |
| 系统提示 | `prompts/context.py` | 新增 past_conversation_context 段（在相关记忆之后） |
| 技能加载器 | `skills/` | 支持子目录扫描（skills/{category}/*.md） |
| CLI / 服务 | `cli.py`, `services/` | 与 compact/cron 服务一同启动学习服务 |

## 新增文件

```
src/openharness/learning/
├── __init__.py
├── service.py              # LearningService 守护进程（启动工作器、定时任务）
├── events.py               # LearningEvent 数据类、EventBus
├── skill_evolver.py        # 技能提取、校验、写入
├── session_indexer.py      # FTS5 索引构建 + 基于会话 JSON 的搜索
├── user_model.py           # 偏好提取 → 记忆 + 个性化
└── config.py               # LearningSettings（功能开关、阈值）
```

## 配置

```python
class LearningSettings(BaseModel):
    enabled: bool = True
    # 技能进化器
    skill_evolver_enabled: bool = True
    skill_max_size_kb: int = 15
    skill_consolidation_interval_minutes: int = 30
    # 会话索引器
    session_index_enabled: bool = True
    session_search_max_results: int = 5
    # 用户建模器
    user_model_enabled: bool = True
    user_model_consolidation_interval_minutes: int = 60
    # EventBus
    event_queue_maxsize: int = 100
```

## 错误处理

- 所有学习工作器运行在 try/except 中——异常仅记录日志，绝不向上传播
- EventBus.push() 为即发即弃模式，带队列溢出保护（满时丢弃最早的事件）
- 提取用的 LLM 调用优先使用更便宜/更快的模型（haiku）；haiku 不可用时回退到会话配置的模型
- 技能校验器优雅处理 LLM 的畸形输出

## 测试策略

- 每个管道组件的单元测试（进化器、索引器、用户建模器）
- 集成测试：端到端 事件 → 学习 → 检索 循环
- 使用模拟 LLM 响应以避免 CI 中的 API 费用
- 从会话 JSON fixture 构建 FTS5 索引的测试
- 技能去重逻辑的重叠内容测试
