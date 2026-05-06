# 架构设计决策

## 摘要

本文档记录 OpenHarness 中的 8 条核心架构决策。每条决策包含决策背景、当前方案、替代方案、为何未选替代方案及替代方案的代价。决策覆盖工具抽象、MCP 集成、沙箱后端、Swarm 执行模型、Coordinator 权限、配置加载、会话持久化和 Channel 抽象层八个领域。

## 你将了解

- 8 个关键架构决策的设计逻辑与权衡
- 各决策的当前方案与替代方案的完整对比
- 每个决策涉及的代码证据引用

## 范围

本文档覆盖 OpenHarness 核心引擎层面的架构决策，不包括 UI、插件系统、Channel 实现细节等外围模块的具体决策。决策列表按领域分组，组内按重要性排序。

---

## 1. 工具抽象：BaseTool 类 vs 直接函数调用

### 决策背景

OpenHarness 需要支持多种类型的工具：本地内置工具（bash、file_read）、MCP 工具（来自外部 MCP 服务器）、项目级技能（skills）。这些工具在调用方式（同步/异步）、参数模式（结构化/自由文本）、执行上下文（需要 cwd、需要 MCP 连接）上存在显著差异。需要一个统一的抽象层使 Agent 引擎无需感知具体工具类型即可调用。

### 当前方案

`BaseTool` 作为所有工具的抽象基类，定义以下接口：

- `name: str`：工具的唯一标识符
- `description: str`：工具的描述（供 Agent 理解用途）
- `input_model: type[BaseModel]`：参数 Pydantic 模型（支持 Schema 推导）
- `async execute(arguments: BaseModel, context: ToolExecutionContext) -> ToolResult`：异步执行入口
- `is_read_only(arguments: BaseModel) -> bool`：判断是否为只读调用

`ToolRegistry` 提供注册、查询和 Schema 聚合能力：

`src/openharness/tools/base.py` -> `BaseTool` / `ToolRegistry`

```python
class BaseTool(ABC):
    name: str
    description: str
    input_model: type[BaseModel]

    @abstractmethod
    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
        """Execute the tool."""
```

### 替代方案

**方案 A：直接函数引用（duck typing）**。每个工具就是一个 `(dict) -> ToolResult` 的函数，注册到全局字典中，按名称查找调用。无需类层次结构。

**方案 B：命令模式（Command Pattern）**。定义统一的 `Command` 接口，每个工具实现 `Command.execute()`，使用类层次结构但不使用泛型参数模型。

### 为何未选方案 A

直接函数调用的优势在于简单，但会失去以下能力：

- 无法为 Agent 动态生成工具 Schema（`to_api_schema()` 需要类上的 `name`、`description`、`input_model`）
- 无法优雅地支持只读判断（`is_read_only` 需要知道参数的语义）
- MCP 工具适配（`McpToolAdapter`）需要统一接口来封装异构的 MCP 工具
- 工具的元数据（描述、Schema）无法与执行逻辑分离，不利于工具注册时的延迟加载

### 为何未选方案 B

命令模式适合具有 undo/redo 能力的场景，但 OpenHarness 的工具执行是一次性的，不需要撤销能力。BaseTool 的 async execute 更直接地映射到 AI Agent 工具调用的异步语义。

### 替代方案的代价

- **方案 A**：失去类型安全的参数模型和 Schema 生成能力，Agent 的工具调用需要额外的前置验证逻辑
- **方案 B**：对于简单的 bash/file_read 工具，引入 Command 类的开销不成比例

---

## 2. MCP 集成策略：内置客户端 vs 外部 MCP 网关

### 决策背景

MCP 协议定义了工具发现、调用、订阅等多种能力。OpenHarness 需要将 MCP 工具集成到 Agent 的工具集中。问题是：OpenHarness 应该内置 MCP 客户端实现（直接连接 MCP 服务器），还是将 MCP 服务器视为外部服务，通过一个独立的 MCP 网关（Gateway）代理连接？

### 当前方案

OpenHarness 内置 `McpClientManager`，直接管理 stdio 和 HTTP 两种传输方式的 MCP 连接。`McpToolAdapter` 将每个 MCP 工具适配为 `BaseTool` 实例，注册到 `ToolRegistry`。连接生命周期完全由 OpenHarness 控制。

`src/openharness/mcp/client.py` -> `McpClientManager`

### 替代方案

**方案 A：外部 MCP Gateway**。运行一个独立的 MCP Gateway 进程（作为 Claude Code 的 sidecar），OpenHarness 仅通过其暴露的 HTTP API 发现和调用工具。所有 MCP 协议细节对 OpenHarness 透明。

**方案 B：仅支持 MCP over stdio，不支持 HTTP**。STDIO 模式最简单，无需管理 HTTP 连接生命周期。

### 为何未选方案 A

外部网关引入了额外的部署复杂度和进程间通信开销：
- 用户需要额外启动网关进程
- 网关的认证、配置需要独立管理
- MCP 服务器的生命周期与 OpenHarness 会话的绑定需要额外协调
- 对于简单的本地 MCP 服务器（stdio），网关是不必要的中间层

### 为何未选方案 B

HTTP 传输对于远程 MCP 服务器是必需的。很多 MCP 服务器部署在云端（如数据库服务、API 服务），只能通过 HTTP 访问。排除 HTTP 支持会限制 OpenHarness 可集成的 MCP 服务器范围。

### 替代方案的代价

- **方案 A**：增加用户的部署复杂度，但获得更好的进程隔离（Gateway 崩溃不影响 OpenHarness 主进程）
- **方案 B**：失去对 HTTP MCP 服务器的支持，仅适合纯本地工具场景

---

## 3. 沙箱后端选择：Docker vs gVisor / seccomp / firecracker

### 决策背景

代码执行隔离是安全工具系统的核心需求。OpenHarness 需要在保障安全性的同时保持良好的跨平台兼容性和易用性。容器化隔离（Docker）是最广泛部署和理解的技术，但存在攻击面较大、资源开销较高等问题。

### 当前方案

OpenHarness 支持两种沙箱后端：

- **srt 后端**（默认）：使用 `bubblewrap`（Linux）和 `sandbox-exec`（macOS）进行操作系统级隔离，轻量但安全性依赖内核 namespace
- **Docker 后端**：使用 Docker 容器隔离，提供更强的网络和资源限制能力

`src/openharness/sandbox/adapter.py` -> `wrap_command_for_sandbox`

`src/openharness/sandbox/docker_backend.py` -> `DockerSandboxSession`

### 替代方案

**方案 A：gVisor**。Google 的用户态内核实现，提供比 Docker 更强的隔离（每个容器有独立的内核），但配置复杂度高，macOS 不支持。

**方案 B：seccomp + AppArmor/SELinux**。纯 Linux 内核安全机制，无需额外守护进程，但规则编写复杂，跨平台一致性差。

**方案 C：firecracker microVM**。轻量级虚拟机，提供近乎裸机的隔离，但启动延迟高（100-500ms），资源占用大。

**方案 D：纯 srt（默认）**。不提供 Docker 选项，统一使用 srt。

### 为何未选方案 A / B / C

gVisor、seccomp 和 firecracker 都需要特定的运行时支持，在跨平台场景（Linux/macOS/WSL）的一致性实现成本很高。Docker 是目前最广泛支持的容器技术，用户已经在本地安装了 Docker Desktop/Engine 的场景非常普遍。

### 为何未选方案 D（仅 srt）

某些场景下 Docker 容器比 bubblewrap 提供更强的隔离（如网络策略、用户命名空间）。同时 Docker 镜像的可复现性优于依赖宿主系统工具链的 bubblewrap（`bwrap` 在不同发行版上的可用性和配置方式差异较大）。

### 替代方案的代价

- **方案 A/B/C**：实现和维护成本高，macOS 支持几乎不可能（gVisor 和 firecracker 依赖 Linux 内核）
- **方案 D**：失去 Docker 的强隔离能力和跨平台一致性的优势

---

## 4. Swarm 执行模型：InProcess vs Subprocess

### 决策背景

Swarm 是 OpenHarness 的多 Agent 协作框架，支持多个 Worker Agent 并行执行，由 Coordinator Agent 协调。当 Worker Agent 的执行需要跨进程隔离（防止单点崩溃影响整个会话）时，应该选择 Subprocess 模型；当需要最大化通信效率（零序列化开销）时，应该选择 InProcess 模型。

### 当前方案

OpenHarness 同时实现了两种执行后端：

**InProcessBackend**：Worker 作为 asyncio Task 运行在 Coordinator 的同一进程中，通过 `ContextVar` 实现每个 Agent 的上下文隔离。通信通过文件 mailbox 实现（支持持久化），也支持直接入队消息到 `message_queue`。

`src/openharness/swarm/in_process.py` -> `InProcessBackend` / `start_in_process_teammate`

```python
# asyncio.create_task() copies the current Context automatically,
# so each Task starts with an independent ContextVar state.
task = asyncio.create_task(
    start_in_process_teammate(...),
    name=f"teammate-{agent_id}",
)
```

**SubprocessBackend**：Worker 作为独立子进程运行，通过 `BackgroundTaskManager` 创建和销毁，通信通过 stdin/stdout 的 JSON 行协议。

`src/openharness/swarm/subprocess_backend.py` -> `SubprocessBackend`

### 替代方案

**方案 A：仅 InProcess**。所有 Worker 共享同一进程，通过协程切换实现并发。

**方案 B：仅 Subprocess**。所有 Worker 都是独立进程，通过 IPC 通信。

### 为何未选方案 A

InProcess 模式存在以下风险：

- Worker 中的未处理异常可能导致整个 Coordinator 崩溃（虽然有 `except` 保护，但不保证所有代码路径都被保护）
- 一个 Worker 的无限循环或内存泄漏会直接影响所有其他 Worker 和 Coordinator
- Python GIL 不影响 IO 密集型的 Agent 任务，但 CPU 密集型任务在 InProcess 中会互相竞争

### 为何未选方案 B

Subprocess 模式的开销不可忽视：

- 每次 spawn 需要启动新的 Python 解释器（冷启动延迟 200-500ms）
- 进程间通信需要序列化（即使使用高效的 JSON 行协议，也有额外的编码解码开销）
- 对于轻量级 Worker（如简单的文件检查），subprocess 的开销可能超过任务本身
- 文件 mailbox 的持久化在 Subprocess 模式下也带来额外的 IO 开销

### 替代方案的代价

- **方案 A**：牺牲进程级故障隔离，单点崩溃风险高，调试困难
- **方案 B**：牺牲低延迟通信能力，spawn 延迟显著，轻量任务性价比低

---

## 5. Coordinator 权限模型：受限 Worker 工具集 vs 全权限 Worker

### 决策背景

在 Swarm 模式中，Coordinator Agent 可以通过 `agent` 工具启动 Worker Agent。Worker 的能力边界直接影响整个系统的安全性和功能丰富度。需要决定：Worker 是否应该拥有与 Coordinator 同等的工具集，还是应该被限制在特定的安全工具子集内？

### 当前方案

Coordinator 通过 `get_coordinator_system_prompt()` 注入系统级指令，明确声明 Worker 只能访问受限工具集：

```python
_WORKER_TOOLS = [
    "bash", "file_read", "file_edit", "file_write", "glob", "grep",
    "web_fetch", "web_search",
    "task_create", "task_get", "task_list", "task_output",
    "skill",
]
```

Coordinator 保留的工具（不暴露给 Worker）：`agent`、`send_message`、`task_stop`。

`src/openharness/coordinator/coordinator_mode.py` -> `get_coordinator_system_prompt`

### 替代方案

**方案 A：全权限 Worker**。Worker 拥有与 Coordinator 完全相同的工具集，包括可以再启动 Worker 的 `agent` 工具（形成递归调用）。

**方案 B：最小权限 Worker**。Worker 只能访问 `bash`、`file_read`、`file_edit` 三个工具，所有复杂功能（如 web_fetch、task_*）都通过向 Coordinator 发消息并等待转发来实现。

### 为何未选方案 A

全权限 Worker 会导致：

- 递归 Agent 风险：Worker 可以再启动 Worker，可能形成无限递归调用
- 权限蔓延：Worker 执行危险操作（如 `rm -rf /`）的潜在影响范围扩大
- 审计困难：无法区分 Coordinator 和 Worker 的操作边界

### 为何未选方案 B

最小权限 Worker 过于严格：

- `web_fetch` / `web_search` 是 Worker 执行研究任务的核心工具，禁止它们会大幅降低 Worker 的独立工作能力
- `task_*` 系列工具用于 Worker 与任务管理系统的交互，是 Swarm 异步协作的基础
- 强制所有复杂操作通过 Coordinator 转发会抵消并行执行的优势（Coordinator 成为瓶颈）

### 替代方案的代价

- **方案 A**：安全风险增加，递归 Agent 场景需要额外的深度限制机制
- **方案 B**：Worker 独立性大幅降低，并行执行优势被削弱，Coordinator 成为所有外部交互的单点

---

## 6. 配置加载优先级：环境变量 vs 配置文件 vs 硬编码默认值

### 决策背景

OpenHarness 需要在多种场景下运行（本地开发、CI/CD、远程部署），不同场景有不同的配置来源优先级：
- 本地开发：配置文件为主，CLI 参数覆盖
- CI/CD：环境变量为主（便于 secrets 管理）
- 远程部署：环境变量或配置文件，按运维策略决定

### 当前方案

配置加载优先级（高到低）：

```
1. CLI arguments（最高优先级，通过 merge_cli_overrides() 应用）
2. Environment variables（OPENHARNESS_*, ANTHROPIC_API_KEY 等）
3. Config file（~/.openharness/settings.json）
4. Defaults（最低优先级）
```

`src/openharness/config/settings.py` -> 文档注释 + `load_settings` / `_apply_env_overrides`

```python
"""
Settings are resolved with the following precedence (highest first):
1. CLI arguments
2. Environment variables (ANTHROPIC_API_KEY, OPENHARNESS_MODEL, etc.)
3. Config file (~/.openharness/settings.json)
4. Defaults
"""
```

### 替代方案

**方案 A：仅配置文件 + CLI 参数**，不读取环境变量。

**方案 B：环境变量优先于配置文件**，适用于云原生部署场景。

**方案 C：统一使用 pydantic-settings**，依赖环境变量驱动配置。

### 为何未选方案 A

纯配置文件方案在 CI/CD 场景中需要额外的 secret 注入机制（如 AWS Secrets Manager、Doppler），不适合需要快速配置的开发体验。

### 为何未选方案 B

环境变量优先在本地开发场景中会导致问题：用户设置了一个 `ANTHROPIC_API_KEY` 环境变量后就无法通过配置文件覆盖，造成调试困难。

### 为何未选方案 C

pydendant-settings 框架虽然成熟，但其环境变量命名约定（`APP_SETTING_NAME`）与现有的 `OPENHARNESS_*` 前缀不一致。迁移成本高，且当前的手动实现更透明（每条环境变量对应哪个字段一目了然）。

### 替代方案的代价

- **方案 A**：CI/CD 集成复杂，需要额外的 secret 注入层
- **方案 B**：本地开发体验差，环境变量污染难以调试
- **方案 C**：依赖外部框架，增加包依赖和命名约定的迁移成本

---

## 7. 会话状态持久化：文件存储 vs 数据库 vs 内存仅存

### 决策背景

OpenHarness 支持会话恢复（resuming a session）。当用户退出后重新启动 CLI，需要能够恢复之前的对话上下文、工具执行历史和 Agent 状态。需要决定会话状态的存储介质和格式。

### 当前方案

OpenHarness 使用文件存储作为会话持久化的主要机制：

- **Transcript 文件**：对话历史以 JSON Lines 格式存储在 `~/.claude/sessions/` 下
- **Mailbox 文件**：Swarm 中 Worker 之间的消息通过文件实现持久化（`TeammateMailbox` 使用文件系统）
- **Settings 文件**：`~/.openharness/settings.json` 存储用户配置

Coordinator 的会话模式检测通过环境变量 `CLAUDE_CODE_COORDINATOR_MODE` 与会话存储的模式字段比对，确保恢复时模式一致。

`src/openharness/coordinator/coordinator_mode.py` -> `match_session_mode`

```python
if session_is_coordinator:
    os.environ["CLAUDE_CODE_COORDINATOR_MODE"] = "1"
else:
    os.environ.pop("CLAUDE_CODE_COORDINATOR_MODE", None)
```

### 替代方案

**方案 A：SQLite 数据库**。将所有状态存储在单一 SQLite 文件中，支持事务查询和迁移。

**方案 B：仅内存存储**。会话状态不持久化，每次启动都是全新会话，通过会话 ID 关联的外部存储（由用户自行管理）。

**方案 C：云存储**。会话状态存储到 S3/云对象存储，支持跨设备同步。

### 为何未选方案 A

SQLite 作为嵌入式数据库虽然方便，但引入以下问题：
- 多进程并发写入需要额外的锁管理（OpenHarness 有 CLI、主进程、Worker 子进程等）
- Schema 迁移需要额外的迁移脚本和版本管理
- 对于纯文本的对话历史，关系数据库的查询优势不明显

### 为何未选方案 B

纯内存存储意味着用户每次启动都必须重建上下文。对于长时间运行的复杂项目，用户无法在会话中断后继续工作（需要重新输入上下文和执行历史），极大损害可用性。

### 为何未选方案 C

云存储增加了网络依赖和认证复杂性。对于本地 CLI 工具，强制云存储不是合理的默认选择（隐私风险、网络不可用场景）。

### 替代方案的代价

- **方案 A**：增加 SQLite 依赖和并发管理复杂性
- **方案 B**：会话无法恢复，损害用户体验
- **方案 C**：增加网络依赖、认证管理，不适合离线场景

---

## 8. Channel 抽象层：统一 Stream 接口 vs 平台特定实现

### 决策背景

OpenHarness 需要在多种运行环境（本地 TUI、远程 API 代理、测试环境）中与不同的后端服务通信。每种环境有不同的 IO 特性：
- 本地 TUI：stdin/stdout 字符流
- 远程 API：通过 HTTP SSE（Server-Sent Events）流式传输
- 测试环境：内存中的 mock stream

需要决定是否需要一个统一的 Channel 抽象层来屏蔽这些差异。

### 当前方案

（注：以下分析基于 OpenHarness 的 MCP 类型和 Channel 相关代码推断。实际的 Channel 实现涉及 infrastructure 层，具体代码需参考 `src/openharness/channels/` 目录。）

OpenHarness 通过 ProviderProfile 抽象不同的 API Provider（Anthropic、OpenAI、GitHub Copilot、Claude Subscription 等），每个 Provider 有独立的认证源和 API 格式：

`src/openharness/config/settings.py` -> `ProviderProfile` / `default_provider_profiles`

```python
class ProviderProfile(BaseModel):
    provider: str
    api_format: str  # "anthropic", "openai", "copilot"
    auth_source: str
    default_model: str
    base_url: str | None = None
```

每个 Provider 对应不同的 API 客户端（Anthropic 原生 SDK、OpenAI 兼容客户端等）。配置通过 `base_url` 差异化。

### 替代方案

**方案 A：统一 Channel 抽象**。定义 `Channel[T]` 接口，包含 `send(message: T)`、`receive() -> AsyncIterator[T]`、`close()` 等方法。每个 Provider 实现该接口（`AnthropicChannel`、`OpenAIChannel` 等）。

**方案 B：单一 HTTP 客户端 + 协议协商**。使用统一的 HTTP 客户端，所有 Provider 通过不同的 API 端点（`/v1/messages` vs `/v1/chat/completions`）区分。

### 为何未选方案 A

统一 Channel 接口在理论上有吸引力，但在实践中：
- 不同 Provider 的认证流程差异大（OAuth 设备流 vs API Key vs Bearer Token），难以用统一接口表达
- Anthropic 和 OpenAI 的流式响应格式不同（前者是 SSE，后者是 data: 行的 JSON）
- 引入 Channel 接口会增加新的抽象层次，每次 Provider 新增特性都需要在接口层面做变更

### 为何未选方案 B

单一 HTTP 客户端方案看似简单，但忽略了 Provider 之间深层次的差异：
- 错误码和重试策略不同（Anthropic 的 rate limit 处理与 OpenAI 不同）
- 模型列表和模型别名管理不同
- Token 计算方式不同

### 替代方案的代价

- **方案 A**：过度抽象，每个 Provider 的特性都需要通过适配器转换，增加间接层
- **方案 B**：差异被强行抹平，某些 Provider 的特性无法正确表达，可能导致意外行为

---

## 证据引用

1. `src/openharness/tools/base.py` -> `BaseTool` — 工具抽象基类定义
2. `src/openharness/tools/base.py` -> `ToolRegistry` — 工具注册表
3. `src/openharness/tools/base.py` -> `ToolExecutionContext` / `ToolResult` — 执行上下文与结果模型
4. `src/openharness/mcp/client.py` -> `McpClientManager` — MCP 客户端管理器
5. `src/openharness/mcp/types.py` -> `McpServerConfig` / `McpStdioServerConfig` / `McpHttpServerConfig` — MCP 配置类型
6. `src/openharness/sandbox/adapter.py` -> `SandboxAvailability` / `wrap_command_for_sandbox` — 沙箱可用性检查与命令包装
7. `src/openharness/sandbox/docker_backend.py` -> `DockerSandboxSession` — Docker 沙箱会话
8. `src/openharness/sandbox/docker_backend.py` -> `get_docker_availability` — Docker 可用性检查
9. `src/openharness/swarm/in_process.py` -> `InProcessBackend` — InProcess 执行后端
10. `src/openharness/swarm/in_process.py` -> `start_in_process_teammate` — InProcess teammate 启动逻辑
11. `src/openharness/swarm/in_process.py` -> `TeammateAbortController` — 双信号取消控制器
12. `src/openharness/swarm/subprocess_backend.py` -> `SubprocessBackend` — Subprocess 执行后端
13. `src/openharness/swarm/subprocess_backend.py` -> `spawn` — subprocess spawn 逻辑
14. `src/openharness/coordinator/coordinator_mode.py` -> `get_coordinator_system_prompt` — Coordinator 系统提示词（Worker 权限限制）
15. `src/openharness/coordinator/coordinator_mode.py` -> `match_session_mode` — 会话模式匹配
16. `src/openharness/coordinator/coordinator_mode.py` -> `_WORKER_TOOLS` — Worker 受限工具列表
17. `src/openharness/config/settings.py` -> `Settings` / `load_settings` — 配置加载逻辑
18. `src/openharness/config/settings.py` -> `_apply_env_overrides` — 环境变量覆盖
19. `src/openharness/config/settings.py` -> `ProviderProfile` / `default_provider_profiles` — Provider 配置
20. `src/openharness/config/settings.py` -> `SandboxSettings` / `DockerSandboxSettings` — 沙箱配置模型
21. `src/openharness/sandbox/docker_image.py` -> `_DOCKERFILE_CONTENT` — 默认沙箱镜像定义
