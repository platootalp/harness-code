# 风险与技术债

## 摘要

本文档系统性地梳理 OpenHarness 架构中的已知风险（按类别分组，每条包含触发条件、影响范围、可观测信号和缓解动作）和技术债（阻碍系统演进或增加维护成本的设计缺陷和未完成工作）。

## 你将了解

- 8 条按类别分组的风险，每条包含完整的四段式描述
- 5 项主要技术债及其对系统的影响
- 哪些风险已被缓解、哪些仍在开放状态
- 风险分类：API 依赖、安全、运维、性能、兼容性

## 范围

本文档覆盖 OpenHarness 架构层面的风险和技术债，不包括业务逻辑 bug、UI/UX 问题或特定通道实现的缺陷。

---

## 风险

### 风险 1：Anthropic API 单点故障（类别：API 依赖）

**触发条件**

Anthropic API 发生区域性服务中断（5xx 响应）、API 版本不兼容变更（如从 v1 升级到 v2 导致请求格式失效），或账户的 API Key 被检测为异常后封禁（401/403 响应）。

**影响范围**

所有使用 `claude-api` 和 `claude-subscription` Provider Profile 的会话完全中断。由于 Swarm 中所有 Worker Agent 共享同一个 API Key，API Key 的失效会导致整个多智能体团队（包括已启动的 Worker）同时停止工作，即使部分 Worker 仍处于空闲状态。

**可观测信号**

- `openharness/api/` 客户端的 HTTP 请求日志中出现连续的 5xx 错误
- `CostTracker` 的 `total` 对象中 `input_tokens` 和 `output_tokens` 计数停止增长
- `--verbose` 模式下 stderr 出现 `anthropic API error` 或 `401 Unauthorized`
- `resolve_auth` 抛出 `ValueError: No credentials found`（Key 失效时）
- `oh auth status` 显示 active provider 的 `state` 为 `expired` 或 `revoked`

**缓解动作**

1. 用户应预先配置至少一个备用 Provider Profile（如 `kimi-anthropic` 使用 Kimi 的 Anthropic 兼容端点），通过 `oh provider use kimi-anthropic` 切换到备用 Provider
2. `Settings` 支持通过 `ANTHROPIC_API_KEY` 环境变量覆盖配置文件中的 Key，紧急情况下可通过环境变量注入新 Key
3. 对于 `claude-subscription` 用户，`load_external_credential` 支持 `refresh_if_needed=True`，定期刷新 token 以避免过期
4. Swarm Coordinator 应在 Worker spawn 配置中指定独立的 API Key 环境变量，使各 Worker 使用不同的凭据，降低单 Key 失效的级联影响

---

### 风险 2：MCP stdio 冷启动导致的首工具调用超时（类别：性能）

**触发条件**

Worker Agent 首次调用某个 MCP 工具时，对应的 MCP 服务器子进程尚未启动（在 `AsyncExitStack` 中尚未创建连接）。由于 stdio 传输需要先 fork/exec 子进程，再通过 stdin/stdout 建立 JSON-RPC 连接，整个过程在 MCP 服务器启动较慢（如 Python 模块导入耗时长、Go 二进制文件 I/O 密集）时可能超过 5 秒。

**影响范围**

单个工具调用超时，可能导致整个推理轮次失败并重试。在 `max_turns` 限制较紧（如 `--max-turns 4`）的场景下，多次超时可能耗尽轮次配额。在 Swarm 中，Worker 的首次 MCP 工具调用比 Coordinator 更频繁，因为 Worker 默认配置下使用较少的工具（`bash`、`file_read`、`file_edit`），但 MCP 工具仍需在首次使用时建立连接。

**可观测信号**

- `McpClientManager.list_statuses()` 返回的某个 server 的 `state="failed"`，且 `detail` 字段包含 Python traceback（如 `FileNotFoundError` 或 subprocess 启动超时）
- OpenHarness 日志中首次 MCP 工具调用耗时显著高于后续调用（首次 >1s，后续 <100ms）
- `oh mcp list` 在会话开始前执行时显示所有 server 为 `pending`，需要等待一段时间后才变为 `connected`

**缓解动作**

1. 在启动会话前通过 `oh mcp list` 验证所有 MCP 服务器已成功连接，待所有 server 进入 `connected` 状态后再开始任务
2. 对启动较慢的 MCP 服务器（如包含大量依赖导入的 Python 服务器），将传输方式从 stdio 改为 HTTP Streamable，在服务器端预热 HTTP 连接池
3. 在 `Settings.sandbox.enabled=True` 时使用 Docker 后端，通过预拉取镜像（`docker pull`）减少容器启动冷启动时间
4. 在 Swarm Team 配置中为需要 MCP 工具的 Worker 指定 `mcp_clients` 列表，确保 MCP 连接在 Worker spawn 时已经建立

---

### 风险 3：Worker Agent 孤儿化（类别：运维）

**触发条件**

主 OpenHarness 进程在 Worker 子进程退出前收到 `SIGKILL`（无法被捕获的进程终止信号），或主进程遭遇 OOM（Out-of-Memory）被操作系统直接杀死，导致 `BackgroundTaskManager._watch_process` 的清理逻辑无法执行。

**影响范围**

仍在运行中的 Worker 子进程（`local_agent` / `in_process_teammate` 类型任务）成为孤儿进程。它们继续占用 CPU 和内存资源，但不产生任何有效输出。如果 Worker 正在进行文件写入操作，可能在主进程退出后继续修改代码库，造成状态不一致。

**可观测信号**

- 进程退出后，`ps aux | grep "openharness --task-worker"` 显示仍有 Python 进程在运行
- `~/.openharness/data/tasks/` 目录中存在 `status="running"` 的 `.log` 文件，但对应的进程已不存在
- `oh tasks list` 的输出与实际进程状态不符
- 系统日志（`dmesg` 或 `syslog`）中出现 OOM killer 记录

**缓解动作**

1. 用户应在终止 OpenHarness 会话前运行 `oh tasks list` 检查后台任务状态，对孤儿任务使用 `oh tasks stop <task_id>` 手动清理
2. 在 Swarm Team 工作流中，Coordinator 应在收到用户中断信号（`SIGINT`）前，先通过 `task_stop` 工具停止所有活跃的 Worker
3. `BackgroundTaskManager` 实现了基于 generation 的进程跟踪（`_generations` 字典），在进程重启场景下正确忽略旧 generation 的退出事件，但该机制不覆盖父进程被强制终止的场景
4. 建议在生产环境中使用进程管理器（如 `launchd`、`systemd`）管理 OpenHarness 主进程，由进程管理器在主进程退出时自动清理其子进程

---

### 风险 4：Coordinator XML 解析脆弱性（类别：兼容性）

**触发条件**

Worker Agent 在其输出中包含形似 `<task-notification>` 标签的文本（如代码注释 `<task-id>`、文档字符串、错误消息中的 XML 片段），导致 `parse_task_notification` 的正则表达式提取到错误的字段值。

**影响范围**

Coordinator 误判任务状态：将 `running` 解析为 `completed`，将失败任务解析为成功。最严重的情况是正则表达式 `re.DOTALL` 模式在接收超长、格式错误的 XML 时触发回溯（ReDoS），导致单次解析操作占用数秒 CPU 时间，在高并发 Swarm 场景下造成事件循环阻塞。

**可观测信号**

- Coordinator 日志中出现 "TaskNotification parse error" 或正则回溯警告
- 某个 Worker 已完成但 Coordinator 仍在等待 `<task-notification>`
- 系统监控显示正则解析函数（`parse_task_notification`）出现间歇性 CPU 尖峰

**缓解动作**

1. `parse_task_notification` 在解析失败时返回默认值（空字段的 `TaskNotification`），避免程序崩溃，但可能导致任务状态静默丢失
2. 建议 Worker Agent 在输出 `<task-notification>` 时使用明确的边界标记（如在 XML 前后各添加一个空行），降低误匹配风险
3. 长期解决方案是用结构化序列化（JSON）替换 XML 文本传递，或引入带版本号的二进制信封格式

---

### 风险 5：Plugin 动态代码执行（类别：安全）

**触发条件**

用户从不可信来源安装 OpenHarness 插件，插件的 `plugin.json` 中 `commands` 字段指向恶意 Markdown 文件，或 `hooks` 配置中嵌入了窃取凭据的命令（如将 `ANTHROPIC_API_KEY` 通过 `curl` 外发到攻击者服务器）。

**影响范围**

恶意插件可以在用户不知情的情况下执行任意系统命令、外发 API 凭据、修改文件系统。由于插件在 OpenHarness 启动时即被加载（`PluginLoader.load_plugins`），恶意代码的执行时机早于任何用户交互。

**可观测信号**

- `oh plugin list` 显示插件来源路径不在预期的 `~/.openharness/plugins/` 或项目 `.openharness/plugins/` 目录中
- Agent 在执行常规任务时出现非预期的 `curl` / `wget` / `nc` 等网络工具调用
- `~/.openharness/data/` 目录中出现非预期的凭据外发记录
- 插件安装后，`~/.openharness/plugins/<name>/` 目录包含可执行文件或包含 `os.system`、`subprocess` 等危险操作的 Python 文件

**缓解动作**

1. OpenHarness 插件系统没有内置签名验证机制，用户只能通过人工审查 `plugin.json` 的 `commands` 和 `hooks` 字段来识别恶意行为
2. `PluginLoader` 在 manifest 解析失败时仅记录 debug 日志，不抛出异常，避免了单点加载失败导致的全局崩溃，但同时也意味着部分恶意插件可能静默跳过加载
3. 建议用户只从可信来源（官方插件市场或经过代码审查的社区插件）安装插件
4. 在企业环境中，建议通过 `OPENHARNESS_PLUGIN_ROOTS` 环境变量限制插件加载路径，并使用文件完整性监控工具（`osquery`、`aide`）监控插件目录的变化

---

### 风险 6：Sandbox 逃逸（类别：安全）

**触发条件**

`SandboxSettings.enabled=True` 且 `SandboxSettings.backend="docker"` 时，存在以下逃逸路径：

- `sandbox-runtime` 工具的特权操作（`--privileged` 模式被错误启用）
- `openharness-sandbox` 镜像包含可被利用的 SUID 二进制文件
- `extra_mounts` 配置中将宿主机目录错误挂载为读写权限

**影响范围**

恶意或被注入的 Agent Prompt 可能突破沙箱限制，删除宿主机上的文件（如 `rm -rf $HOME`）、访问 `denied_domains` 列表外的网络端点，或在宿主机上建立持久化后门。

**可观测信号**

- Docker 容器日志中出现异常系统调用（`ptrace`、`mount`、`capset`）
- 宿主机文件系统出现非预期的修改时间戳（`find ~/. -mmin -5`）
- `SandboxSettings` 配置中的 `deny_write` 规则未被正确执行（如 `rm -rf /` 在沙箱内执行成功）
- 网络连接日志显示容器内进程连接了 `allowed_domains` 之外的端点

**缓解动作**

1. `DockerSandboxSettings` 提供了资源约束配置（`memory_limit`、`cpu_limit`），但不足以防止文件系统逃逸
2. 沙箱配置应遵循最小权限原则：显式列出 `allow_write` 目录，配置 `deny_write=/` 和 `deny_read=/etc/shadow`
3. 使用非特权容器运行（默认 `docker run` 不带 `--privileged`）
4. 定期使用 `trivy` 或 `grype` 扫描 `openharness-sandbox` 镜像的已知 CVE

---

### 风险 7：Cron Scheduler 多实例竞争（类别：运维）

**触发条件**

用户多次运行 `oh cron start`（如在脚本中无条件调用、未检查调度器是否已在运行），或 PID 文件残留（调度器因 SIGKILL 非正常退出，导致 `scheduler.pid` 文件未被删除）。

**影响范围**

多个 Cron Scheduler 守护进程实例同时运行，每个实例都按相同的 cron 表达式触发任务，导致重复执行（任务被执行两次或更多次），浪费 API 调用配额，严重时可能导致数据损坏（如同一个 commit 被 push 多次）。

**可观测信号**

- `ps aux | grep "cron_scheduler"` 显示多个 Python 进程
- `~/.openharness/data/cron/history/` 目录中同一任务的执行时间戳过于接近（间隔 <1 分钟）
- API 调用日志中出现相同任务描述的重复请求
- `cron_scheduler.log` 出现写入冲突（多个进程同时追加同一文件）

**缓解动作**

1. `start_daemon()` 函数在 fork 前检查 PID 文件是否存在，如果存在则验证对应进程是否仍在运行
2. `is_scheduler_running()` 通过 `os.kill(pid, 0)` 检测 PID 是否有效，避免仅依赖文件存在判断
3. 建议使用幂等性的 cron 任务设计，使重复执行不会产生副作用（如在任务开始时检查是否已有相同任务在运行）

---

### 风险 8：Git Worktree 路径冲突（类别：兼容性）

**触发条件**

Swarm Team 中的多个 Worker 被分配了相同的 Worktree 路径，或用户在项目目录中手动创建了与 Worktree 路径冲突的分支。冲突在 `git worktree add` 时被检测到，但如果 `WorktreeManager` 在并发场景下未正确加锁，可能出现 TOCTOU（Time-of-check to Time-of-use）竞态。

**影响范围**

Git 操作失败（`fatal: working tree ... already exists`），导致后续文件写入操作被路由到错误的 Worktree 目录，可能导致代码修改丢失或分支混乱。在最坏情况下，一个 Worker 的修改被另一个 Worker 意外覆盖。

**可观测信号**

- Worker 日志中出现 `git worktree add failed: fatal: working tree ... already exists`
- `git worktree list` 输出中存在重复的 worktree 路径
- 代码修改在主分支和工作分支之间出现不一致（diff 不符合预期）

**缓解动作**

1. `WorktreeManager.allocate_worktree` 在分配路径前调用 `git worktree list` 检查现有 Worktree，并在操作前后使用文件锁保护
2. Coordinator 应在 spawn Worker 时明确指定唯一的 `worktree_path`，避免自动分配路径冲突
3. `git worktree prune` 定期清理孤立（对应的目录已被删除但 worktree 引用仍存在）的 Worktree 条目

---

## 技术债

### 技术债 1：Provider Profile 与 API Client 的双轨解析

**描述**

`Settings` 类同时维护两套并行的配置表示：

1. **扁平字段**（legacy）：`settings.model`、`settings.provider`、`settings.api_format`、`settings.base_url` 等顶层字段
2. **Profile 层**（modern）：`settings.profiles[profile_name]`（`ProviderProfile` 对象）

`Settings` 提供了双向转换方法：`materialize_active_profile()`（Profile → 扁平字段）和 `sync_active_profile_from_flat_fields()`（扁平字段 → Profile）。这种双轨设计在以下场景中产生微妙的行为：

- 用户在 `settings.json` 中同时设置了顶层字段和 `profiles` 时，合并优先级不够透明
- `resolve_auth()` 需要同时处理多种认证来源（API Key、环境变量、外部 CLI 桥接），每种 Provider 的认证路径分散在多处
- 新增 Provider 需要在 `default_provider_profiles`、`auth_source_provider_name`、`default_auth_source_for_provider` 等多处同时修改

**影响**

- 添加新 Provider 需要修改至少 4 个函数中的代码，容易遗漏
- 测试需要覆盖多种 Provider × 认证来源的组合矩阵，测试用例数量膨胀
- 配置迁移（如将 legacy 扁平字段迁移到 Profile 层）缺乏自动化工具

**代码证据：** `src/openharness/config/settings.py` → `Settings.sync_active_profile_from_flat_fields`（第 510 行），`Settings.materialize_active_profile`（第 488 行），`default_auth_source_for_provider`（第 341 行），`resolve_model_setting`（第 266 行）。

---

### 技术债 2：BackgroundTaskManager 的重启锁逻辑复杂度

**描述**

`BackgroundTaskManager` 的 `_ensure_writable_process` 和 `_restart_agent_task` 方法共同处理 Agent 进程的自动重启，但逻辑分支较多：

- 当 `write_to_task` 遇到 `BrokenPipeError` 或 `ConnectionResetError` 时，判断任务类型是否允许重启（`local_agent`、`remote_agent`、`in_process_teammate`）
- 重启时使用 `_generations` 计数器防止旧 generation 的进程干扰新 generation 的状态
- 重启计数存储在 `task.metadata["restart_count"]` 中，但该字段没有上限检查，可能导致无限重启循环

**影响**

- 复杂的分支逻辑增加了测试难度，重启边界条件的单元测试覆盖不完整
- 无限重启循环在 API 持续失败时可能导致大量子进程反复 spawn，耗尽系统进程数（`ulimit -u`）或 API 配额
- `_restart_agent_task` 中 `await waiter` 的等待逻辑在进程快速退出时可能引入微妙的竞态条件

**代码证据：** `src/openharness/tasks/manager.py` → `_ensure_writable_process`（第 229 行），`_restart_agent_task`（第 240 行）。

---

### 技术债 3：Plugin 加载器的路径解析多版本共存

**描述**

`PluginLoader` 需要兼容两种插件目录布局：

1. **标准布局**：`~/.openharness/plugins/<name>/plugin.json`
2. **Claude 插件布局**：`~/.openharness/plugins/<name>/.claude-plugin/plugin.json`

`_find_manifest` 函数依次检查两个候选路径，但：

- 对于 `.claude-plugin/` 布局，插件的命令文件（`commands/`）和 skills 文件（`skills/`）的相对路径计算可能与标准布局不一致
- 插件的 `SKILL.md` 识别逻辑（通过检查子目录中是否存在 `SKILL.md` 文件）依赖于文件系统的遍历顺序
- 插件加载失败时静默返回 `None`，不提供详细的错误诊断，用户难以定位加载失败原因

**影响**

- 从 Claude Code 迁移过来的插件在 OpenHarness 中可能部分加载（如 skills 可用但 commands 不可用），行为不一致
- 调试插件加载问题需要对比两种目录布局的路径解析逻辑

**代码证据：** `src/openharness/plugins/loader.py` → `_find_manifest`（第 47 行），`_walk_plugin_markdown`（第 159 行），`load_plugin`（第 88 行）的异常处理分支。

---

### 技术债 4：Channels 层的长连接管理重复

**描述**

每个通道实现（Slack、Discord、钉钉、飞书、Telegram、WhatsApp、Matrix、QQ、MoChat）都需要独立实现以下逻辑：

- 连接建立（WebSocket 握手或 Polling 启动）
- 断线重连（指数退避策略）
- 心跳保活
- 消息去重（处理平台的消息重试机制）
- 消息格式化（将平台格式转换为 OpenHarness 内部消息格式）

这些逻辑在 10 个通道实现中高度重复，没有提取到共享的基类中。虽然存在 `ChannelAdapter` 基类接口，但具体的通道实现（`src/openharness/channels/impl/`）各自维护了自己的连接管理代码。

**影响**

- 每个新通道的接入都需要重新实现上述逻辑，容易引入 bug
- 断线重连策略在各通道中的实现参数不一致（退避时间、重试次数），难以统一运维
- 难以对连接健康状态进行统一的监控和告警

**代码证据：** `src/openharness/channels/impl/slack.py`、`src/openharness/channels/impl/discord.py`、`src/openharness/channels/impl/telegram.py` 等各通道实现中的重复连接管理代码。

---

### 技术债 5：Coordinator 系统提示词的字符串拼接构造

**描述**

`get_coordinator_system_prompt()`（`src/openharness/coordinator/coordinator_mode.py`）通过多行字符串拼接和条件分支构造 Coordinator 的系统提示词：

```python
if is_simple:
    worker_capabilities = "Workers have access to Bash, Read, and Edit tools..."
else:
    worker_capabilities = "Workers have access to standard tools..."

return f"""You are Claude Code, an AI assistant that orchestrates...

## 2. Your Tools

- **{_AGENT_TOOL_NAME}** - Spawn a new worker
...
## 4. Task Workflow

Most tasks can be broken down...
"""
```

这个提示词包含约 500 行文本硬编码在 Python 代码中，存在以下问题：

- 无法热更新——修改提示词需要修改源代码并重新部署
- 缺乏版本控制——提示词的变更历史无法与代码 commit 一一对应
- 测试困难——提示词的内容正确性无法通过单元测试验证，只能通过集成测试观察 Agent 行为来间接验证
- 国际化缺失——提示词不支持多语言，无法在非英语环境中使用

**影响**

- 提示词的迭代周期受制于代码部署周期，无法快速 A/B 测试不同的提示词策略
- 提示词中的工具名称硬编码（如 `_AGENT_TOOL_NAME = "agent"`），在工具重命名时需要同步修改多处
- `<task-notification>` 的 XML 格式规范也在提示词中硬编码，如果未来迁移到 JSON 格式，需要同时修改代码和提示词

**代码证据：** `src/openharness/coordinator/coordinator_mode.py` → `get_coordinator_system_prompt`（第 251 行起，约 270 行的字符串字面量）。

---

## 风险分类总览

| # | 风险名称 | 类别 | 状态 | 优先级 |
|---|---------|------|------|--------|
| 1 | Anthropic API 单点故障 | API 依赖 | 已知 | 高 |
| 2 | MCP stdio 冷启动超时 | 性能 | 已知 | 中 |
| 3 | Worker Agent 孤儿化 | 运维 | 已知 | 中 |
| 4 | Coordinator XML 解析脆弱性 | 兼容性 | 已知 | 中 |
| 5 | Plugin 动态代码执行 | 安全 | 已知 | 高 |
| 6 | Sandbox 逃逸 | 安全 | 已知 | 高 |
| 7 | Cron Scheduler 多实例竞争 | 运维 | 已知 | 低 |
| 8 | Git Worktree 路径冲突 | 兼容性 | 已知 | 低 |

---

## 技术债分类总览

| # | 技术债名称 | 影响维度 | 建议行动 |
|---|----------|---------|---------|
| 1 | Provider Profile 与 API Client 双轨解析 | 可维护性、可扩展性 | 统一为 Profile 层，废弃 legacy 扁平字段 |
| 2 | BackgroundTaskManager 重启锁逻辑 | 可靠性、可测试性 | 添加重启次数上限，提取为独立的状态机模块 |
| 3 | Plugin 加载器路径多版本共存 | 可移植性 | 统一为单一目录布局，移除 Claude 兼容路径 |
| 4 | Channels 长连接管理重复 | 可维护性 | 提取共享基类（ReconnectingChannelAdapter） |
| 5 | Coordinator 提示词字符串拼接 | 可演进性、可测试性 | 外置到配置文件，支持热加载和版本化 |
