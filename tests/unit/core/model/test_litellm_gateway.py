"""Unit tests for LitellmGateway."""

from __future__ import annotations

import pytest

from mozi.core.model.adapter import (
    Message,
    MessageRole,
    ModelProvider,
    ModelRequest,
    ToolCall,
)
from mozi.core.model.errors import (
    InvalidRequestError,
)
from mozi.core.model.litellm_gateway import SUPPORTED_MODELS, LitellmGateway


class TestLitellmGatewayInitialization:
    """Tests for LitellmGateway initialization."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with API key."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        assert gateway._api_key == "test-key"
        assert gateway._provider == ModelProvider.OPENAI
        assert gateway._base_url is None
        assert gateway._timeout == 60.0

    def test_init_with_custom_base_url(self) -> None:
        """Test initialization with custom base URL."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.ANTHROPIC,
            base_url="https://custom.api.com",
            timeout=120.0,
        )
        assert gateway._base_url == "https://custom.api.com"
        assert gateway._timeout == 120.0

    def test_provider_property(self) -> None:
        """Test provider property returns correct value."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.ANTHROPIC,
        )
        assert gateway.provider == ModelProvider.ANTHROPIC

    def test_supported_models_anthropic(self) -> None:
        """Test supported models for Anthropic provider."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.ANTHROPIC,
        )
        models = gateway.supported_models
        assert len(models) == 3
        assert all(m.provider == ModelProvider.ANTHROPIC for m in models)

    def test_supported_models_openai(self) -> None:
        """Test supported models for OpenAI provider."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        models = gateway.supported_models
        assert len(models) == 5
        assert all(m.provider == ModelProvider.OPENAI for m in models)


class TestLitellmGatewayGetModelInfo:
    """Tests for LitellmGateway.get_model_info."""

    def test_get_model_info_found(self) -> None:
        """Test getting model info when model exists."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.ANTHROPIC,
        )
        info = gateway.get_model_info("claude-3-5-sonnet-latest")
        assert info is not None
        assert info.name == "claude-3-5-sonnet-latest"
        assert info.display_name == "Claude 3.5 Sonnet"

    def test_get_model_info_not_found(self) -> None:
        """Test getting model info when model doesn't exist."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.ANTHROPIC,
        )
        info = gateway.get_model_info("non-existent-model")
        assert info is None


class TestLitellmGatewayValidateRequest:
    """Tests for LitellmGateway.validate_request."""

    def test_validate_valid_request(self) -> None:
        """Test validating a valid request."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        request = ModelRequest(
            model="gpt-4o",
            messages=[Message(role=MessageRole.USER, content="Hello")],
            temperature=1.0,
        )
        # Should not raise
        gateway.validate_request(request)

    def test_validate_missing_model(self) -> None:
        """Test validating request with missing model."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        request = ModelRequest(
            model="",
            messages=[Message(role=MessageRole.USER, content="Hello")],
        )
        with pytest.raises(InvalidRequestError, match="Model name is required"):
            gateway.validate_request(request)

    def test_validate_missing_messages(self) -> None:
        """Test validating request with missing messages."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        request = ModelRequest(
            model="gpt-4o",
            messages=[],
        )
        with pytest.raises(InvalidRequestError, match="At least one message is required"):
            gateway.validate_request(request)

    def test_validate_invalid_temperature(self) -> None:
        """Test validating request with invalid temperature."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        request = ModelRequest(
            model="gpt-4o",
            messages=[Message(role=MessageRole.USER, content="Hello")],
            temperature=3.0,  # Invalid: > 2.0
        )
        with pytest.raises(InvalidRequestError, match="Temperature must be between"):
            gateway.validate_request(request)

    def test_validate_invalid_top_p(self) -> None:
        """Test validating request with invalid top_p."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        request = ModelRequest(
            model="gpt-4o",
            messages=[Message(role=MessageRole.USER, content="Hello")],
            top_p=1.5,  # Invalid: > 1.0
        )
        with pytest.raises(InvalidRequestError, match="top_p must be between"):
            gateway.validate_request(request)

    def test_validate_invalid_max_tokens(self) -> None:
        """Test validating request with invalid max_tokens."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        request = ModelRequest(
            model="gpt-4o",
            messages=[Message(role=MessageRole.USER, content="Hello")],
            max_tokens=0,  # Invalid: must be positive
        )
        with pytest.raises(InvalidRequestError, match="max_tokens must be positive"):
            gateway.validate_request(request)


class TestLitellmGatewayFormatMessages:
    """Tests for LitellmGateway._format_messages."""

    def test_format_messages_simple(self) -> None:
        """Test formatting simple messages."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there"),
        ]
        result = gateway._format_messages(messages, None)

        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Hello"}
        assert result[1] == {"role": "assistant", "content": "Hi there"}

    def test_format_messages_with_system_prompt(self) -> None:
        """Test formatting messages with system prompt."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]
        result = gateway._format_messages(messages, "You are helpful.")

        assert len(result) == 2
        assert result[0] == {"role": "system", "content": "You are helpful."}
        assert result[1] == {"role": "user", "content": "Hello"}

    def test_format_messages_with_tool_calls(self) -> None:
        """Test formatting messages with tool calls."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        messages = [
            Message(
                role=MessageRole.ASSISTANT,
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_123",
                        name="get_weather",
                        arguments={"location": "Boston"},
                    ),
                ],
            ),
        ]
        result = gateway._format_messages(messages, None)

        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["tool_calls"][0]["id"] == "call_123"
        assert result[0]["tool_calls"][0]["function"]["name"] == "get_weather"

    def test_format_messages_with_tool_call_id(self) -> None:
        """Test formatting messages with tool call ID."""
        gateway = LitellmGateway(
            api_key="test-key",
            provider=ModelProvider.OPENAI,
        )
        messages = [
            Message(
                role=MessageRole.TOOL,
                content="The weather is sunny.",
                tool_call_id="call_123",
            ),
        ]
        result = gateway._format_messages(messages, None)

        assert len(result) == 1
        assert result[0]["role"] == "tool"
        assert result[0]["tool_call_id"] == "call_123"
        assert result[0]["content"] == "The weather is sunny."


class TestLitellmGatewaySupportedModels:
    """Tests for SUPPORTED_MODELS configuration."""

    def test_anthropic_models(self) -> None:
        """Test Anthropic models are configured correctly."""
        models = SUPPORTED_MODELS[ModelProvider.ANTHROPIC]
        assert len(models) == 3
        model_names = [m.name for m in models]
        assert "claude-3-5-sonnet-latest" in model_names
        assert "claude-3-5-haiku-latest" in model_names
        assert "claude-3-opus-latest" in model_names

    def test_openai_models(self) -> None:
        """Test OpenAI models are configured correctly."""
        models = SUPPORTED_MODELS[ModelProvider.OPENAI]
        assert len(models) == 5
        model_names = [m.name for m in models]
        assert "gpt-4o" in model_names
        assert "gpt-4o-mini" in model_names
        assert "gpt-4-turbo" in model_names
        assert "gpt-4" in model_names
        assert "gpt-3.5-turbo" in model_names

    def test_model_info_attributes(self) -> None:
        """Test ModelInfo attributes are correct."""
        model = SUPPORTED_MODELS[ModelProvider.ANTHROPIC][0]
        assert model.provider == ModelProvider.ANTHROPIC
        assert model.context_window == 200000
        assert model.supports_tools is True
        assert model.tier in ["fast", "balanced", "powerful"]
