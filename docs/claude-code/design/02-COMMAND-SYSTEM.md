# 命令系统设计文档

> 本文档详细解析 Claude Code 命令系统的架构设计、类型定义、执行流程和扩展机制。

---

## 1. 设计概述

### 1.1 设计目标

命令系统是用户与 Claude Code 交互的**主要入口之一**：

- **slash 命令** - 用户输入 `/command args` 触发
- **技能执行** - 复杂的多轮交互模式
- **UI 命令** - 需要复杂交互界面的命令

### 1.2 核心挑战

1. 如何统一处理不同类型的命令（prompt/local/local-jsx）？
2. 如何支持命令的懒加载（减小初始 bundle 大小）？
3. 如何实现命令的参数解析和验证？
4. 如何在命令中安全地限制工具访问？
5. 如何支持命令间的状态传递？

---

## 2. 类型系统

### 2.1 Command 类型层次

```
Command
  │
  ├─── CommandBase (基础属性)
  │        │
  │        ├─── name: string
  │        ├─── description: string
  │        ├─── aliases?: string[]
  │        ├─── isEnabled?: () => boolean
  │        ├─── isHidden?: boolean
  │        ├─── userInvocable?: boolean
  │        ├─── argumentHint?: string
  │        └─── whenToUse?: string
  │
  └─── CommandBase + 具体类型
           │
           ├─── PromptCommand (技能类型)
           │        │
           │        ├─── type: 'prompt'
           │        ├─── getPromptForCommand(args, context)
           │        ├─── allowedTools?: string[]
           │        ├─── model?: string
           │        ├─── hooks?: HooksSettings
           │        └─── context?: 'inline' | 'fork'
           │
           ├─── LocalCommand (简单命令)
           │        │
           │        ├─── type: 'local'
           │        └─── load(): Promise<LocalCommandModule>
           │
           └─── LocalJSXCommand (UI 命令)
                    │
                    ├─── type: 'local-jsx'
                    └─── load(): Promise<LocalJSXCommandModule>
```

### 2.2 核心类型定义

```typescript
// src/types/command.ts:175-206
export type CommandBase = {
  // 基础元数据
  name: string
  description: string
  hasUserSpecifiedDescription?: boolean

  // 可用性控制
  availability?: CommandAvailability[]
  isEnabled?: () => boolean
  isHidden?: boolean

  // 调用控制
  aliases?: string[]
  userInvocable?: boolean  // 是否允许 /command 语法
  argumentHint?: string
  whenToUse?: string

  // 元数据
  version?: string
  isMcp?: boolean
  disableModelInvocation?: boolean  // 禁止模型调用

  // 加载来源
  loadedFrom?: CommandSource

  // 特殊分类
  kind?: 'workflow'
  immediate?: boolean  // 无需等待 stop point
  isSensitive?: boolean  // 从历史中编辑参数

  // 显示
  userFacingName?: () => string
}

// 命令来源
type CommandSource =
  | 'commands_DEPRECATED'  // 旧版 commands/ 目录
  | 'skills'              // 技能系统
  | 'plugin'              // 插件
  | 'managed'             // 托管策略
  | 'bundled'             // 内置
  | 'mcp'                 // MCP 服务器

// 可用平台
type CommandAvailability = 'claude-ai' | 'console'
```

### 2.3 PromptCommand (技能命令)

```typescript
// src/types/command.ts:25-57
export type PromptCommand = CommandBase & {
  type: 'prompt'

  // 内容
  progressMessage: string
  contentLength: number
  argNames?: string[]

  // 工具限制
  allowedTools?: string[]  // 白名单

  // 模型控制
  model?: string
  disableNonInteractive?: boolean

  // 来源
  source: SettingSource | 'builtin' | 'mcp' | 'plugin' | 'bundled'
  pluginInfo?: {
    pluginManifest: PluginManifest
    repository: string
  }

  // 生命周期钩子
  hooks?: HooksSettings

  // 技能资源
  skillRoot?: string  // 基础目录

  // 执行上下文
  context?: 'inline' | 'fork'
  agent?: string

  // 条件激活
  effort?: EffortValue
  paths?: string[]  // 匹配文件时激活

  // 执行入口
  getPromptForCommand(
    args: string,
    context: ToolUseContext
  ): Promise<ContentBlockParam[]>
}
```

### 2.4 LocalCommand (本地命令)

```typescript
// src/types/command.ts:74-78
type LocalCommand = CommandBase & {
  type: 'local'
  supportsNonInteractive: boolean
  load: () => Promise<LocalCommandModule>
}

// LocalCommand 模块
interface LocalCommandModule {
  call: (
    args: string,
    context: ToolUseContext
  ) => Promise<LocalCommandResult>
}

// 返回结果类型
type LocalCommandResult =
  | { type: 'text'; value: string }
  | { type: 'compact'; compactionResult: unknown; displayText?: string }
  | { type: 'skip' }
```

### 2.5 LocalJSXCommand (UI 命令)

```typescript
// src/types/command.ts:144-152
type LocalJSXCommand = CommandBase & {
  type: 'local-jsx'
  load: () => Promise<LocalJSXCommandModule>
}

interface LocalJSXCommandModule {
  // React 组件，懒加载
  component: React.ComponentType<LocalJSXCommandProps>
}

interface LocalJSXCommandProps {
  args: string
  run: (
    onDone: LocalJSXCommandOnDone,
    context: ToolUseContext & LocalJSXCommandContext
  ) => Promise<React.ReactNode>
  onExit: () => void
}

type LocalJSXCommandOnDone = (
  result: LocalCommandResult
) => void

type LocalJSXCommandContext = {
  // 命令执行所需的上下文
}
```

---

## 3. 命令注册

### 3.1 注册表结构

```typescript
// src/commands.ts:258-346
// 单例注册表
const COMMANDS = memoize((): Command[] => [
  // 内置命令
  addDir,
  advisor,
  agents,
  branch,
  btw,
  clear,
  commit,
  commitPushPr,
  compact,
  config,
  cost,
  diff,
  doctor,
  exit,
  feedback,
  help,
  // ... 70+ 命令
])()
```

### 3.2 命令加载流程

```typescript
// src/commands.ts:449-468
async function loadAllCommands(cwd: string): Promise<Command[]> {
  const [
    { skillDirCommands, pluginSkills, bundledSkills, builtinPluginSkills },
    pluginCommands,
    workflowCommands,
  ] = await Promise.all([
    getSkills(cwd),           // 技能系统
    getPluginCommands(),     // 插件命令
    getWorkflowCommands?.(), // 工作流 (可选)
  ])

  return [
    ...bundledSkills,         // 1. 内置技能
    ...builtinPluginSkills,   // 2. 内置插件技能
    ...skillDirCommands,      // 3. 技能目录
    ...workflowCommands,      // 4. 工作流
    ...pluginCommands,        // 5. 插件命令
    ...pluginSkills,          // 6. 插件技能
    ...COMMANDS,              // 7. 内置命令
  ]
}

// 公开 API
export async function getCommands(cwd: string): Promise<Command[]> {
  const allCommands = await loadAllCommands(cwd)

  // 按可用性过滤
  const platform = getCurrentPlatform()
  return allCommands.filter(cmd => {
    // 检查 platform 可用性
    if (cmd.availability?.length && !cmd.availability.includes(platform)) {
      return false
    }
    // 检查 isEnabled
    if (cmd.isEnabled?.() === false) {
      return false
    }
    return true
  })
}

// 查找命令
export function findCommand(
  name: string,
  commands: Command[]
): Command | undefined {
  // 1. 精确匹配 name
  const byName = commands.find(c => c.name === name)
  if (byName) return byName

  // 2. 匹配别名
  for (const cmd of commands) {
    if (cmd.aliases?.includes(name)) {
      return cmd
    }
  }

  return undefined
}
```

---

## 4. 斜杠命令解析

### 4.1 解析器实现

```typescript
// src/utils/slashCommandParsing.ts
export interface ParsedSlashCommand {
  commandName: string  // 命令名称
  args: string         // 参数字符串
  isMcp: boolean       // 是否为 MCP 命令
}

/**
 * 解析斜杠命令输入
 * "/commit -m 'fix bug'" → { commandName: 'commit', args: "-m 'fix bug'" }
 * "/mcp:tool (MCP) arg" → { commandName: 'mcp:tool (MCP)', args: 'arg', isMcp: true }
 */
export function parseSlashCommand(input: string): ParsedSlashCommand | null {
  const trimmedInput = input.trim()

  // 必须以 / 开头
  if (!trimmedInput.startsWith('/')) {
    return null
  }

  // 移除前导 /
  const withoutSlash = trimmedInput.slice(1)

  // 按空格分割
  const words = withoutSlash.split(/\s+/)

  if (!words[0]) {
    return null
  }

  let commandName = words[0]
  let isMcp = false
  let argsStartIndex = 1

  // 检查 MCP 命令格式: "/mcp:tool (MCP) arg1 arg2"
  // 第二个词是 "(MCP)" 表示这是 MCP 命令
  if (words.length > 1 && words[1] === '(MCP)') {
    commandName = commandName + ' (MCP)'  // 添加 MCP 标记
    isMcp = true
    argsStartIndex = 2
  }

  // 合并参数
  const args = words.slice(argsStartIndex).join(' ')

  return { commandName, args, isMcp }
}
```

### 4.2 解析示例

| 输入 | 解析结果 |
|------|----------|
| `"/commit -m 'fix bug'"` | `{ commandName: 'commit', args: "-m 'fix bug'", isMcp: false }` |
| `"/mcp:tool (MCP) arg1"` | `{ commandName: 'mcp:tool (MCP)', args: 'arg1', isMcp: true }` |
| `"/help"` | `{ commandName: 'help', args: '', isMcp: false }` |
| `"search foo"` | `null` (不以 / 开头) |

---

## 5. 命令执行流程

### 5.1 完整执行管道

```
用户输入 "/commit -m 'fix bug'"
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  processSlashCommand()                                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 1. parseSlashCommand(input)                                │ │
│  │    → { commandName: 'commit', args: "-m 'fix bug'" }        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 2. findCommand('commit', commands)                          │ │
│  │    - 查找 name                                              │ │
│  │    - 查找 aliases                                           │ │
│  │    - 返回 Command 或 undefined                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 3. 验证检查                                                  │ │
│  │    - 命令存在?                                              │ │
│  │    - userInvocable === false? (只能模型调用)                  │ │
│  │    - isEnabled?() === false?                                │ │
│  │    - platform 可用性?                                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│              ┌───────────────┴───────────────┐                  │
│              │                               │                  │
│              ▼                               ▼                  │
│  ┌─────────────────────────┐   ┌─────────────────────────────────┐│
│  │ type === 'local-jsx'    │   │ type === 'prompt'               ││
│  │                         │   │                                 ││
│  │ 4a. Lazy 加载组件        │   │ 4b. 检查 context               ││
│  │    load().then(m => {   │   │    - 'inline' → 直接执行       ││
│  │      render(m.component)│   │    - 'fork' → 子 Agent 执行    ││
│  │    })                   │   │                                 ││
│  │                         │   │ 4c. 调用                        ││
│  │ 4a. 组件渲染后          │   │    getPromptForCommand(args)    ││
│  │    onDone(result) 回调  │   │    → ContentBlockParam[]        ││
│  │                         │   │                                 ││
│  │                         │   │ 4d. 工具限制                    ││
│  │                         │   │    allowedTools? → 临时修改      ││
│  │                         │   │    工具权限上下文               ││
│  └─────────────────────────┘   └─────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 5. 返回 SlashCommandResult                                   │ │
│  │    - messages: Message[]                                    │ │
│  │    - shouldQuery: boolean                                   │ │
│  │    - allowedTools?: Tool[]                                  │ │
│  │    - resultText?: string (local 命令)                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 processSlashCommand 实现

```typescript
// src/utils/processUserInput/processSlashCommand.tsx:309-700
export async function processSlashCommand(
  inputString: string,
  precedingInputBlocks: ContentBlockParam[],
  imageContentBlocks: ContentBlockParam[],
  attachmentMessages: AttachmentMessage[],
  context: ProcessUserInputContext,
  setToolJSX: SetToolJSXFn,
  uuid?: string,
  isAlreadyProcessing?: boolean,
  canUseTool?: CanUseToolFn,
): Promise<SlashCommandResult> {
  // 1. 解析输入
  const parsed = parseSlashCommand(inputString)
  if (!parsed) {
    throw new Error('Not a slash command')
  }

  const { commandName, args, isMcp } = parsed

  // 2. 查找命令
  const commands = await getCommands(context.cwd)
  const command = findCommand(commandName, commands)

  if (!command) {
    throw new Error(`Command not found: ${commandName}`)
  }

  // 3. 验证调用权限
  if (!command.userInvocable && !isMcp) {
    throw new Error(`Command not user-invocable: ${commandName}`)
  }

  // 4. 根据类型执行
  switch (command.type) {
    case 'local-jsx':
      return await executeLocalJSXCommand(command, args, context, setToolJSX)

    case 'prompt':
      return await executePromptCommand(command, args, context, canUseTool)

    case 'local':
      return await executeLocalCommand(command, args, context)

    default:
      throw new Error(`Unknown command type: ${(command as Command).type}`)
  }
}
```

### 5.3 Prompt 命令执行 (inline)

```typescript
// src/utils/processUserInput/processSlashCommand.tsx:600-650
async function executePromptCommand(
  command: PromptCommand,
  args: string,
  context: ProcessUserInputContext,
  canUseTool?: CanUseToolFn
): Promise<SlashCommandResult> {
  // Fork 模式: 在子 Agent 中执行
  if (command.context === 'fork') {
    return await executeForkedSlashCommand(
      command as CommandBase & PromptCommand,
      args,
      context,
      precedingInputBlocks,
      setToolJSX,
      canUseTool
    )
  }

  // Inline 模式: 直接获取 prompt 内容
  const toolUseContext = buildToolUseContext(context)

  // 应用工具限制
  let modifiedContext = toolUseContext
  if (command.allowedTools) {
    modifiedContext = {
      ...toolUseContext,
      toolPermissionContext: {
        ...toolUseContext.toolPermissionContext,
        alwaysAllowRules: {
          ...toolUseContext.toolPermissionContext.alwaysAllowRules,
          command: command.allowedTools,  // 临时覆盖
        },
      },
    }
  }

  // 获取 prompt 内容
  const contentBlocks = await command.getPromptForCommand(
    args,
    modifiedContext
  )

  // 构建结果
  return {
    command,
    messages: [
      // 用户消息引用命令
      {
        type: 'user',
        content: [
          {
            type: 'text',
            text: inputString,
          },
        ],
      },
    ],
    shouldQuery: true,  // 需要发送消息到模型
    allowedTools: command.allowedTools,
    resultText: undefined,
  }
}
```

### 5.4 Forked 命令执行

```typescript
// src/utils/processUserInput/processSlashCommand.tsx:62-200
async function executeForkedSlashCommand(
  command: CommandBase & PromptCommand,
  args: string,
  context: ProcessUserInputContext,
  precedingInputBlocks: ContentBlockParam[],
  setToolJSX: SetToolJSXFn,
  canUseTool?: CanUseToolFn
): Promise<SlashCommandResult> {
  // 1. 准备子 Agent 配置
  const agentConfig = {
    agentType: command.agent ?? 'GeneralPurpose',
    tools: command.allowedTools,
    skills: command.hooks?.PreToolUse?.map(h => h.skill).filter(Boolean),
    permissionMode: 'auto',
    // fork 模式: 隔离执行，有自己的 token 预算
    isolation: 'worktree',
  }

  // 2. 构建初始 prompt
  const initialPrompt = await command.getPromptForCommand(args, context)

  // 3. 派生子 Agent
  const agentResult = await runAgent({
    config: agentConfig,
    initialPrompt,
    parentContext: context,
    onProgress: (progress) => {
      setToolJSX?.(progress.toolUseId, progress)
    },
  })

  // 4. 收集结果
  const resultMessages: Message[] = []
  for await (const msg of agentResult) {
    resultMessages.push(msg)
  }

  // 5. 返回结果
  return {
    command,
    messages: resultMessages,
    shouldQuery: false,  // 不需要再查询
    resultText: extractResultText(resultMessages),
  }
}
```

---

## 6. 工具限制机制

### 6.1 为什么需要工具限制？

某些命令（如 `/commit`）只需要特定的工具：

```typescript
// src/commands/commit.ts
const ALLOWED_TOOLS = [
  'Bash(git add:*)',      // git add
  'Bash(git status:*)',   // git status
  'Bash(git commit:*)',    // git commit
  'Read(*)',               // 读取文件
  'Glob(*)',               // 查找文件
]
```

### 6.2 工具限制实现

```typescript
// src/skills/loadSkillsDir.ts:377-391
function createToolRestrictedContext(
  originalContext: ToolUseContext,
  allowedTools: string[]
): ToolUseContext {
  return {
    ...originalContext,
    toolPermissionContext: {
      ...originalContext.toolPermissionContext,
      alwaysAllowRules: {
        ...originalContext.toolPermissionContext.alwaysAllowRules,
        // 添加命令级别的工具白名单
        command: allowedTools,
      },
      // 清空其他允许规则，只保留白名单
      denyRules: [],  // 保留安全检查
    },
  }
}

// 使用
const restrictedContext = createToolRestrictedContext(
  context,
  command.allowedTools ?? []
)

const contentBlocks = await command.getPromptForCommand(args, restrictedContext)
```

### 6.3 工具限制匹配

```typescript
// src/utils/permissions/permissions.ts
// 工具限制使用 glob 模式匹配

function matchesToolPattern(toolName: string, pattern: string): boolean {
  // 转换为正则
  // "Bash(git add:*)" → /^Bash\(git add:.*\)$/
  const regex = globToRegex(pattern)
  return regex.test(toolName)
}

function globToRegex(glob: string): RegExp {
  return new RegExp(
    '^' +
    glob
      .replace(/\./g, '\\.')
      .replace(/\*/g, '.*')
      .replace(/\?/g, '.') +
    '$'
  )
}
```

---

## 7. 命令实现示例

### 7.1 /commit 命令 (Prompt 类型)

```typescript
// src/commands/commit.ts
const commitCommand: Command = {
  type: 'prompt',
  name: 'commit',
  description: 'Create a git commit with a descriptive message',
  aliases: ['ci'],
  argumentHint: '[-m <message>]',
  whenToUse: 'When you want to commit staged changes',

  // 限制工具
  allowedTools: [
    'Bash(git status:*)',
    'Bash(git add:*)',
    'Bash(git commit:*)',
    'Read(*)',
    'Glob(*)',
  ],

  // 不允许模型直接调用
  disableModelInvocation: false,
  userInvocable: true,

  progressMessage: 'Creating commit...',

  getPromptForCommand: async (args, context) => {
    // 解析参数
    const message = extractCommitMessage(args)

    return [
      {
        type: 'text',
        text: `Create a git commit. Use git status to see staged files.\n` +
              `Commit message: ${message ?? 'Provide a descriptive message'}\n` +
              `After staging files, use: git commit -m "<message>"`
      }
    ]
  }
}
```

### 7.2 /clear 命令 (Local 类型)

```typescript
// src/commands/clear/clear.ts
const clearCommand: Command = {
  type: 'local',
  name: 'clear',
  description: 'Clear the conversation history',
  aliases: ['cl'],
  userInvocable: true,
  supportsNonInteractive: true,

  load: async () => ({
    call: async (args, context) => {
      // 清空消息
      context.setAppState((prev) => ({
        ...prev,
        messages: [],  // 清空消息
      }))

      return { type: 'text', value: 'Conversation cleared' }
    }
  })
}
```

### 7.3 /help 命令 (LocalJSX 类型)

```typescript
// src/commands/help/help.tsx
const helpCommand: Command = {
  type: 'local-jsx',
  name: 'help',
  description: 'Show help information',
  aliases: ['h', '?'],
  userInvocable: true,

  load: async () => {
    // 懒加载 React 组件
    const { HelpScreen } = await import('./HelpScreen.tsx')
    return { component: HelpScreen }
  }
}

// HelpScreen.tsx
const HelpScreen: React.FC<{
  run: (onDone: OnDone, context: ToolUseContext) => Promise<React.ReactNode>
  onExit: () => void
}> = ({ run, onExit }) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [commands, setCommands] = useState<Command[]>([])

  useEffect(() => {
    loadCommands().then(setCommands)
  }, [])

  const filteredCommands = commands.filter(cmd =>
    cmd.name.includes(searchQuery) ||
    cmd.description.includes(searchQuery)
  )

  return (
    <Box flexDirection="column">
      <Text bold>Available Commands</Text>
      <TextInput
        value={searchQuery}
        onChange={setSearchQuery}
        placeholder="Search commands..."
      />
      {/* 命令列表 */}
      {filteredCommands.map(cmd => (
        <CommandRow key={cmd.name} command={cmd} />
      ))}
      {/* 退出 */}
      <Button onPress={onExit}>Exit</Button>
    </Box>
  )
}
```

---

## 8. 命令与工具的交互

### 8.1 命令调用工具

命令内部可以调用工具：

```typescript
// 某些命令（如 /review）需要调用工具执行分析
const reviewCommand: Command = {
  type: 'prompt',

  getPromptForCommand: async (args, context) => {
    // 命令内部可以使用工具
    // 这通常通过 fork 到子 Agent 实现
    return [{
      type: 'text',
      text: `Review the code changes...`
    }]
  }
}
```

### 8.2 SkillTool (模型可调用技能)

```typescript
// src/tools/SkillTool/SkillTool.ts
// 模型可以通过 SkillTool 调用技能

const SkillTool = buildTool({
  name: 'Skill',
  aliases: ['skills', 'invoke_skill'],

  inputSchema: lazySchema(() =>
    z.strictObject({
      skill: z.string().describe('Skill name to invoke'),
      args: z.string().optional().describe('Arguments for the skill'),
    })
  ),

  // 列出可用技能
  getPromptForSkillList: async (context) => {
    const commands = await getSkillCommands(context.cwd)
    return commands
      .filter(cmd => cmd.loadedFrom === 'skills')
      .map(cmd => ({
        name: cmd.name,
        description: cmd.description,
        argumentHint: cmd.argumentHint,
      }))
  },

  // 执行技能
  call: async (input, context) => {
    const { skill, args } = input

    // 查找技能
    const commands = await getCommands(context.cwd)
    const command = findCommand(skill, commands)

    if (!command || command.type !== 'prompt') {
      return {
        content: [{
          type: 'tool_result',
          tool_use_id: '',
          content: `Skill not found: ${skill}`
        }]
      }
    }

    // 执行技能
    const result = await executePromptCommand(command, args ?? '', context)

    return {
      content: [{
        type: 'tool_result',
        tool_use_id: '',
        content: result.resultText ?? 'Skill executed'
      }]
    }
  }
})
```

---

## 9. MCP 命令

### 9.1 MCP 命令暴露

```typescript
// src/commands.ts:547-559
export function getMcpSkillCommands(
  mcpCommands: readonly Command[]
): readonly Command[] {
  if (!feature('MCP_SKILLS')) {
    return []
  }

  return mcpCommands.filter(
    cmd =>
      cmd.type === 'prompt' &&
      cmd.loadedFrom === 'mcp' &&
      !cmd.disableModelInvocation
  )
}

// MCP 服务器可以提供命令
interface MCPServer {
  commands: Command[]

  // 命令格式化为技能
  toSkillCommand(): SkillCommand {
    return {
      type: 'prompt',
      name: `mcp:${this.name}`,
      description: this.description,
      loadedFrom: 'mcp',
      getPromptForCommand: async (args) => {
        // 调用 MCP 命令
        const result = await this.execute(args)
        return [{ type: 'text', text: result }]
      }
    }
  }
}
```

---

## 10. 设计模式总结

### 10.1 模式列表

| 模式 | 应用 | 优势 |
|------|------|------|
| **策略模式** | 命令类型 (prompt/local/local-jsx) | 统一接口，多种实现 |
| **工厂模式** | 命令创建 | 懒加载，类型安全 |
| **观察者模式** | onDone 回调 | 异步结果处理 |
| **责任链模式** | 权限检查 | 可组合的验证 |
| **享元模式** | 命令注册表 | 高效查找 |
| **Builder** | Context 构建 | 可选的上下文修改 |

### 10.2 懒加载设计

```typescript
// LocalJSX 命令使用动态 import 实现懒加载
const helpCommand: Command = {
  type: 'local-jsx',
  load: async () => {
    // 只在需要时加载
    const { HelpScreen } = await import('./HelpScreen.tsx')
    return { component: HelpScreen }
  }
}

// Bundle 大小优化
// 主 bundle 不包含 HelpScreen 等大型组件
// 按需加载减少初始加载时间
```

### 10.3 安全性设计

1. **userInvocable 标志** - 敏感命令只能代码调用
2. **工具白名单** - 限制命令可用的工具
3. **参数清理** - 敏感参数从历史中排除
4. **平台限制** - 命令的平台可用性控制

---

*文档版本: 2026-03-31*
