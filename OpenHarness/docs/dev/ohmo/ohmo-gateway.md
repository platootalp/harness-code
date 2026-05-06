# Gateway Server

Gateway 是 ohmo 的消息网关服务，负责接收来自各渠道的消息、调度 Runtime 处理、返回响应。

## 架构概览

```
ohmo/gateway/
├── service.py   # OhmoGatewayService — 服务生命周期
├── runtime.py   # OhmoSessionRuntimePool — Session Runtime 池
├── bridge.py    # OhmoGatewayBridge — 消息桥接
├── router.py    # session_key 路由逻辑
├── config.py    # 配置加载/保存
└── models.py    # GatewayConfig / GatewayState
```

## OhmoGatewayService

源码：`ohmo/gateway/service.py`

核心服务类，管理 Gateway 的完整生命周期：

```python
class OhmoGatewayService:
    def __init__(self, cwd: str | Path | None = None, workspace: str | Path | None = None) -> None:
        # 1. 初始化 workspace
        root = initialize_workspace(self._workspace)
        
        # 2. 加载 Gateway 配置
        self._config = load_gateway_config(self._workspace)
        
        # 3. 创建 MessageBus（渠道 ↔ Gateway 通信）
        self._bus = MessageBus()
        
        # 4. 创建 Runtime Pool
        self._runtime_pool = OhmoSessionRuntimePool(
            cwd=self._cwd,
            workspace=self._workspace,
            provider_profile=self._config.provider_profile,
        )
        
        # 5. 创建 Bridge
        self._bridge = OhmoGatewayBridge(bus=self._bus, runtime_pool=self._runtime_pool)
        
        # 6. 创建 Channel Manager
        self._manager = ChannelManager(build_channel_manager_config(self._config), self._bus)
```

### 前台运行

```python
async def run_foreground(self) -> int:
    self.pid_file.write_text(str(os.getpid()))
    self.write_state(running=True)
    
    # 并行启动 Bridge 和 Channel Manager
    bridge_task = asyncio.create_task(self._bridge.run(), name="ohmo-gateway-bridge")
    manager_task = asyncio.create_task(self._manager.start_all(), name="ohmo-gateway-channels")
    
    # 等待 SIGTERM/SIGINT
    stop_event = asyncio.Event()
    loop.add_signal_handler(signal.SIGTERM, lambda: stop_event.set())
    
    await stop_event.wait()
    
    # 优雅关闭
    self._bridge.stop()
    bridge_task.cancel()
    manager_task.cancel()
    await self._manager.stop_all()
```

### 进程管理

```python
def start_gateway_process(cwd, workspace) -> int:
    """启动为后台子进程"""
    # 通过 Popen 启动新进程，stdout/stderr 重定向到日志文件

def stop_gateway_process(cwd, workspace) -> bool:
    """停止后台进程 — 发送 SIGTERM"""

def gateway_status(cwd, workspace) -> GatewayState:
    """查询 Gateway 运行状态"""
```

### 状态文件

```
~/.ohmo/
├── gateway.pid   # 运行中 PID
├── gateway.log   # 日志输出
└── state.json    # GatewayState JSON
```

## OhmoSessionRuntimePool

源码：`ohmo/gateway/runtime.py`

每个 chat_id/thread 维护一个独立的 `RuntimeBundle`：

```python
class OhmoSessionRuntimePool:
    def __init__(self, *, cwd, workspace, provider_profile, model=None, max_turns=None):
        self._bundles: dict[str, RuntimeBundle] = {}
        self._session_backend = OhmoSessionBackend(self._workspace)
    
    async def get_bundle(self, session_key: str, latest_user_prompt: str | None) -> RuntimeBundle:
        """获取或创建 session bundle"""
        if bundle := self._bundles.get(session_key):
            # 复用已有 bundle，更新 system prompt
            bundle.engine.set_system_prompt(...)
            return bundle
        
        # 从存储恢复或创建新 bundle
        snapshot = self._session_backend.load_latest_for_session_key(session_key)
        bundle = await build_runtime(...)
        await start_runtime(bundle)
        self._bundles[session_key] = bundle
        return bundle
```

### 流式消息处理

```python
async def stream_message(self, message: InboundMessage, session_key: str):
    """处理 inbound 消息并 yield 进度更新"""
    user_message = _build_inbound_user_message(message)
    bundle = await self.get_bundle(session_key, latest_user_prompt=user_prompt)
    
    # 先 yield thinking 提示
    yield GatewayStreamUpdate(kind="progress", text="Thinking...")
    
    # 转发到引擎，yield 状态/工具/错误事件
    async for event in bundle.engine.submit_message(user_message):
        if isinstance(event, AssistantTextDelta):
            reply_parts.append(event.text)
        elif isinstance(event, StatusEvent):
            yield GatewayStreamUpdate(kind="progress", text=event.message)
        elif isinstance(event, ToolExecutionStarted):
            yield GatewayStreamUpdate(kind="tool_hint", text=f"Using {event.tool_name}")
        elif isinstance(event, ErrorEvent):
            yield GatewayStreamUpdate(kind="error", text=event.message)
    
    # 保存会话快照
    self._session_backend.save_snapshot(...)
    
    # yield 最终回复
    yield GatewayStreamUpdate(kind="final", text=reply)
```

### 渠道进度格式化

根据渠道类型和内容语言，生成适合的进度提示：

```python
# 中文渠道
_CHANNEL_THINKING_PHRASES = (
    "🤔 想一想…", "🧠 琢磨中…", "✨ 整理一下思路…",
)

# 英文渠道
_CHANNEL_THINKING_PHRASES_EN = (
    "🤔 Thinking…", "🧠 Working through it…", 
    "✨ Pulling the pieces together…",
)

# 检测内容语言（CJK vs Latin）
def _prefers_chinese_progress(content: str) -> bool:
    # 统计 CJK 字符和 Latin 字符比例
```

## OhmoGatewayBridge

源码：`ohmo/gateway/bridge.py`

桥接 MessageBus 和 RuntimePool：

```python
class OhmoGatewayBridge:
    async def run(self) -> None:
        """消费 inbound，发布 outbound"""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._bus.consume_inbound(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            
            session_key = session_key_for_message(message)
            
            try:
                async for update in self._runtime_pool.stream_message(message, session_key):
                    if update.kind == "final":
                        reply = update.text
                        continue
                    # 发布进度/错误等到 outbound
                    await self._bus.publish_outbound(OutboundMessage(...))
            except Exception as exc:
                reply = _format_gateway_error(exc)
            
            if reply:
                await self._bus.publish_outbound(OutboundMessage(
                    channel=message.channel,
                    chat_id=message.chat_id,
                    content=reply,
                ))
```

## Session 路由

源码：`ohmo/gateway/router.py`

```python
def session_key_for_message(message: InboundMessage) -> str:
    """确定消息所属的 session_key"""
    # 1. 优先使用 override
    if message.session_key_override:
        return message.session_key_override
    
    # 2. 从 metadata 提取 thread_id
    thread_id = (
        message.metadata.get("thread_id")
        or message.metadata.get("thread_ts")
        or message.metadata.get("message_thread_id")
    )
    
    # 3. 有 thread_id → 线程级会话
    if thread_id:
        return f"{message.channel}:{message.chat_id}:{thread_id}"
    
    # 4. 否则 → 聊天级会话
    return f"{message.channel}:{message.chat_id}"
```

路由模式由 `gateway.json` 的 `session_routing` 控制：
- `"chat-thread"`：优先线程级，否则聊天级
- 其他模式可通过修改 `router.py` 扩展

## GatewayConfig

源码：`ohmo/gateway/models.py`

```python
class GatewayConfig(BaseModel):
    provider_profile: str = "codex"       # 使用的 Provider Profile
    enabled_channels: list[str] = []      # 启用的渠道列表
    session_routing: str = "chat-thread"  # 会话路由模式
    send_progress: bool = True           # 发送进度提示
    send_tool_hints: bool = True         # 发送工具提示
    permission_mode: str = "default"       # 权限模式
    sandbox_enabled: bool = False
    log_level: str = "INFO"
    channel_configs: dict[str, dict] = {}  # 各渠道特定配置
```

## 配置加载

源码：`ohmo/gateway/config.py`

```python
def load_gateway_config(workspace) -> GatewayConfig:
    """从 ~/.ohmo/gateway.json 加载"""

def build_channel_manager_config(config: GatewayConfig) -> Config:
    """将 GatewayConfig 转换为 ChannelManager 所需的 Config"""
    root = Config()
    root.channels.send_progress = config.send_progress
    root.channels.send_tool_hints = config.send_tool_hints
    for name in config.enabled_channels:
        channel_config = getattr(root.channels, name).model_copy(
            update={"enabled": True, **config.channel_configs.get(name, {})}
        )
        setattr(root.channels, name, channel_config)
    return root
```

## 启动流程

```
ohmo gateway run
    │
    ├─► OhmoGatewayService.__init__()
    │       ├─► initialize_workspace()
    │       ├─► load_gateway_config()
    │       ├─► MessageBus()
    │       ├─► OhmoSessionRuntimePool()
    │       ├─► OhmoGatewayBridge()
    │       └─► ChannelManager(build_channel_manager_config())
    │
    └─► OhmoGatewayService.run_foreground()
            ├─► 写入 pid_file, state_file
            ├─► bridge_task = asyncio.create_task(bridge.run())
            ├─► manager_task = asyncio.create_task(manager.start_all())
            └─► 等待信号 → 优雅关闭
```

## 扩展指南

### 添加新路由策略

在 `router.py` 中修改 `session_key_for_message()`：

```python
def session_key_for_message(message: InboundMessage) -> str:
    # 添加新的路由逻辑
    if message.metadata.get("group_id"):
        return f"group:{message.metadata['group_id']}"
    return f"{message.channel}:{message.chat_id}"
```

### 添加进度事件类型

在 `runtime.py` 的 `GatewayStreamUpdate` 和 `_format_channel_progress()` 中添加新的 `kind` 值。

### 修改渠道配置格式

在 `gateway/models.py` 的 `GatewayConfig` 中添加新字段，并在 `config.py` 的 `build_channel_manager_config()` 中处理。

## 关键文件

| 文件 | 职责 |
|------|------|
| `service.py` | 服务生命周期，进程管理 |
| `runtime.py` | Session Runtime 池，流式处理 |
| `bridge.py` | Bus ↔ Runtime 桥接 |
| `router.py` | Session 路由 |
| `config.py` | 配置加载/转换 |
| `models.py` | GatewayConfig / GatewayState |
