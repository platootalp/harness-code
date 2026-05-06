# 阅读指南

## 摘要

OpenHarness 文档分为 L1（概览）、L2（参考）、L3（架构详细）三层。本页为不同角色提供个性化的阅读路径指引，帮助你根据需求找到最相关的文档。

## 你将了解

- 按角色（终端用户、开发者、贡献者）的阅读路径
- 各角色在不同场景下的关注重点
- 文档依赖关系和推荐阅读顺序
- L1/L2/L3 不同深度的阅读策略

## 范围

面向所有使用 OpenHarness 的人群，涵盖从快速上手到深度开发的全场景。

---

## 文档层级概览

OpenHarness 文档分为三个深度级别：

| 层级 | 名称 | 目标读者 | 内容特点 |
|------|------|----------|----------|
| L1 | 概览层 | 所有用户 | 概念介绍、快速上手、核心工作流 |
| L2 | 参考层 | 日常使用 | CLI 参考、配置参考、数据模型、故障排除 |
| L3 | 架构层 | 深度开发 | 模块设计、内部实现、集成细节 |

---

## 按角色的阅读路径

### 终端用户

终端用户指直接通过 CLI 使用 OpenHarness 的开发者或运维人员。

#### 快速上手路径（首次使用）

```
docs/user/getting-started.md     ->  L1  安装与首次启动
  -> docs/reference/cli.md       ->  L2  CLI 参考（主命令和子命令）
  -> docs/user/channels-user.md  ->  L1  渠道接入（Telegram/Discord 等）
```

#### 日常使用路径

```
docs/reference/cli.md            ->  L2  CLI 参考
  -> docs/user/providers-user.md ->  L2  Provider 配置
  -> docs/user/permissions-user.md -> L2  权限模式
```

#### 排障路径

```
docs/user/troubleshooting.md     ->  L1  常见问题与解决方案
  -> docs/reference/cli.md       ->  L2  CLI 全局参数（--debug）
  -> docs/user/providers-user.md ->  L2  认证问题排查
```

#### 终端用户的关注重点

1. **CLI 命令行参数**：如何启动会话、如何继续会话、如何使用 `--print` 单次查询
2. **Provider 配置**：如何配置 API 密钥、如何切换 Provider、如何使用 Claude 订阅
3. **权限控制**：`--permission-mode` 的三种模式（`default`、`plan`、`full_auto`）
4. **沙箱配置**：何时启用沙箱、网络和文件系统限制如何设置
5. **渠道接入**：Telegram、Discord、Slack 等渠道的配置和使用

> 终端用户不需要深入了解 Engine 层、Swarm 层或 Coordinator 层的实现细节。

---

### 开发者

开发者指在 OpenHarness 基础上进行集成、插件开发或功能定制的用户。

#### 集成开发路径

```
docs/dev/architecture-overview.md -> L1  架构总览
  -> docs/dev/core/agent-loop.md   -> L3  Agent 循环详细
  -> docs/dev/core/tools.md         -> L3  工具系统
  -> docs/dev/core/mcp.md           -> L3  MCP 协议集成
  -> docs/dev/core/plugins.md       -> L3  插件系统
  -> docs/reference/config.md       -> L2  完整配置参考
  -> docs/reference/data-models.md  -> L2  数据模型参考
```

#### 渠道集成路径

```
docs/dev/infrastructure/channels.md -> L3  渠道基础设施
  -> docs/reference/data-models.md    -> L2  Channel 层数据模型
  -> docs/dev/core/mcp.md            -> L3  MCP 工具集成
```

#### 开发者关注重点

1. **数据模型**：所有核心 Pydantic 模型的结构和字段含义
2. **配置系统**：`Settings` 模型、`ProviderProfile` 配置、`McpServerConfig` 配置
3. **工具注册**：`BaseTool` 抽象类、`ToolRegistry` 注册机制
4. **MCP 集成**：stdio / HTTP / WebSocket 三种传输配置
5. **插件架构**：`LoadedPlugin`、`PluginCommandDefinition`、Hook 机制
6. **渠道桥接**：`ChannelBridge` 如何连接消息总线和查询引擎

---

### 贡献者

贡献者指为 OpenHarness 核心代码库提交 PR 或参与架构决策的用户。

#### 核心贡献路径

```
docs/dev/design-principles.md    -> L1  设计原则
  -> docs/dev/architecture-overview.md -> L1  整体架构
  -> docs/dev/architecture/        -> L3  架构详细文档
  -> docs/dev/core/coordinator.md  -> L3  协调器设计
  -> docs/dev/core/agent-loop.md   -> L3  Agent 循环实现
  -> docs/dev/core/state.md        -> L3  状态管理
```

#### 问题修复路径

```
docs/dev/risk-technical-debt.md -> L1  风险与技术债
  -> docs/dev/architecture/        -> L3  相关模块架构
  -> docs/reference/data-models.md  -> L2  受影响的数据模型
  -> 源码阅读                      -> L3  定位具体实现
```

#### 贡献者关注重点

1. **设计原则**：为什么这样设计、有哪些约束和权衡
2. **架构决策**：各模块的职责边界、数据流和控制流
3. **风险与技术债**：已知问题、尚未解决的复杂区域
4. **模块设计**：Engine 层、Swarm 层、Coordinator 层的详细设计
5. **测试策略**：如何验证改动不会引入回归

---

## 文档依赖关系图

以下是有向依赖图，箭头表示"先读箭头起点的文档"：

```
                              ┌─────────────────────┐
                              │  getting-started.md  │
                              │  (L1 快速上手)      │
                              └──────────┬──────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
          ┌──────────────────┐  ┌────────────────┐  ┌──────────────────┐
          │ architecture-    │  │  cli.md         │  │ channels-user.md │
          │ overview.md      │  │  (L2 CLI 参考)  │  │  (L1 渠道用户)   │
          │ (L1 架构总览)    │  └───────┬────────┘  └────────┬─────────┘
          └────────┬─────────┘          │                   │
                   │                   │                   │
                   │         ┌──────────┴───────────────────┘
                   │         │
                   ▼         ▼
          ┌──────────────────────────────────────────┐
          │         architecture/ (L3)              │
          │  core/ 模块详细文档                      │
          │  infrastructure/ 基础设施文档            │
          └────────┬─────────────────────────────────┘
                   │
                   ▼
          ┌─────────────────────────────────────────┐
          │  config.md   (L2 配置参考)               │
          │  data-models.md (L2 数据模型)            │
          └────────┬────────────────────────────────┘
                   │
                   ▼
          ┌──────────────────────────────────────────┐
          │  swarm.md  (L3 Swarm 团队协作)            │
          │  mcp.md    (L3 MCP 协议集成)              │
          │  plugins.md (L3 插件系统)                 │
          └──────────────────────────────────────────┘
```

### 核心依赖链

**路径 A（配置驱动）：**
```
getting-started.md -> cli.md -> config.md -> data-models.md
```

**路径 B（架构驱动）：**
```
architecture-overview.md -> architecture/ -> core/* -> data-models.md
```

**路径 C（集成驱动）：**
```
getting-started.md -> channels-user.md -> infrastructure/channels.md
-> data-models.md (ChannelBridge、InboundMessage)
```

---

## L1/L2/L3 阅读建议

### L1（概览层）

适合对象：
- 刚接触 OpenHarness 的新用户
- 需要了解系统概览的项目经理或架构师
- 评估是否采用 OpenHarness 的决策者

阅读策略：
- 通读所有 L1 文档，建立全局认知
- 不必记住所有细节，重点是理解系统提供的核心能力
- 遇到具体问题时再查阅 L2 参考文档

关键 L1 文档：

| 文档 | 必读原因 |
|------|----------|
| `docs/user/getting-started.md` | 安装、配置、首次运行 |
| `docs/dev/architecture-overview.md` | 系统整体架构和模块关系 |
| `docs/dev/design-principles.md` | 设计哲学和约束 |
| `docs/dev/risk-technical-debt.md` | 已知风险和技术债 |

### L2（参考层）

适合对象：
- 日常使用 OpenHarness 的开发者
- 需要精确配置参数的用户
- 需要理解数据结构的插件开发者

阅读策略：
- 按需查阅，不必从头到尾阅读
- `cli.md` 是最常用的参考文档，建议熟悉所有子命令
- `config.md` 在配置复杂场景时查阅
- `data-models.md` 在开发新工具或 MCP 服务器时查阅

关键 L2 文档：

| 文档 | 常用场景 |
|------|----------|
| `docs/reference/cli.md` | 所有 CLI 命令和参数 |
| `docs/reference/config.md` | 所有配置字段和环境变量 |
| `docs/reference/data-models.md` | 所有 Pydantic/dataclass 模型 |
| `docs/user/troubleshooting.md` | 常见错误和解决方法 |

### L3（架构详细层）

适合对象：
- 核心代码贡献者
- 需要深度定制的集成开发者
- 需要修复复杂 Bug 的维护者

阅读策略：
- 在需要深入了解某个模块时选择性阅读
- 阅读前先通过 Grep 定位相关源码
- 文档和源码相互印证

关键 L3 文档：

| 文档 | 适用场景 |
|------|----------|
| `docs/dev/core/agent-loop.md` | 修改 Agent 行为、理解工具调用循环 |
| `docs/dev/core/tools.md` | 开发新工具、修改工具注册逻辑 |
| `docs/dev/core/mcp.md` | 深度 MCP 集成、自定义 MCP 服务器 |
| `docs/dev/core/plugins.md` | 开发新插件、Hook 系统 |
| `docs/dev/core/coordinator.md` | 修改 Swarm 行为、理解任务协调 |
| `docs/dev/core/state.md` | 状态管理和持久化 |
| `docs/dev/infrastructure/channels.md` | 渠道基础设施、消息总线 |

---

## 关键文档推荐阅读顺序

### 顺序一：完整新人路径（按顺序阅读）

```
1. docs/user/getting-started.md          [15 分钟]  安装和首次运行
2. docs/dev/architecture-overview.md     [20 分钟]  系统架构概览
3. docs/reference/cli.md                 [30 分钟]  CLI 完整参考
4. docs/reference/config.md              [30 分钟]  配置完整参考
5. docs/user/troubleshooting.md          [15 分钟]  常见问题
```

### 顺序二：开发者快速上手（按顺序阅读）

```
1. docs/dev/architecture-overview.md     [20 分钟]  架构总览
2. docs/reference/data-models.md          [45 分钟]  数据模型一览
3. docs/dev/core/agent-loop.md           [30 分钟]  Agent 循环
4. docs/dev/core/mcp.md                 [30 分钟]  MCP 集成
5. docs/dev/core/plugins.md              [30 分钟]  插件系统
```

### 顺序三：核心贡献者路径（按顺序阅读）

```
1. docs/dev/design-principles.md         [20 分钟]  设计原则
2. docs/dev/risk-technical-debt.md      [15 分钟]  风险与技术债
3. docs/dev/architecture-overview.md     [20 分钟]  架构总览
4. docs/dev/architecture/               [60 分钟]  各模块详细架构
5. docs/reference/data-models.md         [45 分钟]  数据模型（与源码对照）
6. docs/dev/core/state.md               [30 分钟]  状态管理
```

### 顺序四：渠道集成路径（按顺序阅读）

```
1. docs/user/channels-user.md            [15 分钟]  渠道接入概览
2. docs/dev/infrastructure/channels.md   [30 分钟]  渠道基础设施
3. docs/reference/data-models.md         [20 分钟]  ChannelBridge、InboundMessage
4. docs/reference/cli.md                 [10 分钟]  渠道相关 CLI
```

---

## 各角色关注重点速查

### 终端用户速查表

| 需求 | 推荐文档 |
|------|----------|
| 如何安装 | `docs/user/getting-started.md` |
| 如何启动对话 | `docs/reference/cli.md` -> `oh` 主命令 |
| 如何单次查询 | `docs/reference/cli.md` -> `--print` 参数 |
| 如何配置 API | `docs/user/providers-user.md` |
| 如何切换 Provider | `docs/reference/cli.md` -> `oh provider use` |
| 如何配置 MCP | `docs/reference/cli.md` -> `oh mcp add` |
| 如何启用沙箱 | `docs/reference/config.md` -> `SandboxSettings` |
| 如何使用 cron | `docs/reference/cli.md` -> `oh cron` |
| 认证失败怎么办 | `docs/user/troubleshooting.md` |

### 开发者速查表

| 需求 | 推荐文档 |
|------|----------|
| 如何配置 Provider | `docs/reference/config.md` -> `ProviderProfile` |
| 如何配置 MCP | `docs/reference/config.md` -> `McpServerConfig` |
| 如何注册工具 | `docs/reference/data-models.md` -> `BaseTool`、`ToolRegistry` |
| 如何开发插件 | `docs/dev/core/plugins.md` |
| 如何定义 Agent | `docs/reference/data-models.md` -> `AgentDefinition` |
| 如何配置 Hook | `docs/reference/config.md` -> `HookDefinition` |
| 如何使用 Swarm | `docs/dev/core/swarm.md` |
| 认证流程是什么 | `docs/dev/infrastructure/auth.md` |

### 贡献者速查表

| 需求 | 推荐文档 |
|------|----------|
| 为什么这样设计 | `docs/dev/design-principles.md` |
| 模块边界在哪里 | `docs/dev/architecture-overview.md` |
| 数据流是怎样的 | `docs/dev/architecture/` 各模块详细文档 |
| 有什么已知问题 | `docs/dev/risk-technical-debt.md` |
| 如何测试改动 | 测试目录下的 `README.md` |
| 如何提交 PR | 项目根目录 `CONTRIBUTING.md` |

---

## 文档版本同步

OpenHarness CLI 当前版本：**0.1.6**

配置参考版本对应：`Settings` Pydantic 模型 v0.1.6

> 如果你发现文档内容与实际行为不一致，请查看 `src/openharness/cli.py` 中的 `__version__` 变量确认版本，并检查源码中是否有新增的 CLI 参数。

---

## 反馈与改进

如果你发现文档缺失、错误或难以理解，欢迎通过以下方式反馈：

- 在 GitHub 仓库提交 Issue
- 在文档目录下提交 PR
- 通过 `oh` 会话反馈给维护者

> 文档持续更新中，部分 L3 模块文档（如 `core/swarm.md`、`core/state.md`）可能尚未完全覆盖。
