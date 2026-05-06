# 竞品对比分析：OpenHarness vs Claude Code / Hermes Agent / OpenClaw

## 摘要

本文档对比 OpenHarness 与三个主要竞品（Claude Code、Hermes Agent、OpenClaw）在 17 个能力维度上的差距，识别出 12 项关键不足，并按优先级提出三阶段演进路线。核心判断：OpenHarness 架构基础扎实（工具/记忆/多 Agent/多 Channel），主要差距在**精细化**（安全、缓存、搜索）和**生态化**（SDK、市场、IDE）两个方向。

## 你将了解

- 四个系统在 17 个维度上的能力矩阵对比
- OpenHarness 的 12 项关键不足，按 P0/P1/P2 优先级分组
- 三阶段演进路线（夯实基础 → 生态建设 → 差异化突破）
- OpenHarness 的 6 项既有优势及放大策略

## 范围

本文档覆盖 OpenHarness 与 Claude Code (2026.4)、Hermes Agent (Nous Research, ~120k stars)、OpenClaw (~365k stars) 的功能级对比，重点关注架构能力差异而非 UI/UX 细节。所有分析基于代码库实际实现和公开文档，不包含推测性功能。

---

## 一、能力矩阵对比

### 1.1 总览表

| 能力维度 | OpenHarness | Claude Code | Hermes Agent | OpenClaw |
|---------|------------|-------------|--------------|----------|
| 会话持久化 | ✅ JSON 快照 + 恢复 | ✅ 多表面连续性 | ✅ SQLite + FTS5 + 血缘追踪 | ✅ Gateway 常驻跨 channel |
| 工具系统 | ✅ 40+ 工具 Pydantic 校验 | ✅ 12 核心工具 + MCP 扩展 | ✅ 47 工具 19 toolset | ✅ 一等工具 + Skills 扩展 |
| MCP 集成 | ✅ 双客户端 (stdio/HTTP) | ✅ + 注册表市场 + 延迟 schema | ✅ 作为工具类别支持 | ❌ 无原生 MCP |
| 记忆系统 | ✅ Markdown + mem0 后端 | ✅ CLAUDE.md 分层 + 自动记忆 | ✅ 双文件有界 + FTS5 + 8 外部后端 | ⚠️ 仅 workspace 文件级 |
| 多 Agent | ✅ Coordinator + Swarm | ✅ Subagent + Agent Teams (实验) | ✅ delegate_task 隔离子代理 | ✅ Gateway 多 agent 路由 |
| 权限安全 | ✅ 敏感路径 + 3 模式 | ✅ 6 模式 + LLM 安全分类器 | ✅ 7 层纵深防御 + SSRF + 上下文扫描 | ✅ DM 配对 + 沙箱 + 治理工作流 |
| Hook 系统 | ✅ Pre/Post ToolUse 等 | ✅ 5 类型 22+ 事件 + 决策控制 | ⚠️ 回调机制 | ⚠️ 事件驱动 |
| Skills | ✅ SKILL.md + frontmatter | ✅ + 动态上下文注入 + 路径范围 | ✅ + 自主创建/自我改进 + agentskills.io | ✅ + 13k+ 社区技能 + ClawHub |
| IDE 集成 | ❌ 无原生 IDE 插件 | ✅ VS Code + JetBrains + Desktop | ❌ 无 | ❌ 无 |
| 跨设备连续性 | ⚠️ Ohmo Gateway 有限 | ✅ 终端↔VS Code↔Web↔手机↔Desktop | ⚠️ 跨消息平台连续 | ✅ Gateway WebSocket + 伴生 App |
| 语音能力 | ❌ 无 | ⚠️ 有限 | ✅ 语音备忘录 + 语音唤醒 | ✅ 语音唤醒 + 持续语音 |
| 沙箱/终端后端 | ⚠️ 本地为主 | ✅ 文件系统 + 网络沙箱 | ✅ 6 后端 (Docker/SSH/Modal/Daytona...) | ✅ Docker/SSH/OpenShell |
| SDK/编程接口 | ❌ 无独立 SDK | ✅ Python + TypeScript Agent SDK | ⚠️ RPC 脚本 | ⚠️ RPC 协议 |
| Skill 生态/市场 | ❌ 无市场 | ⚠️ Plugin 市场 (早期) | ✅ agentskills.io + Hub 安全扫描 | ✅ ClawHub 13k+ + 安全审核 |
| 可视化/Canvas | ❌ 无 | ❌ 无 | ❌ 无 | ✅ A2UI 实时渲染 |
| RL/研究 | ❌ 无 | ❌ 无 | ✅ 批量轨迹 + Atropos RL | ❌ 无 |
| 团队治理 | ❌ 无 | ⚠️ 企业策略 (早期) | ❌ 无 | ✅ Mission Control |

### 1.2 评分量化

按 0-5 分量化（5=行业领先，3=可用但平庸，0=缺失）：

| 维度 | OpenHarness | Claude Code | Hermes | OpenClaw |
|------|-----------|-------------|--------|----------|
| 会话持久化 | 3 | 5 | 5 | 4 |
| 工具系统 | 4 | 4 | 5 | 4 |
| MCP 集成 | 4 | 5 | 3 | 0 |
| 记忆系统 | 3 | 4 | 5 | 2 |
| 多 Agent | 4 | 4 | 4 | 4 |
| 权限安全 | 3 | 5 | 5 | 4 |
| Hook 系统 | 3 | 5 | 2 | 2 |
| Skills | 3 | 4 | 5 | 5 |
| IDE 集成 | 0 | 5 | 0 | 0 |
| 跨设备 | 2 | 5 | 3 | 4 |
| 语音 | 0 | 1 | 4 | 4 |
| 沙箱后端 | 2 | 4 | 5 | 3 |
| SDK | 0 | 5 | 2 | 2 |
| Skill 生态 | 0 | 2 | 5 | 5 |
| **总分** | **31** | **53** | **48** | **42** |

---

## 二、关键不足详细分析

### P0 — 核心竞争力缺失

#### 不足 1：无会话搜索能力

**现状**

`session_storage.py` 提供 JSON 快照的 `save_snapshot()` / `load_latest()` / `list_snapshots()`，但所有快照为独立 JSON 文件，无全文索引。`list_snapshots()` 仅能按时间列举，无法按内容搜索。

**竞品做法**

- **Hermes Agent**：SQLite + FTS5 全文搜索。`session_search` 工具提供跨会话检索 + LLM 摘要，配合有界记忆形成"常驻知识 + 无限历史"双轨架构
- **Claude Code**：`/resume` 交互式选择器，按目录/会话名/ID 搜索历史会话

**影响**

用户无法从过往经验中检索知识。每次解决新问题可能重复过去的探索路径，记忆系统有界但历史无界——搜索能力是打通这一断点的关键。

**改进方向**

```
存储层: JSON 文件 → SQLite 表 (sessions, messages, snapshots)
索引层: message content 全文索引 + session metadata 索引
工具层: session_search 工具 → FTS5 查询 + LLM 结果摘要
兼容性: 保留 JSON 导出能力，SQLite 为主存储
迁移: 现有 JSON 快照 → SQLite 导入脚本
```

---

#### 不足 2：记忆系统未优化前缀缓存

**现状**

`prompt_builder` 从 Markdown 文件和 mem0 后端动态组装记忆内容注入系统提示词。每次会话的记忆内容可能因新增/修改而变化，破坏 Anthropic API 的 prompt prefix cache 命中。

**竞品做法**

- **Hermes Agent**：`MEMORY.md` (~800 tokens) + `USER.md` (~500 tokens) 作为**冻结快照**注入系统提示词前缀。会话期间修改立即写盘但**下一会话才生效**——前缀永远稳定，缓存命中率最大化

**影响**

每次会话浪费 token 重新发送本可缓存的系统提示词前缀。以 200K context window 计算，每次未命中额外消耗约 680-1200 tokens 的输入成本。

**改进方向**

```
MEMORY.md → 冻结快照注入前缀 (~800 tokens, 会话期间不变)
USER.md → 用户偏好快照 (~500 tokens, 会话期间不变)
规则: 会话中修改 → 立即写盘 → 下一会话生效
mem0 后端 → 降级为搜索后端，不再注入系统提示词前缀
工具: memory 工具支持 add/replace/remove 三种操作
```

---

#### 不足 3：无 LLM 安全分类器

**现状**

`permissions/checker.py` 提供三种权限模式 (`FULL_AUTO` / `DEFAULT` / `PLAN`)，但 `FULL_AUTO` 模式仅依赖路径规则和命令模式匹配，无智能判断能力。用户面临两难：DEFAULT 模式频繁确认效率低，FULL_AUTO 模式缺乏安全兜底。

**竞品做法**

- **Claude Code**：auto 模式使用独立 LLM 审查每个待执行动作，分类为 allow/block/ask。阻止危险操作（下载执行、数据外传、force push、IAM 变更）但允许自主工作（本地文件操作、依赖安装、push 到自有分支）。对话中声明的边界（"不要 push"）也被分类器尊重。连续 3 次或累计 20 次阻止后退回用户确认
- **Hermes Agent**：7 层纵深防御，其中危险命令审批的 smart 模式也使用辅助 LLM 做风险评估

**影响**

无分类器的 auto 模式要么过度放行（安全风险），要么因路径规则不够精细而仍然频繁打断用户（效率问题）。这是自主 agent 可用性的核心瓶颈。

**改进方向**

```
架构: 独立快速 LLM (如 Haiku 级别) 审查每个待执行动作
输入: 动作类型 + 目标路径/命令 + 对话上下文摘要
输出: allow / block / ask + 理由
阻止清单: 下载执行、数据外传、生产部署、批量删除、force push、IAM 变更
允许清单: 本地文件操作、声明式依赖安装、只读 HTTP、push 到自有分支
对话尊重: 解析对话中的显式边界约束
降级: 连续 3 次阻止 → 退回用户确认
成本: Haiku 级别每动作约 $0.001，可接受
```

---

#### 不足 4：无上下文文件扫描

**现状**

Agent 通过 `FileReadTool` 读取项目文件内容后，直接注入对话上下文，无任何安全检测。恶意项目文件可通过 prompt 注入操纵 agent 行为。

**竞品做法**

- **Hermes Agent**：上下文文件扫描层检测：ignore-instructions 模式、隐藏 HTML、凭证访问模式、不可见 Unicode、prompt 注入模式。检测到后警告 + 标记
- **Claude Code**：系统提示词中内置输入净化规则，Tool result 中包含的 prompt injection 尝试会被识别和标记

**影响**

恶意项目文件（如包含隐藏指令的 `.env`、注入指令的 README、不可见 Unicode 的配置文件）可操纵 agent 执行非预期操作，这是 agent 安全的核心攻击面。

**改进方向**

```
扫描时机: Read/Glob 加载项目文件后、MCP 工具返回内容时
检测模式:
  - prompt 注入: "ignore previous instructions" 等模式
  - 隐藏 HTML: <script>, <iframe>, data: URI
  - 不可见 Unicode: 零宽字符、RTL 覆盖、同形字
  - 凭证泄露: API key / password / token 模式
动作: 警告 + 内容标记 (不自动修改/拒绝)
性能: 正则预扫描 + 可疑时 LLM 深度分析
```

---

### P1 — 生态与体验短板

#### 不足 5：无 IDE 插件

**现状**

仅有 TUI (Textual) + React 终端前端。开发者需要在终端和 IDE 之间切换。

**竞品做法**

- **Claude Code**：VS Code 扩展（图形化 chat 面板、inline diff、@文件引用、checkpoint 回退、Session 面板）、JetBrains 插件、Desktop App（多会话并行、可视化 diff review、定时任务、Dispatch 集成）

**改进方向**

Phase 2 优先开发 VS Code 插件，核心功能：inline diff 查看/接受/拒绝、@文件引用（含行范围）、会话历史面板、权限模式选择器。基于 Language Server Protocol 或 VS Code Extension API 实现。

---

#### 不足 6：无 Agent SDK

**现状**

无独立编程接口。外部系统只能通过 CLI 子进程调用或直接 import 内部模块。

**竞品做法**

- **Claude Code**：Python (`claude_agent_sdk`) + TypeScript (`@anthropic-ai/claude-agent-sdk`) SDK，提供 `query()` 异步迭代器，可编程访问 agent loop、工具、上下文管理、hooks、权限、会话

**改进方向**

```
Python SDK: openharness-sdk 包
核心 API: query() 异步迭代器 → 流式返回消息/工具调用/结果
配置: model, tools, permission_mode, max_turns, hooks
集成: 可嵌入 CI/CD、可构建自定义工作流、可与其他系统组合
```

---

#### 不足 7：Skill 无生态/市场

**现状**

Skill 系统完整（SKILL.md + YAML frontmatter + 自动发现），但完全孤岛运行，无分发、发现、版本管理机制。

**竞品做法**

- **OpenClaw**：ClawHub 注册表（13,729+ 技能，5,211 经审核），支持 CLI 安装、版本管理、向量搜索、安全审核（373 恶意技能被移除）
- **Hermes Agent**：agentskills.io 开放标准 + Skills Hub，集成官方技能、Vercel skills.sh、GitHub repos、ClawHub，安装后经安全扫描
- **Claude Code**：Plugin 市场（早期），打包 skills + hooks + subagents + MCP servers

**改进方向**

```
注册表: Skill Hub REST API + CLI (oh skill install/search/publish)
安全: 安装时扫描 → 数据泄露/prompt 注入/破坏性命令检测
版本: 语义化版本 + 锁文件
搜索: 向量嵌入 + 关键词混合搜索
生态: 支持外部目录 (GitHub repo、ClawHub、agentskills.io 兼容)
```

---

#### 不足 8：无自主 Skill 创建

**现状**

Skill 全靠人工编写。Agent 完成复杂任务后的经验无法自动沉淀为可复用 skill。

**竞品做法**

- **Hermes Agent**：`skill_manage` 工具允许 agent 完成复杂任务后自主创建 skill（程序性记忆），并在后续使用中自我改进。3 级渐进披露减少 token 占用

**改进方向**

```
触发: Agent 完成复杂任务后 → 提示是否提取 skill
提取: LLM 分析任务过程 → 提取通用步骤 → 生成 SKILL.md
改进: 使用 skill 后收集反馈 → LLM 优化 skill 内容
渐进披露: name/description (启动时) → 摘要 (匹配时) → 全文 (调用时)
```

---

#### 不足 9：Hook 系统深度不足

**现状**

Hook 系统覆盖 Pre/Post ToolUse 等基本事件，但 handler 类型单一（仅 shell 命令），事件覆盖有限，无决策控制能力。

**竞品做法**

- **Claude Code**：5 种 handler (command / HTTP / MCP tool / prompt / agent) × 22+ 生命周期事件，支持决策控制（allow / deny / block / 修改输入），matcher 模式匹配，async 后台执行

**改进方向**

```
Handler 类型: command + HTTP + MCP tool (3 种优先)
事件扩展: SessionStart/End, UserPromptSubmit, PreCompact/PostCompact,
          PermissionRequest/Denied, SubagentStart/Stop, FileChanged
决策控制: PreToolUse hook 返回 allow/deny/ask + 可修改工具输入
匹配器: 支持精确匹配、正则、通配符
```

---

### P2 — 差异化机会

#### 不足 10：无 SSRF 防护

**现状**

`WebFetchTool` 和 `BashTool` 可被诱导访问内部网络服务（169.254.169.254 cloud metadata、127.0.0.1 本地服务、10.0.0.0/8 内网），无内置防护。

**竞品做法**

- **Hermes Agent**：内置 SSRF 防护，屏蔽 RFC 1918、loopback、link-local、cloud metadata 端点、CGNAT 范围和 cloud metadata 主机名。**不可关闭**

**改进方向**

```
URL 验证: 解析目标 URL → DNS 解析 → 检查 IP 范围
阻止范围: 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16,
          169.254.0.0/16, 100.64.0.0/10, ::1, fe80::/10
阻止域名: metadata.google.internal, metadata.azure.com, 169.254.169.254
默认不可关闭, 可配置白名单
```

---

#### 不足 11：沙箱后端单一

**现状**

`BashTool` 在本地进程直接执行命令，无容器隔离。

**竞品做法**

- **Hermes Agent**：6 种终端后端 (local / Docker / SSH / Singularity / Modal / Daytona)，Docker 后端有加固设置（dropped capabilities、no-new-privileges、PID limits、size-limited tmpfs、read-only rootfs）
- **OpenClaw**：Docker (默认) / SSH / OpenShell

**改进方向**

```
Phase 2: Docker 后端 (默认沙箱)
  - dropped capabilities, no-new-privileges
  - PID limits, size-limited tmpfs
  - read-only root filesystem
Phase 3: SSH 远程后端 (远程机器执行)
配置: agents.defaults.sandbox.mode: "non-main" (非主会话沙箱化)
```

---

#### 不足 12：无跨设备/跨表面连续性

**现状**

Ohmo Gateway 有基础消息路由（Slack/Discord/Telegram），但无会话迁移能力。用户无法在终端开始会话后在手机继续。

**竞品做法**

- **Claude Code**：terminal ↔ VS Code ↔ Web ↔ 手机 ↔ Desktop 无缝切换，`--teleport` 将 Web 会话拉到本地终端
- **OpenClaw**：Gateway WebSocket + macOS/Android/iOS 伴生 App

**改进方向**

```
短期: Ohmo Gateway 增加会话迁移 API
中期: Web Dashboard (会话列表 + 恢复 + 管理)
长期: 伴生 App (WebSocket 连接 Gateway, 接收通知 + 发送消息)
```

---

## 三、演进路线

### Phase 1 — 夯实基础 (1-2 月)

| # | 改进项 | 优先级 | 预估复杂度 | 依赖 |
|---|-------|--------|-----------|------|
| ① | 会话搜索 (SQLite + FTS5) | P0 | 中 | 无 |
| ② | 冻结记忆 + 前缀缓存 | P0 | 低 | 无 |
| ③ | Auto 模式 LLM 安全分类器 | P0 | 中 | Haiku 级别 API |
| ④ | 上下文文件扫描 | P0 | 低 | 无 |

**Phase 1 产出**：安全性达到 Hermes 水平，效率（缓存）和记忆（搜索）追平竞品基线。

### Phase 2 — 生态建设 (2-4 月)

| # | 改进项 | 优先级 | 预估复杂度 | 依赖 |
|---|-------|--------|-----------|------|
| ⑤ | VS Code 插件 | P1 | 高 | LSP / Extension API |
| ⑥ | Agent SDK (Python) | P1 | 中 | Phase 1 完成 |
| ⑦ | Skill 市场 + 安全审核 | P1 | 高 | ① (SQLite) |
| ⑧ | 沙箱后端 (Docker/SSH) | P1 | 中 | Docker API |

**Phase 2 产出**：开发者体验闭环（IDE 内编码），生态可扩展（SDK + 市场），安全隔离（沙箱）。

### Phase 3 — 差异化突破 (4-6 月)

| # | 改进项 | 优先级 | 预估复杂度 | 依赖 |
|---|-------|--------|-----------|------|
| ⑨ | 自主 Skill 创建 | P2 | 中 | ⑦ (Skill 市场) |
| ⑩ | A2UI 可视化 Canvas | P2 | 高 | WebSocket |
| ⑪ | 语音能力 (STT/TTS) | P2 | 中 | 音频 API |
| ⑫ | RL / 自我改进循环 | P2 | 高 | 训练基础设施 |

**Phase 3 产出**：从"工具"进化为"自我进化的智能体"，形成不可替代的差异化壁垒。

### 路线图依赖关系

```
① 会话搜索 ──────────────┐
② 冻结记忆 ──────────────┤
③ LLM 安全分类器 ────────┤── Phase 1 (1-2 月)
④ 上下文扫描 ────────────┘
                         │
⑤ VS Code 插件 ──────────┤
⑥ Agent SDK ─────────────┤── Phase 2 (2-4 月)
⑦ Skill 市场 ────────────┤
⑧ 沙箱后端 ──────────────┘
                         │
⑨ 自主 Skill 创建 ───────┤
⑩ A2UI Canvas ───────────┤── Phase 3 (4-6 月)
⑪ 语音 ──────────────────┤
⑫ RL 自我改进 ───────────┘
```

---

## 四、OpenHarness 既有优势

以下优势应在演进中**保持并放大**，而非因追逐竞品而弱化：

| # | 优势 | 现状 | 放大策略 |
|---|------|------|---------|
| A | **Ohmo Gateway 多 Channel** | 已集成 Slack/Discord/Telegram/iMessage 等 10+ 平台 | 配合 Phase 2 跨设备连续性，做"全平台入口"差异化 |
| B | **Coordinator + Swarm 多 Agent** | subprocess/in_process/tmux 三种后端，Agent Teams 概念 | 配合 Phase 2 沙箱后端，加 Docker/SSH 隔离执行 |
| C | **Mem0 语义记忆** | 已集成 mem0 语义搜索 | 配合 Phase 1 ① FTS5，形成"语义 + 全文"双轨搜索，超越竞品单一方案 |
| D | **40+ 内置工具** | 工具数量与 Hermes 持平 | 继续打磨质量，Phase 1 ④ 加扫描后安全性领先 |
| E | **Pydantic 配置系统** | 类型安全，比竞品 JSON 配置更可靠 | Phase 2 ⑥ SDK 可直接复用 Pydantic model 做验证 |
| F | **Cron 定时任务** | 已有 CronCreate/CronDelete/CronList/CronToggle | Phase 3 ⑪ 语音 + Cron = 语音定时触发，形成闭环自动化 |

---

## 五、竞品差异化特征备忘

以下为竞品中 OpenHarness 目前不具备但值得长期关注的独特能力：

| 特征 | 来源 | 是否采纳建议 |
|------|------|------------|
| 多表面连续性 (terminal↔IDE↔Web↔手机) | Claude Code | Phase 2-3 逐步引入 |
| agentskills.io 开放标准 | Hermes | Phase 2 Skill 市场兼容 |
| SOUL.md 人格层 + 社区注册表 | OpenClaw/Hermes | 长期考虑，非核心 |
| A2UI 实时渲染 (agent 直出 UI) | OpenClaw | Phase 3 ⑩ |
| Mission Control 团队治理 | OpenClaw | 企业场景需要，长期 |
| RL 轨迹采集 + 模型自我改进 | Hermes | Phase 3 ⑫ |
| Zero Token 社区 fork (浏览器认证) | OpenClaw | 不建议，合规风险 |
| 6 种终端后端含 Serverless | Hermes | Phase 2 ⑧ 引入 Docker/SSH |

---

## 六、总结

OpenHarness 当前总分 31/75，与 Claude Code (53)、Hermes (48)、OpenClaw (42) 存在差距。差距主要集中在前缀缓存、会话搜索、安全分类器、上下文扫描四个基础能力（P0），以及 IDE 集成、SDK、Skill 市场三个生态能力（P1）。

**核心策略**：Phase 1 补安全与效率短板 → 基础能力追平竞品基线；Phase 2 扩生态 → 开发者体验闭环；Phase 3 做差异化 → 从工具进化为自我进化的智能体。6 个月内可追平主要竞品并形成"多 Channel + 双轨记忆 + 自主进化"的差异化组合。
