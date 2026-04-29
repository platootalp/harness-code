"""
查询引擎 Python 实现

展示 Claude Code 查询引擎的核心设计模式在 Python 中的实现：
- AsyncGenerator 模式
- 上下文压缩管道
- 流式响应处理
- 重试机制
"""

from __future__ import annotations

import asyncio
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
    TypeVar,
    Generic,
    Awaitable,
)
from dataclasses import dataclass, field
import time
import json


# =============================================================================
# 1. 消息类型
# =============================================================================

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ContentBlock:
    """内容块"""
    type: str  # 'text', 'tool_use', 'tool_result', 'thinking'
    text: Optional[str] = None
    name: Optional[str] = None
    id: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    content: Optional[Any] = None


@dataclass
class Message:
    """消息"""
    role: MessageRole
    content: List[ContentBlock] = field(default_factory=list)


@dataclass
class Usage:
    """Token 使用统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


# =============================================================================
# 2. Stream Event 类型
# =============================================================================

@dataclass
class StreamEvent:
    """流式事件"""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageStartEvent(StreamEvent):
    """消息开始"""
    type: str = "message_start"
    message: Optional[Message] = None


@dataclass
class ContentBlockEvent(StreamEvent):
    """内容块"""
    type: str = "content_block"
    content: Optional[ContentBlock] = None


@dataclass
class MessageDeltaEvent(StreamEvent):
    """消息增量"""
    type: str = "message_delta"
    delta: Optional[Dict[str, Any]] = None
    usage: Optional[Usage] = None


@dataclass
class MessageStopEvent(StreamEvent):
    """消息结束"""
    type: str = "message_stop"


# =============================================================================
# 3. SDK 消息类型
# =============================================================================

@dataclass
class SDKMessage:
    """SDK 消息"""
    type: str
    content: Optional[List[ContentBlock]] = None
    id: Optional[str] = None
    uuid: Optional[str] = None


# =============================================================================
# 4. 查询状态
# =============================================================================

@dataclass
class QueryState:
    """查询状态"""
    messages: List[Message]
    tool_use_context: 'ToolUseContext'
    turn_count: int = 0
    total_usage: Usage = field(default_factory=Usage)
    last_stop_reason: Optional[str] = None
    auto_compact_tracking: Optional[Dict[str, Any]] = None
    max_output_tokens_recovery_count: int = 0
    has_attempted_reactive_compact: bool = False
    max_output_tokens_override: Optional[int] = None
    stop_hook_active: bool = False
    transition: Optional[str] = None


# =============================================================================
# 5. 继续原因
# =============================================================================

class ContinueReason(str, Enum):
    """查询继续原因"""
    COLLAPSE_DRAIN_RETRY = "collapse_drain_retry"
    REACTIVE_COMPACT_RETRY = "reactive_compact_retry"
    MAX_OUTPUT_TOKENS_ESCALATE = "max_output_tokens_escalate"
    MAX_OUTPUT_TOKENS_RECOVERY = "max_output_tokens_recovery"
    STOP_HOOK_BLOCKING = "stop_hook_blocking"
    TOKEN_BUDGET_CONTINUATION = "token_budget_continuation"
    NEXT_TURN = "next_turn"


# =============================================================================
# 6. 上下文压缩
# =============================================================================

class CompactStrategy(ABC):
    """压缩策略基类"""

    @abstractmethod
    async def compact(
        self,
        messages: List[Message],
        context: 'CompactContext'
    ) -> 'CompactResult':
        pass


@dataclass
class CompactContext:
    """压缩上下文"""
    compactable_count: int = 0
    time_since_last_assistant: float = 0
    use_cache_edits: bool = True
    cache_edits_threshold: int = 10
    token_budget: int = 100000


@dataclass
class CompactResult:
    """压缩结果"""
    messages: List[Message]
    cleared_tool_ids: List[str] = field(default_factory=list)
    cache_edits: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None


class MicroCompact(CompactStrategy):
    """微压缩 - Level 1"""

    # 可压缩的工具类型
    COMPACTABLE_TOOLS = {
        'Read', 'Bash', 'Grep', 'Glob',
        'WebSearch', 'WebFetch', 'FileEdit', 'FileWrite'
    }

    async def compact(
        self,
        messages: List[Message],
        context: CompactContext
    ) -> CompactResult:
        result: List[Message] = []
        cleared_ids: List[str] = []

        for msg in messages:
            if msg.role != MessageRole.ASSISTANT:
                result.append(msg)
                continue

            # 处理 assistant 消息中的工具
            new_content: List[ContentBlock] = []

            for block in msg.content:
                if block.type == 'tool_use':
                    if self._should_compact(block.name, context):
                        # 标记为已清除
                        new_content.append(ContentBlock(
                            type='tool_use',
                            id=block.id,
                            name=block.name,
                            input={
                                **block.input,
                                '_cleared': True,
                                '_cleared_content': '[Old tool result content cleared]'
                            }
                        ))
                        cleared_ids.append(block.id)
                    else:
                        new_content.append(block)
                else:
                    new_content.append(block)

            result.append(Message(role=msg.role, content=new_content))

        return CompactResult(
            messages=result,
            cleared_tool_ids=cleared_ids
        )

    def _should_compact(self, tool_name: str, context: CompactContext) -> bool:
        """检查是否应该压缩"""
        if tool_name not in self.COMPACTABLE_TOOLS:
            return False

        if context.use_cache_edits:
            return context.compactable_count > context.cache_edits_threshold

        return context.time_since_last_assistant > 300  # 5 分钟


class FullCompact(CompactStrategy):
    """完整压缩 - Level 2"""

    def __init__(self, summary_model: str = "sonnet"):
        self.summary_model = summary_model

    async def compact(
        self,
        messages: List[Message],
        context: CompactContext
    ) -> CompactResult:
        # 1. 准备压缩提示
        compact_prompt = self._build_compact_prompt(messages)

        # 2. 调用模型生成摘要 (简化实现)
        summary = await self._generate_summary(compact_prompt)

        # 3. 创建压缩边界消息
        boundary = Message(
            role=MessageRole.SYSTEM,
            content=[ContentBlock(
                type='text',
                text=f"[Previous conversation summarized. {summary}]"
            )]
        )

        # 4. 生成后压缩附件
        attachments = await self._generate_post_compact_attachments(context)

        return CompactResult(
            messages=[boundary, *attachments],
            summary=summary
        )

    def _build_compact_prompt(self, messages: List[Message]) -> str:
        """构建压缩提示"""
        # 简化实现
        total_content = ""
        for msg in messages[-10:]:  # 只用最后 10 条
            for block in msg.content:
                if block.type == 'text' and block.text:
                    total_content += block.text[:500] + "\n"

        return f"Summarize this conversation briefly:\n\n{total_content[:2000]}"

    async def _generate_summary(self, prompt: str) -> str:
        """调用模型生成摘要"""
        # 简化实现 - 实际会调用 API
        await asyncio.sleep(0.1)
        return f"Summary of conversation (truncated for brevity)"

    async def _generate_post_compact_attachments(
        self,
        context: CompactContext
    ) -> List[Message]:
        """生成后压缩附件"""
        # 简化实现
        return []


# =============================================================================
# 6. 压缩管道
# =============================================================================

class CompactPipeline:
    """上下文压缩管道"""

    def __init__(
        self,
        micro_compact: Optional[MicroCompact] = None,
        full_compact: Optional[FullCompact] = None
    ):
        self.micro_compact = micro_compact or MicroCompact()
        self.full_compact = full_compact or FullCompact()

    async def run(
        self,
        state: QueryState,
        options: Dict[str, Any]
    ) -> QueryState:
        """
        运行压缩管道

        等价于 TypeScript 的 runCompactPipeline()
        """
        context = CompactContext(
            compactable_count=len(state.messages),
            time_since_last_assistant=self._get_time_since_last_assistant(state)
        )

        # Level 1: 微压缩
        if options.get('use_micro_compact', True):
            result = await self.micro_compact.compact(state.messages, context)
            state.messages = result.messages

        # Level 2: 完整压缩 (仅在需要时)
        if options.get('use_full_compact', False):
            result = await self.full_compact.compact(state.messages, context)
            state.messages = result.messages

        return state

    def _get_time_since_last_assistant(self, state: QueryState) -> float:
        """获取距离上次 assistant 消息的时间"""
        # 简化实现
        return 0.0


# =============================================================================
# 7. API 调用
# =============================================================================

class APIClient(ABC):
    """API 客户端基类"""

    @abstractmethod
    async def query_with_streaming(
        self,
        request: 'ModelRequest'
    ) -> AsyncGenerator[StreamEvent, None]:
        """流式查询"""
        pass


@dataclass
class ModelRequest:
    """模型请求"""
    model: str
    messages: List[Message]
    system: Optional[List[ContentBlock]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = True


class SimpleAPIClient(APIClient):
    """简化 API 客户端 - 用于演示"""

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key
        self.base_url = base_url

    async def query_with_streaming(
        self,
        request: ModelRequest
    ) -> AsyncGenerator[StreamEvent, None]:
        """模拟流式响应"""
        # 模拟流式响应
        yield MessageStartEvent(
            type="message_start",
            message=Message(role=MessageRole.ASSISTANT, content=[])
        )

        # 模拟内容块
        for i, content in enumerate(["Hello", ", ", "world", "!"]):
            yield ContentBlockEvent(
                type="content_block",
                content=ContentBlock(type="text", text=content)
            )
            await asyncio.sleep(0.05)

        yield MessageDeltaEvent(
            type="message_delta",
            delta={"stop_reason": "end_turn"},
            usage=Usage(input_tokens=10, output_tokens=5, total_tokens=15)
        )

        yield MessageStopEvent(type="message_stop")


# =============================================================================
# 8. 查询引擎
# =============================================================================

class QueryEngine:
    """
    查询引擎

    等价于 TypeScript 的 QueryEngine 类
    """

    def __init__(
        self,
        config: 'QueryEngineConfig',
        api_client: APIClient
    ):
        self.config = config
        self.api_client = api_client
        self.state: Optional[QueryState] = None
        self.abort_controller: Optional[asyncio.Event] = None

    async def submit_message(
        self,
        prompt: str,
        options: Dict[str, Any]
    ) -> AsyncGenerator[SDKMessage, None]:
        """
        提交消息

        等价于 TypeScript 的 submitMessage()
        """
        # 初始化
        self.abort_controller = asyncio.Event()

        # 构建消息
        user_message = Message(
            role=MessageRole.USER,
            content=[ContentBlock(type="text", text=prompt)]
        )

        # 初始化状态
        self.state = QueryState(
            messages=[user_message],
            tool_use_context=options.get('tool_use_context')
        )

        # 预循环设置
        await self._pre_loop_setup(options)

        # 查询循环
        async for sdk_msg in self._query_loop(options):
            yield sdk_msg

    async def _pre_loop_setup(self, options: Dict[str, Any]) -> None:
        """预循环设置"""
        # 1. 初始化压缩追踪
        self.state.auto_compact_tracking = {
            'last_compact_at': time.time()
        }

    async def _query_loop(
        self,
        options: Dict[str, Any]
    ) -> AsyncGenerator[SDKMessage, None]:
        """查询循环"""
        max_turns = options.get('max_turns', 100)

        while self.state.turn_count < max_turns:
            # 检查中止
            if self.abort_controller and self.abort_controller.is_set():
                break

            # 运行压缩管道
            pipeline = CompactPipeline()
            self.state = await pipeline.run(self.state, options)

            # API 调用
            try:
                async for event in self._call_api(options):
                    # 处理事件
                    sdk_msg = self._process_stream_event(event)
                    if sdk_msg:
                        yield sdk_msg

                    # 检查是否继续
                    if self._should_continue(event):
                        self.state.turn_count += 1
                        continue

            except Exception as e:
                # 错误处理
                error_msg = await self._handle_error(e, options)
                if error_msg:
                    yield error_msg
                break

            # 正常结束
            break

    async def _call_api(
        self,
        options: Dict[str, Any]
    ) -> AsyncGenerator[StreamEvent, None]:
        """调用 API"""
        request = ModelRequest(
            model=options.get('model', 'claude-sonnet'),
            messages=self.state.messages,
            max_tokens=self.state.max_output_tokens_override or 4096,
            stream=True
        )

        async for event in self.api_client.query_with_streaming(request):
            yield event

    def _process_stream_event(self, event: StreamEvent) -> Optional[SDKMessage]:
        """处理流式事件"""
        if event.type == "message_start":
            return SDKMessage(
                type="assistant",
                content=[]
            )

        elif event.type == "content_block":
            if isinstance(event, ContentBlockEvent) and event.content:
                return SDKMessage(
                    type="assistant",
                    content=[event.content]
                )

        elif event.type == "message_delta":
            if isinstance(event, MessageDeltaEvent) and event.delta:
                self.state.last_stop_reason = event.delta.get('stop_reason')

        return None

    def _should_continue(self, event: StreamEvent) -> bool:
        """检查是否应该继续循环"""
        if isinstance(event, MessageDeltaEvent) and event.delta:
            reason = event.delta.get('stop_reason')
            if reason == 'tool_use':
                return True
            if reason == 'end_turn':
                return False

        return False

    async def _handle_error(
        self,
        error: Exception,
        options: Dict[str, Any]
    ) -> Optional[SDKMessage]:
        """处理错误"""
        if isinstance(error, PromptTooLongError):
            # 尝试压缩恢复
            if self.state.has_attempted_reactive_compact:
                return SDKMessage(
                    type="error",
                    content=[ContentBlock(
                        type="text",
                        text=f"Context too long: {str(error)}"
                    )]
                )

            self.state.has_attempted_reactive_compact = True
            # 重新进入循环进行压缩
            return None

        if isinstance(error, MaxOutputTokensError):
            # 尝试恢复
            if self.state.max_output_tokens_recovery_count < 3:
                self.state.max_output_tokens_recovery_count += 1
                return None

        return SDKMessage(
            type="error",
            content=[ContentBlock(type="text", text=str(error))]
        )

    def abort(self) -> None:
        """中止查询"""
        if self.abort_controller:
            self.abort_controller.set()


# =============================================================================
# 9. 错误类型
# =============================================================================

class QueryError(Exception):
    """查询错误基类"""
    pass


class PromptTooLongError(QueryError):
    """Prompt 太长"""
    pass


class MaxOutputTokensError(QueryError):
    """Output tokens 超出限制"""
    pass


class ModelFallbackError(QueryError):
    """模型回退触发"""
    pass


# =============================================================================
# 10. Token 估算
# =============================================================================

class TokenEstimator:
    """Token 估算器"""

    @staticmethod
    def rough_estimate(content: str) -> int:
        """粗略估算 - 4 bytes ≈ 1 token"""
        return len(content.encode('utf-8')) // 4

    @staticmethod
    def estimate_message(message: Message) -> int:
        """估算单条消息的 token 数"""
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

        # overhead
        total += 10

        return total


# =============================================================================
# 11. 示例用法
# =============================================================================

async def main():
    """示例用法"""

    # 创建 API 客户端
    api_client = SimpleAPIClient()

    # 创建配置
    config = QueryEngineConfig(
        max_turns=100,
        max_budget_usd=10.0,
        default_model="claude-sonnet"
    )

    # 创建引擎
    engine = QueryEngine(config, api_client)

    # 提交消息
    print("Submitting message...")

    async for msg in engine.submit_message(
        "Hello, how are you?",
        options={
            'model': 'claude-sonnet',
            'max_turns': 10
        }
    ):
        print(f"Received: type={msg.type}, content={msg.content}")

    print("Done!")


@dataclass
class QueryEngineConfig:
    """查询引擎配置"""
    max_turns: int = 100
    max_budget_usd: Optional[float] = None
    default_model: str = "claude-sonnet"


@dataclass
class ToolUseContext:
    """工具上下文"""
    pass


if __name__ == "__main__":
    asyncio.run(main())
