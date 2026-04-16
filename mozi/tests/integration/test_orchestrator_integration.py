"""Integration tests for OrchestratorIntegration class.

This module contains integration tests for:
- Session message operations (add_session_message, get_session_messages)
- Context building operations
- Memory retrieval and storage
- Singleton pattern (get_integration)
- Event publishing for context and memory operations
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.infrastructure.event_bus import BaseEventBus, EventPriority
from mozi.orchestrator.integration import (
    OrchestratorIntegration,
    get_integration,
)


@pytest.fixture
def mock_session_manager() -> MagicMock:
    """Create a mock session manager."""
    manager = MagicMock()
    manager.add_message = AsyncMock()
    manager.get_messages = AsyncMock(return_value=[])
    return manager


@pytest.fixture
def mock_context_builder() -> MagicMock:
    """Create a mock context builder."""
    builder = MagicMock()
    context = MagicMock()
    context.total_tokens = 100
    context.to_dict = MagicMock(return_value={"messages": []})
    builder.build = AsyncMock(return_value=context)
    return builder


@pytest.fixture
def mock_memory_retriever() -> MagicMock:
    """Create a mock memory retriever."""
    retriever = MagicMock()
    retriever.hybrid_search = AsyncMock(return_value=[])
    retriever.long_term = MagicMock()
    retriever.long_term.add = AsyncMock()
    return retriever


@pytest.fixture
def mock_event_bus() -> MagicMock:
    """Create a mock event bus."""
    bus = MagicMock(spec=BaseEventBus)
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def integration(
    mock_session_manager: MagicMock,
    mock_context_builder: MagicMock,
    mock_memory_retriever: MagicMock,
    mock_event_bus: MagicMock,
) -> OrchestratorIntegration:
    """Create an OrchestratorIntegration instance with mocks."""
    return OrchestratorIntegration(
        session_manager=mock_session_manager,
        context_builder=mock_context_builder,
        memory_retriever=mock_memory_retriever,
        event_bus=mock_event_bus,
    )


@pytest.mark.integration
class TestAddSessionMessage:
    """Tests for add_session_message method."""

    @pytest.mark.asyncio
    async def test_add_session_message_success(
        self,
        integration: OrchestratorIntegration,
        mock_session_manager: MagicMock,
    ) -> None:
        """Test successfully adding a session message."""
        from mozi.session.models import Message

        mock_message = Message(
            id="msg-123",
            session_id="session-1",
            role="user",
            content="Hello",
        )
        mock_session_manager.add_message = AsyncMock(return_value=mock_message)

        result = await integration.add_session_message(
            session_id="session-1",
            role="user",
            content="Hello",
        )

        assert result["status"] == "success"
        assert result["message_id"] == "msg-123"
        mock_session_manager.add_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_session_message_no_manager(
        self,
        mock_context_builder: MagicMock,
        mock_memory_retriever: MagicMock,
    ) -> None:
        """Test add_session_message when no session manager is set."""
        integration = OrchestratorIntegration(
            session_manager=None,
            context_builder=mock_context_builder,
            memory_retriever=mock_memory_retriever,
        )

        result = await integration.add_session_message(
            session_id="session-1",
            role="user",
            content="Hello",
        )

        assert result["status"] == "no_session_manager"

    @pytest.mark.asyncio
    async def test_add_session_message_session_not_found(
        self,
        integration: OrchestratorIntegration,
        mock_session_manager: MagicMock,
    ) -> None:
        """Test add_session_message when session is not found."""
        mock_session_manager.add_message = AsyncMock(return_value=None)

        result = await integration.add_session_message(
            session_id="nonexistent",
            role="user",
            content="Hello",
        )

        assert result["status"] == "session_not_found"

    @pytest.mark.asyncio
    async def test_add_session_message_with_metadata(
        self,
        integration: OrchestratorIntegration,
        mock_session_manager: MagicMock,
    ) -> None:
        """Test add_session_message with metadata."""
        from mozi.session.models import Message

        mock_message = Message(
            id="msg-456",
            session_id="session-1",
            role="assistant",
            content="Response",
        )
        mock_session_manager.add_message = AsyncMock(return_value=mock_message)

        metadata = {"tool_calls": [], "tokens": 100}
        result = await integration.add_session_message(
            session_id="session-1",
            role="assistant",
            content="Response",
            metadata=metadata,
        )

        assert result["status"] == "success"
        assert result["message_id"] == "msg-456"
        mock_session_manager.add_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_session_message_exception(
        self,
        mock_session_manager: MagicMock,
        mock_context_builder: MagicMock,
        mock_memory_retriever: MagicMock,
    ) -> None:
        """Test add_session_message when exception occurs."""
        mock_session_manager.add_message = AsyncMock(
            side_effect=Exception("Database error")
        )
        integration = OrchestratorIntegration(
            session_manager=mock_session_manager,
            context_builder=mock_context_builder,
            memory_retriever=mock_memory_retriever,
        )

        result = await integration.add_session_message(
            session_id="session-1",
            role="user",
            content="Hello",
        )

        assert result["status"] == "error"
        assert "Database error" in result["error"]


@pytest.mark.integration
class TestGetSessionMessages:
    """Tests for get_session_messages method."""

    @pytest.mark.asyncio
    async def test_get_session_messages_success(
        self,
        integration: OrchestratorIntegration,
        mock_session_manager: MagicMock,
    ) -> None:
        """Test successfully getting session messages."""
        from mozi.session.models import Message, MessageRole

        mock_messages = [
            Message(id="msg-1", session_id="s1", role=MessageRole.USER, content="Hi"),
            Message(id="msg-2", session_id="s1", role=MessageRole.ASSISTANT, content="Hi there"),
        ]
        mock_session_manager.get_messages = AsyncMock(return_value=mock_messages)

        result = await integration.get_session_messages(session_id="s1")

        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["messages"]) == 2
        assert result["messages"][0]["id"] == "msg-1"
        assert result["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_session_messages_empty(
        self,
        integration: OrchestratorIntegration,
        mock_session_manager: MagicMock,
    ) -> None:
        """Test getting messages when session is empty."""
        mock_session_manager.get_messages = AsyncMock(return_value=[])

        result = await integration.get_session_messages(session_id="s1")

        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["messages"] == []

    @pytest.mark.asyncio
    async def test_get_session_messages_no_manager(
        self,
        mock_context_builder: MagicMock,
        mock_memory_retriever: MagicMock,
    ) -> None:
        """Test get_session_messages when no session manager is set."""
        integration = OrchestratorIntegration(
            session_manager=None,
            context_builder=mock_context_builder,
            memory_retriever=mock_memory_retriever,
        )

        result = await integration.get_session_messages(session_id="s1")

        assert result["status"] == "no_session_manager"
        assert result["messages"] == []

    @pytest.mark.asyncio
    async def test_get_session_messages_exception(
        self,
        mock_session_manager: MagicMock,
        mock_context_builder: MagicMock,
        mock_memory_retriever: MagicMock,
    ) -> None:
        """Test get_session_messages when exception occurs."""
        mock_session_manager.get_messages = AsyncMock(
            side_effect=Exception("Database error")
        )
        integration = OrchestratorIntegration(
            session_manager=mock_session_manager,
            context_builder=mock_context_builder,
            memory_retriever=mock_memory_retriever,
        )

        result = await integration.get_session_messages(session_id="s1")

        assert result["status"] == "error"
        assert "Database error" in result["error"]
        assert result["messages"] == []


@pytest.mark.integration
class TestBuildContext:
    """Tests for build_context method."""

    @pytest.mark.asyncio
    async def test_build_context_success(
        self,
        integration: OrchestratorIntegration,
        mock_context_builder: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """Test successfully building context."""
        result = await integration.build_context(
            session_id="s1",
            system_prompt="You are helpful.",
        )

        assert result["status"] == "success"
        assert result["total_tokens"] == 100
        mock_context_builder.build.assert_called_once_with(
            session_id="s1",
            system_prompt="You are helpful.",
        )
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_context_no_builder(
        self,
        mock_session_manager: MagicMock,
        mock_memory_retriever: MagicMock,
    ) -> None:
        """Test build_context when no context builder is set."""
        integration = OrchestratorIntegration(
            session_manager=mock_session_manager,
            context_builder=None,
            memory_retriever=mock_memory_retriever,
        )

        result = await integration.build_context(session_id="s1")

        assert result["status"] == "no_context_builder"

    @pytest.mark.asyncio
    async def test_build_context_error(
        self,
        mock_context_builder: MagicMock,
        mock_session_manager: MagicMock,
        mock_memory_retriever: MagicMock,
    ) -> None:
        """Test build_context when error occurs."""
        mock_context_builder.build = AsyncMock(
            side_effect=Exception("Context build failed")
        )
        integration = OrchestratorIntegration(
            session_manager=mock_session_manager,
            context_builder=mock_context_builder,
            memory_retriever=mock_memory_retriever,
        )

        result = await integration.build_context(session_id="s1")

        assert result["status"] == "error"
        assert "Context build failed" in result["error"]


@pytest.mark.integration
class TestRetrieveMemories:
    """Tests for retrieve_memories method."""

    @pytest.mark.asyncio
    async def test_retrieve_memories_success(
        self,
        integration: OrchestratorIntegration,
        mock_memory_retriever: MagicMock,
        mock_event_bus: MagicMock,
    ) -> None:
        """Test successfully retrieving memories."""
        from unittest.mock import MagicMock as MockMemory

        memory = MockMemory()
        memory.block = MockMemory()
        memory.block.content = "Previous task"
        memory.block.id = "mem-1"
        memory.score = 0.95
        memory.source = "session"
        mock_memory_retriever.hybrid_search = AsyncMock(return_value=[memory])

        result = await integration.retrieve_memories(
            session_id="s1",
            query="task",
            limit=5,
        )

        assert result["status"] == "success"
        assert result["count"] == 1
        assert result["memories"][0]["content"] == "Previous task"
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_memories_no_retriever(
        self,
        mock_session_manager: MagicMock,
        mock_context_builder: MagicMock,
    ) -> None:
        """Test retrieve_memories when no memory retriever is set."""
        integration = OrchestratorIntegration(
            session_manager=mock_session_manager,
            context_builder=mock_context_builder,
            memory_retriever=None,
        )

        result = await integration.retrieve_memories(session_id="s1", query="task")

        assert result["status"] == "no_memory_retriever"
        assert result["memories"] == []

    @pytest.mark.asyncio
    async def test_retrieve_memories_error(
        self,
        mock_memory_retriever: MagicMock,
        mock_session_manager: MagicMock,
        mock_context_builder: MagicMock,
    ) -> None:
        """Test retrieve_memories when error occurs."""
        mock_memory_retriever.hybrid_search = AsyncMock(
            side_effect=Exception("Vector DB error")
        )
        integration = OrchestratorIntegration(
            session_manager=mock_session_manager,
            context_builder=mock_context_builder,
            memory_retriever=mock_memory_retriever,
        )

        result = await integration.retrieve_memories(session_id="s1", query="task")

        assert result["status"] == "error"
        assert "Vector DB error" in result["error"]
        assert result["memories"] == []


@pytest.mark.integration
class TestStoreMemory:
    """Tests for store_memory method."""

    @pytest.mark.asyncio
    async def test_store_memory_success(
        self,
        integration: OrchestratorIntegration,
        mock_memory_retriever: MagicMock,
    ) -> None:
        """Test successfully storing a memory."""
        from unittest.mock import MagicMock as MockBlock

        block = MockBlock()
        block.id = "block-123"
        mock_memory_retriever.long_term.add = AsyncMock(return_value=block)

        result = await integration.store_memory(
            session_id="s1",
            content="Learned something",
            memory_type="session",
            importance=0.8,
        )

        assert result["status"] == "success"
        assert result["block_id"] == "block-123"

    @pytest.mark.asyncio
    async def test_store_memory_no_retriever(
        self,
        mock_session_manager: MagicMock,
        mock_context_builder: MagicMock,
    ) -> None:
        """Test store_memory when no memory retriever is set."""
        integration = OrchestratorIntegration(
            session_manager=mock_session_manager,
            context_builder=mock_context_builder,
            memory_retriever=None,
        )

        result = await integration.store_memory(
            session_id="s1",
            content="Test memory",
        )

        assert result["status"] == "no_memory_retriever"

    @pytest.mark.asyncio
    async def test_store_memory_error(
        self,
        mock_memory_retriever: MagicMock,
        mock_session_manager: MagicMock,
        mock_context_builder: MagicMock,
    ) -> None:
        """Test store_memory when error occurs."""
        mock_memory_retriever.long_term.add = AsyncMock(
            side_effect=Exception("Storage failed")
        )
        integration = OrchestratorIntegration(
            session_manager=mock_session_manager,
            context_builder=mock_context_builder,
            memory_retriever=mock_memory_retriever,
        )

        result = await integration.store_memory(
            session_id="s1",
            content="Test memory",
        )

        assert result["status"] == "error"
        assert "Storage failed" in result["error"]


@pytest.mark.integration
class TestGetIntegrationSingleton:
    """Tests for get_integration singleton function."""

    def test_get_integration_creates_instance(self) -> None:
        """Test that get_integration creates an instance."""
        # Reset global state
        import mozi.orchestrator.integration as integration_module
        integration_module._integration = None

        integration = get_integration()

        assert integration is not None
        assert isinstance(integration, OrchestratorIntegration)
        # Clean up
        integration_module._integration = None

    def test_get_integration_returns_same_instance(self) -> None:
        """Test that get_integration returns the same instance."""
        import mozi.orchestrator.integration as integration_module
        integration_module._integration = None

        integration1 = get_integration()
        integration2 = get_integration()

        assert integration1 is integration2
        # Clean up
        integration_module._integration = None

    def test_get_integration_with_custom_managers(
        self,
        mock_session_manager: MagicMock,
        mock_context_builder: MagicMock,
    ) -> None:
        """Test get_integration with custom managers."""
        import mozi.orchestrator.integration as integration_module
        integration_module._integration = None

        integration = get_integration(
            session_manager=mock_session_manager,
            context_builder=mock_context_builder,
        )

        assert integration.session_manager is mock_session_manager
        assert integration.context_builder is mock_context_builder
        # Clean up
        integration_module._integration = None


@pytest.mark.integration
class TestPublishContextBuilt:
    """Tests for publish_context_built method."""

    @pytest.mark.asyncio
    async def test_publish_context_built(
        self,
        integration: OrchestratorIntegration,
        mock_event_bus: MagicMock,
    ) -> None:
        """Test publishing context built event."""
        await integration.publish_context_built(
            session_id="s1",
            token_count=500,
        )

        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.topic == "orchestrator.context_built"
        assert event.payload["token_count"] == 500

    @pytest.mark.asyncio
    async def test_publish_context_built_no_event_bus(
        self,
        mock_session_manager: MagicMock,
        mock_context_builder: MagicMock,
        mock_memory_retriever: MagicMock,
    ) -> None:
        """Test publishing when no event bus is set."""
        integration = OrchestratorIntegration(
            session_manager=mock_session_manager,
            context_builder=mock_context_builder,
            memory_retriever=mock_memory_retriever,
            event_bus=None,
        )

        # Should not raise
        await integration.publish_context_built(session_id="s1", token_count=100)


@pytest.mark.integration
class TestPublishMemoryRetrieved:
    """Tests for publish_memory_retrieved method."""

    @pytest.mark.asyncio
    async def test_publish_memory_retrieved(
        self,
        integration: OrchestratorIntegration,
        mock_event_bus: MagicMock,
    ) -> None:
        """Test publishing memory retrieved event."""
        await integration.publish_memory_retrieved(
            session_id="s1",
            memory_count=3,
        )

        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.topic == "orchestrator.memory_retrieved"
        assert event.payload["memory_count"] == 3

    @pytest.mark.asyncio
    async def test_publish_memory_retrieved_no_event_bus(
        self,
        mock_session_manager: MagicMock,
        mock_context_builder: MagicMock,
        mock_memory_retriever: MagicMock,
    ) -> None:
        """Test publishing when no event bus is set."""
        integration = OrchestratorIntegration(
            session_manager=mock_session_manager,
            context_builder=mock_context_builder,
            memory_retriever=mock_memory_retriever,
            event_bus=None,
        )

        # Should not raise
        await integration.publish_memory_retrieved(session_id="s1", memory_count=5)
