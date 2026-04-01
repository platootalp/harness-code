"""Tests for context isolator."""

from __future__ import annotations

import pytest

from mozi.context.isolator import IsolationResult, Isolator
from mozi.context.models import BuiltContext, ContextConfig


@pytest.mark.unit
class TestIsolator:
    """Tests for Isolator class."""

    def test_init_default(self) -> None:
        """Test initialization with defaults."""
        isolator = Isolator()
        assert isolator.isolated_count == 0
        assert isolator.config is not None

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = ContextConfig(max_tokens=50000)
        isolator = Isolator(config=config)
        assert isolator.config.max_tokens == 50000

    def test_should_isolate_large_messages(self) -> None:
        """Test should_isolate with many messages."""
        context = BuiltContext(
            system_prompt="Test",
            messages=["Message"] * 60,
            total_tokens=1000,
        )
        isolator = Isolator()
        assert isolator.should_isolate(context) is True

    def test_should_isolate_large_memory(self) -> None:
        """Test should_isolate with many memory results."""
        context = BuiltContext(
            system_prompt="Test",
            memory_results=["Memory"] * 25,
            total_tokens=1000,
        )
        isolator = Isolator()
        assert isolator.should_isolate(context) is True

    def test_should_isolate_false(self) -> None:
        """Test should_isolate returns False when not needed."""
        context = BuiltContext(
            system_prompt="Test",
            messages=["Message"] * 5,
            memory_results=["Memory"] * 3,
            total_tokens=100,
        )
        isolator = Isolator()
        assert isolator.should_isolate(context) is False

    @pytest.mark.asyncio
    async def test_create_isolated_context(self) -> None:
        """Test creating an isolated context."""
        parent = BuiltContext(
            system_prompt="Parent System",
            messages=["Message 1", "Message 2"],
            memory_results=["Memory 1"],
            total_tokens=200,
        )
        isolator = Isolator()
        result = await isolator.create_isolated_context("agent1", parent)
        assert isinstance(result, IsolationResult)
        assert result.original_context is parent
        assert result.isolated_context is not parent
        assert result.metadata["agent_id"] == "agent1"

    @pytest.mark.asyncio
    async def test_create_isolated_context_with_filtering(self) -> None:
        """Test creating isolated context with message filtering."""
        parent = BuiltContext(
            system_prompt="Parent",
            messages=["Message 1", "[Agent agent2]: Message 2"],
            total_tokens=100,
        )
        isolator = Isolator()
        result = await isolator.create_isolated_context(
            "agent1", parent, filter_messages=True
        )
        assert len(result.isolated_context.messages) <= len(parent.messages)

    @pytest.mark.asyncio
    async def test_merge_results(self) -> None:
        """Test merging agent results back into parent context."""
        isolator = Isolator()
        parent = BuiltContext(
            system_prompt="Parent",
            messages=["Parent Message"],
            total_tokens=100,
        )
        agent_context = BuiltContext(
            system_prompt="Agent",
            messages=["Agent Message"],
            total_tokens=50,
        )
        merged = await isolator.merge_results("agent1", agent_context, parent)
        assert len(merged.messages) == 2
        assert "Parent Message" in merged.messages
        assert "[Agent agent1]: Agent Message" in merged.messages

    @pytest.mark.asyncio
    async def test_merge_results_removes_isolated(self) -> None:
        """Test that merge_results removes isolated context."""
        isolator = Isolator()
        parent = BuiltContext(system_prompt="Parent", total_tokens=100)
        agent_context = BuiltContext(system_prompt="Agent", total_tokens=50)
        await isolator.create_isolated_context("agent1", parent)
        assert isolator.isolated_count == 1
        await isolator.merge_results("agent1", agent_context, parent)
        assert isolator.isolated_count == 0

    def test_get_isolated_context_exists(self) -> None:
        """Test getting an existing isolated context."""
        isolator = Isolator()
        context = BuiltContext(system_prompt="Test", total_tokens=100)
        isolator._isolated_contexts["agent1"] = context
        result = isolator.get_isolated_context("agent1")
        assert result is context

    def test_get_isolated_context_not_exists(self) -> None:
        """Test getting a non-existent isolated context."""
        isolator = Isolator()
        result = isolator.get_isolated_context("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_filter_messages_for_agent(self) -> None:
        """Test message filtering for specific agent."""
        isolator = Isolator()
        messages = [
            "Normal message",
            "[Agent agent2]: Agent 2 message",
            "[Agent agent1]: Agent 1 message",
            "Another normal",
        ]
        filtered = isolator._filter_messages_for_agent(messages, "agent1")
        assert "Normal message" in filtered
        assert "[Agent agent1]: Agent 1 message" in filtered
        assert "[Agent agent2]: Agent 2 message" not in filtered

    @pytest.mark.asyncio
    async def test_filter_memory_for_agent(self) -> None:
        """Test memory filtering for specific agent."""
        isolator = Isolator()
        memories = [
            "Shared memory",
            "agent_1 specific memory",
            "agent_2 specific memory",
            "General memory",
        ]
        filtered = isolator._filter_memory_for_agent(memories, "agent1")
        assert "Shared memory" in filtered
        assert "agent_1 specific memory" in filtered
        assert "agent_2 specific memory" not in filtered
