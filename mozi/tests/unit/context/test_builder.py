"""Tests for context builder."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from mozi.context.builder import ContextBuilder
from mozi.context.models import BuiltContext, ContextConfig


@pytest.mark.unit
class TestContextBuilder:
    """Tests for ContextBuilder class."""

    def test_init_default_config(self) -> None:
        """Test initialization with default config."""
        builder = ContextBuilder()
        assert builder.config is not None
        assert isinstance(builder.config, ContextConfig)

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = ContextConfig(max_tokens=50000)
        builder = ContextBuilder(config=config)
        assert builder.config.max_tokens == 50000

    def test_init_with_dependencies(self) -> None:
        """Test initialization with session manager and memory retriever."""
        session_manager = MagicMock()
        memory_retriever = MagicMock()
        builder = ContextBuilder(
            session_manager=session_manager,
            memory_retriever=memory_retriever,
        )
        assert builder._session_manager is session_manager
        assert builder._memory_retriever is memory_retriever

    @pytest.mark.asyncio
    async def test_build_basic(self) -> None:
        """Test basic context building."""
        builder = ContextBuilder()
        context = await builder.build(
            session_id="test-session",
            system_prompt="Test system prompt",
        )
        assert isinstance(context, BuiltContext)
        assert context.system_prompt == "Test system prompt"
        assert context.total_tokens >= 0

    @pytest.mark.asyncio
    async def test_build_with_history_disabled(self) -> None:
        """Test building context without history."""
        config = ContextConfig(include_history=False)
        builder = ContextBuilder(config=config)
        context = await builder.build(
            session_id="test-session",
            system_prompt="Test",
        )
        assert context.messages == []

    @pytest.mark.asyncio
    async def test_build_with_memory_disabled(self) -> None:
        """Test building context without memory."""
        config = ContextConfig(include_memory=False)
        builder = ContextBuilder(config=config)
        context = await builder.build(
            session_id="test-session",
            system_prompt="Test",
        )
        assert context.memory_results == []

    @pytest.mark.asyncio
    async def test_build_with_additional_context(self) -> None:
        """Test building with additional context metadata."""
        builder = ContextBuilder()
        context = await builder.build(
            session_id="test-session",
            additional_context={"key": "value"},
        )
        assert context.metadata["key"] == "value"

    @pytest.mark.asyncio
    async def test_gather_history_with_session_manager(self) -> None:
        """Test gathering history from session manager."""
        mock_message = MagicMock()
        mock_message.role.value = "user"
        mock_message.content = "Test message"

        session_manager = MagicMock()
        session_manager.get_messages = AsyncMock(return_value=[mock_message])

        builder = ContextBuilder(session_manager=session_manager)
        messages = await builder._gather_history("test-session")

        assert len(messages) == 1
        assert "User: Test message" in messages[0]

    @pytest.mark.asyncio
    async def test_gather_history_without_session_manager(self) -> None:
        """Test gathering history without session manager."""
        builder = ContextBuilder()
        messages = await builder._gather_history("test-session")
        assert messages == []

    @pytest.mark.asyncio
    async def test_gather_memory_with_retriever(self) -> None:
        """Test gathering memory from retriever."""
        mock_result = MagicMock()
        mock_result.content = "Retrieved memory"

        memory_retriever = MagicMock()
        memory_retriever.retrieve = AsyncMock(return_value=[mock_result])

        builder = ContextBuilder(memory_retriever=memory_retriever)
        memories = await builder._gather_memory("test-session")

        assert len(memories) == 1
        assert memories[0] == "Retrieved memory"

    @pytest.mark.asyncio
    async def test_gather_memory_without_retriever(self) -> None:
        """Test gathering memory without retriever."""
        builder = ContextBuilder()
        memories = await builder._gather_memory("test-session")
        assert memories == []

    @pytest.mark.asyncio
    async def test_gather_memory_handles_exception(self) -> None:
        """Test that memory gathering handles exceptions gracefully."""
        memory_retriever = MagicMock()
        memory_retriever.retrieve = AsyncMock(side_effect=Exception("Test error"))

        builder = ContextBuilder(memory_retriever=memory_retriever)
        memories = await builder._gather_memory("test-session")
        assert memories == []
