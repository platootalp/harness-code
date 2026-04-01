"""Anthropic Claude model adapter.

Adapter for Anthropic Claude series models.
"""

from __future__ import annotations

from typing import Any

import httpx

from mozi.core.model.adapter import (
    Message,
    MessageRole,
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


class AnthropicAdapter(ModelAdapter):
    """Adapter for Anthropic Claude models.

    Supports Claude 3.5, Claude 3, and Claude 2 series.
    """

    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    SUPPORTED_MODELS = [
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
        ModelInfo(
            name="claude-3-sonnet-latest",
            provider=ModelProvider.ANTHROPIC,
            display_name="Claude 3 Sonnet",
            context_window=200000,
            tier="balanced",
            supports_tools=True,
        ),
        ModelInfo(
            name="claude-3-haiku-latest",
            provider=ModelProvider.ANTHROPIC,
            display_name="Claude 3 Haiku",
            context_window=200000,
            tier="fast",
            supports_tools=True,
        ),
    ]

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialize Anthropic adapter.

        Args:
            api_key: Anthropic API key.
            base_url: Optional custom base URL.
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key
        self._base_url = base_url or self.BASE_URL
        self._timeout = timeout

    @property
    def provider(self) -> ModelProvider:
        """Return the model provider."""
        return ModelProvider.ANTHROPIC

    @property
    def supported_models(self) -> list[ModelInfo]:
        """Return list of supported models."""
        return self.SUPPORTED_MODELS

    def get_model_info(self, model_name: str) -> ModelInfo | None:
        """Get information about a specific model.

        Args:
            model_name: Name of the model.

        Returns:
            ModelInfo if found, None otherwise.
        """
        for model in self.SUPPORTED_MODELS:
            if model.name == model_name:
                return model
        return None

    def validate_request(self, request: ModelRequest) -> None:
        """Validate a model request.

        Args:
            request: The request to validate.

        Raises:
            InvalidRequestError: If the request is invalid.
        """
        if not request.model:
            raise InvalidRequestError("Model name is required")

        if not request.messages:
            raise InvalidRequestError("At least one message is required")

        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM and request.system_prompt:
                raise InvalidRequestError(
                    "Cannot specify both system message and system_prompt"
                )

        if request.temperature < 0.0 or request.temperature > 2.0:
            raise InvalidRequestError("Temperature must be between 0.0 and 2.0")

        if request.top_p is not None and (request.top_p < 0.0 or request.top_p > 1.0):
            raise InvalidRequestError("top_p must be between 0.0 and 1.0")

        if request.max_tokens is not None and request.max_tokens <= 0:
            raise InvalidRequestError("max_tokens must be positive")

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """Invoke the Anthropic model.

        Args:
            request: The model request.

        Returns:
            The model response.

        Raises:
            InvalidRequestError: If the request is invalid.
            AuthenticationError: If authentication fails.
            RateLimitError: If rate limit is exceeded.
            ModelInvocationError: If invocation fails.
            ResponseParseError: If response parsing fails.
        """
        self.validate_request(request)

        # Build request payload
        messages = self._format_messages(request.messages)
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
        }

        if request.system_prompt:
            payload["system"] = request.system_prompt

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        if request.top_p is not None:
            payload["top_p"] = request.top_p

        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences

        if request.tools:
            payload["tools"] = request.tools

        # Make request
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/messages",
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as e:
            raise ModelInvocationError(
                f"Request timed out after {self._timeout}s",
                model=request.model,
            ) from e
        except httpx.HTTPError as e:
            raise ModelInvocationError(
                f"HTTP error: {e}",
                model=request.model,
            ) from e

        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            raise RateLimitError(
                "Rate limit exceeded",
                retry_after=float(retry_after) if retry_after else None,
            )

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except Exception:
                error_msg = response.text

            raise ModelInvocationError(
                f"API error ({response.status_code}): {error_msg}",
                model=request.model,
            )

        try:
            return self._parse_response(response.json(), request.model)
        except Exception as e:
            raise ResponseParseError(f"Failed to parse response: {e}") from e

    def _format_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """Format messages for Anthropic API.

        Args:
            messages: List of Message objects.

        Returns:
            List of formatted message dicts.
        """
        result: list[dict[str, Any]] = []

        for msg in messages:
            formatted: dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }

            if msg.name:
                formatted["name"] = msg.name

            if msg.tool_calls:
                # Format tool calls
                tool_content = []
                for tc in msg.tool_calls:
                    tool_content.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                formatted["content"] = tool_content

            if msg.tool_call_id:
                # Convert content to list if it's a non-empty string
                content_value = formatted.get("content")
                if isinstance(content_value, str) and content_value:
                    formatted["content"] = [{"type": "text", "text": content_value}]
                elif content_value is None or content_value == "":
                    formatted["content"] = []
                formatted["content"].append({
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id,
                    "content": msg.content,
                })

            result.append(formatted)

        return result

    def _parse_response(
        self,
        data: dict[str, Any],
        model: str,
    ) -> ModelResponse:
        """Parse Anthropic API response.

        Args:
            data: Raw response data.
            model: Model name.

        Returns:
            Parsed ModelResponse.
        """
        # Extract content
        content_blocks = data.get("content", [])
        content_text = ""
        tool_calls: list[ToolCall] = []

        for block in content_blocks:
            if block.get("type") == "text":
                content_text += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.get("id", ""),
                    name=block.get("name", ""),
                    arguments=block.get("input", {}),
                ))

        # Extract usage
        usage_data = data.get("usage", {})
        usage = ModelUsage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
        )
        usage.total_tokens = usage.input_tokens + usage.output_tokens

        return ModelResponse(
            content=content_text,
            model=model,
            stop_reason=data.get("stop_reason"),
            tool_calls=tool_calls if tool_calls else None,
            usage=usage,
            metadata=data.get("id", ""),
        )
