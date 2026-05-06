# ohmo Channels

ohmo 通过 OpenHarness 的 Channels 系统接入多个 IM 平台，所有渠道共享相同的 MessageBus 架构。

## 架构关系

```
ohmo gateway
    │
    ├─► OhmoGatewayBridge
    │         │
    │         ▼
    │    MessageBus (openharness/channels/bus/queue.py)
    │         │
    │         ▼
    │    ChannelManager (openharness/channels/impl/manager.py)
    │         │
    │         ├──► TelegramChannel
    │         ├──► SlackChannel
    │         ├──► DiscordChannel
    │         ├──► FeishuChannel
    │         ├──► WhatsAppChannel
    │         ├──► DingTalkChannel
    │         ├──► EmailChannel
    │         ├──► MatrixChannel
    │         ├──► QQChannel
    │         └──► MochatChannel
```

## Gateway 渠道配置

源码：`ohmo/workspace.py` 的 `initialize_workspace()`

默认 `gateway.json` 结构：

```json
{
    "provider_profile": "codex",
    "enabled_channels": [],
    "session_routing": "chat-thread",
    "send_progress": true,
    "send_tool_hints": true,
    "permission_mode": "default",
    "sandbox_enabled": false,
    "log_level": "INFO",
    "channel_configs": {}
}
```

启用渠道示例：

```json
{
    "enabled_channels": ["telegram", "slack"],
    "channel_configs": {
        "telegram": {
            "api_token": "123456:ABC-DEF...",
            "allow_from": ["*"]
        },
        "slack": {
            "bot_token": "xoxb-...",
            "allow_from": ["*"]
        }
    }
}
```

## Bootstrap 流程

ohmo workspace 首次初始化时，会创建 `BOOTSTRAP.md`：

```markdown
# BOOTSTRAP.md - First Contact

You just came online in a fresh personal workspace.
Your job is not to interrogate the user. Start naturally...
```

Gateway 启动后，ohmo 会：
1. 检查 `BOOTSTRAP.md` 是否存在
2. 将其作为 system prompt 的一部分注入
3. 完成后可删除或保留

## Identity 配置

`identity.md` 定义 ohmo 的身份：

```markdown
# IDENTITY.md - Your Shape

- Name: ohmo
- Kind: personal agent
- Vibe: calm, capable, warm when useful
- Signature: 
```

## 渠道与 Memory

渠道消息的附件（图片、文件）下载到：

```
~/.ohmo/attachments/{channel_name}/
```

Memory 系统（`ohmo/memory.py`）从 `memory/` 目录加载持久化记忆：

```
~/.ohmo/memory/
├── MEMORY.md        # 记忆索引
└── *.md             # 各记忆条目
```

## 会话与 Identity 绑定

当用户通过渠道首次与 ohmo 对话时：

1. **Identity 确认**：ohmo 读取 `identity.md` 了解自己的身份
2. **User 学习**：通过对话和 `user.md` 了解用户
3. **记忆积累**：重要信息写入 `memory/` 目录

## 渠道安全

所有渠道通过 `BaseChannel.is_allowed()` 实现访问控制：

```python
def is_allowed(self, sender_id: str) -> bool:
    allow_list = getattr(self.config, "allow_from", [])
    if not allow_list:
        return False  # 空列表 = 拒绝所有
    return "*" in allow_list or sender_id in allow_list
```

配置示例（只允许特定用户）：

```json
{
    "telegram": {
        "allow_from": ["123456789", "987654321"]
    }
}
```

## 进度消息发送

根据 `gateway.json` 的配置，Gateway 会向渠道发送进度消息：

```python
# gateway.json
send_progress: true      # 发送 "Thinking..." 等进度
send_tool_hints: true    # 发送 "Using tool_name" 提示
```

进度消息格式示例（中文 Telegram）：

```
🤔 想一想…
🛠️ 正在使用 web_search: query="..."
🫧 正在读取文件...
```

## 扩展指南

### 自定义渠道配置

在 `gateway.json` 的 `channel_configs` 中添加渠道特定配置：

```json
{
    "channel_configs": {
        "mychannel": {
            "api_key": "...",
            "allow_from": ["*"],
            "custom_option": "value"
        }
    }
}
```

### 添加新渠道到 ohmo

1. 在 `openharness/channels/impl/` 实现 `BaseChannel` 子类
2. 在 `openharness/channels/impl/manager.py` 的 `_init_channels()` 中注册
3. 在 `openharness/config/schema.py` 中添加渠道配置模型
4. 在 `ohmo/workspace.py` 的 `initialize_workspace()` 中添加默认配置
5. 在 `gateway.json` 的 `enabled_channels` 列表中添加渠道名

### 渠道消息预处理

在 `ohmo/gateway/runtime.py` 的 `_build_inbound_user_message()` 中添加预处理逻辑：

```python
def _build_inbound_user_message(message: InboundMessage) -> ConversationMessage:
    # 添加自定义预处理
    content = preprocess_channel_content(message.content, message.channel)
    # ...
```

## 渠道支持矩阵

| 渠道 | 状态 | 特点 |
|------|------|------|
| Telegram | 稳定 | 支持 Groq API 中继 |
| Slack | 稳定 | 企业级支持 |
| Discord | 稳定 | 支持 Thread |
| Feishu | 稳定 | 飞书平台 |
| WhatsApp | 稳定 | Meta 生态 |
| DingTalk | 稳定 | 钉钉平台 |
| Email | 稳定 | SMTP/POP3 |
| Matrix | 稳定 | 去中心化协议 |
| QQ | 稳定 | 腾讯 QQ |
| Mochat | 稳定 | 企业微信 |

## 故障排查

### 渠道无法启动

1. 检查 `gateway.json` 中 `enabled_channels` 是否包含该渠道
2. 检查 `channel_configs` 中的 token/key 是否正确
3. 查看 `gateway.log` 中的错误信息

### 消息无响应

1. 确认 `allow_from` 配置正确
2. 检查 `OHMO_WORKSPACE` 环境变量指向的 workspace
3. 查看 `sessions/` 中的会话快照是否损坏

### Token 过期

OAuth 渠道（Slack、Discord）需要定期刷新 token：
- 每次 Gateway 启动时自动刷新
- 或手动重新授权
