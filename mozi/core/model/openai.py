"""OpenAI GPT model adapter.

Adapter for OpenAI GPT series models.
"""

from __future__ import annotations

from typing import Any

import httpx

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


class OpenAIAdapter(ModelAdapter):
    """Adapter for OpenAI GPT models.

    Supports GPT-4o, GPT-4 Turbo, GPT-4, and GPT-3.5 Turbo series.
    """

    BASE_URL = "https://api.openai.com/v1"

    SUPPORTED_MODELS = [
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
    ]

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        organization: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initialize OpenAI adapter.

        Args:
            api_key: OpenAI API key.
            base_url: Optional custom base URL.
            organization: Optional organization ID.
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key
        self._base_url = base_url or self.BASE_URL
        self._organization = organization
        self._timeout = timeout

    @property
    def provider(self) -> ModelProvider:
        """Return the model provider."""
        return ModelProvider.OPENAI

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

        if request.temperature < 0.0 or request.temperature > 2.0:
            raise InvalidRequestError("Temperature must be between 0.0 and 2.0")

        if request.top_p is not None and (request.top_p < 0.0 or request.top_p > 1.0):
            raise InvalidRequestError("top_p must be between 0.0 and 1.0")

        if request.max_tokens is not None and request.max_tokens <= 0:
            raise InvalidRequestError("max_tokens must be positive")

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        """Invoke the OpenAI model.

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
        messages = self._format_messages(request.messages, request.system_prompt)
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        if request.top_p is not None:
            payload["top_p"] = request.top_p

        if request.stop_sequences:
            payload["stop"] = request.stop_sequences

        if request.tools:
            payload["tools"] = request.tools

        # Make request
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        if self._organization:
            headers["OpenAI-Organization"] = self._organization

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
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

    def _format_messages(
        self,
        messages: list[Message],
        system_prompt: str | None,
    ) -> list[dict[str, Any]]:
        """Format messages for OpenAI API.

        Args:
            messages: List of Message objects.
            system_prompt: System prompt if provided.

        Returns:
            List of formatted message dicts.
        """
        result: list[dict[str, Any]] = []

        # Add system message first if provided
        if system_prompt:
            result.append({
                "role": "system",
                "content": system_prompt,
            })

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
        data: dict[str, Any],
        model: str,
    ) -> ModelResponse:
        """Parse OpenAI API response.

        Args:
            data: Raw response data.
            model: Model name.

        Returns:
            Parsed ModelResponse.
        """
        # Extract content
        choices = data.get("choices", [])
        if not choices:
            return ModelResponse(
                content="",
                model=model,
                stop_reason=None,
                tool_calls=None,
                usage=ModelUsage(),
            )

        choice = choices[0]
        message = choice.get("message", {})

        content_text = message.get("content", "")

        # Extract tool calls
        tool_calls: list[ToolCall] = []
        raw_tool_calls = message.get("tool_calls", [])
        for raw_tc in raw_tool_calls:
            func = raw_tc.get("function", {})
            tool_calls.append(ToolCall(
                id=raw_tc.get("id", ""),
                name=func.get("name", ""),
                arguments=func.get("arguments", {}),
            ))

        # Extract usage
        usage_data = data.get("usage", {})
        usage = ModelUsage(
            input_tokens=usage_data.get("prompt_tokens", 0),
            output_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return ModelResponse(
            content=content_text,
            model=model,
            stop_reason=choice.get("finish_reason"),
            tool_calls=tool_calls if tool_calls else None,
            usage=usage,
            metadata=data.get("id", ""),
        )
