"""
服务层 Python 实现

展示 Claude Code 服务层的核心设计模式在 Python 中的实现：
- API 多提供者支持
- MCP 客户端
- OAuth 服务
- LSP 服务器
- Analytics (无环设计)
- Context Compression
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)
import hashlib


# =============================================================================
# 1. API 服务 - 多提供者支持
# =============================================================================

class APIProvider(str, Enum):
    DIRECT = "direct"
    AWS_BEDROCK = "aws-bedrock"
    AZURE_FOUNDERY = "azure-foundry"
    VERTEX_AI = "vertex-ai"


@dataclass
class ClientConfig:
    """API 客户端配置"""
    provider: APIProvider = APIProvider.DIRECT
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    # Provider-specific 配置
    bedrock_region: Optional[str] = None
    azure_endpoint: Optional[str] = None
    vertex_project: Optional[str] = None


class APIClient(ABC):
    """API 客户端基类"""

    @abstractmethod
    async def query_with_streaming(
        self,
        request: 'ModelRequest'
    ) -> AsyncGenerator['StreamEvent', None]:
        """流式查询"""
        pass


class DirectAPIClient(APIClient):
    """Direct API 客户端 (api.anthropic.com)"""

    def __init__(self, config: ClientConfig):
        self.config = config
        self.base_url = config.base_url or "https://api.anthropic.com"

    async def query_with_streaming(
        self,
        request: 'ModelRequest'
    ) -> AsyncGenerator['StreamEvent', None]:
        """发送流式请求"""
        import aiohttp

        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.config.api_key or '',
            'anthropic-version': '2023-06-01',
        }

        payload = {
            'model': request.model,
            'messages': [
                {'role': m.role, 'content': [
                    {'type': b.type, 'text': b.text}
                    for b in m.content
                ]} for m in request.messages
            ],
            'max_tokens': request.max_tokens or 4096,
            'stream': True,
        }

        if request.system:
            payload['system'] = [b.text for b in request.system if b.text]

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=payload
            ) as response:
                async for line in response.content:
                    if line:
                        yield self._parse_line(line)


class BedrockAPIClient(APIClient):
    """AWS Bedrock API 客户端"""

    def __init__(self, config: ClientConfig):
        self.config = config
        self.region = config.bedrock_region or 'us-east-1'

    async def query_with_streaming(
        self,
        request: 'ModelRequest'
    ) -> AsyncGenerator['StreamEvent', None]:
        """发送 Bedrock 请求"""
        # 简化实现
        # 实际需要使用 @anthropic-ai/bedrock-sdk
        yield StreamEvent(type="message_start", data={})


class APIFactory:
    """API 客户端工厂"""

    @staticmethod
    def create(config: ClientConfig) -> APIClient:
        """创建 API 客户端"""
        if config.provider == APIProvider.AWS_BEDROCK:
            return BedrockAPIClient(config)
        elif config.provider == APIProvider.DIRECT:
            return DirectAPIClient(config)
        else:
            return DirectAPIClient(config)


# =============================================================================
# 2. OAuth 服务
# =============================================================================

import secrets
import base64
import hashlib
import urllib.parse
from dataclasses import dataclass


@dataclass
class OAuthTokens:
    """OAuth 令牌"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int = 0
    token_type: str = "Bearer"


@dataclass
class OAuthConfig:
    """OAuth 配置"""
    client_id: str
    authorization_endpoint: str
    token_endpoint: str
    redirect_uri: str
    scope: str = "offline_access profile"


class OAuthService:
    """
    OAuth 2.0 服务

    等价于 TypeScript 的 OAuthService 类
    """

    def __init__(self, config: OAuthConfig):
        self.config = config
        self._server: Optional[Any] = None

    async def authorize(self) -> OAuthTokens:
        """
        执行 OAuth 授权流程

        1. 生成 PKCE
        2. 启动本地服务器
        3. 构建 auth URL
        4. 等待回调
        5. 交换 token
        """
        # 1. 生成 PKCE
        code_verifier = secrets.token_urlsafe(128)
        code_challenge = self._generate_code_challenge(code_verifier)

        # 2. 启动本地服务器
        self._server = await self._start_callback_server()

        # 3. 构建 auth URL
        auth_url = self._build_auth_url(code_challenge)

        # 4. 打开浏览器
        import webbrowser
        webbrowser.open(auth_url)

        # 5. 等待回调
        code = await self._server.wait_for_callback()

        # 6. 交换 token
        tokens = await self._exchange_code(code, code_verifier)

        # 7. 清理
        await self._server.close()

        return tokens

    def _generate_code_challenge(self, verifier: str) -> str:
        """生成 code challenge"""
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip('=')

    def _build_auth_url(self, code_challenge: str) -> str:
        """构建授权 URL"""
        params = {
            'client_id': self.config.client_id,
            'redirect_uri': self.config.redirect_uri,
            'response_type': 'code',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'scope': self.config.scope,
        }
        return f"{self.config.authorization_endpoint}?{urllib.parse.urlencode(params)}"

    async def _start_callback_server(self) -> 'CallbackServer':
        """启动回调服务器"""
        import aiohttp

        queue = asyncio.Queue()

        async def handler(request):
            code = request.query.get('code')
            if code:
                queue.put_nowait(code)
            return aiohttp.web.Response(text="Authorization complete")

        app = aiohttp.web.Application()
        app.router.add_get('/callback', handler)

        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = runner电信()
        await site.start()

        return CallbackServer(runner=runner, queue=queue)

    async def _exchange_code(
        self,
        code: str,
        code_verifier: str
    ) -> OAuthTokens:
        """交换 code 为 token"""
        import aiohttp

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.config.client_id,
            'code_verifier': code_verifier,
            'redirect_uri': self.config.redirect_uri,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.config.token_endpoint,
                data=data
            ) as response:
                result = await response.json()
                return OAuthTokens(
                    access_token=result['access_token'],
                    refresh_token=result.get('refresh_token'),
                    expires_in=result.get('expires_in', 3600),
                    token_type=result.get('token_type', 'Bearer')
                )


class CallbackServer:
    """OAuth 回调服务器"""

    def __init__(self, runner, queue: asyncio.Queue):
        self._runner = runner
        self._queue = queue

    async def wait_for_callback(self) -> str:
        """等待回调"""
        return await self._queue.get()

    async def close(self) -> None:
        """关闭服务器"""
        await self._runner.cleanup()


# =============================================================================
# 3. MCP 服务
# =============================================================================

from enum import Enum


class MCPTransportType(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WEBSOCKET = "websocket"


class MCPConnectionState(str, Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    FAILED = "failed"
    DISABLED = "disabled"
    NEEDS_AUTH = "needs-auth"


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    id: str
    name: str
    transport: MCPTransportType = MCPTransportType.STDIO
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class MCPTool:
    """MCP 工具"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_id: str


class MCPClient:
    """
    MCP 客户端

    等价于 TypeScript 的 MCPClient 类
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.state: MCPConnectionState = MCPConnectionState.PENDING
        self._process: Optional[asyncio.subprocess.Process] = None

    async def connect(self) -> None:
        """连接 MCP 服务器"""
        try:
            if self.config.transport == MCPTransportType.STDIO:
                await self._connect_stdio()
            elif self.config.transport == MCPTransportType.SSE:
                await self._connect_sse()
            elif self.config.transport == MCPTransportType.WEBSOCKET:
                await self._connect_websocket()

            self.state = MCPConnectionState.CONNECTED

        except Exception as e:
            self.state = MCPConnectionState.FAILED
            raise

    async def _connect_stdio(self) -> None:
        """通过 stdio 连接"""
        self._process = await asyncio.create_subprocess_exec(
            self.config.command,
            *self.config.args,
            env={**self.config.env},
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def _connect_sse(self) -> None:
        """通过 SSE 连接"""
        # 简化实现
        pass

    async def _connect_websocket(self) -> None:
        """通过 WebSocket 连接"""
        # 简化实现
        pass

    async def call_tool(
        self,
        name: str,
        input_data: Dict[str, Any]
    ) -> Any:
        """调用 MCP 工具"""
        if self.state != MCPConnectionState.CONNECTED:
            raise RuntimeError("MCP client not connected")

        # 发送请求
        request = {
            'jsonrpc': '2.0',
            'id': str(time.time()),
            'method': 'tools/call',
            'params': {
                'name': name,
                'arguments': input_data
            }
        }

        if self._process:
            # stdio 传输
            self._process.stdin.write(json.dumps(request).encode())
            await self._process.stdin.drain()

            # 读取响应
            response_line = await self._process.stdout.readline()
            response = json.loads(response_line.decode())

            return response.get('result', {}).get('content')
        else:
            raise NotImplementedError("Only stdio transport implemented")

    async def reconnect(self) -> None:
        """重连"""
        self.state = MCPConnectionState.PENDING
        delay = 1.0

        for attempt in range(5):
            try:
                await self.connect()
                return
            except Exception:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)  # 指数退避，最大 30s

        self.state = MCPConnectionState.FAILED

    async def disconnect(self) -> None:
        """断开连接"""
        if self._process:
            self._process.terminate()
            await self._process.wait()
            self._process = None
        self.state = MCPConnectionState.DISABLED


# =============================================================================
# 4. Analytics 服务 - 无环设计
# =============================================================================

@dataclass
class QueuedEvent:
    """队列事件"""
    name: str
    metadata: Optional[Dict[str, Any]]
    timestamp: float


class AnalyticsService:
    """
    Analytics 服务 - 无环设计

    等价于 TypeScript 的 Analytics 服务

    关键设计：事件队列模式，避免循环依赖
    """

    _instance: Optional['AnalyticsService'] = None
    _event_queue: List[QueuedEvent] = []
    _sink: Optional['AnalyticsSink'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def attach_sink(cls, sink: 'AnalyticsSink') -> None:
        """
        附加 sink

        等价于 attachAnalyticsSink()
        """
        cls._sink = sink

        # 队列事件出队
        while cls._event_queue:
            event = cls._event_queue.pop(0)
            cls._sink.log_event(event.name, event.metadata)

    @classmethod
    def log_event(
        cls,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录事件

        等价于 logEvent()
        """
        event = QueuedEvent(
            name=name,
            metadata=metadata,
            timestamp=time.time()
        )

        if cls._sink:
            cls._sink.log_event(name, metadata)
        else:
            # 队列，稍后处理
            cls._event_queue.append(event)


class AnalyticsSink(ABC):
    """Analytics Sink 基类"""

    @abstractmethod
    def log_event(self, name: str, metadata: Optional[Dict[str, Any]]) -> None:
        pass


class GrowthBookSDK:
    """
    GrowthBook SDK Wrapper

    等价于 TypeScript 的 GrowthBook SDK
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._features: Dict[str, Any] = {}
        self._user_attributes: Dict[str, Any] = {}
        self._cache: Dict[str, Any] = {}

    async def initialize(self) -> None:
        """初始化"""
        # 从缓存加载
        cached = self._load_cached_features()
        if cached:
            self._features = cached

        # 从远程获取
        remote = await self._fetch_remote_features()
        self._features.update(remote)

        # 保存缓存
        self._save_cached_features(self._features)

        # 启动定期刷新
        asyncio.create_task(self._start_periodic_refresh())

    def get_feature_value(
        self,
        feature_name: str,
        default_value: Any = None
    ) -> Any:
        """
        获取特性值 (可能返回陈旧值)

        等价于 getFeatureValue_CACHED_MAY_BE_STALE()
        """
        feature = self._features.get(feature_name)

        if not feature:
            return default_value

        # 评估条件
        if feature.get('condition'):
            if not self._evaluate_condition(
                feature['condition'],
                self._user_attributes
            ):
                return default_value

        return feature.get('value', default_value)

    def check_gate(self, gate_name: str) -> bool:
        """
        检查 gate (同步快速路径)

        等价于 checkGate_CACHED_OR_BLOCKING()
        """
        gate_value = self._features.get(f'__gate__{gate_name}')

        if gate_value == True:
            return True  # 快速路径

        # 需要检查
        return False

    def _evaluate_condition(
        self,
        condition: Dict[str, Any],
        attributes: Dict[str, Any]
    ) -> bool:
        """评估条件"""
        # 简化实现
        return True

    async def _fetch_remote_features(self) -> Dict[str, Any]:
        """从远程获取特性"""
        # 简化实现
        return {}

    def _load_cached_features(self) -> Optional[Dict[str, Any]]:
        """加载缓存的特性"""
        # 简化实现
        return None

    def _save_cached_features(self, features: Dict[str, Any]) -> None:
        """保存特性缓存"""
        # 简化实现
        pass

    async def _start_periodic_refresh(self) -> None:
        """启动定期刷新"""
        while True:
            await asyncio.sleep(1200)  # 20 分钟
            await self.initialize()


# =============================================================================
# 5. Token 估算
# =============================================================================

class TokenEstimator:
    """
    Token 估算器

    等价于 TypeScript 的 tokenEstimation.ts
    """

    @staticmethod
    def rough_estimate(content: str) -> int:
        """
        粗略估算

        4 bytes ≈ 1 token
        """
        return len(content.encode('utf-8')) // 4

    @staticmethod
    def estimate_message(message: 'Message') -> int:
        """估算消息的 token 数"""
        total = 0

        for block in message.content:
            if block.type == 'text':
                total += TokenEstimator.rough_estimate(block.text or '')
            elif block.type == 'tool_use':
                total += TokenEstimator.rough_estimate(block.name or '')
                total += TokenEstimator.rough_estimate(
                    json.dumps(block.input or {})
                )
            elif block.type == 'tool_result':
                if isinstance(block.content, str):
                    total += TokenEstimator.rough_estimate(block.content)

        return total + 10  # overhead

    @staticmethod
    async def count_tokens_with_api(content: str) -> int:
        """使用 API 计数"""
        # 简化实现
        return TokenEstimator.rough_estimate(content)


# =============================================================================
# 6. 示例用法
# =============================================================================

async def main():
    """示例用法"""

    # 1. API 客户端
    config = ClientConfig(
        provider=APIProvider.DIRECT,
        api_key="sk-...",
        base_url="https://api.anthropic.com"
    )

    client = APIFactory.create(config)
    print(f"Created client: {type(client).__name__}")

    # 2. MCP 客户端
    mcp_config = MCPServerConfig(
        id="local",
        name="Local MCP",
        transport=MCPTransportType.STDIO,
        command="npx",
        args=["-y", "@anthropic/mcp-server"]
    )

    mcp_client = MCPClient(mcp_config)
    print(f"Created MCP client: {mcp_client.config.name}")

    # 3. Analytics
    AnalyticsService.log_event("test_event", {"key": "value"})

    sink = GrowthBookSDK({"apiHost": "", "clientKey": ""})
    AnalyticsService.attach_sink(sink)

    # 4. Token 估算
    text = "Hello, world!"
    tokens = TokenEstimator.rough_estimate(text)
    print(f"Token estimate for '{text}': {tokens}")


@dataclass
class Message:
    """消息"""
    role: str
    content: List['ContentBlock']


@dataclass
class ContentBlock:
    """内容块"""
    type: str
    text: Optional[str] = None
    name: Optional[str] = None
    input: Optional[Dict] = None
    content: Optional[Any] = None


@dataclass
class StreamEvent:
    """流式事件"""
    type: str
    data: Dict[str, Any]


if __name__ == "__main__":
    asyncio.run(main())
