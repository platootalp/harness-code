"""Context builder for Mozi.

Builds the complete context from various sources including
system prompts, conversation history, and memory retrieval results.
"""

from __future__ import annotations

from typing import Any

from mozi.context.models import BuiltContext, ContextConfig


class ContextBuilder:
    """Builds complete context from multiple sources.

    Orchestrates the context building process by gathering:
    - System prompt
    - Conversation history
    - Memory retrieval results

    Attributes:
        config: Configuration for context building.
        _session_manager: Optional session manager reference.
        _memory_retriever: Optional memory retriever reference.
    """

    def __init__(
        self,
        config: ContextConfig | None = None,
        session_manager: Any = None,
        memory_retriever: Any = None,
    ) -> None:
        """Initialize the context builder.

        Args:
            config: Configuration for context building.
            session_manager: Session manager for retrieving history.
            memory_retriever: Memory retriever for retrieving memories.
        """
        self.config = config or ContextConfig()
        self._session_manager = session_manager
        self._memory_retriever = memory_retriever

    async def build(
        self,
        session_id: str,
        system_prompt: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> BuiltContext:
        """Build the complete context for a session.

        Args:
            session_id: The session ID to build context for.
            system_prompt: Override system prompt.
            additional_context: Additional context to include.

        Returns:
            The built context ready for model input.
        """
        final_system_prompt = system_prompt or self.config.system_prompt or ""

        messages: list[str] = []
        if self.config.include_history and self._session_manager:
            messages = await self._gather_history(session_id)

        memory_results: list[str] = []
        if self.config.include_memory and self._memory_retriever:
            memory_results = await self._gather_memory(session_id)

        context = BuiltContext(
            system_prompt=final_system_prompt,
            messages=messages,
            memory_results=memory_results,
            config=self.config,
            metadata=additional_context or {},
        )

        context.total_tokens = self._estimate_total_tokens(context)

        return context

    async def _gather_history(self, session_id: str) -> list[str]:
        """Gather conversation history from session manager.

        Args:
            session_id: The session ID to gather history for.

        Returns:
            List of formatted message strings.
        """
        if not self._session_manager:
            return []

        messages = await self._session_manager.get_messages(session_id)
        formatted: list[str] = []

        for msg in messages:
            role = msg.role.value.capitalize()
            formatted.append(f"{role}: {msg.content}")

        return formatted

    async def _gather_memory(self, session_id: str) -> list[str]:
        """Gather relevant memories from memory retriever.

        Args:
            session_id: The session ID to gather memories for.

        Returns:
            List of memory content strings.
        """
        if not self._memory_retriever:
            return []

        try:
            results = await self._memory_retriever.retrieve(
                query=f"session {session_id}",
                limit=5,
            )
            return [result.content for result in results]
        except Exception:
            return []

    def _estimate_total_tokens(self, context: BuiltContext) -> int:
        """Estimate total tokens in the context.

        Args:
            context: The built context.

        Returns:
            Estimated token count.
        """
        total = context.estimate_tokens(context.system_prompt)
        for msg in context.messages:
            total += context.estimate_tokens(msg)
        for memory in context.memory_results:
            total += context.estimate_tokens(memory)
        return total
