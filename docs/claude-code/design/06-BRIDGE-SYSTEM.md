# 桥接系统设计文档

> 本文档详细解析 Claude Code 桥接系统的架构设计、传输协议、IDE 集成机制。

---

## 1. 设计概述

### 1.1 核心职责

桥接系统实现 **IDE 远程控制**，允许：

- VS Code/JetBrains 扩展连接到 Claude Code CLI
- 通过 claude.ai 服务器进行双向通信
- 在 IDE 中使用 Claude Code 会话

### 1.2 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                      claude.ai Backend                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Environments API (v1)                                      │  │
│  │  POST /environments/bridge                                │  │
│  │  GET  /environments/{id}/work/poll                        │  │
│  │  POST /environments/{id}/work/{id}/ack                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Session Ingress (WS/SSE)                                  │  │
│  │  WS /session_ingress/ws/{sessionId}                       │  │
│  │  SSE /worker/events/stream                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CCR v2 API (/worker/*)                                    │  │
│  │  POST /worker/register                                     │  │
│  │  POST /worker/events                                       │  │
│  │  PUT  /worker/state                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Bridge Protocol
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Claude Code CLI (Bridge Mode)                  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  initReplBridge()                                          │  │
│  │  - OAuth、git、标题派生                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Bridge Core                                               │  │
│  │  - 环境注册                                                │  │
│  │  - 会话创建                                                │  │
│  │  - 工作轮询                                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Transport Layer                                          │  │
│  │  - HybridTransport (v1): WS + HTTP POST                  │  │
│  │  - SSETransport + CCRClient (v2)                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Session Runner                                            │  │
│  │  - 派生子 Claude Code 进程                                │  │
│  │  - stdout NDJSON 解析                                     │  │
│  │  - 权限请求转发                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 传输架构

### 2.1 v1 vs v2 对比

| 方面 | v1 (Env-Based) | v2 (Env-Less) |
|------|----------------|---------------|
| 协议 | Environments API | 直接 CCR |
| 传输 | HybridTransport | SSETransport + CCRClient |
| 读 | WebSocket | SSE stream |
| 写 | HTTP POST (batched) | HTTP POST |
| 会话生命周期 | 工作分发队列 | 直接 OAuth 交换 |
| 持久模式 | 支持 | 不支持 |

### 2.2 HybridTransport (v1)

```typescript
// src/bridge/replBridgeTransport.ts
/**
 * v1 传输: WebSocket 读取 + HTTP POST 写入
 *
 * 设计理由:
 * - WebSocket 适合低延迟入站消息
 * - HTTP POST 适合可靠的有保证投递
 * - 某些网络只允许 HTTP
 */
export class HybridTransport {
  private ws: WebSocket | null = null
  private pendingWrites: Message[] = []
  private flushTimer: NodeJS.Timeout | null = null

  constructor(
    private wsUrl: string,
    private postUrl: string,
    private auth: AuthHeaders
  ) {}

  // 连接 WebSocket
  async connect(): Promise<void> {
    this.ws = new WebSocket(this.wsUrl, {
      headers: this.auth,
    })

    this.ws.on('message', (data) => {
      this.handleInboundMessage(JSON.parse(data.toString()))
    })

    this.ws.on('close', () => {
      this.scheduleReconnect()
    })

    // 启动写入 flush 循环
    this.startFlushLoop()
  }

  // 发送消息 (批量 HTTP POST)
  send(message: Message): void {
    this.pendingWrites.push(message)
  }

  // 定期 flush 批量写入
  private async flushWriteBatch(): Promise<void> {
    if (this.pendingWrites.length === 0) return

    const batch = this.pendingWrites.splice(0, this.pendingWrites.length)

    await fetch(this.postUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.auth,
      },
      body: JSON.stringify({ messages: batch }),
    })
  }

  // 自动重连
  private scheduleReconnect(): void {
    // 指数退避，最多 10 分钟
    const delay = Math.min(1000 * Math.pow(2, this.retryCount), 600000)
    setTimeout(() => {
      this.retryCount++
      this.connect()
    }, delay)
  }
}
```

### 2.3 SSETransport (v2)

```typescript
// src/bridge/replBridgeTransport.ts
/**
 * v2 传输: SSE 读取 + HTTP POST 写入
 *
 * 设计理由:
 * - SSE 比 WebSocket 更简单
 * - 某些代理只允许 HTTP
 * - 支持更好的负载均衡
 */
export class SSETransport {
  private eventSource: EventSource | null = null
  private pendingWrites: Message[] = []

  constructor(
    private sessionUrl: string,
    private ingressToken: string,
    private epoch: number
  ) {}

  // 连接 SSE 流
  async connect(): Promise<void> {
    // SSE endpoint
    const sseUrl = `${this.sessionUrl}/events/stream?epoch=${this.epoch}`

    this.eventSource = new EventSource(sseUrl, {
      headers: { 'Authorization': `Bearer ${this.ingressToken}` }
    })

    this.eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      this.handleInboundMessage(data)
    }

    this.eventSource.addEventListener('init', (event) => {
      // 初始化消息，包含序列号
      const init = JSON.parse((event as MessageEvent).data)
      this.lastSequenceNum = init.sequenceNum
    })
  }

  // 发送消息
  async send(message: Message): Promise<void> {
    // 单次写入，不批量
    await fetch(`${this.sessionUrl}/events`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.ingressToken}`,
      },
      body: JSON.stringify({
        sequenceNum: this.nextSequenceNum++,
        ...message,
      }),
    })
  }
}
```

---

## 3. 消息协议

### 3.1 消息类型

```typescript
// src/bridge/bridgeMessaging.ts

// 出站消息 (CLI → Server)
type OutboundMessage =
  | { type: 'assistant'; content: ContentBlock[]; uuid: string }
  | { type: 'result'; subtype: 'success' | 'error'; uuid: string }
  | { type: 'user'; content: ContentBlock[]; uuid: string }
  | { type: 'control_response'; request_id: string; result: unknown }
  | { type: 'control_cancel_request'; request_id: string }

// 入站消息 (Server → CLI)
type InboundMessage =
  | { type: 'user'; content: ContentBlock[]; uuid: string }
  | { type: 'control_request'; subtype: ControlSubtype; request_id: string; params?: unknown }
  | { type: 'control_response'; request_id: string; result: unknown }
  | { type: 'control_cancel_request'; request_id: string }

// 控制请求子类型
type ControlSubtype =
  | 'initialize'       // 会话初始化
  | 'set_model'        // 更改模型
  | 'set_max_thinking_tokens'  // 调整思考预算
  | 'set_permission_mode'     // 更改权限模式
  | 'can_use_tool'     // 权限请求
  | 'interrupt'        // 取消当前轮次
```

### 3.2 UUID 去重

```typescript
// src/bridge/bridgeMessaging.ts
/**
 * BoundedUUIDSet - FIFO 环缓冲
 *
 * 问题：WebSocket/SSE 消息可能重复投递或回显
 * 解决：使用环缓冲跟踪最近看到的 UUID
 */
export class BoundedUUIDSet {
  private set: Set<string> = new Set()
  private queue: string[] = []

  constructor(private capacity: number = 2000) {}

  add(uuid: string): void {
    if (this.set.size >= this.capacity) {
      // 移除最老的
      const oldest = this.queue.shift()!
      this.set.delete(oldest)
    }

    this.set.add(uuid)
    this.queue.push(uuid)
  }

  has(uuid: string): boolean {
    return this.set.has(uuid)
  }
}

// 入站消息处理
export function handleIngressMessage(
  data: string,
  recentPostedUUIDs: BoundedUUIDSet,  // 我们发送的消息 (回声)
  recentInboundUUIDs: BoundedUUIDSet, // 入站消息 (重传)
  onInboundMessage?: (msg: InboundMessage) => void,
  onPermissionResponse?: (resp: ControlResponse) => void
): void {
  const message: InboundMessage = JSON.parse(data)

  // 1. 去除回声 (我们发送的消息弹回)
  if (message.uuid && recentPostedUUIDs.has(message.uuid)) {
    return  // 忽略
  }

  // 2. 去除重传 (服务器重复投递)
  if (message.uuid && recentInboundUUIDs.has(message.uuid)) {
    return  // 忽略
  }

  // 3. 记录 UUID
  if (message.uuid) {
    recentInboundUUIDs.add(message.uuid)
  }

  // 4. 分发消息
  if (message.type === 'control_response') {
    onPermissionResponse?.(message)
  } else {
    onInboundMessage?.(message)
  }
}
```

### 3.3 控制请求处理

```typescript
// src/bridge/bridgeMessaging.ts
export async function handleControlRequest(
  request: ControlRequest,
  handlers: ServerControlRequestHandlers
): Promise<ControlResponse> {
  const { subtype, request_id, params } = request

  switch (subtype) {
    case 'initialize':
      return handlers.onInitialize(request_id, params as InitializeParams)

    case 'set_model':
      return handlers.onSetModel(request_id, params as SetModelParams)

    case 'set_permission_mode':
      return handlers.onSetPermissionMode(
        request_id,
        params as SetPermissionModeParams
      )

    case 'can_use_tool':
      // 转发到子进程
      return handlers.onCanUseTool(request_id, params as CanUseToolParams)

    case 'interrupt':
      return handlers.onInterrupt(request_id)

    case 'set_max_thinking_tokens':
      return handlers.onSetMaxThinkingTokens(
        request_id,
        params as SetMaxThinkingTokensParams
      )

    default:
      // 未知子类型返回错误 (防止 WS 挂起)
      return {
        type: 'control_response',
        request_id,
        result: { error: `Unknown subtype: ${subtype}` }
      }
  }
}
```

---

## 4. Bridge 配置

### 4.1 配置类型

```typescript
// src/bridge/bridgeMain.ts
export interface BridgeConfig {
  // 工作目录
  dir: string

  // 环境标识
  machineName: string
  branch: string
  gitRepoUrl: string | null

  // 会话配置
  maxSessions: number  // 默认 1
  spawnMode: SpawnMode
  sessionTimeoutMs?: number

  // 连接配置
  bridgeId: string  // 客户端生成 UUID
  environmentId?: string  // 服务器分配
  workerType: 'claude_code' | 'claude_code_assistant'

  // 持久化
  reuseEnvironmentId?: string  // --session-id resume
}

type SpawnMode =
  | 'single-session'  // 一个会话，桥接结束后终止
  | 'worktree'        // 每个会话隔离 git worktree
  | 'same-dir'        // 所有会话共享目录
```

### 4.2 环境注册

```typescript
// src/bridge/bridgeMain.ts
async function registerEnvironment(
  config: BridgeConfig,
  auth: AuthHeaders
): Promise<EnvironmentInfo> {
  // 构建注册请求
  const registerRequest = {
    dir: config.dir,
    machine_name: config.machineName,
    branch: config.branch,
    git_repo_url: config.gitRepoUrl,
    max_sessions: config.maxSessions,
    spawn_mode: config.spawnMode,
    bridge_id: config.bridgeId,
    worker_type: config.workerType,
  }

  // POST /v1/environments/bridge
  const response = await fetch(
    `${API_BASE}/v1/environments/bridge`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...auth,
      },
      body: JSON.stringify(registerRequest),
    }
  )

  if (!response.ok) {
    throw new BridgeError(`Environment registration failed: ${response.status}`)
  }

  const info: EnvironmentInfo = await response.json()

  return {
    environmentId: info.environment_id,
    sessionIngressUrl: info.session_ingress_url,
    workerEpoch: info.worker_epoch,
  }
}
```

---

## 5. Session Runner

### 5.1 SessionHandle 类型

```typescript
// src/bridge/sessionRunner.ts
export interface SessionHandle {
  sessionId: string
  done: Promise<SessionDoneStatus>

  // 控制
  kill(): void        // SIGTERM
  forceKill(): void   // SIGKILL

  // 活动追踪
  activities: SessionActivity[]  // 环缓冲 (最后 10 个)
  currentActivity: SessionActivity | null

  // 调试
  lastStderr: string[]  // 环缓冲 (最后 10 行)

  // 输入/输出
  writeStdin(data: string): void

  // Token 刷新
  updateAccessToken(token: string): void
}

type SessionDoneStatus =
  | { type: 'completed' }
  | { type: 'failed'; error: string }
  | { type: 'interrupted' }
```

### 5.2 子进程派生

```typescript
// src/bridge/sessionRunner.ts
export async function spawnSession(
  options: SpawnOptions
): Promise<SessionHandle> {
  // 构建 CLI 参数
  const args = [
    '--print',
    '--sdk-url', options.sdkUrl,
    '--session-id', options.sessionId,
    '--input-format', 'stream-json',
    '--output-format', 'stream-json',
    '--replay-user-messages',

    // 调试选项
    ...(options.verbose ? ['--verbose'] : []),
    ...(options.debugFile ? ['--debug-file', options.debugFile] : []),

    // 权限模式
    ...(options.permissionMode
      ? ['--permission-mode', options.permissionMode]
      : []
    ),
  ]

  // 环境变量
  const env = {
    ...process.env,

    // 认证
    CLAUDE_CODE_SESSION_ACCESS_TOKEN: options.accessToken,

    // 标记为桥接模式
    CLAUDE_CODE_ENVIRONMENT_KIND: 'bridge',

    // v2 提示
    CLAUDE_CODE_POST_FOR_SESSION_INGRESS_V2: '1',
  }

  // v2 额外参数
  if (options.useCcrV2) {
    env.CLAUDE_CODE_USE_CCR_V2 = '1'
    env.CLAUDE_CODE_WORKER_EPOCH = String(options.workerEpoch)
  }

  // 派生子进程
  const child = spawn('claude', args, {
    cwd: options.cwd,
    env,
    stdio: ['pipe', 'pipe', 'pipe'],
  })

  // 创建 SessionHandle
  const handle: SessionHandle = {
    sessionId: options.sessionId,
    done: new Promise((resolve) => {
      child.on('exit', (code, signal) => {
        resolve(
          code === 0
            ? { type: 'completed' }
            : { type: 'failed', error: `Exit code ${code}` }
        )
      })
    }),

    kill: () => child.kill('SIGTERM'),
    forceKill: () => child.kill('SIGKILL'),

    activities: [],
    currentActivity: null,
    lastStderr: [],

    writeStdin: (data) => child.stdin?.write(data),

    updateAccessToken: (token) => {
      // 通过 stdin 发送 token 更新
      child.stdin?.write(JSON.stringify({
        type: 'update_environment_variables',
        variables: {
          CLAUDE_CODE_SESSION_ACCESS_TOKEN: token,
        }
      }) + '\n')
    },
  }

  // 解析 stdout NDJSON
  child.stdout?.on('data', (data) => {
    const lines = data.toString().split('\n')

    for (const line of lines) {
      if (!line.trim()) continue

      const activity = parseActivityLine(line)
      if (activity) {
        updateActivities(handle, activity)
      }
    }
  })

  return handle
}
```

### 5.3 活动提取

```typescript
// 从 stdout NDJSON 提取活动
interface SessionActivity {
  type: 'assistant' | 'tool_use' | 'result' | 'error'
  toolUseId?: string
  toolName?: string
  content?: string
  timestamp: number
}

export function parseActivityLine(
  line: string,
  sessionId: string,
  onDebug?: (msg: string) => void
): SessionActivity | null {
  try {
    const msg = JSON.parse(line)

    // 处理 assistant 消息
    if (msg.type === 'assistant') {
      const toolUses = msg.content?.filter(
        (c: ContentBlock) => c.type === 'tool_use'
      )

      return {
        type: toolUses?.length > 0 ? 'tool_use' : 'assistant',
        toolUseId: toolUses?.[0]?.id,
        toolName: toolUses?.[0]?.name,
        content: msg.content?.[0]?.text?.slice(0, 100),
        timestamp: Date.now(),
      }
    }

    // 处理 result 消息
    if (msg.type === 'result') {
      return {
        type: msg.subtype === 'success' ? 'result' : 'error',
        content: msg.content?.[0]?.text,
        timestamp: Date.now(),
      }
    }

    return null
  } catch {
    onDebug?.(`Failed to parse: ${line.slice(0, 100)}`)
    return null
  }
}
```

---

## 6. ReplBridge

### 6.1 初始化流程

```typescript
// src/bridge/replBridge.ts
export async function initReplBridge(
  options: ReplBridgeOptions
): Promise<ReplBridgeHandle> {
  // 1. OAuth (如果需要)
  if (options.needsAuth) {
    await performOAuth()
  }

  // 2. 派生环境
  const { environmentId, sessionIngressUrl, workerEpoch } =
    await registerEnvironment(options)

  // 3. 创建会话
  const { bridgeSessionId, sessionUrl, ingressToken } =
    await createSession(environmentId, options)

  // 4. 写入桥接指针 (崩溃恢复)
  await writeBridgePointer({
    environmentId,
    bridgeSessionId,
    sessionIngressUrl,
    workerEpoch,
  })

  // 5. 初始化传输
  const transport = options.useCcrV2
    ? createSSETransport(sessionUrl, ingressToken, workerEpoch)
    : createHybridTransport(sessionIngressUrl, ingressToken)

  // 6. 启动工作轮询
  const workPollLoop = startWorkPollLoop({
    environmentId,
    transport,
    onWorkReceived: (work) => handleWork(work, transport),
  })

  // 返回 handle
  return {
    bridgeSessionId,
    environmentId,
    sessionIngressUrl,

    writeMessages: (messages) => transport.send({ type: 'batch', messages }),
    writeSdkMessages: (messages) => transport.send({ type: 'sdk_batch', messages }),

    sendControlRequest: (request) =>
      transport.send({ type: 'control_request', ...request }),

    sendControlResponse: (response) =>
      transport.send({ type: 'control_response', ...response }),

    sendResult: () => archiveSession(bridgeSessionId),

    teardown: async () => {
      workPollLoop.stop()
      await transport.close()
    },
  }
}
```

### 6.2 工作轮询

```typescript
// src/bridge/replBridge.ts
function startWorkPollLoop(options: {
  environmentId: string
  transport: Transport
  onWorkReceived: (work: WorkItem) => void
}): { stop: () => void } {
  let running = true
  let pollInterval = 1000  // 初始轮询间隔

  async function poll() {
    if (!running) return

    try {
      const work = await fetchWork(options.environmentId)

      if (work.items.length > 0) {
        // 有工作，更新轮询间隔
        pollInterval = 1000

        for (const item of work.items) {
          // 确认工作
          await ackWork(options.environmentId, item.id)

          // 分发工作
          options.onWorkReceived(item)
        }
      } else {
        // 无工作，指数退避到最大 30s
        pollInterval = Math.min(pollInterval * 1.5, 30000)
      }
    } catch (error) {
      if (error instanceof EnvironmentNotFoundError) {
        // 环境被回收，需要重建
        await recoverEnvironment(options)
      }

      pollInterval = Math.min(pollInterval * 2, 30000)
    }

    // 调度下一次轮询
    if (running) {
      setTimeout(poll, pollInterval)
    }
  }

  // 启动轮询
  poll()

  return {
    stop: () => {
      running = false
    }
  }
}
```

---

## 7. IDE 扩展通信

### 7.1 消息流

```
┌─────────────────────────────────────────────────────────────────┐
│  VS Code / JetBrains Extension                                   │
│                                                                  │
│  User Input ──────────────────────────────────────────────────►│
│                                                                  │
│  ◄────────────────────── AI Response                             │
│                                                                  │
│  ◄────────────────────── Permission Prompt                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Extension ↔ claude.ai WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      claude.ai Server                            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Session Ingress                                         │  │
│  │  - 入站: 用户消息 (from extension)                       │  │
│  │  - 出站: assistant 消息, tool_result, permission_request │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Bridge Protocol (WS/SSE + HTTP)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Code CLI                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Session Runner (子进程)                                  │  │
│  │  - 接收: 用户消息                                         │  │
│  │  - 发送: assistant 消息, tool_result                      │  │
│  │  - 转发: permission_request → extension                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 权限请求流

```typescript
// 子进程发送权限请求
child.stdin?.write(JSON.stringify({
  type: 'control_request',
  subtype: 'can_use_tool',
  request_id: 'req-123',
  params: {
    tool: 'Bash',
    input: { command: 'rm -rf /tmp/test' },
  }
}) + '\n')

// CLI 转发到桥接
bridgeHandle.sendControlRequest({
  subtype: 'can_use_tool',
  request_id: 'req-123',
  params: { tool: 'Bash', input: { command: 'rm -rf /tmp/test' } },
})

// 桥接发送到服务器
transport.send({
  type: 'control_request',
  request_id: 'req-123',
  params: { tool: 'Bash', input: { command: 'rm -rf /tmp/test' } },
})

// 服务器转发到 extension
// extension 显示确认 UI

// 用户确认/拒绝
// 响应通过桥接送回 CLI
bridgeHandle.sendControlResponse({
  request_id: 'req-123',
  result: { behavior: 'allow' | 'deny' },
})

// CLI 写入子进程 stdin
child.stdin?.write(JSON.stringify({
  type: 'control_response',
  request_id: 'req-123',
  result: { behavior: 'allow' | 'deny' },
}) + '\n')
```

---

## 8. 设计模式总结

### 8.1 模式列表

| 模式 | 应用 | 优势 |
|------|------|------|
| **传输抽象** | HybridTransport / SSETransport | 可替换 |
| **批量写入** | HTTP POST 批量 | 可靠性 |
| **指数退避** | 重连、轮询 | 稳定性 |
| **UUID 去重** | BoundedUUIDSet | 防止重复 |
| **状态机** | Session 生命周期 | 清晰 |
| **工作池** | 环境/会话管理 | 资源控制 |

### 8.2 错误恢复

```typescript
// 错误恢复策略
interface RecoveryStrategy {
  onError(error: Error): Promise<RecoveryAction>
}

const strategies: RecoveryStrategy[] = [
  // 1. 环境被回收
  {
    error: EnvironmentNotFoundError,
    recover: async (opts) => {
      // 重新注册环境，保持 sessionId
      const info = await registerEnvironment({
        ...opts.config,
        reuseEnvironmentId: opts.environmentId,
      })
      return { ...info, strategy: 'reuse' }
    }
  },

  // 2. 会话超时
  {
    error: SessionTimeoutError,
    recover: async (opts) => {
      // 创建新会话
      const session = await createSession(opts.environmentId)
      return { ...session, strategy: 'new_session' }
    }
  },

  // 3. 传输断开
  {
    error: TransportDisconnectError,
    recover: async (opts) => {
      // 重新连接
      await opts.transport.reconnect()
      return { strategy: 'reconnect' }
    }
  },
]
```

---

*文档版本: 2026-03-31*
