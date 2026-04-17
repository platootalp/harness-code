# 状态管理设计文档

> 本文档详细解析 Claude Code 状态管理系统的架构设计、核心实现和 React 集成模式。

---

## 1. 设计概述

### 1.1 设计目标

状态管理系统负责：

- 管理应用全局状态
- 提供响应式数据流
- 协调状态变更与副作用
- 支持 React 并发模式

### 1.2 核心挑战

1. **性能** - 避免不必要的重渲染
2. **可维护性** - 集中管理状态逻辑
3. **类型安全** - TypeScript 泛型支持
4. **可测试性** - 纯函数 + 可观测性

---

## 2. 核心 Store 实现

### 2.1 Store 类型

```typescript
// src/state/store.ts
export type Store<T> = {
  // 获取当前状态
  getState: () => T

  // 更新状态 (函数式)
  setState: (updater: (prev: T) => T) => void

  // 订阅状态变更
  subscribe: (listener: Listener) => () => void
}

type Listener = (state: unknown) => void
```

### 2.2 完整实现

```typescript
// src/state/store.ts (~35 行核心实现)
export function createStore<T>(
  initialState: T,
  onChange?: OnChange<T>
): Store<T> {
  // 内部状态
  let state: T = initialState

  // 监听器集合 (Set 高效去重)
  const listeners = new Set<Listener>()

  return {
    getState() {
      return state
    },

    setState(updater) {
      // 函数式更新
      const next = typeof updater === 'function'
        ? (updater as Function)(state)
        : updater

      // Memoization guard - 防止不必要的更新
      if (!Object.is(next, state)) {
        state = next

        // 通知所有监听器
        listeners.forEach(listener => listener(state))

        // 调用可选的 onChange 回调
        onChange?.(state)
      }
    },

    subscribe(listener) {
      listeners.add(listener)

      // 返回取消订阅函数
      return () => listeners.delete(listener)
    }
  }
}

// TypeScript 类型守卫
function isFunction(value: unknown): value is Function {
  return typeof value === 'function'
}
```

### 2.3 设计优势

| 特性 | 实现 | 优势 |
|------|------|------|
| **Immutable** | 总是产生新状态 | 易于追踪变化 |
| **Memoization** | `Object.is` 比较 | 避免不必要更新 |
| **高效订阅** | `Set<Listener>` | O(1) 添加/删除 |
| **类型安全** | 泛型 `Store<T>` | TypeScript 支持 |
| **可选副作用** | `onChange` 回调 | 灵活扩展 |

---

## 3. AppState 类型系统

### 3.1 AppState 概览

```typescript
// src/state/AppStateStore.ts (~22KB, ~450 行类型定义)
export type AppState = {
  // ========== 会话与 UI 状态 ==========
  settings: SettingsJson
  verbose: boolean
  mainLoopModel: ModelSetting
  mainLoopModelForSession: ModelSetting
  statusLineText: string | undefined
  expandedView: 'none' | 'tasks' | 'teammates'
  isBriefOnly: boolean
  coordinatorTaskIndex: number
  viewSelectionMode: 'none' | 'selecting-agent' | 'viewing-agent'
  footerSelection: FooterItem | null
  spinnerTip?: string

  // ========== 远程/桥接状态 ==========
  remoteSessionUrl: string | undefined
  remoteConnectionStatus: ConnectionStatus
  remoteBackgroundTaskCount: number
  replBridgeEnabled: boolean
  replBridgeConnected: boolean
  replBridgeSessionActive: boolean
  replBridgeReconnecting: boolean

  // ========== 任务状态 ==========
  tasks: { [taskId: string]: TaskState }
  agentNameRegistry: Map<string, AgentId>
  foregroundedTaskId?: string
  viewingAgentTaskId?: string  // 正在查看的 teammate transcript

  // ========== MCP/插件状态 ==========
  mcp: {
    clients: MCPServerConnection[]
    tools: Tool[]
    commands: Command[]
    resources: Record<string, ServerResource[]>
    pluginReconnectKey: number
  }
  plugins: {
    enabled: LoadedPlugin[]
    disabled: LoadedPlugin[]
    errors: PluginError[]
    installationStatus: InstallationStatus
    needsRefresh: boolean
  }

  // ========== 推测/AI 状态 ==========
  speculation: SpeculationState
  thinkingEnabled: boolean | undefined
  promptSuggestionEnabled: boolean
  promptSuggestion: PromptSuggestion | null

  // ========== 工具特定状态 ==========
  tungstenPanelVisible?: boolean
  bagelActive?: boolean
  computerUseMcpState?: ComputerUseMcpState
  replContext?: ReplContext

  // ========== 通知 ==========
  notifications: {
    current: Notification | null
    queue: Notification[]
  }

  // ========== Session Hooks ==========
  sessionHooks: Map<string, SessionHook>
}
```

### 3.2 主要状态分组

```
AppState
├── 会话状态
│    ├── settings, model, thinkingEnabled
│    └── verbose, isBriefOnly
│
├── UI 状态
│    ├── statusLineText, spinnerTip
│    ├── expandedView, footerSelection
│    └── viewSelectionMode
│
├── 远程/桥接状态
│    ├── remoteSessionUrl, remoteConnectionStatus
│    └── replBridgeEnabled, replBridgeConnected
│
├── 任务状态
│    ├── tasks, agentNameRegistry
│    ├── foregroundedTaskId, viewingAgentTaskId
│    └── coordinatorTaskIndex
│
├── MCP/插件状态
│    ├── mcp.clients, mcp.tools, mcp.resources
│    └── plugins.enabled, plugins.disabled, plugins.errors
│
├── 通知状态
│    └── notifications.current, notifications.queue
│
└── 工具特定状态
     ├── tungstenPanelVisible, bagelActive
     └── computerUseMcpState, replContext
```

---

## 4. 默认状态工厂

### 4.1 getDefaultAppState

```typescript
// src/state/AppStateStore.ts
export function getDefaultAppState(): AppState {
  return {
    // ========== 会话与 UI ==========
    settings: getDefaultSettings(),
    verbose: false,
    mainLoopModel: undefined,
    mainLoopModelForSession: undefined,
    statusLineText: undefined,
    expandedView: 'none',
    isBriefOnly: false,
    coordinatorTaskIndex: 0,
    viewSelectionMode: 'none',
    footerSelection: null,
    spinnerTip: undefined,

    // ========== 远程/桥接 ==========
    remoteSessionUrl: undefined,
    remoteConnectionStatus: 'disconnected',
    remoteBackgroundTaskCount: 0,
    replBridgeEnabled: false,
    replBridgeConnected: false,
    replBridgeSessionActive: false,
    replBridgeReconnecting: false,

    // ========== 任务 ==========
    tasks: {},
    agentNameRegistry: new Map(),
    foregroundedTaskId: undefined,
    viewingAgentTaskId: undefined,

    // ========== MCP/插件 ==========
    mcp: {
      clients: [],
      tools: [],
      commands: [],
      resources: {},
      pluginReconnectKey: 0,
    },
    plugins: {
      enabled: [],
      disabled: [],
      errors: [],
      commands: [],
      needsRefresh: false,
      installationStatus: { type: 'idle' },
    },

    // ========== 推测/AI ==========
    speculation: { status: 'idle' },
    thinkingEnabled: shouldEnableThinkingByDefault(),
    promptSuggestionEnabled: shouldEnablePromptSuggestion(),
    promptSuggestion: null,

    // ========== 通知 ==========
    notifications: {
      current: null,
      queue: [],
    },

    // ========== Session Hooks ==========
    sessionHooks: new Map(),
  }
}
```

### 4.2 辅助默认值

```typescript
// 推测是否应默认启用
function shouldEnableThinkingByDefault(): boolean {
  // 检查设置和特性开关
  return feature('THINKING_BY_DEFAULT') ?? false
}

// 提示建议是否应默认启用
function shouldEnablePromptSuggestion(): boolean {
  return feature('PROMPT_SUGGESTION') ?? true
}
```

---

## 5. React 集成

### 5.1 AppStateProvider

```typescript
// src/state/AppState.tsx
export const AppStoreContext = React.createContext<AppStateStore | null>(null)

export function AppStateProvider({
  children,
  initialState,
  onChangeAppState,
}: {
  children: React.ReactNode
  initialState?: Partial<AppState>
  onChangeAppState?: OnChange<AppState>
}) {
  // 使用 useState 创建单例 store
  // useState 的初始化函数只执行一次
  const [store] = useState(() =>
    createStore(
      { ...getDefaultAppState(), ...initialState },
      onChangeAppState
    )
  )

  // 挂载检查
  useEffect(() => {
    if (store.getState().mcp.pluginReconnectKey > 0) {
      // 禁用 bypass 模式如果远程设置在挂载前加载
      disableBypassModeIfNeeded(store)
    }
  }, [])

  // 同步外部设置变更到 AppState
  useEffect(() => {
    return useSettingsChange(onSettingsChange)
  }, [store])

  // 嵌套 Provider
  return (
    <HasAppStateContext.Provider value={true}>
      <AppStoreContext.Provider value={store}>
        <MailboxProvider>
          <VoiceProvider>
            {children}
          </VoiceProvider>
        </MailboxProvider>
      </AppStoreContext.Provider>
    </HasAppStateContext.Provider>
  )
}
```

### 5.2 useAppState Hook

```typescript
// src/state/AppState.tsx:142
/**
 * 订阅状态切片
 * 使用 useSyncExternalStore 实现 React 18 并发模式兼容
 */
export function useAppState<T>(selector: (state: AppState) => T): T {
  const store = useAppStore()

  // 获取当前选定值
  const getSnapshot = () => selector(store.getState())

  // useSyncExternalStore 确保：
  // 1. 订阅时调用 getSnapshot
  // 2. 存储变更时比较结果 (Object.is)
  // 3. 只在值变化时触发重渲染
  return useSyncExternalStore(
    store.subscribe,
    getSnapshot,
    getSnapshot  // 服务端 snapshot (同 getSnapshot)
  )
}

// 使用示例
function StatusBar() {
  const statusText = useAppState(s => s.statusLineText)
  const isConnected = useAppState(s => s.remoteConnectionStatus === 'connected')

  return (
    <Box>
      <Text>{statusText}</Text>
      {isConnected && <Text color="green">●</Text>}
    </Box>
  )
}
```

### 5.3 useSetAppState Hook

```typescript
// src/state/AppState.tsx
/**
 * 获取状态更新器 (不订阅)
 * 用于只需要更新而不需要读取状态的组件
 */
export function useSetAppState(): (
  updater: (prev: AppState) => Partial<AppState>
) => void {
  const store = useAppStore()

  // 返回 setState，但不创建订阅
  // 使用组件不会因为状态变化而重渲染
  return store.setState
}

// 使用示例
function ClearButton() {
  const setState = useSetAppState()

  const handleClear = () => {
    setState(prev => ({
      ...prev,
      tasks: {},  // 清空任务
    }))
  }

  return <Button onPress={handleClear}>Clear Tasks</Button>
}
```

### 5.4 useSyncExternalStore 优势

```typescript
// 传统 useState 的问题
const [state, setState] = useState(initial)

// 问题：如果组件只使用 state.count，
// 那么 state.obj 变化也会导致重渲染

// useAppState + selector 的优势
const count = useAppState(s => s.count)

// 问题解决：
// 1. 只有 count 变化时才重渲染
// 2. Object.is 比较防止不必要更新
// 3. React 18 并发模式兼容
```

---

## 6. 状态变更处理

### 6.1 onChangeAppState 中央处理器

```typescript
// src/state/onChangeAppState.ts
/**
 * 状态变更的中央侧效应协调器
 *
 * 问题：状态变更通常需要触发副作用：
 * - 权限模式变更 → 通知外部系统
 * - 设置变更 → 持久化到磁盘
 * - 认证变更 → 清除缓存
 *
 * 解决方案：集中处理，通过 diff 检测变更
 */
export function onChangeAppState({
  prevState,
  newState,
}: StateChange<AppState>): void {
  // ========== 1. 权限模式同步 ==========
  if (prevState.permissionMode !== newState.permissionMode) {
    const prevExternal = toExternalPermissionMode(prevState.permissionMode)
    const newExternal = toExternalPermissionMode(newState.permissionMode)

    // 同步到会话元数据
    if (prevExternal !== newExternal) {
      notifySessionMetadataChanged({
        permission_mode: newExternal,
        is_ultraplan_mode: newState.permissionMode === 'plan',
      })
    }

    // 通知权限系统
    notifyPermissionModeChanged(newState.permissionMode)
  }

  // ========== 2. 设置持久化 ==========
  // mainLoopModel 变更 → 保存到设置
  if (newState.mainLoopModel === null) {
    updateSettingsForSource('userSettings', { model: undefined })
  } else if (newState.mainLoopModel !== null) {
    updateSettingsForSource('userSettings', { model: newState.mainLoopModel })
  }

  // expandedView 变更 → 保存到全局配置
  if (newState.expandedView !== oldState.expandedView) {
    saveGlobalConfig({
      showExpandedTodos: newState.expandedView === 'tasks',
      showSpinnerTree: newState.expandedView === 'teammates',
    })
  }

  // ========== 3. 认证缓存失效 ==========
  if (newState.settings !== oldState.settings) {
    // 清除 API 密钥缓存
    clearApiKeyHelperCache()

    // 清除云厂商凭证缓存
    clearAwsCredentialsCache()
    clearGcpCredentialsCache()

    // 环境变量变更
    if (newState.settings.env !== oldState.settings.env) {
      applyConfigEnvironmentVariables()
    }
  }

  // ========== 4. MCP/插件状态变更 ==========
  if (newState.mcp.pluginReconnectKey !== oldState.mcp.pluginReconnectKey) {
    // 触发 MCP 重连
    scheduleMcpReconnect(newState.mcp.pluginReconnectKey)
  }

  if (newState.plugins.needsRefresh) {
    // 刷新插件列表
    refreshPluginList()
  }
}
```

### 6.2 权限模式同步

```typescript
// 权限模式变更通知
function notifyPermissionModeChanged(mode: PermissionMode): void {
  // 通知桥接系统
  if (appState.remoteConnectionStatus === 'connected') {
    sendBridgeMessage({
      type: 'permission_mode_changed',
      mode: toExternalPermissionMode(mode),
    })
  }

  // 通知 CLI 会话
  notifySessionMetadataChanged({
    permission_mode: toExternalPermissionMode(mode),
  })
}

function notifySessionMetadataChanged(metadata: SessionMetadata): void {
  // 通过 API 发送会话元数据更新
  apiClient.updateSessionMetadata(metadata).catch(console.error)
}
```

---

## 7. 选择器模式

### 7.1 选择器函数

```typescript
// src/state/selectors.ts
/**
 * 选择器：从状态中提取派生数据
 * 在组件中使用而不是直接访问状态
 */

// 获取当前查看的 teammate 任务
export function getViewedTeammateTask(
  appState: AppState
): InProcessTeammateTaskState | undefined {
  if (!appState.viewingAgentTaskId) {
    return undefined
  }

  const task = appState.tasks[appState.viewingAgentTaskId]

  if (!task || task.type !== 'in_process_teammate') {
    return undefined
  }

  return task as InProcessTeammateTaskState
}

// 确定用户输入应该路由到哪里
export function getActiveAgentForInput(
  appState: AppState
): InputRouting {
  // 1. 如果正在查看 teammate view，输入发送到该 teammate
  if (appState.viewingAgentTaskId) {
    const task = getViewedTeammateTask(appState)
    if (task) {
      return { type: 'viewed', task }
    }
  }

  // 2. 如果有前台任务，输入发送到该任务
  if (appState.foregroundedTaskId) {
    const task = appState.tasks[appState.foregroundedTaskId]
    if (task) {
      return { type: 'named_agent', task }
    }
  }

  // 3. 默认发送到 leader
  return { type: 'leader' }
}
```

### 7.2 使用选择器

```typescript
// 组件中使用选择器
function InputRouter() {
  const routing = useAppState(getActiveAgentForInput)

  switch (routing.type) {
    case 'leader':
      return <LeaderInput />
    case 'viewed':
      return <TeammateInput taskId={routing.task.agentId} />
    case 'named_agent':
      return <AgentInput taskId={routing.task.taskId} />
  }
}
```

---

## 8. Teammate View Helpers

### 8.1 状态转换辅助

```typescript
// src/state/teammateViewHelpers.ts
/**
 * teammate view 的状态转换辅助函数
 *
 * 问题：进入/退出 teammate view 涉及多个状态字段的变更
 * 解决：封装为单一函数，确保原子性
 */

// 进入 teammate view
export function enterTeammateView(
  taskId: string,
  setAppState: SetAppState
): void {
  setAppState(prev => ({
    ...prev,
    // 设置正在查看的 task
    viewingAgentTaskId: taskId,
    // 保留被驱逐的任务 (用于退出时恢复)
    previousForegroundedTaskId: prev.foregroundedTaskId,
  }))
}

// 退出 teammate view
export function exitTeammateView(
  setAppState: SetAppState
): void {
  setAppState(prev => {
    // 恢复之前的前台任务
    const foregroundedTaskId = prev.previousForegroundedTaskId

    // 清理 teammate view 状态
    const { previousForegroundedTaskId, ...rest } = prev

    return {
      ...rest,
      foregroundedTaskId,
      viewingAgentTaskId: undefined,
    }
  })
}

// 上下文相关的停止/解散
export function stopOrDismissAgent(
  taskId: string,
  setAppState: SetAppState
): void {
  setAppState(prev => {
    const task = prev.tasks[taskId]

    // 如果正在查看该 agent，退出 view
    const viewingAgentTaskId =
      prev.viewingAgentTaskId === taskId
        ? undefined
        : prev.viewingAgentTaskId

    // 移除任务
    const { [taskId]: _, ...remainingTasks } = prev.tasks

    return {
      ...prev,
      tasks: remainingTasks,
      viewingAgentTaskId,
    }
  })
}
```

---

## 9. 状态隔离与测试

### 9.1 创建隔离 Store

```typescript
// 用于测试
function createTestStore(initial?: Partial<AppState>): Store<AppState> {
  return createStore<AppState>({
    ...getDefaultAppState(),
    ...initial,
  })
}

// 测试示例
test('task creation updates state', async () => {
  const store = createTestStore({ tasks: {} })

  // 订阅变更
  const changes: AppState[] = []
  store.subscribe(state => changes.push(state))

  // 执行操作
  store.setState(prev => ({
    ...prev,
    tasks: {
      ...prev.tasks,
      'task-1': createTask('Test Task'),
    },
  }))

  // 验证
  expect(store.getState().tasks['task-1'].subject).toBe('Test Task')
  expect(changes).toHaveLength(1)
})
```

### 9.2 Mock AppStateProvider

```typescript
// 测试工具
function MockAppStateProvider({
  children,
  initialState,
}: {
  children: React.ReactNode
  initialState?: Partial<AppState>
}) {
  const [store] = useState(() =>
    createStore({
      ...getDefaultAppState(),
      ...initialState,
    })
  )

  return (
    <AppStoreContext.Provider value={store}>
      {children}
    </AppStoreContext.Provider>
  )
}

// 测试示例
test('component reads status', () => {
  render(
    <MockAppStateProvider
      initialState={{ statusLineText: 'Ready' }}
    >
      <StatusBar />
    </MockAppStateProvider>
  )

  expect(screen.getByText('Ready')).toBeInTheDocument()
})
```

---

## 10. 性能优化

### 10.1 避免不必要的重渲染

```typescript
// 问题：大型状态对象的任何字段变化都会触发所有订阅者的重渲染

// 解决方案 1：细粒度选择器
function Component1() {
  // 只订阅 count
  const count = useAppState(s => s.count)
  // count 变化时重渲染
}

function Component2() {
  // 只订阅 name
  const name = useAppState(s => s.name)
  // name 变化时重渲染
}

// 解决方案 2：useSyncExternalStore 的 Object.is 比较
const store = createStore({ count: 0, name: '' })

// 内部已经做了 memoization
// 只有真正变化时才会通知订阅者
```

### 10.2 批量更新

```typescript
// 问题：连续多次 setState 会导致多次重渲染

// 解决方案：批量更新
function batchUpdate(store: Store<AppState>, updates: Partial<AppState>) {
  // 外部调用者负责批量
  store.setState(prev => ({ ...prev, ...updates }))
}

// React 18 自动批量更新
function handleClick() {
  // React 18 会自动批量这些更新
  setCount(c => c + 1)
  setName('new name')
  setTasks({})
}
```

---

## 11. 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Component                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  useAppState(selector)                                    │  │
│  │                                                           │  │
│  │  const value = selector(store.getState())               │  │
│  │                                                           │  │
│  │  return useSyncExternalStore(                            │  │
│  │    store.subscribe,                                       │  │
│  │    getSnapshot,    // = () => selector(store.getState())  │  │
│  │    getSnapshot                                             │  │
│  │  )                                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AppStateStore                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  createStore<AppState>(initialState, onChange)            │  │
│  │                                                           │  │
│  │  state: AppState                                          │  │
│  │  listeners: Set<Listener>                                 │  │
│  │                                                           │  │
│  │  setState(updater):                                       │  │
│  │    next = updater(state)                                  │  │
│  │    if (!Object.is(next, state)) {                        │  │
│  │      state = next                                        │  │
│  │      listeners.forEach(l => l(state))                     │  │
│  │      onChange?.(state)                                    │  │
│  │    }                                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     onChangeAppState                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. 权限模式同步 → notifyPermissionModeChanged()           │  │
│  │  2. 设置持久化 → updateSettingsForSource()                │  │
│  │  3. 认证缓存失效 → clearApiKeyHelperCache()               │  │
│  │  4. MCP 重连 → scheduleMcpReconnect()                     │  │
│  │  5. 插件刷新 → refreshPluginList()                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

*文档版本: 2026-03-31*
