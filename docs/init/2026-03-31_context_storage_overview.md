# 上下文与存储层概览

> **版本**: 1.0
> **日期**: 2026-03-31
> **子模块**: Context、Session、Memory、Storage

---

## 1. 概述

### 1.1 模块定位

上下文与存储层是 Mozi 架构中的**基础设施层**，负责数据的管理、持久化和检索。它由四个紧密协作的模块组成：

```
┌─────────────────────────────────────────────────────────────────┐
│                      上下文与存储层                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│   │   Context   │  │   Session   │  │   Memory    │           │
│   │  上下文构建  │  │  会话管理   │  │  记忆系统   │           │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘           │
│          │                │                │                    │
│          └────────────────┼────────────────┘                    │
│                           ▼                                     │
│                  ┌─────────────┐                               │
│                  │   Storage   │                               │
│                  │   存储层    │                               │
│                  └─────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 子模块职责

| 模块 | 文档 | 核心职责 |
|------|------|---------|
| **Context** | [2026-03-29_context.md](./module/2026-03-29_context.md) | 上下文构建、窗口管理、JIT Context、压缩调控 |
| **Session** | [2026-03-29_session.md](./module/2026-03-29_session.md) | 会话生命周期、消息持久化、崩溃恢复 |
| **Memory** | [2026-03-29_memory.md](./module/2026-03-29_memory.md) | 短/长期记忆管理、混合检索、去重合并 |
| **Storage** | [2026-03-29_storage.md](./module/2026-03-29_storage.md) | 通用存储抽象、会话持久化、向量存储 |

---

## 2. 共享类型定义

> **重要**：以下类型为跨模块共享，各子模块文档中的定义应与此保持一致。

### 2.1 枚举类型

#### MessageRole（消息角色）

```python
class MessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
```

#### SessionStatus（会话状态）

```python
class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "active"       # 活跃会话
    IDLE = "idle"           # 空闲会话（超过阈值未交互）
    ARCHIVED = "archived"   # 已归档会话
    EXPIRED = "expired"     # 已过期会话
```

#### MemoryType（记忆类型）

```python
class MemoryType(Enum):
    """记忆类型

    - SHORT_TERM: 短期记忆，滑动窗口，内存存储
    - SEMANTIC: 语义记忆，一般知识，向量存储
    - EPISODIC: 情景记忆，过去事件，向量存储
    - PROCEDURAL: 程序记忆，行为模式，向量存储
    """
    SHORT_TERM = "short_term"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
```

### 2.2 核心数据结构

#### Message（对话消息）

```python
@dataclass
class Message:
    """对话消息"""
    id: str
    session_id: str
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_call_id: str | None = None
    attachment_path: str | None = None  # 大结果存文件
    metadata: dict[str, Any] = field(default_factory=dict)
    streaming_content: str = ""          # 流式输出渐进内容
    is_streaming: bool = False           # 是否正在流式输出
```

#### Session（会话结构）

```python
@dataclass
class Session:
    """会话结构"""
    id: str
    name: str = ""
    working_dir: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_active_at: datetime = field(default_factory=datetime.now)
```

#### MemoryBlock（记忆块）

```python
@dataclass
class MemoryBlock:
    """记忆块"""
    id: str
    session_id: str
    content: str
    memory_type: MemoryType
    embedding: list[float] | None = None
    importance: float = 0.5  # 0.0 - 1.0
    status: SessionStatus = SessionStatus.ACTIVE  # ACTIVE/ARCHIVED/DELETED
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 2.3 类型一致性说明

| 类型 | 一致性要求 | 说明 |
|------|-----------|------|
| `MessageRole` | 四篇文档必须一致 | SYSTEM, USER, ASSISTANT, TOOL |
| `SessionStatus` | 四篇文档必须一致 | ACTIVE, IDLE, ARCHIVED, EXPIRED |
| `MemoryType` | 四篇文档必须一致 | SHORT_TERM, SEMANTIC, EPISODIC, PROCEDURAL |
| `Message` | Session/Memory/Storage 必须一致 | 字段定义以 Session.md 为准 |
| `Session` | Session/Storage 必须一致 | Storage.md 的 Session 模型过于简单，应向 Session.md 看齐 |
| `MemoryBlock` | Memory/Storage 必须一致 | Storage.md 缺少 status 字段 |

---

## 3. 模块交互

### 3.1 上下文构建流程

```
Orchestrator
    │
    ▼
ContextBuilder.build(user_input, session_id)
    │
    ├──► Push: 预加载项目规范、开发偏好 (~30% tokens)
    │
    ├──► Session: 获取历史消息
    │
    ├──► Memory: 召回相关记忆
    │
    ├──► WindowManager: 检查 token 阈值
    │         │
    │         ├── token >= 12000 ──► Compress 策略
    │         ├── token >= 14000 ──► Write 策略
    │         └── token >= 15000 ──► Isolate 策略
    │
    ▼
BuiltContext ──► Model
```

### 3.2 消息持久化流程

```
用户输入
    │
    ▼
Orchestrator.append_message()
    │
    ▼
SQLiteSessionStorage.save_message()
    │
    ├── 内容 < 4KB ──► 直接存储
    └── 内容 >= 4KB ──► 存储到文件 + 记录 attachment_path
```

### 3.3 崩溃恢复流程

```
进程崩溃
    │
    ▼
用户执行 resume <session-id>
    │
    ▼
加载 Session（从最后一条已保存消息）
    │
    ▼
如果 is_streaming == True
    │
    ▼
使用 streaming_content 作为上下文继续
```

### 3.4 记忆召回流程

```
Context.retrieve(query, session_id)
    │
    ├── ShortTermMemory ──► 滑动窗口内最近 N 条
    │
    └── LongTermMemory ──► 向量相似度检索
              │
              ▼
         MemoryBlock 列表
```

---

## 4. 架构约束

### 4.1 分层依赖

```
┌─────────────────────────────────────────┐
│           Orchestrator (调用方)          │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│              Context (构建层)            │
│  - ContextBuilder                        │
│  - WindowManager                         │
│  - Push (预加载)                         │
└─────────────────┬───────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│    Session    │   │    Memory    │
│   (会话层)    │   │   (记忆层)   │
└───────┬───────┘   └───────┬───────┘
        │                   │
        └─────────┬─────────┘
                  ▼
┌─────────────────────────────────────────┐
│             Storage (基础设施层)          │
│  - SQLiteSessionStorage                   │
│  - VectorStore                           │
│  - FileStorage                           │
└─────────────────────────────────────────┘
```

**依赖规则：**
- Context 可调用 Session 和 Memory
- Session 和 Memory 只能调用 Storage
- Storage 不能调用上层模块

### 4.2 数据流方向

| 方向 | 描述 |
|------|------|
| **请求流** | Orchestrator → Context → Session/Memory → Storage |
| **响应流** | Storage → Session/Memory → Context → Orchestrator |

---

## 5. 配置汇总

| 模块 | 配置前缀 | 关键配置项 |
|------|---------|-----------|
| Context | `context.` | `window_messages`, `max_tokens`, `compress_threshold` |
| Session | `session.` | `db_path`, `idle_timeout_seconds`, `auto_save_message_count` |
| Memory | `memory.` | `vector_store`, `short_term_window_size`, `similarity_threshold` |
| Storage | `storage.` | `backend`, `base_path`, `retention_days` |

详细配置见各子模块文档。

---

## 6. 参考

| 文档 | 路径 | 说明 |
|------|------|------|
| Context 模块 | [2026-03-29_context.md](./module/2026-03-29_context.md) | 上下文构建与窗口管理 |
| Session 模块 | [2026-03-29_session.md](./module/2026-03-29_session.md) | 会话生命周期与持久化 |
| Memory 模块 | [2026-03-29_memory.md](./module/2026-03-29_memory.md) | 短/长期记忆管理 |
| Storage 模块 | [2026-03-29_storage.md](./module/2026-03-29_storage.md) | 存储抽象与多后端支持 |
| 错误处理 | [2026-03-29_error_handling.md](./module/2026-03-29_error_handling.md) | 统一异常体系 |
| 测试策略 | [2026-03-29_testing.md](./module/2026-03-29_testing.md) | 测试规范 |

---

## 7. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| 1.0 | 2026-03-31 | 创建概览文档，组织 Context/Session/Memory/Storage 四篇文档 |

_版本: 1.0_
_更新日期: 2026-03-31_
