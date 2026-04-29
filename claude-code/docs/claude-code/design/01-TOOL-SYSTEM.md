# 工具系统设计文档

> 本文档详细解析 Claude Code 工具系统的架构设计、核心类型、执行流程和设计模式。

---

## 1. 设计概述

### 1.1 设计目标

工具系统是 Claude Code 的**核心扩展机制**，允许 AI 模型通过结构化接口执行各种操作：

- **类型安全** - 所有工具输入通过 Zod Schema 验证
- **权限控制** - 细粒度的权限检查和决策
- **可组合性** - 工具可并发或串行执行
- **可观测性** - 进度回调、Hook 机制
- **可扩展性** - 内置工具 + MCP 外部工具

### 1.2 核心问题

工具系统需要解决：

1. 如何定义类型安全的工具接口？
2. 如何在 CLI 环境中安全地执行危险操作？
3. 如何处理工具间的依赖和并发？
4. 如何支持远程 MCP 工具？
5. 如何实现零开销的 UI 渲染？

---

## 2. 类型系统

### 2.1 Tool 接口层次

```
AnyToolDef (约束工具定义)
    │
    ├─── Tool<Input, Output, Progress> (完整工具接口)
    │        │
    │        ├─── 必需属性
    │        │    ├── name: string
    │        │    ├── inputSchema: ZodSchema<Input>
    │        │    ├── call(args, context, canUseTool, parentMessage, onProgress?)
    │        │    ├── description(input, options)
    │        │    ├── prompt(options)
    │        │    ├── userFacingName(input)
    │        │    ├── maxResultSizeChars: number
    │        │    └── mapToolResultToToolResultBlockParam(content, toolUseID)
    │        │
    │        └─── 可选属性 (高级特性)
    │             ├── aliases?: string[]
    │             ├── isConcurrencySafe?(input): boolean
    │             ├── isReadOnly?(input): boolean
    │             ├── isDestructive?(input): boolean
    │             ├── checkPermissions?(input, context)
    │             ├── validateInput?(input, context)
    │             └── ...
    │
    └─── BuiltTool<D> (运行时工具实例)
             │
             └─── 通过 buildTool() 工厂创建
```

### 2.2 核心类型定义

```typescript
// src/Tool.ts:362-400
export type ToolDefinition<
  Input extends z.ZodType = z.ZodType,
  Output = unknown,
  Progress = unknown,
> = {
  // 核心元数据
  name: string
  aliases?: string[]
  description(input: unknown, options: ToolDescriptionOptions): Promise<string>

  // Schema 定义
  inputSchema: Input
  outputSchema?: z.ZodType<Output>

  // 执行入口
  call(
    args: z.infer<Input>,
    context: ToolUseContext,
    canUseTool: CanUseToolFn,
    parentMessage: Message | undefined,
    onProgress?: (progress: ToolProgress<Progress>) => void
  ): Promise<ToolResult<Output>>

  // 提示词生成
  prompt(options: ToolPromptOptions): Promise<string>
  userFacingName(input: z.infer<Input>): string

  // UI 渲染
  maxResultSizeChars: number
  renderToolUseMessage(
    input: z.infer<Input>,
    options: RenderToolUseMessageOptions
  ): React.ReactNode
  mapToolResultToToolResultBlockParam(
    content: ToolResultContent<Output>,
    toolUseID: string
  ): ToolResultBlockParam

  // 执行特性
  isConcurrencySafe?(input: z.infer<Input>): boolean
  isReadOnly?(input: z.infer<Input>): boolean
  isDestructive?(input: z.infer<Input>): boolean

  // 权限与验证
  checkPermissions?(
    input: z.infer<Input>,
    context: ToolUseContext
  ): Promise<PermissionResult>
  validateInput?(
    input: unknown,
    context: ToolUseContext
  ): Promise<ValidationResult>

  // 路径提取 (用于权限匹配)
  getPath?(input: z.infer<Input>): string | string[] | undefined

  // 高级特性
  shouldDefer?: boolean  // 通过 ToolSearch 延迟加载
  alwaysLoad?: boolean  // 永不延迟
  isMcp?: boolean      // MCP 工具标记
}

// ToolUseContext - 执行上下文
// src/Tool.ts:158-300
export type ToolUseContext = {
  // 工具相关
  options: {
    tools: Tool[]
    mcpClients: MCPClient[]
  }
  abortController: AbortController

  // 文件状态缓存
  readFileState: FileStateCache
  updateFileState?: (path: string, newState: FileState) => void

  // 状态管理
  getAppState: () => AppState
  setAppState: (
    updater: (prev: AppState) => Partial<AppState>
  ) => void

  // UI 渲染回调
  setToolJSX: SetToolJSXFn
  renderToolProgressMessage?: (
    toolName: string,
    progress: unknown,
    options: unknown
  ) => React.ReactNode

  // 权限上下文
  toolPermissionContext: ToolPermissionContext

  // 会话信息
  session: {
    id: string
    accessToken?: string
    orgId?: string
  }

  // 工具决策追踪
  toolDecisions: Map<string, ToolDecision>

  // 配置
  config: {
    maxToolUseCount?: number
    maxResultSizeChars?: number
  }
}
```

### 2.3 Zod Schema 模式

工具输入使用 Zod 进行运行时验证：

```typescript
// src/tools/TaskCreateTool/TaskCreateTool.ts:18-33
const inputSchema = lazySchema(() =>
  z.strictObject({
    subject: z.string().describe('Task 的简短标题'),
    description: z.string().describe('需要完成的内容'),
    activeForm: z.string().optional().describe('现在分词形式'),
    metadata: z.record(z.string(), z.unknown()).optional(),
  })
)

// src/tools/BashTool/bashSchema.ts
// Bash 工具使用更复杂的 schema
const bashInputSchema = z.strictObject({
  command: z.string().describe('要执行的命令'),
  context: z.enum(['execute', 'interactive', 'login']).optional(),
  timeout: z.number().optional(),  // ms
  currentDir: z.string().optional(),
  env: z.record(z.string(), z.string()).optional(),
})

// lazySchema 延迟解析避免循环依赖
function lazySchema<T extends z.ZodType>(
  schemaFactory: () => T
): z.ZodType {
  let schema: T | undefined
  return {
    _zod: true,
    get type() {
      if (!schema) schema = schemaFactory()
      return schema.type
    },
    // ... 其他 Zod 接口方法，懒初始化 schema
  }
}
```

---

## 3. 工厂模式 (buildTool)

### 3.1 工厂函数设计

```typescript
// src/Tool.ts:783-792
export function buildTool<D extends AnyToolDef>(def: D): BuiltTool<D> {
  return {
    ...TOOL_DEFAULTS,
    userFacingName: () => def.name,
    ...def,
  } as BuiltTool<D>
}

// 默认安全值
const TOOL_DEFAULTS = {
  // 默认启用
  isEnabled: () => true,

  // 默认非并发安全 (保守策略)
  isConcurrencySafe: (_input?: unknown) => false,

  // 默认非只读
  isReadOnly: (_input?: unknown) => false,

  // 默认非破坏性
  isDestructive: (_input?: unknown) => false,

  // 默认允许 (但权限检查仍会运行)
  checkPermissions: (input, _ctx) =>
    Promise.resolve({ behavior: 'allow', updatedInput: input }),

  // 空的用户-facing 名称
  userFacingName: (_input?: unknown) => '',

  // 无路径提取
  getPath: () => undefined,

  // 默认不使用延迟加载
  shouldDefer: false,
  alwaysLoad: false,
} as const
```

### 3.2 工厂优势

1. **默认安全** - 所有工具默认禁用并发、非只读时需明确声明
2. **类型保持** - TypeScript 泛型确保输入输出类型
3. **渐进增强** - 可选属性有默认值，可选覆盖

---

## 4. 工具注册与组装

### 4.1 注册表结构

```typescript
// src/tools.ts
// 单例注册表
let toolRegistry: Tool[] | undefined

export function getAllBaseTools(): Tool[] {
  if (toolRegistry) return toolRegistry

  toolRegistry = [
    // 文件操作
    BashTool,
    FileEditTool,
    FileReadTool,
    FileWriteTool,
    NotebookEditTool,

    // 搜索
    GlobTool,
    GrepTool,

    // Agent 与任务
    AgentTool,
    TaskCreateTool,
    TaskUpdateTool,
    TaskListTool,
    TaskStopTool,
    TaskGetTool,

    // 外部集成
    WebSearchTool,
    WebFetchTool,
    MCPTool,
    SkillTool,

    // 模式控制
    EnterPlanModeTool,
    ExitPlanModeV2Tool,
    EnterWorktreeTool,
    ExitWorktreeTool,

    // 工具
    TodoWriteTool,
    BriefTool,
    ConfigTool,
    AskUserQuestionTool,
    LSPTool,

    // ... 45+ 工具
  ]

  return toolRegistry
}

// 按权限上下文过滤
export function getTools(permissionContext: PermissionContext): Tool[] {
  const tools = getAllBaseTools()

  return tools.filter(tool => {
    // 1. 检查 isEnabled 特性开关
    if (tool.isEnabled?.() === false) return false

    // 2. 检查权限上下文的工具限制
    if (permissionContext.disabledTools?.includes(tool.name)) return false

    return true
  })
}
```

### 4.2 工具池组装

```typescript
// src/tools.ts
export function assembleToolPool(
  permissionContext: PermissionContext,
  mcpTools: Tool[]
): AssembledToolPool {
  // 获取过滤后的内置工具
  const baseTools = getTools(permissionContext)

  // 合并 MCP 工具
  const allTools = [...baseTools, ...mcpTools]

  // 按名称建立索引
  const toolByName = new Map<string, Tool>()
  for (const tool of allTools) {
    toolByName.set(tool.name, tool)
    // 注册别名
    for (const alias of tool.aliases ?? []) {
      toolByName.set(alias, tool)
    }
  }

  return {
    tool: allTools,
    toolByName,
    mcpTools,
    mcpToolByName: new Map(
      mcpTools.map(t => [t.name, t])
    ),
  }
}
```

---

## 5. 执行流程

### 5.1 完整执行管道

```
┌─────────────────────────────────────────────────────────────────┐
│  ToolOrchestration (runTools)                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. 工具调用分区 (partitionToolCalls)                       │  │
│  │    - 按 isConcurrencySafe 分组                            │  │
│  │    - 连续并发安全的工具合并为批次                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 2. 并发执行循环 (runToolsConcurrently)                     │  │
│  │    - MAX_TOOL_USE_CONCURRENCY = 10                        │  │
│  │    - 使用 Promise.allSettled 而非 all                       │  │
│  │    - 单个失败不影响其他                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│              ┌───────────────┴───────────────┐                 │
│              │                               │                 │
│              ▼                               ▼                 │
│  ┌─────────────────────────┐   ┌─────────────────────────────┐  │
│  │ Batch 1 (串行)           │   │ Batch 2+ (最多 10 并发)      │  │
│  │ for (tool of tools) {   │   │ await Promise.allSettled([ │  │
│  │   yield* runToolUse()   │   │   runToolUse(tool1),        │  │
│  │ }                        │   │   runToolUse(tool2),        │  │
│  └─────────────────────────┘   │   ...                        │  │
│                                │ ])                            │  │
│                                └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ToolExecution (checkPermissionsAndCallTool)                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. Input Schema 验证 (Zod safeParse)                      │  │
│  │    - 失败 → 返回 ValidationError                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 2. validateInput Hook (可选)                               │  │
│  │    - 工具自定义验证逻辑                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 3. PreToolUse Hooks                                       │  │
│  │    - 全局前置处理                                          │  │
│  │    - 可修改输入或取消执行                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 4. 权限检查 (checkPermissions / canUseTool)                │  │
│  │    ┌────────────────────────────────────────────────────┐ │  │
│  │    │ 4.1 检查 deny 规则                                  │ │  │
│  │    │ 4.2 检查 ask 规则                                   │ │  │
│  │    │ 4.3 调用 tool.checkPermissions()                   │ │  │
│  │    │ 4.4 安全检查 (.git/ 等路径)                         │ │  │
│  │    │ 4.5 应用权限模式 (bypass/acceptEdits/auto/plan)    │ │  │
│  │    └────────────────────────────────────────────────────┘ │  │
│  │                                                          │  │
│  │    Decision:                                              │  │
│  │    - deny → 返回 PermissionDeniedError                    │  │
│  │    - ask → 暂停执行，等待用户确认                          │  │
│  │    - passthrough → 跳过 (MCP 工具)                        │  │
│  │    - allow → 继续                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 5. tool.call() 执行                                       │  │
│  │    - 传递 ToolUseContext                                   │  │
│  │    - 支持 onProgress 回调                                 │  │
│  │    - 返回 ToolResult                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 6. PostToolUse Hooks                                      │  │
│  │    - 全局后置处理                                          │  │
│  │    - 结果验证/日志                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 7. 返回 ToolResult                                        │  │
│  │    - content: string | CustomContent                      │  │
│  │    - suppressed?: boolean                                  │  │
│  │    - error?: string                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 工具调用分区算法

```typescript
// src/services/tools/toolOrchestration.ts:91-116
interface ToolBatch {
  isConcurrencySafe: boolean
  blocks: ToolUseBlock[]
}

function partitionToolCalls(
  toolUseMessages: ToolUseBlock[],
  toolUseContext: ToolUseContext
): ToolBatch[] {
  return toolUseMessages.reduce((acc: ToolBatch[], toolUse) => {
    const tool = findToolByName(toolUseContext.options.tools, toolUse.name)
    const parsedInput = tool?.inputSchema.safeParse(toolUse.input)

    // 推断并发安全性
    // 失败时假设不安全 (保守)
    const isConcurrencySafe = parsedInput?.success
      ? Boolean(tool?.isConcurrencySafe(parsedInput.data))
      : false

    // 合并连续的并发安全工具
    if (isConcurrencySafe && acc[acc.length - 1]?.isConcurrencySafe) {
      acc[acc.length - 1]!.blocks.push(toolUse)
    } else {
      acc.push({ isConcurrencySafe, blocks: [toolUse] })
    }

    return acc
  }, [])
}

// 分区结果示例
// 输入: [Read(A), Read(B), Bash(X), Read(C), Write(Y), Read(D)]
// 输出: [
//   { isConcurrencySafe: true, blocks: [Read(A), Read(B)] },   // 并发
//   { isConcurrencySafe: false, blocks: [Bash(X)] },             // 串行
//   { isConcurrencySafe: true, blocks: [Read(C)] },             // 并发
//   { isConcurrencySafe: false, blocks: [Write(Y)] },            // 串行
//   { isConcurrencySafe: true, blocks: [Read(D)] },             // 并发
// ]
```

### 5.3 权限检查流程

```typescript
// src/services/tools/toolExecution.ts
// 权限检查主函数
async function checkPermissionsAndCallTool(
  toolUse: ToolUseBlock,
  context: ToolUseContext,
  canUseTool: CanUseToolFn
): Promise<ToolResult> {
  const tool = context.options.tools.find(t => t.name === toolUse.name)

  // 1. Input Schema 验证
  const parsedInput = tool?.inputSchema.safeParse(toolUse.input)
  if (!parsedInput?.success) {
    return {
      content: [{
        type: 'tool_result',
        tool_use_id: toolUse.id,
        content: `Invalid input: ${parsedInput?.error.message}`
      }],
      suppression: { type: 'error' }
    }
  }

  // 2. validateInput Hook
  if (tool?.validateInput) {
    const validation = await tool.validateInput(parsedInput.data, context)
    if (!validation.success) {
      return {
        content: [{
          type: 'tool_result',
          tool_use_id: toolUse.id,
          content: `Validation failed: ${validation.message}`
        }],
        suppression: { type: 'error' }
      }
    }
  }

  // 3. 权限检查
  const permissionResult = await canUseTool(
    tool!.name,
    parsedInput.data,
    context
  )

  switch (permissionResult.behavior) {
    case 'deny':
      return {
        content: [{
          type: 'tool_result',
          tool_use_id: toolUse.id,
          content: permissionResult.message ?? `Permission denied for ${tool!.name}`
        }],
        suppression: { type: 'permission_denied' }
      }

    case 'ask':
      // 暂停，等待用户确认
      // 通过 context.setToolJSX 显示提示
      // 用户确认后递归调用
      return await waitForPermission(toolUse, context, canUseTool)

    case 'passthrough':
      // MCP 工具跳过
      return await tool!.call(
        parsedInput.data,
        context,
        canUseTool,
        undefined,
        undefined
      )

    case 'allow':
    default:
      // 继续执行
      break
  }

  // 4. 执行 tool.call()
  return await tool!.call(
    parsedInput.data,
    context,
    canUseTool,
    undefined,
    (progress) => {
      // 进度回调
      context.setToolJSX?.(toolUse.id, {
        type: 'progress',
        toolName: tool!.name,
        progress
      })
    }
  )
}
```

---

## 6. 权限系统

### 6.1 权限决策类型

```typescript
// src/types/permissions.ts
type PermissionDecision =
  | {
      behavior: 'allow'
      updatedInput?: Record<string, unknown>  // 可修改输入
    }
  | {
      behavior: 'deny'
      message?: string
      decisionReason?: PermissionDecisionReason
      updatedInput?: Record<string, unknown>
    }
  | {
      behavior: 'ask'
      message?: string
      suggestions?: PermissionUpdate[]
    }
  | {
      behavior: 'passthrough'  // 跳过权限检查 (MCP)
    }
```

### 6.2 权限决策原因

```typescript
// src/types/permissions.ts
type PermissionDecisionReason =
  | 'user_requested'           // 用户明确请求
  | 'always_allow_rule'        // 匹配始终允许规则
  | 'tool_default_allow'      // 工具默认允许
  | 'transient_permission'     // 临时权限
  | 'denied_rule'             // 匹配拒绝规则
  | 'safety_check_blocked'    // 安全检查阻止
  | 'path_blocked'            // 路径被阻止 (.git/ 等)
  | 'auto_mode_denied'        // 自动模式拒绝
  | 'auto_mode_ask'           // 自动模式询问
```

### 6.3 权限规则匹配

```typescript
// src/utils/permissions/shellRuleMatching.ts
// Shell 命令使用特殊匹配逻辑

interface ShellPermissionRule {
  pattern: {
    cmd: string           // 命令名 (如 "rm", "git")
    args?: string         // 参数模式 (支持 * 通配符)
  }
  behavior: 'allow' | 'deny'
  reason?: string
}

// 示例规则
const rules: ShellPermissionRule[] = [
  { pattern: { cmd: 'git', args: '*' }, behavior: 'allow' },
  { pattern: { cmd: 'rm', args: '*' }, behavior: 'deny', reason: 'Use rm -rf with caution' },
  { pattern: { cmd: 'npm', args: 'install *' }, behavior: 'allow' },
]

function matchShellCommand(
  command: string,
  rules: ShellPermissionRule[]
): 'allow' | 'deny' | 'ask' {
  // 解析命令和参数
  const [cmd, ...args] = command.split(' ')
  const argsStr = args.join(' ')

  for (const rule of rules) {
    if (cmd !== rule.pattern.cmd) continue

    // 简单通配符匹配
    const pattern = rule.pattern.args?.replace(/\*/g, '.*') ?? '.*'
    const regex = new RegExp(`^${pattern}$`)

    if (regex.test(argsStr)) {
      return rule.behavior
    }
  }

  return 'ask'  // 默认询问
}
```

### 6.4 权限模式

```typescript
// src/types/permissions.ts
type PermissionMode =
  | 'auto'           // AI 决定何时询问
  | 'bypass'         // 允许所有操作 (危险)
  | 'acceptEdits'    // 允许编辑，不允许破坏性命令
  | 'plan'           // 计划模式，询问所有工具
  | 'review'         // 仅在执行前审查

// 模式转换
function toExternalPermissionMode(mode: PermissionMode): string {
  switch (mode) {
    case 'auto': return 'auto'
    case 'bypass': return 'bypass'
    case 'acceptEdits': return 'limited'
    case 'plan': return 'plan'
    case 'review': return 'review'
  }
}
```

---

## 7. 工具实现示例

### 7.1 FileReadTool

```typescript
// src/tools/FileReadTool/FileReadTool.ts
const FileReadTool = buildTool({
  name: 'Read',
  inputSchema: lazySchema(() =>
    z.strictObject({
      file_path: z.string().describe('要读取的文件路径'),
      offset: z.number().optional().describe('字节偏移量'),
      limit: z.number().optional().describe('读取字节数限制'),
      show_line_numbers: z.boolean().optional().default(false),
      omit: z.array(z.number()).optional().describe('要跳过的行号'),
    })
  ),

  // 并发安全 (只读)
  isConcurrencySafe: () => true,
  isReadOnly: () => true,

  // 返回描述
  description: async (input) =>
    `Read file "${input.file_path}"${input.limit ? ` (limit ${input.limit} bytes)` : ''}`,

  userFacingName: () => 'Read',

  // 路径提取 (用于权限匹配)
  getPath: (input) => input.file_path,

  maxResultSizeChars: 50000,

  // 验证输入
  validateInput: async (input, context) => {
    // 检查文件是否在 readFileState 中
    const fileState = context.readFileState.get(input.file_path)
    if (!fileState) {
      return {
        success: false,
        message: `File "${input.file_path}" has not been read yet`
      }
    }
    return { success: true }
  },

  // 执行
  call: async (input, context) => {
    const { file_path, offset, limit, show_line_numbers, omit } = input

    // 读取文件
    const content = await readFile(file_path, { offset, limit })

    // 处理行号显示
    const lines = content.split('\n')
    const displayLines = omit
      ? lines.filter((_, i) => !omit.includes(i + 1))
      : lines

    // 渲染
    const rendered = show_line_numbers
      ? displayLines.map((l, i) => `${i + 1}: ${l}`).join('\n')
      : displayLines.join('\n')

    // 更新文件状态缓存
    context.updateFileState?.(file_path, {
      ...context.readFileState.get(file_path),
      lastRead: Date.now(),
    })

    return {
      content: [{
        type: 'tool_result',
        tool_use_id: '',  // 填充
        content: rendered,
      }]
    }
  },

  // UI 渲染
  renderToolUseMessage: (input, options) => (
    <Box>
      <Text dimColor>Reading </Text>
      <Text bold>{input.file_path}</Text>
    </Box>
  ),
})
```

### 7.2 BashTool

```typescript
// src/tools/BashTool/BashTool.tsx
const BashTool = buildTool({
  name: 'Bash',
  aliases: ['Shell', 'Command'],
  inputSchema: lazySchema(() => bashInputSchema),

  // 非并发安全 (可能有副作用)
  isConcurrencySafe: () => false,

  // 可能破坏性 (取决于命令)
  isDestructive: (input) => {
    const cmd = input.command.split(' ')[0]
    return ['rm', 'rmdir', 'dd', 'mkfs'].includes(cmd)
  },

  description: (input) => `Execute shell command: ${input.command}`,

  userFacingName: () => 'Bash',

  getPath: () => undefined,  // 不适用

  maxResultSizeChars: 10000,

  checkPermissions: async (input, context) => {
    const { command } = input

    // 检查权限规则
    const decision = matchShellCommand(command, context.toolPermissionContext.rules)

    if (decision === 'allow') {
      return { behavior: 'allow' }
    }

    if (decision === 'deny') {
      return {
        behavior: 'deny',
        message: `Shell command "${command}" is not allowed`
      }
    }

    // 'ask' - 根据权限模式决定
    if (context.toolPermissionContext.mode === 'bypass') {
      return { behavior: 'allow' }
    }

    if (context.toolPermissionContext.mode === 'acceptEdits') {
      // 允许读取命令，拒绝写入命令
      const cmd = command.split(' ')[0]
      const readCommands = ['cat', 'ls', 'grep', 'find', 'head', 'tail', 'echo']
      if (readCommands.includes(cmd)) {
        return { behavior: 'allow' }
      }
    }

    return {
      behavior: 'ask',
      message: `Allow shell command "${command}"?`,
      suggestions: [
        { type: 'update_rule', rule: { command, behavior: 'allow' } }
      ]
    }
  },

  call: async (input, context, canUseTool) => {
    const { command, timeout = 60000, currentDir } = input

    // 使用 Node.js child_process 执行
    const result = await execAsync(command, {
      cwd: currentDir ?? process.cwd(),
      timeout,
      signal: context.abortController.signal,
    })

    return {
      content: [{
        type: 'tool_result',
        tool_use_id: '',
        content: result.stdout || result.stderr,
      }]
    }
  },

  renderToolUseMessage: (input, options) => (
    <Box>
      <Text dimColor>Executing </Text>
      <Text bold color="cyan">{input.command}</Text>
    </Box>
  ),
})
```

---

## 8. UI 渲染系统

### 8.1 渲染接口

```typescript
// 工具使用消息渲染
renderToolUseMessage(
  input: z.infer<Input>,  // 工具输入
  options: RenderToolUseMessageOptions
): React.ReactNode

// 工具结果消息渲染
renderToolResultMessage?(
  content: ToolResultContent<Output>,
  progressMessages: React.ReactNode[],
  options: RenderToolResultMessageOptions
): React.ReactNode

// 工具进度消息渲染
renderToolUseProgressMessage?(
  progressMessages: React.ReactNode[],
  options: RenderToolProgressMessageOptions
): React.ReactNode
```

### 8.2 渲染上下文

```typescript
// src/Tool.ts
type RenderToolUseMessageOptions = {
  isStreaming: boolean
  toolUseId: string
  parentMessageId: string
  // ...
}

// src/Tool.ts
type RenderToolResultMessageOptions = {
  isLast: boolean
  streamingToolUseIDs: Set<string>
  // ...
}
```

### 8.3 Ink 渲染组件

```typescript
// src/components/ToolUseMessage.tsx
export const ToolUseMessage: React.FC<{
  toolName: string
  input: unknown
  toolUseId: string
  isStreaming: boolean
}> = ({ toolName, input, toolUseId, isStreaming }) => {
  const tool = useTool(toolName)

  if (!tool) {
    return <Text dimColor>Unknown tool: {toolName}</Text>
  }

  return (
    <Box flexDirection="column" marginY={1}>
      {tool.renderToolUseMessage?.(input, { isStreaming, toolUseId })}
      {isStreaming && (
        <Box marginLeft={2}>
          <Spinner variant="dots12" />
        </Box>
      )}
    </Box>
  )
}
```

---

## 9. 工具搜索 (ToolSearch)

### 9.1 延迟加载机制

```typescript
// src/tools/ToolSearchTool/ToolSearchTool.ts
// 用于发现和加载延迟的工具

const ToolSearchTool = buildTool({
  name: 'ToolSearch',
  inputSchema: lazySchema(() =>
    z.strictObject({
      query: z.string().describe('Search query for tools'),
    })
  ),

  // 延迟加载 - 不应立即加载
  shouldDefer: true,
  alwaysLoad: false,

  call: async (input, context) => {
    const { query } = input

    // 从所有工具中搜索
    const allTools = context.options.tools
    const matches = allTools.filter(tool => {
      const searchText = [
        tool.name,
        tool.description?.toString() ?? '',
        tool.searchHint ?? '',
        ...(tool.aliases ?? [])
      ].join(' ').toLowerCase()

      return searchText.includes(query.toLowerCase())
    })

    return {
      content: [{
        type: 'tool_result',
        tool_use_id: '',
        content: matches.map(t => t.name).join(', ')
      }]
    }
  }
})
```

---

## 10. 设计模式总结

### 10.1 模式列表

| 模式 | 应用 | 优势 |
|------|------|------|
| **工厂模式** | `buildTool()` | 统一创建，类型安全，默认值 |
| **策略模式** | `checkPermissions` | 可插拔的权限检查 |
| **观察者模式** | `onProgress` 回调 | 实时进度更新 |
| **模板方法** | Tool 基类 | 可继承定制行为 |
| **责任链模式** | 权限检查链 | 分离关注点 |
| **享元模式** | `toolByName` Map | 高效工具查找 |
| **Builder** | Zod Schema | 声明式输入验证 |

### 10.2 安全性设计

1. **默认拒绝** - `isConcurrencySafe`, `isReadOnly` 默认 false
2. **Schema 验证** - 所有输入必须通过 Zod 验证
3. **路径验证** - 防止 `../../etc/passwd` 攻击
4. **权限检查** - 危险操作需要明确授权
5. **超时控制** - 防止长时间运行命令
6. **结果大小限制** - 防止内存耗尽

### 10.3 性能设计

1. **并发执行** - `isConcurrencySafe` 工具并行运行
2. **Map 索引** - O(1) 工具查找
3. **延迟加载** - `shouldDefer` 工具按需加载
4. **Schema 缓存** - `lazySchema` 避免重复解析
5. **结果大小限制** - 防止大结果占用内存

---

*文档版本: 2026-03-31*
