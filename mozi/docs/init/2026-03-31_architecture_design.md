# Mozi 高层架构设计文档

> **版本**: v1.4
> **日期**: 2026-03-31
> **状态**: 已批准
> **模板版本**: 1.0

---

## 1. 概述

### 1.1 项目定位

Mozi 是一款 AI Coding Agent，旨在通过智能编排和模块化架构，为开发者提供高效、可靠的代码生成和任务执行能力。项目采用**四层架构**（接入层 → 编排层 → 能力层 → 基础设施层）结合** Orchestrator-Worker 模式**，实现复杂任务的智能分解与执行。

### 1.2 架构目标

| 目标           | 说明                                                                       |
| -------------- | -------------------------------------------------------------------------- |
| **智能编排**   | 基于 Orchestrator-Worker 模式，编排器作为智能大脑做决策，Worker 无状态执行 |
| **上下文可控** | 委托 Context 模块，编排器按需分配给 Worker，避免上下文爆炸                 |
| **状态持久化** | TODO 列表、进度、决策历史支持断点续传                                      |
| **多模式执行** | 根据任务复杂度自动路由到 QUICK/DEEP/STRATEGIC 执行模式                     |
| **可扩展性**   | 存储、向量检索等基础设施可插拔，支持多后端                                 |

### 1.3 设计原则

| 原则                               | 说明                                         |
| ---------------------------------- | -------------------------------------------- |
| **编排器 = 大脑**                  | 有状态，做决策，决定给 Worker 分配什么上下文 |
| **Worker = 手脚**                  | 无状态，只执行，用完即焚                     |
| **核心循环在编排器**               | ReAct: Thought → Decide → Delegate → Review  |
| **上下文爆炸通过 Worker 隔离解决** | 只给必要信息，返回摘要                       |
| **JIT vs Pre-computed**            | LLM/Agent 自主按需探索，而非预设检索规则     |

---

## 2. 整体架构

### 2.1 六层架构总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              1. 接入层                                      │
│                    CLI (REPL)  │  IDE Plugin  │  REST API  │  WebSocket    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              2. 会话层                                      │
│            会话管理器：创建/销毁/路由 │ 并发控制 │ 鉴权 │ 配额管理           │
│            (注：这是会话的"容器"，每个 Session 实例持有 Orchestrator)       │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              3. 编排层                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Orchestrator (v3 Orchestrator-Worker 核心)                           │  │
│  │  - ReAct 循环引擎 (Thought → Decide → Delegate → Review)                │  │
│  │  - 全局状态存储 (TODO 列表、进度、决策历史)                             │  │
│  │  - 调用 Context 模块构建上下文（按需分配给 Worker）                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Worker 池 (无状态执行器)                                              │  │
│  │  - Explorer / Planner / Coder + QualityChecker + Reviewer             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              4. Core 层                                      │
│        Model Gateway │ 工具注册中心 │ MCP 客户端 │ Skills                    │
│        (注：负责与外部世界交互，屏蔽底层差异)                               │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              5. 知识层                                       │
│      短期上下文：滑动窗口 │ 长期记忆：向量库 │ 项目知识库：RAG              │
│      (注：这是会话的"海马体"，纯数据服务，被编排层调用)                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                            6. 基础设施层                                    │
│      SQLite │ Milvus │ Phoenix │ 事件总线  │
└───────────────────────────────────────────────────────────────────────────┘

══════════════════════ 横切面 (Cross-Cutting) ══════════════════════
   [安全] (加密)  │  [可观测性] (ELK/Log/Tracing/Metrics)  │  [熔断限流重试超时]
```

### 2.2 Orchestrator-Worker 模式与六层架构的融合

v3 版本的 Orchestrator 在六层架构的**编排层**内部实现了 Orchestrator-Worker 模式：

| 六层架构中的角色        | v3 实现                       | 说明                                                |
| ----------------------- | ----------------------------- | --------------------------------------------------- |
| **编排层 Orchestrator** | Manager（编排器）             | 保持控制平面定位，内部演化为有状态的 ReAct 循环引擎 |
| **编排层 Planner**      | Planner Worker                | 任务分解职责由专门的 Worker 执行                    |
| **Core 层**             | Explorer/Coder Workers        | 原有的工具执行能力由无状态 Worker 承担              |

---

## 3. 包结构

### 3.1 目录结构

基于四层架构 + Clean Architecture 原则：

```
mozi/
├── ingress/                    # 接入层
│   ├── __init__.py
│   ├── cli.py                  # REPL 交互入口
│   ├── rest_api.py             # REST API
│   ├── websocket.py            # WebSocket
│   └── ide_plugin/             # IDE 插件集成
│       ├── __init__.py
│       └── vscode.py
│
├── session/                    # 会话层
│   ├── __init__.py
│   ├── manager.py              # 会话管理器
│   ├── session.py              # 会话实例
│   └── auth.py                 # 鉴权
│
├── orchestrator/               # 编排层 ⭐
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # 编排器主类
│   │   ├── react_engine.py     # ReAct 循环引擎
│   │   ├── state_store.py      # 全局状态存储
│   │   └── router.py           # Category 路由
│   │
│   ├── workers/                 # Worker 池
│   │   ├── __init__.py
│   │   ├── explorer.py         # Explorer Worker
│   │   ├── planner.py          # Planner Worker
│   │   ├── coder.py            # Coder Worker (= ExecutionAgent)
│   │   ├── quality_checker.py   # QualityChecker
│   │   └── reviewer.py          # Reviewer
│   │
│   └── adapters/
│       ├── __init__.py
│       └── context_adapter.py   # Context 模块适配器
│
├── core/                       # Core 层（能力层）
│   ├── __init__.py
│   ├── model/                  # Model Gateway
│   │   ├── __init__.py
│   │   ├── gateway.py          # 统一模型网关
│   │   └── adapters/           # 模型适配器
│   │       ├── __init__.py
│   │       ├── openai.py
│   │       └── anthropic.py
│   │
│   ├── tools/                  # 工具注册中心
│   │   ├── __init__.py
│   │   ├── registry.py         # 工具注册表
│   │   ├── base.py             # Tool 基类
│   │   └── builtins/           # 内置工具
│   │       ├── __init__.py
│   │       ├── file_ops.py     # Read/Write/Edit/Glob/Grep
│   │       ├── bash.py         # Bash
│   │       └── code_analysis.py # AST-Grep/LSP
│   │
│   ├── mcp/                    # MCP 客户端
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── protocol.py
│   │
│   └── skills/                 # Skills 管理
│       ├── __init__.py
│       └── registry.py
│
├── context/                    # 知识层：上下文管理
│   ├── __init__.py
│   ├── builder.py              # ContextBuilder
│   ├── window.py               # WindowManager
│   ├── compactor.py            # Compress 策略
│   ├── offloader.py            # Write 策略
│   ├── isolator.py             # Isolate 策略
│   └── models.py                # 数据模型
│
├── memory/                     # 知识层：记忆管理
│   ├── __init__.py
│   ├── short_term.py           # 短期记忆（滑动窗口）
│   ├── long_term.py            # 长期记忆（向量存储）
│   ├── retriever.py            # 记忆检索器
│   └── stores/                 # 向量存储适配器
│       ├── __init__.py
│       ├── milvus.py
│       └── pgvector.py
│
└── infrastructure/             # 基础设施层
    ├── __init__.py
    ├── database.py              # SQLite
    ├── vector_db.py             # Milvus/PGVector
    ├── observability.py         # Phoenix
    ├── event_bus.py             # 事件总线
    ├── security.py              # 安全（加密、白名单）
    └── resilience.py            # 熔断、限流、重试
```

### 3.2 包职责

| 包 | 层级 | 职责 |
|---|------|------|
| `ingress` | 接入层 | 外部交互入口（CLI、API、WebSocket） |
| `session` | 会话层 | 会话生命周期、并发控制、鉴权 |
| `orchestrator` | 编排层 | 决策引擎、Worker 调度、状态管理 |
| `core` | Core 层 | 模型网关、工具执行、MCP 协议 |
| `context` | 知识层 | 上下文构建、窗口管理、Snapshot 分层 |
| `memory` | 知识层 | 短期/长期记忆、向量检索 |
| `infrastructure` | 基础设施 | 数据库、可观测性、事件总线 |

### 3.3 依赖关系

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           依赖方向（由外到内）                            │
└─────────────────────────────────────────────────────────────────────────┘

  Ingress ──► Session ──► Orchestrator ──┬──► Core (tools/model/mcp)
                                         │
                                         └──► Context ──► Memory
                                                             │
                                                     ┌───────┴───────┐
                                                     │  Infrastructure │
                                                     └───────────────┘

说明：
- 依赖只允许从外向内
- Orchestrator 依赖 Core 和 Context
- Context 依赖 Memory 和 Infrastructure
- Core、Memory、Infrastructure 无外部依赖（可独立测试）
```

---

## 4. 核心组件

> **注**：以下核心组件详细设计见对应模块设计文档：
> - [2026-03-31_orchestrator.md](./module/2026-03-31_orchestrator.md)
> - [2026-03-29_context.md](./module/2026-03-29_context.md)
> - [2026-03-29_memory.md](./module/2026-03-29_memory.md)

### 3.1 Orchestrator（编排器）

Orchestrator 是整个系统的**智能大脑**，负责决策和控制。

#### 3.1.1 核心架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    编排器 (Orchestrator)                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  核心 ReAct 循环 (Thought → Decide → Delegate → Review)     │  │
│  │  - 思考：当前状态是什么？下一步需要什么？                     │  │
│  │  - 决策：调用哪个 Worker？给什么上下文？                     │  │
│  │  - 委托：发送任务给 Worker，等待结果                         │  │
│  │  - 审查：Worker 返回的结果是否满意？是否需要重试？           │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  全局状态存储 (State Store)                                │  │
│  │  - TODO 列表及进度                                         │  │
│  │  - 已完成任务摘要                                          │  │
│  │  - 关键决策历史                                            │  │
│  │  - 上下文引用索引                                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  调用 Context 模块（外部依赖）                               │  │
│  │  - Orchestrator 委托 Context 模块构建上下文                  │  │
│  │  - Orchestrator 只决定"给 Worker 分配什么"                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 委托 (带上下文)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      执行组件池                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Worker (无状态)：Explorer / Planner / Coder              │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌────────────────────┐  ┌──────────────┐                     │
│  │ QualityChecker     │  │ Reviewer     │                     │
│  │ 统一质量门禁       │  │ 语义验收     │                     │
│  │ (Tester+Verifier) │  │ (需求对齐)   │                     │
│  └────────────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.1.2 ReAct 循环

编排器内部是一个完整的 **ReAct 循环**：

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

#### 3.1.3 编排器职责

| 职责           | 说明                                 |
| -------------- | ------------------------------------ |
| **状态管理**   | 维护 TODO 列表、进度、决策历史       |
| **上下文管理** | 委托 Context 模块，编排器按需分配    |
| **决策**       | 决定下一步调用哪个 Worker            |
| **审查**       | 评估 Worker 返回结果，决定重试或继续 |
| **生命周期**   | 会话级，贯穿整个任务                 |

详细设计见 [2026-03-31_orchestrator_v3_design.md](./2026-03-31_orchestrator_v3_design.md)

### 3.2 Workers（无状态执行器池）

| Worker       | 职责                     | 特点                   |
| ------------ | ------------------------ | ---------------------- |
| **Explorer**       | 探索代码库、搜索信息     | 无状态，只返回搜索结果 |
| **Planner**        | 生成 TODO 列表、任务分解 | 无状态，只生成计划     |
| **Coder**          | 编码执行、代码修改       | 无状态，只返回 diff    |
| **QualityChecker** | 合并 Tester+Verifier：运行时测试+静态检查 | 统一质量门禁 |
| **Reviewer**       | 语义验收：需求对齐/最终交付评估 | 复杂任务触发 |

**Worker 设计原则**：

| 原则         | 说明                                    |
| ------------ | --------------------------------------- |
| **最小暴露** | Worker 只接收完成当前任务所需的上下文   |
| **摘要返回** | Worker 返回结果的压缩摘要，而非完整输出 |
| **用完即焚** | Worker 完成后不保留其上下文             |

### 3.3 Context（上下文管理）

Context 模块是**上下文管理层**，负责：

- 构建当前任务的上下文信息
- 管理历史消息与会话状态
- 提供向量化检索能力，从 Memory 召回相关记忆
- 整合短期记忆（滑动窗口）和长期记忆（向量化存储）

**核心能力**：

| 能力        | 说明                                                          |
| ----------- | ------------------------------------------------------------- |
| 上下文构建  | 聚合用户输入、历史消息、Memory 数据，生成完整的模型调用上下文 |
| Push 预加载 | 自动预加载高频通用上下文（项目规范、开发偏好等）~30% tokens   |
| 上下文精简  | Compress（阈值触发），管理上下文膨胀，对 Agent 透明           |
| JIT 探索    | Agent 自主按需探索（grep/ls/read_file），而非预设检索规则     |

**架构定位**：

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        Agent 与 Context 模块的关系                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

       ┌─────────────────────────────────────────────────────────────────────────┐
       │                                Agent                                     │
       │                                                                             │
       │   JIT 是 Agent 的自主行为：                                                │
       │   - Agent 根据任务自主决定调用什么工具                                      │
       │   - Agent 根据推理结果决定是否继续探索                                      │
       │   - 工具调用由 Agent 决策，Context 模块仅执行                              │
       │                                                                             │
       └───────────────────────────────────────────────────────────────────────────┘
                                            │
                                            │ 工具调用 (grep, ls, read_file, vector_search...)
                                            ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                                 Context 模块                                          │
│                                                                                       │
│   角色一：工具提供者 (Tool Provider) - Agent 调用 ls/grep/read_file 等工具             │
│   角色二：窗口管理者 (Window Manager) - 阈值触发 Compress，无需 Agent 介入           │
│                                                                                       │
│   存储层                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │  Session (对话历史) │ Memory (向量存储) │ Scratchpad (草稿纸) │ FileSystem   │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

详细设计见 [module/2026-03-29_context.md](./module/2026-03-29_context.md)

### 3.4 Session（会话管理）

Session 模块负责管理用户与 Agent 之间的**会话生命周期**：

| 能力             | 说明                                       |
| ---------------- | ------------------------------------------ |
| 会话生命周期管理 | 创建、获取、更新、删除会话                 |
| 元数据存储       | 会话状态、创建时间、最后活跃时间、用户偏好 |
| 消息存储         | 消息追加、获取、列表管理                   |
| 会话持久化       | 支持 SQLite 存储、跨会话恢复               |
| 流式输出持久化   | 流式输出过程中渐进式保存，崩溃后可恢复     |

**生命周期状态机**：

```
                    创建
                      │
                      ▼
    ┌──────────────────────────────────────┐
    │              ACTIVE                   │
    │  (收到消息/发送消息时更新 last_active)│
    └──────────────┬───────────────────────┘
                   │ 超过 idle_timeout 无交互
                   ▼
    ┌──────────────────────────────────────┐
    │               IDLE                   │◄────────┐
    │  (可恢复，保留完整上下文)             │         │
    └──────────────┬───────────────────────┘         │
                   │ 超过 max_lifetime               │ 用户继续交互
                   ▼                                 │
    ┌──────────────────────────────────────┐         │
    │             ARCHIVED                 │─────────┘
    │  (压缩存储，可手动恢复)
    └──────────────┬───────────────────────┘
                   │ 超过 archive_lifetime
                   ▼
    ┌──────────────────────────────────────┐
    │             EXPIRED                  │
    │  (自动清理)
    └──────────────────────────────────────┘
```

详细设计见 [module/2026-03-29_session.md](./module/2026-03-29_session.md)

### 3.5 Memory（记忆系统）

Memory 模块是**记忆管理层**，负责短/长期记忆的管理和检索：

| 记忆类型                  | 用途                 | 存储方式 |
| ------------------------- | -------------------- | -------- |
| **短期记忆 (ShortTerm)**  | 滑动窗口内的最近对话 | 内存存储 |
| **语义记忆 (Semantic)**   | 一般知识和事实       | 向量存储 |
| **情景记忆 (Episodic)**   | 具体过去事件和交互   | 向量存储 |
| **程序记忆 (Procedural)** | 行为模式和操作知识   | 向量存储 |

**核心能力**：

| 能力         | 说明                                  |
| ------------ | ------------------------------------- |
| 短期记忆管理 | 基于滑动窗口的最近 N 轮对话，自动淘汰 |
| 长期记忆存储 | 三种记忆类型，支持向量检索            |
| 多后端支持   | 向量存储、Embedding 模型可插拔        |
| 混合检索     | 向量相似度 + metadata 标量过滤        |
| 冲突解决     | 相似度去重 + 合并策略 + 版本历史      |

详细设计见 [module/2026-03-29_memory.md](./module/2026-03-29_memory.md)

### 3.6 Storage（存储层）

Storage 模块是**基础设施层**，负责所有持久化数据的存储和管理：

| 能力       | 说明                                             |
| ---------- | ------------------------------------------------ |
| 会话持久化 | 会话数据的创建、读取、更新、删除，支持跨会话恢复 |
| 记忆存储   | 长期记忆的向量化和持久化，支持语义检索           |
| 文件管理   | 产物文件的存储、检索、清理和空间管理             |
| 存储抽象   | 多后端存储支持（文件系统，云存储），统一接口     |
| 迁移管理   | 数据迁移、版本升级、向后兼容                     |

**存储架构**：

```
SessionStorageManager
        │
        ├──► FileSessionStorage ──► 文件系统
        │
        └──► DBSessionStorage ──► SQLite/PostgreSQL（未来扩展）

MemoryStorageManager
        │
        ├──► VectorStore ──► 向量存储接口
        │         │
        │         ├──► FileVectorStore ──► 文件系统向量存储
        │         │
        │         └──► PGVectorStore ──► PostgreSQL/PGVector（未来扩展）
        │
        └──► MemoryIndex ──► 记忆索引管理
```

详细设计见 [module/2026-03-29_storage.md](./module/2026-03-29_storage.md)

### 3.7 共享类型定义

> **重要**：以下类型为跨模块共享，各子模块文档中的定义应与此保持一致。

#### 3.7.1 枚举类型

```python
class MessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "active"       # 活跃会话
    IDLE = "idle"           # 空闲会话（超过阈值未交互）
    ARCHIVED = "archived"   # 已归档会话
    EXPIRED = "expired"     # 已过期会话


class MemoryType(Enum):
    """记忆类型"""
    SHORT_TERM = "short_term"    # 短期记忆，滑动窗口
    SEMANTIC = "semantic"        # 语义记忆，一般知识
    EPISODIC = "episodic"        # 情景记忆，过去事件
    PROCEDURAL = "procedural"     # 程序记忆，行为模式
```

#### 3.7.2 核心数据结构

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

#### 3.7.3 类型一致性要求

| 类型 | 一致性要求 | 说明 |
|------|-----------|------|
| `MessageRole` | 四篇文档必须一致 | SYSTEM, USER, ASSISTANT, TOOL |
| `SessionStatus` | 四篇文档必须一致 | ACTIVE, IDLE, ARCHIVED, EXPIRED |
| `MemoryType` | 四篇文档必须一致 | SHORT_TERM, SEMANTIC, EPISODIC, PROCEDURAL |
| `Message` | Session/Memory/Storage 必须一致 | 字段定义以本文档为准 |
| `Session` | Session/Storage 必须一致 | Storage.md 的 Session 模型应向本定义看齐 |
| `MemoryBlock` | Memory/Storage 必须一致 | Storage.md 缺少 status 字段 |

---

## 5. 数据流

### 4.1 主交互流程

```
用户输入
    │
    ▼
CLI（解析命令/REPL）
    │
    ▼
EventBus.publish("user_message", payload)
    │
    ▼
Orchestrator（接收事件）
    │
    ├──► Orchestrator 意图识别
    ├──► Orchestrator 多轮澄清（如需要）
    ├──► Orchestrator Category 判定
    │         │
    │         ▼
    │    QUICK ──► 轻量探索 ──► 单Agent执行
    │    DEEP ──► 完整探索 ──► 多Agent协作
    │    STRATEGIC ──► 用户触发 ──► 完整流水线
    │
    ▼
ContextBuilder.build() ──► 从 Memory 召回短期+长期记忆
    │
    ▼
Model.invoke() ──► 生成响应/工具调用
    │
    ▼
Tools.execute() ──► 执行
    │
    ▼
EventBus.publish("tool_result", payload)
    │
    ▼
Orchestrator（处理结果）
    │
    ▼
Session.append() ──► 更新上下文
    │
    ▼
Memory.compact() ──► 必要时压缩上下文
    │
    ▼
CLI 输出
```

### 4.2 多Agent协作流程（DEEP任务）

```
Orchestrator 触发多Agent模式
    │
    ▼
Planner 分解任务
    │
    ├──► Agent-A 执行子任务-1
    ├──► Agent-B 执行子任务-2（可并行）
    └──► Agent-C 执行子任务-3
              │
              ▼
        各Agent通过EventBus通信
              │
              ▼
        Orchestrator 汇总结果
              │
              ▼
        验证完整性 ──► 通过 ──► 返回结果
                     │
                     ▼（失败）
              回滚或重规划
```

### 4.3 上下文构建流程

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
    │         ├── token >= 12000 ──► Compress 策略（摘要压缩）
    │         ├── 工具结果过长 ──► Write 策略（卸载到本地+引用路径）
    │         └── 复杂任务 ──► Isolate 策略（subagent 隔离）
    │
    ▼
BuiltContext ──► Model
```

### 4.4 崩溃恢复流程

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

---

## 6. 模块交互

### 5.1 模块依赖关系

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

**依赖规则**：

- Orchestrator 可调用 Context
- Context 可调用 Session 和 Memory
- Session 和 Memory 只能调用 Storage
- Storage 不能调用上层模块

### 5.2 接口边界

| 调用方       | 被调用方 | 接口                                  | 说明               |
| ------------ | -------- | ------------------------------------- | ------------------ |
| Orchestrator | Context  | `ContextBuilder.build()`              | 获取构建好的上下文 |
| Orchestrator | Session  | `SessionManager.append_message()`     | 追加消息并持久化   |
| Context      | Memory   | `Memory.recall()`                     | 召回相关记忆       |
| Context      | Session  | `SessionContextManager.get_history()` | 获取历史消息       |
| Memory       | Storage  | `VectorStore.upsert/search()`         | 向量存储操作       |
| Session      | Storage  | `SessionStorage.save/load()`          | 会话持久化         |

---

## 7. Category 体系

### 6.1 三种执行模式

| Category      | 触发    | 探索 | 任务规划   | 编码 | 自测       | 用户确认 |
| ------------- | ------- | ---- | ---------- | ---- | ---------- | -------- |
| **QUICK**     | 自动    | 轻量 | 否         | 是   | 可选       | 否       |
| **DEEP**      | 自动    | 是   | 是（显式） | 是   | 是（强制） | 否       |
| **STRATEGIC** | `/plan` | 是   | 是         | 是   | 是         | 是       |

### 6.2 执行流水线

所有任务共享流水线，编排器根据 Category 决定跳过哪些阶段：

```
预分析 → 全局规划(可选) → 执行循环 → 验证 → Review
```

### 6.3 架构矩阵

| 阶段         | 核心组件        | 输出物          | QUICK | DEEP | STRATEGIC |
| ------------ | --------------- | --------------- | ----- | ---- | --------- |
| **预分析**   | PreAnalysis     | 任务分类 + 权限 | 是    | 是   | 是        |
| **全局规划** | Planner Worker    | 设计文档        | 否    | 否   | 是        |
| **探索**     | Explorer Worker   | 搜索结果        | 轻量  | 是   | 是        |
| **任务规划** | Planner Worker    | TODO 列表       | 否    | 是   | 是        |
| **编码**     | Coder Worker      | Code Diff       | 是    | 是   | 是        |
| **质量检查** | QualityChecker    | 质量报告        | 可选  | 是   | 是        |
| **语义验收** | Reviewer          | 交付报告        | 否    | 复杂 | 是        |

---

## 8. 技术选型

### 7.1 核心依赖

| 组件           | 技术选型          | 说明                                    |
| -------------- | ----------------- | --------------------------------------- |
| **运行时**     | Python 3.11+      | 核心语言                                |
| **数据验证**   | Pydantic 2.x      | 类型校验、数据模型、配置校验            |
| **CLI 框架**   | Typer             | 命令行应用框架，基于 type hints         |
| **终端输出**   | Rich              | 富文本输出、表格、进度条、日志          |
| **模型网关**   | litellm           | 统一接口调用 OpenAI/Anthropic/Cohere 等 |
| **MCP 客户端** | FastMCP           | 高性能 MCP 协议实现                     |
| **向量数据库** | Milvus            | 生产级向量检索                          |
| **会话存储**   | SQLite (WAL 模式) | 多进程并发支持                          |
| **可观测性**   | Phoenix (Arize)   | Tracing + Evaluation + Metrics          |

### 7.2 存储架构

```
┌─────────────────────────────────────────────────────────────┐
│                        存储层架构                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   SQLite    │  │   Milvus    │  │   本地      │        │
│  │ (会话/消息)  │  │  (向量存储)  │  │  (产物文件) │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| 数据类型  | 存储方案        | 说明                 |
| --------- | --------------- | -------------------- |
| 会话/消息 | SQLite WAL 模式 | 多进程并发，崩溃恢复 |
| 向量记忆  | Milvus          | 高性能相似度检索     |
| 产物文件  | 本地文件系统    | 大结果分块存储       |

### 7.3 模型与 Embedding

| 组件          | 技术选型                        | 说明                                 |
| ------------- | ------------------------------- | ------------------------------------ |
| **模型网关**  | litellm                         | 统一接口，OpenAI/Anthropic/Cohere 等 |
| **Embedding** | text-embedding-3-small (OpenAI) | 1536 维度，可插拔                    |

### 7.4 可观测性

| 组件           | 技术选型         | 说明                                    |
| -------------- | ---------------- | --------------------------------------- |
| **Tracing**    | Phoenix          | 分布式追踪，Span 管理                   |
| **Evaluation** | Phoenix          | LLM 输出评估，质量监控                  |
| **Metrics**    | Phoenix          | 自定义指标，性能监控                    |
| **日志**       | ELK / Rich (dev) | 生产：ELK 分布式日志；开发：Rich 富文本 |

### 7.5 扩展接口

| 组件      | 技术选型 | 说明               |
| --------- | -------- | ------------------ |
| **MCP**   | FastMCP  | 外部工具协议       |
| **Tools** | 注册中心 | 内置工具发现与路由 |

---

## 9. 上下文精简策略

### 8.1 Compress（阈值触发）

当 token >= 阈值（默认 80%）时自动触发，通过 LLM 摘要压缩上下文。

### 8.2 Context 模块的 Snapshot 分层

> **注意**：以下是由 Context 模块负责的压缩快照分层机制，与 Orchestrator 的上下文分配是正交的。

```
┌─────────────────────────────────────────────────────────────┐
│                    Context 模块：Snapshot 分层               │
├─────────────────────────────────────────────────────────────┤
│  Snapshot-0：原始消息（最近 10 条）                           │
│  Snapshot-1：压缩快照 #1（50 轮摘要）                         │
│  Snapshot-2：压缩快照 #2（200 轮摘要）                         │
│  Offload：外部存储（按需 Reload）                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. 未来演进

### 9.1 近期规划

| 方向           | 说明                       |
| -------------- | -------------------------- |
| **多模态支持** | 支持图像、文档等非文本输入 |
| **增强记忆**   | 跨会话记忆、用户偏好学习   |
| **协作模式**   | 多 Agent 协作、角色分工    |

### 9.2 长期愿景

| 方向           | 说明                     |
| -------------- | ------------------------ |
| **自主学习**   | 从交互中持续优化决策策略 |
| **插件生态**   | 开放的工具和技能市场     |
| **企业级特性** | SSO、审计日志、权限管理  |

---

## 11. 参考文档

| 文档               | 路径                                                                               |
| ------------------ | ---------------------------------------------------------------------------------- |
| 编排层 v3 设计     | [2026-03-31_orchestrator_v3_design.md](./2026-03-31_orchestrator_v3_design.md)     |
| Context 模块       | [module/2026-03-29_context.md](./module/2026-03-29_context.md)                     |
| Session 模块       | [module/2026-03-29_session.md](./module/2026-03-29_session.md)                     |
| Memory 模块        | [module/2026-03-29_memory.md](./module/2026-03-29_memory.md)                       |
| Storage 模块       | [module/2026-03-29_storage.md](./module/2026-03-29_storage.md)                     |

---

_版本: v1.3_
_更新日期: 2026-03-31_

## 变更记录

| 版本 | 日期       | 变更内容                                                                                       |
| ---- | ---------- | ---------------------------------------------------------------------------------------------- |
| v1.4 | 2026-03-31 | 合并上下文与存储层概览：新增共享类型定义章节（MessageRole/SessionStatus/MemoryType/Message/Session/MemoryBlock） |
| v1.3 | 2026-03-31 | Manager-Worker 模式更名为 Orchestrator-Worker 模式                                             |
| v1.2 | 2026-03-31 | 精简精简策略描述：阈值触发仅触发 Compress；Write/Isolate 为独立机制                            |
| v1.1 | 2026-03-31 | 更新技术选型：Python + Pydantic + SQLite + Milvus + litellm + FastMCP + Phoenix + Typer + Rich |
| v1.0 | 2026-03-31 | 初始版本，整合各模块设计文档生成高层架构文档                                                   |
