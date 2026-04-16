"""Context isolator for Mozi.

Provides context isolation capabilities for multi-agent scenarios,
ensuring each agent's context remains separate and independent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from mozi.context.models import BuiltContext, ContextConfig


@dataclass
class IsolationResult:
    """Result of an isolation operation.

    Attributes:
        original_context: The original context that was isolated.
        isolated_context: The newly isolated context.
        created_at: When the isolation was performed.
        metadata: Additional metadata about the isolation.
    """

    original_context: BuiltContext
    isolated_context: BuiltContext
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class Isolator:
    """Provides context isolation for multi-agent scenarios.

    In multi-agent systems, each agent needs its own isolated
    context to prevent cross-contamination of data.

    Attributes:
        config: Configuration for the isolator.
        _isolated_contexts: Registry of isolated contexts.
    """

    def __init__(self, config: ContextConfig | None = None) -> None:
        """Initialize the isolator.

        Args:
            config: Configuration for context building.
        """
        self.config = config or ContextConfig()
        self._isolated_contexts: dict[str, BuiltContext] = {}

    @property
    def isolated_count(self) -> int:
        """Get the number of isolated contexts."""
        return len(self._isolated_contexts)

    def should_isolate(self, context: BuiltContext) -> bool:
        """Determine if a context should be isolated.

        Args:
            context: The context to evaluate.

        Returns:
            True if isolation is recommended.
        """
        if len(context.messages) > 50:
            return True
        if len(context.memory_results) > 20:
            return True
        return False

    async def create_isolated_context(
        self,
        agent_id: str,
        parent_context: BuiltContext,
        filter_messages: bool = True,
    ) -> IsolationResult:
        """Create an isolated context for an agent.

        Args:
            agent_id: Unique identifier for the agent.
            parent_context: The parent context to isolate from.
            filter_messages: Whether to filter messages for the agent.

        Returns:
            Result containing original and isolated contexts.
        """
        if filter_messages:
            filtered_messages = self._filter_messages_for_agent(
                parent_context.messages,
                agent_id,
            )
        else:
            filtered_messages = list(parent_context.messages)

        filtered_memory = self._filter_memory_for_agent(
            parent_context.memory_results,
            agent_id,
        )

        isolated = BuiltContext(
            system_prompt=self._filter_system_prompt(parent_context.system_prompt, agent_id),
            messages=filtered_messages,
            memory_results=filtered_memory,
            config=parent_context.config,
            metadata={
                **parent_context.metadata,
                "isolated_from_parent": True,
                "agent_id": agent_id,
            },
        )
        isolated.total_tokens = parent_context.total_tokens

        self._isolated_contexts[agent_id] = isolated

        return IsolationResult(
            original_context=parent_context,
            isolated_context=isolated,
            metadata={"agent_id": agent_id, "filter_messages": filter_messages},
        )

    async def merge_results(
        self,
        agent_id: str,
        agent_context: BuiltContext,
        parent_context: BuiltContext,
    ) -> BuiltContext:
        """Merge agent results back into the parent context.

        Args:
            agent_id: The agent ID whose results are being merged.
            parent_context: The original parent context.

        Returns:
            Merged context with agent results incorporated.
        """
        merged_messages = list(parent_context.messages)
        merged_messages.extend([
            f"[Agent {agent_id}]: {msg}" for msg in agent_context.messages
        ])

        merged_memory = list(parent_context.memory_results)
        merged_memory.extend(agent_context.memory_results)

        merged = BuiltContext(
            system_prompt=parent_context.system_prompt,
            messages=merged_messages,
            memory_results=merged_memory,
            config=parent_context.config,
            metadata={
                **parent_context.metadata,
                "merged_agent_id": agent_id,
                "merged_at": datetime.now(UTC).isoformat(),
            },
        )
        merged.total_tokens = (
            parent_context.total_tokens + agent_context.total_tokens
        )

        if agent_id in self._isolated_contexts:
            del self._isolated_contexts[agent_id]

        return merged

    def get_isolated_context(self, agent_id: str) -> BuiltContext | None:
        """Get an isolated context by agent ID.

        Args:
            agent_id: The agent ID to look up.

        Returns:
            The isolated context, or None if not found.
        """
        return self._isolated_contexts.get(agent_id)

    def _filter_messages_for_agent(
        self,
        messages: list[str],
        agent_id: str,
    ) -> list[str]:
        """Filter messages for a specific agent.

        In a real implementation, this would filter based on
        message annotations or permissions.

        Args:
            messages: All messages.
            agent_id: The agent to filter for.

        Returns:
            Filtered messages.
        """
        filtered: list[str] = []
        for msg in messages:
            if f"[Agent {agent_id}]" in msg or "broadcast" in msg.lower():
                filtered.append(msg)
            elif not msg.startswith("[Agent"):
                filtered.append(msg)
        return filtered

    def _filter_memory_for_agent(
        self,
        memories: list[str],
        agent_id: str,
    ) -> list[str]:
        """Filter memory results for a specific agent.

        Args:
            memories: All memory results.
            agent_id: The agent to filter for.

        Returns:
            Filtered memory results.
        """
        filtered: list[str] = []
        for mem in memories:
            mem_lower = mem.lower()
            # Include shared memories
            if "shared" in mem_lower:
                filtered.append(mem)
                continue
            # Check if it has any agent_X pattern
            has_agent_pattern = False
            agent_num = None
            for a in range(10):
                if f"agent_{a}" in mem_lower:
                    has_agent_pattern = True
                    agent_num = a
                    break
            if has_agent_pattern:
                # Extract the agent number from agent_id (e.g., "agent1" -> 1)
                agent_id_num = None
                if agent_id.startswith("agent") and len(agent_id) > 5:
                    try:
                        agent_id_num = int(agent_id[5:])
                    except ValueError:
                        pass
                # Include if it's this agent's memory or if we can't determine
                if agent_id_num == agent_num:
                    filtered.append(mem)
                # Otherwise exclude (other agent's memory)
            else:
                # No agent pattern, include it
                filtered.append(mem)
        return filtered

    def _filter_system_prompt(self, system_prompt: str, agent_id: str) -> str:
        """Filter system prompt for a specific agent.

        Args:
            system_prompt: The original system prompt.
            agent_id: The agent to filter for.

        Returns:
            Filtered system prompt.
        """
        return f"{system_prompt}\n\n[Context for Agent {agent_id}]"
