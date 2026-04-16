# Phase 5: 桥接系统设计

> 日期：2026-04-05
> 状态：设计阶段
> 对应 TypeScript：`src/bridge/*`

---

## 1. 桥接系统架构

### 1.1 两种桥接模式

| 模式 | TypeScript | 说明 |
|------|------------|------|
| Env-Based Bridge | `replBridge.ts` + `bridgeMain.ts` | 使用 Environments API 的原始实现 |
| Env-Less Bridge | `remoteBridgeCore.ts` | 直接 CCR v2 连接，无轮询 |

### 1.2 核心组件

```
Bridge System
├── BridgeProtocol
│   ├── message serialization
│   ├── routing
│   └── versioning
├── Transport (v1/v2)
│   ├── HybridTransport (WebSocket + HTTP)
│   └── SSETransport + CCRClient
├── SessionManager
│   ├── createSession()
│   ├── reconnectSession()
│   └── archiveSession()
└── BridgeCore
    ├── message handling
    ├── event publishing
    └── error recovery
```

---

## 2. 桥接协议

### 2.1 BridgeProtocol

对应 TypeScript：`src/bridge/types.ts`, `src/bridge/bridgeMessaging.ts`

```python
"""IDE Bridge protocol.

TypeScript equivalent: src/bridge/types.ts, bridgeMessaging.ts
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum
import json


class BridgeMessageType(str, Enum):
    """Bridge message types."""
    # Client → Server
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    # Server → Client
    CONTROL_REQUEST = "control_request"
    CONTROL_RESPONSE = "control_response"

    # Results
    RESULT = "result"


@dataclass
class BridgeMessage:
    """Message in the bridge protocol."""
    type: str
    payload: dict[str, Any]
    id: str | None = None
    version: str = "1.0"


@dataclass
class SDKControlRequest:
    """Server-initiated control requests."""
    subtype: str  # initialize, set_model, set_max_thinking_tokens, etc.
    request_id: str | None = None
    # Subtype-specific fields
    model: str | None = None
    max_thinking_tokens: int | None = None
    mode: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_use_id: str | None = None


@dataclass
class SDKControlResponse:
    """Client response to control requests."""
    subtype: str  # success, error
    request_id: str
    response: dict[str, Any] | None = None
    error: str | None = None


class BridgeProtocol:
    """Protocol for IDE bridge communication.

    TypeScript equivalent: Message protocol in bridgeMessaging.ts
    """

    PROTOCOL_VERSION = "1.0"

    def __init__(self):
        self._handlers: dict[str, Callable] = {}

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a message handler."""
        self._handlers[message_type] = handler

    def parse_message(self, data: str | bytes) -> BridgeMessage | None:
        """Parse a message from JSON."""
        try:
            if isinstance(data, bytes):
                data = data.decode()
            parsed = json.loads(data)
            return BridgeMessage(
                type=parsed.get("type", ""),
                payload=parsed.get("payload", {}),
                id=parsed.get("id"),
                version=parsed.get("version", self.PROTOCOL_VERSION),
            )
        except json.JSONDecodeError:
            return None

    def serialize_message(self, message: BridgeMessage) -> bytes:
        """Serialize a message to JSON."""
        data = {
            "type": message.type,
            "payload": message.payload,
            "id": message.id,
            "version": message.version,
        }
        return json.dumps(data).encode("utf-8")

    def create_user_message(
        self,
        content: str | list[dict],
        uuid: str | None = None,
    ) -> BridgeMessage:
        """Create a user message."""
        return BridgeMessage(
            type=BridgeMessageType.USER.value,
            payload={"message": {"content": content}},
            id=uuid,
        )

    def create_assistant_message(
        self,
        content: str | list[dict],
        uuid: str | None = None,
    ) -> BridgeMessage:
        """Create an assistant message."""
        return BridgeMessage(
            type=BridgeMessageType.ASSISTANT.value,
            payload={"message": {"content": content}},
            id=uuid,
        )

    def create_result_message(
        self,
        subtype: str,  # success, error_max_turns, etc.
        **kwargs,
    ) -> BridgeMessage:
        """Create a result message."""
        return BridgeMessage(
            type=BridgeMessageType.RESULT.value,
            payload={"subtype": subtype, **kwargs},
        )
```

---

## 3. 传输层

### 3.1 Transport 接口

对应 TypeScript：`src/bridge/replBridgeTransport.ts`

```python
"""Transport abstraction for bridge communication."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncGenerator


class Transport(ABC):
    """Abstract transport for bridge communication."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the remote endpoint."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the remote endpoint."""
        ...

    @abstractmethod
    async def send(self, data: bytes) -> None:
        """Send data to the remote endpoint."""
        ...

    @abstractmethod
    async def receive(self) -> AsyncGenerator[bytes, None]:
        """Receive data from the remote endpoint."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        ...
```

### 3.2 HybridTransport (v1)

对应 TypeScript：`src/cli/transports/HybridTransport.ts`

```python
"""Hybrid transport - WebSocket read + HTTP POST write.

TypeScript equivalent: HybridTransport.ts
Used for Env-Based Bridge (v1).
"""
from __future__ import annotations
import asyncio
import websockets
import httpx
from typing import AsyncGenerator

from .transport import Transport


class HybridTransport(Transport):
    """Hybrid transport using WebSocket for reads and HTTP for writes.

    v1 Transport:
    - WebSocket reads from session-ingress
    - HTTP POST writes to session-ingress
    """

    def __init__(
        self,
        ingress_url: str,  # e.g., wss://session-ingress.example.com/v1/session_ingress/ws/{sessionId}
        write_url: str,    # e.g., https://session-ingress.example.com/v1/session_ingress
    ):
        self.ingress_url = ingress_url
        self.write_url = write_url
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._http: httpx.AsyncClient | None = None
        self._connected = False

    async def connect(self) -> None:
        """Connect WebSocket and HTTP client."""
        self._ws = await websockets.connect(self.ingress_url)
        self._http = httpx.AsyncClient()
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect WebSocket and HTTP client."""
        self._connected = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._http:
            await self._http.aclose()
            self._http = None

    async def send(self, data: bytes) -> None:
        """Send data via HTTP POST."""
        if not self._http:
            raise RuntimeError("Not connected")

        await self._http.post(
            self.write_url,
            content=data,
            headers={"Content-Type": "application/json"},
        )

    async def receive(self) -> AsyncGenerator[bytes, None]:
        """Receive data via WebSocket."""
        if not self._ws:
            raise RuntimeError("Not connected")

        while self._connected:
            try:
                message = await self._ws.recv()
                yield message.encode() if isinstance(message, str) else message
            except websockets.ConnectionClosed:
                break

    def is_connected(self) -> bool:
        return self._connected
```

### 3.3 SSETransport (v2)

对应 TypeScript：`src/cli/transports/SSETransport.ts`

```python
"""SSE transport for v2 bridge.

TypeScript equivalent: SSETransport.ts
Used for Env-Less Bridge (v2).
"""
from __future__ import annotations
import asyncio
import httpx
from typing import AsyncGenerator

from .transport import Transport


class SSETransport(Transport):
    """SSE transport for reading events.

    v2 Transport:
    - SSE reads from CCR worker events stream
    - HTTP writes to CCR worker events
    """

    def __init__(
        self,
        events_url: str,  # GET /v1/code/sessions/{id}/worker/events/stream
        write_url: str,   # POST /v1/code/sessions/{id}/worker/events
        state_url: str,   # PUT /v1/code/sessions/{id}/worker/state
        heartbeat_url: str,  # POST /v1/code/sessions/{id}/worker/heartbeat
    ):
        self.events_url = events_url
        self.write_url = write_url
        self.state_url = state_url
        self.heartbeat_url = heartbeat_url
        self._http: httpx.AsyncClient | None = None
        self._connected = False
        self._sequence_num: int = 0

    async def connect(self) -> None:
        """Connect SSE stream."""
        self._http = httpx.AsyncClient(timeout=30.0)
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect SSE stream."""
        self._connected = False
        if self._http:
            await self._http.aclose()
            self._http = None

    async def send(self, data: bytes) -> None:
        """Send event via HTTP POST."""
        if not self._http:
            raise RuntimeError("Not connected")

        await self._http.post(
            self.write_url,
            content=data,
            headers={"Content-Type": "application/json"},
        )

    async def receive(self) -> AsyncGenerator[bytes, None]:
        """Receive SSE events."""
        if not self._http:
            raise RuntimeError("Not connected")

        headers = {"Accept": "text/event-stream"}
        async with self._http.stream("GET", self.events_url, headers=headers) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    # Parse sequence number from event
                    # Format: sequence:{num}:{data}
                    if data.startswith("sequence:"):
                        parts = data.split(":", 2)
                        self._sequence_num = int(parts[1])
                        yield parts[2].encode()
                    else:
                        yield data.encode()

    async def send_state(self, state: dict) -> None:
        """Send worker state via HTTP PUT."""
        if not self._http:
            raise RuntimeError("Not connected")

        await self._http.put(
            self.state_url,
            json=state,
        )

    async def send_heartbeat(self) -> None:
        """Send heartbeat via HTTP POST."""
        if not self._http:
            raise RuntimeError("Not connected")

        await self._http.post(self.heartbeat_url)

    def get_sequence_num(self) -> int:
        """Get current SSE sequence number."""
        return self._sequence_num

    def is_connected(self) -> bool:
        return self._connected
```

---

## 4. 桥接核心

### 4.1 ReplBridgeHandle

对应 TypeScript：`src/bridge/replBridge.ts` ReplBridgeHandle

```python
"""RePL bridge handle - public API for bridge communication."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, AsyncGenerator
import asyncio

from .protocol import BridgeProtocol, BridgeMessage
from .transport import Transport


class ReplBridgeHandle:
    """Handle for bridge communication.

    TypeScript equivalent: ReplBridgeHandle in replBridge.ts

    Public API:
    - write_messages(): Send messages to server
    - send_control_request(): Send control request
    - teardown(): Clean shutdown
    """

    def __init__(
        self,
        transport: Transport,
        protocol: BridgeProtocol,
        session_id: str,
    ):
        self.transport = transport
        self.protocol = protocol
        self.session_id = session_id

        # Callbacks
        self.on_user_message: Callable[[BridgeMessage], None] | None = None
        self.on_control_request: Callable[[BridgeMessage], None] | None = None
        self.on_error: Callable[[Exception], None] | None = None

        # Internal state
        self._running = False
        self._message_queue: asyncio.Queue[BridgeMessage] = field(default_factory=asyncio.Queue)
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start the bridge."""
        self._running = True

        # Connect transport
        await self.transport.connect()

        # Start receive loop
        self._tasks.append(asyncio.create_task(self._receive_loop()))

        # Start send loop
        self._tasks.append(asyncio.create_task(self._send_loop()))

    async def stop(self) -> None:
        """Stop the bridge."""
        self._running = False

        # Cancel tasks
        for task in self._tasks:
            task.cancel()

        # Disconnect transport
        await self.transport.disconnect()

    async def write_messages(self, messages: list[BridgeMessage]) -> None:
        """Write messages to the bridge.

        TypeScript equivalent: writeMessages()
        """
        for msg in messages:
            await self._message_queue.put(msg)

    async def send_control_request(
        self,
        request: dict[str, Any],
        request_id: str,
    ) -> dict[str, Any]:
        """Send a control request and wait for response.

        TypeScript equivalent: sendControlRequest()
        """
        msg = BridgeMessage(
            type="control_request",
            payload={"request": request, "request_id": request_id},
        )

        # Send request
        await self._message_queue.put(msg)

        # Wait for response (with timeout)
        try:
            response = await asyncio.wait_for(
                self._get_control_response(request_id),
                timeout=60.0,
            )
            return response
        except asyncio.TimeoutError:
            return {"subtype": "error", "error": "Request timeout"}

    async def _receive_loop(self) -> None:
        """Receive loop - processes incoming messages."""
        async for data in self.transport.receive():
            msg = self.protocol.parse_message(data)
            if msg is None:
                continue

            # Handle based on type
            if msg.type == "user":
                if self.on_user_message:
                    self.on_user_message(msg)
            elif msg.type == "control_request":
                if self.on_control_request:
                    self.on_control_request(msg)

    async def _send_loop(self) -> None:
        """Send loop - sends queued messages."""
        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0,
                )
                data = self.protocol.serialize_message(msg)
                await self.transport.send(data)
            except asyncio.TimeoutError:
                continue

    async def _get_control_response(self, request_id: str) -> dict[str, Any]:
        """Wait for a control response with given request_id."""
        # This would be implemented with a future/condition
        # Simplified here
        return {"subtype": "success", "request_id": request_id}

    async def teardown(self) -> None:
        """Clean up bridge resources."""
        await self.stop()
```

---

## 5. 会话管理

### 5.1 SessionManager

对应 TypeScript：`src/bridge/createSession.ts`, `src/bridge/bridgeApi.ts`

```python
"""Session management for bridge."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import uuid

from ..services.api.client import HTTPClient


@dataclass
class SessionInfo:
    """Information about a bridge session."""
    session_id: str
    environment_id: str | None = None
    title: str | None = None
    created_at: str | None = None


class SessionManager:
    """Manages bridge sessions.

    TypeScript equivalent: createSession.ts, bridgeApi.ts
    """

    def __init__(
        self,
        base_url: str = "https://api.claude.ai",
    ):
        self.base_url = base_url
        self.http = HTTPClient(base_url=base_url)

    async def create_session(
        self,
        title: str | None = None,
        git_context: dict[str, Any] | None = None,
    ) -> SessionInfo:
        """Create a new bridge session.

        TypeScript equivalent: createSession()
        """
        session_id = str(uuid.uuid4())

        # In production, this would call the API
        # POST /v1/sessions
        return SessionInfo(
            session_id=session_id,
            title=title,
        )

    async def reconnect_session(
        self,
        session_id: str,
        environment_id: str | None = None,
    ) -> SessionInfo:
        """Reconnect to an existing session.

        TypeScript equivalent: reconnectSession()
        """
        # Would call API to get session info
        # POST /v1/sessions/{id}/reconnect
        return SessionInfo(session_id=session_id)

    async def archive_session(self, session_id: str) -> None:
        """Archive (end) a session.

        TypeScript equivalent: archiveSession()
        """
        # POST /v1/sessions/{id}/archive
        pass

    async def update_session_title(
        self,
        session_id: str,
        title: str,
    ) -> None:
        """Update session title.

        TypeScript equivalent: updateSessionTitle()
        """
        # PUT /v1/sessions/{id}/title
        pass

    def write_bridge_pointer(
        self,
        session_id: str,
        environment_id: str | None = None,
    ) -> None:
        """Write bridge pointer file for crash recovery.

        TypeScript equivalent: bridgePointer.json
        """
        import json
        from pathlib import Path

        pointer = {
            "sessionId": session_id,
            "environmentId": environment_id,
            "source": "repl",
        }

        path = Path.home() / ".claude" / "bridge" / "bridge_pointer.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(pointer, indent=2))

    def read_bridge_pointer(self) -> dict[str, Any] | None:
        """Read bridge pointer file for reconnection.

        TypeScript equivalent: readBridgePointer()
        """
        import json
        from pathlib import Path

        path = Path.home() / ".claude" / "bridge" / "bridge_pointer.json"
        if path.exists():
            return json.loads(path.read_text())
        return None
```

---

## 6. 消息处理

### 6.1 IngressMessageHandler

对应 TypeScript：`src/bridge/bridgeMessaging.ts` handleIngressMessage

```python
"""Message handling for bridge."""
from __future__ import annotations
from typing import Any, Callable
from dataclasses import dataclass

from .protocol import BridgeMessage, BridgeProtocol


@dataclass
class BoundedUUIDSet:
    """Ring buffer for UUID dedup.

    TypeScript equivalent: BoundedUUIDSet
    """
    max_size: int = 100
    _uuids: list[str] | None = None
    _set: set[str] | None = None

    def __post_init__(self):
        self._uuids = []
        self._set = set()

    def add(self, uuid: str) -> bool:
        """Add UUID, returns True if new (not duplicate)."""
        if uuid in self._set:
            return False

        self._set.add(uuid)
        self._uuids.append(uuid)

        if len(self._uuids) > self.max_size:
            old = self._uuids.pop(0)
            self._set.discard(old)

        return True


class IngressMessageHandler:
    """Handles incoming bridge messages.

    TypeScript equivalent: handleIngressMessage() in bridgeMessaging.ts
    """

    def __init__(
        self,
        protocol: BridgeProtocol,
        on_user_message: Callable[[BridgeMessage], None] | None = None,
        on_control_request: Callable[[BridgeMessage], None] | None = None,
    ):
        self.protocol = protocol
        self.on_user_message = on_user_message
        self.on_control_request = on_control_request
        self._uuid_dedup = BoundedUUIDSet()

    def handle_message(self, data: str | bytes) -> None:
        """Handle an incoming message."""
        msg = self.protocol.parse_message(data)
        if msg is None:
            return

        # Check for duplicate (echo filtering)
        if msg.id and not self._uuid_dedup.add(msg.id):
            return  # Duplicate, skip

        # Route based on type
        if msg.type == "user":
            self._handle_user_message(msg)
        elif msg.type == "control_request":
            self._handle_control_request(msg)
        elif msg.type == "control_response":
            self._handle_control_response(msg)

    def _handle_user_message(self, msg: BridgeMessage) -> None:
        """Handle user message from server."""
        if self.on_user_message:
            self.on_user_message(msg)

    def _handle_control_request(self, msg: BridgeMessage) -> None:
        """Handle control request from server."""
        if self.on_control_request:
            self.on_control_request(msg)

    def _handle_control_response(self, msg: BridgeMessage) -> None:
        """Handle control response."""
        # Would notify waiting request
        pass


def is_sdk_message(data: dict) -> bool:
    """Type guard for SDK message."""
    return "type" in data and "payload" in data


def is_sdk_control_request(data: dict) -> bool:
    """Type guard for SDK control request."""
    return data.get("type") == "control_request"
```

---

## 7. 错误恢复

### 7.1 BridgeErrorRecovery

对应 TypeScript：错误恢复逻辑在 `bridgeMain.ts`, `replBridge.ts`

```python
"""Error recovery for bridge connections."""
from __future__ import annotations
import asyncio
from typing import Callable


class BridgeErrorRecovery:
    """Handles reconnection and error recovery for bridge.

    TypeScript equivalent: Reconnection logic in bridgeMain.ts
    """

    def __init__(
        self,
        on_reconnect: Callable,
        max_reconnect_attempts: int = 10,
    ):
        self.on_reconnect = on_reconnect
        self.max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_count = 0

    async def handle_disconnect(self, exception: Exception | None = None) -> bool:
        """Handle disconnect, attempt reconnection.

        Returns True if reconnected, False if giving up.
        """
        self._reconnect_count += 1

        if self._reconnect_count > self.max_reconnect_attempts:
            return False

        # Exponential backoff: 2s, 4s, 8s, 16s, 32s, 60s (cap)
        delay = min(2 ** (self._reconnect_count - 1), 60)
        await asyncio.sleep(delay)

        # Attempt reconnection
        try:
            await self.on_reconnect()
            self._reconnect_count = 0
            return True
        except Exception:
            return await self.handle_disconnect()

    def reset_reconnect_count(self) -> None:
        """Reset reconnect counter after successful connection."""
        self._reconnect_count = 0
```

---

## 8. IDE 集成

### 8.1 IDEDetection

对应 TypeScript：`src/commands/ide/ide.tsx`

```python
"""IDE detection for bridge integration."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class IDEInfo:
    """Information about detected IDE."""
    name: str  # vscode, cursor, intellij, etc.
    workspace_folders: list[str]
    port: int
    pid: int | None = None
    use_websocket: bool = True


class IDEDetector:
    """Detect running IDE and its connection info.

    TypeScript equivalent: src/commands/ide/ide.tsx
    """

    # IDE lockfile patterns
    IDE_LOCKFILES = {
        "vscode": "~/.claude/ide/vscode.lock",
        "cursor": "~/.claude/ide/cursor.lock",
        "windsurf": "~/.claude/ide/windsurf.lock",
        "intellij": "~/.claude/ide/intellij.lock",
        "pycharm": "~/.claude/ide/pycharm.lock",
        "webstorm": "~/.claude/ide/webstorm.lock",
    }

    def detect(self) -> list[IDEInfo]:
        """Detect all running IDEs."""
        detected = []
        for ide_name, lockfile in self.IDE_LOCKFILES.items():
            path = Path(lockfile).expanduser()
            if path.exists():
                info = self._read_lockfile(path, ide_name)
                if info:
                    detected.append(info)
        return detected

    def _read_lockfile(self, path: Path, ide_name: str) -> IDEInfo | None:
        """Read IDE lockfile."""
        import json
        try:
            data = json.loads(path.read_text())
            return IDEInfo(
                name=ide_name,
                workspace_folders=data.get("workspaceFolders", []),
                port=data.get("port", 18792),
                pid=data.get("pid"),
                use_websocket=data.get("useWebSocket", "ws") == "ws",
            )
        except (json.JSONDecodeError, KeyError):
            return None
```

---

## 9. 实施任务清单

### Phase 5.1: 协议层
- [ ] 实现 `bridge/protocol.py` - BridgeProtocol
- [ ] 实现消息序列化/反序列化
- [ ] 实现消息类型定义

### Phase 5.2: 传输层
- [ ] 实现 `bridge/transport.py` - Transport 基类
- [ ] 实现 `bridge/transports/hybrid.py` - HybridTransport (v1)
- [ ] 实现 `bridge/transports/sse.py` - SSETransport (v2)

### Phase 5.3: 桥接核心
- [ ] 实现 `bridge/handle.py` - ReplBridgeHandle
- [ ] 实现消息队列
- [ ] 实现控制请求/响应

### Phase 5.4: 会话管理
- [ ] 实现 `bridge/session.py` - SessionManager
- [ ] 实现创建/重连/归档
- [ ] 实现 bridge pointer

### Phase 5.5: 消息处理
- [ ] 实现 `bridge/handler.py` - IngressMessageHandler
- [ ] 实现 UUID 去重
- [ ] 实现类型路由

### Phase 5.6: 错误恢复
- [ ] 实现 `bridge/recovery.py` - BridgeErrorRecovery
- [ ] 实现重连逻辑
- [ ] 实现退避策略

### Phase 5.7: IDE 集成
- [ ] 实现 `bridge/ide.py` - IDEDetector
- [ ] 实现 IDE 检测
- [ ] 实现 lockfile 读取
