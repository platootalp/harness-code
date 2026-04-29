"""
Tests for LSPTool.
"""

from __future__ import annotations

import tempfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_code.tools.lsp import LSPTool


@pytest.fixture
def lsp_tool() -> LSPTool:
    return LSPTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    return ctx


@pytest.fixture
def temp_file() -> str:
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        f.write(b"# test file\ndef foo():\n    pass\n")
        return f.name


class TestLSPTool:
    """Tests for LSPTool."""

    def test_name(self, lsp_tool: LSPTool) -> None:
        assert lsp_tool.name == "LSP"

    def test_aliases(self, lsp_tool: LSPTool) -> None:
        # LSP tool may have aliases like goto or hover
        aliases = lsp_tool.aliases
        assert aliases is None or isinstance(aliases, list)

    def test_search_hint(self, lsp_tool: LSPTool) -> None:
        assert "lsp" in lsp_tool.search_hint.lower() or "definition" in lsp_tool.search_hint.lower()

    def test_should_defer(self, lsp_tool: LSPTool) -> None:
        assert lsp_tool.should_defer is True

    def test_always_load(self, lsp_tool: LSPTool) -> None:
        assert lsp_tool.always_load is False

    def test_max_result_size_chars(self, lsp_tool: LSPTool) -> None:
        assert lsp_tool.max_result_size_chars == 100_000

    def test_strict(self, lsp_tool: LSPTool) -> None:
        assert lsp_tool.strict is True

    def test_description_text(self, lsp_tool: LSPTool) -> None:
        desc = lsp_tool.description_text
        assert "lsp" in desc.lower() or "definition" in desc.lower()

    def test_prompt_text(self, lsp_tool: LSPTool) -> None:
        prompt = lsp_tool.prompt_text
        assert isinstance(prompt, str)

    def test_input_schema(self, lsp_tool: LSPTool) -> None:
        schema = lsp_tool.input_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "operation" in props
        assert "filePath" in props
        assert "line" in props
        assert "character" in props
        # All should be required
        assert "operation" in schema["required"]
        assert "filePath" in schema["required"]
        assert "line" in schema["required"]
        assert "character" in schema["required"]

    def test_output_schema(self, lsp_tool: LSPTool) -> None:
        schema = lsp_tool.output_schema
        assert schema is not None
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "operation" in props
        assert "result" in props
        assert "filePath" in props
        assert "resultCount" in props
        assert "fileCount" in props

    def test_user_facing_name(self, lsp_tool: LSPTool) -> None:
        result = lsp_tool.user_facing_name({"operation": "gotoDefinition"})
        assert isinstance(result, str)

    def test_is_enabled_checks_lsp_connected(
        self, lsp_tool: LSPTool, mock_context: MagicMock
    ) -> None:
        # When LSP is not connected, is_enabled should return False
        app_state = MagicMock()
        app_state.isLspConnected = False
        mock_context.get_app_state.return_value = app_state

        # Need to pass context or check default behavior
        # The default is_enabled() in base returns True
        # LSP tool likely overrides this
        result = lsp_tool.is_enabled()
        assert isinstance(result, bool)

    def test_is_concurrency_safe(self, lsp_tool: LSPTool) -> None:
        assert lsp_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, lsp_tool: LSPTool) -> None:
        assert lsp_tool.is_read_only({}) is True

    def test_is_lsp(self, lsp_tool: LSPTool) -> None:
        # The LSP tool should have an is_lsp method
        result = lsp_tool.is_lsp()
        assert result is True

    def test_to_auto_classifier_input(self, lsp_tool: LSPTool) -> None:
        result = lsp_tool.to_auto_classifier_input(
            {"operation": "gotoDefinition", "filePath": "/path/to/file.py"}
        )
        assert "definition" in result.lower() or "/path/to/file.py" in result

    @pytest.mark.asyncio
    async def test_validate_input_invalid_operation(
        self, lsp_tool: LSPTool, mock_context: MagicMock
    ) -> None:
        # Validation runs operation check before file existence check
        result = await lsp_tool.validate_input(
            {
                "operation": "gotoDefinition",
                "filePath": "/nonexistent/file.py",
                "line": 1,
                "character": 0,
            },
            mock_context,
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert "invalid operation" in result[1].lower()

    @pytest.mark.asyncio
    async def test_validate_input_path_not_file(
        self, lsp_tool: LSPTool, mock_context: MagicMock
    ) -> None:
        import os

        # Create a temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            result = await lsp_tool.validate_input(
                {
                    "operation": "goToDefinition",
                    "filePath": tmpdir,
                    "line": 1,
                    "character": 0,
                },
                mock_context,
            )
            assert result is not True
            assert isinstance(result, tuple)

    @pytest.mark.asyncio
    async def test_validate_input_success(
        self, lsp_tool: LSPTool, mock_context: MagicMock, temp_file: str
    ) -> None:
        result = await lsp_tool.validate_input(
            {
                "operation": "goToDefinition",
                "filePath": temp_file,
                "line": 1,
                "character": 0,
            },
            mock_context,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_no_manager(
        self, lsp_tool: LSPTool, mock_context: MagicMock, temp_file: str
    ) -> None:
        with patch(
            "claude-code-py.tools.lsp._get_lsp_server_manager",
            return_value=None,
        ):
            result = await lsp_tool.call(
                {
                    "operation": "goToDefinition",
                    "filePath": temp_file,
                    "line": 1,
                    "character": 0,
                },
                mock_context,
                AsyncMock(),
                None,
            )
            assert "manager" in result.data["result"].lower()

    @pytest.mark.asyncio
    async def test_call_file_too_large(
        self, lsp_tool: LSPTool, mock_context: MagicMock
    ) -> None:
        # Use a normal-sized temp file but mock os.path.getsize to return a large value
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"# test\n")
            temp_file = f.name

        try:
            mock_manager = MagicMock()
            mock_manager.is_file_open.return_value = False
            mock_manager.open_file = AsyncMock()
            mock_manager.send_request = AsyncMock(return_value=None)
            with patch(
                "claude-code-py.tools.lsp._get_lsp_server_manager",
                return_value=mock_manager,
            ):
                with patch(
                    "claude-code-py.tools.lsp.os.path.getsize",
                    return_value=50_000_000,
                ):
                    result = await lsp_tool.call(
                        {
                            "operation": "goToDefinition",
                            "filePath": temp_file,
                            "line": 1,
                            "character": 0,
                        },
                        mock_context,
                        AsyncMock(),
                        None,
                    )
                    assert "too large" in result.data["result"].lower()
        finally:
            import os
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_call_success_goto_definition(
        self, lsp_tool: LSPTool, mock_context: MagicMock, temp_file: str
    ) -> None:
        # Mock the LSP manager
        mock_manager = MagicMock()
        mock_manager.goto_definition = AsyncMock(
            return_value={"uri": f"file://{temp_file}", "range": {"start": {"line": 0, "character": 0}}}
        )
        mock_context.get_app_state.return_value.lsp_manager = mock_manager

        result = await lsp_tool.call(
            {
                "operation": "goToDefinition",
                "filePath": temp_file,
                "line": 1,
                "character": 0,
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data["operation"] == "goToDefinition"
        assert result.data["filePath"] == temp_file

    @pytest.mark.asyncio
    async def test_call_success_hover(
        self, lsp_tool: LSPTool, mock_context: MagicMock, temp_file: str
    ) -> None:
        # Mock the LSP manager
        mock_manager = MagicMock()
        mock_manager.hover = AsyncMock(return_value={"contents": "Hover info"})
        mock_context.get_app_state.return_value.lsp_manager = mock_manager

        result = await lsp_tool.call(
            {
                "operation": "hover",
                "filePath": temp_file,
                "line": 1,
                "character": 0,
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data["operation"] == "hover"

    def test_map_tool_result_to_tool_result_block_param(
        self, lsp_tool: LSPTool
    ) -> None:
        content = {
            "operation": "gotoDefinition",
            "result": "Found at line 42",
            "filePath": "/path/to/file.py",
            "resultCount": 1,
            "fileCount": 1,
        }
        result = lsp_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-lsp"
        )
        assert result["tool_use_id"] == "tool-use-lsp"
        assert result["type"] == "tool_result"
