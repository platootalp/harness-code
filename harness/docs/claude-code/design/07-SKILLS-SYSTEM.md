# 技能系统设计文档

> 本文档详细解析 Claude Code 技能系统的架构设计、加载机制、工具限制和执行模式。

---

## 1. 设计概述

### 1.1 什么是技能？

技能 (Skill) 是**可复用的提示模板**，以 Markdown 文件形式存储在文件系统中。

```
Skill 本质上是一段预定义的提示词，
当用户调用 /skill-name 时，这段提示词被插入到对话中。
```

### 1.2 技能 vs 工具

| 方面 | 工具 (Tool) | 技能 (Skill) |
|------|-------------|--------------|
| **执行方式** | 原生代码直接执行 | 展开为提示内容发送给模型 |
| **调用方式** | AI 模型决定调用 | 用户 `/skill-name` 或 AI 通过 SkillTool |
| **上下文** | 可访问完整对话状态 | 作为消息前缀注入 |
| **使用场景** | 文件操作、Shell、API 调用 | 代码审查、提交生成、问题分析 |
| **可编程性** | TypeScript 实现 | Markdown + Frontmatter |
| **状态管理** | 通过 ToolUseContext | 无状态 (展开后由模型决定) |

---

## 2. 类型系统

### 2.1 技能定义类型

```typescript
// src/skills/bundledSkills.ts
export type BundledSkillDefinition = {
  // ========== 基础信息 ==========
  name: string
  description: string
  aliases?: string[]
  whenToUse?: string  // 使用场景描述
  argumentHint?: string  // 参数提示

  // ========== 工具限制 ==========
  allowedTools?: string[]  // 允许使用的工具白名单

  // ========== 模型控制 ==========
  model?: string  // 指定使用的模型
  disableModelInvocation?: boolean  // 禁止 AI 模型调用此技能

  // ========== 调用控制 ==========
  userInvocable?: boolean  // 是否允许 /skill-name 调用
  isEnabled?: () => boolean  // 特性开关检查

  // ========== 生命周期钩子 ==========
  hooks?: HooksSettings  // PreToolUse, PostToolUse 等

  // ========== 执行上下文 ==========
  context?: 'inline' | 'fork'  // inline: 直接展开 | fork: 子 Agent 执行
  agent?: string  // fork 模式使用的 agent 类型

  // ========== 资源文件 ==========
  files?: Record<string, string>  // 引用文件路径 → 内容

  // ========== 执行入口 ==========
  getPromptForCommand(
    args: string,
    context: ToolUseContext
  ): Promise<ContentBlockParam[]>
}
```

### 2.2 技能来源

```typescript
// src/types/command.ts
type SkillSource =
  | 'bundled'      // 内置技能 (编译到二进制)
  | 'commands'     // 旧版 commands/ 目录
  | 'skills'       // ~/.claude/skills/
  | 'plugin'       // 插件提供
  | 'managed'      // 托管策略控制
  | 'mcp'          // MCP 服务器提供
```

---

## 3. 技能加载

### 3.1 加载来源优先级

```typescript
// src/skills/loadSkillsDir.ts
// 技能加载优先级 (高 → 低)

const SKILL_LOAD_PRIORITY: SkillSource[] = [
  'bundled',      // 1. 内置技能
  'managed',      // 2. 托管策略 (只读)
  'skills',       // 3. 用户技能 ~/.claude/skills/
  'project',      // 4. 项目技能 .claude/skills/
  'plugin',       // 5. 插件技能
  'mcp',          // 6. MCP 技能
]
```

### 3.2 加载流程

```typescript
// src/skills/loadSkillsDir.ts
export async function loadSkillsDir(
  dir: string,
  options: LoadSkillsOptions
): Promise<SkillCommand[]> {
  // 1. 检查目录是否存在
  if (!fs.existsSync(dir)) {
    return []
  }

  // 2. 遍历目录 (递归)
  const skillFiles = await glob('**/*.md', {
    cwd: dir,
    ignore: ['**/node_modules/**'],
  })

  const skills: SkillCommand[] = []

  for (const file of skillFiles) {
    // 3. 解析 frontmatter
    const content = await fs.readFile(file, 'utf-8')
    const { frontmatter, body } = parseFrontmatter(content)

    // 4. 创建技能命令
    const skill = createSkillCommand({
      name: frontmatter.name ?? path.basename(file, '.md'),
      description: frontmatter.description ?? '',
      body,
      root: dir,
      file,
      loadedFrom: options.source,
    })

    if (skill) {
      skills.push(skill)
    }
  }

  // 5. 去重 (按名称)
  return deduplicateByName(skills)
}
```

### 3.3 Frontmatter 解析

```typescript
// src/skills/loadSkillsDir.ts
interface SkillFrontmatter {
  name?: string
  description?: string
  whenToUse?: string
  argumentHint?: string

  // 工具限制
  allowedTools?: string[]

  // 模型控制
  model?: string
  disableModelInvocation?: boolean

  // 调用控制
  userInvocable?: boolean
  isEnabled?: boolean

  // 生命周期
  hooks?: HooksSettings

  // 执行上下文
  context?: 'inline' | 'fork'
  agent?: string
  effort?: EffortValue

  // 条件激活
  paths?: string[]  // 文件路径模式
}

export function parseFrontmatter(
  content: string
): { frontmatter: SkillFrontmatter; body: string } {
  // 检测 frontmatter
  const match = content.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/)

  if (!match) {
    return { frontmatter: {}, body: content }
  }

  // YAML 解析
  const yamlStr = match[1]
  const body = match[2]

  const frontmatter = yaml.parse(yamlStr) as SkillFrontmatter

  return { frontmatter, body }
}
```

### 3.4 条件激活

```typescript
// src/skills/loadSkillsDir.ts
/**
 * 条件技能激活
 *
 * 问题：某些技能只在特定文件被编辑时才有用
 * 解决：通过 frontmatter paths 字段指定激活条件
 */

interface ConditionalSkill {
  name: string
  paths: string[]  // glob 模式
  skill: SkillCommand
}

// 激活条件检查
export function shouldActivateSkill(
  skill: ConditionalSkill,
  touchedPaths: string[]
): boolean {
  // 任意触达路径匹配任一模式即激活
  return touchedPaths.some(touchedPath =>
    skill.paths.some(pattern => matchGlob(pattern, touchedPath))
  )
}

// 动态技能发现
export async function discoverSkillDirsForPaths(
  baseDir: string,
  paths: string[]
): Promise<string[]> {
  const discovered: string[] = []

  for (const filePath of paths) {
    // 从文件所在目录向上查找 .claude/skills/
    let dir = path.dirname(filePath)

    while (true) {
      const skillsDir = path.join(dir, '.claude', 'skills')

      if (fs.existsSync(skillsDir)) {
        discovered.push(skillsDir)
      }

      // 到达 baseDir 或根目录停止
      if (dir === baseDir || dir === path.dirname(dir)) {
        break
      }

      dir = path.dirname(dir)
    }
  }

  return [...new Set(discovered)]  // 去重
}
```

---

## 4. 技能命令创建

### 4.1 createSkillCommand

```typescript
// src/skills/loadSkillsDir.ts
export function createSkillCommand(
  options: CreateSkillOptions
): SkillCommand {
  const {
    name,
    description,
    body,
    root,
    file,
    loadedFrom,
    frontmatter,
  } = options

  // 构建 getPromptForCommand
  const getPromptForCommand: SkillCommand['getPromptForCommand'] = async (
    args,
    context
  ) => {
    // 1. 替换变量
    let prompt = body

    // ${CLAUDE_SKILL_DIR} → 技能目录
    prompt = prompt.replace(
      /\$\{CLAUDE_SKILL_DIR\}/g,
      path.dirname(file)
    )

    // ${CLAUDE_SESSION_ID} → 会话 ID
    prompt = prompt.replace(
      /\$\{CLAUDE_SESSION_ID\}/g,
      context.session?.id ?? 'unknown'
    )

    // ${1}, ${2}... → 位置参数
    const argParts = args.split(/\s+/)
    prompt = prompt.replace(
      /\$\{(\d+)\}/g,
      (_, index) => argParts[parseInt(index) - 1] ?? ''
    )

    // 2. 执行 shell 命令 (!command)
    prompt = await executeShellCommands(prompt, context)

    // 3. 添加参数
    if (args) {
      prompt = `${prompt}\n\nUser arguments: ${args}`
    }

    // 4. 返回内容块
    return [{ type: 'text', text: prompt }]
  }

  // 返回完整命令
  return {
    type: 'prompt',
    name,
    description,
    aliases: frontmatter.aliases,
    argumentHint: frontmatter.argumentHint,
    whenToUse: frontmatter.whenToUse,
    allowedTools: frontmatter.allowedTools,
    model: frontmatter.model,
    disableModelInvocation: frontmatter.disableModelInvocation,
    userInvocable: frontmatter.userInvocable ?? true,
    isEnabled: frontmatter.isEnabled
      ? () => frontmatter.isEnabled!
      : undefined,
    hooks: frontmatter.hooks,
    context: frontmatter.context,
    agent: frontmatter.agent,
    progressMessage: `Running ${name}...`,
    contentLength: body.length,
    loadedFrom,
    skillRoot: root,
    getPromptForCommand,
  }
}
```

### 4.2 Shell 命令执行

```typescript
// src/skills/loadSkillsDir.ts
/**
 * 技能中的 shell 命令执行
 *
 * 语法: !{command}
 * 示例: !{cat package.json | jq '.version'}
 */
async function executeShellCommands(
  prompt: string,
  context: ToolUseContext
): Promise<string> {
  const result: string[] = []
  const lines = prompt.split('\n')

  for (const line of lines) {
    if (line.startsWith('!{') && line.endsWith('}')) {
      // 提取命令
      const command = line.slice(2, -1).trim()

      try {
        // 执行命令
        const output = await execAsync(command, {
          cwd: context.session?.cwd ?? process.cwd(),
          timeout: 30000,
        })

        result.push(output.stdout || output.stderr)
      } catch (error) {
        result.push(`[Command failed: ${error.message}]`)
      }
    } else {
      result.push(line)
    }
  }

  return result.join('\n')
}
```

---

## 5. 工具限制机制

### 5.1 为什么需要工具限制？

某些技能只需要特定工具：

```
/commit 技能:
  - 只需要: git status, git add, git commit
  - 不需要: 文件编辑、Shell 等
```

### 5.2 工具限制实现

```typescript
// src/skills/loadSkillsDir.ts
export function createToolRestrictedContext(
  originalContext: ToolUseContext,
  allowedTools: string[]
): ToolUseContext {
  return {
    ...originalContext,

    // 修改工具权限上下文
    toolPermissionContext: {
      ...originalContext.toolPermissionContext,

      // 白名单规则
      alwaysAllowRules: {
        ...originalContext.toolPermissionContext.alwaysAllowRules,

        // 添加技能级别的工具白名单
        skill: allowedTools,
      },
    },
  }
}

// 在 getPromptForCommand 中使用
const getPromptForCommand: SkillCommand['getPromptForCommand'] = async (
  args,
  context
) => {
  // 应用工具限制
  const restrictedContext = allowedTools
    ? createToolRestrictedContext(context, allowedTools)
    : context

  // 使用受限上下文执行
  // ...
}
```

### 5.3 工具模式匹配

```typescript
// src/utils/permissions/permissions.ts
/**
 * 工具名称匹配
 *
 * 模式格式: "ToolName" 或 "ToolName(arg:*)"
 * 示例:
 *   "Bash(git *)"      → 所有 git 命令
 *   "Read(*.env)"      → 读取 .env 文件
 *   "Bash"             → 精确匹配 Bash 工具
 */

function matchesToolPattern(toolName: string, pattern: string): boolean {
  // 解析模式
  const [namePart, argPart] = pattern.split('(')

  // 工具名匹配
  if (!globMatch(toolName, namePart.trim())) {
    return false
  }

  // 参数匹配 (如果有)
  if (argPart) {
    const argPattern = argPart.replace(/\*/g, '.*').replace(/\?/g, '.')
    const args = extractToolArgs(toolName)

    return new RegExp(`^${argPattern}$`).test(args)
  }

  return true
}
```

---

## 6. 技能执行模式

### 6.1 Inline 模式

```typescript
// 技能内容直接展开到用户消息
// 模型收到的是展开后的提示词
async function executeInlineSkill(
  skill: SkillCommand,
  args: string,
  context: ToolUseContext
): Promise<ContentBlockParam[]> {
  // 调用技能的 getPromptForCommand
  const contentBlocks = await skill.getPromptForCommand(args, context)

  return contentBlocks
}

// 结果: 用户消息 + 技能提示词 → 发送给模型
```

### 6.2 Fork 模式

```typescript
// 技能在子 Agent 中执行
async function executeForkedSkill(
  skill: SkillCommand,
  args: string,
  context: ToolUseContext
): Promise<SkillResult> {
  // 1. 获取初始 prompt
  const contentBlocks = await skill.getPromptForCommand(args, context)

  // 2. 构建子 Agent 配置
  const agentConfig: AgentConfig = {
    agentType: skill.agent ?? 'GeneralPurpose',
    tools: skill.allowedTools,
    permissionMode: 'auto',

    // fork 隔离
    isolation: 'worktree',

    // token 预算
    maxTurns: skill.effort
      ? effortToMaxTurns(skill.effort)
      : 10,
  }

  // 3. 派生子 Agent
  const agentResult = await runAgent({
    config: agentConfig,
    initialMessages: [
      { role: 'user', content: contentBlocks }
    ],
    parentContext: context,
  })

  // 4. 收集结果
  const resultMessages: Message[] = []
  for await (const msg of agentResult) {
    resultMessages.push(msg)
  }

  return {
    messages: resultMessages,
    summary: extractSummary(resultMessages),
  }
}
```

---

## 7. 内置技能

### 7.1 内置技能注册

```typescript
// src/skills/bundledSkills.ts
export const BUNDLED_SKILLS: BundledSkillDefinition[] = [
  {
    name: 'commit',
    description: 'Create a git commit with a descriptive message',
    whenToUse: 'When you want to commit staged changes',
    argumentHint: '[-m <message>]',
    allowedTools: [
      'Bash(git status:*)',
      'Bash(git add:*)',
      'Bash(git commit:*)',
      'Read(*)',
      'Glob(*)',
    ],
    getPromptForCommand: async (args) => {
      const message = extractMessageArg(args)
      return [{
        type: 'text',
        text: `Create a git commit. Use git status to see staged files.\n` +
              `Commit message: ${message ?? 'Provide a descriptive message'}\n` +
              `After staging files, use: git commit -m "<message>"`
      }]
    }
  },

  {
    name: 'review',
    description: 'Review code changes in a pull request',
    whenToUse: 'When reviewing PRs or code changes',
    allowedTools: [
      'Bash(git diff:*)',
      'Bash(git log:*)',
      'Read(*)',
    ],
    context: 'fork',  // Fork 模式执行
    agent: 'CodeReview',
    getPromptForCommand: async (args) => {
      const prNumber = extractPRNumber(args)
      return [{
        type: 'text',
        text: `Review the pull request #${prNumber}.\n` +
              `Examine the changes, look for potential issues,\n` +
              `and provide constructive feedback.`
      }]
    }
  },

  // ... 更多内置技能
]
```

### 7.2 内置技能注册函数

```typescript
// src/skills/bundledSkills.ts
const registeredSkills = new Map<string, BundledSkillDefinition>()

export function registerBundledSkill(
  skill: BundledSkillDefinition
): void {
  registeredSkills.set(skill.name, skill)

  // 注册别名
  for (const alias of skill.aliases ?? []) {
    registeredSkills.set(alias, skill)
  }
}

export function getBundledSkill(
  name: string
): BundledSkillDefinition | undefined {
  return registeredSkills.get(name)
}

// 初始化注册
for (const skill of BUNDLED_SKILLS) {
  registerBundledSkill(skill)
}
```

---

## 8. MCP 技能

### 8.1 MCP 技能暴露

```typescript
// src/commands.ts
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

// MCP 服务器 → 技能转换
function convertMCPServerToSkill(
  server: MCPServer,
  command: MCPCommand
): SkillCommand {
  return {
    type: 'prompt',
    name: `${server.name}:${command.name}`,
    description: command.description,
    loadedFrom: 'mcp',
    isMcp: true,
    userInvocable: true,

    getPromptForCommand: async (args, context) => {
      // 调用 MCP 命令
      const result = await server.callCommand(command.name, {
        input: args,
      })

      return [{
        type: 'text',
        text: `MCP Command: ${command.name}\nInput: ${args}\n\nResult:\n${JSON.stringify(result, null, 2)}`
      }]
    }
  }
}
```

---

## 9. 技能目录结构

### 9.1 标准目录布局

```
~/.claude/
└── skills/
    ├── commit.md
    ├── review.md
    ├── test.md
    └── ...


project/
└── .claude/
    └── skills/
        ├── architecture.md
        └── deploy.md
```

### 9.2 技能文件格式

```markdown
<!-- commit.md -->

---
name: commit
description: Create a git commit with a descriptive message
whenToUse: When you want to commit staged changes
argumentHint: [-m <message>]
allowedTools:
  - Bash(git status:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Read(*)
  - Glob(*)
---

# Git Commit Skill

Create a thoughtful git commit with the following steps:

1. Run `git status` to see staged files
2. Review the changes to understand what was modified
3. Create a descriptive commit message following conventional commits:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `refactor:` for code refactoring
   - `test:` for adding or updating tests

4. Commit with: `git commit -m "<message>"`

## Examples

- `feat: add user authentication with OAuth`
- `fix: resolve memory leak in cache manager`
- `docs: update API documentation for v2`

## Arguments

{1} - Optional commit message. If not provided, you should generate one based on the changes.
```

---

## 10. 设计模式总结

### 10.1 模式列表

| 模式 | 应用 | 优势 |
|------|------|------|
| **模板模式** | getPromptForCommand | 可变的提示词生成 |
| **变量替换** | ${CLAUDE_SKILL_DIR} | 动态内容 |
| **Shell 执行** | !{command} | 运行时信息注入 |
| **条件激活** | paths glob | 上下文感知 |
| **工具白名单** | allowedTools | 最小权限 |
| **Fork 执行** | context: 'fork' | 隔离执行 |

### 10.2 安全性设计

```typescript
// 1. 技能文件路径验证
function validateSkillPath(filePath: string): boolean {
  // 防止路径遍历攻击
  const resolved = path.resolve(filePath)
  const allowedBase = path.resolve(HOME_DIR, '.claude', 'skills')

  return resolved.startsWith(allowedBase)
}

// 2. Shell 命令执行限制
const ALLOWED_SHELL_COMMANDS = new Set([
  'cat', 'head', 'tail', 'grep', 'jq', 'git', // 安全命令
])

function validateShellCommand(command: string): boolean {
  const cmd = command.split(' ')[0]
  return ALLOWED_SHELL_COMMANDS.has(cmd)
}

// 3. 工具限制强制执行
function enforceToolRestrictions(
  context: ToolUseContext,
  allowedTools: string[]
): ToolUseContext {
  return {
    ...context,
    toolPermissionContext: {
      ...context.toolPermissionContext,
      alwaysAllowRules: {
        ...context.toolPermissionContext.alwaysAllowRules,
        skill: allowedTools,
      },
      // 清空其他可能允许的规则
      transientPermissions: [],
    },
  }
}
```

---

*文档版本: 2026-03-31*
