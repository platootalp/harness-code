"""Orchestrator Integration Module.

This module provides integration between the Orchestrator and other Mozi modules:
- Session: For session management and message persistence
- Context: For context building and management
- Memory: For memory retrieval and storage
- Model: For LLM invocation
- EventBus: For event publishing

It wraps the base Orchestrator with full module integration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mozi.infrastructure.event_bus import BaseEventBus, Event, EventPriority

if TYPE_CHECKING:
    from mozi.context.builder import ContextBuilder
    from mozi.core.model.service import ModelService
    from mozi.memory.retriever import MemoryRetriever
    from mozi.session.manager import SessionManager


# Event topics for orchestrator operations
ORCHESTRATOR_TOPIC = "orchestrator"
ORCHESTRATOR_STARTED_EVENT = "task_started"
ORCHESTRATOR_COMPLETED_EVENT = "task_completed"
ORCHESTRATOR_FAILED_EVENT = "task_failed"
ORCHESTRATOR_STATE_CHANGED_EVENT = "state_changed"
ORCHESTRATOR_WORKER_STARTED_EVENT = "worker_started"
ORCHESTRATOR_WORKER_COMPLETED_EVENT = "worker_completed"
ORCHESTRATOR_CONTEXT_BUILT_EVENT = "context_built"
ORCHESTRATOR_MEMORY_RETRIEVED_EVENT = "memory_retrieved"


class OrchestratorIntegration:
    """Integration layer connecting Orchestrator with other modules.

    This class wraps the core Orchestrator and provides:
    - Session integration for message persistence
    - Context integration for context building
    - Memory integration for memory retrieval/storage
    - Model integration for LLM calls
    - Event publishing for observability

    Attributes:
        session_manager: Optional session manager for session integration.
        context_builder: Optional context builder for context integration.
        memory_retriever: Optional memory retriever for memory integration.
        model_service: Optional model service for LLM integration.
        event_bus: Optional event bus for event publishing.
    """

    def __init__(
        self,
        session_manager: SessionManager | None = None,
        context_builder: ContextBuilder | None = None,
        memory_retriever: MemoryRetriever | None = None,
        model_service: ModelService | None = None,
        event_bus: BaseEventBus | None = None,
    ) -> None:
        """Initialize the orchestrator integration.

        Args:
            session_manager: Session manager for session integration.
            context_builder: Context builder for context integration.
            memory_retriever: Memory retriever for memory integration.
            model_service: Model service for LLM integration.
            event_bus: Event bus for event publishing.
        """
        self.session_manager = session_manager
        self.context_builder = context_builder
        self.memory_retriever = memory_retriever
        self.model_service = model_service
        self.event_bus = event_bus

    async def publish_event(
        self,
        topic: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        """Publish an event to the event bus.

        Args:
            topic: Event topic.
            event_type: Type of event.
            payload: Event payload.
            correlation_id: Optional correlation ID.
            priority: Event priority.
        """
        if self.event_bus is None:
            return

        event = Event(
            topic=topic,
            event_type=event_type,
            payload=payload,
            priority=priority,
            correlation_id=correlation_id,
            source="orchestrator_integration",
        )

        await self.event_bus.publish(event)

    async def publish_task_started(
        self,
        session_id: str,
        task_description: str,
        category: str,
    ) -> None:
        """Publish task started event.

        Args:
            session_id: Session ID.
            task_description: Description of the task.
            category: Task category.
        """
        await self.publish_event(
            topic=f"{ORCHESTRATOR_TOPIC}.{ORCHESTRATOR_STARTED_EVENT}",
            event_type=ORCHESTRATOR_STARTED_EVENT,
            payload={
                "session_id": session_id,
                "task_description": task_description,
                "category": category,
            },
            correlation_id=session_id,
            priority=EventPriority.HIGH,
        )

    async def publish_task_completed(
        self,
        session_id: str,
        category: str,
        result: dict[str, Any],
    ) -> None:
        """Publish task completed event.

        Args:
            session_id: Session ID.
            category: Task category.
            result: Task result.
        """
        await self.publish_event(
            topic=f"{ORCHESTRATOR_TOPIC}.{ORCHESTRATOR_COMPLETED_EVENT}",
            event_type=ORCHESTRATOR_COMPLETED_EVENT,
            payload={
                "session_id": session_id,
                "category": category,
                "result_summary": result.get("status", "unknown"),
            },
            correlation_id=session_id,
            priority=EventPriority.HIGH,
        )

    async def publish_task_failed(
        self,
        session_id: str,
        category: str,
        error: str,
    ) -> None:
        """Publish task failed event.

        Args:
            session_id: Session ID.
            category: Task category.
            error: Error message.
        """
        await self.publish_event(
            topic=f"{ORCHESTRATOR_TOPIC}.{ORCHESTRATOR_FAILED_EVENT}",
            event_type=ORCHESTRATOR_FAILED_EVENT,
            payload={
                "session_id": session_id,
                "category": category,
                "error": error,
            },
            correlation_id=session_id,
            priority=EventPriority.CRITICAL,
        )

    async def publish_worker_started(
        self,
        session_id: str,
        worker_name: str,
        todo_id: str,
    ) -> None:
        """Publish worker started event.

        Args:
            session_id: Session ID.
            worker_name: Name of the worker.
            todo_id: Todo item ID.
        """
        await self.publish_event(
            topic=f"{ORCHESTRATOR_TOPIC}.{ORCHESTRATOR_WORKER_STARTED_EVENT}",
            event_type=ORCHESTRATOR_WORKER_STARTED_EVENT,
            payload={
                "session_id": session_id,
                "worker": worker_name,
                "todo_id": todo_id,
            },
            correlation_id=session_id,
            priority=EventPriority.NORMAL,
        )

    async def publish_worker_completed(
        self,
        session_id: str,
        worker_name: str,
        todo_id: str,
        result: dict[str, Any],
    ) -> None:
        """Publish worker completed event.

        Args:
            session_id: Session ID.
            worker_name: Name of the worker.
            todo_id: Todo item ID.
            result: Worker result.
        """
        await self.publish_event(
            topic=f"{ORCHESTRATOR_TOPIC}.{ORCHESTRATOR_WORKER_COMPLETED_EVENT}",
            event_type=ORCHESTRATOR_WORKER_COMPLETED_EVENT,
            payload={
                "session_id": session_id,
                "worker": worker_name,
                "todo_id": todo_id,
                "status": result.get("status", "unknown"),
            },
            correlation_id=session_id,
            priority=EventPriority.NORMAL,
        )

    async def publish_state_changed(
        self,
        session_id: str,
        old_state: str,
        new_state: str,
    ) -> None:
        """Publish state changed event.

        Args:
            session_id: Session ID.
            old_state: Previous state.
            new_state: New state.
        """
        await self.publish_event(
            topic=f"{ORCHESTRATOR_TOPIC}.{ORCHESTRATOR_STATE_CHANGED_EVENT}",
            event_type=ORCHESTRATOR_STATE_CHANGED_EVENT,
            payload={
                "session_id": session_id,
                "old_state": old_state,
                "new_state": new_state,
            },
            correlation_id=session_id,
            priority=EventPriority.LOW,
        )

    async def publish_context_built(
        self,
        session_id: str,
        token_count: int,
    ) -> None:
        """Publish context built event.

        Args:
            session_id: Session ID.
            token_count: Number of tokens in built context.
        """
        await self.publish_event(
            topic=f"{ORCHESTRATOR_TOPIC}.{ORCHESTRATOR_CONTEXT_BUILT_EVENT}",
            event_type=ORCHESTRATOR_CONTEXT_BUILT_EVENT,
            payload={
                "session_id": session_id,
                "token_count": token_count,
            },
            correlation_id=session_id,
            priority=EventPriority.LOW,
        )

    async def publish_memory_retrieved(
        self,
        session_id: str,
        memory_count: int,
    ) -> None:
        """Publish memory retrieved event.

        Args:
            session_id: Session ID.
            memory_count: Number of memories retrieved.
        """
        await self.publish_event(
            topic=f"{ORCHESTRATOR_TOPIC}.{ORCHESTRATOR_MEMORY_RETRIEVED_EVENT}",
            event_type=ORCHESTRATOR_MEMORY_RETRIEVED_EVENT,
            payload={
                "session_id": session_id,
                "memory_count": memory_count,
            },
            correlation_id=session_id,
            priority=EventPriority.LOW,
        )

    async def build_context(
        self,
        session_id: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Build context for a session.

        Args:
            session_id: Session ID to build context for.
            system_prompt: Optional system prompt override.

        Returns:
            Built context dictionary.
        """
        if self.context_builder is None:
            return {"status": "no_context_builder"}

        try:
            context = await self.context_builder.build(
                session_id=session_id,
                system_prompt=system_prompt,
            )

            await self.publish_context_built(session_id, context.total_tokens)

            return {
                "status": "success",
                "context": context.to_dict(),
                "total_tokens": context.total_tokens,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    async def retrieve_memories(
        self,
        session_id: str,
        query: str,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Retrieve memories for a session.

        Args:
            session_id: Session ID.
            query: Query string for memory retrieval.
            limit: Maximum number of memories to retrieve.

        Returns:
            Retrieved memories dictionary.
        """
        if self.memory_retriever is None:
            return {"status": "no_memory_retriever", "memories": []}

        try:
            # Use hybrid search with a zero embedding since we don't have
            # an embedding service available. The text query will still work.
            memories = await self.memory_retriever.hybrid_search(
                query_embedding=[0.0] * 768,  # Dummy embedding
                query_text=query,
                top_k=limit,
            )

            await self.publish_memory_retrieved(session_id, len(memories))

            return {
                "status": "success",
                "memories": [
                    {"content": m.block.content, "score": m.score, "source": m.source}
                    for m in memories
                ],
                "count": len(memories),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "memories": [],
            }

    async def store_memory(
        self,
        session_id: str,
        content: str,
        memory_type: str = "session",
        importance: float = 0.5,
    ) -> dict[str, Any]:
        """Store a memory for a session.

        Args:
            session_id: Session ID.
            content: Memory content.
            memory_type: Type of memory.
            importance: Importance score.

        Returns:
            Storage result dictionary.
        """
        if self.memory_retriever is None:
            return {"status": "no_memory_retriever"}

        try:
            from mozi.infrastructure.vector_db import MemoryType

            # Map session memory type to EPISODIC
            memory_type_map = {
                "session": MemoryType.EPISODIC,
                "short_term": MemoryType.SHORT_TERM,
                "semantic": MemoryType.SEMANTIC,
                "procedural": MemoryType.PROCEDURAL,
            }
            memory_type_enum = memory_type_map.get(memory_type, MemoryType.EPISODIC)

            block = await self.memory_retriever.long_term.add(
                content=content,
                memory_type=memory_type_enum,
                importance=importance,
            )

            return {
                "status": "success",
                "block_id": block.id,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    async def add_session_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Add a message to a session.

        Args:
            session_id: Session ID.
            role: Message role (user/assistant/system).
            content: Message content.
            metadata: Optional metadata.

        Returns:
            Result dictionary.
        """
        if self.session_manager is None:
            return {"status": "no_session_manager"}

        try:
            from mozi.session.models import MessageRole

            role_enum = MessageRole(role)
            message = await self.session_manager.add_message(
                session_id=session_id,
                role=role_enum,
                content=content,
                metadata=metadata,
            )

            if message is None:
                return {"status": "session_not_found"}

            return {
                "status": "success",
                "message_id": message.id,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    async def get_session_messages(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """Get all messages for a session.

        Args:
            session_id: Session ID.

        Returns:
            Messages dictionary.
        """
        if self.session_manager is None:
            return {"status": "no_session_manager", "messages": []}

        try:
            messages = await self.session_manager.get_messages(session_id)

            return {
                "status": "success",
                "messages": [
                    {
                        "id": m.id,
                        "role": m.role.value,
                        "content": m.content,
                    }
                    for m in messages
                ],
                "count": len(messages),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "messages": [],
            }


# Global integration instance
_integration: OrchestratorIntegration | None = None


def get_integration(
    session_manager: SessionManager | None = None,
    context_builder: ContextBuilder | None = None,
    memory_retriever: MemoryRetriever | None = None,
    model_service: ModelService | None = None,
    event_bus: BaseEventBus | None = None,
) -> OrchestratorIntegration:
    """Get or create the global integration instance.

    Args:
        session_manager: Optional session manager override.
        context_builder: Optional context builder override.
        memory_retriever: Optional memory retriever override.
        model_service: Optional model service override.
        event_bus: Optional event bus override.

    Returns:
        OrchestratorIntegration instance.
    """
    global _integration
    if _integration is None:
        _integration = OrchestratorIntegration(
            session_manager=session_manager,
            context_builder=context_builder,
            memory_retriever=memory_retriever,
            model_service=model_service,
            event_bus=event_bus,
        )
    return _integration
