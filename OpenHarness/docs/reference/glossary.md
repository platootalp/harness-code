# OpenHarness 术语表

> 本术语表收录 OpenHarness 项目的核心术语定义，包含中文术语、英文原词、代码符号及源码证据。
> 最后更新：与源码同步（v0.1.x）

---

## 术语分类索引

- [A: Agent 系统](#a-agent-系统)
- [B: Bridge 与渠道](#b-bridge-与渠道)
- [C: Config 与设置](#c-config-与设置)
- [D: Docker 与沙箱](#d-docker-与沙箱)
- [E: Engine 与查询](#e-engine-与查询)
- [H: Hooks 与生命周期](#h-hooks-与生命周期)
- [M: MCP 与协议](#m-mcp-与协议)
- [P: Permissions 与安全](#p-permissions-与安全)
- [S: Swarm 与团队](#s-swarm-与团队)
- [T: Tasks 与后台任务](#t-tasks-与后台任务)
- [U: UI 与交互](#u-ui-与交互)
- [其他](#其他)

---

## A: Agent 系统

### 1. Agent Harness（Agent 挽具）

**中文术语：** Agent 挽具（Agent Harness）
**英文原词：** Agent Harness
**代码符号：** 无特定符号，文档中描述为 OpenHarness 核心概念

**定义：** Agent Harness 是包裹在 LLM（大语言模型）外围的完整基础设施，使 LLM 成为可工作的功能性 Agent。模型提供智能，Harness 提供手（工具）、眼（感知）、记忆和安全边界。

**源码证据：** `README.md` -> Agent Harness 定义，描述为 Tools + Knowledge + Observation + Action + Permissions

**关联术语：** QueryEngine、ToolRegistry、Swarm、Teammate

---

### 2. Coordinator（协调器）

**中文术语：** 协调器
**英文原词：** Coordinator
**代码符号：** `is_coordinator_mode()`、`CLAUDE_CODE_COORDINATOR_MODE`

**定义：** 在多 Agent 架构中扮演领导者角色的 Agent，负责分解任务、派生工作器、汇总结果。Coordinator 通过 `agent` 工具派生工作器，通过 `send_message` 工具继续工作器。

**源码证据：**
- `src/openharness/coordinator/coordinator_mode.py` -> `is_coordinator_mode()` 判断是否运行在协调器模式
- `src/openharness/coordinator/coordinator_mode.py` -> `get_coordinator_system_prompt()` 返回协调器系统提示

**关联术语：** Teammate、TeamRegistry、SpawnResult

---

### 3. Teammate（队友）

**中文术语：** 队友
**英文原词：** Teammate
**代码符号：** `TeammateSpawnConfig`、`SubprocessBackend`、`InProcessBackend`

**定义：** 由 Coordinator 派生的子 Agent，在 Swarm 团队中执行具体任务。Teammate 可以是子进程（subprocess）或进程内（in_process）运行。

**源码证据：**
- `src/openharness/swarm/subprocess_backend.py` -> `SubprocessBackend.spawn()` 派生子进程 teammate
- `src/openharness/swarm/types.py` -> `TeammateSpawnConfig` 派生配置数据类

**关联术语：** Coordinator、Swarm、SpawnResult、BackendRegistry

---

### 4. TeammateExecutor（队友执行器）

**中文术语：** 队友执行器
**英文原词：** TeammateExecutor
**代码符号：** `TeammateExecutor`、`BackendRegistry.get_executor()`

**定义：** 抽象接口，定义 spawn/send_message/shutdown 等方法。`SubprocessBackend` 和 `InProcessBackend` 是两种具体实现。

**源码证据：** `src/openharness/swarm/types.py` -> `TeammateExecutor` 接口定义

**关联术语：** SubprocessBackend、InProcessBackend、BackendRegistry

---

### 5. Tool Agent（工具 Agent）

**中文术语：** 工具 Agent
**英文原词：** Tool Agent
**代码符号：** `AgentTool`、`agent_tool.py`

**定义：** 一类特殊工具，允许在对话中派生新的 Agent 子进程。通过 `openharness.tools.agent_tool` 实现。

**源码证据：** `src/openharness/tools/agent_tool.py` -> `AgentTool` 工具实现

**关联术语：** Coordinator、TeammateSpawnConfig

---

## B: Bridge 与渠道

### 6. Bridge（桥接）

**中文术语：** 桥接
**英文原词：** Bridge
**代码符号：** `BridgeSessionManager`、`BridgeSessionRecord`

**定义：** 允许在 OpenHarness 会话中启动外部 CLI 工具（如 `claude`、`codex`）的机制。Bridge 会话通过子进程运行，输出被捕获到日志文件。

**源码证据：**
- `src/openharness/bridge/manager.py` -> `BridgeSessionManager.spawn()` 派生新桥接会话
- `src/openharness/bridge/session_runner.py` -> `spawn_session()` 启动桥接会话进程

**关联术语：** BridgeSessionRecord、SessionHandle

---

### 7. Channel（渠道）

**中文术语：** 渠道
**英文原词：** Channel
**代码符号：** `ChannelAdapter`、`ChannelManager`

**定义：** ohmo personal agent 与外部通信的通道。支持 Telegram、Slack、Discord、飞书等多种 IM 平台。

**源码证据：**
- `src/openharness/channels/impl/base.py` -> `ChannelAdapter` 渠道适配器基类
- `src/openharness/channels/impl/manager.py` -> `ChannelManager` 渠道管理器

**关联术语：** ohmo、ChannelBusAdapter、BusEvent

---

### 8. ohmo（个人 Agent 应用）

**中文术语：** ohmo 个人 Agent
**英文原词：** ohmo
**代码符号：** 无特定代码符号，`~/.ohmo/` 为工作区根目录

**定义：** 基于 OpenHarness 构建的个人 Agent 应用，可在飞书/Slack/Telegram/Discord 等平台中运行，在后台执行代码编写、PR 创建等任务。

**源码证据：** `README.md` -> ohmo 描述及 `ohmo init/config/gateway` 命令系列

**关联术语：** Channel、Gateway、soul.md

---

## C: Config 与设置

### 9. Provider Profile（Provider 配置）

**中文术语：** Provider 配置
**英文原词：** Provider Profile
**代码符号：** `ProviderProfile`、`Settings.resolve_profile()`

**定义：** 命名的工作流配置，包含 provider/api_format/auth_source/default_model/base_url 等字段。支持多个 Provider 配置切换。

**源码证据：**
- `src/openharness/config/settings.py` -> `ProviderProfile` 数据模型
- `src/openharness/config/settings.py` -> `Settings.resolve_profile()` 返回当前活动配置

**关联术语：** Settings、AuthFlow、API Client

---

### 10. Settings（设置）

**中文术语：** 设置
**英文原词：** Settings
**代码符号：** `Settings`、`load_settings()`、`save_settings()`

**定义：** OpenHarness 主配置类，包含 API 密钥、模型、权限、钩子、内存、沙箱等所有配置项。配置解析优先级：CLI 参数 > 环境变量 > 配置文件 > 默认值。

**源码证据：**
- `src/openharness/config/settings.py` -> `Settings` 主配置模型
- `src/openharness/config/settings.py` -> `load_settings()` 从配置文件加载

**关联术语：** ProviderProfile、PermissionSettings、SandboxSettings

---

### 11. Auto-Compact（自动压缩）

**中文术语：** 自动压缩
**英文原词：** Auto-Compact
**代码符号：** `auto_compact_if_needed()`、`auto_compact_threshold_tokens`、`AUTO_COMPACT_STATUS_MESSAGE`

**定义：** 当对话 token 数超过阈值时，自动对旧消息进行摘要压缩，保持上下文在模型上下文窗口内。

**源码证据：**
- `src/openharness/services/compact.py` -> `auto_compact_if_needed()` 压缩核心函数
- `src/openharness/engine/query_engine.py` -> `AUTO_COMPACT_STATUS_MESSAGE` 压缩前提示
- `src/openharness/config/settings.py` -> `auto_compact_threshold_tokens` 配置项

**关联术语：** ConversationMessage、MemorySettings

---

## D: Docker 与沙箱

### 12. Docker Sandbox（Docker 沙箱）

**中文术语：** Docker 沙箱
**英文原词：** Docker Sandbox
**代码符号：** `DockerSandboxSession`、`get_docker_availability()`

**定义：** 基于 Docker 容器的隔离执行环境，用于沙箱化工具执行。提供网络隔离（none/bridge）和资源限制（CPU/内存）。

**源码证据：**
- `src/openharness/sandbox/docker_backend.py` -> `DockerSandboxSession` 沙箱会话管理
- `src/openharness/sandbox/docker_backend.py` -> `DockerSandboxSession.start()` 启动容器
- `src/openharness/sandbox/docker_backend.py` -> `get_docker_availability()` 检查可用性

**关联术语：** SandboxSettings、DockerSandboxSettings、SandboxUnavailableError

---

### 13. Sandbox Backend（沙箱后端）

**中文术语：** 沙箱后端
**英文原词：** Sandbox Backend
**代码符号：** `SandboxSettings`、`backend`

**定义：** 沙箱执行的后端类型，支持 `srt` 和 `docker` 两种后端。SandboxSettings 配置后端类型和平台限制。

**源码证据：** `src/openharness/config/settings.py` -> `SandboxSettings` 数据模型

**关联术语：** DockerSandboxSession、SandboxSettings

---

## E: Engine 与查询

### 14. QueryEngine（查询引擎）

**中文术语：** 查询引擎
**英文原词：** QueryEngine
**代码符号：** `QueryEngine`、`QueryEngine.submit_message()`

**定义：** 管理会话历史和工具感知模型循环的核心类。持有 `_messages`（会话历史）和 `_cost_tracker`（使用量追踪），提供 `submit_message` 和 `continue_pending` 方法。

**源码证据：**
- `src/openharness/engine/query_engine.py` -> `QueryEngine` 类定义
- `src/openharness/engine/query_engine.py` -> `QueryEngine.submit_message()` 提交消息并执行循环

**关联术语：** run_query、QueryContext、ToolRegistry

---

### 15. QueryContext（查询上下文）

**中文术语：** 查询上下文
**英文原词：** QueryContext
**代码符号：** `QueryContext`、`QueryContext`

**定义：** 跨查询运行共享的上下文数据类，包含 api_client/tool_registry/permission_checker/cwd/model/system_prompt 等。

**源码证据：** `src/openharness/engine/query_engine.py` -> `QueryContext` dataclass

**关联术语：** QueryEngine、ToolRegistry、PermissionChecker、HookExecutor

---

### 16. run_query（运行查询）

**中文术语：** 运行查询
**英文原词：** run_query
**代码符号：** `run_query`、`run_query()`

**定义：** 异步生成器函数，实现工具感知模型循环的核心逻辑：调用模型 → 收集工具调用 → 执行工具 → 循环直到模型停止请求工具。

**源码证据：** `src/openharness/engine/query_engine.py` -> `run_query()` 异步生成器函数

**关联术语：** QueryEngine、_execute_tool_call、StreamEvent

---

### 17. ToolExecutionContext（工具执行上下文）

**中文术语：** 工具执行上下文
**英文原词：** Tool Execution Context
**代码符号：** `ToolExecutionContext`、`ToolExecutionContext.cwd`

**定义：** 传递给工具 `execute()` 方法的上下文对象，包含 cwd（当前工作目录）和 metadata（工具元数据/携带状态）。

**源码证据：** `src/openharness/tools/base.py` -> `ToolExecutionContext` dataclass

**关联术语：** BaseTool.execute()、ToolMetadata

---

### 18. ToolMetadata（工具元数据）

**中文术语：** 工具元数据
**英文原词：** Tool Metadata
**代码符号：** `tool_metadata`、`QueryContext.tool_metadata`

**定义：** 跨工具调用携带的累积状态字典，包含 task_focus_state（目标跟踪）、recent_verified_work（已验证工作）、invoked_skills（已调用技能）等桶。

**源码证据：** `src/openharness/engine/query_engine.py` -> `_task_focus_state()` 管理目标焦点状态

**关联术语：** QueryContext、_record_tool_carryover

---

### 19. ConversationMessage（会话消息）

**中文术语：** 会话消息
**英文原词：** Conversation Message
**代码符号：** `ConversationMessage`、`ConversationMessage.role`

**定义：** 表示单条 assistant 或 user 消息的 Pydantic 模型，包含 role 和 content（TextBlock/ImageBlock/ToolUseBlock/ToolResultBlock 列表）。

**源码证据：** `src/openharness/engine/messages.py` -> `ConversationMessage` 数据模型

**关联术语：** TextBlock、ToolUseBlock、ToolResultBlock

---

### 20. StreamEvent（流事件）

**中文术语：** 流事件
**英文原词：** Stream Event
**代码符号：** `StreamEvent`、`AssistantTextDelta | AssistantTurnComplete | ...`

**定义：** QueryEngine 产生的异步流事件联合类型，包含增量文本、完成事件、工具开始/完成事件、错误事件、状态事件、压缩进度事件等。

**源码证据：** `src/openharness/engine/stream_events.py` -> `StreamEvent` 联合类型定义

**关联术语：** AssistantTextDelta、ToolExecutionStarted、CompactProgressEvent

---

## H: Hooks 与生命周期

### 21. Hook（钩子）

**中文术语：** 钩子
**英文原词：** Hook
**代码符号：** `HookExecutor.execute()`、`HookEvent`

**定义：** 生命周期事件拦截点，允许在工具执行前/后注入自定义逻辑。支持命令钩子、HTTP 钩子、提示钩子和 Agent 钩子四种类型。

**源码证据：**
- `src/openharness/hooks/executor.py` -> `HookExecutor.execute()` 执行事件匹配的所有钩子
- `src/openharness/hooks/events.py` -> `HookEvent` 事件枚举

**关联术语：** HookExecutor、PRE_TOOL_USE、POST_TOOL_USE

---

### 22. PRE_TOOL_USE / POST_TOOL_USE

**中文术语：** 工具使用前钩子 / 工具使用后钩子
**英文原词：** Pre-Tool-Use Hook / Post-Tool-Use Hook
**代码符号：** `HookEvent.PRE_TOOL_USE`、`HookEvent.POST_TOOL_USE`

**定义：** 两种主要的生命周期钩子事件。PRE_TOOL_USE 在工具执行前触发，可阻止工具执行；POST_TOOL_USE 在工具执行后触发。

**源码证据：**
- `src/openharness/hooks/events.py` -> `HookEvent` 枚举定义
- `src/openharness/engine/query_engine.py` -> `_execute_tool_call()` 中的钩子调用逻辑

**关联术语：** HookExecutor、HookResult、block_on_failure

---

### 23. HookExecutor（钩子执行器）

**中文术语：** 钩子执行器
**英文原词：** Hook Executor
**代码符号：** `HookExecutor`、`HookExecutionContext`

**定义：** 执行生命周期钩子的引擎类。遍历 HookRegistry 中的事件匹配钩子，调用命令/ HTTP / LLM 推理等不同执行路径。

**源码证据：** `src/openharness/hooks/executor.py` -> `HookExecutor` 类定义

**关联术语：** HookRegistry、HookExecutionContext、HookResult

---

## M: MCP 与协议

### 24. MCP（Model Context Protocol）

**中文术语：** 模型上下文协议
**英文原词：** Model Context Protocol
**代码符号：** `McpClientManager`、`mcp/` 模块

**定义：** Anthropic 提出的标准协议，用于连接 AI 助手与外部工具和数据源。OpenHarness 实现 MCP 客户端，支持 stdio 和 HTTP 两种传输方式。

**源码证据：**
- `src/openharness/mcp/client.py` -> `McpClientManager` MCP 客户端管理器
- `src/openharness/mcp/client.py` -> `McpClientManager.connect_all()` 连接所有 MCP 服务器

**关联术语：** McpClientManager、McpToolInfo、McpConnectionStatus

---

### 25. MCP Client Manager（MCP 客户端管理器）

**中文术语：** MCP 客户端管理器
**英文原词：** MCP Client Manager
**代码符号：** `McpClientManager`、`McpClientManager.call_tool()`

**定义：** 管理 MCP 服务器连接并暴露工具和资源的主类。维护 `_sessions`（连接会话）和 `_statuses`（连接状态）。

**源码证据：** `src/openharness/mcp/client.py` -> `McpClientManager` 类定义

**关联术语：** McpServerNotConnectedError、McpStdioServerConfig、McpHttpServerConfig

---

### 26. MCP Transport（MCP 传输方式）

**中文术语：** MCP 传输方式
**英文原词：** MCP Transport
**代码符号：** `stdio` | `http`、`McpStdioServerConfig` | `McpHttpServerConfig`

**定义：** MCP 服务器的两种通信方式。stdio 通过标准输入/输出管道；HTTP 通过 `streamable_http_client` 进行 HTTP 流传输。

**源码证据：**
- `src/openharness/mcp/client.py` -> `_connect_stdio()` stdio 连接
- `src/openharness/mcp/client.py` -> `_connect_http()` HTTP 连接

**关联术语：** McpStdioServerConfig、McpHttpServerConfig

---

## P: Permissions 与安全

### 27. Permission Mode（权限模式）

**中文术语：** 权限模式
**英文原词：** Permission Mode
**代码符号：** `PermissionMode`、`PermissionMode.DEFAULT` | `FULL_AUTO` | `PLAN`

**定义：** 控制工具执行权限级别的枚举类型。DEFAULT（默认）要求用户确认变更操作；FULL_AUTO（全自动）允许所有操作；PLAN（计划模式）阻止所有变更直到用户退出计划模式。

**源码证据：**
- `src/openharness/permissions/modes.py` -> `PermissionMode` 枚举定义
- `src/openharness/permissions/checker.py` -> `PermissionChecker.evaluate()` 根据模式返回决策

**关联术语：** PermissionChecker、PermissionDecision、SENSITIVE_PATH_PATTERNS

---

### 28. Permission Checker（权限检查器）

**中文术语：** 权限检查器
**英文原词：** Permission Checker
**代码符号：** `PermissionChecker`、`PermissionChecker.evaluate()`

**定义：** 评估工具调用是否可运行的组件。执行多层检查：内置敏感路径保护 > 显式拒绝列表 > 显式允许列表 > 路径规则 > 命令拒绝模式 > 权限模式 > 确认提示。

**源码证据：** `src/openharness/permissions/checker.py` -> `PermissionChecker` 类定义

**关联术语：** PermissionDecision、SENSITIVE_PATH_PATTERNS、PathRule

---

### 29. SENSITIVE_PATH_PATTERNS（敏感路径模式）

**中文术语：** 敏感路径模式
**英文原词：** Sensitive Path Patterns
**代码符号：** `SENSITIVE_PATH_PATTERNS`

**定义：** 始终拒绝访问的高价值凭证路径模式元组，包含 SSH 密钥、AWS/GCP/Azure/Kubernetes 凭证、Docker 凭证等。

**源码证据：** `src/openharness/permissions/checker.py` -> `SENSITIVE_PATH_PATTERNS` 元组常量

**关联术语：** PermissionChecker.evaluate()、SENSITIVE_PATH_PATTERNS

---

## S: Swarm 与团队

### 30. Swarm（蜂群）

**中文术语：** 蜂群（Swarm）
**英文原词：** Swarm
**代码符号：** `swarm/` 模块、`CLAUDE_CODE_TEAM_NAME`、`CLAUDE_CODE_AGENT_NAME`

**定义：** OpenHarness 的多 Agent 协调架构，通过团队（Team）组织多个 Agent（Teammate），由 Coordinator 协调。

**源码证据：**
- `src/openharness/swarm/team_lifecycle.py` -> `TeamLifecycleManager` 团队生命周期管理
- `src/openharness/swarm/team_lifecycle.py` -> `TeamFile` 持久化团队元数据

**关联术语：** TeamLifecycleManager、Teammate、Coordinator

---

### 31. BackendRegistry（后端注册表）

**中文术语：** 后端注册表
**英文原词：** Backend Registry
**代码符号：** `BackendRegistry`、`get_backend_registry()`

**定义：** 管理 TeammateExecutor 后端实现的注册表。实现自动检测最佳可用后端的管道：in_process > tmux > subprocess。

**源码证据：** `src/openharness/swarm/registry.py` -> `BackendRegistry` 类定义

**关联术语：** SubprocessBackend、InProcessBackend、TeammateExecutor

---

### 32. TeamFile（团队文件）

**中文术语：** 团队文件
**英文原词：** Team File
**代码符号：** `TeamFile`、`TeamFile.save()` / `TeamFile.load()`

**定义：** 持久化团队元数据的 dataclass，存储为 `~/.openharness/teams/<name>/team.json`。包含团队名称、创建时间、领导 Agent ID、成员字典（agent_id -> TeamMember）和允许路径列表。

**源码证据：** `src/openharness/swarm/team_lifecycle.py` -> `TeamFile` dataclass

**关联术语：** TeamMember、AllowedPath、TeamLifecycleManager

---

### 33. TaskNotification（任务通知）

**中文术语：** 任务通知
**英文原词：** Task Notification
**代码符号：** `TaskNotification`、`format_task_notification()` / `parse_task_notification()`

**定义：** 从已完成 Teammate 传回 Coordinator 的 XML 格式通知，包含 task_id/status/summary/result/usage 等字段。

**源码证据：** `src/openharness/coordinator/coordinator_mode.py` -> `TaskNotification` dataclass

**关联术语：** Coordinator、TeammateSpawnConfig

---

## T: Tasks 与后台任务

### 34. BackgroundTaskManager（后台任务管理器）

**中文术语：** 后台任务管理器
**英文原词：** Background Task Manager
**代码符号：** `BackgroundTaskManager`、`get_task_manager()`

**定义：** 管理 Shell 和 Agent 子进程任务的生命周期。提供创建、更新、停止、写入 stdin、读取输出等接口。

**源码证据：** `src/openharness/tasks/manager.py` -> `BackgroundTaskManager` 类定义

**关联术语：** TaskRecord、TaskType、create_agent_task

---

### 35. TaskRecord（任务记录）

**中文术语：** 任务记录
**英文原词：** Task Record
**代码符号：** `TaskRecord`、`TaskRecord.id` / `TaskRecord.status`

**定义：** 表示单个后台任务的数据类，包含 id/type/status/description/cwd/output_file/command/created_at/started_at/ended_at/return_code 等字段。

**源码证据：** `src/openharness/tasks/types.py` -> `TaskRecord` dataclass

**关联术语：** BackgroundTaskManager、TaskType

---

### 36. ToolRegistry（工具注册表）

**中文术语：** 工具注册表
**英文原词：** Tool Registry
**代码符号：** `ToolRegistry`、`ToolRegistry.register()`

**定义：** 工具名称到实现的映射注册表。提供 register/get/list_tools/to_api_schema 等方法。

**源码证据：** `src/openharness/tools/base.py` -> `ToolRegistry` 类定义

**关联术语：** BaseTool、ToolExecutionContext

---

## U: UI 与交互

### 37. AppStateStore（应用状态存储）

**中文术语：** 应用状态存储
**英文原词：** Application State Store
**代码符号：** `AppStateStore`、`AppStateStore.subscribe()`

**定义：** 非常轻量的可观察状态存储，使用发布-订阅模式。UI 层订阅状态变化，引擎层通过 `set()` 更新状态并通知所有监听器。

**源码证据：** `src/openharness/state/store.py` -> `AppStateStore` 类定义

**关联术语：** AppState、Listener

---

### 38. CostTracker（成本追踪器）

**中文术语：** 成本追踪器
**英文原词：** Cost Tracker
**代码符号：** `CostTracker`、`QueryEngine._cost_tracker`

**定义：** 在会话生命周期内累积 API 使用量的追踪器。存储 input_tokens 和 output_tokens 总数。

**源码证据：** `src/openharness/engine/cost_tracker.py` -> `CostTracker` 类定义

**关联术语：** UsageSnapshot、QueryEngine.total_usage

---

### 39. React TUI（React 终端用户界面）

**中文术语：** React 终端用户界面
**英文原词：** React TUI
**代码符号：** `TUIApp`、`run_tui()`

**定义：** 基于 React/Ink 库的终端用户界面，提供交互式体验（命令选择器、权限对话框、模式切换器、会话恢复等）。

**源码证据：** `src/openharness/ui/app.py` -> `TUIApp` 主应用类

**关联术语：** TUIRuntime、PermissionDialog

---

## 其他

### 40. CLAUDE.md（Claude 项目说明）

**中文术语：** Claude 项目说明文件
**英文原词：** CLAUDE.md
**代码符号：** `find_claude_md()` / `load_claude_md()`

**定义：** 存放在项目根目录的 Markdown 文件，在 Agent 会话开始时自动注入到系统提示中，为项目提供领域知识和约定。

**源码证据：** `src/openharness/prompts/claudemd.py` -> `find_claude_md()` / `load_claude_md()`

**关联术语：** SystemPrompt、Skill

---

### 41. Skill（技能）

**中文术语：** 技能
**英文原词：** Skill
**代码符号：** `SkillRegistry`、`SkillTool`、`SkillDefinition`

**定义：** 按需加载的 Markdown 格式领域知识文件。与 CLAUDE.md 不同，技能是在需要时才加载（通过 SkillTool），而非会话开始时注入。兼容 anthropics/skills 格式。

**源码证据：**
- `src/openharness/skills/registry.py` -> `SkillRegistry` 技能注册表
- `src/openharness/skills/types.py` -> `SkillDefinition` 技能定义

**关联术语：** SkillRegistry、SkillTool

---

### 42. Plugin（插件）

**中文术语：** 插件
**英文原词：** Plugin
**代码符号：** `load_plugin()`、`PluginManifest`、`LoadedPlugin`

**定义：** 包含 commands/hooks/agents/MCP servers 组件的可分发扩展包。与 Claude Code 插件格式兼容。

**源码证据：**
- `src/openharness/plugins/loader.py` -> `load_plugin()` 加载单个插件
- `src/openharness/plugins/schemas.py` -> `PluginManifest` 插件清单数据模型

**关联术语：** PluginManifest、LoadedPlugin、PluginCommandDefinition

---

### 43. AuthFlow（认证流程）

**中文术语：** 认证流程
**英文原词：** Authentication Flow
**代码符号：** `AuthFlow`、`ApiKeyFlow` | `DeviceCodeFlow` | `BrowserFlow`

**定义：** 抽象基类 + 三种具体认证方式：ApiKeyFlow（直接输入 API Key）、DeviceCodeFlow（GitHub OAuth 设备码流程）、BrowserFlow（打开浏览器完成认证）。

**源码证据：** `src/openharness/auth/flows.py` -> `AuthFlow` / `ApiKeyFlow` / `DeviceCodeFlow` / `BrowserFlow`

**关联术语：** AuthManager、ProviderProfile

---

### 44. UsageSnapshot（使用量快照）

**中文术语：** 使用量快照
**英文原词：** Usage Snapshot
**代码符号：** `UsageSnapshot`、`CostTracker.add()`

**定义：** 单次 API 调用的使用量快照，包含 input_tokens 和 output_tokens。

**源码证据：** `src/openharness/api/usage.py` -> `UsageSnapshot` 数据类

**关联术语：** CostTracker

---

### 45. Memory（内存/持久化知识）

**中文术语：** 持久化知识
**英文原词：** Memory
**代码符号：** `MemoryManager`、`MEMORY.md`

**定义：** 跨会话持久化存储知识的系统，通过 `memory/` 目录中的 Markdown 文件和 `MEMORY.md` 索引实现。

**源码证据：**
- `src/openharness/memory/manager.py` -> `MemoryManager` 内存管理器
- `src/openharness/memory/types.py` -> `MemoryEntry` 内存条目数据类

**关联术语：** MemorySettings、add_memory_entry、MEMORY.md

---

### 46. RESOLVED_AUTH（已解析认证）

**中文术语：** 已解析认证
**英文原词：** Resolved Auth
**代码符号：** `ResolvedAuth`、`Settings.resolve_auth()`

**定义：** 规范化后的认证材料数据类，包含 provider/auth_kind/value/source/state 字段。

**源码证据：** `src/openharness/config/settings.py` -> `ResolvedAuth` frozen dataclass

**关联术语：** AuthFlow、ProviderProfile

---

## 术语对照表

| 中文术语 | 英文原词 | 代码符号/路径 |
|----------|----------|---------------|
| Agent 挽具 | Agent Harness | README.md |
| 协调器 | Coordinator | `coordinator_mode.py` / `is_coordinator_mode()` |
| 队友 | Teammate | `swarm/types.py` / `TeammateSpawnConfig` |
| 队友执行器 | TeammateExecutor | `swarm/types.py` |
| 工具 Agent | Tool Agent | `tools/agent_tool.py` / `AgentTool` |
| 桥接 | Bridge | `bridge/manager.py` / `BridgeSessionManager` |
| 渠道 | Channel | `channels/impl/base.py` / `ChannelAdapter` |
| ohmo 个人 Agent | ohmo | README.md |
| Provider 配置 | Provider Profile | `config/settings.py` / `ProviderProfile` |
| 设置 | Settings | `config/settings.py` / `Settings` |
| 自动压缩 | Auto-Compact | `services/compact.py` / `auto_compact_if_needed()` |
| Docker 沙箱 | Docker Sandbox | `sandbox/docker_backend.py` / `DockerSandboxSession` |
| 沙箱后端 | Sandbox Backend | `config/settings.py` / `SandboxSettings` |
| 查询引擎 | QueryEngine | `engine/query_engine.py` / `QueryEngine` |
| 查询上下文 | QueryContext | `engine/query_engine.py` / `QueryContext` |
| 运行查询 | run_query | `engine/query_engine.py` / `run_query()` |
| 工具执行上下文 | Tool Execution Context | `tools/base.py` / `ToolExecutionContext` |
| 工具元数据 | Tool Metadata | `engine/query_engine.py` / `tool_metadata` |
| 会话消息 | Conversation Message | `engine/messages.py` / `ConversationMessage` |
| 流事件 | Stream Event | `engine/stream_events.py` / `StreamEvent` |
| 钩子 | Hook | `hooks/executor.py` / `HookExecutor` |
| 工具使用前钩子 | Pre-Tool-Use Hook | `hooks/events.py` / `HookEvent.PRE_TOOL_USE` |
| 工具使用后钩子 | Post-Tool-Use Hook | `hooks/events.py` / `HookEvent.POST_TOOL_USE` |
| 钩子执行器 | Hook Executor | `hooks/executor.py` / `HookExecutor` |
| 模型上下文协议 | MCP | `mcp/client.py` / `McpClientManager` |
| MCP 客户端管理器 | MCP Client Manager | `mcp/client.py` / `McpClientManager` |
| MCP 传输方式 | MCP Transport | `mcp/client.py` / `stdio` \| `http` |
| 权限模式 | Permission Mode | `permissions/modes.py` / `PermissionMode` |
| 权限检查器 | Permission Checker | `permissions/checker.py` / `PermissionChecker` |
| 敏感路径模式 | Sensitive Path Patterns | `permissions/checker.py` / `SENSITIVE_PATH_PATTERNS` |
| 蜂群（Swarm） | Swarm | `swarm/` 模块 |
| 后端注册表 | Backend Registry | `swarm/registry.py` / `BackendRegistry` |
| 团队文件 | Team File | `swarm/team_lifecycle.py` / `TeamFile` |
| 任务通知 | Task Notification | `coordinator/coordinator_mode.py` / `TaskNotification` |
| 后台任务管理器 | Background Task Manager | `tasks/manager.py` / `BackgroundTaskManager` |
| 任务记录 | Task Record | `tasks/types.py` / `TaskRecord` |
| 工具注册表 | Tool Registry | `tools/base.py` / `ToolRegistry` |
| 应用状态存储 | App State Store | `state/store.py` / `AppStateStore` |
| 成本追踪器 | Cost Tracker | `engine/cost_tracker.py` / `CostTracker` |
| React 终端界面 | React TUI | `ui/app.py` / `TUIApp` |
| Claude 项目说明 | CLAUDE.md | `prompts/claudemd.py` / `find_claude_md()` |
| 技能 | Skill | `skills/registry.py` / `SkillRegistry` |
| 插件 | Plugin | `plugins/loader.py` / `load_plugin()` |
| 认证流程 | AuthFlow | `auth/flows.py` / `AuthFlow` |
| 使用量快照 | Usage Snapshot | `api/usage.py` / `UsageSnapshot` |
| 持久化知识 | Memory | `memory/manager.py` / `MemoryManager` |
| 已解析认证 | Resolved Auth | `config/settings.py` / `ResolvedAuth` |

---

## 按字母顺序索引

A: Agent Harness · AgentTool · AppStateStore · AuthFlow
B: BackendRegistry · Bridge
C: Channel · CLAUDE.md · ConversationMessage · Coordinator · CoordinatorSystemPrompt · CostTracker
D: DockerSandboxSession
E: Engine · execute_tool_call
H: Hook · HookEvent · HookExecutor
M: MCP · McpClientManager · Memory · MemorySettings
P: PermissionChecker · PermissionDecision · PermissionMode · Plugin · PluginManifest · ProviderProfile
Q: QueryContext · QueryEngine
R: React TUI
S: SandboxBackend · SENSITIVE_PATH_PATTERNS · Settings · Skill · SkillDefinition · SkillRegistry · StreamEvent · Swarm
T: TaskNotification · TaskRecord · TaskType · TeamFile · Teammate · TeammateExecutor · ToolExecutionContext · ToolMetadata · ToolRegistry
U: UsageSnapshot

---

*最后更新：2026-04-14 | 与 OpenHarness v0.1.x 源码同步*
