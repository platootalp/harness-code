"""
Tests for EnterWorktreeTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.enter_worktree import EnterWorktreeTool


@pytest.fixture
def enter_worktree_tool() -> EnterWorktreeTool:
    return EnterWorktreeTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    return ctx


@pytest.fixture(autouse=True)
def patch_set_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make set_cwd and os.chdir no-ops in tests."""
    import claude_code.utils.shell as shell_module

    def noop_set_cwd(path: str) -> None:
        pass

    monkeypatch.setattr(shell_module, "set_cwd", noop_set_cwd)

    import os

    monkeypatch.setattr(os, "chdir", lambda path: None)


class TestEnterWorktreeTool:
    """Tests for EnterWorktreeTool."""

    def test_name(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        assert enter_worktree_tool.name == "EnterWorktree"

    def test_aliases(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        assert enter_worktree_tool.aliases is None

    def test_search_hint(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        assert "worktree" in enter_worktree_tool.search_hint.lower()

    def test_should_defer(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        assert enter_worktree_tool.should_defer is True

    def test_always_load(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        assert enter_worktree_tool.always_load is False

    def test_max_result_size_chars(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        assert enter_worktree_tool.max_result_size_chars == 100_000

    def test_strict(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        assert enter_worktree_tool.strict is False

    def test_description_text(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        assert "worktree" in enter_worktree_tool.description_text.lower()

    def test_prompt_text(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        prompt = enter_worktree_tool.prompt_text
        assert "worktree" in prompt.lower()

    def test_input_schema(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        schema = enter_worktree_tool.input_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "name" in props

    def test_output_schema(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        schema = enter_worktree_tool.output_schema
        assert schema is not None
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "worktreePath" in props
        assert "worktreeBranch" in props
        assert "message" in props

    def test_user_facing_name(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        result = enter_worktree_tool.user_facing_name({})
        assert isinstance(result, str)

    def test_should_defer_property(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        assert enter_worktree_tool.should_defer_property() is True

    def test_to_auto_classifier_input(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        result = enter_worktree_tool.to_auto_classifier_input({"name": "feature-branch"})
        assert result == "feature-branch"

    def test_to_auto_classifier_input_empty(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        result = enter_worktree_tool.to_auto_classifier_input({})
        assert result == ""

    def test_validate_input(self, enter_worktree_tool: EnterWorktreeTool) -> None:
        result = enter_worktree_tool.validate_input({}, MagicMock())
        assert result is True

    @pytest.mark.asyncio
    async def test_call_already_in_worktree(
        self, enter_worktree_tool: EnterWorktreeTool, mock_context: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test call when already in a worktree session returns error."""
        import claude_code.utils.worktree as worktree_module

        # Return a WorktreeSession to indicate we're already in a worktree
        from claude_code.utils.worktree import WorktreeSession

        mock_session = WorktreeSession(
            path="/test/worktree",
            branch="test",
            original_cwd="/original",
            created_at=1234567890,
        )
        monkeypatch.setattr(worktree_module, "get_current_worktree_session", lambda: mock_session)

        result = await enter_worktree_tool.call(
            {},
            mock_context,
            AsyncMock(),
            None,
        )
        # Should return error about already being in a worktree
        assert "already" in result["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_call_success_with_name(
        self, enter_worktree_tool: EnterWorktreeTool, mock_context: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import claude_code.utils.worktree as worktree_module

        monkeypatch.setattr(worktree_module, "get_current_worktree_session", lambda: None)
        monkeypatch.setattr(
            worktree_module, "create_worktree_for_session",
            AsyncMock(
                return_value={"worktreePath": "/path/to/my-feature", "worktreeBranch": "worktree/my-feature"}
            ),
        )
        monkeypatch.setattr(worktree_module, "get_session_id", lambda: "test-session")

        result = await enter_worktree_tool.call(
            {"name": "my-feature"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["worktreePath"] == "/path/to/my-feature"
        assert "my-feature" in result["data"]["worktreePath"]

    @pytest.mark.asyncio
    async def test_call_success_generated_name(
        self, enter_worktree_tool: EnterWorktreeTool, mock_context: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import claude_code.utils.worktree as worktree_module

        monkeypatch.setattr(worktree_module, "get_current_worktree_session", lambda: None)
        monkeypatch.setattr(
            worktree_module, "create_worktree_for_session",
            AsyncMock(
                return_value={"worktreePath": "/path/to/generated", "worktreeBranch": "worktree/generated"}
            ),
        )
        monkeypatch.setattr(worktree_module, "get_session_id", lambda: "test-session")

        result = await enter_worktree_tool.call(
            {},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["worktreePath"] == "/path/to/generated"
        assert result["data"]["worktreeBranch"] == "worktree/generated"
        assert result["data"]["message"] is not None

    def test_map_tool_result_to_tool_result_block_param(
        self, enter_worktree_tool: EnterWorktreeTool
    ) -> None:
        content = {
            "worktreePath": "/path/to/worktree",
            "worktreeBranch": "feature-branch",
            "message": "Entered worktree",
        }
        result = enter_worktree_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-123"
        )
        assert result["tool_use_id"] == "tool-use-123"
        assert result["type"] == "tool_result"
        assert "worktree" in result["content"].lower()
