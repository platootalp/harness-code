"""Unit tests for OpenAIAdapter."""

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
from mozi.core.model.errors import (
    AuthenticationError,
    InvalidRequestError,
    ModelInvocationError,
    RateLimitError,
)
from mozi.core.model.openai import OpenAIAdapter


@pytest.fixture
def adapter() -> OpenAIAdapter:
    """Create an adapter instance for testing."""
    return OpenAIAdapter(api_key="test-api-key")


@pytest.fixture
def sample_request() -> ModelRequest:
    """Create a sample model request."""
    return ModelRequest(
        model="gpt-4o",
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


class TestOpenAIAdapterProperties:
    """Tests for OpenAIAdapter properties."""

    def test_provider(self, adapter: OpenAIAdapter) -> None:
        """Test provider property returns OPENAI."""
        from mozi.core.model.adapter import ModelProvider

        assert adapter.provider == ModelProvider.OPENAI

    def test_supported_models(self, adapter: OpenAIAdapter) -> None:
        """Test supported_models returns list of ModelInfo."""
        models = adapter.supported_models
        # OpenAIAdapter has 5 models
        assert len(models) == 5
        assert all(m.provider == ModelProvider.OPENAI for m in models)

    def test_get_model_info_found(self, adapter: OpenAIAdapter) -> None:
        """Test get_model_info returns ModelInfo for valid model."""
        info = adapter.get_model_info("gpt-4o")
        assert info is not None
        assert info.name == "gpt-4o"
        assert info.display_name == "GPT-4o"

    def test_get_model_info_not_found(self, adapter: OpenAIAdapter) -> None:
        """Test get_model_info returns None for invalid model."""
        info = adapter.get_model_info("invalid-model")
        assert info is None


class TestOpenAIAdapterValidateRequest:
    """Tests for OpenAIAdapter.validate_request."""

    def test_valid_request(self, adapter: OpenAIAdapter, sample_request: ModelRequest) -> None:
        """Test validate_request passes for valid request."""
        adapter.validate_request(sample_request)  # Should not raise

    def test_missing_model(self, adapter: OpenAIAdapter) -> None:
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

    def test_missing_messages(self, adapter: OpenAIAdapter) -> None:
        """Test validate_request raises for missing messages."""
        request = ModelRequest(
            model="gpt-4o",
            messages=[],
        )
        with pytest.raises(InvalidRequestError) as exc_info:
            adapter.validate_request(request)
        assert "At least one message is required" in str(exc_info.value)

    def test_invalid_temperature_too_high(self, adapter: OpenAIAdapter) -> None:
        """Test validate_request raises for temperature > 2.0."""
        request = ModelRequest(
            model="gpt-4o",
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

    def test_invalid_temperature_negative(self, adapter: OpenAIAdapter) -> None:
        """Test validate_request raises for temperature < 0.0."""
        request = ModelRequest(
            model="gpt-4o",
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

    def test_invalid_top_p(self, adapter: OpenAIAdapter) -> None:
        """Test validate_request raises for invalid top_p."""
        request = ModelRequest(
            model="gpt-4o",
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

    def test_invalid_max_tokens(self, adapter: OpenAIAdapter) -> None:
        """Test validate_request raises for max_tokens <= 0."""
        request = ModelRequest(
            model="gpt-4o",
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


class TestOpenAIAdapterFormatMessages:
    """Tests for OpenAIAdapter._format_messages."""

    def test_format_basic_message(self, adapter: OpenAIAdapter) -> None:
        """Test formatting basic user message."""
        messages = [
            Message(
                role=MessageRole.USER,
                content="Hello",
            ),
        ]
        formatted = adapter._format_messages(messages, None)
        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"

    def test_format_system_message(self, adapter: OpenAIAdapter) -> None:
        """Test formatting system message separately."""
        messages = [
            Message(
                role=MessageRole.USER,
                content="Hello",
            ),
        ]
        formatted = adapter._format_messages(messages, "You are helpful.")
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are helpful."
        assert formatted[1]["role"] == "user"
        assert formatted[1]["content"] == "Hello"

    def test_format_messages_with_name(self, adapter: OpenAIAdapter) -> None:
        """Test formatting message with name field."""
        messages = [
            Message(
                role=MessageRole.USER,
                content="Hello",
                name="user1",
            ),
        ]
        formatted = adapter._format_messages(messages, None)
        assert formatted[0]["name"] == "user1"

    def test_format_tool_call_message(self, adapter: OpenAIAdapter) -> None:
        """Test formatting message with tool calls."""
        messages = [
            Message(
                role=MessageRole.ASSISTANT,
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
        formatted = adapter._format_messages(messages, None)
        assert "tool_calls" in formatted[0]
        tc = formatted[0]["tool_calls"][0]
        assert tc["id"] == "call_123"
        assert tc["type"] == "function"
        assert tc["function"]["name"] == "get_weather"
        assert tc["function"]["arguments"] == {"location": "NYC"}

    def test_format_tool_result_message(self, adapter: OpenAIAdapter) -> None:
        """Test formatting message with tool call result."""
        messages = [
            Message(
                role=MessageRole.USER,
                content="The weather is nice",
                tool_call_id="call_123",
            ),
        ]
        formatted = adapter._format_messages(messages, None)
        assert formatted[0]["tool_call_id"] == "call_123"


class TestOpenAIAdapterParseResponse:
    """Tests for OpenAIAdapter._parse_response."""

    def test_parse_text_response(self, adapter: OpenAIAdapter) -> None:
        """Test parsing text-only response."""
        data = {
            "id": "chatcmpl_abc123",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello, world!"},
                    "finish_reason": "stop",
                },
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }
        response = adapter._parse_response(data, "gpt-4o")

        assert response.content == "Hello, world!"
        assert response.model == "gpt-4o"
        assert response.stop_reason == "stop"
        assert response.tool_calls is None
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 20
        assert response.usage.total_tokens == 30

    def test_parse_tool_call_response(self, adapter: OpenAIAdapter) -> None:
        """Test parsing response with tool calls."""
        data = {
            "id": "chatcmpl_abc123",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Let me check the weather.",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "NYC"}',
                                },
                            },
                        ],
                    },
                    "finish_reason": "tool_calls",
                },
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 50,
                "total_tokens": 60,
            },
        }
        response = adapter._parse_response(data, "gpt-4o")

        assert response.content == "Let me check the weather."
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].id == "call_123"
        assert response.tool_calls[0].name == "get_weather"

    def test_parse_empty_choices(self, adapter: OpenAIAdapter) -> None:
        """Test parsing response with empty choices."""
        data = {
            "id": "chatcmpl_abc123",
            "choices": [],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 0,
                "total_tokens": 10,
            },
        }
        response = adapter._parse_response(data, "gpt-4o")
        assert response.content == ""
        assert response.stop_reason is None

    def test_parse_missing_usage(self, adapter: OpenAIAdapter) -> None:
        """Test parsing response with missing usage."""
        data = {
            "id": "chatcmpl_abc123",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hi!"},
                    "finish_reason": "stop",
                },
            ],
        }
        response = adapter._parse_response(data, "gpt-4o")
        assert response.usage.input_tokens == 0
        assert response.usage.output_tokens == 0


class TestOpenAIAdapterInvoke:
    """Tests for OpenAIAdapter.invoke."""

    @pytest.mark.asyncio
    async def test_invoke_success(
        self,
        adapter: OpenAIAdapter,
        sample_request: ModelRequest,
    ) -> None:
        """Test successful model invocation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl_abc123",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hi there!"},
                    "finish_reason": "stop",
                },
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
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
        adapter: OpenAIAdapter,
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
        adapter: OpenAIAdapter,
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
        adapter: OpenAIAdapter,
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
        adapter: OpenAIAdapter,
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
        adapter: OpenAIAdapter,
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
    async def test_invoke_with_organization_header(
        self,
        adapter: OpenAIAdapter,
        sample_request: ModelRequest,
    ) -> None:
        """Test invocation includes organization header when set."""
        adapter._organization = "org_123"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl_abc123",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hi!"},
                    "finish_reason": "stop",
                },
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            await adapter.invoke(sample_request)

            # Verify organization header was passed
            call_args = mock_client.post.call_args
            headers = call_args.kwargs["headers"]
            assert "OpenAI-Organization" in headers
            assert headers["OpenAI-Organization"] == "org_123"


class TestOpenAIAdapterInitialization:
    """Tests for OpenAIAdapter initialization."""

    def test_default_base_url(self) -> None:
        """Test default base URL is set correctly."""
        adapter = OpenAIAdapter(api_key="test-key")
        assert adapter._base_url == OpenAIAdapter.BASE_URL

    def test_custom_base_url(self) -> None:
        """Test custom base URL is used."""
        adapter = OpenAIAdapter(
            api_key="test-key",
            base_url="https://custom.api.com/v1",
        )
        assert adapter._base_url == "https://custom.api.com/v1"

    def test_custom_organization(self) -> None:
        """Test custom organization is set."""
        adapter = OpenAIAdapter(
            api_key="test-key",
            organization="org_abc",
        )
        assert adapter._organization == "org_abc"

    def test_custom_timeout(self) -> None:
        """Test custom timeout is set."""
        adapter = OpenAIAdapter(
            api_key="test-key",
            timeout=120.0,
        )
        assert adapter._timeout == 120.0
