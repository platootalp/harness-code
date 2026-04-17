"""
Tests for ExitWorktreeTool.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.exit_worktree import ExitWorktreeTool
from claude_code.utils.worktree import WorktreeSession


@pytest.fixture
def exit_worktree_tool() -> ExitWorktreeTool:
    return ExitWorktreeTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    return ctx


@pytest.fixture
def mock_worktree_session() -> WorktreeSession:
    return WorktreeSession(
        path="/path/to/worktree",
        branch="feature",
        original_cwd=os.getcwd(),
        created_at=1234567890,
        name="feature",
    )


@pytest.fixture(autouse=True)
def patch_set_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make set_cwd a no-op in tests."""
    import claude_code.utils.shell as shell_module

    def noop_set_cwd(path: str) -> None:
        pass

    monkeypatch.setattr(shell_module, "set_cwd", noop_set_cwd)


class TestExitWorktreeTool:
    """Tests for ExitWorktreeTool."""

    def test_name(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        assert exit_worktree_tool.name == "ExitWorktree"

    def test_aliases(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        assert exit_worktree_tool.aliases is None

    def test_search_hint(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        assert "worktree" in exit_worktree_tool.search_hint.lower()

    def test_should_defer(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        assert exit_worktree_tool.should_defer is True

    def test_always_load(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        assert exit_worktree_tool.always_load is False

    def test_max_result_size_chars(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        assert exit_worktree_tool.max_result_size_chars == 100_000

    def test_strict(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        assert exit_worktree_tool.strict is False

    def test_is_destructive(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        assert exit_worktree_tool.is_destructive({"action": "remove"}) is True
        assert exit_worktree_tool.is_destructive({"action": "keep"}) is False

    def test_description_text(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        assert "worktree" in exit_worktree_tool.description_text.lower()

    def test_prompt_text(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        prompt = exit_worktree_tool.prompt_text
        assert "exit" in prompt.lower()

    def test_input_schema(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        schema = exit_worktree_tool.input_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "action" in props
        assert "action" in schema["required"]
        assert "discardChanges" in props

    def test_output_schema(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        schema = exit_worktree_tool.output_schema
        assert schema is not None
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "action" in props
        assert "originalCwd" in props
        assert "worktreePath" in props
        assert "worktreeBranch" in props
        assert "message" in props

    def test_user_facing_name(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        result = exit_worktree_tool.user_facing_name({})
        assert isinstance(result, str)

    def test_to_auto_classifier_input(self, exit_worktree_tool: ExitWorktreeTool) -> None:
        result = exit_worktree_tool.to_auto_classifier_input({"action": "keep"})
        assert "keep" in result.lower()

    @pytest.mark.asyncio
    async def test_validate_input_no_session(
        self, exit_worktree_tool: ExitWorktreeTool, mock_context: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import claude_code.utils.worktree as worktree_module

        monkeypatch.setattr(worktree_module, "get_current_worktree_session", lambda: None)
        mock_context.get_app_state = None

        result = await exit_worktree_tool.validate_input(
            {"action": "keep"}, mock_context
        )
        assert isinstance(result, tuple)
        assert result[0] is False
        assert result[2] == 1

    @pytest.mark.asyncio
    async def test_validate_input_remove_with_changes(
        self,
        exit_worktree_tool: ExitWorktreeTool,
        mock_context: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        mock_worktree_session: WorktreeSession,
    ) -> None:
        """Test remove action when worktree has changes."""
        import claude_code.tools.exit_worktree as ewt_module
        import claude_code.utils.worktree as worktree_module

        monkeypatch.setattr(worktree_module, "get_current_worktree_session", lambda: mock_worktree_session)

        app_state = MagicMock()
        app_state.is_in_worktree = True
        app_state.worktree_path = "/path/to/worktree"
        app_state.original_head_commit = "abc123"
        app_state.worktree_branch = "feature"
        mock_context.get_app_state = MagicMock(return_value=app_state)

        async def mock_count(path: str | None, commit: str | None) -> dict[str, int]:
            return {"changedFiles": 5, "commits": 2}

        monkeypatch.setattr(ewt_module, "_count_worktree_changes", mock_count)

        result = await exit_worktree_tool.validate_input(
            {"action": "remove"}, mock_context
        )
        assert isinstance(result, tuple)
        assert result[0] is False
        assert result[2] == 2

    @pytest.mark.asyncio
    async def test_validate_input_remove_unknown_state(
        self,
        exit_worktree_tool: ExitWorktreeTool,
        mock_context: MagicMock,
        mock_worktree_session: WorktreeSession,  # noqa: ARG002
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test remove action when worktree state cannot be verified."""
        import claude_code.tools.exit_worktree as ewt_module
        import claude_code.utils.worktree as worktree_module

        # Override session to have no original_head_commit
        mock_session_no_commit = WorktreeSession(
            path="/path/to/worktree",
            branch="feature",
            original_cwd=os.getcwd(),
            created_at=1234567890,
            name="feature",
        )
        monkeypatch_session = MagicMock(return_value=mock_session_no_commit)
        monkeypatch.setattr(worktree_module, "get_current_worktree_session", monkeypatch_session)

        app_state = MagicMock()
        app_state.is_in_worktree = True
        app_state.worktree_path = "/path/to/worktree"
        app_state.original_head_commit = None  # No baseline
        mock_context.get_app_state = MagicMock(return_value=app_state)

        async def mock_count(path: str | None, commit: str | None) -> dict[str, int] | None:
            # Simulate git not being available or state unverifiable
            return None

        monkeypatch.setattr(ewt_module, "_count_worktree_changes", mock_count)

        result = await exit_worktree_tool.validate_input(
            {"action": "remove"}, mock_context
        )
        assert isinstance(result, tuple)
        assert result[0] is False
        assert result[2] == 3

    @pytest.mark.asyncio
    async def test_validate_input_success_keep(
        self,
        exit_worktree_tool: ExitWorktreeTool,
        mock_context: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        mock_worktree_session: WorktreeSession,
    ) -> None:
        import claude_code.tools.exit_worktree as ewt_module
        import claude_code.utils.worktree as worktree_module

        monkeypatch.setattr(worktree_module, "get_current_worktree_session", lambda: mock_worktree_session)

        app_state = MagicMock()
        app_state.is_in_worktree = True
        app_state.worktree_path = "/path/to/worktree"
        app_state.worktree_branch = "feature"
        mock_context.get_app_state = MagicMock(return_value=app_state)

        async def mock_count(path: str | None, commit: str | None) -> dict[str, int]:
            return {"changedFiles": 0, "commits": 0}

        monkeypatch.setattr(ewt_module, "_count_worktree_changes", mock_count)

        result = await exit_worktree_tool.validate_input(
            {"action": "keep"}, mock_context
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_input_success_remove_clean(
        self,
        exit_worktree_tool: ExitWorktreeTool,
        mock_context: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        mock_worktree_session: WorktreeSession,
    ) -> None:
        import claude_code.tools.exit_worktree as ewt_module
        import claude_code.utils.worktree as worktree_module

        monkeypatch.setattr(worktree_module, "get_current_worktree_session", lambda: mock_worktree_session)

        app_state = MagicMock()
        app_state.is_in_worktree = True
        app_state.worktree_path = "/path/to/worktree"
        app_state.worktree_branch = "feature"
        mock_context.get_app_state = MagicMock(return_value=app_state)

        async def mock_count(path: str | None, commit: str | None) -> dict[str, int]:
            return {"changedFiles": 0, "commits": 0}

        monkeypatch.setattr(ewt_module, "_count_worktree_changes", mock_count)

        result = await exit_worktree_tool.validate_input(
            {"action": "remove"}, mock_context
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_keep_action(
        self,
        exit_worktree_tool: ExitWorktreeTool,
        mock_context: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        mock_worktree_session: WorktreeSession,
    ) -> None:
        import claude_code.tools.exit_worktree as ewt_module
        import claude_code.utils.worktree as worktree_module

        monkeypatch.setattr(worktree_module, "get_current_worktree_session", lambda: mock_worktree_session)
        monkeypatch.setattr(worktree_module, "keep_worktree", AsyncMock())

        async def mock_count(path: str | None, commit: str | None) -> dict[str, int]:
            return {"changedFiles": 0, "commits": 0}

        monkeypatch.setattr(ewt_module, "_count_worktree_changes", mock_count)

        result = await exit_worktree_tool.call(
            {"action": "keep"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["action"] == "keep"
        assert "worktree" in result["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_call_remove_action(
        self,
        exit_worktree_tool: ExitWorktreeTool,
        mock_context: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        mock_worktree_session: WorktreeSession,
    ) -> None:
        import claude_code.tools.exit_worktree as ewt_module
        import claude_code.utils.worktree as worktree_module

        monkeypatch.setattr(worktree_module, "get_current_worktree_session", lambda: mock_worktree_session)
        monkeypatch.setattr(worktree_module, "cleanup_worktree", AsyncMock())

        async def mock_count(path: str | None, commit: str | None) -> dict[str, int]:
            return {"changedFiles": 0, "commits": 0}

        monkeypatch.setattr(ewt_module, "_count_worktree_changes", mock_count)

        result = await exit_worktree_tool.call(
            {"action": "remove"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["action"] == "remove"
        assert result["data"]["worktreePath"] == "/path/to/worktree"

    @pytest.mark.asyncio
    async def test_call_remove_with_discard(
        self,
        exit_worktree_tool: ExitWorktreeTool,
        mock_context: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        mock_worktree_session: WorktreeSession,
    ) -> None:
        import claude_code.tools.exit_worktree as ewt_module
        import claude_code.utils.worktree as worktree_module

        monkeypatch.setattr(worktree_module, "get_current_worktree_session", lambda: mock_worktree_session)
        monkeypatch.setattr(worktree_module, "cleanup_worktree", AsyncMock())

        async def mock_count(path: str | None, commit: str | None) -> dict[str, int]:
            return {"changedFiles": 3, "commits": 2}

        monkeypatch.setattr(ewt_module, "_count_worktree_changes", mock_count)

        result = await exit_worktree_tool.call(
            {"action": "remove", "discardChanges": True},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["action"] == "remove"
        assert result["data"]["discardedFiles"] == 3
        assert result["data"]["discardedCommits"] == 2

    def test_map_tool_result_to_tool_result_block_param(
        self, exit_worktree_tool: ExitWorktreeTool
    ) -> None:
        content = {
            "action": "keep",
            "originalCwd": "/original/path",
            "worktreePath": "/path/to/worktree",
            "worktreeBranch": "feature-branch",
            "message": "Exited worktree, keeping it",
        }
        result = exit_worktree_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-456"
        )
        assert result["tool_use_id"] == "tool-use-456"
        assert result["type"] == "tool_result"
        assert "worktree" in result["content"].lower()
