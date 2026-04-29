# Interview Guide 面试指南

---

## 一、Task 任务体系

Claude Code 的 Task 模块是整个 Agent 系统的执行基础设施，负责管理所有后台任务的创建、执行、追踪、通知与回收。

### 1.1 任务执行模式

**前后台双模式：**

- **Foreground 任务**：Main Agent 在当前 turn 内等待执行，通过 `yield` 实时返回中间结果，协程而非线程
- **Background 任务**：`void` 机制启动立即返回，Main Agent 无需等待，真正实现并行执行

```typescript
// Background 关键实现
void runWithAgentContext(
  asyncAgentContext,
  () => runAsyncAgentLifecycle({...})
)
return { status: 'async_launched' }  // 立即返回，不等待
```

### 1.2 任务生命周期

**完整状态流转：**

```
pending → running → completed/failed/killed → evicted
```

| 状态 | 说明 |
|------|------|
| `pending` | 任务已注册，等待执行 |
| `running` | 任务执行中 |
| `completed` | 正常完成 |
| `failed` | 执行失败 |
| `killed` | 被强制终止 |
| `evicted` | 从内存驱逐 |

**TaskStateBase 核心字段：**

```typescript
{
  id: string,              // Task ID = Agent ID
  type: TaskType,          // local_bash / local_agent / in_process_teammate / remote_agent
  status: TaskStatus,
  description: string,
  startTime: number,
  endTime?: number,
  outputOffset: number,    // 增量读取偏移
  notified: boolean,        // 是否已发送通知
}
```

### 1.3 任务持久化

**内存与磁盘分离：**

| 存储 | 位置 | 生命周期 |
|------|------|----------|
| 内存状态 | `AppState.tasks` | Session 结束消失 |
| 磁盘输出 | `{project}/.claude/tmp/{sessionId}/tasks/` | 持久化 |

**outputOffset 增量读取：**

```typescript
// 每次 poll 只读取新增内容，避免重复
getTaskOutputDelta(taskId, outputOffset)
```

### 1.4 任务进度追踪

**pollTasks() 每秒轮询机制：**

```typescript
// utils/task/framework.ts
export async function pollTasks(
  getAppState: () => AppState,
  setAppState: SetAppState,
): Promise<void> {
  // 1. 读取磁盘输出增量
  // 2. 更新 outputOffset
  // 3. 识别终态任务
  // 4. 发送通知
}
```

**进度更新：**

```typescript
updateAgentProgress(taskId, {
  toolUseCount: number,
  tokenCount: number,
  lastActivity: number,
})
```

### 1.5 任务通知机制

**XML Task Notification：**

```xml
<task_notification>
  <task_id>a1b2c3d4e5f6g7h8</task_id>
  <status>completed</status>
  <summary>Agent "xxx" completed</summary>
  <result>SubAgent 最终输出</result>
  <usage>
    <total_tokens>1234</total_tokens>
  </usage>
</task_notification>
```

**通知流程：**

```
completeAgentTask() → enqueueAgentNotification() → enqueuePendingNotification()
                                                    ↓
                              Main Agent 下次 query 轮询时 dequeue 获取
```

### 1.6 任务依赖管理

**blockedBy / blocks 依赖声明：**

```typescript
// 只有 blockedBy 中所有任务都 completed 时才能认领
const unresolvedTaskIds = new Set(
  allTasks.filter(t => t.status !== 'completed').map(t => t.id)
)
const blockedByTasks = task.blockedBy.filter(id => unresolvedTaskIds.has(id))
if (blockedByTasks.length > 0) {
  return { success: false, reason: 'blocked', blockedByTasks }
}
```

### 1.7 任务资源回收

**30s 面板宽限期：**

```
任务完成 → notified=true → 等待 30s → evicted=true → 从内存移除
```

```typescript
// PANEL_GRACE_MS = 30000
evictAfter: Date.now() + PANEL_GRACE_MS
```

### 1.8 任务注册调度

**Task ID 生成规则：**

```
{prefix}{8位随机字符 [0-9a-z]}
36^8 ≈ 2.8 万亿种组合
```

| 前缀 | 类型 |
|------|------|
| `b` | local_bash |
| `a` | local_agent |
| `r` | remote_agent |
| `t` | in_process_teammate |
| `w` | local_workflow |
| `m` | monitor_mcp |
| `d` | dream |

---

## 二、Agent 编排体系

### 2.1 三种编排模式

| 模式 | Main Agent 角色 | 通信机制 | 适用场景 |
|------|-----------------|----------|----------|
| **Single Agent** | 唯一执行者 | 无 | 简单独立任务 |
| **Main+SubAgent** | 启动者+结果接收者 | XML Notification | 后台长时任务 |
| **Coordinator** | 纯协调者 | File Mailbox + SendMessage | 多步骤协作 |

### 2.2 Main+SubAgent vs Coordinator

| 维度 | Main+SubAgent | Coordinator |
|------|---------------|-------------|
| Main Agent 角色 | 执行者+接收者 | 纯协调者（不执行任务） |
| 任务分发 | 启动时确定 prompt | 动态通过 SendMessage |
| 继续任务 | Main Agent 直接处理 | 必须 SendMessage 给 Worker |
| Worker 类型 | SubAgent | 也是 SubAgent（但通过 team_name 触发） |

### 2.3 Foreground vs Background SubAgent

| 维度 | Foreground | Background |
|------|------------|------------|
| Main Agent 等待？ | ✅ 是 | ❌ 否（void 启动） |
| 实现方式 | `for await (const msg of runAgent())` | `void runAsyncAgentLifecycle()` |
| 结果传递 | yield 实时返回 | XML Notification |

---

## 三、关键技术点

### 3.1 async generator vs 线程

| 维度 | 线程 | async generator (SubAgent) |
|------|------|----------------------------|
| 调度方式 | 抢占式 (OS) | 协作式 (事件循环) |
| 堆栈 | 独立堆栈 | 共享堆栈 |
| 创建开销 | 大 (KB~MB) | 极小 |
| 并行性 | 真正并行 | 假并行（单线程） |

**SubAgent 之所以不阻塞，是因为大量 `await` 操作（API 调用、文件读写、命令执行）自然让出事件循环。**

### 3.2 XML vs JSON 通知格式

**选择 XML 的原因：**

1. **特殊字符无需转义**：`<>` 不与对话内容冲突
2. **标签边界清晰**：易于在纯文本流中定位
3. **格式统一**：Claude Code 统一使用 XML（teammate、bash、command）

### 3.3 File Mailbox vs 内存队列

**选择 File Mailbox 的原因：**

1. **无需外部依赖**：不依赖 Redis 等外部服务
2. **天然持久化**：team 信息存储在文件系统
3. **跨进程共享**：适合 CLI 环境的进程间通信

---

## 四、常见面试问题

### Q1: SubAgent 是线程还是协程？

**答**：SubAgent 是协程（async generator），不是线程。它通过 `runAgent()` 返回一个 `AsyncGenerator<Message>`，在主事件循环中协作执行，不是独立的 OS 线程。

### Q2: Background SubAgent 如何做到不阻塞 Main Agent？

**答**：Background SubAgent 使用 `void runAsyncAgentLifecycle()` 启动，不 `await` 结果，立即返回。SubAgent 的执行通过 `enqueueAgentNotification()` 发送 XML 通知，Main Agent 在下次 query 轮询时获取。

### Q3: Task ID 和 Agent ID 是什么关系？

**答**：Task ID 和 Agent ID 一一对应，`id === agentId`。这种设计简化了状态管理，每个 SubAgent 有一个对应的 Task 状态，通过 `AppState.tasks[agentId]` 统一管理。

### Q4: 任务完成通知为什么用 XML 而不是 JSON？

**答**：XML 因为「特殊字符无需转义 + 标签边界清晰 + 格式统一」被采用。任务通知需要跨 query 循环传递，在纯文本流中 XML 标签更易于定位和解析。

### Q5: Coordinator 和 Main+SubAgent 的核心区别？

**答**：Coordinator 模式下 Main Agent 变成纯协调者，不执行具体任务。Main+SubAgent 模式下 Main Agent 自己执行也启动 SubAgent 帮忙。Coordinator 通过 `SendMessage` 动态分发任务，Main+SubAgent 在启动时就确定 prompt。

### Q6: 任务 30s 宽限期的作用？

**答**：`PANEL_GRACE_MS = 30000ms`，任务完成后 30s 内面板可见，用户可以查看结果。30s 后 `evictTerminalTask()` 自动从内存驱逐，释放空间。

### Q7: blockedBy 和 blocks 的区别？

**答**：`blockedBy` 表示「被谁阻塞」，`blocks` 表示「阻塞谁」。A 的 `blockedBy` 包含 B，等价于 B 的 `blocks` 包含 A。`claimTask()` 检查 `blockedBy` 依赖是否都完成。