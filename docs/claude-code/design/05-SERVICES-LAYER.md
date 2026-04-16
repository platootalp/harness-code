# 服务层设计文档

> 本文档详细解析 Claude Code 服务层架构，包括 API、MCP、OAuth、LSP、Analytics、Context Compression 等核心服务。

---

## 1. 服务架构概述

### 1.1 服务组织

```
src/services/
├── api/                    # Anthropic API 客户端
│   ├── client.ts          # 多提供者工厂
│   ├── bootstrap.ts       # 引导数据获取
│   ├── filesApi.ts       # 文件附件管理
│   └── claude.ts         # 核心 API 交互
│
├── mcp/                   # Model Context Protocol
│   ├── useManageMCPConnections.ts  # React Hook
│   ├── client.ts          # MCP 客户端核心
│   ├── channelNotification.ts       # 通道权限
│   └── oauthPort.ts       # MCP OAuth 处理
│
├── oauth/                 # OAuth 2.0
│   ├── index.ts          # OAuthService 类
│   └── client.ts         # OAuth 工具函数
│
├── lsp/                   # Language Server Protocol
│   ├── LSPServerManager.ts
│   ├── LSPServerInstance.ts
│   └── manager.ts        # 单例包装
│
├── analytics/            # GrowthBook + Datadog
│   ├── growthbook.ts    # 特性开关 SDK
│   ├── sink.ts          # 事件路由器
│   ├── datadog.ts       # Datadog 集成
│   └── firstPartyEventLogger.ts
│
├── compact/              # 上下文压缩
│   ├── compact.ts       # 完整压缩
│   └── microCompact.ts  # 轻量级压缩
│
├── plugins/              # 插件系统
│   └── PluginInstallationManager.ts
│
└── tokenEstimation.ts   # Token 计数
```

### 1.2 设计原则

| 原则 | 实现 | 优势 |
|------|------|------|
| **依赖注入** | 工厂函数而非类 | 可测试、可替换 |
| **懒加载** | 动态 import | 减小初始 bundle |
| **无环依赖** | Analytics 独立 | 避免导入循环 |
| **单一职责** | 每个服务一个职责 | 可维护 |
| **可观测性** | Hook + 回调 | 状态追踪 |

---

## 2. API 服务

### 2.1 多提供者支持

```typescript
// src/services/api/client.ts
export type ApiProvider =
  | 'direct'           // api.anthropic.com
  | 'aws-bedrock'      // AWS Bedrock
  | 'azure-foundry'    // Azure Foundry
  | 'vertex-ai'        // Google Vertex AI

export interface ClientConfig {
  provider: ApiProvider
  apiKey?: string
  // Provider-specific 配置
  bedrockRegion?: string
  azureEndpoint?: string
  vertexProject?: string
}

export function createApiClient(config: ClientConfig): ApiClient {
  switch (config.provider) {
    case 'aws-bedrock':
      return createBedrockClient(config)

    case 'azure-foundry':
      return createFoundryClient(config)

    case 'vertex-ai':
      return createVertexClient(config)

    case 'direct':
    default:
      return createDirectClient(config)
  }
}
```

### 2.2 Direct 客户端

```typescript
// src/services/api/client.ts
async function createDirectClient(
  config: ClientConfig
): Promise<ApiClient> {
  const baseURL = process.env.ANTHROPIC_BASE_URL ?? 'https://api.anthropic.com'

  return {
    async queryModelWithStreaming(request, options) {
      // 1. OAuth token 刷新
      await checkAndRefreshOAuthTokenIfNeeded()

      // 2. 构建请求
      const response = await fetch(`${baseURL}/v1/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': config.apiKey,
          'anthropic-version': '2023-06-01',
          'anthropic-dangerous-direct-password': 'true',
          // 自定义头
          ...getCustomHeaders(),
        },
        body: JSON.stringify(request),
        // 代理支持
        ...getProxyOptions(),
      })

      // 3. 处理响应
      if (!response.ok) {
        throw await handleApiError(response)
      }

      // 4. 返回流式响应
      return response.body
    }
  }
}
```

### 2.3 Bedrock 客户端

```typescript
// AWS Bedrock 客户端
async function createBedrockClient(config: ClientConfig) {
  // 使用 @anthropic-ai/bedrock-sdk
  const { createBedrockClient: initBedrock } = await import(
    '@anthropic-ai/bedrock-sdk'
  )

  const bedrock = initBedrock({
    region: config.bedrockRegion ?? 'us-east-1',
    credentials: await getAwsCredentials(),
  })

  return {
    async queryModelWithStreaming(request, options) {
      // Bedrock 使用不同的模型 ID 格式
      const model = convertToBedrockModelId(request.model)

      const response = await bedrock.query({
        ...request,
        model,
      })

      return response.body
    }
  }
}
```

### 2.4 文件 API

```typescript
// src/services/api/filesApi.ts
export class FilesApiClient {
  constructor(private config: ClientConfig) {}

  // 下载文件
  async downloadFile(fileId: string): Promise<Buffer> {
    const response = await this.request(
      `GET /v1/files/${fileId}/download`
    )
    return Buffer.from(await response.arrayBuffer())
  }

  // 上传文件
  async uploadFile(
    file: Buffer,
    filename: string,
    mimeType: string
  ): Promise<FileUploadResult> {
    const formData = new FormData()
    formData.append('file', file, filename)

    const response = await this.request(
      'POST /v1/files',
      {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
          'anthropic-version': 'files-api-2025-04-14',
        },
      }
    )

    return response.json()
  }

  // 并发上传
  async uploadSessionFiles(
    files: FileUploadRequest[],
    concurrency = 5
  ): Promise<FileUploadResult[]> {
    // 使用信号量控制并发
    const semaphore = new Semaphore(concurrency)

    return Promise.all(
      files.map(file =>
        semaphore.acquire(() => this.uploadFile(file))
      )
    )
  }
}
```

---

## 3. MCP 服务

### 3.1 MCP 客户端架构

```
┌─────────────────────────────────────────────────────────────────┐
│  MCP Service                                                     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  useManageMCPConnections (React Hook)                       │ │
│  │  - 生命周期管理                                            │ │
│  │  - 状态批量更新 (16ms 合并窗口)                             │ │
│  │  - 重连策略 (指数退避)                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  MCP Client (per server)                                    │ │
│  │  - Transport 管理 (stdio/SSE/HTTP/WS)                       │ │
│  │  - 工具/命令/资源获取                                       │ │
│  │  - 消息协议                                                │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 React Hook

```typescript
// src/services/mcp/useManageMCPConnections.ts
export function useManageMCPConnections(
  config: MCPConfig
): MCPConnectionResult {
  // 状态
  const [state, setState] = useState<MCPState>({
    clients: [],
    status: 'initializing',
  })

  // 初始化
  useEffect(() => {
    initializeConnections(config)
  }, [config])

  // 两阶段配置加载
  async function initializeConnections(config: MCPConfig) {
    // 阶段 1: Claude Code 配置 (快速)
    const localConfig = await loadMCPConfig()

    // 阶段 2: claude.ai 配置 (可能较慢)
    const remoteConfig = await fetchRemoteMCPConfig()

    // 合并配置
    const allServers = [...localConfig.servers, ...remoteConfig.servers]

    // 连接每个服务器
    for (const server of allServers) {
      await connectToServer(server)
    }
  }

  // 批量状态更新 (16ms 合并窗口)
  const batchUpdate = useMemo(
    () => createBatchedUpdater(setState, 16),
    []
  )

  return { state, connect, disconnect, reconnect }
}
```

### 3.3 MCP 客户端

```typescript
// src/services/mcp/client.ts
export class MCPClient {
  constructor(
    private config: MCPServerConfig,
    private transport: MCPTransport
  ) {}

  // 连接服务器
  async connect(): Promise<void> {
    switch (this.transport.type) {
      case 'stdio':
        await this.connectStdio()
        break
      case 'sse':
        await this.connectSSE()
        break
      case 'http':
        await this.connectHTTP()
        break
      case 'websocket':
        await this.connectWebSocket()
        break
    }

    this.state = 'connected'
  }

  // 获取工具
  async fetchTools(): Promise<MCPTool[]> {
    const response = await this.sendRequest({
      method: 'tools/list',
      params: {}
    })

    return response.tools.map(tool => ({
      name: tool.name,
      description: tool.description,
      inputSchema: tool.input_schema,
      // 包装为 Claude Code Tool 格式
    }))
  }

  // 调用工具
  async callTool(
    name: string,
    input: Record<string, unknown>
  ): Promise<unknown> {
    const response = await this.sendRequest({
      method: 'tools/call',
      params: {
        name,
        arguments: input,
      }
    })

    return response.content
  }

  // 重连
  async reconnect(): Promise<void> {
    this.state = 'reconnecting'

    // 指数退避
    let delay = 1000
    for (let attempt = 0; attempt < 5; attempt++) {
      try {
        await this.connect()
        return
      } catch (error) {
        await sleep(delay)
        delay = Math.min(delay * 2, 30000)  // 最大 30s
      }
    }

    this.state = 'failed'
  }
}
```

### 3.4 通道通知

```typescript
// src/services/mcp/channelNotification.ts
/**
 * MCP 通道权限系统
 *
 * 问题：MCP 服务器可能需要用户授权才能执行某些操作
 * 解决：通过通道通知机制请求用户授权
 */

interface ChannelPermission {
  type: 'channel_permission'
  server: string
  permission: string
  message?: string
}

export async function requestChannelPermission(
  server: string,
  permission: string
): Promise<boolean> {
  // 显示 UI 提示
  const result = await showPermissionPrompt({
    server,
    permission,
    message: `${server} is requesting permission to ${permission}`,
  })

  return result === 'allow'
}

// 包装通道消息
export function wrapChannelMessage(
  message: unknown,
  permission?: ChannelPermission
): WrappedMessage {
  return {
    content: message,
    metadata: {
      permission,
      timestamp: Date.now(),
    }
  }
}
```

---

## 4. OAuth 服务

### 4.1 OAuth 流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    OAuth 2.0 Authorization Flow                  │
│                                                                  │
│  1. Generate PKCE pair                                          │
│     code_verifier = random(128)                                  │
│     code_challenge = base64url(sha256(code_verifier))            │
│                                                                  │
│  2. Start local server                                           │
│     server = http.createServer(PORT = 0)  // 随机端口            │
│                                                                  │
│  3. Build auth URL                                               │
│     url = authorization_endpoint +                               │
│           ?client_id=...                                        │
│           &redirect_uri=http://localhost:PORT/callback          │
│           &code_challenge=...                                   │
│           &code_challenge_method=S256                           │
│                                                                  │
│  4. Open browser / Display URL                                   │
│                                                                  │
│  5. User authenticates in browser                               │
│                                                                  │
│  6. Callback received on local server                           │
│     code = extractCodeFromCallback(url)                          │
│                                                                  │
│  7. Exchange code for tokens                                     │
│     tokens = POST token_endpoint +                               │
│               code=...                                         │
│               &code_verifier=...                                │
│                                                                  │
│  8. Fetch profile info                                           │
│     profile = GET userinfo_endpoint + access_token              │
│                                                                  │
│  9. Store tokens securely                                        │
│     keychain.set('claude-oauth-tokens', tokens)                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 OAuthService 实现

```typescript
// src/services/oauth/index.ts
export class OAuthService {
  constructor(private config: OAuthConfig) {}

  async authorize(): Promise<OAuthTokens> {
    // 1. 生成 PKCE
    const codeVerifier = generateRandomString(128)
    const codeChallenge = await sha256Base64url(codeVerifier)

    // 2. 启动本地服务器
    const server = await this.startCallbackServer()
    const port = server.address().port

    try {
      // 3. 构建 auth URL
      const authUrl = buildAuthUrl({
        endpoint: this.config.authorizationEndpoint,
        clientId: this.config.clientId,
        redirectUri: `http://localhost:${port}/callback`,
        codeChallenge,
        scope: this.config.scope ?? 'offline_access profile',
      })

      // 4. 打开浏览器
      await openBrowser(authUrl)

      // 5. 等待回调
      const code = await server.waitForCallback()

      // 6. 交换 token
      const tokens = await exchangeCodeForTokens({
        endpoint: this.config.tokenEndpoint,
        code,
        codeVerifier,
        clientId: this.config.clientId,
        redirectUri: `http://localhost:${port}/callback`,
      })

      // 7. 获取 profile
      const profile = await this.fetchProfileInfo(tokens.accessToken)

      // 8. 存储 tokens
      await this.storeTokens(tokens, profile)

      return tokens
    } finally {
      // 清理服务器
      await server.close()
    }
  }

  private async startCallbackServer(): Promise<CallbackServer> {
    const server = http.createServer()

    return new Promise(resolve => {
      server.listen(0, () => {
        resolve({
          address: server.address(),
          waitForCallback: () => this.waitForCallback(server),
          close: () => server.close(),
        })
      })
    })
  }
}
```

---

## 5. LSP 服务

### 5.1 服务器管理器

```typescript
// src/services/lsp/LSPServerManager.ts
export interface LSPServerManager {
  initialize(): Promise<void>
  shutdown(): Promise<void>

  getServerForFile(filePath: string): LSPServerInstance | undefined
  ensureServerStarted(filePath: string): Promise<LSPServerInstance | undefined>

  sendRequest<T>(filePath: string, method: string, params: unknown): Promise<T>
  openFile(filePath: string, content: string): Promise<void>
  changeFile(filePath: string, content: string): Promise<void>
  saveFile(filePath: string): Promise<void>
  closeFile(filePath: string): Promise<void>
}

// 工厂函数 (避免类，更易测试)
export function createLSPServerManager(
  config: LSPManagerConfig
): LSPServerManager {
  const servers = new Map<string, LSPServerInstance>()
  const extensionMap = new Map<string, string>()  // ext -> serverId

  // 初始化扩展名映射
  for (const server of config.servers) {
    for (const ext of server.extensions ?? []) {
      extensionMap.set(ext, server.id)
    }
  }

  return {
    async initialize() {
      // 预启动配置的服务器
      for (const server of config.servers) {
        if (server.autostart) {
          await this.ensureServerStarted(server.id)
        }
      }
    },

    getServerForFile(filePath: string): LSPServerInstance | undefined {
      const ext = path.extname(filePath)
      const serverId = extensionMap.get(ext)
      return serverId ? servers.get(serverId) : undefined
    },

    async sendRequest<T>(filePath, method, params): Promise<T> {
      const server = this.getServerForFile(filePath)
      if (!server) {
        throw new Error(`No LSP server for ${filePath}`)
      }
      return server.sendRequest(method, params)
    },
  }
}
```

### 5.2 服务器实例

```typescript
// src/services/lsp/LSPServerInstance.ts
export interface LSPServerInstance {
  id: string
  state: 'stopped' | 'starting' | 'running' | 'stopping' | 'error'

  sendRequest<T>(method: string, params: unknown): Promise<T>
  notify(method: string, params: unknown): void
}

/**
 * 状态机：
 *
 * stopped ───► starting ───► running
 *   ▲              │            │
 *   │              ▼            │
 *   │           stopping ◄───────┤
 *   │              │            │
 *   │              ▼            ▼
 *   └────────── error ─────────►
 */

export function createLSPServerInstance(
  config: LSPServerConfig
): LSPServerInstance {
  let state: LSPServerState = 'stopped'
  let process: ChildProcess | null = null
  let restartCount = 0

  const capabilities: ServerCapabilities = {}
  const pendingRequests = new Map<string, Completer>()

  async function start(): Promise<void> {
    if (state === 'running') return

    state = 'starting'

    try {
      // 启动子进程
      process = spawn(config.command, config.args, {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, ...config.env },
      })

      // 启动超时
      const startupTimeout = setTimeout(() => {
        if (state === 'starting') {
          state = 'error'
          process?.kill()
        }
      }, config.startupTimeout ?? 30000)

      // 处理 LSP 协议
      process.stdout.on('data', handleLSPMessage)

      // 启动完成
      await handshake()
      state = 'running'
      clearTimeout(startupTimeout)

    } catch (error) {
      state = 'error'

      // 崩溃恢复
      if (restartCount < (config.maxRestarts ?? 3)) {
        restartCount++
        await sleep(1000 * restartCount)
        return start()
      }

      throw error
    }
  }

  async function sendRequest<T>(method: string, params: unknown): Promise<T> {
    const id = generateRequestId()

    sendMessage({
      jsonrpc: '2.0',
      id,
      method,
      params,
    })

    return pendingRequests.get(id)
  }

  return {
    get state() { return state },
    sendRequest,
    notify,
  }
}
```

### 5.3 LSP 协议处理

```typescript
// 处理 LSP 消息
function handleLSPMessage(data: Buffer): void {
  const message = JSON.parse(data.toString())

  switch (message.method) {
    case 'initialize':
      // 返回服务器能力
      sendMessage({
        jsonrpc: '2.0',
        id: message.id,
        result: {
          capabilities: {
            textDocumentSync: 1,  // Full sync
            hoverProvider: true,
            definitionProvider: true,
            referencesProvider: true,
          }
        }
      })
      break

    case 'textDocument/didOpen':
      handleDidOpen(message.params)
      break

    case 'textDocument/didChange':
      handleDidChange(message.params)
      break

    case 'textDocument/definition':
      handleDefinition(message)
      break

    case 'shutdown':
      sendMessage({ jsonrpc: '2.0', id: message.id, result: null })
      state = 'stopping'
      break
  }
}
```

---

## 6. Analytics 服务

### 6.1 无环依赖设计

```typescript
// src/services/analytics/index.ts
/**
 * Analytics 服务的关键设计：无循环依赖
 *
 * 问题：Analytics 需要从其他服务获取上下文 (用户、设置等)
 *       但其他服务可能依赖 Analytics
 *
 * 解决：事件队列模式
 *       - logEvent() 总是成功，即使没有 sink
 *       - 事件被队列，稍后通过 attachAnalyticsSink() 消费
 */

// 内部队列
let eventQueue: QueuedEvent[] = []
let sink: AnalyticsSink | null = null

export function attachAnalyticsSink(newSink: AnalyticsSink): void {
  sink = newSink

  // 队列事件出队
  while (eventQueue.length > 0) {
    const event = eventQueue.shift()!
    sink.logEvent(event.name, event.metadata)
  }
}

export function logEvent(name: string, metadata?: Record<string, unknown>): void {
  const event = { name, metadata, timestamp: Date.now() }

  if (sink) {
    sink.logEvent(name, metadata)
  } else {
    // 队列，稍后处理
    eventQueue.push(event)
  }
}
```

### 6.2 GrowthBook 特性开关

```typescript
// src/services/analytics/growthbook.ts
interface GrowthBookConfig {
  apiHost: string
  clientKey: string
  enableStreaming?: boolean
}

export class GrowthBookSDK {
  private features = new Map<string, FeatureValue>()
  private userAttributes: UserAttributes

  constructor(private config: GrowthBookConfig) {
    this.userAttributes = this.loadUserAttributes()
  }

  // 初始化
  async initialize(): Promise<void> {
    // 1. 尝试本地缓存
    const cached = loadCachedFeatures()
    if (cached) {
      this.features = new Map(Object.entries(cached))
    }

    // 2. 从远程获取
    const remoteFeatures = await this.fetchRemoteFeatures()

    // 3. 合并 (远程优先)
    for (const [key, value] of Object.entries(remoteFeatures)) {
      this.features.set(key, value)
    }

    // 4. 保存缓存
    saveCachedFeatures(Object.fromEntries(this.features))

    // 5. 定期刷新
    this.startPeriodicRefresh()
  }

  // 获取特性值 (可能返回陈旧值)
  getFeatureValue<T>(featureName: string, defaultValue: T): T {
    const feature = this.features.get(featureName)

    if (!feature) {
      return defaultValue
    }

    // 评估条件
    if (!this.evaluateCondition(feature.condition, this.userAttributes)) {
      return defaultValue
    }

    return feature.value as T
  }

  // 检查 gate (同步快速路径)
  checkGate(gateName: string): boolean {
    const gate = this.features.get(`__gate__${gateName}`)

    if (gate?.value === true) {
      return true  // 快速路径：已启用
    }

    // 需要远程检查
    return this.checkGateRemote(gateName)
  }
}
```

### 6.3 事件路由

```typescript
// src/services/analytics/sink.ts
interface AnalyticsSink {
  logEvent(name: string, metadata?: Record<string, unknown>): void
}

// 双写 Datadog + First-party
export function createDualSink(
  datadogSink: AnalyticsSink,
  firstPartySink: AnalyticsSink
): AnalyticsSink {
  return {
    logEvent(name, metadata) {
      // 1. 写入 Datadog (剥离 PII)
      datadogSink.logEvent(name, stripPII(metadata))

      // 2. 写入 First-party (完整数据)
      firstPartySink.logEvent(name, metadata)
    }
  }
}

// PII 剥离
function stripPII(metadata: Record<string, unknown>): Record<string, unknown> {
  const result = { ...metadata }

  // 剥离 _PROTO_* 键 (PII 标记列)
  for (const key of Object.keys(result)) {
    if (key.startsWith('_PROTO_')) {
      delete result[key]
    }
  }

  return result
}
```

---

## 7. Context Compression 服务

### 7.1 两级压缩策略

```
┌─────────────────────────────────────────────────────────────────┐
│  Level 1: microCompact (每轮轻量压缩)                            │
│                                                                  │
│  触发条件：                                                       │
│  - 计数阈值 (GrowthBook 配置)                                     │
│  - 时间阈值 (距上次 assistant 消息)                               │
│                                                                  │
│  策略：                                                           │
│  - 缓存编辑 (cache_edits API) 保留缓存前缀                        │
│  - 清除工具结果内容，替换为 [Cleared]                             │
│  - 不调用模型                                                      │
│                                                                  │
│  适用工具：Read, Bash, Grep, Glob, WebSearch, WebFetch           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Level 2: compact (完整对话压缩)                                  │
│                                                                  │
│  触发条件：                                                       │
│  - 上下文大小接近限制                                             │
│  - 用户请求 (/compact)                                            │
│                                                                  │
│  策略：                                                           │
│  - 调用模型生成摘要                                               │
│  - 替换原始消息为摘要                                             │
│  - 保留最近访问的文件、技能等                                     │
│                                                                  │
│  成本：额外 API 调用                                              │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Microcompact 实现

```typescript
// src/services/compact/microCompact.ts
export interface MicrocompactResult {
  messages: Message[]
  clearedToolIds: string[]
  cacheEdits?: CacheEdit[]
}

export async function microcompact(
  messages: Message[],
  context: MicrocompactContext
): Promise<MicrocompactResult> {
  const result: Message[] = []
  const clearedToolIds: string[] = []
  const cacheEdits: CacheEdit[] = []

  for (const msg of messages) {
    if (msg.role !== 'assistant') {
      result.push(msg)
      continue
    }

    const newContent: ContentBlock[] = []

    for (const block of msg.content) {
      if (block.type === 'tool_use') {
        if (shouldCompact(block.name, context)) {
          // 标记为已清除
          newContent.push({
            ...block,
            input: {
              ...block.input,
              _cleared: true,
              _clearedContent: '[Old tool result content cleared]',
            }
          })

          clearedToolIds.push(block.id)

          // 生成 cache edit
          if (context.useCacheEdits) {
            cacheEdits.push({
              toolUseId: block.id,
              edit: { type: 'clear_content' }
            })
          }
        } else {
          newContent.push(block)
        }
      } else {
        newContent.push(block)
      }
    }

    result.push({ ...msg, content: newContent })
  }

  return { messages: result, clearedToolIds, cacheEdits }
}

function shouldCompact(toolName: string, context: MicrocompactContext): boolean {
  // 检查是否可压缩
  if (!COMPACTABLE_TOOLS.has(toolName)) {
    return false
  }

  // 检查缓存编辑是否可用
  if (context.useCacheEdits) {
    return context.compactableCount > context.cacheEditsThreshold
  }

  // 检查时间
  return context.timeSinceLastAssistant > context.timeThreshold
}
```

### 7.3 完整压缩实现

```typescript
// src/services/compact/compact.ts
export interface CompactResult {
  boundaryMessage: Message
  attachments: ContentBlockParam[]
  summary: string
  originalMessageCount: number
  summaryTokenCount: number
}

export async function compact(
  messages: Message[],
  options: CompactOptions
): Promise<CompactResult> {
  // 1. 执行 PreCompact hooks
  await executeHooks(options.hooks?.PreCompact)

  // 2. 准备压缩消息
  const messagesForSummary = prepareMessagesForSummary(messages)

  // 3. 构建压缩提示词
  const compactPrompt = buildCompactPrompt(messagesForSummary)

  // 4. 剥离图片 (不需要用于摘要)
  const messagesWithoutImages = stripImages(messages)

  // 5. 调用模型生成摘要
  const summaryStream = await callModel({
    messages: [
      { role: 'user', content: compactPrompt }
    ],
    system: COMPACT_SYSTEM_PROMPT,
    model: options.summaryModel ?? 'sonnet',
    maxTokens: 1024,
  })

  let summary = ''
  for await (const event of summaryStream) {
    if (event.type === 'content_block' && event.content.type === 'text') {
      summary += event.content.text
    }
  }

  // 6. 创建压缩边界消息
  const boundaryMessage: Message = {
    role: 'system',
    content: [{
      type: 'text',
      text: ` [Previous conversation summarized. ${summary}] `
    }]
  }

  // 7. 生成后压缩附件
  const attachments = await generatePostCompactAttachments(options)

  // 8. 执行 PostCompact hooks
  await executeHooks(options.hooks?.PostCompact)

  // 9. 记录指标
  await logCompactEvent({
    originalMessageCount: messages.length,
    summaryTokenCount: estimateTokens(summary),
  })

  return {
    boundaryMessage,
    attachments,
    summary,
    originalMessageCount: messages.length,
    summaryTokenCount: estimateTokens(summary),
  }
}

async function generatePostCompactAttachments(
  options: CompactOptions
): Promise<ContentBlockParam[]> {
  const attachments: ContentBlockParam[] = []

  // 最近访问的文件 (最多 5 个，50K token 预算)
  const recentFiles = await getRecentlyAccessedFiles({
    limit: 5,
    tokenBudget: 50000
  })

  for (const file of recentFiles) {
    attachments.push({
      type: 'text',
      text: `Recent file: ${file.path}\n${file.content}`
    })
  }

  // 激活的技能 (每个 5K token，总共 25K)
  const activeSkills = await getActiveSkills({
    tokenBudget: 25000,
    perSkillBudget: 5000
  })

  for (const skill of activeSkills) {
    attachments.push({
      type: 'text',
      text: `Active skill: ${skill.name}\n${skill.content}`
    })
  }

  // 添加其他附件...
  return attachments
}
```

---

## 8. Token 估算服务

### 8.1 Token 计数方法

```typescript
// src/services/tokenEstimation.ts
export interface TokenCountResult {
  count: number
  method: 'api' | 'haiku' | 'rough'
}

export async function countTokens(
  content: string | Message[],
  options?: TokenCountOptions
): Promise<TokenCountResult> {
  // 1. 优先使用 API (最准确)
  if (options?.useAPI ?? true) {
    try {
      const count = await countTokensWithAPI(content)
      return { count, method: 'api' }
    } catch (error) {
      // API 失败，fallback
    }
  }

  // 2. Haiku fallback
  if (options?.useHaikuFallback ?? true) {
    try {
      const count = await countTokensViaHaikuFallback(content)
      return { count, method: 'haiku' }
    } catch (error) {
      // Haiku 失败，fallback
    }
  }

  // 3. Rough 估算 (最不准确但最快)
  const roughCount = roughTokenCountEstimation(content)
  return { count: roughCount, method: 'rough' }
}

// Rough 估算
export function roughTokenCountEstimation(content: string | Message[]): number {
  if (typeof content === 'string') {
    // 简单假设: 4 bytes ≈ 1 token
    return Math.ceil(content.length / 4)
  }

  let total = 0
  for (const msg of content) {
    total += roughTokenCountEstimation(JSON.stringify(msg.content))
  }
  return total
}
```

### 8.2 按块类型计数

```typescript
// 计算特定块类型的 token
export function countBlockTokens(
  block: ContentBlock,
  options?: TokenCountOptions
): number {
  switch (block.type) {
    case 'text':
      return roughTokenCountEstimation(block.text)

    case 'image':
    case 'document':
      // 图片/文档: 固定估算 ~2000 tokens
      return 2000

    case 'tool_use':
      // tool_use: name + input JSON
      const nameTokens = roughTokenCountEstimation(block.name)
      const inputTokens = roughTokenCountEstimation(JSON.stringify(block.input))
      return nameTokens + inputTokens + 10  // overhead

    case 'tool_result':
      // 递归计数内容
      return countBlockTokens(block.content, options)

    case 'thinking':
      // Thinking 块: 计数思考文本
      return roughTokenCountEstimation(block.thinking) +
             roughTokenCountEstimation(block.thinking.length.toString())

    case 'redacted_thinking':
      // 脱敏思考: 固定估算
      return 50

    default:
      return roughTokenCountEstimation(JSON.stringify(block))
  }
}
```

---

## 9. 设计模式总结

### 9.1 模式列表

| 模式 | 应用 | 优势 |
|------|------|------|
| **工厂函数** | `createLSPServerManager()` | 可测试、可替换 |
| **事件队列** | Analytics `logEvent()` | 无环依赖 |
| **状态机** | LSP 服务器状态 | 清晰的状态转换 |
| **批量更新** | MCP 连接状态 | 性能优化 |
| **指数退避** | MCP 重连 | 稳定性 |
| **特性开关** | GrowthBook | 灰度发布 |
| **双重写入** | Analytics sink | 渐进迁移 |

### 9.2 依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                      依赖关系图                                   │
│                                                                  │
│  API Service ─────────► OAuth Service                           │
│      │                        │                                 │
│      │                        ▼                                 │
│      │               Token Storage (Keychain)                   │
│      │                                                          │
│  Analytics ◄──────────── (无依赖)                                │
│      │                                                          │
│      ▼                                                          │
│  GrowthBook ◄───► Settings (读取配置)                            │
│                                                                  │
│  MCP Service ◄───► Analytics (事件)                             │
│      │                                                          │
│      ▼                                                          │
│  OAuth Service (MCP OAuth)                                       │
│                                                                  │
│  LSP Service (无外部依赖)                                        │
│                                                                  │
│  Compact ◄──────────► Token Estimation                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*文档版本: 2026-03-31*
