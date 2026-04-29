"""
Tests for services/api/claude.py
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from claude_code.services.api.claude import (
    ChatCompletionChoice,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ClaudeAIClient,
    DEFAULT_MODELS,
    Message,
    MessageDelta,
    ProviderType,
    PROVIDER_BASE_URLS,
    StreamEvent,
    create_client,
    get_api_provider,
)


# =============================================================================
# ProviderType Tests
# =============================================================================


class TestProviderType:
    def test_direct_value(self) -> None:
        assert ProviderType.DIRECT.value == "direct"

    def test_aws_bedrock_value(self) -> None:
        assert ProviderType.AWS_BEDROCK.value == "aws_bedrock"

    def test_azure_foundry_value(self) -> None:
        assert ProviderType.AZURE_FOUNDRY.value == "azure_foundry"

    def test_google_vertex_value(self) -> None:
        assert ProviderType.GOOGLE_VERTEX.value == "google_vertex"

    def test_all_providers_have_string_values(self) -> None:
        for provider in ProviderType:
            assert isinstance(provider.value, str)
            assert provider.value

    def test_provider_count(self) -> None:
        assert len(ProviderType) == 4


# =============================================================================
# Message Tests
# =============================================================================


class TestMessage:
    def test_init_with_string_content(self) -> None:
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_init_with_list_content(self) -> None:
        content = [{"type": "text", "text": "Hello"}]
        msg = Message(role="user", content=content)
        assert msg.role == "user"
        assert msg.content == content

    def test_to_dict_with_string_content(self) -> None:
        msg = Message(role="user", content="Hello")
        result = msg.to_dict()
        assert result == {"role": "user", "content": "Hello"}

    def test_to_dict_with_list_content(self) -> None:
        content = [{"type": "text", "text": "Hello"}]
        msg = Message(role="user", content=content)
        result = msg.to_dict()
        assert result == {"role": "user", "content": content}

    def test_to_dict_assistant_role(self) -> None:
        msg = Message(role="assistant", content="Hello")
        result = msg.to_dict()
        assert result == {"role": "assistant", "content": "Hello"}


# =============================================================================
# MessageDelta Tests
# =============================================================================


class TestMessageDelta:
    def test_init_defaults(self) -> None:
        delta = MessageDelta(text="Hello")
        assert delta.text == "Hello"
        assert delta.index == 0
        assert delta.type == "content_block_delta"

    def test_init_with_index(self) -> None:
        delta = MessageDelta(text=" world", index=1)
        assert delta.text == " world"
        assert delta.index == 1

    def test_init_with_type(self) -> None:
        delta = MessageDelta(text="thinking", type="thinking_delta")
        assert delta.type == "thinking_delta"


# =============================================================================
# StreamEvent Tests
# =============================================================================


class TestStreamEvent:
    def test_init_content_block_delta(self) -> None:
        delta = MessageDelta(text="Hello")
        event = StreamEvent(type="content_block_delta", delta=delta)
        assert event.type == "content_block_delta"
        assert event.delta == delta
        assert event.content_block is None
        assert event.usage is None

    def test_init_content_block_start(self) -> None:
        block = {"type": "text"}
        event = StreamEvent(type="content_block_start", content_block=block)
        assert event.type == "content_block_start"
        assert event.content_block == block

    def test_init_message_stop(self) -> None:
        event = StreamEvent(type="message_stop")
        assert event.type == "message_stop"

    def test_init_with_usage(self) -> None:
        event = StreamEvent(type="message_delta", usage={"output_tokens": 100})
        assert event.usage == {"output_tokens": 100}


# =============================================================================
# ChatCompletionUsage Tests
# =============================================================================


class TestChatCompletionUsage:
    def test_init_defaults(self) -> None:
        usage = ChatCompletionUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cache_creation_input_tokens == 0
        assert usage.cache_read_input_tokens == 0

    def test_init_with_values(self) -> None:
        usage = ChatCompletionUsage(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_input_tokens=200,
            cache_read_input_tokens=300,
        )
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.cache_creation_input_tokens == 200
        assert usage.cache_read_input_tokens == 300


# =============================================================================
# ChatCompletionResponse Tests
# =============================================================================


class TestChatCompletionResponse:
    def test_from_dict_basic(self) -> None:
        data = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello"}],
            "model": "claude-sonnet-4",
            "stop_reason": "end_turn",
        }
        response = ChatCompletionResponse.from_dict(data)
        assert response.id == "msg_123"
        assert response.type == "message"
        assert response.role == "assistant"
        assert response.content == [{"type": "text", "text": "Hello"}]
        assert response.model == "claude-sonnet-4"
        assert response.stop_reason == "end_turn"
        assert response.stop_sequence is None

    def test_from_dict_with_usage(self) -> None:
        data = {
            "id": "msg_123",
            "content": [{"type": "text", "text": "Hi"}],
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 20,
                "cache_read_input_tokens": 30,
            },
        }
        response = ChatCompletionResponse.from_dict(data)
        assert response.usage.input_tokens == 100
        assert response.usage.output_tokens == 50
        assert response.usage.cache_creation_input_tokens == 20
        assert response.usage.cache_read_input_tokens == 30

    def test_from_dict_missing_fields(self) -> None:
        data: dict[str, object] = {}
        response = ChatCompletionResponse.from_dict(data)
        assert response.id == ""
        assert response.type == "message"
        assert response.role == "assistant"
        assert response.content == []
        assert response.model == ""
        assert response.usage.input_tokens == 0

    def test_from_dict_content_extraction(self) -> None:
        data = {
            "id": "msg_456",
            "content": [{"type": "text", "text": "Response text"}],
        }
        response = ChatCompletionResponse.from_dict(data)
        assert len(response.content) == 1
        assert response.content[0]["text"] == "Response text"


# =============================================================================
# ChatCompletionChoice Tests
# =============================================================================


class TestChatCompletionChoice:
    def test_init_defaults(self) -> None:
        msg = Message(role="assistant", content="Hello")
        choice = ChatCompletionChoice(message=msg)
        assert choice.message == msg
        assert choice.index == 0
        assert choice.finish_reason is None

    def test_init_with_index_and_finish_reason(self) -> None:
        msg = Message(role="assistant", content="Hi")
        choice = ChatCompletionChoice(
            message=msg, index=1, finish_reason="end_turn"
        )
        assert choice.index == 1
        assert choice.finish_reason == "end_turn"


# =============================================================================
# ClaudeAIClient Tests
# =============================================================================


class TestClaudeAIClientInit:
    def test_init_basic(self) -> None:
        client = ClaudeAIClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.provider == ProviderType.DIRECT
        assert client.timeout == 60.0
        assert client.max_retries == 3
        client.close()

    def test_init_with_provider(self) -> None:
        client = ClaudeAIClient(
            api_key="test-key", provider=ProviderType.AWS_BEDROCK
        )
        assert client.provider == ProviderType.AWS_BEDROCK
        client.close()

    def test_init_with_all_params(self) -> None:
        client = ClaudeAIClient(
            api_key="test-key",
            provider=ProviderType.GOOGLE_VERTEX,
            base_url="https://custom.url",
            timeout=30.0,
            max_retries=5,
        )
        assert client.base_url == "https://custom.url"
        assert client.timeout == 30.0
        assert client.max_retries == 5
        client.close()

    def test_default_models_exist(self) -> None:
        for provider in ProviderType:
            model = DEFAULT_MODELS[provider]
            assert isinstance(model, str)
            assert model

    def test_provider_base_urls_exist(self) -> None:
        for provider in ProviderType:
            url = PROVIDER_BASE_URLS[provider]
            assert isinstance(url, str)


class TestClaudeAIClientContextManager:
    def test_context_manager_enter_exit(self) -> None:
        with ClaudeAIClient(api_key="test-key") as client:
            assert client.api_key == "test-key"
        # Client should be closed after exit

    def test_context_manager_reopens_client(self) -> None:
        with ClaudeAIClient(api_key="test-key") as client:
            assert client._client is not None
        # After exit, _client should be None
        assert client._client is None


class TestClaudeAIClientBuildHeaders:
    def test_build_headers_direct(self) -> None:
        client = ClaudeAIClient(api_key="my-key", provider=ProviderType.DIRECT)
        headers = client._build_headers()
        assert headers["x-api-key"] == "my-key"
        assert headers["anthropic-version"] == "2023-06-01"
        assert headers["content-type"] == "application/json"
        assert "anthropic-dangerous-direct-browser-access" in headers
        client.close()

    def test_build_headers_azure(self) -> None:
        client = ClaudeAIClient(api_key="my-key", provider=ProviderType.AZURE_FOUNDRY)
        headers = client._build_headers()
        assert headers["x-api-key"] == "my-key"
        assert headers["api-key"] == "my-key"
        client.close()


class TestClaudeAIClientGetModel:
    def test_get_model_explicit(self) -> None:
        client = ClaudeAIClient(api_key="key")
        model = client._get_model("claude-opus-4")
        assert model == "claude-opus-4"
        client.close()

    def test_get_model_default_for_direct(self) -> None:
        client = ClaudeAIClient(api_key="key", provider=ProviderType.DIRECT)
        model = client._get_model(None)
        assert model == DEFAULT_MODELS[ProviderType.DIRECT]
        client.close()

    def test_get_model_default_for_bedrock(self) -> None:
        client = ClaudeAIClient(api_key="key", provider=ProviderType.AWS_BEDROCK)
        model = client._get_model(None)
        assert model == DEFAULT_MODELS[ProviderType.AWS_BEDROCK]
        client.close()


class TestClaudeAIClientBuildRequestBody:
    def test_build_body_basic(self) -> None:
        client = ClaudeAIClient(api_key="key")
        messages = [Message(role="user", content="Hello")]
        body = client._build_request_body(messages, "claude-sonnet-4", False)
        assert body["model"] == "claude-sonnet-4"
        assert body["stream"] is False
        assert body["max_tokens"] == 8192
        assert len(body["messages"]) == 1
        client.close()

    def test_build_body_with_system(self) -> None:
        client = ClaudeAIClient(api_key="key")
        body = client._build_request_body([], "claude-sonnet-4", False, system="You are helpful")
        assert body["system"] == "You are helpful"
        client.close()

    def test_build_body_with_temperature(self) -> None:
        client = ClaudeAIClient(api_key="key")
        body = client._build_request_body([], "claude-sonnet-4", False, temperature=0.7)
        assert body["temperature"] == 0.7
        client.close()

    def test_build_body_with_tools(self) -> None:
        client = ClaudeAIClient(api_key="key")
        tools = [{"name": "web_search", "description": "Search the web"}]
        body = client._build_request_body([], "claude-sonnet-4", False, tools=tools)
        assert body["tools"] == tools
        client.close()

    def test_build_body_with_thinking(self) -> None:
        client = ClaudeAIClient(api_key="key")
        thinking = {"type": "enabled", "budget_tokens": 10000}
        body = client._build_request_body([], "claude-sonnet-4", False, thinking=thinking)
        assert body["thinking"] == thinking
        client.close()

    def test_build_body_with_extra(self) -> None:
        client = ClaudeAIClient(api_key="key")
        extra = {"top_p": 0.9}
        body = client._build_request_body([], "claude-sonnet-4", False, extra=extra)
        assert body["top_p"] == 0.9
        client.close()

    def test_build_body_message_to_dict(self) -> None:
        client = ClaudeAIClient(api_key="key")
        messages = [Message(role="user", content="Hello")]
        body = client._build_request_body(messages, "claude-sonnet-4", False)
        assert body["messages"][0] == {"role": "user", "content": "Hello"}
        client.close()

    def test_build_body_dict_message(self) -> None:
        client = ClaudeAIClient(api_key="key")
        messages = [{"role": "user", "content": "Hello"}]
        body = client._build_request_body(messages, "claude-sonnet-4", False)
        assert body["messages"][0] == {"role": "user", "content": "Hello"}
        client.close()


class TestClaudeAIClientBuildUrl:
    def test_build_url_direct(self) -> None:
        client = ClaudeAIClient(api_key="key")
        url = client._build_url("claude-sonnet-4")
        assert "/messages" in url
        assert "anthropic" in url or "api.anthropic.com" in url
        client.close()

    def test_build_url_direct_with_custom_base(self) -> None:
        client = ClaudeAIClient(api_key="key", base_url="https://custom.api.com")
        url = client._build_url("claude-sonnet-4")
        assert url.startswith("https://custom.api.com")
        assert "/messages" in url
        client.close()

    def test_build_url_azure_foundry(self) -> None:
        client = ClaudeAIClient(
            api_key="key",
            provider=ProviderType.AZURE_FOUNDRY,
            base_url="https://my-resource.cognitiveservices.azure.com",
        )
        url = client._build_url("claude-3-5-sonnet")
        assert "azure" in url.lower()
        assert "deployments" in url
        client.close()


class TestClaudeAIClientParseStreamEvent:
    def test_parse_content_block_delta(self) -> None:
        client = ClaudeAIClient(api_key="key")
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

    def test_parse_content_block_start(self) -> None:
        client = ClaudeAIClient(api_key="key")
        data = {
            "type": "content_block_start",
            "content_block": {"type": "text"},
        }
        event = client._parse_stream_event(data)
        assert event.type == "content_block_start"
        assert event.content_block == {"type": "text"}
        client.close()

    def test_parse_content_block_stop(self) -> None:
        client = ClaudeAIClient(api_key="key")
        data = {"type": "content_block_stop"}
        event = client._parse_stream_event(data)
        assert event.type == "content_block_stop"
        client.close()

    def test_parse_message_delta(self) -> None:
        client = ClaudeAIClient(api_key="key")
        data = {
            "type": "message_delta",
            "delta": {"type": "message_delta", "text": ""},
            "usage": {"output_tokens": 100},
        }
        event = client._parse_stream_event(data)
        assert event.type == "message_delta"
        assert event.usage == {"output_tokens": 100}
        client.close()

    def test_parse_message_stop(self) -> None:
        client = ClaudeAIClient(api_key="key")
        data = {"type": "message_stop"}
        event = client._parse_stream_event(data)
        assert event.type == "message_stop"
        client.close()

    def test_parse_ping(self) -> None:
        client = ClaudeAIClient(api_key="key")
        data = {"type": "ping"}
        event = client._parse_stream_event(data)
        assert event.type == "ping"
        client.close()

    def test_parse_unknown_type(self) -> None:
        client = ClaudeAIClient(api_key="key")
        data = {"type": "custom_event"}
        event = client._parse_stream_event(data)
        assert event.type == "custom_event"
        client.close()


# =============================================================================
# Non-streaming chat_complete Tests
# =============================================================================


class TestClaudeAIClientChatCompleteNonStream:
    def test_non_stream_returns_response(self) -> None:
        client = ClaudeAIClient(api_key="test-key")
        mock_response_data = {
            "id": "msg_test123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-sonnet-4",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        with patch.object(client._client, "post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response_data
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            messages = [Message(role="user", content="Hi")]
            result = client.chat_complete(messages)

            assert isinstance(result, ChatCompletionResponse)
            assert result.id == "msg_test123"
            assert len(result.content) == 1
            mock_post.assert_called_once()
        client.close()

    def test_non_stream_with_system(self) -> None:
        client = ClaudeAIClient(api_key="test-key")
        mock_response_data = {
            "id": "msg_456",
            "content": [{"type": "text", "text": "Response"}],
            "usage": {},
        }

        with patch.object(client._client, "post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response_data
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            messages = [Message(role="user", content="Hi")]
            result = client.chat_complete(messages, system="You are a pirate")

            assert isinstance(result, ChatCompletionResponse)
            call_kwargs = mock_post.call_args
            body = call_kwargs.kwargs.get("json", call_kwargs[1].get("json", {}))
            assert body["system"] == "You are a pirate"
        client.close()

    def test_non_stream_with_temperature(self) -> None:
        client = ClaudeAIClient(api_key="test-key")
        mock_response_data = {"id": "msg_789", "content": [], "usage": {}}

        with patch.object(client._client, "post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response_data
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            messages = [Message(role="user", content="Hi")]
            result = client.chat_complete(messages, temperature=0.5)

            assert isinstance(result, ChatCompletionResponse)
            call_kwargs = mock_post.call_args
            body = call_kwargs.kwargs.get("json", call_kwargs[1].get("json", {}))
            assert body["temperature"] == 0.5
        client.close()

    def test_non_stream_with_explicit_model(self) -> None:
        client = ClaudeAIClient(api_key="test-key")
        mock_response_data = {"id": "msg_abc", "content": [], "usage": {}}

        with patch.object(client._client, "post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response_data
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp

            messages = [Message(role="user", content="Hi")]
            result = client.chat_complete(messages, model="claude-opus-4")

            assert isinstance(result, ChatCompletionResponse)
            call_kwargs = mock_post.call_args
            body = call_kwargs.kwargs.get("json", call_kwargs[1].get("json", {}))
            assert body["model"] == "claude-opus-4"
        client.close()


# =============================================================================
# Streaming chat_complete Tests
# =============================================================================


class TestClaudeAIClientChatCompleteStream:
    def test_stream_returns_generator(self) -> None:
        client = ClaudeAIClient(api_key="test-key")
        mock_response_data = {
            "id": "msg_stream",
            "type": "message",
            "content": [],
            "usage": {},
        }

        with patch.object(client._client, "stream") as mock_stream:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.iter_lines.return_value = iter(
                [
                    'data: {"type": "content_block_delta", "delta": {"type": "content_block_delta", "text": "Hello", "index": 0}}',
                    'data: {"type": "content_block_delta", "delta": {"type": "content_block_delta", "text": " world", "index": 0}}',
                    "data: [DONE]",
                ]
            )
            mock_context.raise_for_status = MagicMock()
            mock_stream.return_value = mock_context

            messages = [Message(role="user", content="Hi")]
            result = client.chat_complete(messages, stream=True)

            assert hasattr(result, "__iter__")
            events = list(result)
            assert len(events) == 2
            assert events[0].type == "content_block_delta"
            assert events[0].delta.text == "Hello"
            assert events[1].delta.text == " world"
        client.close()

    def test_stream_sends_stream_true(self) -> None:
        client = ClaudeAIClient(api_key="test-key")

        with patch.object(client._client, "stream") as mock_stream:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_context)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_context.iter_lines.return_value = iter([])
            mock_context.raise_for_status = MagicMock()
            mock_stream.return_value = mock_context

            messages = [Message(role="user", content="Hi")]
            list(client.chat_complete(messages, stream=True))

            call_kwargs = mock_stream.call_args
            body = call_kwargs.kwargs.get("json", call_kwargs[1].get("json", {}))
            assert body["stream"] is True
        client.close()


# =============================================================================
# Provider Detection Tests
# =============================================================================


class TestGetApiProvider:
    def test_default_no_env_vars(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            # Remove env vars that might be set
            env = {k: v for k, v in os.environ.items()}
            for key in ["CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"]:
                if key in env:
                    del env[key]

            with patch.dict(os.environ, env, clear=True):
                result = get_api_provider()
                assert result == ProviderType.DIRECT

    def test_bedrock_env_var(self) -> None:
        with patch.dict(os.environ, {"CLAUDE_CODE_USE_BEDROCK": "1"}, clear=False):
            result = get_api_provider()
            assert result == ProviderType.AWS_BEDROCK

    def test_vertex_env_var(self) -> None:
        with patch.dict(os.environ, {"CLAUDE_CODE_USE_VERTEX": "true"}, clear=False):
            result = get_api_provider()
            assert result == ProviderType.GOOGLE_VERTEX

    def test_foundry_env_var(self) -> None:
        with patch.dict(os.environ, {"CLAUDE_CODE_USE_FOUNDRY": "1"}, clear=False):
            result = get_api_provider()
            assert result == ProviderType.AZURE_FOUNDRY

    def test_bedrock_takes_precedence(self) -> None:
        # Bedrock should be checked first
        with patch.dict(
            os.environ,
            {
                "CLAUDE_CODE_USE_BEDROCK": "1",
                "CLAUDE_CODE_USE_VERTEX": "1",
                "CLAUDE_CODE_USE_FOUNDRY": "1",
            },
            clear=False,
        ):
            result = get_api_provider()
            assert result == ProviderType.AWS_BEDROCK


# =============================================================================
# create_client Tests
# =============================================================================


class TestCreateClient:
    def test_create_client_with_explicit_key(self) -> None:
        client = create_client(api_key="my-secret-key")
        assert client.api_key == "my-secret-key"
        assert client.provider == ProviderType.DIRECT
        client.close()

    def test_create_client_with_env_var_key(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}, clear=False):
            client = create_client()
            assert client.api_key == "env-key"
            client.close()

    def test_create_client_with_provider(self) -> None:
        client = create_client(
            api_key="key", provider=ProviderType.AWS_BEDROCK
        )
        assert client.provider == ProviderType.AWS_BEDROCK
        client.close()

    def test_create_client_with_base_url(self) -> None:
        client = create_client(api_key="key", base_url="https://my.api.com")
        assert client.base_url == "https://my.api.com"
        client.close()

    def test_create_client_no_key_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key must be provided"):
                create_client(api_key=None)

    def test_create_client_auto_detects_provider(self) -> None:
        with patch.dict(os.environ, {"CLAUDE_CODE_USE_BEDROCK": "1", "ANTHROPIC_API_KEY": "key"}, clear=False):
            client = create_client()
            assert client.provider == ProviderType.AWS_BEDROCK
            client.close()

    def test_create_client_returns_usable_client(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            client = create_client()
            model = client._get_model(None)
            assert model == DEFAULT_MODELS[ProviderType.DIRECT]
            client.close()
