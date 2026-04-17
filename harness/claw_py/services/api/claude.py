"""
Claude AI API client supporting multiple providers.

Supports:
- DIRECT: Direct Anthropic API
- AWS_BEDROCK: AWS Bedrock inference
- AZURE_FOUNDRY: Azure AI Foundry
- GOOGLE_VERTEX: Google Cloud Vertex AI
"""

from __future__ import annotations

import os
from collections.abc import Generator, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx

# =============================================================================
# Provider Types
# =============================================================================


class ProviderType(StrEnum):
    """API provider types supported by the Claude AI client."""

    DIRECT = "direct"
    AWS_BEDROCK = "aws_bedrock"
    AZURE_FOUNDRY = "azure_foundry"
    GOOGLE_VERTEX = "google_vertex"


# =============================================================================
# Message Types
# =============================================================================


@dataclass
class Message:
    """A message in a conversation."""

    role: str
    content: str | list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert message to API format."""
        content = self.content
        if isinstance(content, list):
            return {"role": self.role, "content": content}
        return {"role": self.role, "content": content}


@dataclass
class MessageDelta:
    """Delta update from a streaming response."""

    text: str
    index: int = 0
    type: str = "content_block_delta"


@dataclass
class StreamEvent:
    """A streaming event from the API."""

    type: str
    delta: MessageDelta | None = None
    content_block: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None
    stop_reason: str | None = None


# =============================================================================
# Response Types
# =============================================================================


@dataclass
class ChatCompletionUsage:
    """Usage statistics for a chat completion."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class ChatCompletionChoice:
    """A single choice in a chat completion response."""

    message: Message
    index: int = 0
    finish_reason: str | None = None


@dataclass
class ChatCompletionResponse:
    """Response from a non-streaming chat completion."""

    id: str
    type: str = "message"
    role: str = "assistant"
    content: list[dict[str, Any]] = field(default_factory=list)
    model: str = ""
    stop_reason: str | None = None
    stop_sequence: str | None = None
    usage: ChatCompletionUsage = field(default_factory=ChatCompletionUsage)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatCompletionResponse:
        """Create a response from a dictionary."""
        usage_data = data.get("usage", {})
        usage = ChatCompletionUsage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
            cache_creation_input_tokens=usage_data.get(
                "cache_creation_input_tokens", 0
            ),
            cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
        )
        content = data.get("content", [])
        if isinstance(content, list) and content:
            first_content = content[0]
            first_content.get("text", "") if isinstance(first_content, dict) else str(first_content)
        else:
            pass
        return cls(
            id=data.get("id", ""),
            type=data.get("type", "message"),
            role=data.get("role", "assistant"),
            content=content if isinstance(content, list) else [],
            model=data.get("model", ""),
            stop_reason=data.get("stop_reason"),
            stop_sequence=data.get("stop_sequence"),
            usage=usage,
        )


# =============================================================================
# Claude AI Client
# =============================================================================

# Default model per provider
DEFAULT_MODELS: dict[ProviderType, str] = {
    ProviderType.DIRECT: "claude-sonnet-4-20250514",
    ProviderType.AWS_BEDROCK: "anthropic.claude-3-5-sonnet-20241022-v2:0",
    ProviderType.AZURE_FOUNDRY: "claude-3-5-sonnet-v2",
    ProviderType.GOOGLE_VERTEX: "claude-3-5-sonnet-v2-20241022",
}

# Provider-specific base URLs
PROVIDER_BASE_URLS: dict[ProviderType, str] = {
    ProviderType.DIRECT: "https://api.anthropic.com/v1",
    ProviderType.AWS_BEDROCK: "",
    ProviderType.AZURE_FOUNDRY: "",
    ProviderType.GOOGLE_VERTEX: "",
}


@dataclass
class ClaudeAIClient:
    """
    Client for interacting with Claude AI via various providers.

    Supports multiple backends:
    - DIRECT: Standard Anthropic API
    - AWS_BEDROCK: AWS Bedrock inference
    - AZURE_FOUNDRY: Azure AI Foundry
    - GOOGLE_VERTEX: Google Cloud Vertex AI

    Attributes:
        api_key: API key for authentication.
        provider: The provider type to use.
        base_url: Override for the base API URL.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
    """

    api_key: str
    provider: ProviderType = ProviderType.DIRECT
    base_url: str | None = None
    timeout: float = 60.0
    max_retries: int = 3
    _client: httpx.Client | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize the HTTP client after dataclass initialization."""
        self._client = httpx.Client(
            timeout=httpx.Timeout(self.timeout),
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers based on provider."""
        headers: dict[str, str] = {
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        # MiniMax uses Authorization: Bearer header when base_url is explicitly set
        # (not from environment) to avoid polluting tests that use DIRECT provider
        if self.base_url and "minimaxi" in self.base_url:
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers["x-api-key"] = self.api_key
            if self.provider == ProviderType.DIRECT:
                headers["anthropic-dangerous-direct-browser-access"] = "true"
            elif self.provider == ProviderType.AZURE_FOUNDRY:
                headers["api-key"] = self.api_key
        return headers

    def _get_base_url(self) -> str:
        """Get the effective base URL for the provider."""
        if self.base_url:
            return self.base_url.rstrip("/")
        if self.provider == ProviderType.DIRECT:
            base = os.environ.get("ANTHROPIC_BASE_URL", "")
            return base.rstrip("/") if base else PROVIDER_BASE_URLS[self.provider]
        return ""

    def _get_model(self, model: str | None) -> str:
        """Get the effective model name."""
        return model or DEFAULT_MODELS.get(self.provider, "claude-sonnet-4-20250514")

    def _get_bedrock_auth(self) -> dict[str, Any]:
        """Get AWS Bedrock authentication headers."""
        try:
            import boto3
        except ImportError as err:
            raise RuntimeError(
                "boto3 is required for AWS Bedrock. "
                "Install it with: pip install boto3"
            ) from err
        region = os.environ.get("AWS_REGION", "us-east-1")
        model_id = os.environ.get("BEDROCK_MODEL_ID", "")
        credentials = boto3.Session().get_credentials()
        if credentials is None:
            raise RuntimeError("No AWS credentials found for Bedrock")
        import aws_sigv4
        signer = aws_sigv4.SigV4Signer(
            credentials.get_frozen_credentials(),
            "bedrock",
            region,
        )
        auth_headers, _ = signer.__call__(
            httpx.Request("POST", f"https://bedrock.{region}.amazonaws.com/model/{model_id}/invoke")
        )
        return {"Authorization": auth_headers.get("Authorization", "")}

    def _convert_message_to_api_format(self, message: Message | dict[str, Any]) -> dict[str, Any]:
        """Convert a Message to the API format expected by the server.

        The API expects:
        - role: string
        - content: string | array of content blocks (without the 'content_blocks' wrapper)
        - content blocks must have a 'type' field

        Args:
            message: Message object or dict

        Returns:
            API-compatible message dict
        """
        # Handle dict case
        if isinstance(message, dict):
            # If it has content_blocks, convert to content format
            if "content_blocks" in message:
                content = []
                for cb in message["content_blocks"]:
                    if isinstance(cb, dict):
                        # Add type if not present
                        cb_copy = dict(cb)
                        if "type" not in cb_copy:
                            if "text" in cb_copy:
                                cb_copy["type"] = "text"
                            elif "image_url" in cb_copy:
                                cb_copy["type"] = "image"
                        content.append(cb_copy)
                    else:
                        content.append(cb)
                return {
                    "role": message["role"],
                    "content": content,
                }
            return message

        # Handle Message objects
        # Check if this is the models.message.Message (has content_blocks attribute)
        # or the local Message (has content attribute)
        if hasattr(message, "content_blocks"):
            # models.message.Message
            content_blocks = []
            for cb in message.content_blocks:
                cb_dict = cb.to_dict()
                # Add type if not present
                if "type" not in cb_dict:
                    if cb.text is not None:
                        cb_dict["type"] = "text"
                    elif cb.image_url is not None:
                        cb_dict["type"] = "image"
                content_blocks.append(cb_dict)
            return {
                "role": message.role.value,
                "content": content_blocks,
            }
        else:
            # local Message (services/api/claude.py)
            # Has content: str | list[dict[str, Any]]
            return message.to_dict()

    def _build_request_body(
        self,
        messages: Sequence[Message | dict[str, Any]],
        model: str,
        stream: bool,
        system: str | None = None,
        max_tokens: int = 8192,
        temperature: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        thinking: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the request body for the API."""
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                self._convert_message_to_api_format(m) for m in messages
            ],
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if system:
            body["system"] = system
        if temperature is not None:
            body["temperature"] = temperature
        if tools:
            body["tools"] = tools
        if thinking:
            body["thinking"] = thinking
        if extra:
            body.update(extra)
        return body

    def chat_complete(
        self,
        messages: Sequence[Message | dict[str, Any]],
        stream: bool = False,
        model: str | None = None,
        system: str | None = None,
        max_tokens: int = 8192,
        temperature: float | None = None,
        tools: list[dict[str, Any]] | None = None,
        thinking: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> ChatCompletionResponse | Generator[StreamEvent, None, None]:
        """
        Perform a chat completion request.

        Args:
            messages: List of messages in the conversation.
            stream: Whether to stream the response.
            model: Model to use (defaults to provider-specific default).
            system: System prompt.
            max_tokens: Maximum tokens in the response.
            temperature: Sampling temperature (0.0 to 1.0).
            tools: List of tool definitions.
            thinking: Thinking budget configuration.
            extra: Additional parameters to pass to the API.

        Returns:
            ChatCompletionResponse for non-streaming requests.
            Generator of StreamEvent for streaming requests.

        Raises:
            httpx.HTTPStatusError: On API errors.
        """
        if self._client is None:
            raise RuntimeError("Client not initialized")

        effective_model = self._get_model(model)
        body = self._build_request_body(
            messages=messages,
            model=effective_model,
            stream=stream,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            thinking=thinking,
            extra=extra,
        )

        url = self._build_url(effective_model)

        if stream:
            return self._stream_request(url, body)
        return self._non_stream_request(url, body)

    def _build_url(self, model: str) -> str:
        """Build the full URL for the request."""
        base = self._get_base_url()
        # MiniMax requires /v1 in the path when base_url is explicitly set
        # (not from environment) to avoid polluting tests that use DIRECT provider
        if self.base_url and "minimaxi" in self.base_url:
            # Don't add /v1 if already present
            if "/v1" in self.base_url:
                return f"{self.base_url.rstrip('/')}/messages"
            return f"{self.base_url.rstrip('/')}/v1/messages"
        if self.provider == ProviderType.DIRECT:
            return f"{base}/messages"
        elif self.provider == ProviderType.AWS_BEDROCK:
            region = os.environ.get("AWS_REGION", "us-east-1")
            model_id = os.environ.get("BEDROCK_MODEL_ID", model.replace(".", "-").lower())
            return f"https://bedrock.{region}.amazonaws.com/model/{model_id}/invoke"
        elif self.provider == ProviderType.AZURE_FOUNDRY:
            deployment = os.environ.get("AZURE_FOUNDRY_DEPLOYMENT", model)
            return f"{base}/deployments/{deployment}/chat/completions"
        elif self.provider == ProviderType.GOOGLE_VERTEX:
            os.environ.get("GCP_PROJECT", "")
            os.environ.get("GCP_LOCATION", "us-central1")
            return f"{base}/publishers/anthropic/models/{model}:predict"
        return f"{base}/messages"

    def _non_stream_request(
        self, url: str, body: dict[str, Any]
    ) -> ChatCompletionResponse:
        """Execute a non-streaming request."""
        if self._client is None:
            raise RuntimeError("Client not initialized")
        response = self._client.post(url, json=body)
        response.raise_for_status()
        data = response.json()
        return ChatCompletionResponse.from_dict(data)

    def _stream_request(
        self, url: str, body: dict[str, Any]
    ) -> Generator[StreamEvent, None, None]:
        """Execute a streaming request."""
        if self._client is None:
            raise RuntimeError("Client not initialized")

        headers = self._build_headers()
        import json as _json

        with self._client.stream("POST", url, json=body, headers=headers) as response:
            response.raise_for_status()
            current_event_type: str | None = None
            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("event: "):
                    current_event_type = line[7:].strip()
                    continue
                if line.startswith("data: "):
                    line = line[6:]
                if line == "[DONE]":
                    break
                data = _json.loads(line)
                yield self._parse_stream_event(data, current_event_type)
                current_event_type = None

    def _parse_stream_event(self, data: dict[str, Any], event_type: str | None = None) -> StreamEvent:
        """Parse a streaming event from the API response."""
        # Use the SSE event type if provided, otherwise fall back to data type
        event_type = event_type or data.get("type", "")
        if event_type == "content_block_delta":
            delta = data.get("delta", {})
            delta_type = delta.get("type", "content_block_delta")
            # Handle minimax thinking_delta events
            if delta_type == "thinking_delta":
                return StreamEvent(
                    type=event_type,
                    delta=MessageDelta(
                        text=delta.get("thinking", ""),
                        index=delta.get("index", 0),
                        type=delta_type,
                    ),
                )
            return StreamEvent(
                type=event_type,
                delta=MessageDelta(
                    text=delta.get("text", ""),
                    index=delta.get("index", 0),
                    type=delta_type,
                ),
            )
        elif event_type == "content_block_start":
            return StreamEvent(
                type=event_type,
                content_block=data.get("content_block"),
            )
        elif event_type == "content_block_stop":
            return StreamEvent(type=event_type)
        elif event_type == "message_delta":
            return StreamEvent(
                type=event_type,
                delta=data.get("delta"),
                usage=data.get("usage"),
            )
        elif event_type == "message_stop" or event_type == "ping":
            return StreamEvent(type=event_type)
        else:
            return StreamEvent(type=event_type)

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> ClaudeAIClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# =============================================================================
# Provider Detection
# =============================================================================


def get_api_provider() -> ProviderType:
    """
    Detect the API provider from environment variables.

    Returns:
        ProviderType based on environment configuration.
    """
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK"):
        return ProviderType.AWS_BEDROCK
    if os.environ.get("CLAUDE_CODE_USE_VERTEX"):
        return ProviderType.GOOGLE_VERTEX
    if os.environ.get("CLAUDE_CODE_USE_FOUNDRY"):
        return ProviderType.AZURE_FOUNDRY
    return ProviderType.DIRECT


def create_client(
    api_key: str | None = None,
    provider: ProviderType | None = None,
    base_url: str | None = None,
) -> ClaudeAIClient:
    """
    Create a ClaudeAIClient instance.

    Args:
        api_key: API key (defaults to ANTHROPIC_API_KEY env var).
        provider: Provider type (auto-detected from env if not specified).
        base_url: Custom base URL override (defaults to ANTHROPIC_BASE_URL env var).

    Returns:
        Configured ClaudeAIClient instance.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError(
            "API key must be provided or set via ANTHROPIC_API_KEY env var"
        )
    detected_provider = provider or get_api_provider()
    # Read base_url from env if not explicitly provided
    detected_base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL")
    return ClaudeAIClient(
        api_key=key,
        provider=detected_provider,
        base_url=detected_base_url,
    )
