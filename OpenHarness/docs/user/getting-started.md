# 快速入门指南

本指南将帮助你在 5 分钟内上手 OpenHarness。

## 前置要求

- Python 3.10 或更高版本
- `uv` 包管理器（推荐）或 `pip`

## 一、安装 OpenHarness

### 一键安装脚本

```bash
curl -fsSL https://raw.githubusercontent.com/HKUDS/OpenHarness/main/scripts/install.sh | bash
```

常用安装参数：
- `--from-source`：从源码安装，适合贡献者
- `--with-channels`：一并安装 IM channel 依赖

```bash
curl -fsSL https://raw.githubusercontent.com/HKUDS/OpenHarness/main/scripts/install.sh | bash -s -- --from-source --with-channels
```

### 从源码安装

```bash
git clone https://github.com/HKUDS/OpenHarness.git
cd OpenHarness
uv sync --extra dev
```

## 二、配置 Provider

OpenHarness 支持多种 AI Provider，包括 Anthropic、OpenAI、Codex、GitHub Copilot 等。

运行引导式配置：

```bash
oh setup
```

`oh setup` 会按以下顺序引导：
1. 选择一个 workflow（如 Claude API、OpenAI 兼容接口等）
2. 如果需要，完成认证
3. 选择具体后端 preset
4. 确认模型
5. 保存并激活 profile

### 内置 Workflow

| Workflow | 说明 |
|----------|------|
| `Anthropic-Compatible API` | Claude 官方 API、Moonshot Kimi、Zhipu GLM、MiniMax 等 |
| `Claude Subscription` | 复用本地 Claude CLI 凭据 |
| `OpenAI-Compatible API` | OpenAI 官方 API、OpenRouter、DashScope、DeepSeek 等 |
| `Codex Subscription` | 复用本地 Codex CLI 凭据 |
| `GitHub Copilot` | GitHub Copilot OAuth 认证 |

## 三、运行 Agent

### 交互模式（TUI）

```bash
oh
```

启动后你会得到 React/Ink TUI，支持：
- `/` 命令选择器
- 交互式权限确认
- `/model` 模型切换
- `/permissions` 权限模式切换
- `/resume` 会话恢复
- `/provider` workflow 选择

### 非交互模式

```bash
# 直接执行单个任务
oh -p "Explain this repository"

# JSON 输出
oh -p "List all functions in main.py" --output-format json

# 流式 JSON 输出（实时查看工具调用）
oh -p "Fix the bug" --output-format stream-json
```

## 四、常用命令一览

```bash
# 统一配置入口
oh setup

# 查看已有 workflow/profile
oh provider list

# 切换当前 workflow
oh provider use codex

# 查看认证状态
oh auth status

# 启动交互式会话
oh
```

## 五、使用 ohmo 个人代理

`ohmo` 是基于 OpenHarness 的 personal-agent app，提供更深度的个性化体验。

### 初始化

```bash
ohmo init
```

这会创建：
- `~/.ohmo/soul.md` - 长期人格与行为原则
- `~/.ohmo/identity.md` - ohmo 身份定义
- `~/.ohmo/user.md` - 用户画像和偏好
- `~/.ohmo/BOOTSTRAP.md` - 首次 onboarding 流程
- `~/.ohmo/memory/` - 个人记忆存储
- `~/.ohmo/gateway.json` - Gateway 配置

### 配置 ohmo

```bash
ohmo config
```

### 运行 ohmo

```bash
# 运行 personal agent
ohmo

# 前台运行 gateway
ohmo gateway run

# 查看 gateway 状态
ohmo gateway status
```

## 六、下一步

- 阅读 [安装配置](./installation.md) 了解详细安装选项
- 阅读 [CLI 命令参考](./cli-reference.md) 掌握所有命令
- 阅读 [技能使用指南](./skills-user.md) 学习如何使用和创建技能
- 阅读 [插件使用指南](./plugins-user.md) 扩展 OpenHarness 功能
