# 查询引擎设计文档

> 本文档详细解析 Claude Code 查询引擎的架构设计、数据流、上下文管理和容错机制。

---

## 1. 设计概述

### 1.1 核心职责

查询引擎是 Claude Code 的**核心编排层**，负责：

- 管理对话状态和消息历史
- 构建和发送 API 请求
- 处理流式响应
- 编排工具执行
- 管理上下文大小
- 处理错误和重试

### 1.2 组件架构

```
┌─────────────────────────────────────────────────────────────────┐
│  QueryEngine (src/QueryEngine.ts)                                │
│  - 会话状态管理 (~46KB)                                          │
│  - SDK 消息格式                                                  │
│  - 工具调用循环                                                  │
│  - 预算执行 (USD, token limits)                                   │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  query.ts (AsyncGenerator ~68KB)                                 │
│  - 核心查询循环                                                  │
│  - API 调用 (callModel)                                          │
│  - 流式响应处理                                                  │
│  - 上下文压缩                                                    │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  toolOrchestration.ts                                            │
│  - 工具并发控制                                                  │
│  - 权限检查                                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. QueryEngine 类

### 2.1 核心状态

```typescript
// src/QueryEngine.ts:184-198
class QueryEngine {
  // 配置
  private config: QueryEngineConfig

  // 消息历史
  private mutableMessages: Message[]

  // 中止控制
  private abortController: AbortController

  // 权限追踪
  private permissionDenials: SDKPermissionDenial[]

  // Token 使用统计
  private totalUsage: NonNullableUsage

  // 文件状态缓存
  private readFileState: FileStateCache

  // 发现的技能
  private discoveredSkillNames = new Set<string>()

  // 已加载的嵌套内存路径
  private loadedNestedMemoryPaths = new Set<string>()

  // 孤儿权限处理
  private hasHandledOrphanedPermission = false
}
```

### 2.2 submitMessage 入口

```typescript
// src/QueryEngine.ts:209-1156
async function* submitMessage(
  prompt: string,
  options: MessageOptions
): AsyncGenerator<SDKMessage> {
  // 1. 初始化
  this.discoveredSkillNames.clear()
  this.abortController = new AbortController()

  // 2. 设置工作目录
  setCurrentWorkingDirectory(options.cwd)

  // 3. 包装 canUseTool 追踪权限拒绝
  const canUseTool = wrapCanUseToolForTracking(
    options.canUseTool,
    (denial) => this.permissionDenials.push(denial)
  )

  // 4. 构建系统提示词
  const {
    defaultSystemPrompt,
    userContext: baseUserContext,
    systemContext,
  } = await fetchSystemPromptParts({
    settings: options.settings,
    // ...
  })

  // 5. 加载内存提示词
  const memoryMechanicsPrompt = customPrompt !== undefined
    ? await loadMemoryPrompt()
    : null

  // 6. 合并系统提示词
  const systemPrompt = asSystemPrompt([
    ...(customPrompt !== undefined ? [customPrompt] : defaultSystemPrompt),
    ...(memoryMechanicsPrompt ? [memoryMechanicsPrompt] : []),
    ...(appendSystemPrompt ? [appendSystemPrompt] : []),
  ])

  // 7. 处理用户输入
  const {
    messages,
    shouldQuery,
    allowedTools,
    model,
    resultText,
  } = await processUserInput(
    prompt,
    options,
    canUseTool,
    // ...
  )

  // 8. 非查询路径 (本地命令等)
  if (!shouldQuery) {
    yield { type: 'user_message_replay', content: messages }
    yield { type: 'compact_boundary' }
    yield {
      type: 'result',
      subtype: 'success',
      content: [{ type: 'text', text: resultText ?? '' }]
    }
    return
  }

  // 9. 记录消息 (会话持久化)
  await this.recordMessages(messages)

  // 10. 查询循环
  yield* this.queryLoop(
    messages,
    systemPrompt,
    baseUserContext,
    options,
    model,
    allowedTools
  )
}
```

### 2.3 查询循环

```typescript
// src/QueryEngine.ts:675-1049
private async* queryLoop(
  messages: Message[],
  systemPrompt: ContentBlockParam[],
  baseUserContext: ContentBlockParam[],
  options: MessageOptions,
  model: string,
  allowedTools: Tool[]
): AsyncGenerator<SDKMessage> {
  // 调用核心 query 生成器
  for await (const message of query(
    messages,
    {
      config: this.config,
      systemPrompt,
      baseUserContext,
      tools: allowedTools,
      model,
      abortSignal: this.abortController.signal,
      // ...
    }
  )) {
    // 处理流式消息
    switch (message.event.type) {
      case 'tombstone':
        // 控制信号 (消息移除)
        yield message
        break

      case 'assistant':
        // 捕获 stop_reason
        this.lastStopReason = message.event.message.stop_reason
        // 追加到消息历史
        this.mutableMessages.push(message.event.message)
        yield message
        break

      case 'progress':
        // 内联进度记录
        yield message
        break

      case 'user':
        // 用户消息
        yield message
        break

      case 'stream_event':
        // API 事件 (usage, etc.)
        this.accumulateUsage(message.event)
        yield message
        break

      case 'attachment':
        // 附件处理
        yield message
        break

      case 'system':
        // 系统消息
        if (message.event.subtype === 'compact_boundary') {
          yield message
        }
        break
    }
  }

  // 预算执行检查
  this.checkBudgetEnforcement()
}
```

---

## 3. query.ts 核心管道

### 3.1 状态类型

```typescript
// src/query.ts:201-217
type State = {
  messages: Message[]

  toolUseContext: ToolUseContext

  // 自动压缩追踪
  autoCompactTracking: AutoCompactTrackingState | undefined

  // Output tokens 恢复计数
  maxOutputTokensRecoveryCount: number

  // 是否尝试过响应式压缩
  hasAttemptedReactiveCompact: boolean

  // Output tokens 覆盖
  maxOutputTokensOverride: number | undefined

  // 待处理的工具使用摘要
  pendingToolUseSummary: Promise<ToolUseSummaryMessage | null> | undefined

  // Stop hook 是否激活
  stopHookActive: boolean | undefined

  // 轮次计数
  turnCount: number

  // 继续原因
  transition: Continue | undefined
}
```

### 3.2 核心生成器

```typescript
// src/query.ts:250-500
async function* query(
  initialMessages: Message[],
  options: QueryOptions
): AsyncGenerator<QueryEvent> {
  // 初始化状态
  const state: State = {
    messages: initialMessages,
    toolUseContext: createToolUseContext(options),
    // ...
  }

  // 预循环设置
  await preLoopSetup(state, options)

  // 主循环
  while (true) {
    // 1. 上下文压缩管道
    await runCompactPipeline(state, options)

    // 2. API 调用
    const result = await callModelWithStreaming(state, options)

    // 3. 处理流式响应
    for await (const msg of result.stream) {
      // 处理消息...
      yield msg

      // 检查是否需要继续循环
      if (shouldContinue(msg, state)) {
        state.turnCount++
        state.messages = updateMessages(state.messages, msg)
        continue  // 继续下一轮
      }
    }

    // 4. 停止钩子
    await handleStopHooks(state, options)

    // 5. 退出循环
    break
  }
}
```

### 3.3 预循环设置

```typescript
// src/query.ts:301-368
async function preLoopSetup(state: State, options: QueryOptions): Promise<void> {
  // 1. 内存预取 (非阻塞)
  startMemoryPrefetch(options)

  // 2. 链式追踪初始化
  options.queryTracking = {
    chainId: options.chainId ?? generateChainId(),
    depth: options.depth ?? 0,
  }

  // 3. 应用历史裁剪
  if (feature('HISTORY_SNIP')) {
    state.messages = snipMessagesIfNeeded(state.messages, options)
  }

  // 4. 应用微压缩
  if (feature('MICROCOMPACT')) {
    await runMicroCompact(state, options)
  }

  // 5. 应用上下文折叠
  if (feature('CONTEXT_COLLAPSE')) {
    state.messages = applyCollapsesIfNeeded(state.messages, options)
  }

  // 6. 检查阻塞限制
  checkBlockingLimits(state, options)
}
```

---

## 4. 上下文压缩管道

### 4.1 压缩层级

```
┌─────────────────────────────────────────────────────────────────┐
│  Level 0: snipCompactIfNeeded (HISTORY_SNIP)                    │
│  - 裁剪过长的历史消息                                            │
│  - 基于 token 计数触发                                           │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Level 1: microcompact                                           │
│  - 轻量级每轮压缩                                                │
│  - 清除旧工具结果内容 (保留缓存编辑 ID)                          │
│  - 触发: 计数阈值或时间阈值                                      │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Level 2: applyCollapsesIfNeeded (CONTEXT_COLLAPSE)             │
│  - 折叠连续消息组                                                │
│  - 保留首尾消息                                                  │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Level 3: autocompact (turn-level summarization)                  │
│  - 完整对话压缩                                                  │
│  - 通过额外 API 调用生成摘要                                      │
│  - 替换原始消息                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Microcompact

```typescript
// src/services/compact/microCompact.ts
/**
 * 轻量级每轮压缩
 * 目标: 减少上下文大小而不丢失关键信息
 */
async function microcompact(
  messages: Message[],
  context: ToolUseContext
): Promise<Message[]> {
  const result: Message[] = []

  for (const msg of messages) {
    if (msg.role === 'user') {
      // 用户消息保留
      result.push(msg)
      continue
    }

    if (msg.role === 'assistant') {
      // 检查工具使用
      const toolUses = extractToolUses(msg)

      for (const toolUse of toolUses) {
        // 只压缩特定工具的结果
        if (isCompactableTool(toolUse.name)) {
          // 替换为标记
          msg.content = markToolResultsAsCleared(
            msg.content,
            toolUse.id,
            '[Old tool result content cleared]'
          )
        }
      }

      result.push(msg)
      continue
    }

    // 其他消息保留
    result.push(msg)
  }

  return result
}

// 可压缩的工具
const COMPACTABLE_TOOLS = new Set([
  'Read',
  'Bash',
  'Grep',
  'Glob',
  'WebSearch',
  'WebFetch',
  'FileEdit',
  'FileWrite',
])
```

### 4.3 Autocompact (完整压缩)

```typescript
// src/services/compact/compact.ts
/**
 * 完整对话压缩
 * 通过模型生成摘要替换原始消息
 */
async function autocompact(
  messages: Message[],
  options: CompactOptions
): Promise<CompactResult> {
  // 1. 执行 PreCompact hooks
  await executeHooks(options.hooks?.PreCompact)

  // 2. 准备压缩提示词
  const compactPrompt = buildCompactPrompt(messages)

  // 3. 剥离图片 (不需要用于摘要)
  const messagesWithoutImages = stripImages(messages)

  // 4. 调用模型生成摘要
  const summaryStream = await callModel({
    messages: messagesWithoutImages,
    systemPrompt: [compactPrompt],
    model: options.model ?? 'haiku',
    // 使用较小模型节省成本
  })

  // 5. 流式收集摘要
  let summary = ''
  for await (const event of summaryStream) {
    if (event.type === 'content_block') {
      summary += event.content.text
    }
  }

  // 6. 创建压缩边界标记
  const compactBoundary: Message = {
    role: 'system',
    content: [{
      type: 'text',
      text: `[Previous conversation summarized. Summary: ${summary}]`
    }]
  }

  // 7. 生成后压缩附件
  const attachments = await generatePostCompactAttachments(options)

  // 8. 执行 PostCompact hooks
  await executeHooks(options.hooks?.PostCompact)

  // 9. 记录压缩事件
  await logCompactEvent({
    originalMessageCount: messages.length,
    summaryTokenCount: estimateTokens(summary),
    // ...
  })

  return {
    boundary: compactBoundary,
    attachments,
    summary,
  }
}
```

---

## 5. API 调用与流式处理

### 5.1 callModel 函数

```typescript
// src/query.ts:659-708
async function callModelWithStreaming(
  state: State,
  options: QueryOptions
): Promise<ModelResult> {
  // 1. 准备请求
  const request: ModelRequest = {
    model: options.model ?? getDefaultModel(),
    messages: buildRequestMessages(state, options),

    // System prompt
    system: options.systemPrompt,

    // Tools
    tools: buildToolsForRequest(state.toolUseContext),

    // Streaming
    stream: true,

    // MCP tools
    mcpTools: getMcpTools(options.appState),

    // 预算追踪
    taskBudget: {
      remaining: options.taskBudget?.remaining ?? getDefaultBudget(),
    },
  }

  // 2. 执行请求
  try {
    return await apiClient.queryModelWithStreaming(request, {
      signal: options.abortSignal,
    })
  } catch (error) {
    // 3. 处理错误
    if (error instanceof FallbackTriggeredError) {
      // 模型回退
      return handleModelFallback(state, error, options)
    }

    if (error instanceof PromptTooLongError) {
      // 上下文太长
      return handlePromptTooLong(state, error, options)
    }

    throw error
  }
}
```

### 5.2 流式响应处理

```typescript
// src/query.ts:747-862
async function* handleStreamingResponse(
  stream: AsyncGenerator<StreamEvent>,
  state: State,
  options: QueryOptions
): AsyncGenerator<QueryEvent> {
  let currentMessageUsage = EMPTY_USAGE

  for await (const message of stream) {
    switch (message.event.type) {
      case 'message_start':
        // 重置 usage 计数
        currentMessageUsage = EMPTY_USAGE
        currentMessageUsage = updateUsage(
          currentMessageUsage,
          message.event.message.usage
        )
        break

      case 'content_block':
        // 内容块
        if (message.event.content.type === 'text') {
          yield { type: 'assistant', content: message.event.content }
        } else if (message.event.content.type === 'tool_use') {
          // 工具使用
          yield { type: 'assistant', content: message.event.content }
        }
        break

      case 'message_delta':
        // 更新 usage
        currentMessageUsage = updateUsage(
          currentMessageUsage,
          message.event.usage
        )
        // 捕获 stop_reason
        if (message.event.delta.stop_reason) {
          state.lastStopReason = message.event.delta.stop_reason
        }
        break

      case 'message_stop':
        // 累计 usage
        state.totalUsage = accumulateUsage(
          state.totalUsage,
          currentMessageUsage
        )
        break
    }
  }
}
```

### 5.3 工具输入回填

```typescript
// src/query.ts:748-786
/**
 * 工具输入回填 (Tool Input Backfill)
 *
 * 问题: 工具输入通过 tool_use 块发送，但某些信息只存在于
 *       上下文中 (如引用的文件内容)。这些需要回填到 tool_use 中。
 *
 * 解决: 克隆 assistant 消息，添加可观察的输入字段
 */
function backfillToolInput(
  assistantMessage: AssistantMessage,
  toolUseContext: ToolUseContext
): AssistantMessage {
  // 只在回填添加字段时克隆
  let needsClone = false
  const newContent: ContentBlock[] = []

  for (const block of assistantMessage.content) {
    if (block.type === 'tool_use') {
      const tool = findToolByName(toolUseContext.options.tools, block.name)
      const input = block.input

      // 检查是否需要回填
      const backfill = tool?.backfillObservableInput?.(input)
      if (backfill) {
        needsClone = true
        newContent.push({
          ...block,
          input: { ...input, ...backfill }
        })
      } else {
        newContent.push(block)
      }
    } else {
      newContent.push(block)
    }
  }

  // 如果没有修改，返回原始消息
  if (!needsClone) {
    return assistantMessage
  }

  // 返回克隆的消息 (保留原始用于 API 重新提交)
  return {
    ...assistantMessage,
    content: newContent,
    // 原始消息保留在别处用于重新提交
  }
}
```

---

## 6. 工具执行集成

### 6.1 两种执行路径

```typescript
// src/query.ts:1362-1421
async function executeTools(
  toolUseBlocks: ToolUseBlock[],
  assistantMessages: AssistantMessage[],
  state: State,
  options: QueryOptions
): AsyncGenerator<QueryEvent> {
  // 选择执行路径
  const useStreaming = feature('STREAMING_TOOL_EXECUTION')

  if (useStreaming) {
    // 流式工具执行
    const streamingExecutor = new StreamingToolExecutor(
      toolUseBlocks,
      state.toolUseContext,
      options.canUseTool
    )

    // 添加工具到执行器
    for (const block of toolUseBlocks) {
      streamingExecutor.addTool(block, assistantMessages)
    }

    // 流式产生结果
    for await (const result of streamingExecutor.getResults()) {
      if (result.message) {
        yield result.message
      }
      if (result.newContext) {
        state.toolUseContext = {
          ...state.toolUseContext,
          ...result.newContext,
          queryTracking: options.queryTracking,
        }
      }
    }
  } else {
    // 批量工具执行
    for await (const update of runTools(
      toolUseBlocks,
      assistantMessages,
      options.canUseTool,
      state.toolUseContext
    )) {
      if (update.message) {
        yield update.message
      }
      if (update.newContext) {
        state.toolUseContext = {
          ...state.toolContext,
          ...update.newContext,
          queryTracking: options.queryTracking,
        }
      }
    }
  }
}
```

### 6.2 工具使用摘要

```typescript
// src/query.ts:1411-1482
/**
 * 工具使用摘要 (Tool Use Summary)
 *
 * 使用 Haiku 模型为工具使用生成简短摘要，
 * 帮助用户快速了解工具执行结果
 */
async function generateToolUseSummary(
  toolUseBlocks: ToolUseBlock[],
  results: ToolResult[],
  context: ToolUseContext
): Promise<ToolUseSummaryMessage | null> {
  // 检查特性开关
  if (!feature('TOOL_USE_SUMMARY')) {
    return null
  }

  // 使用 Haiku 模型
  const summaryModel = 'haiku'

  // 构建摘要提示
  const summaryPrompt = buildSummaryPrompt(toolUseBlocks, results)

  try {
    // 异步生成摘要 (不阻塞主流程)
    const summary = await callModel({
      model: summaryModel,
      messages: [{ role: 'user', content: summaryPrompt }],
      maxTokens: 100,
    })

    return {
      type: 'tool_use_summary',
      summary,
      toolIds: toolUseBlocks.map(b => b.id),
    }
  } catch (error) {
    // 摘要失败不阻塞主流程
    return null
  }
}
```

---

## 7. 错误处理与重试

### 7.1 模型回退

```typescript
// src/query.ts:894-951
async function handleModelFallback(
  state: State,
  error: FallbackTriggeredError,
  options: QueryOptions
): Promise<ModelResult> {
  const fallbackModel = options.fallbackModel

  if (!fallbackModel) {
    throw error  // 没有回退模型
  }

  // 清除消息签名 (模型不同签名不同)
  state.messages = stripSignatures(state.messages)

  // 发出警告
  yield {
    type: 'system',
    subtype: 'model_fallback',
    model: fallbackModel,
    reason: error.message,
  }

  // 使用回退模型重试
  options.model = fallbackModel
  options.fallbackModel = undefined  // 防止无限回退

  return callModelWithStreaming(state, options)
}
```

### 7.2 Prompt 太长恢复

```typescript
// src/query.ts:1065-1183
async function handlePromptTooLong(
  state: State,
  error: PromptTooLongError,
  options: QueryOptions
): Promise<ModelResult> {
  // 策略 1: 排出待处理的折叠
  const collapsedMessages = drainStagedCollapses(state.messages)
  if (collapsedMessages.length > 0) {
    state.messages = state.messages.filter(
      msg => !collapsedMessages.includes(msg)
    )
    state.transition = 'collapse_drain_retry'
    return callModelWithStreaming(state, options)
  }

  // 策略 2: 响应式压缩
  if (!state.hasAttemptedReactiveCompact) {
    state.hasAttemptedReactiveCompact = true
    await runReactiveCompact(state, options)
    state.transition = 'reactive_compact_retry'
    return callModelWithStreaming(state, options)
  }

  // 策略 3: 停止钩子 (让用户处理)
  state.stopHookActive = true
  await handleStopHooks(state, options)

  throw error
}
```

### 7.3 Output Tokens 恢复

```typescript
// src/query.ts:1188-1256
async function handleMaxOutputTokens(
  state: State,
  options: QueryOptions
): Promise<ModelResult> {
  // 策略 1: 升级到 64k (如果启用)
  if (
    state.maxOutputTokensRecoveryCount === 0 &&
    feature('TENGU_OTK_SLOT_V1')
  ) {
    state.maxOutputTokensOverride = 65536  // 64k
    state.maxOutputTokensRecoveryCount++
    state.transition = 'max_output_tokens_escalate'
    return callModelWithStreaming(state, options)
  }

  // 策略 2: 注入恢复消息
  if (state.maxOutputTokensRecoveryCount < MAX_OUTPUT_TOKENS_RECOVERY_LIMIT) {
    // 注入恢复消息
    state.messages.push(createRecoveryMessage())
    state.maxOutputTokensRecoveryCount++
    state.transition = 'max_output_tokens_recovery'
    return callModelWithStreaming(state, options)
  }

  throw new Error('Max output tokens recovery limit reached')
}
```

---

## 8. Token 预算管理

### 8.1 预算追踪

```typescript
// src/query.ts:508-515
interface TaskBudget {
  remaining: number  // 剩余 token 预算
  initial: number   // 初始预算
}

// 在每次压缩后更新预算
function updateBudgetAfterCompact(
  budget: TaskBudget,
  state: State
): TaskBudget {
  const finalContextTokens = countTokens(state.messages)

  return {
    ...budget,
    remaining: budget.remaining - finalContextTokens,
  }
}

// 检查预算
function checkBudget(budget: TaskBudget): boolean {
  return budget.remaining > 0
}
```

### 8.2 USD 预算

```typescript
// src/QueryEngine.ts:971-1048
private checkBudgetEnforcement(): void {
  const maxBudgetUsd = this.config.maxBudgetUsd

  if (maxBudgetUsd === undefined) {
    return
  }

  const totalCost = calculateTotalCost(this.totalUsage)

  if (totalCost >= maxBudgetUsd) {
    throw new BudgetExceededError(
      `Session budget of ${maxBudgetUsd} USD exceeded. ` +
      `Total cost: ${totalCost} USD`
    )
  }
}
```

---

## 9. 继续原因 (Transitions)

### 9.1 Transition 类型

```typescript
// src/query.ts
type Continue =
  | 'collapse_drain_retry'        // 排出折叠后重试
  | 'reactive_compact_retry'      // 响应式压缩后重试
  | 'max_output_tokens_escalate'  // 升级 output tokens
  | 'max_output_tokens_recovery'   // 注入恢复消息
  | 'stop_hook_blocking'          // 停止钩子阻塞
  | 'token_budget_continuation'   // token 预算继续
  | 'next_turn'                   // 正常继续
```

### 9.2 Transition 处理

```typescript
// src/query.ts:1660-1671
function shouldContinue(
  message: StreamEvent,
  state: State
): boolean {
  switch (message.event.type) {
    case 'content_block':
      if (message.event.content.type === 'tool_use') {
        return true  // 工具使用需要继续
      }
      break

    case 'message_delta':
      if (message.event.delta.stop_reason === 'tool_use') {
        return true
      }
      break
  }

  return false
}
```

---

## 10. 设计模式总结

### 10.1 AsyncGenerator 模式

```typescript
// 查询使用 AsyncGenerator 实现流式处理
async function* query(
  messages: Message[],
  options: QueryOptions
): AsyncGenerator<SDKMessage> {
  // 流式产生消息
  yield { type: 'assistant', content: [...] }
  yield { type: 'tool_use', id: '1', name: 'Bash', input: {...} }
  yield { type: 'tool_result', id: '1', content: '...' }
  // ...
}
```

### 10.2 状态机模式

```typescript
// 查询循环作为状态机
while (true) {
  const state = yield* compress(state)
  const result = yield* callAPI(state)
  const decision = processResult(result)

  switch (decision) {
    case 'continue':
      continue
    case 'stop':
      break
    case 'retry':
      retryCount++
      continue
  }
}
```

### 10.3 策略模式

```typescript
// 压缩策略可插拔
interface CompactStrategy {
  compact(messages: Message[], context: Context): Promise<Message[]>
}

// 注册策略
const strategies: Record<string, CompactStrategy> = {
  micro: microCompactStrategy,
  full: fullCompactStrategy,
  reactive: reactiveCompactStrategy,
}

// 根据特性开关选择
const activeStrategy = strategies[currentFeature()] ?? microCompactStrategy
```

---

*文档版本: 2026-03-31*
