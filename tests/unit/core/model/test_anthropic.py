"""Unit tests for AnthropicAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.core.model.adapter import (
    Message,
    MessageRole,
    ModelProvider,
    ModelRequest,
    ToolCall,
)
from mozi.core.model.anthropic import AnthropicAdapter
from mozi.core.model.errors import (
    AuthenticationError,
    InvalidRequestError,
    ModelInvocationError,
    RateLimitError,
)


@pytest.fixture
def adapter() -> AnthropicAdapter:
    """Create an adapter instance for testing."""
    return AnthropicAdapter(api_key="test-api-key")


@pytest.fixture
def sample_request() -> ModelRequest:
    """Create a sample model request."""
    return ModelRequest(
        model="claude-3-5-sonnet-latest",
        messages=[
            Message(
                role=MessageRole.USER,
                content="Hello, world!",
            ),
        ],
        system_prompt="You are a helpful assistant.",
        temperature=1.0,
        max_tokens=100,
    )


class TestAnthropicAdapterProperties:
    """Tests for AnthropicAdapter properties."""

    def test_provider(self, adapter: AnthropicAdapter) -> None:
        """Test provider property returns ANTHROPIC."""
        from mozi.core.model.adapter import ModelProvider

        assert adapter.provider == ModelProvider.ANTHROPIC

    def test_supported_models(self, adapter: AnthropicAdapter) -> None:
        """Test supported_models returns list of ModelInfo."""
        models = adapter.supported_models
        # AnthropicAdapter has 5 models
        assert len(models) == 5
        assert all(m.provider == ModelProvider.ANTHROPIC for m in models)

    def test_get_model_info_found(self, adapter: AnthropicAdapter) -> None:
        """Test get_model_info returns ModelInfo for valid model."""
        info = adapter.get_model_info("claude-3-5-sonnet-latest")
        assert info is not None
        assert info.name == "claude-3-5-sonnet-latest"
        assert info.display_name == "Claude 3.5 Sonnet"

    def test_get_model_info_not_found(self, adapter: AnthropicAdapter) -> None:
        """Test get_model_info returns None for invalid model."""
        info = adapter.get_model_info("invalid-model")
        assert info is None


class TestAnthropicAdapterValidateRequest:
    """Tests for AnthropicAdapter.validate_request."""

    def test_valid_request(self, adapter: AnthropicAdapter, sample_request: ModelRequest) -> None:
        """Test validate_request passes for valid request."""
        adapter.validate_request(sample_request)  # Should not raise

    def test_missing_model(self, adapter: AnthropicAdapter) -> None:
        """Test validate_request raises for missing model."""
        request = ModelRequest(
            model="",
            messages=[
                Message(
                    role=MessageRole.USER,
                    content="Hello",
                ),
            ],
        )
        with pytest.raises(InvalidRequestError) as exc_info:
            adapter.validate_request(request)
        assert "Model name is required" in str(exc_info.value)

    def test_missing_messages(self, adapter: AnthropicAdapter) -> None:
        """Test validate_request raises for missing messages."""
        request = ModelRequest(
            model="claude-3-5-sonnet-latest",
            messages=[],
        )
        with pytest.raises(InvalidRequestError) as exc_info:
            adapter.validate_request(request)
        assert "At least one message is required" in str(exc_info.value)

    def test_invalid_temperature_too_high(self, adapter: AnthropicAdapter) -> None:
        """Test validate_request raises for temperature > 2.0."""
        request = ModelRequest(
            model="claude-3-5-sonnet-latest",
            messages=[
                Message(
                    role=MessageRole.USER,
                    content="Hello",
                ),
            ],
            temperature=2.5,
        )
        with pytest.raises(InvalidRequestError) as exc_info:
            adapter.validate_request(request)
        assert "Temperature must be between 0.0 and 2.0" in str(exc_info.value)

    def test_invalid_temperature_negative(self, adapter: AnthropicAdapter) -> None:
        """Test validate_request raises for temperature < 0.0."""
        request = ModelRequest(
            model="claude-3-5-sonnet-latest",
            messages=[
                Message(
                    role=MessageRole.USER,
                    content="Hello",
                ),
            ],
            temperature=-0.5,
        )
        with pytest.raises(InvalidRequestError) as exc_info:
            adapter.validate_request(request)
        assert "Temperature must be between 0.0 and 2.0" in str(exc_info.value)

    def test_invalid_top_p(self, adapter: AnthropicAdapter) -> None:
        """Test validate_request raises for invalid top_p."""
        request = ModelRequest(
            model="claude-3-5-sonnet-latest",
            messages=[
                Message(
                    role=MessageRole.USER,
                    content="Hello",
                ),
            ],
            top_p=1.5,
        )
        with pytest.raises(InvalidRequestError) as exc_info:
            adapter.validate_request(request)
        assert "top_p must be between 0.0 and 1.0" in str(exc_info.value)

    def test_invalid_max_tokens(self, adapter: AnthropicAdapter) -> None:
        """Test validate_request raises for max_tokens <= 0."""
        request = ModelRequest(
            model="claude-3-5-sonnet-latest",
            messages=[
                Message(
                    role=MessageRole.USER,
                    content="Hello",
                ),
            ],
            max_tokens=0,
        )
        with pytest.raises(InvalidRequestError) as exc_info:
            adapter.validate_request(request)
        assert "max_tokens must be positive" in str(exc_info.value)


class TestAnthropicAdapterFormatMessages:
    """Tests for AnthropicAdapter._format_messages."""

    def test_format_basic_message(self, adapter: AnthropicAdapter) -> None:
        """Test formatting basic user message."""
        messages = [
            Message(
                role=MessageRole.USER,
                content="Hello",
            ),
        ]
        formatted = adapter._format_messages(messages)
        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"

    def test_format_messages_with_name(self, adapter: AnthropicAdapter) -> None:
        """Test formatting message with name field."""
        messages = [
            Message(
                role=MessageRole.USER,
                content="Hello",
                name="user1",
            ),
        ]
        formatted = adapter._format_messages(messages)
        assert formatted[0]["name"] == "user1"

    def test_format_tool_call_message(self, adapter: AnthropicAdapter) -> None:
        """Test formatting message with tool calls."""
        messages = [
            Message(
                role=MessageRole.USER,
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_123",
                        name="get_weather",
                        arguments={"location": "NYC"},
                    ),
                ],
            ),
        ]
        formatted = adapter._format_messages(messages)
        assert len(formatted[0]["content"]) == 1
        tool_use = formatted[0]["content"][0]
        assert tool_use["type"] == "tool_use"
        assert tool_use["id"] == "call_123"
        assert tool_use["name"] == "get_weather"

    def test_format_tool_result_message(self, adapter: AnthropicAdapter) -> None:
        """Test formatting message with tool call result."""
        messages = [
            Message(
                role=MessageRole.USER,
                content="The weather is nice",
                tool_call_id="call_123",
            ),
        ]
        formatted = adapter._format_messages(messages)
        # When content is text and tool_call_id is set, both are preserved as a list
        assert len(formatted[0]["content"]) == 2
        # First item is the original text content
        assert formatted[0]["content"][0] == {"type": "text", "text": "The weather is nice"}
        # Second item is the tool result
        tool_result = formatted[0]["content"][1]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "call_123"
        assert tool_result["content"] == "The weather is nice"

    def test_format_tool_result_only(self, adapter: AnthropicAdapter) -> None:
        """Test formatting message with only tool call result (no text content)."""
        messages = [
            Message(
                role=MessageRole.USER,
                content="",
                tool_call_id="call_123",
            ),
        ]
        formatted = adapter._format_messages(messages)
        assert len(formatted[0]["content"]) == 1
        tool_result = formatted[0]["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "call_123"


class TestAnthropicAdapterParseResponse:
    """Tests for AnthropicAdapter._parse_response."""

    def test_parse_text_response(self, adapter: AnthropicAdapter) -> None:
        """Test parsing text-only response."""
        data = {
            "id": "msg_abc123",
            "content": [
                {"type": "text", "text": "Hello, world!"},
            ],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
            },
        }
        response = adapter._parse_response(data, "claude-3-5-sonnet-latest")

        assert response.content == "Hello, world!"
        assert response.model == "claude-3-5-sonnet-latest"
        assert response.stop_reason == "end_turn"
        assert response.tool_calls is None
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 20
        assert response.usage.total_tokens == 30

    def test_parse_tool_use_response(self, adapter: AnthropicAdapter) -> None:
        """Test parsing response with tool calls."""
        data = {
            "id": "msg_abc123",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "get_weather",
                    "input": {"location": "NYC"},
                },
            ],
            "stop_reason": "tool_use",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 50,
            },
        }
        response = adapter._parse_response(data, "claude-3-5-sonnet-latest")

        assert response.content == ""
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].id == "toolu_123"
        assert response.tool_calls[0].name == "get_weather"
        assert response.tool_calls[0].arguments == {"location": "NYC"}

    def test_parse_empty_content(self, adapter: AnthropicAdapter) -> None:
        """Test parsing response with empty content."""
        data = {
            "id": "msg_abc123",
            "content": [],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 0,
            },
        }
        response = adapter._parse_response(data, "claude-3-5-sonnet-latest")
        assert response.content == ""


class TestAnthropicAdapterInvoke:
    """Tests for AnthropicAdapter.invoke."""

    @pytest.mark.asyncio
    async def test_invoke_success(
        self,
        adapter: AnthropicAdapter,
        sample_request: ModelRequest,
    ) -> None:
        """Test successful model invocation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg_abc123",
            "content": [{"type": "text", "text": "Hi there!"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            response = await adapter.invoke(sample_request)

            assert response.content == "Hi there!"
            assert response.usage.input_tokens == 10

    @pytest.mark.asyncio
    async def test_invoke_authentication_error(
        self,
        adapter: AnthropicAdapter,
        sample_request: ModelRequest,
    ) -> None:
        """Test invocation with authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(AuthenticationError):
                await adapter.invoke(sample_request)

    @pytest.mark.asyncio
    async def test_invoke_rate_limit_error(
        self,
        adapter: AnthropicAdapter,
        sample_request: ModelRequest,
    ) -> None:
        """Test invocation with rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers.get.return_value = "60"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(RateLimitError) as exc_info:
                await adapter.invoke(sample_request)
            assert exc_info.value.retry_after == 60.0

    @pytest.mark.asyncio
    async def test_invoke_timeout_error(
        self,
        adapter: AnthropicAdapter,
        sample_request: ModelRequest,
    ) -> None:
        """Test invocation with timeout error."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(ModelInvocationError) as exc_info:
                await adapter.invoke(sample_request)
            assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_http_error(
        self,
        adapter: AnthropicAdapter,
        sample_request: ModelRequest,
    ) -> None:
        """Test invocation with HTTP error."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.HTTPError("Connection failed")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(ModelInvocationError) as exc_info:
                await adapter.invoke(sample_request)
            assert "HTTP error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_api_error(
        self,
        adapter: AnthropicAdapter,
        sample_request: ModelRequest,
    ) -> None:
        """Test invocation with API error response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": {"message": "Internal error"}}
        mock_response.text = "Internal server error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(ModelInvocationError) as exc_info:
                await adapter.invoke(sample_request)
            assert "API error (500)" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_parse_error(
        self,
        adapter: AnthropicAdapter,
        sample_request: ModelRequest,
    ) -> None:
        """Test invocation with response parse error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg_abc123",
            "content": [{"type": "invalid", "unknown": "field"}],
            "stop_reason": None,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # This should still work since our parser handles missing fields gracefully
            response = await adapter.invoke(sample_request)
            assert response.content == ""


class TestAnthropicAdapterInitialization:
    """Tests for AnthropicAdapter initialization."""

    def test_default_base_url(self) -> None:
        """Test default base URL is set correctly."""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter._base_url == AnthropicAdapter.BASE_URL

    def test_custom_base_url(self) -> None:
        """Test custom base URL is used."""
        adapter = AnthropicAdapter(
            api_key="test-key",
            base_url="https://custom.api.com/v1",
        )
        assert adapter._base_url == "https://custom.api.com/v1"

    def test_custom_timeout(self) -> None:
        """Test custom timeout is set."""
        adapter = AnthropicAdapter(
            api_key="test-key",
            timeout=120.0,
        )
        assert adapter._timeout == 120.0
