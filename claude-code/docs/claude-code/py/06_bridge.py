"""
桥接系统 Python 实现

展示 Claude Code 桥接系统的核心设计模式在 Python 中的实现：
- 传输层抽象
- 消息协议
- Session Runner
- IDE 集成
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
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
)
from collections import deque


# =============================================================================
# 1. 消息类型
# =============================================================================

class MessageType(str, Enum):
    """消息类型"""
    # 出站消息 (CLI → Server)
    ASSISTANT = "assistant"
    RESULT = "result"
    USER = "user"
    CONTROL_RESPONSE = "control_response"
    CONTROL_CANCEL_REQUEST = "control_cancel_request"

    # 入站消息 (Server → CLI)
    USER_MESSAGE = "user"
    CONTROL_REQUEST = "control_request"


class ControlSubtype(str, Enum):
    """控制请求子类型"""
    INITIALIZE = "initialize"
    SET_MODEL = "set_model"
    SET_MAX_THINKING_TOKENS = "set_max_thinking_tokens"
    SET_PERMISSION_MODE = "set_permission_mode"
    CAN_USE_TOOL = "can_use_tool"
    INTERRUPT = "interrupt"


@dataclass
class OutboundMessage:
    """出站消息"""
    type: str
    content: Optional[List[Dict]] = None
    uuid: Optional[str] = None
    subtype: Optional[str] = None
    request_id: Optional[str] = None
    result: Optional[Any] = None


@dataclass
class InboundMessage:
    """入站消息"""
    type: str
    content: Optional[List[Dict]] = None
    uuid: Optional[str] = None
    subtype: Optional[str] = None
    request_id: Optional[str] = None
    params: Optional[Dict] = None


# =============================================================================
# 2. UUID 去重 - BoundedUUIDSet
# =============================================================================

class BoundedUUIDSet:
    """
    Bounded UUID Set - FIFO 环缓冲

    等价于 TypeScript 的 BoundedUUIDSet

    用于消息去重，防止重复投递或回声
    """

    def __init__(self, capacity: int = 2000):
        self._capacity = capacity
        self._set: Set[str] = set()
        self._queue: deque = deque(maxlen=capacity)

    def add(self, uuid: str) -> None:
        """添加 UUID"""
        if len(self._set) >= self._capacity:
            # 移除最老的
            oldest = self._queue.popleft()
            self._set.discard(oldest)

        self._set.add(uuid)
        self._queue.append(uuid)

    def has(self, uuid: str) -> bool:
        """检查 UUID 是否存在"""
        return uuid in self._set

    def clear(self) -> None:
        """清空"""
        self._set.clear()
        self._queue.clear()


# =============================================================================
# 3. 传输层抽象
# =============================================================================

class Transport(ABC):
    """传输层基类"""

    @abstractmethod
    async def connect(self) -> None:
        """连接"""
        pass

    @abstractmethod
    async def send(self, message: OutboundMessage) -> None:
        """发送消息"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭"""
        pass


class HybridTransport(Transport):
    """
    Hybrid Transport (v1)

    WebSocket 读取 + HTTP POST 写入

    等价于 TypeScript 的 HybridTransport
    """

    def __init__(
        self,
        ws_url: str,
        post_url: str,
        auth: Dict[str, str]
    ):
        self._ws_url = ws_url
        self._post_url = post_url
        self._auth = auth
        self._ws: Optional[Any] = None
        self._pending_writes: List[OutboundMessage] = []
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(self) -> None:
        """连接 WebSocket"""
        import aiohttp

        self._running = True

        # WebSocket 连接
        self._ws = await aiohttp.ClientSession().ws_connect(self._ws_url)

        # 启动 flush 循环
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def send(self, message: OutboundMessage) -> None:
        """发送消息到待写入队列"""
        self._pending_writes.append(message)

    async def _flush_loop(self) -> None:
        """定期 flush 批量写入"""
        while self._running:
            await asyncio.sleep(0.1)  # 100ms 批量

            if self._pending_writes:
                await self._flush_write_batch()

    async def _flush_write_batch(self) -> None:
        """批量写入"""
        if not self._pending_writes:
            return

        batch = self._pending_writes.copy()
        self._pending_writes.clear()

        import aiohttp

        async with aiohttp.ClientSession() as session:
            await session.post(
                self._post_url,
                json=[self._message_to_dict(m) for m in batch],
                headers=self._auth
            )

    async def close(self) -> None:
        """关闭"""
        self._running = False

        if self._ws:
            await self._ws.close()
            self._ws = None

    def _message_to_dict(self, message: OutboundMessage) -> Dict:
        """消息转字典"""
        return {
            k: v for k, v in {
                'type': message.type,
                'content': message.content,
                'uuid': message.uuid,
                'subtype': message.subtype,
                'request_id': message.request_id,
                'result': message.result,
            }.items() if v is not None
        }


class SSETransport(Transport):
    """
    SSE Transport (v2)

    SSE 读取 + HTTP POST 写入

    等价于 TypeScript 的 SSETransport
    """

    def __init__(
        self,
        session_url: str,
        ingress_token: str,
        epoch: int
    ):
        self._session_url = session_url
        self._ingress_token = ingress_token
        self._epoch = epoch
        self._event_source: Optional[Any] = None
        self._last_sequence_num: int = 0
        self._next_sequence_num: int = 0

    async def connect(self) -> None:
        """连接 SSE 流"""
        import aiohttp

        # SSE endpoint
        sse_url = f"{self._session_url}/events/stream?epoch={self._epoch}"

        self._event_source = await aiohttp.ClientSession().get(
            sse_url,
            headers={'Authorization': f'Bearer {self._ingress_token}'}
        )

    async def send(self, message: OutboundMessage) -> None:
        """发送消息"""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self._session_url}/events",
                json={
                    'sequenceNum': self._next_sequence_num,
                    **self._message_to_dict(message)
                },
                headers={'Authorization': f'Bearer {self._ingress_token}'}
            )
            self._next_sequence_num += 1

    async def close(self) -> None:
        """关闭"""
        if self._event_source:
            self._event_source.close()
            self._event_source = None

    def _message_to_dict(self, message: OutboundMessage) -> Dict:
        """消息转字典"""
        return {
            k: v for k, v in {
                'type': message.type,
                'content': message.content,
                'uuid': message.uuid,
                'subtype': message.subtype,
                'request_id': message.request_id,
                'result': message.result,
            }.items() if v is not None
        }


# =============================================================================
# 4. Session Handle
# =============================================================================

@dataclass
class SessionActivity:
    """Session 活动"""
    type: str  # 'assistant', 'tool_use', 'result', 'error'
    tool_use_id: Optional[str] = None
    tool_name: Optional[str] = None
    content: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionHandle:
    """
    Session Handle

    等价于 TypeScript 的 SessionHandle
    """
    session_id: str
    done: asyncio.Future
    _kill_event: asyncio.Event = field(default_factory=asyncio.Event)
    _activities: deque = field(
        default_factory=lambda: deque(maxlen=10)
    )
    _last_stderr: deque = field(
        default_factory=lambda: deque(maxlen=10)
    )

    def kill(self) -> None:
        """发送 SIGTERM"""
        self._kill_event.set()

    def force_kill(self) -> None:
        """发送 SIGKILL"""
        self._kill_event.set()

    def write_stdin(self, data: str) -> None:
        """写入 stdin"""
        pass

    @property
    def activities(self) -> List[SessionActivity]:
        return list(self._activities)

    @property
    def last_stderr(self) -> List[str]:
        return list(self._last_stderr)


# =============================================================================
# 5. Session Runner
# =============================================================================

@dataclass
class SpawnOptions:
    """派生选项"""
    sdk_url: str
    session_id: str
    access_token: str
    cwd: str
    verbose: bool = False
    debug_file: Optional[str] = None
    permission_mode: Optional[str] = None
    use_ccr_v2: bool = False
    worker_epoch: Optional[int] = None


class SessionRunner:
    """
    Session Runner

    等价于 TypeScript 的 sessionRunner.ts
    """

    def __init__(self, options: SpawnOptions):
        self._options = options
        self._process: Optional[asyncio.subprocess.Process] = None

    async def spawn(self) -> SessionHandle:
        """派生子进程"""
        # 构建 CLI 参数
        args = [
            'claude',
            '--print',
            '--sdk-url', self._options.sdk_url,
            '--session-id', self._options.session_id,
            '--input-format', 'stream-json',
            '--output-format', 'stream-json',
            '--replay-user-messages',
        ]

        if self._options.verbose:
            args.append('--verbose')

        if self._options.debug_file:
            args.extend(['--debug-file', self._options.debug_file])

        if self._options.permission_mode:
            args.extend(['--permission-mode', self._options.permission_mode])

        # 环境变量
        env = {
            'CLAUDE_CODE_SESSION_ACCESS_TOKEN': self._options.access_token,
            'CLAUDE_CODE_ENVIRONMENT_KIND': 'bridge',
            'CLAUDE_CODE_POST_FOR_SESSION_INGRESS_V2': '1',
        }

        if self._options.use_ccr_v2:
            env['CLAUDE_CODE_USE_CCR_V2'] = '1'
            env['CLAUDE_CODE_WORKER_EPOCH'] = str(
                self._options.worker_epoch or 0
            )

        # 派生子进程
        self._process = await asyncio.create_subprocess_exec(
            *args,
            cwd=self._options.cwd,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # 创建 done future
        done_future: asyncio.Future = asyncio.get_event_loop().create_future()

        # 启动输出监听
        asyncio.create_task(self._listen_stdout(self._process))

        # 监听进程退出
        asyncio.create_task(self._handle_exit(self._process, done_future))

        return SessionHandle(
            session_id=self._options.session_id,
            done=done_future,
        )

    async def _listen_stdout(
        self,
        process: asyncio.subprocess.Process
    ) -> None:
        """监听 stdout"""
        if not process.stdout:
            return

        while True:
            line = await process.stdout.readline()
            if not line:
                break

            # 解析 NDJSON
            try:
                msg = json.loads(line.decode())
                activity = self._parse_activity(msg)
                if activity:
                    # 处理活动
                    pass
            except json.JSONDecodeError:
                pass

    async def _handle_exit(
        self,
        process: asyncio.subprocess.Process,
        done_future: asyncio.Future
    ) -> None:
        """处理进程退出"""
        code = await process.wait()

        if code == 0:
            done_future.set_result({'type': 'completed'})
        else:
            done_future.set_result({
                'type': 'failed',
                'error': f'Exit code {code}'
            })

    def _parse_activity(self, msg: Dict) -> Optional[SessionActivity]:
        """解析活动"""
        msg_type = msg.get('type')

        if msg_type == 'assistant':
            tool_uses = [
                c for c in msg.get('content', [])
                if c.get('type') == 'tool_use'
            ]
            return SessionActivity(
                type='tool_use' if tool_uses else 'assistant',
                tool_use_id=tool_uses[0].get('id') if tool_uses else None,
                tool_name=tool_uses[0].get('name') if tool_uses else None,
                content=msg.get('content', [{}])[0].get('text', '')[:100]
            )

        if msg_type == 'result':
            return SessionActivity(
                type='result' if msg.get('subtype') == 'success' else 'error',
                content=msg.get('content', [{}])[0].get('text', '')
            )

        return None


# =============================================================================
# 6. Bridge 配置
# =============================================================================

class SpawnMode(str, Enum):
    """派生模式"""
    SINGLE_SESSION = "single-session"
    WORKTREE = "worktree"
    SAME_DIR = "same-dir"


@dataclass
class BridgeConfig:
    """桥接配置"""
    dir: str
    machine_name: str
    branch: str
    git_repo_url: Optional[str] = None
    max_sessions: int = 1
    spawn_mode: SpawnMode = SpawnMode.SINGLE_SESSION
    bridge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    environment_id: Optional[str] = None
    worker_type: str = "claude-code-py"
    session_timeout_ms: Optional[int] = None
    reuse_environment_id: Optional[str] = None


# =============================================================================
# 7. 工作轮询
# =============================================================================

class WorkPollLoop:
    """
    工作轮询循环

    等价于 TypeScript 的 startWorkPollLoop()
    """

    def __init__(
        self,
        environment_id: str,
        transport: Transport,
        on_work_received: Callable[[Dict], None]
    ):
        self._environment_id = environment_id
        self._transport = transport
        self._on_work_received = on_work_received
        self._running = False
        self._poll_interval = 1.0

    async def start(self) -> None:
        """启动轮询"""
        self._running = True
        await self._poll()

    async def stop(self) -> None:
        """停止轮询"""
        self._running = False

    async def _poll(self) -> None:
        """轮询"""
        while self._running:
            try:
                work = await self._fetch_work()

                if work.get('items'):
                    # 有工作
                    self._poll_interval = 1.0

                    for item in work['items']:
                        # 确认工作
                        await self._ack_work(item['id'])
                        # 处理工作
                        self._on_work_received(item)

                else:
                    # 无工作，指数退避
                    self._poll_interval = min(
                        self._poll_interval * 1.5,
                        30.0  # 最大 30s
                    )

            except Exception as e:
                # 错误，指数退避
                self._poll_interval = min(self._poll_interval * 2, 30)

            await asyncio.sleep(self._poll_interval)

    async def _fetch_work(self) -> Dict:
        """获取工作"""
        # 简化实现
        return {'items': []}

    async def _ack_work(self, work_id: str) -> None:
        """确认工作"""
        pass


# =============================================================================
# 8. 入站消息处理
# =============================================================================

async def handle_ingress_message(
    data: str,
    recent_posted_uuids: BoundedUUIDSet,
    recent_inbound_uuids: BoundedUUIDSet,
    on_inbound_message: Optional[Callable[[InboundMessage], None]] = None,
    on_permission_response: Optional[Callable[[Dict], None]] = None
) -> None:
    """
    处理入站消息

    等价于 TypeScript 的 handleIngressMessage()
    """
    message: InboundMessage = json.loads(data)

    # 1. 去除回声
    if message.uuid and recent_posted_uuids.has(message.uuid):
        return  # 忽略

    # 2. 去除重传
    if message.uuid and recent_inbound_uuids.has(message.uuid):
        return  # 忽略

    # 3. 记录 UUID
    if message.uuid:
        recent_inbound_uuids.add(message.uuid)

    # 4. 分发消息
    if message.type == 'control_response':
        on_permission_response and on_permission_response(message)
    else:
        on_inbound_message and on_inbound_message(message)


# =============================================================================
# 9. 控制请求处理
# =============================================================================

async def handle_control_request(
    request: Dict,
    handlers: Dict[str, Callable]
) -> Dict:
    """
    处理控制请求

    等价于 TypeScript 的 handleControlRequest()
    """
    subtype = request.get('subtype')
    request_id = request.get('request_id')
    params = request.get('params', {})

    handler_map = {
        'initialize': handlers.get('on_initialize'),
        'set_model': handlers.get('on_set_model'),
        'set_permission_mode': handlers.get('on_set_permission_mode'),
        'can_use_tool': handlers.get('on_can_use_tool'),
        'interrupt': handlers.get('on_interrupt'),
        'set_max_thinking_tokens': handlers.get('on_set_max_thinking_tokens'),
    }

    handler = handler_map.get(subtype)

    if not handler:
        return {
            'type': 'control_response',
            'request_id': request_id,
            'result': {'error': f'Unknown subtype: {subtype}'}
        }

    try:
        result = await handler(request_id, params)
        return {
            'type': 'control_response',
            'request_id': request_id,
            'result': result
        }
    except Exception as e:
        return {
            'type': 'control_response',
            'request_id': request_id,
            'result': {'error': str(e)}
        }


# =============================================================================
# 10. 示例用法
# =============================================================================

async def main():
    """示例用法"""

    # 1. 创建 Bridge 配置
    config = BridgeConfig(
        dir="/path/to/project",
        machine_name="my-machine",
        branch="main",
        git_repo_url="https://github.com/example/repo",
        spawn_mode=SpawnMode.SINGLE_SESSION
    )

    print(f"Bridge ID: {config.bridge_id}")

    # 2. 创建 UUID 去重集合
    posted_uuids = BoundedUUIDSet(capacity=2000)
    inbound_uuids = BoundedUUIDSet(capacity=2000)

    # 测试去重
    test_uuid = "test-123"
    posted_uuids.add(test_uuid)
    print(f"UUID {test_uuid} in posted: {posted_uuids.has(test_uuid)}")
    print(f"UUID other in posted: {posted_uuids.has('other')}")

    # 3. 创建传输层
    transport = HybridTransport(
        ws_url="wss://api.anthropic.com/bridge",
        post_url="https://api.anthropic.com/bridge",
        auth={'Authorization': 'Bearer token'}
    )

    print(f"Transport: {type(transport).__name__}")

    # 4. 创建 Session Runner
    runner_options = SpawnOptions(
        sdk_url="https://api.anthropic.com",
        session_id=str(uuid.uuid4()),
        access_token="token",
        cwd="/path/to/project",
        verbose=True
    )

    runner = SessionRunner(runner_options)
    print(f"Session Runner created")


if __name__ == "__main__":
    asyncio.run(main())
