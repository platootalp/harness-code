# 配置参考

## 摘要

OpenHarness 的所有运行时行为由 `Settings` Pydantic 模型驱动。本页详细说明各配置字段的含义、配置优先级、内置 Provider Profile 以及子配置块的结构。

## 你将了解

- `Settings` 主模型的所有字段及说明
- 配置优先级：CLI args > ENV > config file > defaults
- `ProviderProfile`、`PermissionSettings`、`SandboxSettings`、`MemorySettings`、`McpServerConfig` 的完整结构
- 内置 Provider Profile（`claude-api`、`openai-compatible`、`copilot` 等）的差异
- Hook 配置、插件启用等高级选项

## 范围

基于 `openharness/config/settings.py` 中 `Settings` Pydantic 模型 v0.1.6。

---

## 配置优先级

配置值按以下优先级从高到低解析：

```
1. CLI 参数（oh -m opus --print "..."）
2. 环境变量（ANTHROPIC_API_KEY、OPENHARNESS_MODEL 等）
3. 配置文件（~/.openharness/settings.json）
4. 代码默认值
```

> 证据来源：`src/openharness/config/settings.py` 顶部文档字符串

---

## 主模型：Settings

`Settings` 是 OpenHarness 的根配置模型，位于 `src/openharness/config/settings.py`。

### API 配置字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | `str` | `""` | 直接配置的 API 密钥 |
| `model` | `str` | `"claude-sonnet-4-6"` | 默认模型 |
| `max_tokens` | `int` | `16384` | 单次请求最大输出 Token 数 |
| `base_url` | `str \| None` | `None` | API Base URL（覆盖默认端点） |
| `timeout` | `float` | `30.0` | 请求超时时间（秒） |
| `context_window_tokens` | `int \| None` | `None` | 上下文窗口大小（Token），用于自动压缩触发 |
| `auto_compact_threshold_tokens` | `int \| None` | `None` | 自动压缩阈值（Token 数） |
| `api_format` | `str` | `"anthropic"` | API 格式：`anthropic`、`openai`、`copilot` |
| `provider` | `str` | `""` | 运行时 Provider ID |
| `active_profile` | `str` | `"claude-api"` | 当前活跃的 Provider Profile 名称 |
| `profiles` | `dict[str, ProviderProfile]` | `default_provider_profiles()` | 所有 Provider Profile 的映射表 |
| `max_turns` | `int` | `200` | 最大 Agent 轮次数 |

### 行为配置字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `system_prompt` | `str \| None` | `None` | 覆盖默认系统提示词 |
| `permission` | `PermissionSettings` | `PermissionSettings()` | 权限模式配置 |
| `hooks` | `dict[str, list[HookDefinition]]` | `{}` | 生命周期 Hook 定义 |
| `memory` | `MemorySettings` | `MemorySettings()` | 记忆系统配置 |
| `sandbox` | `SandboxSettings` | `SandboxSettings()` | 沙箱运行时配置 |
| `enabled_plugins` | `dict[str, bool]` | `{}` | 插件启用/禁用映射表 |
| `mcp_servers` | `dict[str, McpServerConfig]` | `{}` | MCP 服务器配置映射表 |

### UI 配置字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `theme` | `str` | `"default"` | TUI 主题：`default`、`dark`、`minimal`、`cyberpunk`、`solarized` |
| `output_style` | `str` | `"default"` | 输出样式 |
| `vim_mode` | `bool` | `False` | 启用 Vim 键盘模式 |
| `voice_mode` | `bool` | `False` | 启用语音模式 |
| `fast_mode` | `bool` | `False` | 快速模式（减少延迟） |
| `effort` | `str` | `"medium"` | 努力级别：`low`、`medium`、`high` |
| `passes` | `int` | `1` | Agent 遍历次数 |
| `verbose` | `bool` | `False` | 详细输出模式 |

> 证据来源：`src/openharness/config/settings.py` -> `Settings` 类（行 427-461）

---

## ProviderProfile 配置

`ProviderProfile` 定义一个命名的工作流配置，包括 Provider、认证源和模型设置。

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `label` | `str` | 用户可见的显示名称 |
| `provider` | `str` | 运行时 Provider ID（如 `anthropic`、`openai`、`copilot`） |
| `api_format` | `str` | API 格式：`anthropic`、`openai`、`copilot` |
| `auth_source` | `str` | 认证源名称（如 `anthropic_api_key`、`copilot_oauth`） |
| `default_model` | `str` | 该 Profile 的默认模型 |
| `base_url` | `str \| None` | 可选的 Base URL（OpenAI 兼容 Provider 使用） |
| `last_model` | `str \| None` | 用户最近一次选择的模型 |
| `credential_slot` | `str \| None` | Profile 专用的凭证存储槽位 |
| `allowed_models` | `list[str]` | 允许的模型列表（空表示不限制） |
| `context_window_tokens` | `int \| None` | 上下文窗口 Token 数覆盖 |
| `auto_compact_threshold_tokens` | `int \| None` | 自动压缩阈值 Token 数覆盖 |

### resolved_model 属性

```python
profile.resolved_model  # -> "claude-sonnet-4-6"
```

返回该 Profile 当前激活的模型：`last_model` 或 `default_model` 经 `resolve_model_setting()` 解析后的结果。

> 证据来源：`src/openharness/config/settings.py` -> `ProviderProfile` 类（行 107-129）

---

## PermissionSettings 配置

权限模式配置，控制 Agent 可以执行哪些工具和命令。

### 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `mode` | `PermissionMode` | `PermissionMode.DEFAULT` | 权限模式 |
| `allowed_tools` | `list[str]` | `[]` | 允许的工具名称列表 |
| `denied_tools` | `list[str]` | `[]` | 拒绝的工具名称列表 |
| `path_rules` | `list[PathRuleConfig]` | `[]` | 路径权限规则（glob 模式） |
| `denied_commands` | `list[str]` | `[]` | 拒绝执行的命令列表 |

### PathRuleConfig

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pattern` | `str` | - | glob 模式（如 `**/.env`） |
| `allow` | `bool` | `True` | 匹配时是允许还是拒绝 |

### 权限模式值

- `default`：默认交互式确认模式
- `plan`：仅规划模式，不执行写入操作
- `full_auto`：完全自动，假设已在沙箱中

> 证据来源：`src/openharness/config/settings.py` -> `PermissionSettings` 类（行 48-55）；`src/openharness/permissions/modes.py` -> `PermissionMode` 枚举

---

## SandboxSettings 配置

沙箱运行时集成配置，用于限制 Agent 子进程的网络和文件系统访问。

### 主字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | `bool` | `False` | 是否启用沙箱 |
| `backend` | `str` | `"srt"` | 沙箱后端：`srt`（sandbox-runtime CLI）或 `docker` |
| `fail_if_unavailable` | `bool` | `False` | 沙箱不可用时是否报错退出 |
| `enabled_platforms` | `list[str]` | `[]` | 启用沙箱的平台列表（空表示所有平台） |
| `network` | `SandboxNetworkSettings` | `SandboxNetworkSettings()` | 网络限制 |
| `filesystem` | `SandboxFilesystemSettings` | `SandboxFilesystemSettings()` | 文件系统限制 |
| `docker` | `DockerSandboxSettings` | `DockerSandboxSettings()` | Docker 专用配置 |

### SandboxNetworkSettings

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `allowed_domains` | `list[str]` | `[]` | 允许访问的域名列表 |
| `denied_domains` | `list[str]` | `[]` | 拒绝访问的域名列表 |

### SandboxFilesystemSettings

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `allow_read` | `list[str]` | `[]` | 允许读取的路径（glob 模式） |
| `deny_read` | `list[str]` | `[]` | 拒绝读取的路径 |
| `allow_write` | `list[str]` | `["."]` | 允许写入的路径（默认当前目录） |
| `deny_write` | `list[str]` | `[]` | 拒绝写入的路径 |

### DockerSandboxSettings

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `image` | `str` | `"openharness-sandbox:latest"` | Docker 镜像 |
| `auto_build_image` | `bool` | `True` | 自动构建镜像 |
| `cpu_limit` | `float` | `0.0` | CPU 限制（核心数） |
| `memory_limit` | `str` | `""` | 内存限制（如 `"2g"`） |
| `extra_mounts` | `list[str]` | `[]` | 额外挂载点 |
| `extra_env` | `dict[str, str]` | `{}` | 额外环境变量 |

> 证据来源：`src/openharness/config/settings.py` -> `SandboxSettings`、`SandboxNetworkSettings`、`SandboxFilesystemSettings`、`DockerSandboxSettings`（行 41-104）

---

## MemorySettings 配置

记忆系统配置，控制对话历史压缩和上下文管理。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | `bool` | `True` | 是否启用记忆系统 |
| `max_files` | `int` | `5` | 注入到上下文的最多文件数 |
| `max_entrypoint_lines` | `int` | `200` | 每个入口文件的最多行数 |
| `context_window_tokens` | `int \| None` | `None` | 上下文窗口 Token 数 |
| `auto_compact_threshold_tokens` | `int \| None` | `None` | 自动压缩触发阈值 |

> 证据来源：`src/openharness/config/settings.py` -> `MemorySettings` 类（行 58-65）

---

## HookDefinition 配置

Hook 定义支持四种类型，通过 discriminated union 实现。

### CommandHookDefinition

```python
type: Literal["command"] = "command"
command: str                          # 要执行的 shell 命令
timeout_seconds: int = 30             # 超时时间（1-600 秒）
matcher: str | None = None           # 输出匹配正则（触发条件）
block_on_failure: bool = False       # 失败时是否阻塞
```

### PromptHookDefinition

```python
type: Literal["prompt"] = "prompt"
prompt: str                           # 询问模型的提示词
model: str | None = None              # 使用的模型（默认继承）
timeout_seconds: int = 30             # 超时时间
matcher: str | None = None            # 输出匹配正则
block_on_failure: bool = True        # 失败时阻塞（默认 True）
```

### HttpHookDefinition

```python
type: Literal["http"] = "http"
url: str                              # POST 目标 URL
headers: dict[str, str] = {}         # HTTP 请求头
timeout_seconds: int = 30            # 超时时间
matcher: str | None = None           # 响应匹配正则
block_on_failure: bool = False       # 失败时是否阻塞
```

### AgentHookDefinition

```python
type: Literal["agent"] = "agent"
prompt: str                           # Agent 验证提示词
model: str | None = None              # 使用的模型
timeout_seconds: int = 60            # 超时时间（1-1200 秒）
matcher: str | None = None           # 输出匹配正则
block_on_failure: bool = True        # 失败时阻塞（默认 True）
```

Hook 在 `Settings.hooks` 中按生命周期事件注册：

```python
hooks: dict[str, list[HookDefinition]] = {
    "on_tool_call": [...],
    "on_message": [...],
    "on_error": [...],
}
```

> 证据来源：`src/openharness/hooks/schemas.py` -> `CommandHookDefinition`、`PromptHookDefinition`、`HttpHookDefinition`、`AgentHookDefinition` 和 `HookDefinition` 联合类型（行 10-58）

---

## McpServerConfig 配置

MCP 服务器配置支持三种传输方式，通过 discriminated union 实现。

### McpStdioServerConfig

```python
type: Literal["stdio"] = "stdio"
command: str                           # 启动命令
args: list[str] = []                 # 命令参数
env: dict[str, str] | None = None    # 环境变量
cwd: str | None = None               # 工作目录
```

### McpHttpServerConfig

```python
type: Literal["http"] = "http"
url: str                              # HTTP 服务器 URL
headers: dict[str, str] = {}         # 请求头
```

### McpWebSocketServerConfig

```python
type: Literal["ws"] = "ws"
url: str                              # WebSocket 服务器 URL
headers: dict[str, str] = {}         # 请求头
```

MCP 服务器在 `Settings.mcp_servers` 中注册：

```python
mcp_servers: dict[str, McpServerConfig] = {
    "my-server": McpStdioServerConfig(
        type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    ),
    "remote-api": McpHttpServerConfig(
        type="http",
        url="https://api.example.com/mcp",
        headers={"Authorization": "Bearer ..."}
    ),
}
```

> 证据来源：`src/openharness/mcp/types.py` -> `McpStdioServerConfig`、`McpHttpServerConfig`、`McpWebSocketServerConfig` 和 `McpServerConfig` 联合类型（行 11-37）

---

## enabled_plugins 配置

插件启用/禁用映射表，键为插件名称，值为布尔值。

```python
enabled_plugins: dict[str, bool] = {
    "my-plugin": True,
    "disabled-plugin": False,
}
```

未在映射表中出现的插件默认不启用（取决于插件加载器行为）。

> 证据来源：`src/openharness/config/settings.py` -> `Settings.enabled_plugins` 字段（行 450）

---

## 内置 Provider Profile

OpenHarness 内置以下 Provider Profile，通过 `default_provider_profiles()` 函数返回：

### claude-api

Anthropic 官方 API。

```python
"claude-api": ProviderProfile(
    label="Anthropic-Compatible API",
    provider="anthropic",
    api_format="anthropic",
    auth_source="anthropic_api_key",
    default_model="claude-sonnet-4-6",
    # base_url = None（使用 Anthropic 默认端点）
)
```

### claude-subscription

Claude 订阅（通过 Claude CLI 管理）。

```python
"claude-subscription": ProviderProfile(
    label="Claude Subscription",
    provider="anthropic_claude",
    api_format="anthropic",
    auth_source="claude_subscription",
    default_model="claude-sonnet-4-6",
)
```

### openai-compatible

OpenAI 官方 API。

```python
"openai-compatible": ProviderProfile(
    label="OpenAI-Compatible API",
    provider="openai",
    api_format="openai",
    auth_source="openai_api_key",
    default_model="gpt-5.4",
)
```

### codex

OpenAI Codex 订阅（通过 Codex CLI 管理）。

```python
"codex": ProviderProfile(
    label="Codex Subscription",
    provider="openai_codex",
    api_format="openai",
    auth_source="codex_subscription",
    default_model="gpt-5.4",
)
```

### copilot

GitHub Copilot（通过 OAuth 设备码流程认证）。

```python
"copilot": ProviderProfile(
    label="GitHub Copilot",
    provider="copilot",
    api_format="copilot",
    auth_source="copilot_oauth",
    default_model="gpt-5.4",
)
```

### moonshot

Moonshot Kimi（月之暗面）。

```python
"moonshot": ProviderProfile(
    label="Moonshot (Kimi)",
    provider="moonshot",
    api_format="openai",
    auth_source="moonshot_api_key",
    default_model="kimi-k2.5",
    base_url="https://api.moonshot.cn/v1",
)
```

### gemini

Google Gemini。

```python
"gemini": ProviderProfile(
    label="Google Gemini",
    provider="gemini",
    api_format="openai",
    auth_source="gemini_api_key",
    default_model="gemini-2.5-flash",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
)
```

### 各 Profile 差异汇总

| Profile | Provider ID | API 格式 | 认证源 | 默认模型 | Base URL |
|---------|-------------|----------|--------|----------|----------|
| `claude-api` | `anthropic` | `anthropic` | `anthropic_api_key` | `claude-sonnet-4-6` | Anthropic 默认 |
| `claude-subscription` | `anthropic_claude` | `anthropic` | `claude_subscription` | `claude-sonnet-4-6` | Anthropic 默认 |
| `openai-compatible` | `openai` | `openai` | `openai_api_key` | `gpt-5.4` | OpenAI 默认 |
| `codex` | `openai_codex` | `openai` | `codex_subscription` | `gpt-5.4` | OpenAI 默认 |
| `copilot` | `copilot` | `copilot` | `copilot_oauth` | `gpt-5.4` | Copilot 默认 |
| `moonshot` | `moonshot` | `openai` | `moonshot_api_key` | `kimi-k2.5` | `api.moonshot.cn/v1` |
| `gemini` | `gemini` | `openai` | `gemini_api_key` | `gemini-2.5-flash` | `generativelanguage.googleapis.com` |

> 证据来源：`src/openharness/config/settings.py` -> `default_provider_profiles()` 函数（行 179-233）

---

## 模型别名解析

Claude 家族 Provider 支持以下模型别名：

| 别名 | 解析结果 | 说明 |
|------|----------|------|
| `default` | `claude-sonnet-4-6` | 推荐模型 |
| `best` | `claude-opus-4-6` | 最强能力模型 |
| `sonnet` | `claude-sonnet-4-6` | 最新 Sonnet |
| `opus` | `claude-opus-4-6` | 最新 Opus |
| `haiku` | `claude-haiku-4-5` | 最快模型 |
| `sonnet[1m]` | `claude-sonnet-4-6[1m]` | 1M 上下文 Sonnet |
| `opus[1m]` | `claude-opus-4-6[1m]` | 1M 上下文 Opus |
| `opusplan` | `claude-opus-4-6`（plan 模式）或 `claude-sonnet-4-6` | 规划时用 Opus，其他用 Sonnet |

> 证据来源：`src/openharness/config/settings.py` -> `CLAUDE_MODEL_ALIAS_OPTIONS`、`_CLAUDE_ALIAS_TARGETS`（行 143-160）和 `resolve_model_setting()` 函数（行 266-304）

---

## 完整配置文件示例

```json
{
  "active_profile": "claude-api",
  "profiles": {
    "claude-api": {
      "label": "Anthropic-Compatible API",
      "provider": "anthropic",
      "api_format": "anthropic",
      "auth_source": "anthropic_api_key",
      "default_model": "claude-sonnet-4-6",
      "last_model": "sonnet",
      "base_url": null,
      "allowed_models": []
    },
    "moonshot": {
      "label": "Moonshot (Kimi)",
      "provider": "moonshot",
      "api_format": "openai",
      "auth_source": "moonshot_api_key",
      "default_model": "kimi-k2.5",
      "last_model": "kimi-k2.5",
      "base_url": "https://api.moonshot.cn/v1",
      "allowed_models": ["kimi-k2.5"]
    }
  },
  "permission": {
    "mode": "default",
    "allowed_tools": [],
    "denied_tools": ["bash"],
    "path_rules": [
      {"pattern": "**/.env", "allow": false}
    ],
    "denied_commands": []
  },
  "sandbox": {
    "enabled": true,
    "backend": "srt",
    "fail_if_unavailable": false,
    "enabled_platforms": ["linux", "macos"],
    "network": {
      "allowed_domains": ["github.com", "api.github.com"],
      "denied_domains": []
    },
    "filesystem": {
      "allow_read": ["."],
      "deny_read": ["**/.ssh/**", "**/.aws/**"],
      "allow_write": ["."],
      "deny_write": ["**/.env", "**/node_modules/**"]
    },
    "docker": {
      "image": "openharness-sandbox:latest",
      "auto_build_image": true,
      "cpu_limit": 2.0,
      "memory_limit": "4g",
      "extra_mounts": [],
      "extra_env": {}
    }
  },
  "memory": {
    "enabled": true,
    "max_files": 5,
    "max_entrypoint_lines": 200,
    "context_window_tokens": 200000,
    "auto_compact_threshold_tokens": 150000
  },
  "theme": "dark",
  "verbose": false,
  "mcp_servers": {}
}
```

> 证据来源：`src/openharness/config/settings.py` -> `load_settings()` 和 `save_settings()` 函数（行 817-866）

---

## 环境变量覆盖参考

以下环境变量可以直接覆盖配置文件中的值：

| 环境变量 | 覆盖字段 | 类型 |
|----------|----------|------|
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | `api_key` | `str` |
| `ANTHROPIC_MODEL` / `OPENHARNESS_MODEL` | `model` | `str` |
| `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` / `OPENHARNESS_BASE_URL` | `base_url` | `str` |
| `OPENHARNESS_MAX_TOKENS` | `max_tokens` | `int` |
| `OPENHARNESS_TIMEOUT` | `timeout` | `float` |
| `OPENHARNESS_MAX_TURNS` | `max_turns` | `int` |
| `OPENHARNESS_CONTEXT_WINDOW_TOKENS` | `context_window_tokens` | `int` |
| `OPENHARNESS_AUTO_COMPACT_THRESHOLD_TOKENS` | `auto_compact_threshold_tokens` | `int` |
| `OPENHARNESS_API_FORMAT` | `api_format` | `str` |
| `OPENHARNESS_PROVIDER` | `provider` | `str` |
| `OPENHARNESS_SANDBOX_ENABLED` | `sandbox.enabled` | `bool` |
| `OPENHARNESS_SANDBOX_FAIL_IF_UNAVAILABLE` | `sandbox.fail_if_unavailable` | `bool` |
| `OPENHARNESS_SANDBOX_BACKEND` | `sandbox.backend` | `str` |
| `OPENHARNESS_SANDBOX_DOCKER_IMAGE` | `sandbox.docker.image` | `str` |

> 证据来源：`src/openharness/config/settings.py` -> `_apply_env_overrides()` 函数（行 740-809）

---

## 证据索引

1. `src/openharness/config/settings.py` -> `Settings` 主类（行 427-508）
2. `src/openharness/config/settings.py` -> `ProviderProfile` 类（行 107-129）
3. `src/openharness/config/settings.py` -> `PermissionSettings` 类（行 48-55）
4. `src/openharness/config/settings.py` -> `PathRuleConfig` 类（行 41-45）
5. `src/openharness/config/settings.py` -> `SandboxSettings` 类（行 95-104）
6. `src/openharness/config/settings.py` -> `SandboxNetworkSettings`、`SandboxFilesystemSettings`、`DockerSandboxSettings`（行 68-104）
7. `src/openharness/config/settings.py` -> `MemorySettings` 类（行 58-65）
8. `src/openharness/config/settings.py` -> `default_provider_profiles()` 函数（行 179-233）
9. `src/openharness/config/settings.py` -> `CLAUDE_MODEL_ALIAS_OPTIONS` 和 `_CLAUDE_ALIAS_TARGETS`（行 143-160）
10. `src/openharness/config/settings.py` -> `resolve_model_setting()` 函数（行 266-304）
11. `src/openharness/config/settings.py` -> `_apply_env_overrides()` 函数（行 740-809）
12. `src/openharness/config/settings.py` -> `load_settings()` 和 `save_settings()` 函数（行 817-866）
13. `src/openharness/config/settings.py` -> `Settings.merge_cli_overrides()` 方法（行 712-737）
14. `src/openharness/config/settings.py` -> `Settings.resolve_profile()` 方法（行 478-486）
15. `src/openharness/config/settings.py` -> `Settings.materialize_active_profile()` 方法（行 488-508）
16. `src/openharness/hooks/schemas.py` -> `HookDefinition` 联合类型及四个子类型（行 10-58）
17. `src/openharness/mcp/types.py` -> `McpServerConfig` 联合类型及三个传输类型（行 11-37）
18. `src/openharness/config/settings.py` -> `is_claude_family_provider()` 和 `auth_source_provider_name()`（行 253-321）
