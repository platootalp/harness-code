# Claude Code 架构设计文档

> Claude Code 是一个功能完善的 CLI 应用，用于在终端中与 Claude AI 交互，执行软件工程任务。本文档提供其架构的深度分析。

---

## 目录

1. [系统概述](#1-系统概述)
2. [技术栈](#2-技术栈)
3. [核心架构模式](#3-核心架构模式)
4. [工具系统 (Tools)](docs/design/01-TOOL-SYSTEM.md)
5. [命令系统 (Commands)](docs/design/02-COMMAND-SYSTEM.md)
6. [查询引擎 (Query Engine)](docs/design/03-QUERY-ENGINE.md)
7. [状态管理 (State Management)](docs/design/04-STATE-MANAGEMENT.md)
8. [服务层 (Services)](docs/design/05-SERVICES-LAYER.md)
9. [桥接系统 (Bridge)](docs/design/06-BRIDGE-SYSTEM.md)
10. [UI 组件系统](#10-ui-组件系统)
11. [协调器与插件系统](#11-协调器与插件系统)
12. [技能系统 (Skills)](docs/design/07-SKILLS-SYSTEM.md)
13. [Agent 系统](docs/design/08-AGENT-SYSTEM.md)

---

## 详细设计文档

每个核心模块都有独立的详细设计文档：

| 模块 | 文档路径 |
|------|----------|
| 工具系统 | [docs/design/01-TOOL-SYSTEM.md](docs/design/01-TOOL-SYSTEM.md) |
| 命令系统 | [docs/design/02-COMMAND-SYSTEM.md](docs/design/02-COMMAND-SYSTEM.md) |
| 查询引擎 | [docs/design/03-QUERY-ENGINE.md](docs/design/03-QUERY-ENGINE.md) |
| 状态管理 | [docs/design/04-STATE-MANAGEMENT.md](docs/design/04-STATE-MANAGEMENT.md) |
| 服务层 | [docs/design/05-SERVICES-LAYER.md](docs/design/05-SERVICES-LAYER.md) |
| 桥接系统 | [docs/design/06-BRIDGE-SYSTEM.md](docs/design/06-BRIDGE-SYSTEM.md) |
| 技能系统 | [docs/design/07-SKILLS-SYSTEM.md](docs/design/07-SKILLS-SYSTEM.md) |
| Agent 系统 | [docs/design/08-AGENT-SYSTEM.md](docs/design/08-AGENT-SYSTEM.md) |

---

## 1. 系统概述

### 1.1 项目规模

| 指标 | 数值 |
|------|------|
| 文件总数 | ~1,900 |
| 代码行数 | 512,000+ |
| 工具数量 | ~45 |
| 命令数量 | ~70+ |
| UI 组件 | ~146 |

### 1.2 核心职责

Claude Code 的主要职责：

1. **对话交互** - 通过 REPL 与用户进行多轮对话
2. **工具执行** - 调用文件系统、Shell、LSP 等工具
3. **代码编辑** - 理解和修改代码库
4. **上下文管理** - 压缩和管理对话上下文
5. **IDE 集成** - 通过桥接系统与 VS Code/JetBrains 通信
6. **多 Agent 协调** - 支持并行任务执行

---

## 2. 技术栈

### 2.1 核心技术

| 类别 | 技术 | 用途 |
|------|------|------|
| 运行时 | Bun | JavaScript 运行时，打包优化 |
| 语言 | TypeScript (strict) | 类型安全 |
| 终端 UI | React + Ink | CLI UI 渲染 |
| CLI 解析 | Commander.js | 命令行参数处理 |
| Schema 验证 | Zod v4 | 运行时类型验证 |
| 代码搜索 | ripgrep | 高性能文本搜索 |
| API 客户端 | @anthropic-ai/sdk | Anthropic API 调用 |

### 2.2 集成协议

| 协议 | 用途 |
|------|------|
| MCP (Model Context Protocol) | 扩展工具服务器 |
| LSP (Language Server Protocol) | IDE 功能集成 |
| SSE/WebSocket | 远程会话通信 |
| OAuth 2.0 + JWT | 认证 |

### 2.3 辅助服务

| 服务 | 技术 |
|------|------|
| 遥测 | OpenTelemetry + gRPC |
| 特性开关 | GrowthBook SDK |
| 密钥存储 | macOS Keychain |

---

## 3. 核心架构模式

### 3.1 模块化单体

Claude Code 采用**模块化单体 (Modular Monolith)** 架构：

```
src/
├── main.tsx              # 入口 (~803KB)
├── QueryEngine.ts        # 核心查询引擎 (~46KB)
├── query.ts              # 查询管道 (~68KB)
├── Tool.ts               # 工具类型定义 (~29KB)
├── commands.ts           # 命令注册表 (~25KB)
├── tools.ts              # 工具注册表 (~17KB)
├── commands/             # ~70 个斜杠命令
├── tools/                # ~45 个工具实现
├── components/           # ~146 个 UI 组件
├── services/             # 外部服务集成
├── state/                # 状态管理
├── bridge/               # IDE 桥接
└── ...
```

### 3.2 数据流总览

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  main.tsx (Commander.js)                                    │
│  - CLI 参数解析                                              │
│  - 启动初始化                                                │
│  - 并行预取 (MDM、Keychain)                                  │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  QueryEngine.submitMessage()                                 │
│  - 会话状态管理                                              │
│  - 系统提示词构建                                            │
│  - 消息处理                                                  │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  query.ts (AsyncGenerator)                                   │
│  - 上下文压缩管道                                            │
│  - API 调用 (callModel)                                       │
│  - 流式响应处理                                              │
└─────────────────────────────────────────────────────────────┘
    │
    ├──► Anthropic API ────────────────────────────────────────►
    │                                                          │
    ▼                                                          │
┌─────────────────────────────────────────────────────────────┐
│  工具编排 (toolOrchestration.ts)                             │
│  - 权限检查                                                  │
│  - 并发控制 (MAX_TOOL_USE_CONCURRENCY=10)                    │
│  - 串行/并行执行                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  工具执行 (toolExecution.ts)                                  │
│  - Input Schema 验证 (Zod)                                    │
│  - PreToolUse Hooks                                         │
│  - 权限检查                                                  │
│  - tool.call()                                               │
│  - PostToolUse Hooks                                        │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  工具实现 (tools/*/)                                          │
│  - BashTool / FileEditTool / GrepTool 等                    │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 关键设计模式

#### 工厂模式 (buildTool)

所有工具通过 `buildTool()` 工厂函数创建：

```typescript
// src/Tool.ts:783-792
export function buildTool<D extends AnyToolDef>(def: D): BuiltTool<D> {
  return {
    ...TOOL_DEFAULTS,
    userFacingName: () => def.name,
    ...def,
  } as BuiltTool<D>
}

const TOOL_DEFAULTS = {
  isEnabled: () => true,
  isConcurrencySafe: (_input?: unknown) => false,
  isReadOnly: (_input?: unknown) => false,
  isDestructive: (_input?: unknown) => false,
  checkPermissions: (input, _ctx) =>
    Promise.resolve({ behavior: 'allow', updatedInput: input }),
  // ...
}
```

#### 懒加载模式

```typescript
// 特性开关控制工具加载
const SleepTool = feature('PROACTIVE') || feature('KAIROS')
  ? require('./tools/SleepTool/SleepTool.js').SleepTool
  : null

// Zod Schema 懒解析
const inputSchema = lazySchema(() =>
  z.strictObject({ ... })
)
```

#### Observable Store 模式

```typescript
// src/state/store.ts (~35 行核心实现)
export type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (listener: Listener) => () => void
}
```

#### AsyncGenerator 模式

查询引擎使用 AsyncGenerator 实现流式处理：

```typescript
async function* submitMessage(
  prompt: string,
  options: MessageOptions
): AsyncGenerator<SDKMessage> {
  // 流式产生消息
  yield { type: 'assistant', content: [...] }
  yield { type: 'tool_use', id: '1', name: 'Bash', input: {...} }
  // ...
}
```

---

## 4. 工具系统 (Tools)

### 4.1 架构概述

工具是 Claude Code 最核心的扩展机制。每个工具是一个自包含的模块，提供：

- **Input Schema** - Zod 定义的输入验证
- **Permission Model** - 权限检查和决策
- **Execution Logic** - 工具执行逻辑
- **UI Rendering** - 工具使用/结果的 React 渲染

### 4.2 工具类型定义

```typescript
// src/Tool.ts:362-695
interface Tool<Input, Output, Progress> {
  // 必需属性
  name: string
  inputSchema: Input  // Zod schema
  call(args, context, canUseTool, parentMessage, onProgress?): Promise<ToolResult<Output>>
  description(input, options): Promise<string>
  prompt(options): Promise<string>
  userFacingName(input): string
  maxResultSizeChars: number
  mapToolResultToToolResultBlockParam(content, toolUseID): ToolResultBlockParam
  renderToolUseMessage(input, options): React.ReactNode

  // 可选属性
  aliases?: string[]
  isConcurrencySafe?(input): boolean
  isReadOnly?(input): boolean
  isDestructive?(input): boolean
  checkPermissions?(input, context): Promise<PermissionResult>
  validateInput?(input, context): Promise<ValidationResult>
  getPath?(input): string
  // ...
}
```

### 4.3 工具执行流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. Input Schema 验证 (Zod safeParse)                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. validateInput() Hook                                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. PreToolUse Hooks                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 权限检查 (checkPermissions / canUseTool)                  │
│      - deny / allow / ask / passthrough                      │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
         [denied]                        [allowed]
              │                               │
              ▼                               ▼
    返回权限拒绝错误              ┌─────────────────────────────────────────┐
                                │ 5. tool.call() 执行                      │
                                └─────────────────────────────────────────┘
                                                      │
                                                      ▼
                                ┌─────────────────────────────────────────┐
                                │ 6. PostToolUse Hooks                    │
                                └─────────────────────────────────────────┘
                                                      │
                                                      ▼
                                ┌─────────────────────────────────────────┐
                                │ 7. 返回 ToolResult                       │
                                └─────────────────────────────────────────┘
```

### 4.4 工具分类

#### 文件操作

| 工具 | 文件 | 用途 |
|------|------|------|
| FileReadTool | `tools/FileReadTool/` | 读取文件（文本、图片、PDF、笔记本） |
| FileEditTool | `tools/FileEditTool/` | 部分文件修改（字符串替换） |
| FileWriteTool | `tools/FileWriteTool/` | 创建/覆盖文件 |
| NotebookEditTool | `tools/NotebookEditTool/` | 编辑 Jupyter 笔记本 |

#### Shell 操作

| 工具 | 文件 | 用途 |
|------|------|------|
| BashTool | `tools/BashTool/` | 执行 bash 命令 |
| PowerShellTool | `tools/PowerShellTool/` | 执行 PowerShell 命令 |

#### Agent 与任务管理

| 工具 | 文件 | 用途 |
|------|------|------|
| AgentTool | `tools/AgentTool/` | 派生子 Agent |
| TaskCreateTool | `tools/TaskCreateTool/` | 创建任务 |
| TaskUpdateTool | `tools/TaskUpdateTool/` | 更新任务 |
| TaskStopTool | `tools/TaskStopTool/` | 停止任务 |

#### 搜索与发现

| 工具 | 文件 | 用途 |
|------|------|------|
| GlobTool | `tools/GlobTool/` | 文件模式匹配 |
| GrepTool | `tools/GrepTool/` | 文本内容搜索 |
| ToolSearchTool | `tools/ToolSearchTool/` | 查找工具 |

#### 外部集成

| 工具 | 文件 | 用途 |
|------|------|------|
| WebSearchTool | `tools/WebSearchTool/` | 网络搜索 |
| WebFetchTool | `tools/WebFetchTool/` | 获取 URL 内容 |
| MCPTool | `tools/MCPTool/` | MCP 服务器工具 |
| SkillTool | `tools/SkillTool/` | 执行技能 |

#### 模式控制

| 工具 | 文件 | 用途 |
|------|------|------|
| EnterPlanModeTool | `tools/EnterPlanModeTool/` | 进入计划模式 |
| ExitPlanModeV2Tool | `tools/ExitPlanModeTool/` | 退出计划模式 |
| EnterWorktreeTool | `tools/EnterWorktreeTool/` | 进入 git worktree |
| ExitWorktreeTool | `tools/ExitWorktreeTool/` | 退出 git worktree |

### 4.5 工具注册与组装

```typescript
// src/tools.ts
export function getAllBaseTools(): Tool[] {
  // 根据特性开关过滤工具
  const tools: Tool[] = [
    BashTool,
    FileEditTool,
    FileReadTool,
    // ...
  ]
  return tools.filter(tool => {
    const isEnabled = tool.isEnabled?.() ?? true
    return isEnabled
  })
}

export function assembleToolPool(
  permissionContext: PermissionContext,
  mcpTools: Tool[]
): AssembledToolPool {
  // 合并内置工具和 MCP 工具
  const baseTools = getTools(permissionContext)
  return {
    tool: [...baseTools, ...mcpTools],
    // ...
  }
}
```

### 4.6 并发控制

工具执行支持**并发安全**机制：

```typescript
// src/services/tools/toolOrchestration.ts:91-116
function partitionToolCalls(toolUseMessages, toolUseContext): Batch[] {
  return toolUseMessages.reduce((acc, toolUse) => {
    const tool = findToolByName(toolUseContext.options.tools, toolUse.name)
    const isConcurrencySafe = tool?.isConcurrencySafe?.(parsedInput?.data) ?? false

    // 将连续的并发安全工具分组
    if (isConcurrencySafe && acc[acc.length - 1]?.isConcurrencySafe) {
      acc[acc.length - 1]!.blocks.push(toolUse)
    } else {
      acc.push({ isConcurrencySafe, blocks: [toolUse] })
    }
    return acc
  }, [])
}
```

- **并发执行**：最多 10 个 `isConcurrencySafe=true` 的工具并行运行
- **串行执行**：非并发安全工具按顺序执行

### 4.7 权限系统

```typescript
// src/types/permissions.ts
type PermissionDecision =
  | { behavior: 'allow'; updatedInput?: Record<string, unknown> }
  | { behavior: 'deny'; message?: string; decisionReason?: PermissionDecisionReason }
  | { behavior: 'ask'; message?: string; suggestions?: PermissionUpdate[] }
  | { behavior: 'passthrough' }

// 权限规则匹配 (src/utils/permissions/shellRuleMatching.ts)
// Bash(git *) → allow
// Bash(rm *) → deny
// FileEdit(*.env) → ask
```

---

## 5. 命令系统 (Commands)

### 5.1 命令类型

命令分为三种类型：

| 类型 | 执行方式 | 用途 |
|------|----------|------|
| `prompt` | 调用 `getPromptForCommand()` 返回 ContentBlockParam[] | 技能类命令 |
| `local` | 同步 `call()` 函数 | 简单本地命令 |
| `local-jsx` | 懒加载 React 组件 | 需要复杂 UI 的命令 |

### 5.2 命令定义

```typescript
// src/types/command.ts
type CommandBase = {
  name: string
  description: string
  aliases?: string[]
  isEnabled?: () => boolean
  isHidden?: boolean
  userInvocable?: boolean  // 是否允许 /command 语法
  argumentHint?: string
  whenToUse?: string
  // ...
}

type PromptCommand = CommandBase & {
  type: 'prompt'
  contentLength: number
  allowedTools?: string[]   // 工具白名单
  model?: string
  getPromptForCommand(args, context): Promise<ContentBlockParam[]>
  // Skill 相关字段
  hooks?: HooksSettings
  context?: 'inline' | 'fork'
  agent?: string
  paths?: string[]  // 条件激活
}

type LocalCommand = CommandBase & {
  type: 'local'
  supportsNonInteractive: boolean
  load: () => Promise<LocalCommandModule>
}

type LocalJSXCommand = CommandBase & {
  type: 'local-jsx'
  load: () => Promise<LocalJSXCommandModule>
}
```

### 5.3 命令执行流程

```
用户输入 "/commit -m 'fix bug'"
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  parseSlashCommand()                                          │
│  → { commandName: 'commit', args: "-m 'fix bug'", isMcp: false }│
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  processSlashCommand()                                        │
│  1. 查找命令 (name 或 alias)                                  │
│  2. 检查 userInvocable                                       │
│  3. 根据类型执行                                             │
└─────────────────────────────────────────────────────────────┘
           │
           ├──► prompt 类型 ────────────────────────────────────►
           │    getPromptForCommand() → ContentBlockParam[]      │
           │    → 成为发送给模型的消息                            │
           │                                                      │
           ├──► local 类型 ────────────────────────────────────►
           │    load().then(m => m.call(args, context))          │
           │    → 返回 { type: 'text', value: string }           │
           │                                                      │
           └──► local-jsx 类型 ─────────────────────────────────►
                load().then(m => m.component)                    │
                → 渲染 React 组件，通过 onDone 回调              │
```

### 5.4 命令分类

#### 内置命令

| 类别 | 命令 |
|------|------|
| Git | `/commit`, `/branch` |
| 审查 | `/review`, `/ultrareview` |
| 会话 | `/resume`, `/session`, `/clear` |
| 配置 | `/config`, `/model`, `/theme`, `/keybindings` |
| 技能/插件 | `/skills`, `/plugin` |
| 分析 | `/diff`, `/cost`, `/usage`, `/stats` |
| 开发 | `/init`, `/ide`, `/terminalSetup`, `/permissions` |
| 工具 | `/help`, `/exit`, `/btw`, `/share` |
| MCP | `/mcp`, `/chrome` |

### 5.5 命令解析

```typescript
// src/utils/slashCommandParsing.ts
export function parseSlashCommand(input: string): ParsedSlashCommand | null {
  if (!trimmedInput.startsWith('/')) return null

  const withoutSlash = trimmedInput.slice(1)
  const words = withoutSlash.split(' ')

  // 检查 MCP 命令格式 "/mcp:tool (MCP) arg1"
  if (words.length > 1 && words[1] === '(MCP)') {
    commandName = commandName + ' (MCP)'
    isMcp = true
    argsStartIndex = 2
  }

  return { commandName: words[0], args: words.slice(argsStartIndex).join(' '), isMcp }
}
```

### 5.6 命令注册表

```typescript
// src/commands.ts
const COMMANDS = memoize((): Command[] => [
  addDir, advisor, agents, branch, btw,
  // ... 70+ commands
])

export async function getCommands(cwd: string): Promise<Command[]> {
  const allCommands = await loadAllCommands(cwd)

  // 多源加载
  const [
    { skillDirCommands, pluginSkills, bundledSkills },
    pluginCommands,
  ] = await Promise.all([
    getSkills(cwd),       // ~/.claude/skills, .claude/skills
    getPluginCommands(),   // 插件命令
  ])

  return [
    ...bundledSkills,      // 内置技能
    ...skillDirCommands,  // 技能目录
    ...pluginCommands,     // 插件
    ...COMMANDS(),         // 内置命令
  ]
}
```

---

## 6. 查询引擎 (Query Engine)

### 6.1 核心组件

| 文件 | 大小 | 职责 |
|------|------|------|
| `QueryEngine.ts` | ~46KB | 会话状态管理、查询编排、SDK 消息格式 |
| `query.ts` | ~68KB | 核心查询循环、API 调用、工具执行 |

### 6.2 QueryEngine 类

```typescript
// src/QueryEngine.ts
class QueryEngine {
  private config: QueryEngineConfig
  private mutableMessages: Message[]
  private abortController: AbortController
  private permissionDenials: SDKPermissionDenial[]
  private totalUsage: NonNullableUsage
  private readFileState: FileStateCache
  private discoveredSkillNames = new Set<string>()

  async* submitMessage(
    prompt: string,
    options: MessageOptions
  ): AsyncGenerator<SDKMessage> {
    // 1. 系统提示词构建
    // 2. 消息处理 (processUserInput)
    // 3. 查询循环
    // 4. 预算执行 (USD budget, token limit)
    // 5. 结果确定
  }
}
```

### 6.3 查询管道 (query.ts)

```typescript
// src/query.ts - AsyncGenerator
async function* query(
  messages: Message[],
  options: QueryOptions
): AsyncGenerator<SDKMessage | TombstoneMessage | ToolUseSummaryMessage> {

  // 1. 预循环设置
  //    - 内存预取 (非阻塞)
  //    - 历史裁剪 (HISTORY_SNIP)
  //    - 上下文压缩 (CONTEXT_COLLAPSE)
  //    - 自动压缩 (autocompact)

  // 2. API 调用
  for await (const message of callModel(...)) {
    // 3. 流式响应处理
    //    - message_start: 重置 usage
    //    - content_block: 处理文本/工具块
    //    - message_delta: 捕获 stop_reason
    //    - message_stop: 累计 usage

    // 4. 工具执行
    if (streamingToolExecutor) {
      // 流式工具执行
      for (const result of streamingToolExecutor.getCompletedResults()) {
        yield result.message
      }
    } else {
      // 批量工具执行
      for await (const update of runTools(...)) {
        yield update.message
      }
    }

    // 5. 递归继续 (新消息追加到 messages)
    yield* query(updatedMessages, updatedOptions)
  }
}
```

### 6.4 上下文压缩管道

```
┌─────────────────────────────────────────────────────────────┐
│  snipCompactIfNeeded (HISTORY_SNIP)                          │
│  - 裁剪过长的历史消息                                        │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  microcompact (message-level compaction)                    │
│  - 清除旧工具结果内容                                        │
│  - 保留缓存编辑 ID                                           │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  applyCollapsesIfNeeded (CONTEXT_COLLAPSE)                   │
│  - 折叠连续消息组                                            │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  autocompact (turn-level summarization)                      │
│  - 通过额外 API 调用生成摘要                                 │
│  - 替换原始消息                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.5 重试机制

| 错误类型 | 恢复策略 |
|----------|----------|
| API Error | 指数退避重试 (yield `api_retry`) |
| prompt-too-long | 尝试压缩，失败则降级模型 |
| max-output-tokens | 8k → 64k (如启用)，或注入恢复消息 |
| Model Fallback | 切换到备用模型 |

---

## 7. 状态管理 (State Management)

### 7.1 架构概述

状态管理采用 **Context-based observable store 模式**：

```
┌─────────────────────────────────────────────────────────────┐
│                    AppStateProvider                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              AppStoreContext (React Context)         │    │
│  │  ┌─────────────────────────────────────────────┐     │    │
│  │  │      Store<AppState> (createStore)            │     │    │
│  │  │  ┌──────────┬──────────────┬────────────┐  │     │    │
│  │  │  │ getState │  setState    │ subscribe │  │     │    │
│  │  │  └──────────┴──────────────┴────────────┘  │     │    │
│  │  └─────────────────────────────────────────────┘     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  useAppState(selector) ←── useSyncExternalStore (并发安全)  │
│  useSetAppState()      ←── 返回 store.setState              │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 核心 Store 实现

```typescript
// src/state/store.ts (~35 行)
export type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (listener: Listener) => () => void
}

export function createStore<T>(
  initialState: T,
  onChange?: OnChange<T>,
): Store<T> {
  let state = initialState
  const listeners = new Set<Listener>()

  return {
    getState: () => state,
    setState: (updater) => {
      const next = updater(state)
      if (!Object.is(next, state)) {  // Memoization guard
        state = next
        listeners.forEach(l => l(state))
        onChange?.(state)
      }
    },
    subscribe: (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}
```

### 7.3 AppState 类型结构

```typescript
// src/state/AppStateStore.ts (~22KB, ~450 行类型定义)
type AppState = {
  // 会话与 UI 状态
  settings: SettingsJson
  statusLineText: string | undefined
  expandedView: 'none' | 'tasks' | 'teammates'

  // 远程/桥接状态
  remoteSessionUrl: string | undefined
  remoteConnectionStatus: ConnectionStatus

  // 任务状态
  tasks: { [taskId: string]: TaskState }
  foregroundedTaskId?: string
  viewingAgentTaskId?: string

  // MCP/插件状态
  mcp: { clients: MCPServerConnection[], tools: Tool[], ... }
  plugins: { enabled: LoadedPlugin[], disabled: LoadedPlugin[], ... }

  // 推测/AI 状态
  speculation: SpeculationState
  thinkingEnabled: boolean

  // 工具特定状态
  tungstenPanelVisible?: boolean
  bagelActive?: boolean
  replContext?: ReplContext
}
```

### 7.4 React Hooks

```typescript
// src/state/AppState.tsx

// 订阅状态切片
export function useAppState<T>(selector: (state: AppState) => T): T {
  const store = useAppStore()
  const get = () => selector(store.getState())
  return useSyncExternalStore(store.subscribe, get, get)
  // Object.is 比较防止不必要的重渲染
}

// 获取更新器 (不订阅)
export function useSetAppState(): (updater: (prev: AppState) => AppState) => void {
  return useAppStore().setState
}
```

### 7.5 状态变更处理

```typescript
// src/state/onChangeAppState.ts
// 状态变更的中央侧效应协调器

onChangeAppState({ prevState, newState }) {
  // 权限模式同步
  if (prevMode !== newMode) {
    notifyPermissionModeChanged(newMode)
    notifySessionMetadataChanged({ permission_mode: newExternal, ... })
  }

  // 设置持久化
  if (newState.mainLoopModel !== null) {
    updateSettingsForSource('userSettings', { model: newState.mainLoopModel })
  }

  // 认证缓存失效
  if (newState.settings !== oldState.settings) {
    clearApiKeyHelperCache()
    clearAwsCredentialsCache()
  }
}
```

---

## 8. 服务层 (Services)

### 8.1 服务架构

```
src/services/
├── api/           # Anthropic API 客户端
│   ├── client.ts  # 多提供者支持 (Direct/Bedrock/Foundry/Vertex)
│   ├── bootstrap.ts # 引导数据获取
│   ├── filesApi.ts # 文件附件管理
│   └── claude.ts  # 核心 API 交互
├── mcp/           # Model Context Protocol
│   ├── useManageMCPConnections.ts # React Hook
│   ├── client.ts  # MCP 客户端核心
│   └── channelNotification.ts # 通道权限
├── oauth/         # OAuth 2.0 认证
│   ├── index.ts   # OAuthService 类
│   └── client.ts  # OAuth 工具函数
├── lsp/           # Language Server Protocol
│   ├── LSPServerManager.ts # 服务器管理
│   ├── LSPServerInstance.ts # 单个服务器生命周期
│   └── manager.ts # 单例包装
├── analytics/    # GrowthBook 特性开关
│   ├── growthbook.ts # 特性开关 SDK
│   ├── sink.ts   # 事件路由
│   └── datadog.ts # Datadog 集成
├── compact/       # 上下文压缩
│   ├── compact.ts # 完整压缩
│   └── microCompact.ts # 轻量级压缩
├── plugins/       # 插件系统
│   └── PluginInstallationManager.ts
└── tokenEstimation.ts # Token 计数
```

### 8.2 API 服务 (client.ts)

多提供者支持：

```typescript
// src/services/api/client.ts
export function createApiClient(config: ClientConfig): ApiClient {
  // 自动检测提供者
  if (config.provider === 'aws-bedrock') {
    return createBedrockClient(config)
  } else if (config.provider === 'azure-foundry') {
    return createFoundryClient(config)
  } else if (config.provider === 'vertex-ai') {
    return createVertexClient(config)
  } else {
    return createDirectClient(config)  // 标准 api.anthropic.com
  }
}
```

### 8.3 MCP 服务

```typescript
// src/services/mcp/useManageMCPConnections.ts
// React Hook 管理 MCP 服务器生命周期

function useManageMCPConnections() {
  // 两阶段配置加载 (Claude Code 配置 + claude.ai 配置)
  // 批量状态更新 (16ms 合并窗口)
  // 服务器状态: pending → connected → failed → disabled → needs-auth

  // 重连策略
  // - 5 次尝试
  // - 指数退避 1s-30s
  // - 最大延迟 30s

  // 传输类型: stdio, SSE, HTTP, WebSocket
}
```

### 8.4 OAuth 服务

```typescript
// src/services/oauth/index.ts
class OAuthService {
  async authorize(): Promise<OAuthTokens> {
    // 1. 生成 PKCE code_verifier + code_challenge
    // 2. 启动本地 HTTP 服务器
    // 3. 构建 auth URL
    // 4. 等待回调 (自动或手动)
    // 5. 交换 code 获取 tokens
    // 6. 获取 profile info
  }
}
```

### 8.5 LSP 服务

```typescript
// src/services/lsp/LSPServerManager.ts
interface LSPServerManager {
  initialize(): Promise<void>
  getServerForFile(filePath: string): LSPServerInstance | undefined
  sendRequest<T>(filePath, method, params): Promise<T>
  openFile(filePath, content): Promise<void>
  // ...
}

// 服务器实例状态机
// stopped → starting → running → stopping → stopped
// any → error (最多 3 次重启)
```

### 8.6 上下文压缩

**两级压缩策略**：

```typescript
// Level 1: microCompact - 轻量级每轮压缩
// 触发: 计数阈值或时间阈值
// - 缓存编辑 (cache_edits API)
// - 清除旧工具结果内容

// Level 2: compact - 完整对话压缩
// 1. 执行 PreCompact hooks
// 2. 剥离图片
// 3. 创建压缩提示
// 4. 模型生成摘要
// 5. 创建压缩边界标记
// 6. 生成后压缩附件
// 7. 执行 PostCompact hooks
```

### 8.7 Token 估算

```typescript
// src/services/tokenEstimation.ts
export async function countMessagesTokensWithAPI(
  messages: Message[],
  tools: Tool[]
): Promise<number> {
  // 根据块类型计数
  // text: 4 bytes/token
  // image/document: ~2000 tokens
  // tool_result: 递归计数
  // tool_use: name + JSON 长度
}
```

---

## 9. 桥接系统 (Bridge)

### 9.1 架构概述

桥接系统支持 **IDE 集成 (VS Code/JetBrains)** 与远程控制：

```
┌─────────────────────────────────────────────────────────────┐
│                    claude.ai Backend                         │
│  ┌─────────────────────────────────────────────────────┐      │
│  │  Environments API (v1)                              │      │
│  │  POST /environments/bridge                          │      │
│  │  GET  /environments/{id}/work/poll                  │      │
│  └─────────────────────────────────────────────────────┘      │
│  ┌─────────────────────────────────────────────────────┐      │
│  │  Session Ingress (WS/SSE)                           │      │
│  │  WS /session_ingress/ws/{sessionId}                │      │
│  │  SSE /worker/events/stream                          │      │
│  └─────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│               Claude Code CLI (Bridge Mode)                  │
│  ┌─────────────────────────────────────────────────────┐      │
│  │  initReplBridge()                                    │      │
│  │  - OAuth、git、标题派生                               │      │
│  └─────────────────────────────────────────────────────┘      │
│  ┌─────────────────────────────────────────────────────┐      │
│  │  HybridTransport / SSETransport                      │      │
│  │  - 双向消息传递                                       │      │
│  └─────────────────────────────────────────────────────┘      │
│  ┌─────────────────────────────────────────────────────┐      │
│  │  sessionRunner.ts                                    │      │
│  │  - 派生子 Claude Code 进程                           │      │
│  └─────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 两种传输架构

| 方面 | v1 (Env-Based) | v2 (Env-Less) |
|------|----------------|---------------|
| 协议 | Environments API | 直接 CCR `/bridge` 端点 |
| 传输 | HybridTransport (WS 读 + HTTP 写) | SSETransport + CCRClient |
| 会话生命周期 | 工作分发队列管理 | 直接 OAuth → worker JWT 交换 |
| 持久模式 | 支持 | 不支持 (回退到 v1) |

### 9.3 Bridge 配置

```typescript
// src/bridge/bridgeMain.ts
type BridgeConfig = {
  dir: string                    // 工作目录
  machineName: string           // 主机名
  branch: string                // Git 分支
  maxSessions: number           // 容量 (默认 1)
  spawnMode: 'single-session' | 'worktree' | 'same-dir'
  bridgeId: string              // 客户端生成 UUID
  environmentId: string         // 服务器分配的环境 ID
  sessionTimeoutMs?: number     // 会话看门狗
}
```

### 9.4 消息协议

```typescript
// src/bridge/bridgeMessaging.ts
// 入站路由
export function handleIngressMessage(
  data: string,
  recentPostedUUIDs: BoundedUUIDSet,  // 回声去重
  recentInboundUUIDs: BoundedUUIDSet, // 重传去重
  onInboundMessage?,
  onPermissionResponse?,
  onControlRequest?,
): void

// 控制请求子类型
// 'initialize' - 会话初始化
// 'set_model' - 更改模型
// 'can_use_tool' - 权限请求
// 'interrupt' - 取消当前轮次
// 'set_permission_mode' - 更改权限策略
```

### 9.5 Session Handle

```typescript
// src/bridge/sessionRunner.ts
type SessionHandle = {
  sessionId: string
  done: Promise<SessionDoneStatus>  // 'completed' | 'failed' | 'interrupted'
  kill(): void       // SIGTERM
  forceKill(): void  // SIGKILL
  activities: SessionActivity[]  // 最后 10 个活动
  writeStdin(data: string): void  // 直接子进程控制
}
```

---

## 10. UI 组件系统

### 10.1 架构概述

基于 **React + Ink** 的终端 UI：

```
src/
├── ink.ts                    # 入口 - ThemeProvider 包装
├── ink/                      # 自定义 Ink 实现
│   ├── components/           # 基础组件 (Box, Text, Button)
│   ├── hooks/                # Ink 专用 hooks (useInput, useStdin)
│   ├── events/               # 事件系统
│   └── layout/               # Yoga 布局引擎
├── components/              # UI 组件 (~146 文件)
│   ├── design-system/        # 主题感知组件
│   ├── PromptInput/          # 命令输入
│   ├── messages/            # 消息渲染
│   └── ...
└── screens/                  # 全屏 UI
    ├── REPL.tsx              # 主交互界面 (~896KB)
    ├── Doctor.tsx             # 诊断界面 (~73KB)
    └── ResumeConversation.tsx # 会话恢复 (~60KB)
```

### 10.2 Ink vs React

| 方面 | Ink | React DOM |
|------|-----|-----------|
| 渲染目标 | 终端 ANSI 编码 | 浏览器 DOM |
| 布局引擎 | Yoga (flexbox) | CSS/浏览器 layout |
| 输入处理 | `useInput` hook | DOM 事件 |
| 组件模型 | React 组件 | React 组件 |

### 10.3 主题系统

```typescript
// src/components/design-system/ThemeProvider.tsx
// 支持 light/dark/auto
// OSC 11 监视器实时检测终端主题

<ThemeProvider>
  <ThemedBox background="primary">
    <ThemedText color="foreground">Hello</ThemedText>
  </ThemedBox>
</ThemeProvider>
```

### 10.4 输入处理层次

```
终端按键 → useInput → useTextInput / Ctrl 处理器
                              ↓
              键绑定系统 (如果绑定了动作)
```

```typescript
// 基础输入捕获 (src/ink/hooks/use-input.ts)
const useInput = (inputHandler, options = {}) => {
  const { setRawMode, ... } = useStdin()
  useLayoutEffect(() => {
    if (options.isActive === false) return
    setRawMode(true)  // 同步启用原始模式
    return () => { setRawMode(false) }
  }, [options.isActive, setRawMode])
}

// 文本输入 (src/hooks/useTextInput.ts)
const useTextInput = () => {
  // 光标管理
  // Emacs 键绑定 (Ctrl+A/E/F/B, Ctrl+K/U)
  // 历史导航 (上/下箭头)
  // Kill ring (Alt+Y)
  // Vim 模式支持
}
```

### 10.5 消息渲染

```typescript
// src/components/Messages.tsx
// 容器：过滤、构建查找表

// src/components/MessageRow.tsx
// 单条消息渲染
// - 分组可折叠的读/搜索操作
// - 工具进度显示
// - 折叠/展开状态

// src/components/Markdown.tsx
// Markdown 渲染
// - marked 库解析
// - 语法高亮
// - LRU 缓存 (500 条目)
```

### 10.6 虚拟列表

```typescript
// src/components/VirtualMessageList.tsx
// 高效滚动大量消息
// useUnseenDivider 追踪新消息分隔符位置
// useSyncExternalStore 订阅滚动事件
```

---

## 11. 协调器与插件系统

### 11.1 协调器系统 (Coordinator)

多 Agent 编排机制：

```typescript
// src/coordinator/coordinatorMode.ts
// 特性开关: COORDINATOR_MODE

// 协调器系统提示词
// 角色: 协调器 → 指导 workers → 综合结果 → 实现

// Worker 派生 via AgentTool with subagent_type: "worker"
// 结果通过 <task-notification> 消息接收
```

### 11.2 插件系统

```typescript
// src/plugins/
// 可下载/可安装的插件

type BuiltinPluginDefinition = {
  name: string
  description: string
  skills?: BundledSkillDefinition[]
  hooks?: HooksSettings
  mcpServers?: Record<string, McpServerConfig>
}

// 加载生命周期
// 1. 注册 (registerBuiltinPlugin)
// 2. 发现 (缓存优先，版本化路径)
// 3. 验证 (Zod schema)
// 4. 组件加载 (命令/代理/技能/钩子/MCP/LSP)
```

### 11.3 插件结构

```
my-plugin/
├── plugin.json          # 可选清单
├── commands/            # 自定义斜杠命令
├── agents/              # 自定义 AI 代理
├── hooks/               # 钩子配置
├── skills/              # 自定义技能
├── mcp-servers/         # MCP 服务器定义
└── lsp-servers/         # LSP 服务器定义
```

---

## 12. 技能系统 (Skills)

### 12.1 技能 vs 工具

| 方面 | 工具 | 技能 |
|------|------|------|
| 执行 | 原生代码直接运行 | 展开为提示内容 |
| 调用 | 通过工具调用 | 通过 `/skill-name` 或 SkillTool |
| 上下文 | 访问完整对话 | 作为提示前缀注入 |
| 用途 | 文件操作、bash、API 调用 | 可复用提示模板 |

### 12.2 技能定义

```typescript
// src/skills/bundledSkills.ts
type BundledSkillDefinition = {
  name: string
  description: string
  aliases?: string[]
  whenToUse?: string
  argumentHint?: string
  allowedTools?: string[]        // 工具白名单
  model?: string                 // 指定模型
  disableModelInvocation?: boolean
  userInvocable?: boolean        // 允许 /skill-name 调用
  hooks?: HooksSettings
  context?: 'inline' | 'fork'    // 执行上下文
  agent?: string                  // Fork 时的代理类型
  paths?: string[]               // 条件激活的文件模式
  getPromptForCommand(args, context): Promise<ContentBlockParam[]>
}
```

### 12.3 技能加载来源

1. **内置技能** - 编译到 CLI 二进制
2. **托管技能** - `~/.claude/.claude/skills/` (策略控制)
3. **用户技能** - `~/.claude/skills/`
4. **项目技能** - `.claude/skills/` 目录
5. **MCP 技能** - 来自 MCP 服务器

### 12.4 技能加载过程

```typescript
// src/skills/loadSkillsDir.ts

// 1. 目录遍历 (去重，解析 symlinks)
loadSkillsDir(dir, options)

// 2. Frontmatter 解析
parseFrontmatter(content)
// name, description, whenToUse
// allowed-tools, argument-hint, arguments
// model, disable-model-invocation, user-invocable
// hooks, context, agent, effort, shell, paths

// 3. 命令创建
createSkillCommand(skillDef)
// 包装 getPromptForCommand() 处理
// ${CLAUDE_SKILL_DIR} 替换
// ${CLAUDE_SESSION_ID} 替换
// Shell 命令执行 (!command)
// 参数替换
```

### 12.5 条件激活

```yaml
---
name: my-skill
paths:
  - src/**/*.ts
  - **/*.js
---
# 当触达的文件匹配这些模式时激活
```

---

## 13. Agent 系统

### 13.1 Agent 类型

| 类型 | 来源 | 描述 |
|------|------|------|
| 内置代理 | 代码中的动态提示 | GeneralPurpose, Explore, Plan, Verification |
| 自定义代理 | 来自 markdown 文件 | userSettings, projectSettings, policySettings |
| 插件代理 | 来自插件 | source: 'plugin' |

### 13.2 Agent 定义

```typescript
// src/tools/AgentTool/builtInAgents.ts
type BaseAgentDefinition = {
  agentType: string
  whenToUse: string
  tools?: string[]          // 工具白名单
  disallowedTools?: string[] // 工具黑名单
  skills?: string[]          // 预加载技能
  mcpServers?: AgentMcpServerSpec[]  // Agent 专用 MCP
  hooks?: HooksSettings
  model?: string
  effort?: EffortValue
  permissionMode?: PermissionMode
  maxTurns?: number
  background?: boolean       // 后台运行
  memory?: 'user' | 'project' | 'local'
  isolation?: 'worktree' | 'remote'
  omitClaudeMd?: boolean     // 跳过 CLAUDE.md
}
```

### 13.3 Agent 生命周期

```typescript
// src/tools/AgentTool/runAgent.ts

async function* runAgent(options): AsyncGenerator<SDKMessage> {
  // 1. 初始化
  // - 创建唯一 agentId
  // - 初始化文件状态缓存
  // - 设置权限模式
  // - 注册 Perfetto 追踪

  // 2. 上下文构建
  // - Fork 上下文消息
  // - 用户/系统上下文解析
  // - 可选 CLAUDE.md 省略

  // 3. Hook 执行
  // - 执行 SubagentStart hooks
  // - 注册 frontmatter hooks

  // 4. MCP 服务器设置
  // - 合并 Agent 专用 MCP 服务器

  // 5. 执行
  // - 运行 query() 循环
  // - 记录 sidechain transcript

  // 6. 清理
  // - MCP 服务器清理
  // - Session hooks 清理
  // - 文件状态缓存释放
}
```

### 13.4 Agent 间通信

```typescript
// src/tools/SendMessageTool/SendMessageTool.ts
// Agent 间通过 SendMessageTool 通信

type MessageTarget =
  | { type: 'direct', name: string }      // 发送给特定成员
  | { type: 'broadcast', to: '*' }         // 广播给所有成员

// 消息传递
// - 进程内 teammates: 通过 queuePendingMessage() 到 LocalAgentTask
// - 已停止 agents: 通过 resumeAgentBackground() 自动恢复
// - tmux/iTerm2 teammates: 通过邮箱文件系统

// 邮箱文件: ~/.claude/teams/{teamName}/mailbox/{agentName}/
```

### 13.5 子 Agent 派生

```typescript
// src/tools/AgentTool/shared/spawnMultiAgent.ts

// 三种执行模式
type SpawnMode =
  | 'in-process'        // 同一 Node.js 进程，AsyncLocalStorage
  | 'split-pane-tmux'   // tmux 分屏，与 leader 共享终端
  | 'window-iterm2'     // iTerm2 原生分屏

async function spawnTeammate(options): Promise<TeammateHandle> {
  // 1. 生成唯一名称和确定性 agentId
  // 2. 在后端创建 pane/window
  // 3. 构建继承权限模式、模型的 CLI 标志
  // 4. 注册到 team 文件和 AppState
  // 5. 通过邮箱发送初始提示
}
```

---

## 附录：关键文件参考

| 文件 | 大小 | 职责 |
|------|------|------|
| `src/main.tsx` | ~803KB | 入口，CLI 编排 |
| `src/QueryEngine.ts` | ~46KB | LLM 查询引擎 |
| `src/query.ts` | ~68KB | 查询管道 |
| `src/Tool.ts` | ~29KB | 工具类型定义 |
| `src/tools.ts` | ~17KB | 工具注册表 |
| `src/commands.ts` | ~25KB | 命令注册表 |
| `src/state/AppStateStore.ts` | ~22KB | 核心状态存储 |
| `src/state/AppState.tsx` | ~23KB | React hooks |
| `src/REPL.tsx` | ~896KB | 主 REPL UI |
| `src/bridge/bridgeMain.ts` | ~115KB | 桥接主循环 |
| `src/bridge/replBridge.ts` | ~100KB | REPL 桥接 |
| `src/services/tools/toolOrchestration.ts` | - | 工具编排 |
| `src/services/tools/toolExecution.ts` | - | 工具执行 |

---

*文档版本: 2026-03-31*
*基于 Claude Code 源代码分析生成*
