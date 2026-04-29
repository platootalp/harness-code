"""
Tests for Claude AI client.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from claude_code.services.api.claude import (
    ChatCompletionResponse,
    ChatCompletionUsage,
    ClaudeAIClient,
    DEFAULT_MODELS,
    Message,
    MessageDelta,
    PROVIDER_BASE_URLS,
    ProviderType,
    StreamEvent,
    create_client,
    get_api_provider,
)


class TestProviderType:
    """Tests for ProviderType enum."""

    def test_values(self) -> None:
        """Test all provider types exist."""
        assert ProviderType.DIRECT.value == "direct"
        assert ProviderType.AWS_BEDROCK.value == "aws_bedrock"
        assert ProviderType.AZURE_FOUNDRY.value == "azure_foundry"
        assert ProviderType.GOOGLE_VERTEX.value == "google_vertex"


class TestMessage:
    """Tests for Message dataclass."""

    def test_create(self) -> None:
        """Test creating a message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_to_dict_string_content(self) -> None:
        """Test to_dict with string content."""
        msg = Message(role="user", content="Hello")
        result = msg.to_dict()
        assert result == {"role": "user", "content": "Hello"}

    def test_to_dict_list_content(self) -> None:
        """Test to_dict with list content."""
        msg = Message(role="user", content=[{"text": "Hello"}])
        result = msg.to_dict()
        assert result == {"role": "user", "content": [{"text": "Hello"}]}


class TestMessageDelta:
    """Tests for MessageDelta dataclass."""

    def test_create(self) -> None:
        """Test creating a message delta."""
        delta = MessageDelta(text="Hello", index=0)
        assert delta.text == "Hello"
        assert delta.index == 0
        assert delta.type == "content_block_delta"

    def test_custom_type(self) -> None:
        """Test with custom type."""
        delta = MessageDelta(text="Hi", index=1, type="custom")
        assert delta.type == "custom"


class TestStreamEvent:
    """Tests for StreamEvent dataclass."""

    def test_create(self) -> None:
        """Test creating a stream event."""
        event = StreamEvent(type="content_block_delta")
        assert event.type == "content_block_delta"
        assert event.delta is None

    def test_with_delta(self) -> None:
        """Test with delta."""
        delta = MessageDelta(text="Hello")
        event = StreamEvent(type="content_block_delta", delta=delta)
        assert event.delta == delta


class TestChatCompletionUsage:
    """Tests for ChatCompletionUsage dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        usage = ChatCompletionUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cache_creation_input_tokens == 0
        assert usage.cache_read_input_tokens == 0


class TestChatCompletionResponse:
    """Tests for ChatCompletionResponse dataclass."""

    def test_from_dict(self) -> None:
        """Test creating response from dict."""
        data = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello"}],
            "model": "claude-3-5-sonnet",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }
        response = ChatCompletionResponse.from_dict(data)
        assert response.id == "msg_123"
        assert response.type == "message"
        assert response.role == "assistant"
        assert response.content == [{"type": "text", "text": "Hello"}]
        assert response.model == "claude-3-5-sonnet"
        assert response.stop_reason == "end_turn"
        assert response.usage.input_tokens == 100
        assert response.usage.output_tokens == 50

    def test_from_dict_missing_fields(self) -> None:
        """Test from_dict with missing fields uses defaults."""
        data: dict[str, object] = {}
        response = ChatCompletionResponse.from_dict(data)
        assert response.id == ""
        assert response.type == "message"
        assert response.role == "assistant"
        assert response.content == []
        assert response.model == ""


class TestClaudeAIClient:
    """Tests for ClaudeAIClient."""

    def test_create_client(self) -> None:
        """Test creating a client."""
        client = ClaudeAIClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.provider == ProviderType.DIRECT
        assert client.timeout == 60.0
        assert client.max_retries == 3
        client.close()

    def test_create_client_with_provider(self) -> None:
        """Test creating a client with specific provider."""
        client = ClaudeAIClient(
            api_key="test-key",
            provider=ProviderType.AWS_BEDROCK,
        )
        assert client.provider == ProviderType.AWS_BEDROCK
        client.close()

    def test_create_client_with_base_url(self) -> None:
        """Test creating a client with custom base URL."""
        client = ClaudeAIClient(
            api_key="test-key",
            base_url="https://custom.example.com",
        )
        assert client.base_url == "https://custom.example.com"
        client.close()

    def test_context_manager(self) -> None:
        """Test using client as context manager."""
        with ClaudeAIClient(api_key="test") as client:
            assert client.api_key == "test"
        # Client should be closed after exit

    def test_build_headers_direct(self) -> None:
        """Test headers for DIRECT provider."""
        client = ClaudeAIClient(api_key="test-key")
        headers = client._build_headers()
        assert headers["x-api-key"] == "test-key"
        assert headers["anthropic-version"] == "2023-06-01"
        assert headers["anthropic-dangerous-direct-browser-access"] == "true"
        client.close()

    def test_build_headers_azure(self) -> None:
        """Test headers for AZURE_FOUNDRY provider."""
        client = ClaudeAIClient(
            api_key="test-key",
            provider=ProviderType.AZURE_FOUNDRY,
        )
        headers = client._build_headers()
        assert headers["api-key"] == "test-key"
        client.close()

    def test_get_base_url_default(self) -> None:
        """Test default base URL."""
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": ""}, clear=False):
            client = ClaudeAIClient(api_key="test")
            url = client._get_base_url()
            assert url == PROVIDER_BASE_URLS[ProviderType.DIRECT]
            client.close()

    def test_get_base_url_custom(self) -> None:
        """Test custom base URL."""
        client = ClaudeAIClient(api_key="test", base_url="https://custom.com/v1")
        url = client._get_base_url()
        assert url == "https://custom.com/v1"
        client.close()

    def test_get_model_explicit(self) -> None:
        """Test getting model when explicitly provided."""
        client = ClaudeAIClient(api_key="test")
        model = client._get_model("claude-3-5-haiku")
        assert model == "claude-3-5-haiku"
        client.close()

    def test_get_model_default(self) -> None:
        """Test getting default model for provider."""
        client = ClaudeAIClient(api_key="test")
        model = client._get_model(None)
        assert model == DEFAULT_MODELS[ProviderType.DIRECT]
        client.close()

    def test_build_request_body_basic(self) -> None:
        """Test building basic request body."""
        client = ClaudeAIClient(api_key="test")
        body = client._build_request_body(
            messages=[Message(role="user", content="Hello")],
            model="claude-3-5-sonnet",
            stream=False,
        )
        assert body["model"] == "claude-3-5-sonnet"
        assert body["stream"] is False
        assert body["max_tokens"] == 8192
        assert body["messages"] == [{"role": "user", "content": "Hello"}]
        client.close()

    def test_build_request_body_with_system(self) -> None:
        """Test request body with system prompt."""
        client = ClaudeAIClient(api_key="test")
        body = client._build_request_body(
            messages=[],
            model="claude-3-5-sonnet",
            stream=False,
            system="You are helpful.",
        )
        assert body["system"] == "You are helpful."
        client.close()

    def test_build_request_body_with_temperature(self) -> None:
        """Test request body with temperature."""
        client = ClaudeAIClient(api_key="test")
        body = client._build_request_body(
            messages=[],
            model="claude-3-5-sonnet",
            stream=False,
            temperature=0.7,
        )
        assert body["temperature"] == 0.7
        client.close()

    def test_build_request_body_with_dict_message(self) -> None:
        """Test request body with dict message."""
        client = ClaudeAIClient(api_key="test")
        body = client._build_request_body(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-3-5-sonnet",
            stream=False,
        )
        assert body["messages"] == [{"role": "user", "content": "Hello"}]
        client.close()

    def test_build_url_direct(self) -> None:
        """Test building URL for DIRECT provider."""
        client = ClaudeAIClient(api_key="test")
        url = client._build_url("claude-3-5-sonnet")
        assert url.endswith("/messages")
        client.close()

    def test_build_url_bedrock(self) -> None:
        """Test building URL for AWS Bedrock."""
        with patch.dict(os.environ, {"AWS_REGION": "us-west-2"}):
            client = ClaudeAIClient(api_key="test", provider=ProviderType.AWS_BEDROCK)
            url = client._build_url("anthropic.claude-3-5-sonnet-v2:0")
            assert "bedrock.us-west-2.amazonaws.com" in url
            assert "/model/" in url
            client.close()

    def test_build_url_azure(self) -> None:
        """Test building URL for Azure Foundry."""
        client = ClaudeAIClient(
            api_key="test",
            provider=ProviderType.AZURE_FOUNDRY,
            base_url="https://example.azure.com/v1",
        )
        url = client._build_url("claude-3-5-sonnet-v2")
        assert "/deployments/claude-3-5-sonnet-v2/chat/completions" in url
        client.close()

    def test_build_url_vertex(self) -> None:
        """Test building URL for Google Vertex."""
        client = ClaudeAIClient(
            api_key="test",
            provider=ProviderType.GOOGLE_VERTEX,
            base_url="https://us-central1-aiplatform.googleapis.com/v1",
        )
        url = client._build_url("claude-3-5-sonnet-v2-20241022")
        assert "publishers/anthropic/models/" in url
        assert ":predict" in url
        client.close()

    def test_parse_stream_event_delta(self) -> None:
        """Test parsing content_block_delta event."""
        client = ClaudeAIClient(api_key="test")
        data = {
            "type": "content_block_delta",
            "delta": {"type": "content_block_delta", "text": "Hello", "index": 0},
        }
        event = client._parse_stream_event(data)
        assert event.type == "content_block_delta"
        assert event.delta is not None
        assert event.delta.text == "Hello"
        assert event.delta.index == 0
        client.close()

    def test_parse_stream_event_content_block_start(self) -> None:
        """Test parsing content_block_start event."""
        client = ClaudeAIClient(api_key="test")
        data = {
            "type": "content_block_start",
            "content_block": {"type": "text"},
        }
        event = client._parse_stream_event(data)
        assert event.type == "content_block_start"
        assert event.content_block == {"type": "text"}
        client.close()

    def test_parse_stream_event_message_delta(self) -> None:
        """Test parsing message_delta event."""
        client = ClaudeAIClient(api_key="test")
        data = {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"output_tokens": 50},
        }
        event = client._parse_stream_event(data)
        assert event.type == "message_delta"
        assert event.delta == {"stop_reason": "end_turn"}
        assert event.usage == {"output_tokens": 50}
        client.close()

    def test_parse_stream_event_message_stop(self) -> None:
        """Test parsing message_stop event."""
        client = ClaudeAIClient(api_key="test")
        event = client._parse_stream_event({"type": "message_stop"})
        assert event.type == "message_stop"
        client.close()


class TestProviderDetection:
    """Tests for provider detection."""

    def test_get_api_provider_direct(self) -> None:
        """Test default provider is DIRECT."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_api_provider() == ProviderType.DIRECT

    def test_get_api_provider_bedrock(self) -> None:
        """Test Bedrock detection."""
        with patch.dict(os.environ, {"CLAUDE_CODE_USE_BEDROCK": "1"}):
            assert get_api_provider() == ProviderType.AWS_BEDROCK

    def test_get_api_provider_vertex(self) -> None:
        """Test Vertex detection."""
        with patch.dict(os.environ, {"CLAUDE_CODE_USE_VERTEX": "1"}):
            assert get_api_provider() == ProviderType.GOOGLE_VERTEX

    def test_get_api_provider_foundry(self) -> None:
        """Test Azure Foundry detection."""
        with patch.dict(os.environ, {"CLAUDE_CODE_USE_FOUNDRY": "1"}):
            assert get_api_provider() == ProviderType.AZURE_FOUNDRY


class TestCreateClient:
    """Tests for create_client factory function."""

    def test_create_client_with_key(self) -> None:
        """Test creating client with explicit key."""
        client = create_client(api_key="test-key")
        assert client.api_key == "test-key"
        client.close()

    def test_create_client_from_env(self) -> None:
        """Test creating client from environment variable."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            client = create_client()
            assert client.api_key == "env-key"
            client.close()

    def test_create_client_no_key_raises(self) -> None:
        """Test that missing key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key must be provided"):
                create_client()

    def test_create_client_with_provider(self) -> None:
        """Test creating client with specific provider."""
        client = create_client(api_key="test", provider=ProviderType.AWS_BEDROCK)
        assert client.provider == ProviderType.AWS_BEDROCK
        client.close()

    def test_create_client_with_base_url(self) -> None:
        """Test creating client with custom base URL."""
        client = create_client(
            api_key="test",
            base_url="https://custom.com",
        )
        assert client.base_url == "https://custom.com"
        client.close()
