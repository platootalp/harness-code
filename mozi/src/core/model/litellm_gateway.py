"""Litellm 统一网关适配器。

替代原有的 OpenAIAdapter 和 AnthropicAdapter，
通过 litellm 提供统一的模型调用接口。
"""

from __future__ import annotations

from typing import Any

import litellm
from litellm import (  # type: ignore[attr-defined]
    AuthenticationError as LiteLLMAuthError,
)
from litellm import (  # type: ignore[attr-defined]
    InvalidRequestError as LiteLLMInvalidRequestError,
)
from litellm import (  # type: ignore[attr-defined]
    RateLimitError as LiteLLMRateLimitError,
)

from mozi.core.model.adapter import (
    Message,
    ModelAdapter,
    ModelInfo,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    ToolCall,
)
from mozi.core.model.errors import (
    AuthenticationError,
    InvalidRequestError,
    ModelInvocationError,
    RateLimitError,
    ResponseParseError,
)


class LitellmGateway(ModelAdapter):
    """Litellm 统一网关。

    支持 OpenAI、Anthropic、Azure、Cohere 等 100+ Provider。
    统一处理请求/响应格式转换和错误映射。
    """

    def __init__(
        self,
        api_key: str,
        provider: ModelProvider,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """初始化 Litellm 网关。

        Args:
            api_key: API 密钥。
            provider: 模型 Provider。
            base_url: 可选的自定义 base URL。
            timeout: 请求超时时间（秒）。
        """
        self._api_key = api_key
        self._provider = provider
        self._base_url = base_url
        self._timeout = timeout

        # 配置 litellm
        litellm.drop_params = True

    @property
    def provider(self) -> ModelProvider:
        """返回模型 Provider。"""
        return self._provider

    @property
    def supported_models(self) -> list[ModelInfo]:
        """返回支持的模型列表。"""
        return SUPPORTED_MODELS.get(self._provider, [])

    def get_model_info(self, model_name: str) -> ModelInfo | None:
        """获取模型信息。

        Args:
            model_name: 模型名称。

        Returns:
            ModelInfo if found, None otherwise.
        """
        for model in self.supported_models:
            if model.name == model_name:
                return model
        return None

    def validate_request(self, request: ModelRequest) -> None:
        """验证模型请求。

        Args:
            request: 模型请求。

        Raises:
            InvalidRequestError: If the request is invalid.
        """
        if not request.model:
            raise InvalidRequestError("Model name is required")

        if not request.messages:
            raise InvalidRequestError("At least one message is required")

        if request.temperature < 0.0 or request.temperature > 2.0:
            raise InvalidRequestError("Temperature must be between 0.0 and 2.0")

        if request.top_p is not None and (request.top_p < 0.0 or request.top_p > 1.0):
            raise InvalidRequestError("top_p must be between 0.0 and 1.0")

        if request.max_tokens is not None and request.max_tokens <= 0:
            raise InvalidRequestError("max_tokens must be positive")

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """调用模型。

        Args:
            request: 模型请求。

        Returns:
            ModelResponse.

        Raises:
            InvalidRequestError: If the request is invalid.
            AuthenticationError: If authentication fails.
            RateLimitError: If rate limit is exceeded.
            ModelInvocationError: If invocation fails.
            ResponseParseError: If response parsing fails.
        """
        self.validate_request(request)

        try:
            response = await litellm.acompletion(
                model=request.model,
                messages=self._format_messages(request.messages, request.system_prompt),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                stop=request.stop_sequences,
                tools=request.tools,
                timeout=self._timeout,
                api_key=self._api_key,
                base_url=self._base_url,
            )
            return self._parse_response(response, request.model)

        except LiteLLMAuthError as e:
            raise AuthenticationError(f"Authentication failed: {e}") from e
        except LiteLLMRateLimitError as e:
            raise RateLimitError(f"Rate limit exceeded: {e}") from e
        except LiteLLMInvalidRequestError as e:
            raise InvalidRequestError(f"Invalid request: {e}") from e
        except Exception as e:
            raise ModelInvocationError(f"Model invocation failed: {e}") from e

    def _format_messages(
        self,
        messages: list[Message],
        system_prompt: str | None,
    ) -> list[dict[str, Any]]:
        """格式化消息为 litellm 格式。

        Args:
            messages: 消息列表。
            system_prompt: 系统提示词。

        Returns:
            格式化后的消息列表。
        """
        result: list[dict[str, Any]] = []

        if system_prompt:
            result.append({"role": "system", "content": system_prompt})

        for msg in messages:
            formatted: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }

            if msg.name:
                formatted["name"] = msg.name

            if msg.tool_calls:
                formatted["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]

            if msg.tool_call_id:
                formatted["tool_call_id"] = msg.tool_call_id

            result.append(formatted)

        return result

    def _parse_response(
        self,
        response: Any,
        model: str,
    ) -> ModelResponse:
        """解析 litellm 响应。

        Args:
            response: litellm 响应对象。
            model: 模型名称。

        Returns:
            ModelResponse.

        Raises:
            ResponseParseError: If response parsing fails.
        """
        try:
            choice = response.choices[0]
            message = choice.message

            # 提取文本内容
            content_text = message.content or ""

            # 提取工具调用
            tool_calls: list[ToolCall] = []
            if message.tool_calls:
                for raw_tc in message.tool_calls:
                    function = raw_tc.function
                    tool_calls.append(
                        ToolCall(
                            id=raw_tc.id,
                            name=function.name,
                            arguments=function.arguments,
                        )
                    )

            # 提取用量
            usage = ModelUsage(
                input_tokens=(
                    response.usage.prompt_tokens
                    if hasattr(response.usage, "prompt_tokens")
                    else 0
                ),
                output_tokens=(
                    response.usage.completion_tokens
                    if hasattr(response.usage, "completion_tokens")
                    else 0
                ),
                total_tokens=(
                    response.usage.total_tokens
                    if hasattr(response.usage, "total_tokens")
                    else 0
                ),
            )

            return ModelResponse(
                content=content_text,
                model=model,
                stop_reason=choice.finish_reason,
                tool_calls=tool_calls if tool_calls else None,
                usage=usage,
                metadata={"response_id": response.id},
            )

        except Exception as e:
            raise ResponseParseError(f"Failed to parse response: {e}") from e


# 支持的模型配置
SUPPORTED_MODELS: dict[ModelProvider, list[ModelInfo]] = {
    ModelProvider.ANTHROPIC: [
        ModelInfo(
            name="claude-3-5-sonnet-latest",
            provider=ModelProvider.ANTHROPIC,
            display_name="Claude 3.5 Sonnet",
            context_window=200000,
            tier="balanced",
            supports_tools=True,
        ),
        ModelInfo(
            name="claude-3-5-haiku-latest",
            provider=ModelProvider.ANTHROPIC,
            display_name="Claude 3.5 Haiku",
            context_window=200000,
            tier="fast",
            supports_tools=True,
        ),
        ModelInfo(
            name="claude-3-opus-latest",
            provider=ModelProvider.ANTHROPIC,
            display_name="Claude 3 Opus",
            context_window=200000,
            tier="powerful",
            supports_tools=True,
        ),
    ],
    ModelProvider.OPENAI: [
        ModelInfo(
            name="gpt-4o",
            provider=ModelProvider.OPENAI,
            display_name="GPT-4o",
            context_window=128000,
            tier="balanced",
            supports_tools=True,
            supports_vision=True,
        ),
        ModelInfo(
            name="gpt-4o-mini",
            provider=ModelProvider.OPENAI,
            display_name="GPT-4o Mini",
            context_window=128000,
            tier="fast",
            supports_tools=True,
        ),
        ModelInfo(
            name="gpt-4-turbo",
            provider=ModelProvider.OPENAI,
            display_name="GPT-4 Turbo",
            context_window=128000,
            tier="powerful",
            supports_tools=True,
        ),
        ModelInfo(
            name="gpt-4",
            provider=ModelProvider.OPENAI,
            display_name="GPT-4",
            context_window=128000,
            tier="powerful",
            supports_tools=True,
        ),
        ModelInfo(
            name="gpt-3.5-turbo",
            provider=ModelProvider.OPENAI,
            display_name="GPT-3.5 Turbo",
            context_window=16385,
            tier="fast",
            supports_tools=True,
        ),
    ],
}
