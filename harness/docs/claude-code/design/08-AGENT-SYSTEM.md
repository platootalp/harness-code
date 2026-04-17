# Agent 系统设计文档

> 本文档详细解析 Claude Code Agent 系统的架构设计、子 Agent 生命周期、Agent 间通信和协调机制。

---

## 1. 设计概述

### 1.1 什么是 Agent？

Agent 是一个**自主执行的子进程**，拥有独立的：

- 对话上下文
- 工具集
- Token 预算
- 执行状态

### 1.2 Agent vs Tool

| 方面 | 工具 (Tool) | Agent |
|------|-------------|-------|
| **自主性** | 执行单一操作 | 执行多轮对话 |
| **上下文** | 无内部状态 | 有完整的对话历史 |
| **决策** | AI 决定调用 | AI 自主决定行动 |
| **生命周期** | 单次调用 | 多轮对话 |
| **隔离** | 共享上下文 | 可隔离执行 |

### 1.3 Agent 类型

```typescript
// Agent 执行模式
type AgentExecutionMode =
  | 'in-process'      // 同一进程，AsyncLocalStorage
  | 'tmux-split'       // tmux 分屏
  | 'iterm2-split'     // iTerm2 分屏
  | 'worktree'         // 独立 git worktree
```

---

## 2. Agent 类型定义

### 2.1 核心类型

```typescript
// src/tools/AgentTool/builtInAgents.ts
export type BaseAgentDefinition = {
  // ========== 标识 ==========
  agentType: string
  description?: string
  whenToUse?: string

  // ========== 工具控制 ==========
  tools?: string[]                    // 工具白名单
  disallowedTools?: string[]         // 工具黑名单
  allowedTools?: string[]            // 允许的工具 (别名)

  // ========== 技能加载 ==========
  skills?: string[]                  // 预加载技能

  // ========== MCP 服务器 ==========
  mcpServers?: AgentMcpServerSpec[] // Agent 专用的 MCP 服务器

  // ========== 生命周期钩子 ==========
  hooks?: HooksSettings

  // ========== 模型控制 ==========
  model?: string
  maxTokens?: number
  thinkingEnabled?: boolean

  // ========== 权限控制 ==========
  permissionMode?: PermissionMode

  // ========== 执行控制 ==========
  maxTurns?: number                  // 最大轮次
  effort?: EffortValue
  background?: boolean               // 后台执行

  // ========== 上下文控制 ==========
  memory?: 'user' | 'project' | 'local'  // 记忆类型
  isolation?: 'worktree' | 'remote'       // 隔离模式

  // ========== CLAUDE.md ==========
  omitClaudeMd?: boolean             // 跳过 CLAUDE.md
}

// Agent 来源
type AgentSource =
  | 'built-in'           // 内置 (代码定义)
  | 'userSettings'       // 用户设置
  | 'projectSettings'    // 项目设置
  | 'policySettings'     // 策略控制
  | 'plugin'             // 插件提供
```

### 2.2 内置 Agent 定义

```typescript
// src/tools/AgentTool/builtInAgents.ts
export const BUILTIN_AGENTS: BaseAgentDefinition[] = [
  {
    agentType: 'GeneralPurpose',
    description: 'General purpose agent for any task',
    tools: ['Read', 'Edit', 'Write', 'Bash', 'Glob', 'Grep'],
    thinkingEnabled: true,
    maxTurns: 50,
  },

  {
    agentType: 'Explore',
    description: 'Explore and understand a codebase',
    tools: ['Read', 'Glob', 'Grep', 'Bash'],
    omitClaudeMd: true,  // 不读取项目 CLAUDE.md
    maxTurns: 30,
  },

  {
    agentType: 'Plan',
    description: 'Create a plan for implementing a feature or fix',
    tools: ['Read', 'Glob', 'Grep'],
    omitClaudeMd: true,
    maxTurns: 10,
  },

  {
    agentType: 'Verification',
    description: 'Verify changes and run tests',
    tools: ['Bash', 'Read'],
    maxTurns: 20,
  },

  {
    agentType: 'CodeReview',
    description: 'Review code changes',
    tools: ['Bash', 'Read', 'Glob', 'Grep'],
    allowedTools: ['Bash(git diff:*)', 'Bash(git log:*)'],
    maxTurns: 30,
  },
]
```

---

## 3. AgentTool 实现

### 3.1 Tool 定义

```typescript
// src/tools/AgentTool/AgentTool.tsx
export const AgentTool = buildTool({
  name: 'Agent',
  aliases: ['Task'],  // 向后兼容

  inputSchema: lazySchema(() =>
    z.strictObject({
      prompt: z.string().describe('Instructions for the agent'),
      agentType: z.string().optional().describe('Type of agent'),
      name: z.string().optional().describe('Name for the agent'),
      team: z.string().optional().describe('Team to join'),
      tools: z.array(z.string()).optional().describe('Allowed tools'),
      model: z.string().optional().describe('Model to use'),
      mcpServers: z.array(z.any()).optional(),
      maxTurns: z.number().optional(),
      background: z.boolean().optional().default(false),
      continueInSameContext: z.boolean().optional().default(false),
    })
  ),

  description: (input) =>
    input.background
      ? `Start background agent: ${input.prompt.slice(0, 50)}...`
      : `Run agent: ${input.prompt.slice(0, 50)}...`,

  userFacingName: () => 'Agent',

  maxResultSizeChars: 10000,

  // 权限检查
  checkPermissions: async (input, context) => {
    // AgentTool 需要较高的信任
    return { behavior: 'allow' }
  },

  call: async (input, context) => {
    const {
      prompt,
      agentType,
      name,
      team,
      tools,
      model,
      maxTurns,
      background,
      continueInSameContext,
    } = input

    // 1. 确定执行模式
    const executionMode = determineExecutionMode(
      context.config,
      background
    )

    // 2. 创建/加入团队
    const teamName = team ?? context.session?.teamName ?? 'default'

    if (name && team) {
      // 加入现有团队
      const result = await joinTeam({
        teamName,
        agentName: name,
        prompt,
        context,
      })
      return result
    }

    // 3. 派生新 Agent
    const result = await spawnAgent({
      prompt,
      agentType: agentType ?? 'GeneralPurpose',
      name,
      teamName,
      tools,
      model,
      maxTurns,
      background,
      executionMode,
      context,
    })

    return result
  },
})
```

### 3.2 参数处理

```typescript
// src/tools/AgentTool/AgentTool.tsx
function determineExecutionMode(
  config: AgentConfig,
  background: boolean
): AgentExecutionMode {
  // 1. 检查 tmux
  if (process.env.TERM_PROGRAM?.includes('tmux')) {
    return background ? 'tmux-split' : 'tmux-split'
  }

  // 2. 检查 iTerm2
  if (process.env.TERM_PROGRAM?.includes('iTerm')) {
    return background ? 'iterm2-split' : 'iterm2-split'
  }

  // 3. 检查 Claude Code 配置
  if (config.defaultAgentIsolation === 'worktree') {
    return 'worktree'
  }

  // 4. 默认进程内
  return 'in-process'
}
```

---

## 4. Agent 生命周期

### 4.1 runAgent 函数

```typescript
// src/tools/AgentTool/runAgent.ts
export async function* runAgent(
  options: RunAgentOptions
): AsyncGenerator<AgentMessage> {
  const {
    config,
    initialMessages,
    parentContext,
    onProgress,
  } = options

  // ========== 1. 初始化 ==========
  const agentId = generateAgentId()
  const startTime = Date.now()

  // 初始化文件状态缓存
  const readFileState = new FileStateCache()

  // 设置权限模式
  const permissionMode = config.permissionMode ?? 'auto'

  // 注册 Perfetto 追踪
  registerPerfettoTrace(agentId)

  // ========== 2. 构建上下文 ==========
  // Fork 消息 (过滤未完成的工具调用)
  const forkedMessages = filterMessagesForFork(initialMessages)

  // 解析系统/用户上下文
  const { systemPrompt, userContext } = await buildAgentContext(
    config,
    parentContext
  )

  // 应用 CLAUDE.md
  let effectiveSystemPrompt = systemPrompt
  if (!config.omitClaudeMd) {
    const claudeMd = await loadClaudeMd(parentContext.cwd)
    if (claudeMd) {
      effectiveSystemPrompt = [...systemPrompt, {
        role: 'system' as const,
        content: [{ type: 'text' as const, text: claudeMd }]
      }]
    }
  }

  // ========== 3. Hook 执行 ==========
  await executeHooks('PreAgentStart', config.hooks, {
    agentId,
    agentType: config.agentType,
  })

  // ========== 4. MCP 服务器设置 ==========
  let agentMcpClients: MCPClient[] = []

  if (config.mcpServers?.length) {
    agentMcpClients = await connectAgentMcpServers(
      config.mcpServers,
      parentContext
    )
  }

  try {
    // ========== 5. 执行查询循环 ==========
    for await (const event of queryAgent({
      messages: forkedMessages,
      systemPrompt: effectiveSystemPrompt,
      userContext,
      config,
      readFileState,
      mcpClients: agentMcpClients,
      parentContext,
    })) {
      yield event
    }
  } finally {
    // ========== 6. 清理 ==========
    // 断开 MCP 服务器
    for (const client of agentMcpClients) {
      await client.disconnect()
    }

    // 清理 Session Hooks
    cleanupSessionHooks(agentId)

    // 释放文件状态缓存
    readFileState.release()

    // Perfetto 注销
    unregisterPerfettoTrace(agentId)

    // 清理 Todo
    cleanupAgentTodos(agentId)

    // 清理 Bash 任务
    cleanupBashTasks(agentId)

    // 执行 PostAgentEnd Hook
    await executeHooks('PostAgentEnd', config.hooks, {
      agentId,
      agentType: config.agentType,
      duration: Date.now() - startTime,
    })
  }
}
```

### 4.2 查询循环

```typescript
// src/tools/AgentTool/runAgent.ts
async function* queryAgent(
  options: QueryAgentOptions
): AsyncGenerator<AgentMessage> {
  const {
    messages,
    systemPrompt,
    config,
    readFileState,
    mcpClients,
    parentContext,
  } = options

  let currentMessages = messages
  let turnCount = 0

  while (turnCount < (config.maxTurns ?? Infinity)) {
    // 调用模型
    const response = await callModelWithStreaming({
      model: config.model,
      messages: currentMessages,
      system: systemPrompt,
      tools: buildToolsForAgent(config, mcpClients),
      maxTokens: config.maxTokens,
    })

    // 处理流式响应
    for await (const event of response.stream) {
      yield { type: 'stream', event, agentId: options.agentId }

      // 处理工具调用
      if (event.type === 'content_block' &&
          event.content.type === 'tool_use') {
        const result = await executeTool(
          event.content,
          currentMessages,
          options
        )

        // 添加工具结果到消息
        currentMessages.push({
          role: 'user',
          content: [{
            type: 'tool_result',
            tool_use_id: event.content.id,
            content: result.content,
          }]
        })
      }
    }

    turnCount++

    // 检查停止条件
    if (response.stopReason === 'end_turn') {
      break
    }
  }
}
```

---

## 5. Agent 间通信

### 5.1 SendMessageTool

```typescript
// src/tools/SendMessageTool/SendMessageTool.ts
export const SendMessageTool = buildTool({
  name: 'SendMessage',
  aliases: ['Message', 'Tell', 'Ask'],

  inputSchema: lazySchema(() =>
    z.strictObject({
      to: z.string().describe('Recipient agent name (or "*" for broadcast)'),
      message: z.string().describe('Message content'),
      type: z.enum(['message', 'shutdown_request', 'shutdown_response', 'plan_approval_response']).optional(),
    })
  ),

  call: async (input, context) => {
    const { to, message, type = 'message' } = input

    // 获取团队上下文
    const team = context.session?.team
    if (!team) {
      throw new Error('Not in a team context')
    }

    // 构建消息
    const teammateMessage: TeammateMessage = {
      id: generateMessageId(),
      from: context.session?.agentName ?? 'leader',
      to,
      type,
      content: message,
      timestamp: Date.now(),
    }

    // 发送消息
    if (to === '*') {
      // 广播
      await broadcastMessage(team, teammateMessage)
    } else {
      // 直接发送
      await sendDirectMessage(team, to, teammateMessage)
    }

    return {
      content: [{
        type: 'tool_result',
        tool_use_id: '',
        content: `Message ${type} sent to ${to}`
      }]
    }
  },
})
```

### 5.2 消息传递机制

```typescript
// src/tools/AgentTool/shared/teammateMessaging.ts

// 消息目标类型
type MessageTarget =
  | { type: 'direct'; name: string }      // 直接发给某个 agent
  | { type: 'broadcast'; to: '*' }         // 广播给所有成员
  | { type: 'team'; teamName: string }     // 发给整个团队

// 消息传递策略
async function deliverMessage(
  target: MessageTarget,
  message: TeammateMessage,
  context: AgentContext
): Promise<void> {
  switch (target.type) {
    case 'direct':
      await deliverToAgent(target.name, message, context)
      break

    case 'broadcast':
      await broadcastToTeam(message, context)
      break

    case 'team':
      await sendToTeam(target.teamName, message, context)
      break
  }
}

// 进程内传递 (AsyncLocalStorage)
async function deliverToAgent(
  agentName: string,
  message: TeammateMessage,
  context: AgentContext
): Promise<void> {
  // 查找目标 agent
  const agent = context.team?.agents.get(agentName)

  if (!agent) {
    throw new Error(`Agent not found: ${agentName}`)
  }

  if (agent.type === 'in-process') {
    // 进程内 agent，通过队列直接传递
    agent.messageQueue.push(message)

    // 触发 agent 继续执行
    agent.continue()
  } else if (agent.type === 'tmux' || agent.type === 'iterm2') {
    // 终端分屏 agent，通过 mailbox 文件传递
    await writeMailbox(agent.mailboxPath, message)
  } else if (agent.type === 'background') {
    // 后台 agent，如果已停止则恢复
    if (agent.status === 'stopped') {
      await resumeAgentBackground(agent)
    }
    await writeMailbox(agent.mailboxPath, message)
  }
}
```

### 5.3 Mailbox 系统

```typescript
// 邮箱文件路径
const MAILBOX_PATH = (
  teamName: string,
  agentName: string
): string => `~/.claude/teams/${teamName}/mailbox/${agentName}/`

interface MailboxMessage {
  id: string
  from: string
  content: string
  timestamp: number
  type: 'message' | 'shutdown_request' | 'shutdown_response'
}

// 写入邮箱
async function writeMailbox(
  path: string,
  message: MailboxMessage
): Promise<void> {
  const file = pathJoin(path, `${message.id}.json`)
  await fs.writeFile(file, JSON.stringify(message, null, 2))
}

// 读取邮箱
async function readMailbox(
  path: string
): Promise<MailboxMessage[]> {
  const files = await fs.readdir(path)
  const messages: MailboxMessage[] = []

  for (const file of files) {
    if (file.endsWith('.json')) {
      const content = await fs.readFile(pathJoin(path, file), 'utf-8')
      messages.push(JSON.parse(content))
    }
  }

  return messages.sort((a, b) => a.timestamp - b.timestamp)
}

// 清理已读消息
async function cleanupMailbox(
  path: string,
  processedIds: Set<string>
): Promise<void> {
  const files = await fs.readdir(path)

  for (const file of files) {
    const id = file.replace('.json', '')
    if (processedIds.has(id)) {
      await fs.unlink(pathJoin(path, file))
    }
  }
}
```

---

## 6. 团队管理

### 6.1 团队结构

```typescript
// src/tools/AgentTool/shared/team.ts
export interface Team {
  name: string
  leaderId: string
  agents: Map<string, AgentHandle>
  createdAt: number
  mailboxDir: string
}

export interface AgentHandle {
  agentId: string
  name: string
  type: 'leader' | 'member'
  status: 'running' | 'stopped' | 'failed'
  executionMode: AgentExecutionMode

  // 消息队列 (进程内)
  messageQueue: TeammateMessage[]
  continue?: () => void

  // Mailbox 路径 (tmux/iterm2)
  mailboxPath?: string

  // 进程引用 (外部执行)
  process?: ChildProcess
  stdin?: Writable
}
```

### 6.2 团队创建

```typescript
// src/tools/AgentTool/shared/team.ts
export async function createTeam(
  options: CreateTeamOptions
): Promise<Team> {
  const team: Team = {
    name: options.name,
    leaderId: options.leaderId,
    agents: new Map(),
    createdAt: Date.now(),
    mailboxDir: pathJoin(
      os.homedir(),
      '.claude',
      'teams',
      options.name,
      'mailbox'
    ),
  }

  // 创建 mailbox 目录
  await fs.mkdir(team.mailboxDir, { recursive: true })

  // 注册团队
  await registerTeam(team)

  return team
}

// 添加 Agent 到团队
export async function addAgentToTeam(
  team: Team,
  agent: AgentHandle
): Promise<void> {
  team.agents.set(agent.name, agent)

  // 为新 agent 创建 mailbox 子目录
  const agentMailboxDir = pathJoin(team.mailboxDir, agent.name)
  await fs.mkdir(agentMailboxDir, { recursive: true })

  if (agent.mailboxPath) {
    agent.mailboxPath = agentMailboxDir
  }

  // 更新团队注册
  await updateTeamRegistration(team)
}
```

---

## 7. 子 Agent 派生

### 7.1 spawnAgent 函数

```typescript
// src/tools/AgentTool/shared/spawnMultiAgent.ts
export async function spawnAgent(
  options: SpawnAgentOptions
): Promise<SpawnResult> {
  const {
    prompt,
    agentType,
    name,
    teamName,
    tools,
    model,
    maxTurns,
    background,
    executionMode,
    context,
  } = options

  // 1. 生成唯一标识
  const agentId = generateAgentId()
  const agentName = name ?? generateAgentName(agentType)

  // 2. 确定执行模式
  switch (executionMode) {
    case 'in-process':
      return spawnInProcess(agentId, agentName, options)

    case 'tmux-split':
      return spawnTmuxPane(agentId, agentName, options)

    case 'iterm2-split':
      return spawnITerm2Pane(agentId, agentName, options)

    case 'worktree':
      return spawnWorktree(agentId, agentName, options)
  }
}
```

### 7.2 进程内派生

```typescript
// src/tools/AgentTool/shared/spawnMultiAgent.ts
async function spawnInProcess(
  agentId: string,
  agentName: string,
  options: SpawnAgentOptions
): Promise<SpawnResult> {
  // 使用 AsyncLocalStorage 隔离上下文
  const storage = new AsyncLocalStorage<AgentContext>()

  // 创建 agent handle
  const handle: AgentHandle = {
    agentId,
    name: agentName,
    type: 'member',
    status: 'running',
    executionMode: 'in-process',
    messageQueue: [],
    continue: () => {
      // 触发队列处理
      processAgentQueue(handle)
    },
  }

  // 添加到团队
  await addAgentToTeam(options.team, handle)

  // 在异步上下文中运行 agent
  const agentPromise = storage.run(
    { agentId, agentName, team: options.team, ...options },
    async () => {
      // 运行 agent
      for await (const event of runAgent(options)) {
        // 处理事件
        handleAgentEvent(event, handle)
      }

      handle.status = 'stopped'
    }
  )

  return {
    agentId,
    agentName,
    status: 'running',
    join: () => agentPromise,
  }
}
```

### 7.3 Tmux 分屏派生

```typescript
// src/tools/AgentTool/shared/spawnMultiAgent.ts
async function spawnTmuxPane(
  agentId: string,
  agentName: string,
  options: SpawnAgentOptions
): Promise<SpawnResult> {
  // 1. 创建 tmux pane
  await execAsync('tmux', [
    'split-window',
    '-h',  // 水平分割
    '-t', `${options.teamName}:0`,  // 目标窗口
    '-P',  // 输出 pane ID
  ])

  // 2. 获取 pane ID
  const paneId = await getTmuxPaneId(options.teamName)

  // 3. 构建 CLI 命令
  const agentArgs = buildAgentCLIArgs({
    ...options,
    agentId,
    agentName,
  })

  // 4. 在 pane 中启动 Claude Code
  await execAsync('tmux', [
    'send-keys',
    '-t', paneId,
    `claude --agent-id ${agentId} ${agentArgs.join(' ')}`,
    'Enter'
  ])

  // 5. 创建 mailbox 路径
  const mailboxPath = pathJoin(
    os.homedir(),
    '.claude',
    'teams',
    options.teamName,
    'mailbox',
    agentName
  )

  const handle: AgentHandle = {
    agentId,
    name: agentName,
    type: 'member',
    status: 'running',
    executionMode: 'tmux-split',
    mailboxPath,
  }

  return {
    agentId,
    agentName,
    status: 'running',
    paneId,
  }
}
```

### 7.4 Worktree 派生

```typescript
// src/tools/AgentTool/shared/spawnMultiAgent.ts
async function spawnWorktree(
  agentId: string,
  agentName: string,
  options: SpawnAgentOptions
): Promise<SpawnResult> {
  // 1. 创建独立的 git worktree
  const worktreePath = pathJoin(
    options.context.cwd,
    '.claude',
    'worktrees',
    agentId
  )

  await execAsync('git', [
    'worktree',
    'add',
    '-b', `agent-${agentId}`,
    worktreePath,
  ])

  // 2. 构建 CLI 命令
  const agentArgs = buildAgentCLIArgs({
    ...options,
    agentId,
    agentName,
    cwd: worktreePath,  // 使用 worktree 目录
  })

  // 3. 派生子进程
  const child = spawn('claude', agentArgs, {
    cwd: worktreePath,
    stdio: ['pipe', 'pipe', 'pipe'],
  })

  const handle: AgentHandle = {
    agentId,
    name: agentName,
    type: 'member',
    status: 'running',
    executionMode: 'worktree',
    process: child,
    stdin: child.stdin,
  }

  // 4. 监听输出
  child.stdout?.on('data', (data) => {
    handleAgentOutput(data.toString(), handle)
  })

  return {
    agentId,
    agentName,
    status: 'running',
    worktreePath,
    cleanup: async () => {
      // 清理 worktree
      await execAsync('git', ['worktree', 'remove', worktreePath, '--force'])
    },
  }
}
```

---

## 8. 协调器模式

### 8.1 协调器概述

```typescript
// src/coordinator/coordinatorMode.ts
/**
 * 协调器模式
 *
 * 协调器是一个特殊的 leader agent，负责：
 * 1. 分解复杂任务为子任务
 * 2. 派生子 worker agent 并行执行
 * 3. 收集和综合 worker 结果
 * 4. 处理 worker 间的通信
 */

// 协调器配置
const coordinatorConfig: BaseAgentDefinition = {
  agentType: 'Coordinator',
  description: 'Coordinates multiple workers to complete complex tasks',

  // 协调器工具
  tools: ['Agent', 'SendMessage', 'Read', 'Glob'],

  // 禁止某些工具 (协调器不直接执行)
  disallowedTools: ['Bash', 'Edit', 'Write'],

  // 协调器需要特殊权限
  permissionMode: 'auto',

  // 后台执行所有 worker
  hooks: {
    PreAgentStart: [{
      skill: 'worker-spawn',
      config: { background: true }
    }]
  }
}
```

### 8.2 Worker 结果聚合

```typescript
// src/coordinator/coordinatorMode.ts
/**
 * Worker 结果通过 task-notification 消息接收
 *
 * 格式:
 * <task-notification>
 * <task-id>worker-1</task-id>
 * <status>completed</status>
 * <summary>Research completed</summary>
 * <result>Detailed results...</result>
 * <usage>
 *   <total_tokens>5000</total_tokens>
 *   <tool_uses>15</tool_uses>
 *   <duration_ms>30000</duration_ms>
 * </usage>
 * </task-notification>
 */

function parseTaskNotification(xml: string): TaskNotification {
  // 解析 XML 格式的结果
  const match = xml.match(/<task-id>(.*?)<\/task-id>/)
  const taskId = match?.[1] ?? ''

  const status = xml.includes('<status>completed</status>')
    ? 'completed'
    : 'failed'

  const summary = extractXMLContent(xml, 'summary')
  const result = extractXMLContent(xml, 'result')

  return { taskId, status, summary, result }
}

// 协调器综合结果
async function synthesizeResults(
  notifications: TaskNotification[]
): Promise<string> {
  const completed = notifications.filter(n => n.status === 'completed')
  const failed = notifications.filter(n => n.status === 'failed')

  let summary = `# Task Completion Report\n\n`
  summary += `## Completed (${completed.length})\n`

  for (const n of completed) {
    summary += `### ${n.taskId}\n`
    summary += `${n.summary}\n\n`
  }

  if (failed.length > 0) {
    summary += `## Failed (${failed.length})\n`
    for (const n of failed) {
      summary += `- ${n.taskId}: ${n.result}\n`
    }
  }

  return summary
}
```

---

## 9. 设计模式总结

### 9.1 模式列表

| 模式 | 应用 | 优势 |
|------|------|------|
| **AsyncLocalStorage** | 进程内 agent 隔离 | 零拷贝上下文传递 |
| **Actor 模型** | Agent 通信 | 松耦合 |
| **Mailbox** | 外部 agent 通信 | 持久化、跨进程 |
| **工作池** | 团队管理 | 资源控制 |
| **生成器模式** | Agent 事件流 | 流式输出 |
| **隔离执行** | Worktree/Tmux | 环境隔离 |

### 9.2 隔离级别

```typescript
// 隔离级别对比
const ISOLATION_LEVELS = {
  // Level 0: 共享一切
  'none': {
    context: 'shared',
    state: 'shared',
    filesystem: 'shared',
  },

  // Level 1: AsyncLocalStorage 隔离
  'in-process': {
    context: 'isolated',
    state: 'isolated',
    filesystem: 'shared',
  },

  // Level 2: Tmux 分屏
  'tmux-split': {
    context: 'isolated',
    state: 'isolated',
    filesystem: 'shared',
    terminal: 'split',
  },

  // Level 3: Git Worktree
  'worktree': {
    context: 'isolated',
    state: 'isolated',
    filesystem: 'isolated',
    terminal: 'separate',
  },
}
```

---

## 10. 错误处理

### 10.1 Agent 错误类型

```typescript
// src/tools/AgentTool/shared/errors.ts
export class AgentError extends Error {
  constructor(
    message: string,
    public agentId: string,
    public code: AgentErrorCode
  ) {
    super(message)
    this.name = 'AgentError'
  }
}

export enum AgentErrorCode {
  AGENT_NOT_FOUND = 'AGENT_NOT_FOUND',
  AGENT_TIMEOUT = 'AGENT_TIMEOUT',
  AGENT_CRASHED = 'AGENT_CRASHED',
  TEAM_NOT_FOUND = 'TEAM_NOT_FOUND',
  MESSAGE_DELIVERY_FAILED = 'MESSAGE_DELIVERY_FAILED',
  MCP_CONNECTION_FAILED = 'MCP_CONNECTION_FAILED',
  PERMISSION_DENIED = 'PERMISSION_DENIED',
}
```

### 10.2 错误恢复

```typescript
// Agent 错误恢复策略
const AGENT_RECOVERY_STRATEGIES: Record<
  AgentErrorCode,
  (error: AgentError) => Promise<RecoveryAction>
> = {
  [AgentErrorCode.AGENT_TIMEOUT]: async (error) => {
    // 重试最多 3 次
    if (error.agentId && (error.retryCount ?? 0) < 3) {
      return { action: 'retry', agentId: error.agentId }
    }
    return { action: 'fail', reason: 'max retries exceeded' }
  },

  [AgentErrorCode.AGENT_CRASHED]: async (error) => {
    // 尝试恢复状态
    const checkpoint = await loadAgentCheckpoint(error.agentId)
    if (checkpoint) {
      return { action: 'restore', checkpoint }
    }
    return { action: 'fail', reason: 'no checkpoint available' }
  },

  [AgentErrorCode.MESSAGE_DELIVERY_FAILED]: async (error) => {
    // 重新发送消息
    return { action: 'retry', message: error.message }
  },
}
```

---

*文档版本: 2026-03-31*
