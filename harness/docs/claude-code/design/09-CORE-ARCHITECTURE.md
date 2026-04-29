# Claude Code 核心架构设计

## 1. 架构概览

Claude Code 是一个基于终端的 AI 编程助手，采用**事件驱动 + Async Generator 模式**，核心是一个 **Query/Task 处理循环**。

### 1.1 运行模式

| 模式 | 说明 |
|-----|-----|
| **REPL 交互模式** | 用户在终端通过命令行交互，Ink (React) UI |
| **SDK/Headless 模式** | 通过 SDK 控制，适合自动化脚本 |
| **Bridge 远程控制** | 通过 WebSocket 远程控制本地实例 |

### 1.2 核心设计原则

1. **简单性优先**: 模块级变量做全局状态，避免 Redux/Zustand 过度设计
2. **性能优先**: 预加载、并行初始化、延迟导入、Memoization
3. **可扩展性**: Feature flags、Plugin 系统、Tool 接口、MCP 协议
4. **流式优先**: Async Generator 实现端到端流式处理
5. **安全性**: 权限上下文、权限规则、Tool 沙箱

---

## 2. 核心入口与初始化

### 2.1 启动序列

```
main.tsx (entry)
├── profileCheckpoint('main_tsx_entry')
├── startMdmRawRead() ──────────────┐
├── startKeychainPrefetch() ─────────┼─ 并行执行
├── 大量模块导入 ─────────────────────┘
│
├── setup()
│   ├── Node.js 版本检查
│   ├── switchSession() 设置会话 ID
│   ├── startUdsMessaging() (Mac/Linux)
│   ├── setCwd() 设置工作目录
│   ├── worktree 创建 (可选)
│   └── initSessionMemory()
│
├── init()
│   ├── enableConfigs()
│   ├── applySafeConfigEnvironmentVariables()
│   ├── setupGracefulShutdown()
│   ├── configureGlobalMTLS()
│   └── telemetry 初始化
│
├── logSessionTelemetry()
├── 创建 AppState store
│
└── launchRepl() or headless mode
```

### 2.2 关键设计

**预加载优化**: 在导入任何模块之前，先执行 `profileCheckpoint`、`startMdmRawRead`、`startKeychainPrefetch`，让 MDM 读取和 keychain 预取与后续模块加载并行执行。

**依赖注入**: 通过 `feature('FLAG_NAME')` 实现 Dead Code Elimination (DCE)，根据编译时特性标志选择性导入。

**延迟初始化**: 大量使用动态 `import()` 延迟加载非关键模块。

---

## 3. Query/Task 处理流程

### 3.1 核心组件

```
QueryEngine.submitMessage()
└── query() [Async Generator]
    ├── queryModelWithStreaming()  → 调用 Anthropic API
    ├── runTools()                 → 工具编排
    │   ├── 工具分区: isConcurrencySafe
    │   ├── 只读工具: 并行执行
    │   └── 写操作工具: 串行执行
    ├── autoCompactIfNeeded()      → 自动压缩上下文
    └── yield StreamEvent          → 流式输出
```

### 3.2 Async Generator Pattern

Query 循环使用 async generator 实现真正的流式处理：

```typescript
// QueryEngine.ts
export class QueryEngine {
  async *submitMessage(
    prompt: string | ContentBlockParam[],
    options?: { uuid?: string; isMeta?: boolean }
  ): AsyncGenerator<SDKMessage, void, unknown>
}

// query.ts
export async function* query(
  params: QueryParams,
): AsyncGenerator<
  | StreamEvent
  | RequestStartEvent
  | Message
  | TombstoneMessage
  | ToolUseSummaryMessage,
  Terminal
>
```

**优势**:
- API 响应流式返回
- 工具调用结果流式输出
- 支持中断和恢复

### 3.3 Query Loop 状态管理

```typescript
type State = {
  messages: Message[]
  toolUseContext: ToolUseContext
  turnCount: number
  autoCompact: AutoCompactState
  tokenBudget: TokenBudgetState
  // ...
}
```

---

## 4. Tool 系统架构

### 4.1 Tool 接口定义

```typescript
// Tool.ts
export type Tool<
  Input extends AnyObject = AnyObject,
  Output = unknown,
  P extends ToolProgressData = ToolProgressData,
> = {
  name: string
  aliases?: string[]
  inputSchema: Input
  call(
    args: z.infer<Input>,
    context: ToolUseContext,
    canUseTool: CanUseToolFn,
    parentMessage: AssistantMessage,
    onProgress?: ToolCallProgress<P>,
  ): Promise<ToolResult<Output>>
  description(input, options): Promise<string>
  prompt(options): Promise<string>
}
```

### 4.2 工具分类

| 类别 | 示例 |
|-----|-----|
| **内置工具** | BashTool, FileEditTool, FileReadTool, GlobTool, GrepTool |
| **Agent 工具** | AgentTool (子 agent 调度) |
| **MCP 工具** | MCPTool (动态包装 MCP 协议) |
| **可选工具** | WorkflowTool, WebBrowserTool (feature-gated) |

### 4.3 工具目录结构

```
src/tools/
├── AgentTool/          — 子 agent 调度
├── BashTool/          — Bash 命令执行
├── FileEditTool/      — 文件编辑
├── FileReadTool/      — 文件读取
├── FileWriteTool/     — 文件写入
├── GlobTool/          — Glob 模式匹配
├── GrepTool/          — 文本搜索
├── Task*Tool/         — 任务管理工具系列
├── MCPTool/           — MCP 协议包装
├── SkillTool/         — 技能调用
├── LSPTool/           — 语言服务器协议
└── ...
```

### 4.4 并发安全分区

**核心问题**: 只读工具可以并行执行，但写操作工具需要串行执行避免竞态。

```typescript
// services/tools/toolOrchestration.ts
export async function* runTools(
  toolUseMessages: ToolUseBlock[],
  assistantMessages: AssistantMessage[],
  canUseTool: CanUseToolFn,
  toolUseContext: ToolUseContext,
): AsyncGenerator<MessageUpdate, void> {
  for (const { isConcurrencySafe, blocks } of partitionToolCalls(...)) {
    if (isConcurrencySafe) {
      // 并行执行只读工具
      for await (const update of runToolsConcurrently(blocks, ...)) { ... }
    } else {
      // 串行执行写操作工具
      for await (const update of runToolsSerially(blocks, ...)) { ... }
    }
  }
}
```

---

## 5. 状态管理

### 5.1 四层状态架构

| 层级 | 实现 | 用途 |
|-----|-----|-----|
| **全局单例** | `bootstrap/state.ts` | 真正全局状态 (sessionId, projectRoot) |
| **响应式 Store** | `state/store.ts` | 发布-订阅模式的状态容器 |
| **App State** | `state/AppStateStore.ts` | UI状态 (settings, mcp, tasks, plugins) |
| **Context** | `context.ts` | System/User Context 缓存 |

### 5.2 全局单例状态

```typescript
// bootstrap/state.ts
type State = {
  sessionId: SessionId
  projectRoot: string
  originalCwd: string
  cwd: string
  mainLoopModelOverride: ModelSetting | undefined
  isInteractive: boolean
  kairosActive: boolean
  meter: Meter | null
  sessionCounter: AttributedCounter | null
}
```

**设计原则**: DO NOT ADD MORE STATE HERE - 避免 Redux/Zustand 等外部状态管理库的复杂性。

### 5.3 响应式 Store

```typescript
// state/store.ts
export type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (listener: Listener) => () => void
}
```

### 5.4 AppState 核心字段

```typescript
// state/AppStateStore.ts
export type AppState = DeepImmutable<{
  settings: SettingsJson
  verbose: boolean
  mainLoopModel: ModelSetting
  expandedView: 'none' | 'tasks' | 'teammates'
  toolPermissionContext: ToolPermissionContext
  mcp: {
    clients: MCPServerConnection[]
    tools: Tool[]
    commands: Command[]
    resources: Record<string, ServerResource[]>
  }
  plugins: {
    enabled: LoadedPlugin[]
    disabled: LoadedPlugin[]
    commands: Command[]
    errors: PluginError[]
  }
  tasks: { [taskId: string]: TaskState }
  agentNameRegistry: Map<string, AgentId>
}>
```

---

## 6. 任务系统 (Task System)

### 6.1 Task 类型

```typescript
// Task.ts
export type TaskType =
  | 'local_bash'
  | 'local_agent'
  | 'remote_agent'
  | 'in_process_teammate'
  | 'local_workflow'
  | 'monitor_mcp'
  | 'dream'

export type TaskStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'killed'
```

### 6.2 Task 工厂

```typescript
// tasks.ts
export function getTaskByType(type: TaskType): Task | undefined {
  return getAllTasks().find(t => t.type === type)
}
```

---

## 7. 命令系统

### 7.1 命令注册表

```typescript
// commands.ts
export type Command = {
  type: 'prompt' | 'toggle' | 'background'
  name: string
  description: string
  getPromptForCommand(args, context): Promise<string>
}
```

### 7.2 命令分类

| 类别 | 示例 |
|-----|-----|
| **内置命令** | help, commit, config, session, tasks, skills |
| **可选命令** | proactive, workflows, voice (feature-gated) |

---

## 8. 通信机制

### 8.1 Bridge 系统 (远程控制)

支持 `--remote` 模式，通过 WebSocket 让远程用户控制本地 Claude Code 实例。

```
bridge/
├── bridgeMain.ts     — Bridge 主循环
├── bridgeApi.ts      — Bridge API 客户端
├── bridgeConfig.ts   — Bridge 配置
├── replBridge.ts     — REPL Bridge 实现
├── remoteBridgeCore.ts — 远程 Bridge 核心
├── workSecret.ts     — 工作秘密管理
└── jwtUtils.ts       — JWT 令牌刷新
```

### 8.2 传输层

```
cli/transports/
├── WebSocketTransport.ts — WebSocket 传输
├── SSETransport.ts      — Server-Sent Events 传输
├── HybridTransport.ts   — 混合传输
└── WorkerStateUploader.ts — Worker 状态上传
```

---

## 9. 协调者模式 (Coordinator Mode)

当启用时，Claude Code 作为**协调者**运行，将任务委托给多个 Worker agents。

```typescript
// coordinator/coordinatorMode.ts
export function isCoordinatorMode(): boolean
export function getCoordinatorUserContext(mcpClients, scratchpadDir): {[k: string]: string}
export function getCoordinatorSystemPrompt(): string
```

**核心机制**:
- 协调者拥有完整工具集
- Workers 通过 `AgentTool` spawn，只能使用受限工具集
- 使用 `SEND_MESSAGE_TOOL_NAME` 继续与 workers 通信
- Workers 的结果通过 `<task-notification>` XML 标签以 user-role 消息形式返回

---

## 10. 设计模式总结

| 模式 | 应用场景 |
|-----|---------|
| **Async Generator** | Query 循环流式处理 |
| **Dependency Injection** | QueryDeps 类型便于测试 mock |
| **Feature Flags** | `feature('FLAG')` 控制代码路径裁剪 |
| **Memoization** | `lodash-es/memoize` 缓存计算结果 |
| **策略模式** | 每个 Tool 实现自己的 call/description/prompt |
| **Factory Pattern** | getTaskByType(), getAllBaseTools() |
| **Observer Pattern** | Store 的 subscribe/getState/setState |
| **Builder Pattern** | buildTool() 为部分 tool 定义填充默认值 |

---

## 11. 关键文件索引

| 文件路径 | 职责 |
|---------|-----|
| `main.tsx` | 应用程序入口 |
| `setup.ts` | 会话初始化 |
| `entrypoints/init.ts` | 核心子系统初始化 |
| `replLauncher.tsx` | REPL 启动器 |
| `QueryEngine.ts` | 查询引擎封装 |
| `query.ts` | 查询循环核心 |
| `query/deps.ts` | Query 依赖注入 |
| `Tool.ts` | Tool 接口定义 |
| `tools.ts` | 工具注册表 |
| `services/tools/toolOrchestration.ts` | 工具编排 |
| `Task.ts` | Task 类型定义 |
| `tasks.ts` | Task 工厂 |
| `bootstrap/state.ts` | 全局单例状态 |
| `state/store.ts` | 响应式 Store |
| `state/AppStateStore.ts` | App 状态定义 |
| `context.ts` | System/User Context |
| `history.ts` | 历史记录管理 |
| `commands.ts` | 命令注册表 |
| `coordinator/coordinatorMode.ts` | 协调者模式 |
| `bridge/bridgeMain.ts` | Bridge 主循环 |
| `ink.ts` | Ink (React) 渲染入口 |

---

## 12. 模块依赖关系图（简化）

```
main.tsx
├── setup()
├── init()
├── launchRepl()
│   ├── App.tsx (React)
│   │   └── REPL.tsx (Screen)
│   └── renderAndRun()
├── QueryEngine
│   ├── query()
│   │   ├── queryModelWithStreaming()  [API]
│   │   ├── runTools()                 [Tool Orchestration]
│   │   │   └── tool.call()            [Individual Tools]
│   │   ├── autoCompactIfNeeded()
│   │   └── microcompactMessages()
│   └── submitMessage()
│       └── processUserInput()
├── AppStateStore
│   └── createStore()
└── Commands
    └── getCommands()
```
