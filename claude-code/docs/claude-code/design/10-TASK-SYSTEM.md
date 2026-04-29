# Task System 任务系统架构

## 概述

Task System（任务系统）负责管理 Claude Code 中的并发长时运行操作。它提供统一的接口来追踪、监控和控制各类后台任务。

## 核心概念

### 任务类型

| 类型 | 前缀 | 描述 |
|------|------|------|
| `local_bash` | `b` | 本地 shell 命令执行 |
| `local_agent` | `a` | 本地异步 Agent（通过 AgentTool） |
| `remote_agent` | `r` | 远程 Claude.ai 会话（teleport） |
| `in_process_teammate` | `t` | 进程内队友 Agent |
| `local_workflow` | `w` | 工作流脚本（功能开关） |
| `monitor_mcp` | `m` | MCP 服务器监控（功能开关） |
| `dream` | `d` | 自动记忆整合（auto-dream） |

### 任务状态流转

```mermaid
stateDiagram-v2
    [*] --> pending: 注册任务
    pending --> running: 任务开始执行
    running --> completed: 正常完成
    running --> failed: 执行失败
    running --> killed: 被强制终止
    completed --> evicted: 满足驱逐条件
    failed --> evicted: 满足驱逐条件
    killed --> evicted: 满足驱逐条件
    evicted --> [*]
```

**终态（Terminal States）**：`completed`、`failed`、`killed`

### Task ID 格式

```
{prefix}{8位随机字符 [0-9a-z]}
```

示例：`b1a2b3c4d5e6f7g8`

- 36^8 ≈ 2.8 万亿种组合
- 前缀保持向后兼容（bash 保持 `b`）

## 架构分层

```mermaid
graph TB
    subgraph Layer1["层一：工具层 (Tool Layer)"]
        T1["TaskCreateTool"]
        T2["TaskOutputTool"]
        T3["TaskStopTool"]
        T4["TaskListTool"]
    end

    subgraph Layer2["层二：任务实现层 (Implementation Layer)"]
        I1["LocalShellTask"]
        I2["LocalAgentTask"]
        I3["RemoteAgentTask"]
        I4["InProcessTeammateTask"]
        I5["DreamTask"]
    end

    subgraph Layer3["层三：框架层 (Framework Layer)"]
        F1["registerTask"]
        F2["updateTaskState"]
        F3["pollTasks"]
        F4["evictTerminalTask"]
        F5["stopTask"]
    end

    subgraph Layer4["层四：状态层 (State Layer)"]
        S1["AppState.tasks"]
        S2["磁盘输出文件"]
    end

    T1 --> I1
    T1 --> I2
    T1 --> I3
    T1 --> I4
    T1 --> I5

    I1 --> F1
    I2 --> F1
    I3 --> F1
    I4 --> F1
    I5 --> F1

    F1 --> S1
    F3 --> S2
```

### 各层职责

| 层级 | 职责 | 关键组件 |
|------|------|----------|
| **工具层** | 提供用户交互接口 | TaskCreateTool、TaskOutputTool、TaskStopTool |
| **任务实现层** | 具体任务类型的生命周期管理 | 各种 Task 实现类 |
| **框架层** | 通用框架逻辑：注册、更新、轮询、驱逐 | framework.ts |
| **状态层** | 持久化和内存状态管理 | AppState.tasks、磁盘文件 |

## 核心接口

### Task 基类 (`src/Task.ts`)

```typescript
// 任务注册表条目 - 仅 kill() 为多态调用
interface Task {
  name: string
  type: TaskType
  kill(taskId: string, setAppState: SetAppState): Promise<void>
}

// 所有任务状态共享的基类字段
interface TaskStateBase {
  id: string
  type: TaskType
  status: TaskStatus
  description: string
  toolUseId?: string
  startTime: number
  endTime?: number
  totalPausedMs?: number
  outputFile: string      // 磁盘输出路径
  outputOffset: number   // 增量读取偏移
  notified: boolean       // 用户是否已通知
}
```

### 任务状态存储

任务存储在 `AppState.tasks` 中：

```typescript
interface AppState {
  tasks: Record<string, TaskState>
}
```

### 框架函数 (`src/utils/task/framework.ts`)

| 函数 | 用途 |
|------|------|
| `registerTask(task, setAppState)` | 添加新任务到 AppState |
| `updateTaskState<T>(taskId, setAppState, updater)` | 类型安全的 state 更新 |
| `pollTasks(getAppState, setAppState)` | 主轮询循环（每 1 秒） |
| `evictTerminalTask(taskId, setAppState)` | 移除已完成的任务 |
| `generateTaskAttachments(state)` | 生成推送通知 |
| `applyTaskOffsetsAndEvictions(...)` | 应用轮询结果 |

## 轮询机制

```mermaid
sequenceDiagram
    participant Timer as 定时器 (1s)
    participant Poll as pollTasks()
    participant Disk as 磁盘输出
    participant State as AppState
    participant Notify as enqueueTaskNotification()

    Timer->>Poll: 每秒触发
    Poll->>Disk: 读取任务输出文件
    Poll->>Poll: generateTaskAttachments()
    Note over Poll: 检查新输出、跟踪偏移<br/>识别终态任务
    Poll->>State: applyTaskOffsetsAndEvictions()
    Note over State: 更新偏移量<br/>移除已完成任务
    Poll->>Notify: enqueueTaskNotification()
    Notify->>Notify: 发送 XML 通知到队列
```

## 任务实现详解

### 1. LocalShellTask (`local_bash`)

**状态：** `LocalShellTaskState`

```typescript
{
  type: 'local_bash'
  command: string
  result?: { code: number; interrupted: boolean }
  shellCommand: ShellCommand | null
  isBackgrounded: boolean
  agentId?: AgentId  // 派生此任务的父 Agent
  kind?: 'bash' | 'monitor'
}
```

**关键文件：**
- `src/tasks/LocalShellTask/LocalShellTask.tsx` - 主实现
- `src/tasks/LocalShellTask/guards.ts` - 状态类型 + 守卫函数
- `src/tasks/LocalShellTask/killShellTasks.ts` - 终止逻辑

### 2. LocalAgentTask (`local_agent`)

**状态：** `LocalAgentTaskState`

```typescript
{
  type: 'local_agent'
  agentId: string
  prompt: string
  selectedAgent?: AgentDefinition
  agentType: string
  model?: string
  abortController?: AbortController
  error?: string
  result?: AgentToolResult
  progress?: AgentProgress
  messages?: Message[]
  isBackgrounded: boolean
  retain: boolean       // UI 是否保留此任务
  diskLoaded: boolean   // Bootstrap 是否完成
  evictAfter?: number   // 面板宽限期截止时间
}
```

**进度追踪：**

```typescript
interface AgentProgress {
  toolUseCount: number
  tokenCount: number
  lastActivity?: ToolActivity
  recentActivities?: ToolActivity[]
  summary?: string
}
```

### 3. RemoteAgentTask (`remote_agent`)

**状态：** `RemoteAgentTaskState`

```typescript
{
  type: 'remote_agent'
  remoteTaskType: RemoteTaskType  // 'remote-agent' | 'ultraplan' | 'ultrareview' | 'autofix-pr' | 'background-pr'
  remoteTaskMetadata?: RemoteTaskMetadata
  sessionId: string
  command: string
  title: string
  todoList: TodoList
  log: SDKMessage[]
  isLongRunning?: boolean
  pollStartedAt: number
  isRemoteReview?: boolean
  reviewProgress?: { stage?: 'finding' | 'verifying' | 'synthesizing'; bugsFound/Verified/Refuted: number }
  isUltraplan?: boolean
  ultraplanPhase?: Exclude<UltraplanPhase, 'running'>
}
```

**特性：**
- 通过 `pollRemoteSessionEvents()` 轮询远程会话事件
- 支持不同远程任务类型的完成检查器
- 元数据持久化到会话 sidecar

### 4. InProcessTeammateTask (`in_process_teammate`)

**状态：** `InProcessTeammateTaskState`

```typescript
{
  type: 'in_process_teammate'
  identity: TeammateIdentity  // agentId, agentName, teamName, color, planModeRequired, parentSessionId
  prompt: string
  model?: string
  selectedAgent?: AgentDefinition
  abortController?: AbortController
  currentWorkAbortController?: AbortController  // 中止当前轮次但不终止任务
  awaitingPlanApproval: boolean
  permissionMode: PermissionMode
  error?: string
  result?: AgentToolResult
  progress?: AgentProgress
  messages?: Message[]
  inProgressToolUseIDs?: Set<string>
  pendingUserMessages: string[]
  isIdle: boolean
  shutdownRequested: boolean
}
```

**消息 UI 上限：** `TEAMMATE_MESSAGES_UI_CAP = 50`

### 5. DreamTask (`dream`)

**用途：** 记忆整合子 Agent（auto-dream）

**状态：** `DreamTaskState`

```typescript
{
  type: 'dream'
  phase: 'starting' | 'updating'
  sessionsReviewing: number
  filesTouched: string[]  // 不完整 - bash 写入未被捕获
  turns: DreamTurn[]        // 折叠了 toolUseCount 的 Assistant 响应
  abortController?: AbortController
  priorMtime: number        // 用于 kill 时回滚锁
}
```

**UI 展示：** 在底部药丸和 Shift+Down 对话框中可见forked dream agent

## 停止任务

```mermaid
sequenceDiagram
    participant Caller as 调用者
    participant Stop as stopTask()
    participant Validate as 验证逻辑
    participant Registry as Task Registry
    participant Kill as task.kill()
    participant Bash as Bash特殊处理

    Caller->>Stop: stopTask(taskId)
    Stop->>Validate: 检查任务存在且running
    alt 任务不存在
        Validate-->>Stop: return { error: 'not_found' }
    end
    alt 任务不在running状态
        Validate-->>Stop: return { error: 'not_running' }
    end
    Stop->>Registry: getTaskByType(task.type)
    alt 不支持的类型
        Registry-->>Stop: return { error: 'unsupported_type' }
    end
    Stop->>Kill: taskImpl.kill(taskId, setAppState)
    alt 是bash任务
        Kill->>Bash: 抑制"exit code 137"噪音
        Bash-->>Kill: emit SDK event
    end
    Kill-->>Stop: void
    Stop-->>Caller: StopTaskResult
```

## 输出管理

### 磁盘输出 (`src/utils/task/diskOutput.ts`)

```
~/.claude/memory/{sessionId}/task_output/{taskId}
```

- 每个任务输出到专用文件
- 通过偏移量跟踪增量输出
- 为 agent 转录路径创建符号链接

### 通知格式

```xml
<task_notification>
  <task_id>b1a2b3c4</task_id>
  <tool_use_id>...</tool_use_id>
  <task_type>local_bash</task_type>
  <output_file>/path/to/output</output_file>
  <status>completed</status>
  <summary>Task "npm test" completed successfully</summary>
</task_notification>
```

## 后台任务检测

```mermaid
flowchart TD
    A["isBackgroundTask(task)"] --> B{"task.status"}
    B -->|"不是 running 或 pending"| E["return false"]
    B -->|"是 running 或 pending"| C{"'isBackgrounded' in task"}
    C -->|"是"| D{"task.isBackgrounded === false"}
    D -->|"是"| E
    D -->|"否"| F["return true"]
    C -->|"否"| F
```

## 任务生命周期完整流程

```mermaid
flowchart TD
    Start(["[*] 创建任务"]) --> Register["registerTask() 注册"]
    Register --> Pending["pending 等待调度"]
    Pending --> Running["running 执行中"]
    Running --> Completed{completed}
    Running --> Failed{failed}
    Running --> Killed{killed}
    Completed --> Notified["notified = true"]
    Failed --> Notified
    Killed --> Notified
    Notified --> Evictable{"可驱逐?<br/>retain !== true<br/>或 evictAfter > now"}
    Evictable -->|"是"| Evicted(["[*] 驱逐"])
    Evictable -.->|"否"| Evictable

    Pending:::pendingStyle
    Running:::runningStyle
    Evictable:::evictableStyle

    classDef pendingStyle fill:#f9f,stroke:#333
    classDef runningStyle fill:#ff9,stroke:#333
    classDef evictableStyle fill:#9f9,stroke:#333
```

**驱逐规则：**
1. 必须是终态（`completed` | `failed` | `killed`）
2. 必须 `notified=true`
3. 不能被保留（`retain !== true` 或 `evictAfter > now`）

## 面板宽限期

```mermaid
flowchart LR
    subgraph 任务完成时刻
        C["status='completed'<br/>retain=false<br/>evictAfter=now+30s"]
    end

    subgraph 0-30秒[宽限期 30 秒]
        V1["面板可见<br/>可查看结果"]
    end

    subgraph 30秒后[30 秒后]
        V2["可驱逐"]
    end

    C --> V1 --> V2

    style C fill:#90EE90
    style V1 fill:#FFE4B5
    style V2 fill:#FFB6C1
```

- **LocalAgentTask：** `PANEL_GRACE_MS = 30_000`（30 秒）
  - 让完成的 agent 在协调器面板中短暂可见
  - 允许用户在看结果前看到结果

- **DreamTask：** 通知后立即驱逐（仅 UI）

## 关键设计模式

### 1. 类型安全的 State 更新

```typescript
updateTaskState<LocalAgentTaskState>(taskId, setAppState, task => ({
  ...task,
  status: 'completed',
  endTime: Date.now()
}))
```

### 2. 引用相等优化

```typescript
const updated = updater(task)
if (updated === task) {
  return prev  // 跳过展开 - 无状态变化
}
```

### 3. TOCTOU 保护

```typescript
// 异步操作后重新检查 fresh state 上的状态
if (fresh?.status === 'running') {
  newTasks[id] = { ...fresh, outputOffset: updatedTaskOffsets[id]! }
}
```

### 4. 任务保留模式

```mermaid
sequenceDiagram
    participant UI as UI组件
    participant State as AppState

    UI->>State: enterTeammateView()
    Note over State: retain: true<br/>evictAfter: undefined

    State-->>UI: 任务保留在面板

    UI->>State: exitTeammateView()
    Note over State: retain: false<br/>evictAfter: now + PANEL_GRACE_MS

    Note over State: 30秒后可驱逐
```

## 任务创建到驱逐完整时序

```mermaid
sequenceDiagram
    participant User as 用户
    participant Tool as TaskCreateTool
    participant Task as LocalShellTask
    participant Reg as registerTask()
    participant State as AppState
    participant Poll as pollTasks()
    participant Disk as 磁盘输出
    participant Notify as 通知系统

    User->>Tool: 创建 bash 任务
    Tool->>Task: new LocalShellTask()
    Task->>Reg: registerTask(task, setAppState)
    Reg->>State: AppState.tasks[taskId] = taskState
    State-->>User: 任务已创建，返回 taskId

    loop 每秒轮询
        Poll->>Disk: 读取输出文件
        Poll->>Poll: 检查状态变化
        alt 任务完成
            Poll->>Notify: enqueueTaskNotification()
            Notify-->>User: 通知用户
        end
    end

    User->>Tool: stopTask(taskId)
    Tool->>Task: kill()
    Task->>State: 更新为 killed 状态
    Poll->>State: 下一次轮询检测到killed
    Poll->>Notify: 通知用户任务已终止
```

## 相关文件

| 文件 | 用途 |
|------|------|
| `src/Task.ts` | 核心类型、ID 生成 |
| `src/tasks.ts` | 任务注册表（getAllTasks, getTaskByType） |
| `src/tasks/types.ts` | 联合类型、isBackgroundTask 守卫 |
| `src/tasks/stopTask.ts` | 任务停止逻辑 |
| `src/tasks/LocalMainSessionTask.ts` | 主会话后台化 |
| `src/utils/task/framework.ts` | 核心框架函数 |
| `src/utils/task/diskOutput.ts` | 任务输出磁盘 I/O |
| `src/tools/TaskCreateTool/` | 创建任务的工具 |
| `src/tools/TaskOutputTool/` | 读取任务输出的工具 |

## 功能开关

| 开关 | 任务类型 | 描述 |
|------|---------|------|
| `WORKFLOW_SCRIPTS` | `local_workflow` | 启用工作流脚本 |
| `MONITOR_TOOL` | `monitor_mcp` | 启用 MCP 服务器监控 |
