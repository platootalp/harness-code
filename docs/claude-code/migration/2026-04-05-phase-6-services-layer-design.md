# Phase 6: 服务层设计

> 日期：2026-04-05
> 状态：设计阶段
> 对应 TypeScript：`src/services/*`

---

## 1. 服务层架构

### 1.1 子系统

```
Services Layer
├── API Client
│   ├── ClaudeAIClient (multi-provider)
│   ├── HTTPClient
│   └── Error handling
├── MCP
│   ├── MCPClient
│   ├── MCPServer
│   ├── Protocol
│   └── Auth (OAuth)
├── Storage
│   └── SessionStorage
└── Utilities
    ├── Notifier
    └── TokenCounter
```

---

## 2. API 客户端

### 2.1 Multi-Provider Claude Client

对应 TypeScript：`src/services/api/claude.ts`

```python
"""Anthropic Claude API client with multi-provider support."""
from __future__ import annotations
import os
from typing import Any, AsyncGenerator, Literal
from enum import Enum

from .client import HTTPClient
from .errors import APIError, RateLimitError, AuthError, PromptTooLongError
from ...models.message import Message


class ClaudeProvider(str, Enum):
    """API provider type."""
    DIRECT = "direct"           # Direct API (ANTHROPIC_API_KEY)
    AWS_BEDROCK = "bedrock"      # AWS Bedrock
    AZURE_FOUNDRY = "foundry"   # Azure Foundry
    GOOGLE_VERTEX = "vertex"   # Google Vertex AI


class ClaudeAIClient:
    """Client for Anthropic Claude API.

    TypeScript equivalent: src/services/api/claude.ts

    Supports:
    - Direct API with API key
    - AWS Bedrock
    - Azure Foundry
    - Google Vertex AI
    """

    def __init__(
        self,
        api_key: str | None = None,
        provider: ClaudeProvider = ClaudeProvider.DIRECT,
        model: str = "claude-opus-4-6",
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.provider = provider
        self.model = model
        self.base_url = self._get_base_url()
        self.http = HTTPClient(base_url=self.base_url, timeout=60.0)

        # Session for request correlation
        self.session_id: str | None = None

    def _get_base_url(self) -> str:
        """Get base URL for the provider."""
        match self.provider:
            case ClaudeProvider.DIRECT:
                return "https://api.anthropic.com/v1"
            case ClaudeProvider.AWS_BEDROCK:
                region = os.environ.get("AWS_REGION", "us-east-1")
                return f"https://bedrock.{region}.amazonaws.com"
            case ClaudeProvider.AZURE_FOUNDRY:
                return os.environ.get("ANTHROPIC_FOUNDRY_ENDPOINT", "")
            case ClaudeProvider.GOOGLE_VERTEX:
                project = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID", "")
                return f"https://{project}-aiplatform.googleapis.com"
            case _:
                return "https://api.anthropic.com/v1"

    def _get_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "x-app": "cli",
            "User-Agent": self._get_user_agent(),
        }

        if self.session_id:
            headers["X-Claude-Code-Session-Id"] = self.session_id

        # Custom headers
        custom = os.environ.get("ANTHROPIC_CUSTOM_HEADERS")
        if custom:
            # Parse custom headers (format: "Key: Value; Key2: Value2")
            for pair in custom.split(";"):
                if ":" in pair:
                    key, value = pair.split(":", 1)
                    headers[key.strip()] = value.strip()

        return headers

    def _get_user_agent(self) -> str:
        """Build user agent string."""
        return f"ClaudeCode/{self._get_version()}"

    def _get_version(self) -> str:
        """Get Claude Code version."""
        # Would read from package.json or similar
        return "0.1.0"

    async def chat_complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        thinking: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Non-streaming chat completion.

        TypeScript equivalent: chatComplete()
        """
        payload = {
            "model": self.model,
            "messages": [self._message_to_dict(m) for m in messages],
            "max_tokens": max_tokens,
        }

        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools
        if thinking:
            payload["thinking"] = thinking

        async with self.http:
            response = await self.http.post("/messages", json=payload, headers=self._get_headers())

        return self._handle_response(response)

    async def stream_complete(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Streaming chat completion.

        TypeScript equivalent: streamComplete()

        Yields raw SSE data lines.
        """
        payload = {
            "model": self.model,
            "messages": [self._message_to_dict(m) for m in messages],
            "max_tokens": max_tokens,
            "stream": True,
        }

        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools

        async with self.http:
            async for chunk in self.http.stream_post("/messages", json=payload, headers=self._get_headers()):
                line = chunk.decode().strip()
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    yield data

    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        """Convert Message to API dict format."""
        data = message.to_dict()

        # Remove Python-specific fields
        data.pop("created_at", None)
        data.pop("name", None)
        data.pop("tool_name", None)

        return data

    def _handle_response(self, response: Any) -> dict[str, Any]:
        """Handle API response, raising errors for failures."""
        status = response.status_code

        if status == 200:
            return response.json()

        if status == 401 or status == 403:
            raise AuthError(f"Authentication error: {response.text}", status)

        if status == 429:
            retry_after = response.headers.get("retry-after")
            raise RateLimitError(
                "Rate limit exceeded",
                retry_after=float(retry_after) if retry_after else None,
            )

        if status == 400:
            # Check for specific errors
            data = response.json()
            error_type = data.get("type", "")
            if error_type == "invalid_request_error":
                raise APIError(
                    "bad_request",
                    data.get("error", {}).get("message", "Bad request"),
                    status,
                )
            elif "prompt" in str(data).lower():
                raise PromptTooLongError(str(data))

        if status >= 500:
            raise APIError("server_error", f"Server error: {response.text}", status)

        return response.json()

    def set_session_id(self, session_id: str) -> None:
        """Set session ID for request correlation."""
        self.session_id = session_id
```

### 2.2 HTTP Client

```python
"""HTTP client with streaming support."""
from __future__ import annotations
import httpx
from typing import Any, AsyncGenerator


class HTTPClient:
    """Async HTTP client with streaming support."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 60.0,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> HTTPClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """POST request."""
        assert self._client is not None
        return await self._client.post(url, json=json, headers=headers)

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """GET request."""
        assert self._client is not None
        return await self._client.get(url, params=params, headers=headers)

    async def put(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """PUT request."""
        assert self._client is not None
        return await self._client.put(url, json=json, headers=headers)

    async def stream_post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """Streaming POST request."""
        assert self._client is not None
        async with self._client.stream("POST", url, json=json, headers=headers) as response:
            async for chunk in response.aiter_bytes():
                yield chunk
```

---

## 3. MCP 客户端

### 3.1 MCPClient

对应 TypeScript：`src/services/mcp/client.ts`

```python
"""MCP client implementation."""
from __future__ import annotations
import json
import asyncio
from dataclasses import dataclass
from typing import Any, AsyncGenerator
from enum import Enum

from .protocol import MCPProtocol, MCPMessage
from .auth import ClaudeAuthProvider, OAuthTokens


class MCPTransportType(str, Enum):
    """MCP transport types."""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WS = "ws"
    SSE_IDE = "sse-ide"
    WS_IDE = "ws-ide"
    CLAUDEAI_PROXY = "claudeai-proxy"
    SDK = "sdk"


@dataclass
class MCPServerConfig:
    """MCP server configuration."""
    name: str
    transport_type: MCPTransportType
    url: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None


class MCPClient:
    """Client for Model Context Protocol.

    TypeScript equivalent: src/services/mcp/client.ts

    Features:
    - Multiple transport types (stdio, SSE, HTTP, WebSocket)
    - OAuth authentication
    - Automatic token refresh
    - Request/response correlation
    """

    def __init__(
        self,
        config: MCPServerConfig,
        auth_provider: ClaudeAuthProvider | None = None,
    ):
        self.config = config
        self.auth_provider = auth_provider
        self.protocol = MCPProtocol()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False

    async def connect(self, timeout: float = 30.0) -> None:
        """Connect to the MCP server.

        TypeScript equivalent: connectToServer()
        """
        match self.config.transport_type:
            case MCPTransportType.STDIO:
                await self._connect_stdio()
            case MCPTransportType.SSE | MCPTransportType.SSE_IDE:
                await self._connect_sse()
            case MCPTransportType.WS | MCPTransportType.WS_IDE:
                await self._connect_websocket()
            case _:
                raise ValueError(f"Unsupported transport: {self.config.transport_type}")

        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._connected = False

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the server.

        TypeScript equivalent: tools/list
        """
        message = MCPMessage(
            method="tools/list",
            params={},
        )
        response = await self._send_request(message)
        return response.get("result", {}).get("tools", [])

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Call a tool on the MCP server.

        TypeScript equivalent: tools/call
        """
        message = MCPMessage(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments,
            },
        )
        response = await self._send_request(message)
        return response.get("result", {})

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available resources."""
        message = MCPMessage(
            method="resources/list",
            params={},
        )
        response = await self._send_request(message)
        return response.get("result", {}).get("resources", [])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource."""
        message = MCPMessage(
            method="resources/read",
            params={"uri": uri},
        )
        response = await self._send_request(message)
        return response.get("result", {})

    async def _connect_stdio(self) -> None:
        """Connect via stdio transport."""
        process = await asyncio.create_subprocess_exec(
            self.config.command or "",
            *(self.config.args or []),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **(self.config.env or {})},
        )
        self._reader = asyncio.StreamReader()
        await self._reader.set_protocol(process.stdout)
        # Note: Actual implementation more complex

    async def _connect_sse(self) -> None:
        """Connect via SSE transport."""
        # HTTP + SSE for server-sent events
        pass

    async def _connect_websocket(self) -> None:
        """Connect via WebSocket transport."""
        import websockets
        async with websockets.connect(self.config.url) as ws:
            self._ws = ws
            # Handle messages
            pass

    async def _send_request(
        self,
        message: MCPMessage,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """Send a request and wait for response."""
        if not self._connected:
            raise RuntimeError("Not connected")

        # Send message
        data = self.protocol.serialize_message(message)
        self._writer.write(data)
        await self._writer.drain()

        # Wait for response with timeout
        try:
            response_data = await asyncio.wait_for(
                self._read_response(),
                timeout=timeout,
            )
            return response_data
        except asyncio.TimeoutError:
            raise TimeoutError(f"MCP request timed out after {timeout}s")

    async def _read_response(self) -> dict[str, Any]:
        """Read response from transport."""
        # Implementation depends on transport type
        pass
```

### 3.2 MCP Protocol

```python
"""MCP protocol implementation."""
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class MCPMessage:
    """MCP JSON-RPC message."""
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str | None = None
    params: dict[str, Any] | None = None
    result: Any = None
    error: dict[str, Any] | None = None


class MCPProtocol:
    """MCP protocol handler.

    TypeScript equivalent: MCP protocol in @modelcontextprotocol/sdk
    """

    JSONRPC_VERSION = "2.0"

    def parse_message(self, data: str | bytes) -> MCPMessage | None:
        """Parse a JSON-RPC message."""
        try:
            if isinstance(data, bytes):
                data = data.decode()
            parsed = json.loads(data)
            return MCPMessage(
                id=parsed.get("id"),
                method=parsed.get("method"),
                params=parsed.get("params"),
                result=parsed.get("result"),
                error=parsed.get("error"),
            )
        except json.JSONDecodeError:
            return None

    def serialize_message(self, message: MCPMessage) -> bytes:
        """Serialize a JSON-RPC message."""
        data = {"jsonrpc": self.JSONRPC_VERSION}

        if message.id is not None:
            data["id"] = message.id
        if message.method is not None:
            data["method"] = message.method
        if message.params is not None:
            data["params"] = message.params
        if message.result is not None:
            data["result"] = message.result
        if message.error is not None:
            data["error"] = message.error

        return json.dumps(data).encode("utf-8")

    def create_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        request_id: str | int | None = None,
    ) -> MCPMessage:
        """Create a request message."""
        return MCPMessage(
            id=request_id,
            method=method,
            params=params,
        )

    def create_response(
        self,
        id: str | int,
        result: Any,
    ) -> MCPMessage:
        """Create a response message."""
        return MCPMessage(
            id=id,
            result=result,
        )

    def create_error(
        self,
        id: str | int,
        code: int,
        message: str,
    ) -> MCPMessage:
        """Create an error response."""
        return MCPMessage(
            id=id,
            error={"code": code, "message": message},
        )
```

### 3.3 OAuth Provider

对应 TypeScript：`src/services/mcp/auth.ts` ClaudeAuthProvider

```python
"""MCP OAuth authentication provider."""
from __future__ import annotations
import time
import asyncio
from dataclasses import dataclass
from typing import Any
import httpx

from .auth import OAuthTokens


class ClaudeAuthProvider:
    """OAuth provider for MCP server authentication.

    TypeScript equivalent: ClaudeAuthProvider in mcp/auth.ts

    Features:
    - Automatic token refresh (5 min before expiry)
    - Lockfile-based cross-process deduplication
    - Keychain storage
    - XAA (Cross-App Access) support
    """

    def __init__(
        self,
        server_name: str,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.server_name = server_name
        self._client_id = client_id
        self._client_secret = client_secret
        self._tokens: OAuthTokens | None = None
        self._lockfile_path = f"/tmp/mcp-refresh-{hash(server_name)}.lock"

    async def get_tokens(self) -> OAuthTokens | None:
        """Get current tokens, refreshing if needed.

        TypeScript equivalent: tokens()
        """
        if self._tokens is None:
            self._tokens = await self._load_tokens()

        if self._tokens and self._should_refresh():
            await self._refresh_tokens()

        return self._tokens

    async def save_tokens(self, tokens: OAuthTokens) -> None:
        """Save tokens to keychain.

        TypeScript equivalent: saveTokens()
        """
        # In production: save to keychain
        import json
        from pathlib import Path

        path = Path.home() / ".claude" / "mcp_tokens" / f"{self.server_name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(tokens.__dict__))
        path.chmod(0o600)

        self._tokens = tokens

    async def save_client_info(
        self,
        client_id: str,
        client_secret: str,
    ) -> None:
        """Save OAuth client information.

        TypeScript equivalent: saveClientInformation()
        """
        # In production: save to keychain
        self._client_id = client_id
        self._client_secret = client_secret

    def should_refresh(self) -> bool:
        """Check if token should be refreshed (5 min before expiry)."""
        if not self._tokens:
            return True

        expiry = self._tokens.expires_at
        if not expiry:
            return False

        return time.time() >= (expiry - 300)  # 5 min before

    async def _load_tokens(self) -> OAuthTokens | None:
        """Load tokens from keychain."""
        import json
        from pathlib import Path

        path = Path.home() / ".claude" / "mcp_tokens" / f"{self.server_name}.json"
        if path.exists():
            data = json.loads(path.read_text())
            return OAuthTokens(**data)
        return None

    async def _refresh_tokens(self) -> None:
        """Refresh OAuth tokens with retry logic."""
        if not self._tokens or not self._tokens.refresh_token:
            # Need to do initial auth
            return

        # Lockfile check for cross-process deduplication
        if await self._acquire_refresh_lock():
            try:
                # Perform refresh
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://auth.anthropic.com/oauth/token",
                        json={
                            "grant_type": "refresh_token",
                            "refresh_token": self._tokens.refresh_token,
                            "client_id": self._client_id,
                            "client_secret": self._client_secret,
                        },
                    )

                if response.status_code == 200:
                    new_tokens = OAuthTokens(**response.json())
                    await self.save_tokens(new_tokens)
                elif response.status_code == 400:
                    # Invalid grant - clear tokens
                    self._tokens = None

            finally:
                await self._release_refresh_lock()

    async def _acquire_refresh_lock(self) -> bool:
        """Acquire lockfile for cross-process refresh deduplication."""
        import fcntl

        try:
            lockfile = open(self._lockfile_path, "w")
            fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lockfile.write(str(time.time()))
            return True
        except (IOError, OSError):
            return False

    async def _release_refresh_lock(self) -> None:
        """Release refresh lockfile."""
        import os
        try:
            os.remove(self._lockfile_path)
        except FileNotFoundError:
            pass
```

---

## 4. 会话存储

### 4.1 SessionStorage

对应 TypeScript：`src/services/SessionMemory/`

```python
"""Session storage for conversations."""
from __future__ import annotations
import os
import json
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from ...models.message import Message


@dataclass
class SessionMemoryConfig:
    """Configuration for session memory."""
    minimum_message_tokens_to_init: int = 10_000
    minimum_tokens_between_update: int = 5_000
    tool_calls_between_updates: int = 3


class SessionStorage:
    """Manages session storage and summarization.

    TypeScript equivalent: SessionMemory in services/SessionMemory/
    """

    def __init__(
        self,
        session_dir: Path | None = None,
        config: SessionMemoryConfig | None = None,
    ):
        self.session_dir = session_dir or Path.home() / ".claude" / "sessions"
        self.config = config or SessionMemoryConfig()
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def get_session_path(self, session_id: str) -> Path:
        """Get path for session file."""
        return self.session_dir / f"{session_id}.json"

    async def save_session(
        self,
        session_id: str,
        messages: list[Message],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save session to disk."""
        path = self.get_session_path(session_id)

        data = {
            "session_id": session_id,
            "messages": [self._message_to_dict(m) for m in messages],
            "metadata": metadata or {},
            "saved_at": datetime.now().isoformat(),
        }

        # Write atomically
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2))
        tmp_path.rename(path)

    async def load_session(self, session_id: str) -> dict[str, Any] | None:
        """Load session from disk."""
        path = self.get_session_path(session_id)
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            return data
        except json.JSONDecodeError:
            return None

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all saved sessions."""
        sessions = []
        for path in self.session_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                sessions.append({
                    "session_id": data.get("session_id"),
                    "saved_at": data.get("saved_at"),
                    "message_count": len(data.get("messages", [])),
                })
            except json.JSONDecodeError:
                continue

        return sorted(sessions, key=lambda s: s.get("saved_at", ""), reverse=True)

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        path = self.get_session_path(session_id)
        if path.exists():
            path.unlink()

    def _message_to_dict(self, message: Message) -> dict[str, Any]:
        """Convert Message to dict for storage."""
        return message.to_dict()
```

---

## 5. Token 计算

### 5.1 TokenCounter

对应 TypeScript：token counting utilities

```python
"""Token counting utilities."""
from __future__ import annotations
from typing import Any


class TokenCounter:
    """Estimates token counts for messages.

    TypeScript equivalent: tokenCountWithEstimation() in various files

    Note: This is an approximation. For exact counts, use tiktoken.
    """

    # Approximate tokens per character ratio
    TOKENS_PER_CHAR = 0.25

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Estimate tokens in text."""
        return int(len(text) * cls.TOKENS_PER_CHAR)

    @classmethod
    def estimate_messages_tokens(cls, messages: list[dict[str, Any]]) -> int:
        """Estimate total tokens in messages."""
        total = 0

        for msg in messages:
            # Role overhead
            total += 5

            content = msg.get("content", "")
            if isinstance(content, str):
                total += cls.estimate_tokens(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            total += cls.estimate_tokens(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            # Tool call overhead
                            total += 100
                            total += cls.estimate_tokens(str(block.get("input", {})))

        return total

    @classmethod
    def count_messages_tokens(cls, messages: list[dict[str, Any]]) -> int:
        """Count tokens in messages (placeholder for tiktoken)."""
        # In production, use tiktoken for accurate counting
        return cls.estimate_messages_tokens(messages)
```

---

## 6. 实施任务清单

### Phase 6.1: API 客户端
- [ ] 实现 `services/api/client.py` - HTTPClient
- [ ] 实现 `services/api/claude.py` - ClaudeAIClient (multi-provider)
- [ ] 实现 `services/api/errors.py` - Error types
- [ ] 实现错误处理和重试

### Phase 6.2: MCP 客户端
- [ ] 实现 `services/mcp/protocol.py` - MCPProtocol
- [ ] 实现 `services/mcp/client.py` - MCPClient
- [ ] 实现 `services/mcp/auth.py` - ClaudeAuthProvider
- [ ] 实现多传输类型支持

### Phase 6.3: 会话存储
- [ ] 实现 `services/storage/session.py` - SessionStorage
- [ ] 实现会话保存/加载
- [ ] 实现会话列表
- [ ] 实现会话摘要

### Phase 6.4: 工具函数
- [ ] 实现 `services/utils/token.py` - TokenCounter
- [ ] 实现 token 估算
- [ ] 实现消息 token 计数

### Phase 6.5: 其他服务
- [ ] 实现通知服务 (Notifier)
- [ ] 实现会话记忆 (SessionMemory)
