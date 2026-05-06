# CLI 命令参考

OpenHarness CLI 使用 `oh` 和 `ohmo` 两个主命令。

## oh 主命令

### 基础用法

```bash
oh [OPTIONS]
oh -p "任务描述" [OPTIONS]
```

### 全局选项

| 选项 | 说明 |
|------|------|
| `-p, --print TEXT` | 非交互模式，直接执行任务 |
| `--output-format FORMAT` | 输出格式：text、json、stream-json |
| `--model MODEL` | 指定模型 |
| `--permission-mode MODE` | 权限模式：default、plan、full_auto |
| `--no-color` | 禁用颜色输出 |
| `--version` | 显示版本 |

### 子命令

#### oh setup

引导式配置 workflow 和认证。

```bash
oh setup [PROFILE]
```

#### oh provider

管理 provider profiles。

```bash
oh provider list              # 列出所有 profile
oh provider use <name>        # 激活指定 profile
oh provider add <name> [OPTIONS]  # 添加自定义 profile
```

示例 - 添加自定义兼容接口：

```bash
oh provider add my-endpoint \
  --label "My Endpoint" \
  --provider anthropic \
  --api-format anthropic \
  --auth-source anthropic_api_key \
  --model my-model \
  --base-url https://example.com/anthropic
```

#### oh auth

管理认证。

```bash
oh auth status               # 查看认证状态
oh auth login [PROVIDER]     # 交互式登录
oh auth logout [PROVIDER]    # 清除认证
oh auth switch <source>      # 切换认证源
oh auth copilot-login        # GitHub Copilot OAuth 登录
oh auth codex-login          # 绑定 Codex CLI 订阅
oh auth claude-login         # 绑定 Claude CLI 订阅
```

支持的 provider：
- `anthropic` - Anthropic API key
- `openai` - OpenAI API key
- `copilot` - GitHub Copilot OAuth
- `openai_codex` - OpenAI Codex 订阅
- `anthropic_claude` - Claude 订阅
- `dashscope` - 阿里 DashScope
- `bedrock` - AWS Bedrock
- `vertex` - Google Vertex AI
- `moonshot` - Moonshot (Kimi)

#### oh mcp

管理 MCP (Model Context Protocol) 服务器。

```bash
oh mcp list                  # 列出已配置的 MCP 服务器
oh mcp add <name> <config>   # 添加 MCP 服务器（JSON 配置）
oh mcp remove <name>         # 移除 MCP 服务器
```

示例 - 添加 MCP 服务器：

```bash
oh mcp add my-server '{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/tmp"]}'
```

#### oh plugin

管理插件。

```bash
oh plugin list                # 列出已安装插件
oh plugin install <source>   # 从路径安装插件
oh plugin uninstall <name>   # 卸载插件
```

#### oh cron

管理定时任务调度器。

```bash
oh cron start                # 启动调度器守护进程
oh cron stop                 # 停止调度器
oh cron status               # 显示状态和任务摘要
oh cron list                 # 列出所有定时任务
oh cron toggle <name> <bool> # 启用/禁用任务
oh cron history [OPTIONS]    # 显示执行历史
oh cron logs [OPTIONS]      # 显示调度器日志
```

## ohmo 命令

`ohmo` 是 personal-agent app，提供个性化代理体验。

### 基础命令

```bash
ohmo init                    # 初始化 ohmo 工作区
ohmo config                  # 配置 gateway 和 channel
ohmo                          # 运行 personal agent
```

### gateway 子命令

```bash
ohmo gateway run             # 前台运行 gateway
ohmo gateway status          # 查看 gateway 状态
ohmo gateway restart         # 重启 gateway
```

## 权限模式

| 模式 | 说明 |
|------|------|
| `default` | 默认模式，修改操作需用户确认 |
| `plan` | 计划模式，只读操作可用 |
| `full_auto` | 全自动模式，所有操作直接执行 |

## 输出格式

| 格式 | 说明 |
|------|------|
| `text` | 纯文本输出（默认） |
| `json` | 完整 JSON 响应 |
| `stream-json` | SSE 流式 JSON，可实时查看工具调用 |

## 环境变量

| 变量 | 说明 |
|------|------|
| `OPENHARNESS_CONFIG_DIR` | 覆盖配置目录 |
| `OPENHARNESS_MODEL` | 默认模型 |
| `OPENHARNESS_API_KEY` | API 密钥 |

## 配置文件

主配置文件位于 `~/.config/openharness/settings.json`（Linux/macOS）。

主要配置项：

```json
{
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "permission_mode": "default",
  "mcp_servers": {},
  "allowed_tools": [],
  "denied_tools": [],
  "path_rules": []
}
```
