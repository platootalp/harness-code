# 消息渠道

本文档介绍 OpenHarness 的消息渠道架构，支持 Telegram、Slack、Discord、Feishu 等 IM 平台。

## 架构概览

```
src/openharness/channels/
├── adapter.py          # ChannelManager — 渠道协调器
├── bus/
│   ├── events.py       # InboundMessage / OutboundMessage
│   └── queue.py        # MessageBus — 异步队列
└── impl/
    ├── base.py         # BaseChannel — 抽象基类
    ├── manager.py      # ChannelManager（主逻辑）
    └── impl/
        ├── telegram.py
        ├── discord.py
        ├── slack.py
        ├── feishu.py
        ├── whatsapp.py
        ├── dingtalk.py
        ├── email.py
        ├── matrix.py
        ├── qq.py
        └── mochat.py
```

## MessageBus

`queue.py` 中的 `MessageBus` 是核心解耦机制，采用异步队列：

```python
class MessageBus:
    def __init__(self):
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()

    async def publish_inbound(self, msg: InboundMessage) -> None:
    async def consume_inbound(self) -> InboundMessage -> InboundMessage:
    async def publish_outbound(self, msg: OutboundMessage) -> None:
    async def consume_outbound(self) -> OutboundMessage:
```

## 消息类型

`events.py` 定义了两种核心消息类型：

### InboundMessage

```python
@dataclass
class InboundMessage:
    channel: str         # "telegram", "discord", "slack" 等
    sender_id: str       # 用户标识
    chat_id: str         # 聊天/频道标识
    content: str         # 消息文本
    timestamp: datetime
    media: list[str]     # 媒体 URL 列表
    metadata: dict[str, Any]
    session_key_override: str | None

    @property
    def session_key(self) -> str:
        """Unique key for session identification."""
        return self.session_key_override or f"{self.channel}:{self.chat_id}"
```

### OutboundMessage

```python
@dataclass
class OutboundMessage:
    channel: str
    chat_id: str
    content: str
    reply_to: str | None = None
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
```

## BaseChannel

`impl/base.py` 中的 `BaseChannel` 是所有渠道实现的抽象基类：

```python
class BaseChannel(ABC):
    name: str = "base"

    def __init__(self, config: Any, bus: MessageBus):
        self.config = config
        self.bus = bus
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """Start the channel and begin listening for messages."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel and clean up resources."""

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through this channel."""

    def is_allowed(self, sender_id: str) -> bool:
        """Check if sender is permitted via allow_from list."""
        allow_list = getattr(self.config, "allow_from", [])
        if not allow_list:
            return False  # 空列表拒绝所有
        return "*" in allow_list or sender_str in allow_list

    async def _handle_message(self, sender_id: str, chat_id: str, content: str, ...) -> None:
        """Check permissions and publish to bus."""
        if not self.is_allowed(sender_id):
            return  # 拒绝未授权用户
        msg = InboundMessage(...)
        await self.bus.publish_inbound(msg)
```

### 媒体目录解析

```python
def resolve_channel_media_dir(channel_name: str) -> Path:
    """Return the local download directory for inbound channel media."""
    # 优先级：OPENHARNESS_CHANNEL_MEDIA_DIR > OHMO_WORKSPACE > ~/.openharness/data/media
```

## ChannelManager

`impl/manager.py` 中的 `ChannelManager` 协调所有渠道：

```python
class ChannelManager:
    def __init__(self, config: Config, bus: MessageBus):
        self.config = config
        self.bus = bus
        self.channels: dict[str, BaseChannel] = {}
```

### 支持的渠道

| 渠道 | 模块 | 备注 |
|------|------|------|
| Telegram | `telegram.py` | 支持 Groq API 中继 |
| WhatsApp | `whatsapp.py` | |
| Discord | `discord.py` | |
| Feishu | `feishu.py` | 飞书 |
| Mochat | `mochat.py` | |
| DingTalk | `dingtalk.py` | 钉钉 |
| Email | `email.py` | |
| Slack | `slack.py` | |
| QQ | `qq.py` | |
| Matrix | `matrix.py` | |

### 生命周期

```python
async def start_all(self) -> None:
    # 1. 启动出站分发器
    # 2. 并行启动所有渠道
    tasks = [self._start_channel(name, channel) for name, channel in self.channels.items()]
    await asyncio.gather(*tasks, return_exceptions=True)

async def stop_all(self) -> None:
    # 1. 取消分发器
    # 2. 停止所有渠道
```

### 出站分发

```python
async def _dispatch_outbound(self) -> None:
    """Dispatch outbound messages to the appropriate channel."""
    while True:
        msg = await asyncio.wait_for(self.bus.consume_outbound(), timeout=1.0)
        channel = self.channels.get(msg.channel)
        if channel:
            await channel.send(msg)
```

### allow_from 验证

启动时检查每个渠道的 `allow_from` 配置。若为空列表则拒绝所有访问，抛出错误。

## ChannelBridge

`ChannelBridge`（位于 `channels/impl/bridge.py`）将 MessageBus 连接到 QueryEngine：

```python
class ChannelBridge:
    """Bridges inbound channel messages to the QueryEngine and routes replies back."""

    async def _handle(self, msg: InboundMessage) -> None:
        reply_parts: list[str] = []
        async for event in self._engine.submit_message(msg.content):
            if isinstance(event, AssistantTextDelta):
                reply_parts.append(event.text)
        reply_text = "".join(reply_parts).strip()

        outbound = OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=reply_text,
        )
        await self._bus.publish_outbound(outbound)
```

## 会话路由

`session_key` 用于多会话管理：
- 默认：`{channel}:{chat_id}`（每个聊天一个会话）
- 支持 `session_key_override` 进行线程级会话路由

## 配置结构

每个渠道的配置通过 `Config` 模型管理，包含：
- `enabled`: 是否启用
- `allow_from`: 允许的用户 ID 列表（`*` 表示所有）
- 渠道特定的配置参数

## 扩展指南

### 添加新的渠道

1. 在 `impl/` 目录创建 `{channel}.py`
2. 继承 `BaseChannel` 实现 `start()`、`stop()`、`send()`
3. 在 `manager.py` 的 `_init_channels()` 中添加初始化逻辑
4. 在 `Config` 模型中添加渠道配置

### 渠道特定注意事项

- **Telegram**: 使用 `python-telegram-bot` 库
- **Discord**: 使用 `discord.py` 库
- **Slack**: 使用 `slack-sdk` 库
- **Feishu**: 使用飞书开放平台 API

## 关键文件

| 文件 | 职责 |
|------|------|
| `adapter.py` / `impl/manager.py` | 渠道生命周期管理 |
| `bus/queue.py` | 异步消息队列 |
| `bus/events.py` | 消息类型定义 |
| `impl/base.py` | 渠道抽象基类 |
| `impl/{channel}.py` | 各渠道实现 |
