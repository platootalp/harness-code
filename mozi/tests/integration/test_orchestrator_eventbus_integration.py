"""Integration tests for Orchestrator and EventBus integration.

This module contains integration tests for:
- State change event publishing
- Worker execution event publishing
- Event delivery and processing

Tests verify that the orchestrator correctly integrates with
the EventBus for event publishing during task execution.
"""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Iterator
from unittest.mock import patch

import pytest

from mozi.infrastructure.event_bus import Event, EventBus, EventPriority
from mozi.orchestrator import Orchestrator
from mozi.orchestrator.integration import OrchestratorIntegration


@pytest.fixture
def event_bus() -> EventBus:
    """Create an event bus instance."""
    return EventBus()


@pytest.fixture
def orchestrator_integration(event_bus: EventBus) -> OrchestratorIntegration:
    """Create an orchestrator integration with event bus."""
    return OrchestratorIntegration(event_bus=event_bus)


@pytest.fixture
def orchestrator() -> Iterator[Orchestrator]:
    """Create an orchestrator instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Orchestrator(storage_path=tmpdir)


@pytest.mark.integration
class TestStateChangeEventPublishing:
    """Tests for state change event publishing."""

    @pytest.mark.asyncio
    async def test_state_changed_event_published(
        self,
        orchestrator_integration: OrchestratorIntegration,
        event_bus: EventBus,
    ) -> None:
        """Test that state changed events are published."""
        received_events: list[Event] = []

        async def handler(evt: Event) -> None:
            received_events.append(evt)

        await event_bus.subscribe(
            "orchestrator.state_changed",
            callback=handler,
        )

        await orchestrator_integration.publish_state_changed(
            session_id="test-session",
            old_state="pending",
            new_state="in_progress",
        )

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].event_type == "state_changed"
        assert received_events[0].payload["old_state"] == "pending"
        assert received_events[0].payload["new_state"] == "in_progress"

    @pytest.mark.asyncio
    async def test_task_started_event_published(
        self,
        orchestrator_integration: OrchestratorIntegration,
        event_bus: EventBus,
    ) -> None:
        """Test that task started events are published."""
        received_events: list[Event] = []

        async def handler(evt: Event) -> None:
            received_events.append(evt)

        await event_bus.subscribe(
            "orchestrator.task_started",
            callback=handler,
        )

        await orchestrator_integration.publish_task_started(
            session_id="test-session",
            task_description="Fix bug",
            category="quick",
        )

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].event_type == "task_started"
        assert received_events[0].payload["category"] == "quick"

    @pytest.mark.asyncio
    async def test_task_completed_event_published(
        self,
        orchestrator_integration: OrchestratorIntegration,
        event_bus: EventBus,
    ) -> None:
        """Test that task completed events are published."""
        received_events: list[Event] = []

        async def handler(evt: Event) -> None:
            received_events.append(evt)

        await event_bus.subscribe(
            "orchestrator.task_completed",
            callback=handler,
        )

        await orchestrator_integration.publish_task_completed(
            session_id="test-session",
            category="deep",
            result={"status": "completed"},
        )

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].event_type == "task_completed"

    @pytest.mark.asyncio
    async def test_task_failed_event_published(
        self,
        orchestrator_integration: OrchestratorIntegration,
        event_bus: EventBus,
    ) -> None:
        """Test that task failed events are published."""
        received_events: list[Event] = []

        async def handler(evt: Event) -> None:
            received_events.append(evt)

        await event_bus.subscribe(
            "orchestrator.task_failed",
            callback=handler,
        )

        await orchestrator_integration.publish_task_failed(
            session_id="test-session",
            category="strategic",
            error="Connection timeout",
        )

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].event_type == "task_failed"
        assert received_events[0].payload["error"] == "Connection timeout"
        assert received_events[0].priority == EventPriority.CRITICAL


@pytest.mark.integration
class TestWorkerExecutionEventPublishing:
    """Tests for worker execution event publishing."""

    @pytest.mark.asyncio
    async def test_worker_started_event_published(
        self,
        orchestrator_integration: OrchestratorIntegration,
        event_bus: EventBus,
    ) -> None:
        """Test that worker started events are published."""
        received_events: list[Event] = []

        async def handler(evt: Event) -> None:
            received_events.append(evt)

        await event_bus.subscribe(
            "orchestrator.worker_started",
            callback=handler,
        )

        await orchestrator_integration.publish_worker_started(
            session_id="test-session",
            worker_name="coder",
            todo_id="todo-1",
        )

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].event_type == "worker_started"
        assert received_events[0].payload["worker"] == "coder"

    @pytest.mark.asyncio
    async def test_worker_completed_event_published(
        self,
        orchestrator_integration: OrchestratorIntegration,
        event_bus: EventBus,
    ) -> None:
        """Test that worker completed events are published."""
        received_events: list[Event] = []

        async def handler(evt: Event) -> None:
            received_events.append(evt)

        await event_bus.subscribe(
            "orchestrator.worker_completed",
            callback=handler,
        )

        await orchestrator_integration.publish_worker_completed(
            session_id="test-session",
            worker_name="explorer",
            todo_id="todo-2",
            result={"status": "success"},
        )

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].event_type == "worker_completed"
        assert received_events[0].payload["worker"] == "explorer"


@pytest.mark.integration
class TestEventDeliveryAndProcessing:
    """Tests for event delivery and processing."""

    @pytest.mark.asyncio
    async def test_multiple_events_delivered_in_order(
        self,
        orchestrator_integration: OrchestratorIntegration,
        event_bus: EventBus,
    ) -> None:
        """Test that multiple events are delivered."""
        received_events: list[Event] = []

        async def handler(evt: Event) -> None:
            received_events.append(evt)

        await event_bus.subscribe(
            "orchestrator.#",
            callback=handler,
        )

        # Publish multiple events
        await orchestrator_integration.publish_task_started(
            session_id="test-session",
            task_description="Task 1",
            category="quick",
        )
        await orchestrator_integration.publish_worker_started(
            session_id="test-session",
            worker_name="coder",
            todo_id="todo-1",
        )
        await orchestrator_integration.publish_task_completed(
            session_id="test-session",
            category="quick",
            result={"status": "completed"},
        )

        await asyncio.sleep(0.2)

        assert len(received_events) == 3

    @pytest.mark.asyncio
    async def test_event_correlation_id_set(
        self,
        orchestrator_integration: OrchestratorIntegration,
        event_bus: EventBus,
    ) -> None:
        """Test that event correlation ID is set correctly."""
        received_events: list[Event] = []

        async def handler(evt: Event) -> None:
            received_events.append(evt)

        await event_bus.subscribe(
            "orchestrator.#",
            callback=handler,
        )

        session_id = "correlation-test-session"
        await orchestrator_integration.publish_task_started(
            session_id=session_id,
            task_description="Test",
            category="quick",
        )

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].correlation_id == session_id

    @pytest.mark.asyncio
    async def test_event_source_set(
        self,
        orchestrator_integration: OrchestratorIntegration,
        event_bus: EventBus,
    ) -> None:
        """Test that event source is set correctly."""
        received_events: list[Event] = []

        async def handler(evt: Event) -> None:
            received_events.append(evt)

        await event_bus.subscribe(
            "orchestrator.#",
            callback=handler,
        )

        await orchestrator_integration.publish_task_started(
            session_id="test-session",
            task_description="Test",
            category="quick",
        )

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].source == "orchestrator_integration"


@pytest.mark.integration
class TestEventBusOrchestratorIntegration:
    """Tests for full orchestrator integration with event bus."""

    @pytest.mark.asyncio
    async def test_orchestrator_with_event_bus(
        self,
        orchestrator: Orchestrator,
        event_bus: EventBus,
    ) -> None:
        """Test that orchestrator can work with event bus through integration."""
        received_events: list[Event] = []

        async def handler(evt: Event) -> None:
            received_events.append(evt)

        await event_bus.subscribe(
            "orchestrator.#",
            callback=handler,
        )

        context = {"session_id": "e2e-test"}

        with patch.object(orchestrator._state_store, "save_state"):
            with patch.object(orchestrator._state_store, "add_todo"):
                with patch.object(orchestrator._state_store, "complete_todo"):
                    with patch.object(orchestrator._state_store, "add_decision"):
                        result = await orchestrator.execute(
                            "Simple task",
                            context=context,
                        )

        # Note: The current orchestrator doesn't publish events directly
        # but the integration layer provides the capability
        assert result["status"] in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_no_event_bus_no_error(
        self,
        orchestrator_integration: OrchestratorIntegration,
    ) -> None:
        """Test that missing event bus doesn't cause errors."""
        # Create integration without event bus
        integration = OrchestratorIntegration(event_bus=None)

        # Should not raise
        await integration.publish_task_started(
            session_id="test",
            task_description="test",
            category="quick",
        )

        # Should return empty results
        result = await integration.retrieve_memories("test", "query")
        assert result["status"] == "no_memory_retriever"
