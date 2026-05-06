# OpenHarness 总览

> 本页提供 OpenHarness 项目的整体概述，适合首次了解或快速查阅核心信息。

---

## 系统一句话描述

**OpenHarness** — 开源轻量级 Agent 基础设施核心库，通过一条命令（`oh`）提供完整的 LLM Agent 运行能力：工具调用、技能系统、记忆管理、多 Agent 协调、权限控制与沙箱隔离。

**ohmo** — 基于 OpenHarness 构建的个人 AI Agent 应用，支持飞书/Slack/Telegram/Discord 等多平台接入，可在后台自动执行代码编写、PR 创建、测试运行等任务。

---

## 核心价值主张

OpenHarness 解决的核心问题是 **如何让 LLM 真正成为可工作的软件工程 Agent**。

| 问题 | OpenHarness 方案 |
|------|-----------------|
| 模型只知道"要做什么"，不知道"怎么做" | **43+ 工具系统** — Bash/Read/Write/Edit/Glob/Grep/Web 等工具让模型与文件系统、网络、进程交互 |
| 模型无法保持跨会话记忆 | **Memory 系统** — `MEMORY.md` 索引 + `memory/` 持久化目录 |
| 模型不知道项目约定和规范 | **CLAUDE.md 发现与注入** — 自动加载项目根目录的领域知识 |
| 模型缺乏技能指导 | **按需技能加载** — 40+ 技能文件（commit、review、debug 等），兼容 anthropics/skills |
| 工具执行缺乏安全控制 | **多级权限模式** — Default（确认）/Auto（全自动）/Plan（只读）三级控制 |
| 单 Agent 难以处理复杂任务 | **Swarm 多 Agent 协调** — Coordinator + Teammate 架构，支持并行工作器 |
| 无法扩展自定义工具 | **插件系统** — 命令/钩子/Agent/MCP 组件的完整插件生态 |
| 需要与外部 IM 集成 | **ohmo 渠道系统** — Telegram/Slack/Discord/飞书等渠道接入 |

---

## 架构亮点

### 五层架构

```mermaid
graph TB
    subgraph UI["第五层：UI 层"]
        TUI["React TUI<br/>(命令选择器、权限对话框、模式切换)"]
        CLI["CLI 主入口<br/>(oh 主命令)"]
    end

    subgraph COORD["第四层：协调层"]
        SWARM["Swarm<br/>(团队生命周期、Teammate 派生)"]
        COORD["Coordinator<br/>(多 Agent 协调、任务分发)"]
        BRIDGE["Bridge<br/>(外部 CLI 工具集成)"]
    end

    subgraph AGENT["第三层：Agent 循环"]
        ENGINE["QueryEngine<br/>(query → tool-call → loop)"]
        HOOKS["Hooks<br/>(PreToolUse/PostToolUse)"]
        PROMPTS["Prompts<br/>(系统提示组装、CLAUDE.md)"]
    end

    subgraph CORE["第二层：核心子系统"]
        TOOLS["Tools<br/>(43+ 工具)"]
        PERMS["Permissions<br/>(多级权限模式)"]
        MEMORY["Memory<br/>(跨会话持久化)"]
        SKILLS["Skills<br/>(按需技能加载)"]
        TASKS["Tasks<br/>(后台任务管理)"]
        MCP["MCP Client<br/>(外部工具协议)"]
        AUTH["Auth<br/>(多种认证流程)"]
    end

    subgraph RUNTIME["第一层：运行时"]
        CONFIG["Settings<br/>(多层配置系统)"]
        SANDBOX["Sandbox<br/>(Docker 隔离)"]
        STATE["AppState<br/>(可观察状态)"]
    end

    UI --> COORD
    CLI --> COORD
    COORD --> AGENT
    AGENT --> CORE
    CORE --> RUNTIME

    style UI fill:#4a148c,color:#fff
    style COORD fill:#880e4f,color:#fff
    style AGENT fill:#1a237e,color:#fff
    style CORE fill:#01579b,color:#fff
    style RUNTIME fill:#1b5e20,color:#fff
```

### 核心特性

| 特性 | 描述 | 亮点 |
|------|------|------|
| **工具调用循环** | 模型决定要做什么，Harness 处理怎么做 | 流式文本输出、API 指数退避重试、并行工具执行、Token 计数与成本追踪 |
| **43+ 工具** | 覆盖文件 I/O、Shell、搜索、Web、MCP、任务、Agent | 全部基于 Pydantic 输入验证，支持 JSON Schema 自动推导 |
| **自动压缩** | 上下文超过阈值时自动 LLM 摘要旧消息 | 微压缩（清除旧工具结果）→ 全摘要（LLM 压缩），保留任务状态和频道日志 |
| **Swarm 多 Agent** | Coordinator 分解任务，Teammate 并行执行 | Subprocess/In-Process 两种后端，BackendRegistry 自动选择 |
| **权限安全** | 多级权限 + 路径规则 + 敏感路径保护 | 内置凭证路径保护（不可覆盖），Defense-in-Depth |
| **MCP 集成** | 连接外部 MCP 服务器扩展工具集 | stdio + HTTP 两种传输，自动重连，工具专用服务器兼容 |
| **Docker 沙箱** | 容器化工具执行，资源限制与网络隔离 | CPU/内存限制，none/bridge 网络模式，原子性清理 |
| **插件生态** | 兼容 Claude Code 插件格式 | commands + hooks + agents + MCP servers 完整组件注入 |
| **React TUI** | 交互式终端界面 | 命令选择器、权限对话框、会话恢复、键盘快捷键 |

---

## 关键设计决策摘要

### 决策 1：工具优先而非对话优先

**决策：** OpenHarness 采用工具调用循环而非纯对话模式作为核心交互范式。
**理由：** 模型在软件工程任务中需要执行具体操作（读写文件、运行命令），纯对话无法满足需求。
**替代方案：** 纯对话模式（无工具调用）。**代价：** 无法自动化执行，只能提供建议。
**源码证据：** `src/openharness/engine/query_engine.py` -> `run_query()` 核心循环逻辑

---

### 决策 2：Provider 作为工作流而非硬编码

**决策：** 不硬编码特定 Provider，支持任意 Anthropic/OpenAI 兼容 API 作为后端。
**理由：** 用户可能有不同的订阅和 API 密钥，需要灵活切换；社区需要支持新兴 Provider。
**替代方案：** 只支持 Anthropic 官方 API。**代价：** 锁定单一 Provider，用户黏性高但灵活性低。
**源码证据：** `src/openharness/config/settings.py` -> `ProviderProfile` + `Settings.resolve_auth()`

---

### 决策 3：内存持久化通过文件系统而非数据库

**决策：** 使用 `memory/` 目录中的 Markdown 文件作为跨会话记忆存储。
**理由：** 简单、人类可读、易于版本控制和无缝集成 LLM 上下文注入。
**替代方案：** 结构化数据库（SQLite/PostgreSQL）。**代价：** 增加运维复杂度，与 Markdown 生态不兼容。
**源码证据：** `src/openharness/memory/manager.py` -> `add_memory_entry()` / `remove_memory_entry()`

---

### 决策 4：Swarm Teammate 优先子进程后端

**决策：** SubprocessBackend 作为默认 Teammate 执行后端，而非进程内。
**理由：** 进程隔离更安全，子进程崩溃不影响主 Agent；与 Claude Code 生态一致。
**替代方案：** In-Process 线程/协程共享内存。**代价：** 崩溃传播风险，状态隔离弱。
**源码证据：** `src/openharness/swarm/registry.py` -> `BackendRegistry._register_defaults()` 注册优先级

---

### 决策 5：权限采用黑名单优先模式

**决策：** PermissionChecker 默认询问，只有显式允许才跳过确认。
**理由：** 安全默认值，降低 LLM 意外执行危险操作的风险。
**替代方案：** 白名单模式（默认允许）。**代价：** 用户摩擦增加，需要频繁添加允许规则。
**源码证据：** `src/openharness/permissions/checker.py` -> `PermissionChecker.evaluate()` 决策逻辑

---

## 风险摘要

| 风险 | 触发条件 | 影响范围 | 可观测信号 | 缓解动作 |
|------|----------|----------|------------|----------|
| **Token 成本超限** | 长会话上下文超过 auto_compact 阈值 | 用户账单超支 | UsageSnapshot 累计输出 token 激增 | 配置 `auto_compact_threshold_tokens`，定期 compact |
| **沙箱容器泄漏** | Docker 容器非正常退出，清理失败 | 主机资源泄漏 | `docker ps` 看到孤立容器 | `atexit` 处理器，`stop_sync()` 同步清理 |
| **MCP 服务器超时** | MCP HTTP 服务器响应缓慢或断连 | 工具调用阻塞 | MCP 连接状态变为 failed | `reconnect_all()` 自动重连，graceful degradation |
| **子进程 Teammate 僵尸化** | `stop_task()` 未成功终止进程 | 僵尸进程占用资源 | `ps aux \| grep openharness` 大量残留 | `SIGTERM` → `SIGKILL` 两阶段终止 |
| **CLAUDE.md 注入冲突** | 项目 CLAUDE.md 与当前工具集不一致 | 模型行为异常 | 模型频繁报错 "tool not available" | 定期 review CLAUDE.md，确保与 OpenHarness 工具同步 |
| **权限误判** | 复杂路径 glob 模式下规则覆盖不足 | 敏感文件被修改 | PermissionDecision.reason 中的 deny 消息 | 定期 review `settings.json` 中 `path_rules` |
| **配置漂移** | 环境变量覆盖后 `oh setup` 无法感知 | Provider 切换失败 | API 调用返回认证失败 | `oh provider list` 确认当前活动 profile |

---

## 技术栈

### 语言与运行时

| 类别 | 技术 | 版本要求 |
|------|------|----------|
| **主语言** | Python | >= 3.10 |
| **协议** | AsyncIO (asyncio) | 内置 |
| **类型系统** | Pydantic | v2 |
| **CLI 框架** | Typer | 最新 |
| **HTTP 客户端** | httpx | 最新 |

### 核心依赖

| 依赖 | 用途 |
|------|------|
| `anthropic` | Anthropic API 官方 SDK |
| `mcp` | MCP 协议官方库 |
| `pydantic` | 数据验证与序列化 |
| `typer` | CLI 界面 |
| `httpx` | HTTP 客户端（HTTP MCP 传输） |
| `yaml` | 插件 frontmatter 解析 |
| `shutil` | 文件系统操作（tmux 检测等） |

### 前端与界面

| 组件 | 技术 |
|------|------|
| **TUI 渲染** | React + Ink |
| **TUI 后端协议** | 自定义异步协议（`src/openharness/ui/protocol.py`） |
| **终端交互** | Textual（可选渲染后端） |

### 外部集成

| 集成 | 技术 |
|------|------|
| **多 IM 平台** | Telegram API / Slack WebSocket / Discord Bot / 飞书 SDK |
| **容器化** | Docker |
| **Shell 模拟** | asyncio subprocess |
| **OAuth** | GitHub OAuth Device Flow |

---

## 版本与演进信息

### 当前版本

| 版本 | 发布日期 | 状态 |
|------|----------|------|
| **v0.1.6** | 2026-04-10 | 当前稳定版 |
| v0.1.5 | 2026-04-08 | 稳定 |
| v0.1.4 | 2026-04-08 | 稳定 |
| v0.1.2 | 2026-04-06 | 稳定 |
| v0.1.0 | 2026-04-01 | 初始开源发布 |

### v0.1.x 关键里程碑

- **v0.1.0** — 初始开源发布，完整 Harness 架构（Engine、Tools、Skills、Plugins、Permissions、Hooks、Commands、MCP、Memory、Tasks、Coordinator、Prompts、Config、UI）
- **v0.1.2** — 统一 setup 工作流，ohmo 个人 Agent 应用
- **v0.1.4** — 多 Provider 认证，Moonshot/Kimi 支持，MCP HTTP 传输
- **v0.1.5** — MCP 自动重连、JSON Schema 类型推导、ohmo 渠道文件附件
- **v0.1.6** — Auto-Compaction 保留任务状态、Subprocess teammates 稳定化、Markdown TUI

### 架构演进方向（待规划）

| 功能 | 状态 | 说明 |
|------|------|------|
| Docker 沙箱后端 | 已实现 | `sandbox/docker_backend.py` |
| MCP 多传输支持 | 已实现 | stdio + HTTP |
| tmux 面板后端 | 规划中 | BackendRegistry 中已预留接口 |
| 多团队协调 | 已实现 | `TeamLifecycleManager` |
| Workspace 远程调用 | 规划中 | ohmo Gateway 增强 |

### 兼容性

| 兼容性 | 说明 |
|--------|------|
| **Anthropic/skills 格式** | 兼容，`.md` 技能文件直接复用 |
| **Claude Code 插件格式** | 兼容，`plugin.json` + `commands/hooks/agents` 目录结构兼容 |
| **OpenAI 兼容 API** | 支持，包括 OpenAI 官方、OpenRouter、DashScope、DeepSeek、GitHub Models 等 |
| **Anthropic 兼容 API** | 支持，包括 Moonshot/Kimi、GLM、MiniMax 等 |
| **MCP 服务器** | 双向兼容，任何符合 MCP 规范的服务器 |

---

## 相关链接

| 资源 | 描述 |
|------|------|
| [README.md](../../README.md) | 项目总览、快速上手 |
| [docs/index.md](../index.md) | 文档体系导航入口 |
| [docs/architecture/system-context.md](../architecture/system-context.md) | 系统边界与外部依赖 |
| [docs/overview/architecture-at-a-glance.md](architecture-at-a-glance.md) | 架构总览 |
| [docs/appendix/evidence-index.md](../appendix/evidence-index.md) | 源码证据索引 |
| [docs/reference/glossary.md](../reference/glossary.md) | 术语表 |
| [CHANGELOG.md](../../CHANGELOG.md) | 版本变更记录 |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | 贡献指南 |

---

*最后更新：2026-04-14 | OpenHarness v0.1.6*
