# ohmo 个人代理

## 概述

ohmo 是基于 OpenHarness 的 personal-agent app，提供更深度的个性化体验。与标准的 `oh` 命令不同，ohmo 专注于个人助理场景，包括身份定义、记忆系统和多渠道接入。

## 核心概念

### 工作空间

ohmo 使用 `~/.ohmo/` 作为主工作空间：

```
~/.ohmo/
├── soul.md           # 灵魂/人格定义
├── identity.md       # 身份定义
├── user.md           # 用户画像
├── BOOTSTRAP.md      # 首次启动引导
├── gateway.json      # Gateway 配置
├── memory/           # 个人记忆
└── state/            # 运行状态
```

### Gateway

Gateway 是 ohmo 的核心服务，负责：
- 接收来自各渠道的消息
- 管理 Agent 会话
- 协调记忆系统
- 处理多渠道路由

## 初始化

### 首次初始化

```bash
ohmo init
```

这会：
1. 创建 `~/.ohmo/` 目录结构
2. 生成 soul.md、identity.md、user.md 等模板
3. 启动配置向导

### 配置 Provider

```bash
ohmo config
```

选择 Provider workflow 和渠道配置。

### 检查状态

```bash
ohmo doctor
```

检查：
- 工作空间完整性
- Provider 认证状态
- Gateway 运行状态

## soul.md - 灵魂定义

soul.md 定义 ohmo 的人格特征和行为原则。

### 内容结构

```markdown
# Soul

你是一个温柔、有耐心的人工智能助手。

## 性格特点

- 善解人意，能感知用户情绪
- 回答问题清晰、有条理
- 诚实，不确定时会承认

## 行为准则

- 尊重用户隐私
- 不主动打扰
- 建议而非说教

## 专长领域

- 编程问题解答
- 技术文档撰写
- 项目规划和咨询
```

## identity.md - 身份定义

定义 ohmo 的身份信息。

### 内容结构

```markdown
# Identity

## 名字

我叫小 mo，是你的个人 AI 助手。

## 来历

我由 OpenHarness 提供支持，基于 Claude 模型构建。

## 能力

- 24/7 在线
- 多渠道接入
- 持续学习记忆
```

## user.md - 用户画像

记录用户信息，用于个性化服务。

### 内容结构

```markdown
# User Profile

## 基本信息

- 姓名：XXX
- 职业：软件工程师
- 地点：上海

## 偏好

- 喜欢简洁的技术方案
- 偏好 Python 开发
- 习惯使用命令行

## 关系

- 使用 ohmo 3 个月
- 主要用于编程辅助
```

## 运行模式

### 交互式模式

```bash
ohmo
```

启动 React TUI 界面进行对话。

### 单次任务模式

```bash
ohmo -p "帮我写一个快速排序算法"
```

### 后端模式

```bash
ohmo --backend-only
```

只启动后端服务，不启动 TUI。

## Gateway 管理

### 前台运行

```bash
ohmo gateway run
```

### 后台启动

```bash
ohmo gateway start
```

### 查看状态

```bash
ohmo gateway status
```

输出示例：
```json
{
  "running": true,
  "pid": 12345,
  "uptime": "2h 30m",
  "channels": ["telegram", "slack"]
}
```

### 重启

```bash
ohmo gateway restart
```

### 停止

```bash
ohmo gateway stop
```

## 记忆管理

### ohmo memory 命令

```bash
# 列出所有记忆
ohmo memory list

# 添加记忆
ohmo memory add "项目进度" "完成了用户认证模块"

# 删除记忆
ohmo memory remove project-progress
```

### 记忆类型

| 类型 | 说明 | 位置 |
|------|------|------|
| 项目记忆 | 特定项目的信息 | 随项目 |
| 个人记忆 | 关于用户的长期信息 | ~/.ohmo/memory/ |
| 会话记忆 | 当前会话的上下文 | 内存中 |

## 渠道集成

ohmo 支持多渠道接入（详见 [渠道配置](./channels-user.md)）：

- Telegram
- Slack
- Discord
- Feishu

配置后，可以随时随地通过这些渠道与 ohmo 对话。

## 与 oh 的区别

| 特性 | oh | ohmo |
|------|-----|------|
| 用途 | 通用 Agent | 个人助理 |
| 人格 | 固定 | 可自定义 |
| 记忆 | 项目级 | 个人级 + 项目级 |
| 渠道 | 无 | 多渠道 |
| 工作空间 | 无 | ~/.ohmo/ |

## 最佳实践

### 1. soul.md 定制

花时间精心设计 soul.md，这决定了 ohmo 的交互风格。

### 2. user.md 维护

定期更新 user.md，保持用户画像准确。

### 3. 记忆整理

定期使用 `ohmo memory list` 检查记忆，删除过时内容。

### 4. 渠道安全

配置渠道时使用 allow_from 限制，只允许你本人使用。

## 配置参考

### gateway.json 结构

```json
{
  "provider_profile": "claude-api",
  "enabled_channels": ["telegram"],
  "channel_configs": {
    "telegram": {
      "token": "xxx",
      "allow_from": ["your-user-id"]
    }
  },
  "send_progress": true,
  "send_tool_hints": false,
  "log_level": "INFO"
}
```

## 故障排除

### Gateway 启动失败

1. 检查 `ohmo doctor` 输出
2. 确认 Provider 已配置
3. 查看日志：`ohmo gateway run`

### 渠道无响应

1. 确认渠道已启用：`ohmo gateway status`
2. 检查 Bot Token/API Key
3. 尝试重启 Gateway

### 记忆丢失

记忆文件存储在 `~/.ohmo/memory/`，确认目录存在且有写入权限。
