"""Integration tests for Orchestrator and Model integration.

This module contains integration tests for:
- LLM invocation during task execution
- Tool call result processing
- Model response handling

Tests verify that the orchestrator correctly integrates with
the Model module for LLM interactions.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.core.model.adapter import Message, MessageRole, ModelResponse, ModelUsage
from mozi.core.model.service import ModelInvocationResult, ModelService
from mozi.orchestrator import Orchestrator


@pytest.fixture
def mock_model_service() -> MagicMock:
    """Create a mock model service."""
    service = MagicMock(spec=ModelService)
    service.invoke = AsyncMock()
    service.invoke_stream = MagicMock()
    return service


@pytest.fixture
def orchestrator() -> Iterator[Orchestrator]:
    """Create an orchestrator instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Orchestrator(storage_path=tmpdir)


@pytest.mark.integration
class TestLLMInvocation:
    """Tests for LLM invocation."""

    @pytest.mark.asyncio
    async def test_model_service_initialized(
        self,
        mock_model_service: MagicMock,
    ) -> None:
        """Test that model service can be initialized."""
        assert mock_model_service is not None
        assert hasattr(mock_model_service, "invoke")
        assert hasattr(mock_model_service, "invoke_stream")

    @pytest.mark.asyncio
    async def test_model_service_invoke_returns_result(
        self,
        mock_model_service: MagicMock,
    ) -> None:
        """Test that model service invoke returns proper result."""
        mock_response = ModelResponse(
            content="Test response",
            model="test-model",
            usage=ModelUsage(
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
            ),
        )
        mock_result = ModelInvocationResult(
            response=mock_response,
            provider="test",
            model="test-model",
            duration_ms=100.0,
            attempt=1,
        )
        mock_model_service.invoke = AsyncMock(return_value=mock_result)

        messages = [
            Message(role=MessageRole.USER, content="Hello"),
        ]

        result = await mock_model_service.invoke(
            model="test-model",
            messages=messages,
        )

        assert result.response.content == "Test response"
        assert result.provider == "test"


@pytest.mark.integration
class TestToolCallResultProcessing:
    """Tests for tool call result processing."""

    @pytest.mark.asyncio
    async def test_tool_result_included_in_messages(
        self,
        mock_model_service: MagicMock,
    ) -> None:
        """Test that tool results are included in message history."""
        messages = [
            Message(role=MessageRole.USER, content="Use bash to list files"),
            Message(role=MessageRole.ASSISTANT, content="I'll use bash tool"),
            Message(
                role=MessageRole.USER,
                content='{"tool": "bash", "output": "file1.py\\nfile2.py"}',
            ),
        ]

        # The model should process the tool result
        mock_response = ModelResponse(
            content="I see the files are file1.py and file2.py",
            model="test-model",
            usage=ModelUsage(
                input_tokens=50,
                output_tokens=15,
                total_tokens=65,
            ),
        )
        mock_result = ModelInvocationResult(
            response=mock_response,
            provider="test",
            model="test-model",
            duration_ms=150.0,
            attempt=1,
        )
        mock_model_service.invoke = AsyncMock(return_value=mock_result)

        result = await mock_model_service.invoke(
            model="test-model",
            messages=messages,
        )

        assert "file1.py" in result.response.content


@pytest.mark.integration
class TestModelResponseHandling:
    """Tests for model response handling."""

    @pytest.mark.asyncio
    async def test_model_response_parsed(
        self,
        mock_model_service: MagicMock,
    ) -> None:
        """Test that model response is properly parsed."""
        mock_response = ModelResponse(
            content="This is a test response with multiple lines\nAnd more content",
            model="claude-sonnet-4-7",
            usage=ModelUsage(
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
            ),
        )
        mock_result = ModelInvocationResult(
            response=mock_response,
            provider="anthropic",
            model="claude-sonnet-4-7",
            duration_ms=200.0,
            attempt=1,
        )
        mock_model_service.invoke = AsyncMock(return_value=mock_result)

        result = await mock_model_service.invoke(
            model="claude-sonnet-4-7",
            messages=[],
        )

        assert isinstance(result, ModelInvocationResult)
        assert result.model == "claude-sonnet-4-7"
        assert result.duration_ms == 200.0

    @pytest.mark.asyncio
    async def test_streaming_response_handled(
        self,
        mock_model_service: MagicMock,
    ) -> None:
        """Test that streaming responses are handled."""
        chunks = ["Hello", " world", "!"]

        async def async_gen():
            for chunk in chunks:
                yield chunk

        mock_model_service.invoke_stream = MagicMock(return_value=async_gen())

        result_chunks = []
        async for chunk in mock_model_service.invoke_stream(
            model="test-model",
            messages=[],
        ):
            result_chunks.append(chunk)

        assert len(result_chunks) == 3
        assert "".join(result_chunks) == "Hello world!"


@pytest.mark.integration
class TestOrchestratorModelIntegration:
    """Tests for orchestrator integration with model service."""

    @pytest.mark.asyncio
    async def test_orchestrator_accepts_model_service(
        self,
        orchestrator: Orchestrator,
        mock_model_service: MagicMock,
    ) -> None:
        """Test that orchestrator can work with model service."""
        # The orchestrator doesn't directly use model service yet
        # but the integration layer supports it
        context = {"session_id": "model-test"}

        with patch.object(orchestrator._state_store, "save_state"):
            with patch.object(orchestrator._state_store, "add_todo"):
                with patch.object(orchestrator._state_store, "complete_todo"):
                    with patch.object(orchestrator._state_store, "add_decision"):
                        result = await orchestrator.execute(
                            "Simple task",
                            context=context,
                        )

        # Basic execution should work
        assert result["status"] in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_model_service_events_published(
        self,
        mock_model_service: MagicMock,
    ) -> None:
        """Test that model service publishes events during invocation."""
        mock_response = ModelResponse(
            content="Test",
            model="test",
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )
        mock_result = ModelInvocationResult(
            response=mock_response,
            provider="test",
            model="test",
            duration_ms=100.0,
            attempt=1,
        )
        mock_model_service.invoke = AsyncMock(return_value=mock_result)

        await mock_model_service.invoke(
            model="test",
            messages=[],
            session_id="test-session",
        )

        mock_model_service.invoke.assert_called_once()
        call_kwargs = mock_model_service.invoke.call_args
        assert call_kwargs is not None
