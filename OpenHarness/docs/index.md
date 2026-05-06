# OpenHarness 文档中心

欢迎使用 OpenHarness 文档。本文档中心包含面向**最终用户**的使用手册和面向**开发者**的架构文档。

---

## 用户手册 (`user/`)

面向使用 OpenHarness 的开发者、研究者和终端用户。

| 文档 | 说明 |
|------|------|
| [快速入门](user/getting-started.md) | 5 分钟上手 OpenHarness |
| [安装配置](user/installation.md) | 完整安装、依赖、环境配置 |
| [CLI 命令参考](user/cli-reference.md) | 所有 CLI 子命令详解 |
| [技能使用指南](user/skills-user.md) | 如何使用和加载技能 |
| [插件使用指南](user/plugins-user.md) | 安装和管理插件 |
| [权限模式说明](user/permissions-user.md) | 安全模式、权限级别、路径规则 |
| [记忆系统使用](user/memory-user.md) | MEMORY.md、CLAUDE.md、会话持久化 |
| [任务管理](user/tasks-user.md) | 前台/后台任务、生命周期 |
| [消息渠道配置](user/channels-user.md) | Telegram/Slack/Discord/Feishu 等 |
| [ohmo 个人代理](user/ohmo-user.md) | ohmo 私有化部署、个人 AI 助手 |
| [Provider 配置](user/providers-user.md) | Anthropic/OpenAI/Claude/Copilot 等 |

---

## 开发者文档 (`dev/`)

面向贡献者、架构师和扩展 OpenHarness 的开发者。

### 核心模块 (`dev/core/`)

| 文档 | 说明 |
|------|------|
| [架构总览](dev/architecture-overview.md) | 10 大子系统全景图 |
| [设计原则](dev/design-principles.md) | 核心设计哲学和约束 |
| [Agent 循环引擎](dev/core/agent-loop.md) | QueryEngine、Streaming、Retry |
| [工具系统](dev/core/tools.md) | 工具注册、执行、权限检查 |
| [技能加载](dev/core/skills.md) | Markdown 技能解析、动态加载 |
| [插件系统](dev/core/plugins.md) | 插件注册、生命周期、类型定义 |
| [权限系统](dev/core/permissions.md) | 权限模式、PathRule、CommandRule |
| [生命周期钩子](dev/core/hooks.md) | PreToolUse/PostToolUse 事件 |
| [命令系统](dev/core/commands.md) | 命令注册、解析、执行 |
| [MCP 客户端](dev/core/mcp.md) | Model Context Protocol 集成 |
| [记忆系统](dev/core/memory.md) | 持久化记忆、上下文压缩 |
| [任务系统](dev/core/tasks.md) | TaskCreate/Get/List/Update/Stop |
| [多 Agent 协调](dev/core/coordinator.md) | Subagent、Team、任务委派 |
| [Prompt 构建](dev/core/prompts.md) | SystemPrompt、Context、CLAUDE.md |
| [配置系统](dev/core/config.md) | 多层配置、Schema、Migrations |

### 基础设施 (`dev/infrastructure/`)

| 文档 | 说明 |
|------|------|
| [API 客户端](dev/infrastructure/api-clients.md) | Anthropic/OpenAI/Codex/Copilot |
| [认证系统](dev/infrastructure/auth.md) | Auth Manager、Flows、Storage |
| [Bridge 系统](dev/infrastructure/bridge.md) | Bridge Manager、SessionRunner |
| [消息渠道](dev/infrastructure/channels.md) | Channel Adapter、IM 集成 |

### UI 层 (`dev/ui/`)

| 文档 | 说明 |
|------|------|
| [React TUI](dev/ui/tui.md) | Ink/React 终端 UI、Backend Protocol |

### ohmo 应用 (`dev/ohmo/`)

| 文档 | 说明 |
|------|------|
| [ohmo 架构](dev/ohmo/ohmo-architecture.md) | ohmo 整体架构、组件关系 |
| [ohmo Gateway](dev/ohmo/ohmo-gateway.md) | Gateway Server、Channel Binding |
| [ohmo 渠道](dev/ohmo/ohmo-channels.md) | 渠道配置、Bootstrap、Identity |

---

## 文档规范

- **语言**：中文
- **格式**：Markdown
- **原则**：
  - 每个文档聚焦单一模块，独立可读
  - 用户手册侧重"如何使用"
  - 开发者文档侧重"如何扩展/贡献"
  - 避免重复，通过交叉链接共享概念

---

*最后更新：2026-04-09*
