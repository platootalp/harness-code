# OpenHarness 架构图集

## 1. 系统上下文图（C4 Level 1）

展示 OpenHarness 在运行时与外部系统的边界和交互关系。

```mermaid
graph TD
    subgraph "用户 / 上游调用者"
        USER["👤 终端用户\noh 命令"]
        IM_USER["💬 IM 用户\nSlack / Discord / 飞书 / 钉钉"]
        CRON["⏰ Cron 调度器\ntime → oh --print"]
    end

    subgraph "OpenHarness 系统"
        OH["🏗️ OpenHarness\nAI Agent 运行时\n─────────────────\n• 推理引擎 (QueryEngine)\n• 43+ 内置工具\n• MCP 客户端\n• 多智能体编排\n• 插件系统\n• 多通道适配"]
    end

    subgraph "外部依赖（不可控）"
        ANTHROPIC["🤖 Anthropic API\nClaude 模型推理"]
        OPENAI["🤖 OpenAI / 兼容 API\nKimi / GLM / MiniMax / Gemini"]
        COPILOT["🔑 GitHub Copilot\nOAuth Device Flow"]
        DOCKER["📦 Docker 守护进程\n沙箱执行后端"]
        FS["💾 文件系统\n~/.openharness/\n项目 .openharness/"]
        IM_PLAT["📡 IM 平台 API\nSlack / Discord / 飞书 / 钉钉\nTelegram / WhatsApp / QQ"]
        MCP_EXT["🔌 MCP 服务器\nstdio / HTTP\nGitHub / DB / Search..."]
    end

    USER -->|"oh 命令"| OH
    IM_USER -->|"消息推送"| IM_PLAT
    CRON -->|"定时触发"| OH

    OH -->|"HTTPS 流式调用"| ANTHROPIC
    OH -->|"HTTPS 流式调用"| OPENAI
    OH -->|"OAuth 认证"| COPILOT
    OH -->|"docker exec"| DOCKER
    OH -->|"读写配置/会话/日志"| FS
    OH <-->|"MCP 协议\nstdio / HTTP"| MCP_EXT
    OH <-->|"消息收发"| IM_PLAT
```

---

## 2. 容器/进程视图（C4 Level 2）

展示 OpenHarness 运行时的进程边界与通信方式。

```mermaid
graph TD
    subgraph "主进程 (python -m openharness)"
        CLI["CLI / REPL\ncli.py"]
        ENGINE["QueryEngine\n推理引擎"]
        TOOLS["ToolRegistry\n内置工具 43+"]
        PERM["PermissionChecker\n权限检查"]
        HOOKS["HookExecutor\n生命周期钩子"]
        MEM["Memory\n持久记忆"]
        PROMPTS["Prompts\n系统提示词组装"]
    end

    subgraph "MCP 子进程 (stdio)"
        MCP1["MCP Server A\npython -m xxx"]
        MCP2["MCP Server B\nnpx @xxx/mcp"]
    end

    subgraph "Worker 子进程"
        W1["Worker Agent 1\npython -m openharness\n--task-worker"]
        W2["Worker Agent 2\npython -m openharness\n--task-worker"]
    end

    subgraph "Bridge 子进程"
        BRIDGE["Bridge Session\nopenharness bridge-run"]
    end

    subgraph "守护进程"
        CROND["Cron Scheduler\n守护进程"]
    end

    subgraph "外部服务"
        API["AI API\nAnthropic / OpenAI"]
        DOCKER_D["Docker"]
    end

    CLI --> ENGINE
    ENGINE --> TOOLS
    ENGINE --> PERM
    ENGINE --> HOOKS
    ENGINE --> MEM
    ENGINE --> PROMPTS

    ENGINE -->|"HTTPS 流式"| API
    TOOLS -->|"subprocess.run"| DOCKER_D

    ENGINE <-.->|"MCP JSON-RPC\nstdin/stdout"| MCP1
    ENGINE <-.->|"MCP JSON-RPC\nstdin/stdout"| MCP2

    ENGINE -->|"spawn\nstdin: 任务描述"| W1
    ENGINE -->|"spawn\nstdin: 任务描述"| W2
    W1 -->|"stdout: &lt;task-notification&gt;"| ENGINE
    W2 -->|"stdout: &lt;task-notification&gt;"| ENGINE

    ENGINE -->|"spawn"| BRIDGE
    BRIDGE <-->|"WebSocket"| IM_GW["OHMO Gateway"]

    CROND -->|"fork + exec\noh --print"| ENGINE
```

---

## 3. 五层逻辑架构图

展示 OpenHarness 从用户触达到外部系统的五层逻辑分层。

```mermaid
graph TB
    subgraph "第 1 层 — CLI / REPL（用户入口）"
        direction LR
        CLI_MAIN["oh 命令\n交互/非交互/恢复"]
        CLI_AUTH["oh auth\n多提供商认证"]
        CLI_MCP["oh mcp\nMCP 服务器管理"]
        CLI_PLUGIN["oh plugin\n插件管理"]
        CLI_CRON["oh cron\n定时任务"]
        CLI_PROVIDER["oh provider\nProvider 切换"]
    end

    subgraph "第 2 层 — Engine / Query（推理引擎）"
        direction LR
        QE["QueryEngine\n对话历史 & 推理循环"]
        QCTX["QueryContext\n上下文打包"]
        COST["CostTracker\n成本跟踪"]
        COMPACT["AutoCompactor\n上下文压缩"]
    end

    subgraph "第 3 层 — Tools / MCP（工具抽象）"
        direction LR
        TREG["ToolRegistry\n内置工具注册"]
        MCP_MGR["McpClientManager\nMCP 客户端"]
        PCHK["PermissionChecker\n权限模式"]
        SKILL["SkillTool\n技能加载"]
    end

    subgraph "第 4 层 — Coordinator / Swarm（多智能体编排）"
        direction LR
        COORD["CoordinatorMode\n协调者角色"]
        SWARM["SwarmTeamLifecycle\n团队生命周期"]
        TASK["BackgroundTaskManager\n任务 & 子进程管理"]
        BRIDGE["BridgeSessionManager\n桥接会话"]
        WT["WorktreeManager\nGit Worktree 隔离"]
    end

    subgraph "第 5 层 — Channels / OHMO（通信通道）"
        direction LR
        CH["ChannelAdapter\n通道适配器"]
        EB["EventBus\n事件总线"]
        IM["Slack / Discord / 飞书\n钉钉 / Telegram / QQ"]
    end

    subgraph "配置层（横切关注点）"
        direction LR
        SETTINGS["Settings\n配置 & Provider Profile"]
        PLUGIN_L["PluginLoader\n插件发现 & 加载"]
        HOOKS_L["HookRegistry\n生命周期钩子"]
        MEMORY["Memory\nMEMORY.md 持久记忆"]
    end

    CLI_MAIN --> QE
    CLI_AUTH --> SETTINGS
    CLI_MCP --> MCP_MGR
    CLI_PLUGIN --> PLUGIN_L
    CLI_CRON --> TASK
    CLI_PROVIDER --> SETTINGS

    QE --> QCTX
    QE --> COST
    QE --> COMPACT
    QCTX --> TREG
    QCTX --> MCP_MGR
    QCTX --> PCHK
    QCTX --> SKILL

    QE --> COORD
    COORD --> TASK
    COORD --> SWARM
    SWARM --> WT
    TASK --> BRIDGE

    CH --> EB
    EB --> QE

    SETTINGS -.-> MCP_MGR
    SETTINGS -.-> QE
    PLUGIN_L -.-> SKILL
    PLUGIN_L -.-> MCP_MGR
    PLUGIN_L -.-> HOOKS_L
```

---

## 4. 核心推理循环时序图

展示用户输入到最终输出的完整调用链路。

```mermaid
sequenceDiagram
    actor User
    participant REPL as CLI / REPL
    participant QE as QueryEngine
    participant API as AI API Client
    participant Perm as PermissionChecker
    participant Tool as ToolRegistry
    participant MCP as McpClientManager
    participant Hook as HookExecutor

    User->>REPL: 输入 prompt
    REPL->>QE: submit_message(prompt)
    QE->>QE: 追加消息到 _messages

    loop 推理循环（直到无 tool_use）
        QE->>QE: auto_compact_if_needed()
        QE->>API: stream_message(messages)
        API-->>QE: text_delta (流式)
        QE-->>REPL: AssistantTextDelta
        API-->>QE: message_complete + tool_uses

        alt 模型请求工具调用
            loop 每个工具调用
                QE->>Perm: check(tool_name, args)
                alt 权限通过
                    Perm-->>QE: allow
                else 需要用户确认
                    Perm-->>REPL: 确认对话框
                    User-->>Perm: y / n
                end

                QE->>Hook: execute(PRE_TOOL_USE)
                QE->>Tool: execute(tool_name, args)
                Tool-->>QE: ToolResult
                QE->>Hook: execute(POST_TOOL_USE)
            end
            QE->>QE: 追加工具结果到 _messages
        else 模型无工具调用
            Note over QE: 推理循环结束
        end
    end

    QE-->>REPL: 完成
    REPL-->>User: 显示最终回复
```

---

## 5. 工具体系架构图

展示 43+ 内置工具的分类与注册机制。

```mermaid
graph TD
    subgraph "工具入口"
        QE["QueryEngine\n模型决定调用工具"]
    end

    subgraph "权限层"
        PERM["PermissionChecker\n─────────────\n• default: 危险操作需确认\n• plan: 只读自动，写需确认\n• full_auto: 全部自动"]
    end

    subgraph "ToolRegistry"
        direction TB
        subgraph "文件 I/O"
            BASH["BashTool\nsubprocess 执行"]
            READ["FileReadTool\n读文件"]
            WRITE["FileWriteTool\n写文件"]
            EDIT["FileEditTool\n精确替换"]
            GLOB["GlobTool\n文件搜索"]
            GREP["GrepTool\n内容搜索"]
            NB["NotebookEditTool\nJupyter 编辑"]
        end

        subgraph "搜索"
            WEBF["WebFetchTool\nURL 抓取"]
            WEBS["WebSearchTool\nWeb 搜索"]
            LSP["LspTool\n语言服务"]
        end

        subgraph "智能体"
            AGENT["AgentTool\n子智能体"]
            SEND["SendMessageTool\n发送消息"]
            TEAM_C["TeamCreateTool"]
            TEAM_D["TeamDeleteTool"]
        end

        subgraph "任务"
            TC["TaskCreateTool"]
            TG["TaskGetTool"]
            TL["TaskListTool"]
            TU["TaskUpdateTool"]
            TS["TaskStopTool"]
            TO["TaskOutputTool"]
        end

        subgraph "MCP"
            MCP_A["McpToolAdapter\nMCP 工具适配"]
            MCP_L["ListMcpResourcesTool"]
            MCP_R["ReadMcpResourceTool"]
            MCP_AUTH["McpAuthTool"]
        end

        subgraph "模式 & 调度"
            PLAN["EnterPlanModeTool"]
            EPLAN["ExitPlanModeTool"]
            WTREE["EnterWorktreeTool"]
            CRON_C["CronCreateTool"]
            CRON_L["CronListTool"]
        end

        subgraph "元工具"
            SKILL_T["SkillTool\n技能调用"]
            CONFIG["ConfigTool"]
            ASK["AskUserQuestionTool"]
            BRIEF["BriefTool"]
        end
    end

    QE --> PERM
    PERM --> BASH
    PERM --> READ
    PERM --> WRITE
    PERM --> AGENT
    PERM --> MCP_A
    PERM --> SKILL_T
```

---

## 6. 多智能体编排架构图

展示 Coordinator → Worker → Swarm 的多智能体编排机制。

```mermaid
graph TD
    subgraph "Coordinator 进程"
        C_QE["QueryEngine\n(协调者模式)"]
        C_PROMPT["Coordinator 系统提示词\n─────────────\n编排策略模板"]
        C_TOOLS["编排工具集\n─────────────\n• agent: 启动 Worker\n• send_message: 后续指令\n• task_stop: 停止 Worker"]
    end

    subgraph "Worker 进程 1"
        W1_QE["QueryEngine\n(执行者模式)"]
        W1_TOOLS["完整工具集\n─────────────\nBash / File / Grep\n...43+ 工具"]
        W1_WT["Git Worktree\n/.git/worktrees/w1/"]
    end

    subgraph "Worker 进程 2"
        W2_QE["QueryEngine\n(执行者模式)"]
        W2_TOOLS["完整工具集"]
        W2_WT["Git Worktree\n/.git/worktrees/w2/"]
    end

    subgraph "Swarm 团队管理"
        SWARM_LC["SwarmTeamLifecycle\n─────────────\n• create_team()\n• register_teammate()\n• destroy_team()"]
        EXEC["TeammateExecutor\n─────────────\n• subprocess (默认)\n• in-process\n• tmux\n• iTerm2"]
        MAILBOX["Mailbox\n─────────────\nWorker 间消息传递\n临时文件实现"]
        LOCK["Lockfile\n─────────────\n防止并发写入"]
        PERM_SYNC["PermissionSync\n─────────────\n权限策略同步"]
    end

    C_QE --> C_PROMPT
    C_QE --> C_TOOLS
    C_TOOLS -->|"spawn\nstdin: 任务描述"| W1_QE
    C_TOOLS -->|"spawn\nstdin: 任务描述"| W2_QE
    W1_QE --> W1_TOOLS
    W2_QE --> W2_TOOLS
    W1_TOOLS --> W1_WT
    W2_TOOLS --> W2_WT

    W1_QE -->|"stdout:\n<task-notification>"| C_QE
    W2_QE -->|"stdout:\n<task-notification>"| C_QE

    C_QE --> SWARM_LC
    SWARM_LC --> EXEC
    W1_QE -.->|"消息"| MAILBOX
    MAILBOX -.->|"消息"| W2_QE
    W1_QE -.-> LOCK
    C_QE -.-> PERM_SYNC
    PERM_SYNC -.-> W1_QE
```

---

## 7. MCP 集成架构图

展示 MCP 客户端如何发现和调用外部 MCP 工具。

```mermaid
graph LR
    subgraph "OpenHarness 主进程"
        QE["QueryEngine"]
        MGR["McpClientManager\n─────────────\n• connect_all()\n• list_tools()\n• call_tool()\n• read_resource()"]
        ADAPTER["McpToolAdapter\n─────────────\n将 MCP 工具适配为\nBaseTool 接口"]
        REG["ToolRegistry"]
    end

    subgraph "stdio 传输"
        MCP_S1["MCP Server A\npython -m github_mcp"]
        MCP_S2["MCP Server B\nnpx @modelcontextprotocol/server-filesystem"]
    end

    subgraph "HTTP 传输"
        MCP_H1["MCP Server C\nhttps://mcp.example.com/messages"]
    end

    subgraph "配置来源"
        SETTINGS["settings.json\nmcp_servers 配置"]
        PLUGIN["插件 .mcp.json"]
    end

    QE -->|"模型决定调用\nMCP 工具"| MGR
    SETTINGS --> MGR
    PLUGIN --> MGR
    MGR -->|"初始化\nlist_tools()"| ADAPTER
    ADAPTER --> REG
    REG -->|"透明调用"| QE

    MGR <-.->|"stdin/stdout\nJSON-RPC"| MCP_S1
    MGR <-.->|"stdin/stdout\nJSON-RPC"| MCP_S2
    MGR <-.->|"HTTPS\nStreamable HTTP"| MCP_H1
```

---

## 8. 插件系统架构图

展示插件的发现、加载与注册机制。

```mermaid
graph TD
    subgraph "插件来源"
        USER_DIR["~/.openharness/plugins/\n用户级插件"]
        PROJ_DIR[".openharness/plugins/\n项目级插件"]
    end

    subgraph "PluginLoader"
        LOAD["load_plugins()\n─────────────\n扫描目录 → 解析 manifest → 加载组件"]
        SKILL_L["_load_plugin_skills()\n─────────────\n*.md → SkillDefinition"]
        CMD_L["_load_plugin_commands()\n─────────────\ncommands/*.md → CommandDef"]
        AGENT_L["_load_plugin_agents()\n─────────────\nagents/*.md → AgentDefinition"]
        HOOK_L["_load_plugin_hooks()\n─────────────\nhooks.json → HookConfig"]
        MCP_L["_load_plugin_mcp()\n─────────────\n.mcp.json → McpServerConfig"]
    end

    subgraph "插件注册目标"
        SKILL_REG["SkillTool\n技能注册"]
        CMD_REG["CommandRegistry\n命令注册"]
        AGENT_REG["AgentTool\n智能体注册"]
        HOOK_REG["HookExecutor\n钩子注册"]
        MCP_REG["McpClientManager\nMCP 注册"]
    end

    subgraph "插件目录结构"
        PLUGIN_DIR["my-plugin/\n─────────\n├── plugin.json (manifest)\n├── skills/\n│   └── code-review.md\n├── commands/\n│   └── commit.md\n├── agents/\n│   └── reviewer.md\n├── hooks.json\n└── .mcp.json"]
    end

    USER_DIR --> LOAD
    PROJ_DIR --> LOAD
    LOAD --> SKILL_L
    LOAD --> CMD_L
    LOAD --> AGENT_L
    LOAD --> HOOK_L
    LOAD --> MCP_L

    SKILL_L --> SKILL_REG
    CMD_L --> CMD_REG
    AGENT_L --> AGENT_REG
    HOOK_L --> HOOK_REG
    MCP_L --> MCP_REG

    PLUGIN_DIR -.-> LOAD
```

---

## 9. 通道/OHMO 集成架构图

展示多 IM 平台的接入与消息路由机制。

```mermaid
graph TD
    subgraph "IM 平台"
        SLACK["Slack\nWeb API / RTM"]
        DISCORD["Discord\nREST / Gateway"]
        FEISHU["飞书\nEvents API"]
        DINGTALK["钉钉\nWebhook"]
        TELEGRAM["Telegram\nBot API"]
        QQ["QQ\ngo-cqhttp"]
        EMAIL["Email\nSMTP/IMAP"]
    end

    subgraph "Channel 适配器层"
        direction TB
        CA["ChannelAdapter 接口\n─────────────\n• send(msg)\n• receive() → Message\n• connect() / disconnect()"]
        CA_SLACK["SlackAdapter"]
        CA_DISC["DiscordAdapter"]
        CA_FEI["FeishuAdapter"]
        CA_DING["DingTalkAdapter"]
        CA_TG["TelegramAdapter"]
        CA_QQ["QQAdapter"]
        CA_EMAIL["EmailAdapter"]
    end

    subgraph "消息路由"
        EB["EventBus\n─────────────\n异步事件分发\n消息生产/消费"]
        OHMO["OHMO Gateway\n─────────────\nWebSocket 反向代理\n会话生命周期"]
        BRIDGE["BridgeSessionManager\n─────────────\nBridge 子会话"]
    end

    subgraph "OpenHarness 核心"
        QE["QueryEngine\n推理引擎"]
    end

    SLACK <--> CA_SLACK
    DISCORD <--> CA_DISC
    FEISHU <--> CA_FEI
    DINGTALK <--> CA_DING
    TELEGRAM <--> CA_TG
    QQ <--> CA_QQ
    EMAIL <--> CA_EMAIL

    CA_SLACK --> CA
    CA_DISC --> CA
    CA_FEI --> CA
    CA_DING --> CA
    CA_TG --> CA
    CA_QQ --> CA
    CA_EMAIL --> CA

    CA --> EB
    EB --> QE

    CA <---> OHMO
    OHMO <---> BRIDGE
    BRIDGE --> QE
```

---

## 10. 配置 & 认证流程图

展示 Settings 的多层优先级与 Provider 认证解析。

```mermaid
graph TD
    subgraph "配置来源（优先级从高到低）"
        CLI_ARGS["1️⃣ CLI 参数\n--model / --api-key\n--permission-mode"]
        ENV["2️⃣ 环境变量\nANTHROPIC_API_KEY\nOPENAI_API_KEY\nMOONSHOT_API_KEY"]
        FILE["3️⃣ 配置文件\n~/.openharness/settings.json"]
        DEFAULTS["4️⃣ 默认值\ndefault_provider_profiles"]
    end

    subgraph "Settings 解析"
        LOAD["load_settings()\n─────────────\n合并多层配置"]
        PROFILE["ProviderProfile\n─────────────\n• label: 'claude-api'\n• provider: 'anthropic'\n• api_format: 'anthropic'\n• auth_source: 'api_key'\n• model: 'claude-sonnet-4-6'\n• base_url: null"]
        RESOLVE["resolve_auth()\n─────────────\n按 auth_source 分支解析"]
    end

    subgraph "认证方式"
        API_KEY["api_key\n─────────────\n直接 API Key\n环境变量 / settings"]
        OAUTH["copilot_oauth\n─────────────\nOAuth Device Code\nsave_copilot_auth()"]
        BRIDGE_AUTH["claude_subscription\n─────────────\nClaude CLI 桥接\n~/.claude/auth.json"]
        CODEX["codex_subscription\n─────────────\nCodex CLI 桥接\n本地 session"]
    end

    subgraph "API 客户端"
        ANTHROPIC_C["AnthropicApiClient\nanthropic 格式"]
        OPENAI_C["OpenAICompatibleClient\nopenai 格式"]
        COPILOT_C["CopilotClient\ncopilot 格式"]
    end

    CLI_ARGS --> LOAD
    ENV --> LOAD
    FILE --> LOAD
    DEFAULTS --> LOAD

    LOAD --> PROFILE
    PROFILE --> RESOLVE

    RESOLVE -->|"api_key"| API_KEY
    RESOLVE -->|"copilot_oauth"| OAUTH
    RESOLVE -->|"claude_subscription"| BRIDGE_AUTH
    RESOLVE -->|"codex_subscription"| CODEX

    API_KEY -->|"anthropic 格式"| ANTHROPIC_C
    API_KEY -->|"openai 格式"| OPENAI_C
    OAUTH --> COPILOT_C
    BRIDGE_AUTH --> ANTHROPIC_C
    CODEX --> OPENAI_C
```
