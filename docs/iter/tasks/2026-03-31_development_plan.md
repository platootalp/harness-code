# Mozi AI Coding Agent 项目开发规划

> **版本**: v1.0
> **日期**: 2026-03-31
> **状态**: 规划中

---

## 1. 项目概述

### 1.1 项目定位

Mozi 是一款 AI Coding Agent，采用四层架构（接入层 → 编排层 → 能力层 → 基础设施层）结合 Orchestrator-Worker 模式，实现复杂任务的智能分解与执行。

### 1.2 核心架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              1. 接入层 (Ingress)                          │
│                    CLI (REPL) │ REST API │ WebSocket                    │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              2. 会话层 (Session)                            │
│            会话管理器：创建/销毁/路由 │ 并发控制 │ 鉴权 │ 配额管理            │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              3. 编排层 (Orchestrator)                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Orchestrator: ReAct 循环引擎 + 全局状态存储 + Worker 调度              │  │
│  │  Worker 池: Explorer / Planner / Coder / QualityChecker / Reviewer     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              4. Core 层                                    │
│        Model Gateway │ 工具注册中心 │ MCP 客户端 │ Skills                   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                              5. 知识层                                      │
│      上下文管理 (Context) │ 记忆管理 (Memory)                               │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                            6. 基础设施层                                   │
│      SQLite │ Milvus │ Phoenix │ 事件总线 │ 安全 │ 熔断限流                 │
└───────────────────────────────────────────────────────────────────────────┘
```

### 1.3 技术栈

| 组件 | 技术选型 |
|------|---------|
| 运行时 | Python 3.11+ |
| 数据验证 | Pydantic 2.x |
| CLI 框架 | Typer |
| 终端输出 | Rich |
| 模型网关 | litellm |
| MCP 客户端 | FastMCP |
| 向量数据库 | Milvus |
| 会话存储 | SQLite (WAL 模式) |
| 可观测性 | Phoenix (Arize) |

---

## 2. 模块依赖关系

```
Ingress ──► Session ──► Orchestrator ──┬──► Core (tools/model/mcp/skills)
                                         │
                                         └──► Context ──► Memory
                                                             │
                                                     ┌───────┴───────┐
                                                     │  Infrastructure │
                                                     └───────────────┘
```

**依赖规则**：
- 依赖只允许从外向内
- Orchestrator 依赖 Core 和 Context
- Context 依赖 Memory 和 Infrastructure
- Core、Memory、Infrastructure 无外部依赖（可独立测试）

---

## 3. 开发阶段划分

### 3.1 阶段总览

| 阶段 | 名称 | 周期 | 目标 |
|------|------|------|------|
| **Phase 0** | 基础设施搭建 | 2 周 | 搭建项目骨架、CI/CD、基础设施层 |
| **Phase 1** | 核心模块实现 | 4 周 | 实现 Session、Model、Tools 模块 |
| **Phase 2** | 编排层实现 | 4 周 | 实现 Orchestrator、Context、Memory 模块 |
| **Phase 3** | 接入层与集成 | 3 周 | 实现 Ingress、EventBus、系统集成 |
| **Phase 4** | 质量与交付 | 2 周 | 测试补齐、安全扫描、文档完善 |

**总工期**: 15 周（约 4 个月）

---

## 4. 迭代详情

### Phase 0: 基础设施搭建（第 1-2 周）

**目标**: 搭建项目骨架、配置管理、CI/CD 流水线、基础设施层核心组件

#### 里程碑 M0.1: 项目骨架完成（第 1 周）

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| 项目目录结构 | 基于架构设计的完整目录结构 | 符合 Clean Architecture 原则 |
| `pyproject.toml` | 项目配置 | 依赖版本锁定 |
| `uv` 配置 | 构建工具配置 | 使用 uv 管理依赖 |
| `.claude/rules/*` | 规则文件 | 代码风格、CI/CD、安全规范已配置 |
| Git Hooks | pre-commit 配置 | Ruff、mypy、ESLint 集成 |

**目录结构**：

```
mozi/
├── __init__.py
├── ingress/                    # 接入层
├── session/                   # 会话层
├── orchestrator/              # 编排层
│   ├── core/
│   └── workers/
├── core/                      # Core 层
│   ├── model/
│   ├── tools/
│   │   ├── builtin/
│   │   ├── analysis/
│   │   └── external/
│   ├── mcp/
│   └── skills/
├── context/                   # 知识层
├── memory/                    # 知识层
└── infrastructure/            # 基础设施层
    ├── database.py
    ├── vector_db.py
    ├── observability.py
    ├── event_bus.py
    ├── security.py
    └── resilience.py

tests/
├── unit/
├── integration/
└── e2e/

docs/
├── foundation/
│   └── architecture/
└── iteration/
    └── v1.0/
```

#### 里程碑 M0.2: CI/CD 流水线完成（第 2 周）

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| GitHub Actions 配置 | 完整 CI/CD 流水线 | 所有质量门禁生效 |
| Ruff 配置 | Python 代码格式化 | 行长度 100、双引号、import 排序 |
| mypy 配置 | 严格类型检查 | 无类型错误 |
| pytest 配置 | 测试框架 | AAA 结构、覆盖率 ≥ 80% |
| bandit 配置 | 安全扫描 | 危险函数检测 |
| truffleHog 配置 | 密钥扫描 | 禁止硬编码密钥 |

**CI 流水线阶段**：
```
PR 创建 → 代码检查(Ruff/mypy/ESLint) → 安全扫描(bandit/pip-audit)
       → 单元测试 → 覆盖率检查 → 构建 → 集成测试 → E2E 测试
```

---

### Phase 1: 核心模块实现（第 3-6 周）

#### 迭代 1.1: Storage 与 Session（第 3-4 周）

**目标**: 实现基础设施层的存储抽象和会话管理模块

##### 里程碑 M1.1: Storage 模块完成（第 3 周）

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| `infrastructure/database.py` | SQLite 存储实现 | WAL 模式、多进程并发支持 |
| `infrastructure/vector_db.py` | 向量存储抽象 | Milvus/PGVector 可插拔 |
| `infrastructure/event_bus.py` | 事件总线实现 | 同步/异步事件发布订阅 |
| `SessionStorage` | 会话存储接口 | CRUD 操作 |
| `MessageStorage` | 消息存储接口 | 实时保存、崩溃恢复 |

**关键文件**：
```
infrastructure/
├── database.py          # SQLiteSessionStorage (WAL 模式)
├── vector_db.py         # VectorStore 抽象 + Milvus/PGVector 适配器
└── event_bus.py         # EventBus 实现
```

**验收标准**：
- [ ] SQLite WAL 模式正常，崩溃后数据不丢失
- [ ] 向量存储接口支持 Milvus/PGVector 切换
- [ ] 事件总线支持同步/异步发布订阅
- [ ] 存储层单元测试覆盖率 ≥ 80%

##### 里程碑 M1.2: Session 模块完成（第 4 周）

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| `session/models.py` | Session/Message 数据模型 | Pydantic 模型、类型注解 |
| `session/manager.py` | SessionManager 实现 | CRUD、生命周期管理 |
| `session/storage.py` | 存储抽象接口 | Storage 接口定义 |
| `session/database.py` | SQLite 存储实现 | WAL 模式、大结果文件存储 |
| 会话状态机 | ACTIVE → IDLE → ARCHIVED → EXPIRED | 状态转换正确 |

**关键文件**：
```
session/
├── __init__.py
├── models.py             # Session, Message, SessionStatus, MessageRole
├── manager.py            # SessionManager (create/get/update/delete/list)
├── storage.py            # SessionStorage 抽象接口
└── database.py           # SQLiteSessionStorage 实现
```

**验收标准**：
- [ ] 创建、获取、更新、删除会话正常工作
- [ ] 消息追加和历史查询正常
- [ ] 会话状态机转换正确
- [ ] 流式输出持久化正常
- [ ] resume 命令可恢复崩溃会话
- [ ] Session 模块单元测试覆盖率 ≥ 80%

---

#### 迭代 1.2: Model 模块（第 5-6 周）

**目标**: 实现模型网关，支持多模型适配

##### 里程碑 M1.3: Model 模块核心完成（第 5 周）

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| `core/model/adapter.py` | ModelAdapter 抽象基类 | 统一调用接口 |
| `core/model/anthropic.py` | Anthropic 适配器 | Claude 系列支持 |
| `core/model/openai.py` | OpenAI 适配器 | GPT 系列支持 |
| `core/model/registry.py` | 模型注册表 | 动态模型选择 |
| `core/model/template.py` | Prompt 模板管理 | `{{variable}}` 占位符 |
| `core/model/errors.py` | 异常类型定义 | 统一错误码 |
| `core/model/retry.py` | 重试策略 | 指数退避 |
| `core/model/circuit_breaker.py` | 熔断保护 | 熔断状态管理 |

**关键文件**：
```
core/model/
├── __init__.py
├── adapter.py            # ModelAdapter 抽象基类
├── anthropic.py          # AnthropicAdapter
├── openai.py             # OpenAIAdapter
├── registry.py          # ModelRegistry
├── template.py           # PromptTemplateManager
├── errors.py            # ModelInvocationError 等
├── retry.py             # RetryStrategy
└── circuit_breaker.py    # CircuitBreaker
```

**验收标准**：
- [ ] Anthropic Claude 3.5/3 系列正常调用
- [ ] OpenAI GPT-4o/4 系列正常调用
- [ ] 模型切换功能正常
- [ ] Prompt 模板变量替换正常
- [ ] 重试和熔断机制正常工作
- [ ] Model 模块单元测试覆盖率 ≥ 80%

##### 里程碑 M1.4: Model 模块集成（第 6 周）

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| Model 模块与 Session 集成 | 模型调用记录到会话历史 | 消息历史包含模型响应 |
| Model 模块与 EventBus 集成 | `model_invoked` / `model_error` 事件 | 事件正确发布 |
| Model 配置管理 | `config/model.json` + 环境变量 | 密钥安全存储 |
| API 密钥管理集成 | Config 模块集成 | 环境变量覆盖配置 |

**验收标准**：
- [ ] 模型调用结果正确追加到会话消息
- [ ] EventBus 事件正确发布
- [ ] API 密钥从环境变量读取
- [ ] 配置热更新正常

---

### Phase 2: 编排层实现（第 7-10 周）

#### 迭代 2.1: Context 与 Memory（第 7-8 周）

**目标**: 实现上下文管理和记忆管理模块

##### 里程碑 M2.1: Memory 模块完成（第 7 周）

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| `memory/short_term.py` | 短期记忆（滑动窗口） | 自动淘汰过期记忆 |
| `memory/long_term.py` | 长期记忆（向量存储） | 四种记忆类型支持 |
| `memory/retriever.py` | 记忆检索器 | 向量相似度检索 |
| `memory/stores/milvus.py` | Milvus 适配器 | 向量存储实现 |
| `memory/stores/pgvector.py` | PGVector 适配器 | 向量存储实现 |
| 混合检索 | 向量 + 标量过滤 | 检索结果准确 |

**关键文件**：
```
memory/
├── __init__.py
├── short_term.py         # ShortTermMemory (滑动窗口)
├── long_term.py          # LongTermMemory (向量存储)
├── retriever.py          # MemoryRetriever
└── stores/
    ├── __init__.py
    ├── milvus.py         # MilvusVectorStore
    └── pgvector.py       # PGVectorStore
```

**验收标准**：
- [ ] 短期记忆滑动窗口自动淘汰
- [ ] 长期记忆向量存储和检索正常
- [ ] 四种记忆类型（ShortTerm/Semantic/Episodic/Procedural）正常
- [ ] Milvus/PGVector 适配器可切换
- [ ] Memory 模块单元测试覆盖率 ≥ 80%

##### 里程碑 M2.2: Context 模块完成（第 8 周）

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| `context/builder.py` | ContextBuilder | 上下文构建 |
| `context/window.py` | WindowManager | 阈值触发 Compress |
| `context/compactor.py` | Compress 策略 | LLM 摘要压缩 |
| `context/offloader.py` | Offload 策略 | 大结果卸载到文件 |
| `context/isolator.py` | Isolate 策略 | Worker 隔离 |
| `context/models.py` | 数据模型 | BuiltContext 等 |

**关键文件**：
```
context/
├── __init__.py
├── builder.py            # ContextBuilder
├── window.py             # WindowManager
├── compactor.py          # Compress 策略 (LLM 摘要)
├── offloader.py          # Offload 策略 (大结果存文件)
├── isolator.py           # Isolate 策略 (Worker 隔离)
└── models.py             # BuiltContext 等数据模型
```

**验收标准**：
- [ ] ContextBuilder.build() 正确构建上下文
- [ ] token >= 80% 阈值触发 Compress
- [ ] 大结果正确 Offload 到文件
- [ ] 复杂任务正确 Isolate 到 Worker
- [ ] Context 模块单元测试覆盖率 ≥ 80%

---

#### 迭代 2.2: Orchestrator 模块（第 9-10 周）

**目标**: 实现编排层核心，Orchestrator-Worker 模式

##### 里程碑 M2.3: Orchestrator 核心完成（第 9 周）

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| `orchestrator/orchestrator.py` | Orchestrator 主类 | ReAct 循环实现 |
| `orchestrator/state.py` | 全局状态管理 | TODO/进度/决策历史 |
| `orchestrator/category.py` | Category 路由 | QUICK/DEEP/STRATEGIC |
| `orchestrator/workers/explorer.py` | Explorer Worker | 探索代码库 |
| `orchestrator/workers/planner.py` | Planner Worker | 任务分解 |
| `orchestrator/workers/coder.py` | Coder Worker | 代码执行 |
| `orchestrator/quality.py` | QualityChecker | 质量门禁 |
| `orchestrator/reviewer.py` | Reviewer | 语义验收 |

**关键文件**：
```
orchestrator/
├── __init__.py
├── orchestrator.py        # Orchestrator 主类
├── state.py               # OrchestratorState, StateStore
├── category.py            # Category, CategoryRouter
├── workers/
│   ├── __init__.py
│   ├── explorer.py         # Explorer Worker
│   ├── planner.py          # Planner Worker
│   └── coder.py            # Coder Worker
├── quality.py             # QualityChecker
└── reviewer.py            # Reviewer
```

**ReAct 循环**：
```
Thought → Decide → Delegate → Review
   ↑                              │
   └──────────── Update ←─────────┘
```

**验收标准**：
- [ ] Orchestrator.run() ReAct 循环正常工作
- [ ] Category 路由正确（QUICK/DEEP/STRATEGIC）
- [ ] StateStore 正确管理 TODO/进度/决策历史
- [ ] Worker 无状态执行，用完即焚
- [ ] Orchestrator 模块单元测试覆盖率 ≥ 80%

##### 里程碑 M2.4: Orchestrator 集成（第 10 周）

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| Orchestrator 与 Session 集成 | 会话上下文传递 | 消息历史正确传递 |
| Orchestrator 与 Context 集成 | 上下文分配 | 按需分配给 Worker |
| Orchestrator 与 Memory 集成 | 记忆召回 | 相关记忆正确召回 |
| Orchestrator 与 Model 集成 | 模型调用 | LLM 调用正常 |
| Orchestrator 与 EventBus 集成 | 事件发布 | 状态变更事件正确发布 |
| 断点续传 | 状态持久化 | 崩溃后可恢复 |

**验收标准**：
- [ ] Orchestrator 正确调用 Session 获取历史
- [ ] Context 模块正确为 Orchestrator 构建上下文
- [ ] Memory 模块正确为 Orchestrator 召回记忆
- [ ] Model 模块正确为 Orchestrator 提供 LLM 调用
- [ ] EventBus 事件正确发布
- [ ] 崩溃后状态可恢复
- [ ] 端到端流程测试通过

---

### Phase 3: 接入层与集成（第 11-13 周）

#### 迭代 3.1: Tools 模块（第 11 周）

**目标**: 实现工具注册中心和内置工具

##### 里程碑 M3.1: Tools 模块完成

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| `core/tools/framework.py` | Tool 抽象基类 | 统一工具接口 |
| `core/tools/registry.py` | ToolRegistry | 工具注册管理 |
| `core/tools/security.py` | 安全执行层 | 白名单/危险检测 |
| `core/tools/builtin/read.py` | ReadFileTool | 文件读取 |
| `core/tools/builtin/write.py` | WriteFileTool | 文件写入 |
| `core/tools/builtin/edit.py` | EditFileTool | 文件编辑 |
| `core/tools/builtin/bash.py` | BashTool | 命令执行 |
| `core/tools/builtin/grep.py` | GrepTool | 文本搜索 |
| `core/tools/builtin/glob.py` | GlobTool | 文件匹配 |

**内置工具清单**：
| 工具 | 功能 | 优先级 |
|------|------|--------|
| Read | 读取文件内容 | P0 |
| Write | 创建/覆盖文件 | P0 |
| Edit | 字符串替换编辑 | P0 |
| Bash | 执行 Shell 命令 | P0 |
| Grep | 文本正则搜索 | P0 |
| Glob | glob 模式匹配 | P1 |
| AST-Grep | AST 结构搜索 | P1 |
| LSP | 代码分析/补全 | P2 |
| WebSearch | Web 检索 | P2 |
| WebFetch | URL 内容获取 | P2 |
| TaskCreate/Get/Update/List | 任务操作 | P1 |

**验收标准**：
- [ ] Tool 抽象基类正确定义
- [ ] ToolRegistry 注册/注销/查询正常
- [ ] 所有内置工具正常工作
- [ ] 路径白名单验证正常
- [ ] 危险函数检测正常
- [ ] Tools 模块单元测试覆盖率 ≥ 80%

---

#### 迭代 3.2: Ingress 模块（第 12 周）

**目标**: 实现 CLI 接入层

##### 里程碑 M3.2: Ingress 模块完成

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| `ingress/main.py` | CLI 主入口 | 参数解析、命令路由 |
| `ingress/commands.py` | 命令定义 | do/repl/session 命令 |
| `ingress/output.py` | 输出格式化 | Rich 格式化、进度条 |
| REPL 模式 | 交互式对话 | 实时响应 |
| 命令模式 | 离线命令执行 | `mozi do "task"` |
| 会话管理 | session create/list/continue/delete | 会话生命周期 |

**命令行接口**：
```
mozi                          # 启动 REPL 交互模式
mozi do "<task>"             # 执行单次命令
mozi session create           # 创建新会话
mozi session list             # 列出所有会话
mozi session continue <id>   # 继续指定会话
mozi session delete <id>      # 删除会话
mozi -v                       # 启用详细输出
```

**验收标准**：
- [ ] REPL 模式正常工作
- [ ] 命令模式正常工作
- [ ] 会话管理命令正常
- [ ] 输出格式化美观易读
- [ ] EventBus 事件正确发布
- [ ] Ingress 模块单元测试覆盖率 ≥ 80%

---

#### 迭代 3.3: 系统集成（第 13 周）

**目标**: 完成系统集成，端到端流程测试

##### 里程碑 M3.3: 系统集成完成

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| 端到端流程测试 | 完整用户场景测试 | 所有关键路径覆盖 |
| EventBus 集成 | 全模块事件打通 | 事件正确发布订阅 |
| 错误处理集成 | 统一异常体系 | 错误正确传播和展示 |
| 配置管理集成 | Config 模块集成 | 所有配置统一管理 |
| 可观测性集成 | Phoenix 集成 | Tracing/Metrics 正常 |
| Session 并发测试 | 多会话并发隔离 | 数据不混淆 |

**集成测试场景**：
| 场景 | 输入 | 期望输出 |
|------|------|----------|
| 简单任务 | "读取 package.json" | 正确显示文件内容 |
| 单文件编辑 | "在 main.py 顶部添加 import os" | 文件正确修改 |
| 复杂任务 | "重构 auth 模块" | 完整的 ReAct 循环执行 |
| 会话恢复 | 崩溃后 resume | 正确恢复上下文 |
| 多会话隔离 | 并发两个会话 | 数据不混淆 |

**验收标准**：
- [ ] 所有集成测试通过
- [ ] EventBus 事件链路正确
- [ ] 错误处理链路正确
- [ ] 配置管理链路正确
- [ ] 可观测性链路正确
- [ ] 集成测试覆盖率 ≥ 80%

---

### Phase 4: 质量与交付（第 14-15 周）

#### 迭代 4.1: 质量加固（第 14 周）

**目标**: 测试补齐、安全扫描、缺陷修复

##### 里程碑 M4.1: 质量加固完成

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| 单元测试补齐 | 覆盖率 < 80% 模块补测 | 整体覆盖率 ≥ 80% |
| 集成测试补齐 | 核心路径覆盖 | 核心模块覆盖率 ≥ 90% |
| E2E 测试 | 关键用户场景 | E2E 测试覆盖 |
| 安全扫描修复 | bandit/pip-audit/npm audit | 无高危漏洞 |
| 密钥扫描 | truffleHog | 无硬编码密钥 |
| 性能测试 | 响应时间/并发 | 满足性能指标 |

**覆盖率目标**：
| 模块 | 目标覆盖率 |
|------|-----------|
| infrastructure | ≥ 80% |
| session | ≥ 80% |
| core/model | ≥ 80% |
| context | ≥ 80% |
| memory | ≥ 80% |
| orchestrator | ≥ 80% |
| core/tools | ≥ 80% |
| ingress | ≥ 80% |
| **整体** | **≥ 80%** |

**验收标准**：
- [ ] 整体测试覆盖率 ≥ 80%
- [ ] 核心模块覆盖率 ≥ 90%
- [ ] 所有安全扫描通过
- [ ] 无阻断性缺陷

---

#### 迭代 4.2: 文档与发布（第 15 周）

**目标**: 完善文档、发布准备

##### 里程碑 M4.2: 文档与发布完成

**交付物**：

| 交付物 | 说明 | 验收标准 |
|--------|------|----------|
| API 文档 | 所有公共接口文档 | 文档完整 |
| README.md | 项目说明文档 | 安装使用说明 |
| 架构文档 | 架构设计文档 | 符合最终实现 |
| 模块设计文档 | 各模块详细设计 | 符合最终实现 |
| 开发指南 | 开发者文档 | 贡献指南 |
| 发布说明 | Release Notes | 版本变更说明 |
| 版本标签 | Git Tag v1.0.0 | 发布完成 |

**目录结构（最终版）**：
```
docs/
├── foundation/
│   ├── architecture/
│   │   └── 2026-03-31_architecture_design.md
│   └── requirement/
├── iteration/
│   └── v1.0/
│       ├── README.md
│       ├── prd/
│       ├── design/
│       ├── development/
│       └── release/
└── support/
    ├── adr/
    └── sop/
```

**验收标准**：
- [ ] 所有文档完整且最新
- [ ] README 包含安装使用说明
- [ ] 发布说明完整
- [ ] Git Tag 已创建
- [ ] CHANGELOG 已更新

---

## 5. 交付结果清单

### 5.1 代码交付物

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 项目骨架 | `mozi/` | 完整代码仓库 |
| 单元测试 | `tests/unit/` | 覆盖率 ≥ 80% |
| 集成测试 | `tests/integration/` | 核心路径覆盖 |
| E2E 测试 | `tests/e2e/` | 关键场景覆盖 |
| CI/CD 配置 | `.github/workflows/` | 完整流水线 |

### 5.2 文档交付物

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 架构设计 | `docs/foundation/architecture/` | 高层架构文档 |
| 模块设计 | `docs/init/module/` | 各模块详细设计 |
| 开发指南 | `docs/iteration/v1.0/development/` | 开发者文档 |
| API 文档 | `docs/iteration/v1.0/design/` | 接口文档 |
| 发布说明 | `docs/iteration/v1.0/release/` | Release Notes |

### 5.3 质量指标

| 指标 | 目标 | 当前 |
|------|------|------|
| 单元测试覆盖率 | ≥ 80% | - |
| 核心模块覆盖率 | ≥ 90% | - |
| 安全扫描 | 通过 | - |
| 类型检查 | 通过 | - |
| 格式化检查 | 通过 | - |

---

## 6. 风险与依赖

### 6.1 关键依赖

| 依赖 | 影响 | 缓解措施 |
|------|------|----------|
| 外部 API (Anthropic/OpenAI) | 模型调用可能不稳定 | 重试+熔断机制 |
| Milvus 向量数据库 | 生产级检索依赖 | 支持 PGVector 降级 |
| LLM 任务分解质量 | 分解质量不可控 | 分解有效性验证 |
| 上下文膨胀 | token 消耗不可控 | Compress/Offload/Isolate |

### 6.2 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Worker 上下文隔离不完善 | 信息泄露风险 | 严格的上下文分配审查 |
| 长任务崩溃恢复 | 状态丢失 | 实时持久化+状态恢复 |
| 并发会话数据混淆 | 数据隔离失效 | WAL 模式+会话隔离 |
| 复杂任务规划失败 | 任务无法完成 | 降级策略+人工介入 |

---

## 7. 版本规划

### v1.0 (当前版本)

**目标**: 实现完整的 AI Coding Agent 核心功能

**完成标准**:
- [ ] 所有核心模块实现完成
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 集成测试覆盖核心路径
- [ ] CI/CD 流水线完整
- [ ] 安全扫描全部通过
- [ ] 文档完整

### v1.1 (后续版本)

**目标**: 增强功能和稳定性

**规划特性**:
- [ ] MCP 外部工具协议支持
- [ ] LSP 代码分析增强
- [ ] 多模态支持（图像输入）
- [ ] 跨会话记忆
- [ ] 用户偏好学习

### v2.0 (后续版本)

**目标**: 企业级特性

**规划特性**:
- [ ] SSO 认证
- [ ] 审计日志
- [ ] 权限管理
- [ ] 插件生态
- [ ] 分布式部署

---

## 8. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-03-31 | 初始版本 |

---

_版本: v1.0_
_更新日期: 2026-03-31_
