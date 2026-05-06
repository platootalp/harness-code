# CLI 参考

## 摘要

OpenHarness 通过 `oh`（或 `openharness`）命令提供完整的命令行接口。本页详细列出所有全局参数、子命令及其选项。

## 你将了解

- 主命令 `oh` / `openharness` 的所有全局参数
- 所有子命令的完整用法：`oh mcp`、`oh plugin`、`oh auth`、`oh provider`、`oh cron`、`oh setup`
- 配置覆盖参数（`--model`、`--print`、`--permission-mode` 等）
- 环境变量与 CLI 参数的交互关系

## 范围

覆盖 CLI v0.1.6 中所有已实现的命令和选项。

---

## 全局参数

主命令 `oh`（或 `openharness`）支持以下全局选项，按功能分组：

### 会话控制（Session）

| 参数 | 简写 | 类型 | 说明 |
|------|------|------|------|
| `--continue` | `-c` | bool | 继续当前目录最近一次对话 |
| `--resume` | `-r` | str \| None | 通过 session ID 恢复会话；空值则打开会话选择器 |
| `--name` | `-n` | str \| None | 为本次会话设置显示名称 |

### 模型与努力级别（Model & Effort）

| 参数 | 简写 | 类型 | 说明 |
|------|------|------|------|
| `--model` | `-m` | str \| None | 模型别名（如 `sonnet`、`opus`）或完整模型 ID |
| `--effort` | - | str \| None | 会话努力级别：`low`、`medium`、`high`、`max` |
| `--verbose` | - | bool | 覆盖配置中的 verbose 模式 |
| `--max-turns` | - | int \| None | 最大 Agent 轮次数（`--print` 模式下强制生效） |

### 输出控制（Output）

| 参数 | 简写 | 类型 | 说明 |
|------|------|------|------|
| `--print` | `-p` | str \| None | 打印模式：将提示词作为值传递，直接输出后退出 |
| `--output-format` | - | str \| None | `--print` 模式下的输出格式：`text`（默认）、`json`、`stream-json` |

### 权限控制（Permissions）

| 参数 | 简写 | 类型 | 说明 |
|------|------|------|------|
| `--permission-mode` | - | str \| None | 权限模式：`default`、`plan`、`full_auto` |
| `--dangerously-skip-permissions` | - | bool | 跳过所有权限检查（仅限沙箱环境） |
| `--allowed-tools` | - | list[str] \| None | 逗号或空格分隔的允许工具名称列表 |
| `--disallowed-tools` | - | list[str] \| None | 逗号或空格分隔的拒绝工具名称列表 |

### 系统与上下文（System & Context）

| 参数 | 简写 | 类型 | 说明 |
|------|------|------|------|
| `--system-prompt` | `-s` | str \| None | 覆盖默认系统提示词 |
| `--append-system-prompt` | - | str \| None | 向默认系统提示词追加内容 |
| `--settings` | - | str \| None | JSON 配置文件路径或内联 JSON 字符串 |
| `--base-url` | - | str \| None | Anthropic 兼容 API 的 base URL |
| `--api-key` | `-k` | str \| None | API 密钥（覆盖配置和环境变量） |
| `--bare` | - | bool | 最小化模式：跳过 hooks、插件、MCP 和自动发现 |
| `--api-format` | - | str \| None | API 格式：`anthropic`（默认）、`openai`、`copilot` |
| `--theme` | - | str \| None | TUI 主题：`default`、`dark`、`minimal`、`cyberpunk`、`solarized` 或自定义名称 |

### 高级选项（Advanced）

| 参数 | 简写 | 类型 | 说明 |
|------|------|------|------|
| `--debug` | `-d` | bool | 启用调试日志 |
| `--mcp-config` | - | list[str] \| None | 从 JSON 文件或字符串加载 MCP 服务器 |
| `--cwd` | - | str | 会话工作目录（默认当前目录） |
| `--version` | `-v` | bool | 显示版本号并退出 |

> 证据来源：`src/openharness/cli.py` -> `main()` 中的所有 `typer.Option` 参数定义

---

## 子命令：`oh`（默认 REPL）

不带任何子命令时，`oh` 启动交互式 REPL 会话：

```bash
oh                              # 启动交互式会话
oh -c                           # 继续最近会话
oh -r <session_id>              # 恢复指定会话
oh -p "你的提示词"              # 单次查询模式
oh -m opus -c                   # 使用 Opus 模型继续会话
```

---

## 子命令：`oh mcp`

MCP（MCP Protocol）服务器管理。

### `oh mcp list`

列出所有已配置的 MCP 服务器。

```bash
oh mcp list
```

输出示例：

```
  my-server: stdio
  github-mcp: http
```

### `oh mcp add <name> <config_json>`

添加 MCP 服务器配置。

```bash
oh mcp add my-server '{"type":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/tmp"]}'
```

- `name`：服务器名称（唯一标识）
- `config_json`：服务器配置的 JSON 字符串

### `oh mcp remove <name>`

移除指定名称的 MCP 服务器配置。

```bash
oh mcp remove my-server
```

> 证据来源：`src/openharness/cli.py` -> `@mcp_app` 下的三个子命令（`mcp_list`、`mcp_add`、`mcp_remove`）

---

## 子命令：`oh plugin`

插件管理。

### `oh plugin list`

列出所有已安装的插件及其状态。

```bash
oh plugin list
```

输出示例：

```
  my-plugin [enabled] - A sample plugin
  disabled-plugin [disabled] - Another plugin
```

### `oh plugin install <source>`

从路径或 URL 安装插件。

```bash
oh plugin install /path/to/plugin
oh plugin install https://example.com/plugin.tar.gz
```

### `oh plugin uninstall <name>`

卸载指定名称的插件。

```bash
oh plugin uninstall my-plugin
```

> 证据来源：`src/openharness/cli.py` -> `@plugin_app` 下的三个子命令（`plugin_list`、`plugin_install`、`plugin_uninstall`）

---

## 子命令：`oh auth`

认证管理，支持多种 Provider。

### `oh auth login [provider]`

交互式认证 Provider。若不指定 provider，则显示菜单供选择。

```bash
oh auth login                      # 显示 Provider 选择菜单
oh auth login anthropic            # 认证 Anthropic API
oh auth login openai               # 认证 OpenAI API
oh auth login copilot              # 认证 GitHub Copilot
oh auth login anthropic_claude     # 认证 Claude 订阅
oh auth login openai_codex         # 认证 Codex 订阅
oh auth login moonshot             # 认证 Moonshot API
oh auth login gemini               # 认证 Google Gemini
```

支持的 Provider 列表：`anthropic`、`anthropic_claude`、`openai`、`openai_codex`、`copilot`、`dashscope`、`bedrock`、`vertex`、`moonshot`、`gemini`。

### `oh auth status`

显示认证源和 Provider Profile 状态。

```bash
oh auth status
```

输出包括：
- 各认证源的状态、来源、是否激活
- 各 Provider Profile 的 Provider、认证源、状态、是否激活

### `oh auth logout [provider]`

清除存储的认证信息。

```bash
oh auth logout                    # 清除当前活跃 Profile 的认证
oh auth logout anthropic          # 清除指定 Provider 的认证
```

### `oh auth switch <provider_or_profile>`

切换活跃的认证源或 Profile。

```bash
oh auth switch claude-api
oh auth switch openai
```

### `oh auth copilot-login`

通过设备码流程认证 GitHub Copilot（`oh auth login copilot` 的别名）。

```bash
oh auth copilot-login
```

### `oh auth codex-login`

将 OpenHarness 绑定到本地 Codex CLI 订阅会话。

```bash
oh auth codex-login
```

### `oh auth claude-login`

将 OpenHarness 绑定到本地 Claude CLI 订阅会话。

```bash
oh auth claude-login
```

### `oh auth copilot-logout`

清除存储的 GitHub Copilot 认证。

```bash
oh auth copilot-logout
```

> 证据来源：`src/openharness/cli.py` -> `@auth_app` 下的所有子命令，以及 `_PROVIDER_LABELS` 和 `_AUTH_SOURCE_LABELS` 映射表

---

## 子命令：`oh provider`

Provider Profile 管理。

### `oh provider list`

列出所有已配置的 Provider Profile。

```bash
oh provider list
```

输出示例：

```
* claude-api: Claude official [ready]
    auth=anthropic_api_key model=sonnet base_url=(default)
* openai-compatible: OpenAI / compatible [ready]
    auth=openai_api_key model=gpt-5.4 base_url=(default)
  moonshot: Moonshot (Kimi) [ready]
    auth=moonshot_api_key model=kimi-k2.5 base_url=https://api.moonshot.cn/v1
```

### `oh provider use <name>`

激活指定名称的 Provider Profile。

```bash
oh provider use claude-api
oh provider use moonshot
```

### `oh provider add <name>`

创建新的 Provider Profile。

```bash
oh provider add my-provider \
  --label "My Provider" \
  --provider anthropic \
  --api-format anthropic \
  --auth-source anthropic_api_key \
  --model sonnet \
  --base-url https://api.example.com/v1 \
  --credential-slot my-provider \
  --allowed-model sonnet \
  --context-window-tokens 200000 \
  --auto-compact-threshold-tokens 150000
```

所有选项：

| 选项 | 类型 | 说明 |
|------|------|------|
| `--label` | str | 显示标签（必填） |
| `--provider` | str | 运行时 Provider ID（必填） |
| `--api-format` | str | API 格式（必填） |
| `--auth-source` | str | 认证源名称（必填） |
| `--model` | str | 默认模型（必填） |
| `--base-url` | str \| None | 可选的 Base URL |
| `--credential-slot` | str \| None | 可选的 Profile 专用凭证槽 |
| `--allowed-model` | list[str] \| None | 允许的模型列表 |
| `--context-window-tokens` | int \| None | 可选的上下文窗口覆盖 |
| `--auto-compact-threshold-tokens` | int \| None | 可选的自动压缩阈值覆盖 |

### `oh provider edit <name>`

编辑现有 Provider Profile。

```bash
oh provider edit claude-api --model opus --label "Claude Official"
```

选项与 `oh provider add` 相同，均为可选参数。

### `oh provider remove <name>`

移除指定名称的 Provider Profile。

```bash
oh provider remove my-custom-provider
```

> 证据来源：`src/openharness/cli.py` -> `@provider_app` 下的五个子命令（`provider_list`、`provider_use`、`provider_add`、`provider_edit`、`provider_remove`）

---

## 子命令：`oh cron`

Cron 调度器管理。

### `oh cron start`

启动 Cron 调度器守护进程。

```bash
oh cron start
```

已在运行时输出：`Cron scheduler started (pid=12345)`

### `oh cron stop`

停止 Cron 调度器守护进程。

```bash
oh cron stop
```

### `oh cron status`

显示调度器状态和任务摘要。

```bash
oh cron status
```

输出示例：

```
Scheduler: running (pid=12345)
Jobs:      3 enabled / 5 total
Log:       /Users/user/.openharness/logs/cron_scheduler.log
```

### `oh cron list`

列出所有已注册的 Cron 任务及其调度和状态。

```bash
oh cron list
```

输出示例：

```
  [on ] daily-build  0 2 * * *
        cmd: oh -p 'run the build'
        last: 2026-04-10T02:00:00  next: 2026-04-11T02:00:00
  [off] weekly-report  0 9 * * 1
        cmd: oh -p 'generate report'
        last: never  next: n/a
```

### `oh cron toggle <name> <enabled>`

启用或禁用指定 Cron 任务。

```bash
oh cron toggle daily-build true
oh cron toggle weekly-report false
```

### `oh cron history [--limit N] [name]`

显示 Cron 执行历史。

```bash
oh cron history                        # 显示最近 20 条
oh cron history --limit 50            # 显示最近 50 条
oh cron history daily-build            # 仅显示指定任务的历史
```

### `oh cron logs [--lines N]`

显示最近的调度器日志输出。

```bash
oh cron logs
oh cron logs --lines 100
```

> 证据来源：`src/openharness/cli.py` -> `@cron_app` 下的所有子命令（`cron_start`、`cron_stop`、`cron_status_cmd`、`cron_list_cmd`、`cron_toggle_cmd`、`cron_history_cmd`、`cron_logs_cmd`）

---

## 子命令：`oh setup`

统一设置向导：选择工作流、认证（如需要）、设置模型。

### `oh setup [profile]`

```bash
oh setup                      # 交互式选择工作流
oh setup claude-api           # 直接配置 claude-api
oh setup openai-compatible    # 直接配置 openai-compatible
```

`oh setup` 提供以下子流程：

- **claude-api**：可进一步选择 Claude 官方、Kimi (Anthropic 兼容)、GLM (Anthropic 兼容)、MiniMax (Anthropic 兼容)
- **openai-compatible**：可进一步选择 OpenAI 官方、OpenRouter

每个分支引导用户输入 Base URL、模型等配置。

> 证据来源：`src/openharness/cli.py` -> `@app.command("setup")` 和 `_specialize_setup_target()` 函数

---

## 配置覆盖方式

CLI 参数可覆盖配置文件中的设置。优先级顺序为：

```
CLI 参数 > 环境变量 > 配置文件（~/.openharness/settings.json）> 默认值
```

### 常用覆盖示例

```bash
# 覆盖模型
oh -m opus "解释这段代码"
oh --model sonnet[1m] "分析这个文件"

# 打印模式（单次查询）
oh -p "用 Python 实现快速排序"
oh -p "explain this code" --output-format json

# 继续会话
oh -c
oh --continue

# 恢复指定会话
oh -r <session_id>
oh --resume ""   # 打开会话选择器

# 权限模式
oh --permission-mode plan "规划这个功能的实现"
oh --permission-mode full_auto --dangerously-skip-permissions

# 系统提示词
oh -s "你是一个代码审查助手" "审查这个 PR"
oh --append-system-prompt "额外上下文"

# Base URL 和 API 格式
oh --base-url https://api.example.com/v1 --api-format openai

# 调试模式
oh -d -p "run tests"

# 主题
oh --theme dark
```

### 环境变量

| 环境变量 | 对应参数 | 说明 |
|----------|----------|------|
| `ANTHROPIC_API_KEY` | `--api-key` | Anthropic API 密钥 |
| `OPENAI_API_KEY` | `--api-key` | OpenAI API 密钥 |
| `ANTHROPIC_MODEL` / `OPENHARNESS_MODEL` | `--model` | 默认模型 |
| `ANTHROPIC_BASE_URL` / `OPENHARNESS_BASE_URL` | `--base-url` | API Base URL |
| `OPENHARNESS_MAX_TOKENS` | `--max-turns` | 最大输出 Token 数 |
| `OPENHARNESS_TIMEOUT` | - | 请求超时时间（秒） |
| `OPENHARNESS_MAX_TURNS` | `--max-turns` | 最大 Agent 轮次 |
| `OPENHARNESS_API_FORMAT` | `--api-format` | API 格式 |
| `OPENHARNESS_PROVIDER` | - | Provider 名称 |
| `OPENHARNESS_SANDBOX_ENABLED` | - | 启用沙箱 |
| `OPENHARNESS_SANDBOX_BACKEND` | - | 沙箱后端（`srt` 或 `docker`） |
| `OPENHARNESS_SANDBOX_DOCKER_IMAGE` | - | Docker 沙箱镜像 |

> 证据来源：`src/openharness/cli.py` -> `_version_callback()` 和 `main()` 函数；`src/openharness/config/settings.py` -> `_apply_env_overrides()`

---

## 配置文件

默认配置文件位于 `~/.openharness/settings.json`。也可以通过 `--settings` 参数指定自定义路径：

```bash
oh --settings /path/to/custom-settings.json
oh --settings '{"model":"opus","theme":"dark"}'  # 内联 JSON
```

配置文件的详细结构参见 [配置参考](./config.md)。

---

## 证据索引

1. `src/openharness/cli.py` -> `main()` 函数全局参数定义（`--continue`、`--resume`、`--model`、`--print` 等）
2. `src/openharness/cli.py` -> `@mcp_app` 子命令（`mcp_list`、`mcp_add`、`mcp_remove`）
3. `src/openharness/cli.py` -> `@plugin_app` 子命令（`plugin_list`、`plugin_install`、`plugin_uninstall`）
4. `src/openharness/cli.py` -> `@auth_app` 子命令（`auth_login`、`auth_status_cmd`、`auth_logout`、`auth_switch`）
5. `src/openharness/cli.py` -> `auth_copilot_login`、`auth_codex_login`、`auth_claude_login`、`auth_copilot_logout`
6. `src/openharness/cli.py` -> `@provider_app` 子命令（`provider_list`、`provider_use`、`provider_add`、`provider_edit`、`provider_remove`）
7. `src/openharness/cli.py` -> `@cron_app` 子命令（`cron_start`、`cron_stop`、`cron_status_cmd`、`cron_list_cmd`、`cron_toggle_cmd`、`cron_history_cmd`、`cron_logs_cmd`）
8. `src/openharness/cli.py` -> `@app.command("setup")` 和 `_specialize_setup_target()`
9. `src/openharness/cli.py` -> `_PROVIDER_LABELS` 和 `_AUTH_SOURCE_LABELS` 映射表
10. `src/openharness/cli.py` -> `main()` 中的 `print_mode` 处理和 `run_print_mode()` 调用
11. `src/openharness/cli.py` -> `main()` 中的 `continue_session` / `resume` 处理和 `run_repl()` 调用
12. `src/openharness/cli.py` -> `dangerously_skip_permissions` 到 `permission_mode = "full_auto"` 的转换逻辑
13. `src/openharness/cli.py` -> `__version__ = "0.1.6"` 版本号
14. `src/openharness/config/settings.py` -> `_apply_env_overrides()` 函数（环境变量覆盖逻辑）
15. `src/openharness/config/settings.py` -> `Settings` 模型中的 `merge_cli_overrides()` 方法
16. `src/openharness/config/settings.py` -> `Settings` 模型字段定义（`model`、`permission`、`sandbox`、`theme` 等）
17. `src/openharness/config/settings.py` -> `default_provider_profiles()` 内置 Provider 列表
18. `src/openharness/config/settings.py` -> `resolve_model_setting()` 模型别名解析逻辑
