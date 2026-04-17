# 上下文与记忆系统设计文档

> 本文档解析 Claude Code 中上下文（Context）与记忆（Memory）系统的完整架构设计、核心实现和数据流。

---

## 1. 系统概述

Claude Code 的上下文与记忆系统负责**在对话生命周期内和跨对话场景下保持状态与知识**。系统分为两个正交维度：

| 维度 | 作用范围 | 核心问题 |
|------|----------|----------|
| **上下文（Context）** | 单次对话内 | 如何在每次请求中注入会话级信息（git status、日期等） |
| **记忆（Memory）** | 跨对话持久化 | 如何让 AI 在未来对话中"记住"用户偏好、项目上下文 |

两者都通过 system prompt 注入给模型，但服务于不同的时间尺度。

---

## 2. 上下文系统（Context）

### 2.1 核心架构

```
getSystemContext()     → git status, cache breaker（会话级快照）
getUserContext()       → claude.md files, 当前日期（用户级上下文）
```

**文件位置：** `src/context.ts`

### 2.2 getSystemContext

提供**会话启动时的快照**，包含：

```typescript
// src/context.ts
export const getSystemContext = memoize(async () => {
  const gitStatus = await getGitStatus()  // git branch, status, recent commits
  const injection = getSystemPromptInjection()  // cache breaker（ant-only）

  return {
    gitStatus: "...",      // 完整的 git status 快照
    cacheBreaker: "...",  // [CACHE_BREAKER: ...]
  }
})
```

**关键特性：**
- `memoize` 缓存：整个对话周期内只计算一次
- 跳过条件：CCR（远程会话）或禁用了 git instructions
- Git status 截断：超过 2000 字符则截断并提示用户使用 BashTool

### 2.3 getUserContext

提供**用户级上下文**，通过 `claudemd.ts` 的 `getClaudeMds()` 加载：

```typescript
export const getUserContext = memoize(async () => {
  const claudeMd = getClaudeMds(filterInjectedMemoryFiles(await getMemoryFiles()))

  return {
    claudeMd: "...",     // CLAUDE.md 文件内容
    currentDate: "Today's date is YYYY-MM-DD",
  }
})
```

**禁用条件：**
- `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`（硬关闭）
- `--bare` 模式且没有显式 `--add-dir`

### 2.4 上下文注入时机

```
用户消息到达
    ↓
systemPromptSection('memory') → getClaudeMds()      → claude.md 内容
systemPromptSection('context') → getSystemContext()  → git status + date
systemPromptSection('user')    → getUserContext()    → 当前日期
    ↓
合并到 system prompt → 模型处理
```

### 2.5 上下文压缩（Context Compression / Compaction）

当对话过长超出模型上下文窗口时，系统通过**压缩（Compaction）**机制将历史消息汇总为摘要，释放上下文空间。

#### 2.5.1 压缩类型

| 类型 | 触发方式 | 描述 |
|------|----------|------|
| **Auto Compact** | 自动触发 | 当 token 使用超过阈值时自动执行 |
| **Manual Compact** | `/compact` 命令 | 用户显式触发 |
| **Session Memory Compact** | 实验性 | 优先尝试，保留 session memory 内容 |
| **Micro Compact** | 实时 | 渐进式清理工具输出中的重复内容 |

#### 2.5.2 触发阈值

```typescript
// src/services/compact/autoCompact.ts
export const AUTOCOMPACT_BUFFER_TOKENS = 13_000
export const WARNING_THRESHOLD_BUFFER_TOKENS = 20_000
export const ERROR_THRESHOLD_BUFFER_TOKENS = 20_000
export const MANUAL_COMPACT_BUFFER_TOKENS = 3_000

// 有效上下文窗口 = 模型上下文窗口 - 保留给 summary 输出的 tokens
export function getEffectiveContextWindowSize(model: string): number {
  const contextWindow = getContextWindowForModel(model)
  return contextWindow - MAX_OUTPUT_TOKENS_FOR_SUMMARY  // 20,000
}
```

**阈值计算：**
```
自动压缩阈值 = 有效上下文窗口 - 13,000 (buffer)
警告阈值 = 有效上下文窗口 - 20,000
错误阈值 = 有效上下文窗口 - 20,000
阻塞限制 = 有效上下文窗口 - 3,000
```

#### 2.5.3 压缩流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     shouldAutoCompact()                            │
│  检查 tokenCount >= autoCompactThreshold                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
         ┌────────────────────────────────────────┐
         │  trySessionMemoryCompact() [实验性]      │
         │  - 优先尝试，保留 session memory       │
         │  - 如果成功，跳过 legacy compaction    │
         └────────────────────────────────────────┘
                              │
                              ▼ (fallback)
┌─────────────────────────────────────────────────────────────────┐
│                    compactConversation()                           │
│                                                                  │
│  1. stripImagesFromMessages()     — 移除图片（节省 token）        │
│  2. stripReinjectedAttachments() — 移除重复注入的附件类型         │
│  3. groupMessagesByApiRound()     — 按 API 调用分组              │
│  4. 调用 Sonnet 生成摘要          — 保留 <analysis> 草稿         │
│  5. formatCompactSummary()        — 剥离 analysis，格式化         │
│  6. 创建 CompactBoundaryMessage    — 标记压缩点                   │
│  7. runPostCompactCleanup()       — 清理、重置缓存基线            │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.5.4 摘要格式

```typescript
// src/services/compact/prompt.ts
// 压缩摘要必须包含 9 个部分：

<summary>
1. Primary Request and Intent:
   — 用户原始请求和意图

2. Key Technical Concepts:
   — 关键技术概念、框架

3. Files and Code Sections:
   — 文件路径、修改内容、代码片段

4. Errors and fixes:
   — 错误及修复方法

5. Problem Solving:
   — 问题解决和正在进行的故障排查

6. All user messages:
   — 所有非工具结果的用户消息

7. Pending Tasks:
   — 待处理任务

8. Current Work:
   — 当前正在做的工作

9. Optional Next Step:
   — 下一步（仅当与最近用户请求直接相关时）
</summary>
```

**注意：** `<analysis>` 块是起草草稿，不出现在最终摘要中。

#### 2.5.5 上下文分析

```typescript
// src/utils/contextAnalysis.ts
export function analyzeContext(messages: Message[]): TokenStats {
  // 返回结构：
  {
    toolRequests: Map<string, number>,     // 各工具的请求 token 数
    toolResults: Map<string, number>,       // 各工具结果的 token 数
    humanMessages: number,                 // 用户消息 token
    assistantMessages: number,             // 助手消息 token
    localCommandOutputs: number,           // 本地命令输出 token
    duplicateFileReads: Map<string, {      // 重复读取同一文件的统计
      count: number,
      tokens: number
    }>,
    total: number
  }
}
```

**重复文件读取检测：**
- 多次读取同一文件的 token 开销被标记
- 可用于 micro compact 优化

#### 2.5.6 Circuit Breaker

```typescript
// 连续 3 次压缩失败后停止重试
const MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3
```

防止在上下文已无法恢复时（`prompt_too_long`）浪费 API 调用。

---

## 3. 记忆系统（Memory）

### 3.1 记忆类型分类

Claude Code 采用**封闭四类记忆 taxonomy**，明确区分哪些信息值得保存：

| 类型 | 用途 | 作用域 | 示例 |
|------|------|--------|------|
| `user` | 用户角色、目标、偏好 | 始终 private | "用户是数据科学家，专注可观测性" |
| `feedback` | 用户的纠正与确认 | 优先 team | "不要 mock 数据库，曾因此出问题" |
| `project` | 项目目标、截止、决策原因 | 优先 team | "周三开始 merge freeze，因为 mobile 发版" |
| `reference` | 外部系统指针 | 通常 team | "Linear 项目 INGEST 跟踪所有 pipeline bug" |

**明确不保存的内容：**
- 代码模式、架构、文件路径（可从代码派生）
- Git 历史（`git log` / `git blame` 是权威来源）
- 调试方案（fix 在代码中，commit message 有上下文）
- CLAUDE.md 中已有的内容
- 临时任务细节

### 3.2 记忆存储架构

```
~/.claude/
├── memory/                          # Auto Memory（自动记忆）
│   ├── MEMORY.md                     # 记忆索引（入口文件）
│   ├── user_role.md                  # 主题记忆文件
│   ├── feedback_testing.md
│   └── logs/YYYY/MM/YYYY-MM-DD.md   # 日常日志（KAIROS 模式）
│
└── projects/<sanitized-cwd>/memory/  # 项目级自动记忆
    ├── MEMORY.md
    └── ...

~/.claude/projects/<slug>/memory/     # 实际路径结构
```

**路径解析优先级：**
1. `CLAUDE_COWORK_MEMORY_PATH_OVERRIDE`（Cowork 显式覆盖）
2. `settings.json` 中的 `autoMemoryDirectory`
3. `<memoryBase>/projects/<sanitized-git-root>/memory/`

### 3.3 记忆文件格式

```markdown
---
name: user_role
description: user is a data scientist focused on observability/logging
type: user
---

# 记忆内容

用户是数据科学家，专注于可观测性和日志系统。
对于这类问题，应该用专业术语回答，不需要解释基础概念。
**Why:** 用户明确表示需要深入技术讨论。
**How to apply:** 当用户询问日志或追踪相关问题时，直接给出专业方案。
```

**索引机制（MEMORY.md）：**
```markdown
# auto memory

- [user_role](user_role.md) — user is a data scientist focused on observability
- [feedback_testing](feedback_testing.md) — don't mock the database
```

- 索引最多 200 行，超出截断
- 每个条目限制在 ~150 字符以内
- 内容放在主题文件中，不直接写入索引

### 3.4 记忆召回（Recall）

当用户询问或 AI 主动触发时，通过 `findRelevantMemories()` 召回相关记忆：

```typescript
// src/memdir/findRelevantMemories.ts
export async function findRelevantMemories(
  query: string,
  memoryDir: string,
  signal: AbortSignal,
  recentTools: readonly string[] = [],
  alreadySurfaced: ReadonlySet<string> = new Set(),
): Promise<RelevantMemory[]>
```

**召回流程：**
1. 扫描记忆目录，读取所有 `.md` 文件的 frontmatter（`scanMemoryFiles`）
2. 构建 manifest：`- [type] filename (timestamp): description`
3. 调用 Sonnet 模型选择最相关的最多 5 个记忆
4. 排除已 surfaced 的记忆，避免重复

**选择提示词（SELECT_MEMORIES_SYSTEM_PROMPT）摘要：**
- 只选择**明确有帮助**的记忆，不确定则不选
- 如果没有相关记忆，返回空列表
- 近期使用的工具的参考文档**不选择**，但警告/注意事项**仍然选择**

### 3.5 信任记忆的指导原则

```typescript
// src/memdir/memoryTypes.ts
TRUSTING_RECALL_SECTION = [
  "## Before recommending from memory",
  "A memory that names a specific function, file, or flag is a claim that it existed *when the memory was written*. It may have been renamed, removed, or never merged.",
  "- If the memory names a file path: check the file exists.",
  "- If the memory names a function or flag: grep for it.",
  "- If the user is about to act on your recommendation, verify first.",
  '"The memory says X exists" is not the same as "X exists now."'
]
```

**记忆漂移警告（MEMORY_DRIFT_CAVEAT）：**
> Memory records can become stale over time. Before answering based solely on memory, verify that the memory is still correct and up-to-date by reading the current state of the files.

---

## 4. CLAUDE.md 文件加载

### 4.1 加载顺序与优先级

```typescript
// src/utils/claudemd.ts
// 加载顺序（后面的优先级更高）

// 1. Managed（全局策略，来自 /etc/claude-code/）
// 2. User（用户全局，~/.claude/CLAUDE.md）
// 3. Project（项目级，从 CWD 向上遍历到根）
// 4. Local（本地私有，CLAUDE.local.md，不提交到 git）
```

### 4.2 完整的文件发现机制

```typescript
// 1. Managed
~/.claude-code/CLAUDE.md
/etc/claude-code/CLAUDE.md

// 2. User
~/.claude/CLAUDE.md
~/.claude/rules/*.md

// 3. Project（从 CWD 向上遍历）
./CLAUDE.md
./.claude/CLAUDE.md
./.claude/rules/*.md

// 4. Local
./CLAUDE.local.md

// 5. Auto Memory
~/.claude/projects/<slug>/memory/MEMORY.md
```

### 4.3 @include 指令

```markdown
<!-- 在 CLAUDE.md 中 -->
有关 React 的内容参考 @./docs/react-guidelines.md
有关 Python 的内容参考 @~/notes/python.md
```

**支持格式：**
- `@path` — 相对路径（相对于当前文件）
- `@./relative/path` — 显式相对路径
- `@~/home/path` — 用户主目录路径
- `@/absolute/path` — 绝对路径

**限制：**
- 最多 5 层深度
- 仅在文本节点中处理（代码块内不处理）
- 二进制文件（图片、PDF）被跳过

### 4.4 frontmatter paths（条件规则）

```markdown
---
name: python-style-guide
description: Python 项目代码风格规则
type: project
paths:
  - src/**/*.py
  - tests/**/*.py
---

# Python Style Guide
```

这些规则只在该路径下的文件被编辑时加载。

---

## 6. Team Memory（团队记忆）

### 5.1 架构

```
Auto Memory                      Team Memory
~/.claude/projects/.../memory/   ~/.claude/projects/.../memory/team/
├── MEMORY.md                     ├── MEMORY.md（共享索引）
├── user_role.md
└── ...
```

### 5.2 同步机制

- Team memory 是 auto memory 的子目录
- 所有团队成员共享 `team/` 目录下的记忆
- 需要 `tengu_herring_clock` feature flag

---

## 7. KAIROS 日常日志模式

### 6.1 概念

对于长生命周期会话，采用**追加日志**而非维护索引：

```
记忆写入 → 追加到今天的日志文件
           logs/YYYY/MM/YYYY-MM-DD.md

夜间 /dream skill → 将日志蒸馏到主题文件 + MEMORY.md
```

### 6.2 提示词

```typescript
// buildAssistantDailyLogPrompt
`This session is long-lived. As you work, record anything worth remembering by **appending** to today's daily log file:
${logPathPattern}

Write each entry as a short timestamped bullet. Create the file (and parent directories) on first write if it does not exist. Do not rewrite or reorganize the log — it is append-only.`
```

---

## 8. 状态管理集成

### 7.1 AppState 中的记忆相关字段

```typescript
// src/state/AppStateStore.ts
export type AppState = {
  // ...
  sessionHooks: Map<string, SessionHook>  // 用于记忆相关的 hook
}
```

### 7.2 记忆文件监控

```typescript
// claudemd.ts
getMemoryFiles.cache.clear()  // 清除记忆文件缓存
resetGetMemoryFilesCache()     // 重置并触发 hook
```

---

## 9. 关键设计决策

### 8.1 为什么用文件而非数据库

- **简单性**：易于查看、编辑、版本控制
- **可移植性**：通过 git 共享（Project/Team）
- **可调试性**：直接 cat 查看，无需特殊工具

### 8.2 为什么限制记忆类型

封闭 taxonomy 防止**记忆膨胀**和**记忆污染**。明确排除可派生信息（代码模式、git 历史），确保记忆系统只保存真正的"上下文增量"。

### 8.3 为什么用 Sonnet 选择而非关键词匹配

关键词匹配会产生大量误报（query 中有 "spawn" → 选择包含 spawn 的工具文档）。Sonnet 能理解语义，选择真正相关的记忆，同时排除正在使用的工具文档。

---

## 10. 架构图

### 10.1 上下文与记忆全景

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Message                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     System Prompt Builder                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ getSystemContext │  │ getUserContext    │  │ getClaudeMds() │  │
│  │  - git status   │  │  - currentDate    │  │  - claude.md   │  │
│  │  - cache breaker│  │                  │  │  - rules       │  │
│  └─────────────────┘  └──────────────────┘  └────────────────┘  │
│                              │                    │              │
│                              └────────┬───────────┘              │
│                                       ▼                          │
│                         ┌──────────────────────┐                  │
│                         │  Merged System Prompt │                 │
│                         └──────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    findRelevantMemories()                         │
│  ┌───────────────┐  ┌────────────────┐  ┌─────────────────┐   │
│  │scanMemoryFiles│→ │ formatManifest()│→ │  Sonnet Select  │   │
│  │ (frontmatter) │  │ (type, desc)    │  │  (top 5)        │   │
│  └───────────────┘  └────────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 上下文压缩流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     Token Usage Monitor                           │
│                                                                  │
│  tokenCount >= autoCompactThreshold ?                           │
│    → autoCompactIfNeeded()                                      │
│    → trySessionMemoryCompact() [实验性优先]                      │
│    → compactConversation() [fallback]                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    compactConversation()                           │
│                                                                  │
│  Messages                                                        │
│      │                                                         │
│      ▼                                                         │
│  ┌───────────────────┐                                         │
│  │ stripImagesFrom... │  图片→[image] 占位符                    │
│  └───────────────────┘                                         │
│      │                                                         │
│      ▼                                                         │
│  ┌───────────────────┐                                         │
│  │stripReinjected... │  移除重复注入的附件类型                  │
│  └───────────────────┘                                         │
│      │                                                         │
│      ▼                                                         │
│  ┌───────────────────┐                                         │
│  │groupMessagesByApi..│  按 API 调用分组                        │
│  └───────────────────┘                                         │
│      │                                                         │
│      ▼                                                         │
│  ┌───────────────────┐                                         │
│  │  Sonnet Summary   │  生成 9 部分摘要                         │
│  │  <analysis>      │  (draft, stripped later)                  │
│  │  <summary>       │                                          │
│  └───────────────────┘                                         │
│      │                                                         │
│      ▼                                                         │
│  ┌───────────────────┐                                         │
│  │formatCompactSummary│  剥离 analysis，格式化输出              │
│  └───────────────────┘                                         │
│      │                                                         │
│      ▼                                                         │
│  ┌───────────────────────────┐                                   │
│  │createCompactBoundaryMessage│  标记压缩点                       │
│  └───────────────────────────┘                                   │
│      │                                                         │
│      ▼                                                         │
│  ┌───────────────────┐                                         │
│  │runPostCompactCleanup│  清理、重置缓存基线                    │
│  └───────────────────┘                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. 相关文件索引

| 文件 | 用途 |
|------|------|
| `src/context.ts` | getSystemContext / getUserContext（会话上下文） |
| `src/utils/context.ts` | 模型上下文窗口大小、1M context 支持 |
| `src/utils/contextAnalysis.ts` | 上下文 token 统计分析 |
| `src/utils/claudemd.ts` | CLAUDE.md 加载、@include、paths 条件规则 |
| `src/services/compact/compact.ts` | 核心压缩逻辑（60KB） |
| `src/services/compact/autoCompact.ts` | 自动压缩触发与阈值计算 |
| `src/services/compact/microCompact.ts` | 渐进式工具输出清理 |
| `src/services/compact/sessionMemoryCompact.ts` | Session memory 优先压缩（实验性） |
| `src/services/compact/prompt.ts` | 压缩摘要提示词模板 |
| `src/memdir/memdir.ts` | 记忆提示词构建、记忆类型指导 |
| `src/memdir/memoryTypes.ts` | 四类记忆 taxonomy、not-to-save 指导 |
| `src/memdir/findRelevantMemories.ts` | 基于 Sonnet 的记忆召回 |
| `src/memdir/memoryScan.ts` | 记忆目录扫描、manifest 格式化 |
| `src/memdir/paths.ts` | 记忆路径解析、auto memory 开关 |
| `src/memdir/teamMemPaths.ts` | Team memory 路径管理 |
| `src/state/AppStateStore.ts` | AppState 定义 |
| `src/bootstrap/state.ts` | 启动状态初始化 |

---

*文档版本: 2026-04-15*
