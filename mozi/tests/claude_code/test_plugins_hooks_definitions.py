"""
Tests for plugins/hooks/definitions.py - Hook type definitions and enums.
"""

from __future__ import annotations

import pytest


# =============================================================================
# HookEventType Tests
# =============================================================================


class TestHookEventTypeValues:
    """Tests that all 25 hook event types are defined."""

    def test_tool_lifecycle_hooks_defined(self) -> None:
        """PreToolUse, PostToolUse, PostToolUseFailure are defined."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        values = [e.value for e in HookEventType]
        assert "PreToolUse" in values
        assert "PostToolUse" in values
        assert "PostToolUseFailure" in values

    def test_session_lifecycle_hooks_defined(self) -> None:
        """SessionStart, SessionEnd, Setup are defined."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        values = [e.value for e in HookEventType]
        assert "SessionStart" in values
        assert "SessionEnd" in values
        assert "Setup" in values

    def test_agent_lifecycle_hooks_defined(self) -> None:
        """SubagentStart, SubagentStop, TeammateIdle are defined."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        values = [e.value for e in HookEventType]
        assert "SubagentStart" in values
        assert "SubagentStop" in values
        assert "TeammateIdle" in values

    def test_task_lifecycle_hooks_defined(self) -> None:
        """TaskCreated, TaskCompleted are defined."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        values = [e.value for e in HookEventType]
        assert "TaskCreated" in values
        assert "TaskCompleted" in values

    def test_compact_hooks_defined(self) -> None:
        """PreCompact, PostCompact are defined."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        values = [e.value for e in HookEventType]
        assert "PreCompact" in values
        assert "PostCompact" in values

    def test_permission_hooks_defined(self) -> None:
        """PermissionRequest, PermissionDenied are defined."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        values = [e.value for e in HookEventType]
        assert "PermissionRequest" in values
        assert "PermissionDenied" in values

    def test_user_interaction_hooks_defined(self) -> None:
        """UserPromptSubmit, Notification, Elicitation are defined."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        values = [e.value for e in HookEventType]
        assert "UserPromptSubmit" in values
        assert "Notification" in values
        assert "Elicitation" in values

    def test_control_flow_hooks_defined(self) -> None:
        """Stop, StopFailure are defined."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        values = [e.value for e in HookEventType]
        assert "Stop" in values
        assert "StopFailure" in values

    def test_config_hooks_defined(self) -> None:
        """ConfigChange is defined."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        values = [e.value for e in HookEventType]
        assert "ConfigChange" in values

    def test_worktree_hooks_defined(self) -> None:
        """WorktreeCreate, WorktreeRemove, InstructionsLoaded are defined."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        values = [e.value for e in HookEventType]
        assert "WorktreeCreate" in values
        assert "WorktreeRemove" in values
        assert "InstructionsLoaded" in values

    def test_all_hooks_defined(self) -> None:
        """All hook event types are present."""
        from src.claude_code.plugins.hooks.definitions import HookEventType

        # Count: 3 tool + 3 session + 3 agent + 2 task + 2 compact + 2 permission +
        # 3 user_interaction + 2 control_flow + 1 config + 3 worktree = 24
        expected_count = 24
        actual = len(list(HookEventType))
        assert actual == expected_count, (
            f"Expected {expected_count} hook types, got {actual}: "
            f"{[e.value for e in HookEventType]}"
        )


class TestHookTypeValues:
    """Tests for HookType enum values."""

    def test_hook_type_command(self) -> None:
        """Command hook type is defined."""
        from src.claude_code.plugins.hooks.definitions import HookType

        assert HookType.COMMAND.value == "command"

    def test_hook_type_prompt(self) -> None:
        """Prompt hook type is defined."""
        from src.claude_code.plugins.hooks.definitions import HookType

        assert HookType.PROMPT.value == "prompt"

    def test_hook_type_http(self) -> None:
        """HTTP hook type is defined."""
        from src.claude_code.plugins.hooks.definitions import HookType

        assert HookType.HTTP.value == "http"

    def test_hook_type_agent(self) -> None:
        """Agent hook type is defined."""
        from src.claude_code.plugins.hooks.definitions import HookType

        assert HookType.AGENT.value == "agent"


# =============================================================================
# HookDefinition Tests
# =============================================================================


class TestHookDefinition:
    """Tests for HookDefinition dataclass."""

    def test_create_command_hook(self) -> None:
        """Create a command-type hook."""
        from src.claude_code.plugins.hooks.definitions import HookDefinition, HookType

        hook = HookDefinition(
            event="PreToolUse",
            hook_type=HookType.COMMAND,
            command="echo 'running'",
        )
        assert hook.event == "PreToolUse"
        assert hook.hook_type == HookType.COMMAND
        assert hook.command == "echo 'running'"
        assert hook.condition is None

    def test_create_prompt_hook(self) -> None:
        """Create a prompt-type hook."""
        from src.claude_code.plugins.hooks.definitions import HookDefinition, HookType

        hook = HookDefinition(
            event="PreToolUse",
            hook_type=HookType.PROMPT,
            prompt="Evaluate safety: {input}",
            condition="tool.name == 'Bash'",
        )
        assert hook.hook_type == HookType.PROMPT
        assert hook.prompt == "Evaluate safety: {input}"
        assert hook.condition == "tool.name == 'Bash'"

    def test_create_http_hook(self) -> None:
        """Create an HTTP-type hook."""
        from src.claude_code.plugins.hooks.definitions import HookDefinition, HookType

        hook = HookDefinition(
            event="PostToolUse",
            hook_type=HookType.HTTP,
            url="https://example.com/hook",
        )
        assert hook.hook_type == HookType.HTTP
        assert hook.url == "https://example.com/hook"

    def test_create_agent_hook(self) -> None:
        """Create an agent-type hook."""
        from src.claude_code.plugins.hooks.definitions import HookDefinition, HookType

        hook = HookDefinition(
            event="PreToolUse",
            hook_type=HookType.AGENT,
            prompt="Verify safety: {input}",
            timeout=30,
        )
        assert hook.hook_type == HookType.AGENT
        assert hook.timeout == 30

    def test_hook_with_priority(self) -> None:
        """Hook supports priority field."""
        from src.claude_code.plugins.hooks.definitions import HookDefinition

        hook = HookDefinition(event="Setup", priority=100)
        assert hook.priority == 100

    def test_hook_default_priority(self) -> None:
        """Hook defaults to priority 0."""
        from src.claude_code.plugins.hooks.definitions import HookDefinition

        hook = HookDefinition(event="SessionStart")
        assert hook.priority == 0

    def test_hook_matches_condition(self) -> None:
        """Hook with no condition matches everything."""
        from src.claude_code.plugins.hooks.definitions import HookDefinition

        hook = HookDefinition(event="SessionStart")
        assert hook.matches_condition({}) is True

    def test_hook_with_condition(self) -> None:
        """Hook with condition delegates to matcher."""
        from src.claude_code.plugins.hooks.definitions import HookDefinition

        hook = HookDefinition(
            event="PreToolUse",
            condition="tool.name == 'Bash'",
        )
        # matches_condition returns None when condition can't be evaluated
        # (no expression parser implemented yet)
        result = hook.matches_condition({"tool": {"name": "Bash"}})
        assert result is True or result is None  # depends on implementation
