# 消息渠道配置

## 概述

OpenHarness 的 Channels 系统支持将多种即时通讯平台接入 Agent，实现通过 IM 工具与 Agent 对话。

## 支持的渠道

| 渠道 | 说明 | 状态 |
|------|------|------|
| Telegram | Bot API | 稳定 |
| Slack | Slack App | 稳定 |
| Discord | Discord Bot | 稳定 |
| Feishu | 飞书 | 稳定 |
| DingTalk | 钉钉 | 实验 |
| QQ | QQ 机器人 | 实验 |
| Email | 邮件 | 实验 |
| WhatsApp | WhatsApp | 实验 |
| Matrix | Matrix 协议 | 实验 |
| Mochat | Mochat | 实验 |

## 架构说明

Channels 系统采用消息总线架构：

```
IM 平台 → Channel Adapter → Message Bus → OpenHarness Engine
                                    ↓
                              Response ← Channel Adapter ← IM 平台
```

## 配置渠道

### 通过 ohmo config

```bash
ohmo config
```

这会启动引导式配置，依次配置：
1. Provider profile
2. Channel 类型
3. 各渠道的具体参数

### 渠道配置存储

渠道配置存储在 `~/.ohmo/gateway.json`：

```json
{
  "provider_profile": "claude-api",
  "enabled_channels": ["telegram", "slack"],
  "channel_configs": {
    "telegram": {
      "token": "your-bot-token",
      "allow_from": ["*"],
      "reply_to_message": true
    },
    "slack": {
      "bot_token": "xoxb-...",
      "app_token": "xapp-...",
      "mode": "socket",
      "allow_from": ["*"],
      "reply_in_thread": true,
      "group_policy": "mention"
    }
  }
}
```

## Telegram 配置

### 步骤 1: 创建 Bot

1. 在 Telegram 中搜索 @BotFather
2. 发送 `/newbot` 创建新 Bot
3. 复制获得的 Bot Token

### 步骤 2: 配置

```bash
ohmo config
# 选择 telegram
# 输入 Bot Token
```

### 配置选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| token | Bot Token | 必需 |
| allow_from | 允许的用户 ID（`*` 表示所有人） | `*` |
| reply_to_message | 回复原消息 | true |

## Slack 配置

### 步骤 1: 创建 Slack App

1. 访问 https://api.slack.com/apps
2. 点击 "Create New App" → "From scratch"
3. 配置 Bot Token Scopes

### 步骤 2: 启用 Socket Mode

1. 在 App Settings 中启用 Socket Mode
2. 生成 App-Level Token

### 步骤 3: 配置

```bash
ohmo config
# 选择 slack
# 输入 Bot Token (xoxb-...)
# 输入 App Token (xapp-...)
```

### 配置选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| bot_token | Bot Token (xoxb-) | 必需 |
| app_token | App Token (xapp-) | 必需 |
| mode | 连接模式 | socket |
| reply_in_thread | 在线程中回复 | true |
| group_policy | 群组策略 | mention |

### group_policy 选项

- `mention` - 仅在 @mention 时响应
- `open` - 始终在频道中回复
- `allowlist` - 只在配置的频道中响应

## Discord 配置

### 步骤 1: 创建 Discord Application

1. 访问 https://discord.com/developers/applications
2. 创建新 Application
3. 在 Bot 设置中获取 Token

### 步骤 2: 配置 Intents

需要启用以下 Intents：
- MESSAGE CONTENT INTENT
- GUILD MESSAGES INTENT

### 步骤 3: 配置

```bash
ohmo config
# 选择 discord
# 输入 Bot Token
# 配置 Gateway URL
# 配置 Intents Bitmask
```

### 配置选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| token | Bot Token | 必需 |
| gateway_url | Discord Gateway URL | wss://gateway.discord.gg |
| intents | Intents Bitmask | 513 |
| group_policy | 群组策略 | mention |

## Feishu（飞书）配置

### 步骤 1: 创建飞书应用

1. 访问 飞书开放平台
2. 创建企业自建应用
3. 获取 App ID 和 App Secret

### 步骤 2: 配置

```bash
ohmo config
# 选择 feishu
# 输入 App ID
# 输入 App Secret
# 配置 Encrypt Key（可选）
# 配置 Verification Token（可选）
```

### 配置选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| app_id | 飞书 App ID | 必需 |
| app_secret | 飞书 App Secret | 必需 |
| encrypt_key | 加密密钥（可选） | 空 |
| verification_token | 验证 Token（可选） | 空 |
| react_emoji | 反应 Emoji | OK |

## 运行 Gateway

### 前台运行

```bash
ohmo gateway run
```

### 后台运行

```bash
ohmo gateway start
```

### 查看状态

```bash
ohmo gateway status
```

### 重启

```bash
ohmo gateway restart
```

### 停止

```bash
ohmo gateway stop
```

## 渠道使用

配置完成后，直接在对应的 IM 平台发送消息即可：

- **Telegram**: 给 Bot 发私信
- **Slack**: 在授权的频道 @mention Bot
- **Discord**: 在授权的服务器 @mention Bot
- **Feishu**: 给机器人的单聊或群聊发消息

## 安全考虑

### allow_from 限制

建议配置 `allow_from` 限制允许的用户：

```json
{
  "telegram": {
    "allow_from": ["123456789", "987654321"]
  }
}
```

### 群组策略

在群组中使用时，选择适当的 group_policy：
- `mention` - 最安全，只响应 @mention
- `allowlist` - 只在白名单频道响应

## 调试

### 查看 Gateway 日志

```bash
ohmo gateway run  # 前台运行查看日志
```

### 测试渠道连接

```bash
ohmo doctor
```

这会检查：
- Gateway 配置
- Provider 认证状态
- 各渠道连接状态

## 常见问题

### Q: Bot 没有响应？

1. 检查 Gateway 是否运行：`ohmo gateway status`
2. 确认 Bot Token 正确
3. 检查 allow_from 设置
4. 查看 Gateway 日志

### Q: 收到 "Unauthorized" 错误？

- Telegram: 检查 Bot Token
- Slack: 确认 Bot 已添加到 Workspace
- Discord: 检查 Intents 配置

### Q: 消息延迟？

1. 检查网络连接
2. 确认 Provider API 响应速度
3. 考虑添加超时配置
