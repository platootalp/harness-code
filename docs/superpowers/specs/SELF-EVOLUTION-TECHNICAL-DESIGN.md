# Self-Evolution 插件技术设计

**状态：** Draft  
**作者：** lijunyi  
**初版宿主：** Claude Code v1.x（插件市场兼容）  
**后续宿主（规划）：** OpenCode、Codex、Cursor 等；能力与术语分叉、兼容挡位的落地顺序见[第十二章](#十二风险待确认与后续方向)。  
**编写日期：** 2026-05-08  

本文档描述 **self-evolution** 插件的完整设计：在会话运行过程中，将可复用的「过程知识」安全、按频率地沉淀为用户级 skill（本文初版示例路径 `~/.claude/skills/<category>-<name>/SKILL.md`），与宿主侧事实记忆、会话记忆等机制互补，而不替代其职责；**宿主无关**的核心是「谁来触发审查、**节流与校验如何落地**、写什么形态的文件」，**宿主相关**的是事件名（如 Stop）、结构化输出字段名、插件清单字段等——后续多宿主演进时以保持前者稳定、分叉后者为原则。

**阅读说明**：文中配图均为 **纯文本示意图**（不依赖 Mermaid 等渲染器），方便打印、归档与在任意编辑器中阅读。

---

## 目录

- [一、背景与目标](#一背景与目标)
- [二、总体设计摘要](#二总体设计摘要)
- [三、范围与显式边界](#三范围与显式边界)
- [四、系统架构与数据流](#四系统架构与数据流)
- [五、关键决策](#五关键决策)
- [六、组件与目录结构](#六组件与目录结构)
- [七、运行时：事件、脚本与门控](#七运行时事件脚本与门控)
- [八、命名、Frontmatter 与产出形态](#八命名frontmatter-与产出形态)
- [九、元技能 evolve-skill-writer](#九元技能-evolve-skill-writer)
- [十、关键技术问题与约束](#十关键技术问题与约束)
- [十一、实施计划与验收](#十一实施计划与验收)
- [十二、风险、待确认与后续方向](#十二风险待确认与后续方向)

---

## 一、背景与目标

**问题**：Claude Code 已提供**事实记忆**、**会话记忆**、**团队记忆**等能力，主要覆盖「是什么 / 偏好是什么 / 团队约定是什么」以及会话内的上下文保持。但在长任务中，智能体往往形成**可重复的解决路径**（如某类 5xx 诊断顺序、容器启动排查清单、测试失败分层定位），这类**过程记忆**若在会话结束时不落盘，下次同类任务又要从零摸索。

**目标**：在**安全**、**频率**、**质量**三者约束下实现：（1）回合边界（默认 **Stop**）上自动审查并必要时 CREATE/UPDATE 用户级 skill；（2）用户通过 **`/evolve-review [topic]`** 手动沉淀；（3）自动与手动在「生成 `SKILL.md` + 写前扫描」上口径一致。

**价值流**（从对话到可复用技能）：

```text
   ┌─────────────┐      多步工具调用        ┌─────────────────────┐
   │ 用户与代理   │  ──────────────────▶   │ 非平凡、可推广的工作流  │
   │  自然对话    │      沉淀候选          │  （过程记忆候选）      │
   └─────────────┘                        └──────────┬──────────┘
                                                     │
                     self-evolution 插件               ▼
                                    ┌────────────────────────────────┐
                                    │  审查（自动 Stop / 手动命令）   │
                                    │  + 频率门控 + 写前安全扫描      │
                                    └────────────────┬──────────────┘
                                                     │
                                                     ▼
                       ┌──────────────────────────────────────────────┐
                       │  ~/.claude/skills/<category>-<name>/SKILL.md  │
                       │  后续会话可被 Skills 体系发现、按需加载全文    │
                       └──────────────────────────────────────────────┘
```

**设计溯源（非约束）**：思路与「周期性背景回顾 + 写入 skills + 写入前扫描」同源。**初版**写清 **Claude Code** 侧的插件、`hooks.json`、AgentHook、Skills 管线等叫法；换宿主时等价物可能改名或拆件，但**阈值计数与会话触发标志 + 全局写前校验 + 元技能生成正文**三层结构保持不变。

---

## 二、总体设计摘要

### 双路径、三条支柱与文字说明

```text
                    ┌─────────────────────────────┬─────────────────────────────┐
                    │          自动路径            │          手动路径            │
   ┌────────────────┼─────────────────────────────┼─────────────────────────────┤
   │ 谁来触发？      │ 主会话每一轮结束时的 Stop     │ 用户输入 /evolve-review      │
   ├────────────────┼─────────────────────────────┼─────────────────────────────┤
   │ 谁在审查？      │ Stop 上的 AgentHook（会话内） │ Task → skill-reviewer 子代理 │
   ├────────────────┼─────────────────────────────┼─────────────────────────────┤
   │ 频率限制？      │ 有（工具调用计数 + 标志文件）  │ 无（用户意图优先）            │
   ├────────────────┼─────────────────────────────┼─────────────────────────────┤
   │ 正文谁写？      │ SkillTool(evolve-skill-writer)│ 同左                        │
   ├────────────────┼─────────────────────────────┼─────────────────────────────┤
   │ 写前安检？      │ 全局 PreToolUse → 扫描脚本    │ 同左                        │
   └────────────────┴─────────────────────────────┴─────────────────────────────┘
```

**三条支柱**（下图与上文表格互补）：

```text
        ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────────┐
        │ ① 节流与触发标志 │   │② 全局写前校验  │   │  ③ 元技能单一信源        │
        └────────┬────────┘   └────────┬────────┘   └────────────┬────────────┘
                 │                    │                          │
                 ▼                    ▼                          ▼
   计数 nudge-state        每次写盘前 security-scan      evolve-skill-writer
   + Stop 写触发标志         路径白名单 + 四类内容        承载命名/正文/自检规则
   + AgentHook 先读标志      主体会话写项目代码早退        Hook 与子代理只做编排
```

- **节流与触发标志**：PostToolUse 计数、`pending_review`、`stop-gate` 写入 **`trigger-flag-*`**；AgentHook **首步读标志**，无标志则 StructuredOutput 结束，避免无效的完整审查回合。机理与调度层局限见[第七章「频率门控」小节](#七运行时事件脚本与门控)。  
- **全局写前校验**：通过 **PreToolUse** 挂载 **`security-scan.sh`**，覆盖 **Write / Edit / MultiEdit**；先按路径分层（skills 白名单 / `~/.claude` 非 skills / 工程源码早退），再对 skill 正文做四层内容检查（注入 / 危险 shell / **密钥** / 超长）；路径裁决 ASCII 见图见第七章「写前扫描与 AgentHook 编排」。  
- **元技能单一信源**： **`skills/evolve-skill-writer/SKILL.md`**；编排面不写长篇正文规范——细节见[第九章](#九元技能-evolve-skill-writer)。

### 协议与定时安排

**StructuredOutput（与 D11 同条）**：业务结果一律 **`ok: true` + `reason`**（创建 / 更新 / 跳过 / 门控未满足 / **写前扫描拦截** 均如此）；**禁止**用 **`ok: false`** 表达「本轮未生成 skill」——宿主侧常映射为失败或阻塞主会话。具体问题现象见[第十章](#十关键技术问题与约束)中 StructuredOutput 一行。

**各 Hook 建议 timeout / 异步**：

| Hook / 阶段 | 建议 timeout | 备注 |
|-------------|--------------|------|
| PostToolUse → `nudge-state.sh` | 约 2s，`async: true` | 只做计数与 JSON 更新，须快 |
| Stop → `stop-gate.sh` | 约 3s，同步 | 须在 AgentHook 前完成写标志 |
| Stop → AgentHook | 约 90s，同步 | 含多轮对话，为 CREATE 留足时间 |
| Stop → `stop-gate.sh --cleanup` | 约 2s，`async: true` | 删标志，失败策略见「触发标志残留」一行 |
| PreToolUse → `security-scan.sh` | 约 10s | 整文件内容可能较大 |

---

## 三、范围与显式边界

**范围内**：仅沉淀**过程型** skill（`~/.claude/skills/<category>-<name>/SKILL.md`，首版多为单文件）。交付物包括 `plugin.json`、`agents/`、`commands/`、`hooks/`、`skills/evolve-skill-writer/`、`templates/`（可选）、`scripts/`、`data/`（运行时，宜 gitignore）。

**做 / 不做对照**：

```text
   本插件做                     │   本插件不做
   ────────────────────────────│──────────────────────────────────
   把可复用工作流写成 skill     │   替代「事实记忆」memdir 等
   自动 + 手动两条沉淀路径       │   会话全文检索类能力（可另做插件）
   写前扫描与频率门控           │   修改 MEMORY.md 等系统前缀（破坏 cache）
   元技能统一正文质量           │   全自动合并/删除/评分全库 skill
                                │   交互式 eval / 浏览器报表闭环（非首版）
```

---

## 四、系统架构与数据流

### 全景与插件内挂载

```text
                         ┌──────────┐
                         │   用户    │
                         └────┬─────┘
              /evolve-review   │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Claude Code 主会话                             │
│  ┌────────────┐    Task      ┌─────────────────────────┐        │
│  │ Main Agent │ ────────────▶ │ skill-reviewer（手动路径） │        │
│  └─────┬──────┘              └───────────────────────────┘        │
│        │                                                          │
│        │ PostToolUse / Stop                                       │
│        ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │ hooks.json：计数 · Stop 门控 · AgentHook · 全局写前扫描   │      │
│  └─────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
         │                                    │
         │                                    │ SkillTool
         ▼                                    ▼
┌─────────────────────┐              ┌───────────────────────┐
│ ~/.claude/skills/   │◀─────────────│ evolve-skill-writer   │
│  目录下各 skill 目录 │   Write 前    │ （插件内唯一注册技能）  │
└──────────┬──────────┘   PreToolUse  └───────────────────────┘
           │
           │ 后续轮次：条件发现 + 按需读取全文
           ▼
┌─────────────────────┐
│ 主会话再次使用 Skill │
└─────────────────────┘
```

```text
                    plugin.json
                         │
       ┌─────────────────┼─────────────────┬─────────────────┐
       ▼                 ▼                 ▼                 ▼
   agents/          commands/           hooks/            skills/
 skill-reviewer    evolve-review       hooks.json      evolve-skill-writer/
     .md                .md                 │                  SKILL.md
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    │ PostToolUse  →  nudge-state  →  nudge-state.json │
                    │ Stop[0]      →  stop-gate   →  trigger-flag-*    │
                    │ Stop[1]      →  AgentHook（自动审查）              │
                    │ Stop[2]      →  stop-gate --cleanup            │
                    │ PreToolUse   →  security-scan（全员写盘）        │
                    └─────────────────────────────────────────────────┘
```

### 自动路径：单次 Stop 上发生什么

```text
  主会话：用户消息 → 模型与工具多轮 → 对用户回复完毕
                                              │
                                              ▼
                                      ┌───────────────┐
                                      │  Stop 事件     │
                                      └───────┬───────┘
                                              │
     ┌────────────────────────────────────────┼────────────────────────────────────────┐
     ▼                    ▼                    ▼                    ▼                    ▼
 stop-gate           AgentHook            （审查逻辑）          Write 意图         stop-gate
 写 trigger-flag     读 flag；            Read 对话、列 skill    触发 PreToolUse    --cleanup
 若 pending 为真      无 flag → 快速 SKIP   SkillTool 元技能      security-scan       删 flag
```

对应步骤说明：

1. 每次工具调用结束：**PostToolUse** 异步跑 `nudge-state.sh`，累计次数；达阈值则置 `pending_review`（见第七章计数状态机）。  
2. **Stop** 来临：**stop-gate.sh** 消费 pending，必要时写 **`trigger-flag-<session_id>.json`**。  
3. **AgentHook**：先 **Read** 标志；无则 **StructuredOutput** 跳过；有则 **Read** transcript、列 skill → **CREATE/UPDATE/SKIP**。  
4. 若 CREATE/UPDATE：**SkillTool(元技能)** → **Write**；写前 **PreToolUse** 执行 **`security-scan.sh`**。  
5. 末尾 **异步 cleanup** 删除触发标志，降低泄漏。

### 手动路径：从命令到落盘

```text
  用户：/evolve-review  optional-topic
              │
              ▼
  ┌─────────────────────────┐
  │ evolve-review.md 展开为   │  「用 Task 拉起 skill-reviewer，
  │ 对主代理的指示             │   带上 topic、最近对话、skills 目录说明」
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ 子代理 skill-reviewer    │  禁止再调 Task；可调 Skill / Read / Write…
  └────────────┬────────────┘
               │
               ▼
  SkillTool(evolve-skill-writer) ──▶ Write（经 security-scan）──▶ ~/.claude/skills/…
               │
               ▼
  主会话一句总结：CREATED / UPDATED / SKIPPED + 路径（若有）
```

---

## 五、关键决策

| ID | 决策 | 选择 | 简要理由 |
|----|------|------|----------|
| D1 | 能力边界 | 只做过程型 skill | 与事实记忆等分工清晰 |
| D2 | 自动审查实现 | **AgentHook**（会话内），不再起一个独立 CLI 进程 | 与主会话共用上下文与 transcript，运维简单 |
| D3 | 目录命名 | 扁平 **`<category>-<kebab-name>`** | **Skills 宿主实现通常只扫描 `skills` 根下「一层」子目录** |
| D4 | 产品切面 | 单 command、单 reviewer、单一元技能 | 降低命令面与维护面 |
| D5 | 频率 | **计数阈值 + 会话标志 + Hook 内首步短路** | 调度层未必能禁止 AgentHook 被调用，见§七「调度层与逻辑层门控」 |
| D6 | 默认写入范围 | `~/.claude/skills/`（用户级） | 过程知识常跨项目复用 |
| D7 | 手动子 Agent | `isolation: worktree`（若宿主支持） | 减少误写业务仓库 |
| D8 | 防递归 | 子代理禁用 **Task**；自动路径依赖宿主对子循环的工具黑名单 | 避免审查套审查 |
| D9 | `skills/` 用途 | **仅**注册 **evolve-skill-writer**；模板仍在 `templates/` | 避免无关文件被当 skill 暴露 |
| D10 | 可见性 | 默认 **`paths: ["**/*"]`** | 借助条件发现，同会话后续触达文件后可激活 metadata |
| D11 | StructuredOutput | **永远 `ok: true` + `reason`** | 「未生成 skill」不得用 `ok: false`，见§二协议 |
| D12 | Hook 事件 | 默认 **仅 Stop** | 压缩会话、退出进程等路径是否支持 AgentHook 需单独验证 |
| D13 | 安全挂载点 | **全局** `PreToolUse` | AgentHook 不读单个 agent 的 frontmatter，全局才能覆盖双路径 |
| D14 | PreToolUse 匹配 | **`Write|Edit|MultiEdit`** | 覆盖写盘类；放行策略在脚本内分层 |
| D15 | 正文来源 | **SkillTool(元技能)** | 规则可独立迭代 |
| D16 | 元技能路径 | **`skills/evolve-skill-writer/SKILL.md`** | 随插件分发 |
| D17 | 清单 | `plugin.json` 中 `skillsPath`、`metaSkillName` 等 | 配置化，避免硬编码分散 |
| D18 | YAML 硬校验 | 首版不做；模型自检 + `security-scan` | 降低首版复杂度；后续可加强 |

---

## 六、组件与目录结构

### 插件目录与 `plugin.json`

**目录树与职责**：

```text
~/.claude/plugins/self-evolution/
├── plugin.json                 # 插件清单：components、路径、默认 settings
├── README.md                   # 安装、环境变量、排错、禁用方式
├── LICENSE
├── agents/
│   └── skill-reviewer.md       # 手动路径 Agent：tools 含 Skill；disallowedTools 含 Task
├── commands/
│   └── evolve-review.md        # 仅允许 Task：指示如何传参给 skill-reviewer
├── hooks/
│   └── hooks.json              # PostToolUse / Stop（三段）/ PreToolUse
├── skills/
│   └── evolve-skill-writer/
│       └── SKILL.md            # 元技能：完整写作规范、自检清单、UPDATE 合并规则
├── templates/
│   └── skill.md                # 可选；若元技能已自包含模板段则可弱化
├── scripts/
│   ├── nudge-state.sh          # 计数、pending、consume-pending
│   ├── stop-gate.sh            # Stop 前写标志；--cleanup 删标志
│   └── security-scan.sh        # stdin JSON 取工具名与路径、抽内容、扫描
└── data/                       # 运行时；建议 .gitignore
    ├── nudge-state.json
    └── trigger-flag-<session_id>.json
```

**`plugin.json` 主要配置**：

| 字段 / settings 键 | 含义 | 典型值 |
|---------------------|------|--------|
| `name` | 插件标识 | `self-evolution` |
| `components` | 启用通道 | 含 `agents`,`commands`,`hooks`,`skills` |
| `agentsPath` / `commandsPath` / `hooksPath` / `skillsPath` | 相对插件根的路径 | `agents`,`commands`,`hooks/hooks.json`,`skills` |
| `nudgeIntervalToolCalls` | 多少次工具调用后置 `pending_review` | `10` |
| `skillTargetScope` | 用户级 / 项目级 skill 根（与实现约定） | `user` |
| `categoryWhitelist` | reviewer 允许的前缀类目 | `debug,refactor,...` |
| `maxSkillSizeBytes` | 与 `security-scan` 默认上限一致 | `15360` |
| `reviewerModel` | 子审查模型 | `inherit` 或具体模型名 |
| `metaSkillName` | SkillTool 调用的技能名 | `evolve-skill-writer` |

### 命令与 Agent 约定

| 文件 | 要点 |
|------|------|
| `commands/evolve-review.md` | Frontmatter **`allowed-tools: Task`**（或宿主等价）。正文：用 **Task** 拉起 **`skill-reviewer`**；传 **`$ARGUMENTS`** 为可选 topic；传最近约 30 轮会话与 `~/.claude/skills/` 说明；结束用**一句话**总结并给出新 skill 路径。 |
| `agents/skill-reviewer.md` | **tools**：至少 Read / Write / Edit / Glob / Grep / Bash / Skill（以宿主为准）。**disallowedTools**：含 Task、WebFetch、WebSearch 等。正文只保留：**决策规则**、**如何拼 context 调元技能**、**PreToolUse 拦截或 `BLOCKED` 后不自动重试**、**末行 CREATED/UPDATED/SKIPPED**；长规范均在元技能。 |

---

## 七、运行时：事件、脚本与门控

### Hook 事件一览

| 事件 | 类型 | 脚本 / 行为 | 设计意图 |
|------|------|-------------|----------|
| PostToolUse | command | `nudge-state.sh --event=post-tool-use` | 全工具 `*` 匹配；轻量；异步 |
| Stop | command | `stop-gate.sh` | 消费 pending、写触发标志；**先于** AgentHook |
| Stop | agent | AgentHook | 会话内审查 + 元技能 + Write |
| Stop | command | `stop-gate.sh --cleanup` | 删标志；异步 |
| PreToolUse | command | `security-scan.sh` | `Write|Edit|MultiEdit`；所有代理写盘共用 |

### 频率门控：计数、Stop 流水线、调度层局限与竞态

**计数状态机**（每个 `session_id` 在 `nudge-state.json` 中至少有 `count`、`pending_review`）：

```text
              ┌──────────────────────────────────────────────┐
              │     每个 session_id 在 nudge-state.json 中    │
              │     至少包含： count 、 pending_review        │
              └──────────────────────────────────────────────┘

    PostToolUse 到来
            │
            ▼
       count += 1
            │
            ├──────────────── count < 阈值 ────────────────▶ 仅保存，结束
            │
            └──────────────── count >= 阈值 ────────────────▶ count := 0
                                                      pending_review := true

    Stop 到来时 stop-gate 调用 consume-pending
            │
            ├──────── pending_review == false ────▶ 不写 trigger-flag，结束
            │
            └──────── pending_review == true  ────▶ 置 false，写 trigger-flag-*.json
```

**Stop 上 hook 顺序（示意）**：

```text
   Stop 事件
       │
       ├─────[1] stop-gate.sh ──────────▶ 可能创建 trigger-flag-*.json
       │
       ├─────[2] AgentHook ────────────▶ 读 flag → 审查 → 可能写 SKILL.md
       │
       └─────[3] stop-gate.sh --cleanup ─▶ 尽力删除 flag（常异步）
```

**调度层与逻辑层门控**：同一 Stop 上各 hook 通常按配置**串行**执行；但宿主 API **未必**支持「未创建 `trigger-flag-*` 则根本不调度 AgentHook」。因此 AgentHook **仍可能被调用**——本插件以 **触发标志** 表达「本轮是否进入完整审查」，并在 AgentHook **第一步**若无标志则立即 **StructuredOutput** 结束，将无效调用的成本限制在极短子轮次（在逻辑层补齐调度层无法表达的短路语义）。

**PostToolUse 与 Stop 竞态**：最后一次工具调用的计数尚未落盘，Stop 已触发 → 可能晚一轮才触发审查。缓解：PostToolUse 短超时 + 异步 + 文件锁；产品接受「近似阈值」。

### 写前扫描与 AgentHook 编排

**`security-scan.sh` 路径裁决（概念）**：

```text
                         收到 PreToolUse：即将写入的路径 + 内容
                                         │
                                         ▼
                         目标路径是 ~/.claude/skills/*/SKILL.md ?
                              │                    │
                             是                   否
                              │                    │
                              ▼                    ▼
                    进入「内容四层检查」     目标在 ~/.claude/ 但非 skills/ ?
                    （注入 / 危险 shell / 密钥 / 大小）   │              │
                              │                    是              否
                              │                    │                │
                              ▼                    ▼                ▼
                         不通过 → 拦截           拦截           放行（项目源码等）
                         通过   → 放行
```

**AgentHook 内五步**（写入 `hooks.json` 的 `prompt`，措辞以实现为准）：① Read 触发标志，无则 StructuredOutput（`ok: true` + 跳过原因）；② Read transcript、列 skill，判定 SKIP / CREATE / UPDATE；③ SkillTool(元技能, context)；④ Write，遇 BLOCKED 不重试；⑤ StructuredOutput：业务语义写在 `reason`，**`ok` 恒为 true**（同§二·D11）。

---

## 八、命名、Frontmatter 与产出形态

**目录与扁平命名**：宿主一般只把 `~/.claude/skills/` 下**一层子目录**当作一个 skill，故用 **`<category>-<kebab-name>`** 单目录；**不要**用深层路径代替类目（如 `python/web-debug/SKILL.md` 往往不会被当作一个 skill 加载）。

```text
   允许（一层子目录 = 一个 skill）          不推荐（嵌套，通常不会被加载）
   ─────────────────────────────            ─────────────────────────────
   ~/.claude/skills/                       ~/.claude/skills/
     debug-fastapi-5xx/                       python/
       SKILL.md                                web-debug/
                                                 SKILL.md   ← 易被忽略
```

**Frontmatter 必填字段**：

| 字段 | 要求 |
|------|------|
| `name` | 与目录名完全一致 |
| `description` | 单句、≤约 120 字符；**偏积极触发**，但不含隐私路径、密钥、项目独有内网地址 |
| `when_to_use` | 多行；含**自然语言触发**与简短示例说法 |
| `paths` | 默认 **`["**/*"]`**，换合同会话可见性；metadata 曝光面由 SKIP 与描述收窄对冲 |
| `allowed-tools` | 空格分隔，与 workflow 真实需求对齐 |
| `version` | semver；CREATE 常见 `1.0.0`；UPDATE 递增小版本 |

**正文结构建议**：**标题** → **When to use** → **Steps** → **Example** → **Common pitfalls**；步骤用**祈使句**；示例须**泛化**。**手工编辑**：用户可直接改 `~/.claude/skills/`，全局 PreToolUse 同样生效；UPDATE 时需 Read 旧文件再合并（策略由元技能规定）。

---

## 九、元技能 evolve-skill-writer

**在流水线中的位置**（审查者只编排，正文规则在元技能内）：

```text
        skill-reviewer / AgentHook
                    │
                    │  context 字符串（决策、名称、摘要、步骤、注意事项）
                    ▼
        ┌───────────────────────┐
        │ evolve-skill-writer    │
        │ （插件内 SKILL.md）     │
        └───────────┬───────────┘
                    │
                    ▼  完整 SKILL.md 正文（或 ABORT）
              Write（经 security-scan）
```

**context 建议字段**（实现可打成一行多键值或小块 YAML，由调用方与元技能约定）：

| 字段 | 含义 |
|------|------|
| `decision` | `CREATE` 或 `UPDATE` |
| `proposed_name` | 如 `debug-fastapi-5xx` |
| `existing_skill_path` | 仅 UPDATE，指向现有 `SKILL.md` |
| `workflow_summary` | 3～5 句，抽象后的可推广流程 |
| `key_steps` | 编号逻辑步骤 |
| `context_notes` | 依赖、禁忌、易错点 |

**产出契约**：成功 → 完整 **`SKILL.md`** 且过自检清单；失败 → **`ABORT: <reason>`**，调用方映射为 **`SKIPPED: …`**，**不**写出不完整文件。

**与「完整 skill 工厂」的分工**：

| 维度 | evolve-skill-writer | 完整工厂（若另有） |
|------|---------------------|-------------------|
| 场景 | Stop / 手动审查，**非交互** | 人机多轮迭代 |
| 时长 | 受 AgentHook 超时约束 | 可很长 |
| 依赖 | **禁止**嵌套子任务、禁止跑评分脚本 | 可有 |
| 输出 | 通常单文件 | 可多文件 |

**降级**：若子循环中 **Skill** 工具不可用，则 **Read** **`${CLAUDE_PLUGIN_ROOT}/skills/evolve-skill-writer/SKILL.md`** 按规则手写正文，可落地但体验弱于 SkillTool 分级加载。

---

## 十、关键技术问题与约束

本章列**机制级**风险与对策；命名、Frontmatter、`paths` 默认值与扁平目录的实践说明以[第八章](#八命名frontmatter-与产出形态)为准，此处不重复赘述。

```text
   新建 SKILL.md（含 paths: ["**/*"]）
              │
              ▼
   后续轮次：触及工作区文件 → 条件 skill 激活 → metadata 进入动态列表
              │
              ▼
   模型见摘要；全文仍由 Skill 工具按需读取（不靠改 MEMORY.md「热插」）
```

| 主题 | 现象 / 约束 | 处理要点 |
|------|-------------|----------|
| **同会话可见性** | 进程内可能对 skill 列表有缓存 | 默认策略与 Frontmatter 见§八；本图概括「条件发现 → metadata」链 |
| **扁平目录** | 宿主通常只扫描 `skills` 下一层子目录 | 目录形态与反例见§八；与 D3 一致 |
| **递归审查** | 审查者再开子任务会套娃 | 子代理禁用 Task；黑名单以宿主为准；测试验证无「审查风暴」 |
| **Prefix cache** | 改系统记忆文件会破坏前缀缓存 | 内容只放在 `~/.claude/skills/` 与按需 Skill 读取，**不**把整篇 skill 塞进 `MEMORY.md` |
| **StructuredOutput** | `ok: false` 易被宿主当作硬失败 | **一律** `ok: true` + `reason`；协议见§二、D11 |
| **Stop 以外** | 压缩、退出等阶段 AgentHook 行为未必一致 | **首版只承诺交互会话中的 Stop**（D12） |
| **全局 PreToolUse 性能** | 每次写盘都经过脚本 | 非 skills 路径**早退**；目标单次约几十毫秒；偏高再优化 |
| **触发标志残留** | `--cleanup` 失败残留 `trigger-flag-*` | 幂等删除、`session_id` 隔离、可选 TTL；偶发多一轮短审查可接受 |

---

## 十一、实施计划与验收

**里程碑（示例）**

| 阶段 | 内容 | 退出信号（示例） |
|------|------|------------------|
| A | 最小 AgentHook，只返回 `ok:true` | Stop 后可见执行痕迹，主会话不卡死 |
| B | 对照 `ok:false` 行为 | 确认产品侧绝不用 `ok:false` 表示业务跳过 |
| C | 全局 PreToolUse + 高频项目写 | 延迟可接受；skills 路径仍严格扫描 |
| D | 计数 + 标志 + AgentHook 早退 | 未达阈值短路径；达阈值可落盘 |
| E | 手动路径端到端 | `/evolve-review` 能生成测试 skill |
| F | 元技能接入双路径 | 结构一致 |
| G | 红队 | 越权与四类内容均拦截 |
| H | 文档与发布清单 | 可安装、可关闭、可清理 data |

**验收要点（节选）**

| 维度 | 检查项 |
|------|--------|
| **功能** | 手动 / 自动均能生成；未达频率时 `reason` 合理；主会话无异常 blocking；新 skill 在后续轮次可被条件发现（可复现实验下） |
| **安全** | 诱导写 `/tmp`、`~/.ssh`、`~/.claude` 非 skills 均拦截；四类内容用例覆盖；写项目源码路径不误拦 |
| **一致性** | 双路径产出章节结构一致；元技能被调用或有 Read 降级记录 |

---

## 十二、风险、待确认与后续方向

**风险与缓解**

| 风险 | 缓解 |
|------|------|
| AgentHook 内 Skill 工具不可用 | 首周验证；Read 元技能降级 |
| 全局扫描误伤 / 漏网 | 分层路径逻辑；可选环境变量关闭 |
| 元技能被篡改 | 发布渠道可信；安装后可自行校验 |

**上线前待确认**

| 项 | 说明 |
|----|------|
| 环境变量替换 | **`${CLAUDE_PLUGIN_ROOT}`**、**`${session_id}`** 等在 Hook prompt 中是否按预期替换 |
| Hook 串行性 | **同一 Stop** 上各 hook 是否**严格串行**（影响标志与审查顺序） |
| PostToolUse 与 Stop | 异步完成先后是否可接受 |
| Skill 工具 | 子循环中实际工具名与权限 |
| 其它事件 | **SessionEnd / 压缩** 等是否挂自动审查（默认不承诺） |

**后续方向（非首版）**：**多宿主适配**——对照各宿主是否具备「会话内子循环 / 等价 AgentHook」「全局写前钩子」「Skills 或可迁移的落盘格式」；缺项用兼容挡位（如无 AgentHook 则异步子进程审查）并回写设计取舍。其它：PreToolUse **frontmatter 静态校验**；**description** 离线优化；存量 skill **二轮精修**命令；若需「未达阈值则调度层永不调度 AgentHook」须 **worker/进程** 模型；团队同步、使用统计、与**事实记忆提取**协同等。文首「能力抽象」四要素（审查闭环、**节流与触发标志**、写前校验、元技能产出）仍为多宿主薄适配时的对齐轴。

---

**文档与实现**：本设计供产品与研发共识使用；以插件包内 **`plugin.json`、`hooks/hooks.json`、各脚本与元技能正文** 为实现准绳，变更应同步更新本文表述。
