"""
Tests for ReadMcpResourceTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.read_mcp_resource import (
    ReadMcpResourceTool,
    ReadMcpResourceToolOutput,
    ResourceContent,
)


@pytest.fixture
def read_mcp_tool() -> ReadMcpResourceTool:
    return ReadMcpResourceTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.mcp_clients = []
    return ctx


class TestReadMcpResourceTool:
    """Tests for ReadMcpResourceTool."""

    def test_name(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert read_mcp_tool.name == "ReadMcpResource"

    def test_aliases(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert read_mcp_tool.aliases is None

    def test_search_hint(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert "mcp" in str(read_mcp_tool.search_hint).lower()
        assert "resource" in str(read_mcp_tool.search_hint).lower()

    def test_should_defer(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert read_mcp_tool.should_defer is True

    def test_always_load(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert read_mcp_tool.always_load is False

    def test_max_result_size_chars(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert read_mcp_tool.max_result_size_chars == 100_000

    def test_strict(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert read_mcp_tool.strict is False

    def test_input_schema(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        schema = read_mcp_tool.input_schema
        assert schema["type"] == "object"
        assert "server" in schema["required"]
        assert "uri" in schema["required"]
        props = schema["properties"]
        assert "server" in props
        assert "uri" in props

    def test_output_schema(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        schema = read_mcp_tool.output_schema
        assert schema is not None
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "contents" in props

    def test_user_facing_name(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert read_mcp_tool.user_facing_name({}) == "ReadMcpResource"

    def test_is_enabled(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert read_mcp_tool.is_enabled() is True

    def test_is_concurrency_safe(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert read_mcp_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        assert read_mcp_tool.is_read_only({}) is True

    def test_to_auto_classifier_input(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        result = read_mcp_tool.to_auto_classifier_input({
            "server": "myserver",
            "uri": "resource://path/to/file",
        })
        assert "myserver" in result
        assert "resource://path/to/file" in result

    @pytest.mark.asyncio
    async def test_validate_input(
        self, read_mcp_tool: ReadMcpResourceTool, mock_context: MagicMock
    ) -> None:
        result = await read_mcp_tool.validate_input(
            {"server": "myserver", "uri": "resource://path"},
            mock_context,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_no_clients(
        self, read_mcp_tool: ReadMcpResourceTool, mock_context: MagicMock
    ) -> None:
        result = await read_mcp_tool.call(
            {"server": "myserver", "uri": "resource://path"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, ReadMcpResourceToolOutput)
        assert result.data.contents == []

    @pytest.mark.asyncio
    async def test_call_server_not_found_returns_error_content(
        self, read_mcp_tool: ReadMcpResourceTool, mock_context: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.name = "other-server"
        mock_context.mcp_clients = [mock_client]

        result = await read_mcp_tool.call(
            {"server": "nonexistent-server", "uri": "resource://path"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, ReadMcpResourceToolOutput)
        assert len(result.data.contents) == 1
        assert "nonexistent-server" in result.data.contents[0].text

    @pytest.mark.asyncio
    async def test_call_success_returns_contents(
        self, read_mcp_tool: ReadMcpResourceTool, mock_context: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.name = "myserver"
        mock_client.state = "connected"
        mock_client.send_request = AsyncMock(
            return_value={
                "contents": [
                    {"uri": "resource://myserver/file", "mimeType": "text/plain", "text": "Hello world"},
                ]
            }
        )
        mock_context.mcp_clients = [mock_client]

        result = await read_mcp_tool.call(
            {"server": "myserver", "uri": "resource://myserver/file"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, ReadMcpResourceToolOutput)
        assert len(result.data.contents) == 1
        assert result.data.contents[0].uri == "resource://myserver/file"
        assert result.data.contents[0].text == "Hello world"

    @pytest.mark.asyncio
    async def test_call_error_handled_gracefully(
        self, read_mcp_tool: ReadMcpResourceTool, mock_context: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.name = "myserver"
        mock_client.state = "connected"
        mock_client.send_request = AsyncMock(side_effect=Exception("Connection failed"))
        mock_context.mcp_clients = [mock_client]

        result = await read_mcp_tool.call(
            {"server": "myserver", "uri": "resource://myserver/file"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, ReadMcpResourceToolOutput)
        # Error is handled gracefully, returning empty contents
        assert result.data.contents == []

    def test_find_client(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        mock_client = MagicMock()
        mock_client.name = "my-server"
        clients = [mock_client]

        result = read_mcp_tool._find_client("my-server", clients)
        assert result is mock_client

        result = read_mcp_tool._find_client("nonexistent", clients)
        assert result is None

    def test_persist_blob_creates_file(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        import os

        path, msg = read_mcp_tool._persist_blob("", "text/plain", 0, "test-server")
        # Empty blob still creates a file (empty file)
        assert path != ""
        assert os.path.exists(path)
        assert os.path.getsize(path) == 0
        # Clean up
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_description(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        desc = await read_mcp_tool.description({}, {})
        assert "MCP" in desc or "resource" in desc.lower()

    @pytest.mark.asyncio
    async def test_prompt(self, read_mcp_tool: ReadMcpResourceTool) -> None:
        p = await read_mcp_tool.prompt({})
        assert "MCP" in p or "resource" in p.lower()


class TestResourceContent:
    """Tests for ResourceContent dataclass."""

    def test_creation(self) -> None:
        rc = ResourceContent(
            uri="resource://server/file",
            mime_type="text/plain",
            text="content",
        )
        assert rc.uri == "resource://server/file"
        assert rc.mime_type == "text/plain"
        assert rc.text == "content"
        assert rc.blob_saved_to is None

    def test_blob_content(self) -> None:
        rc = ResourceContent(
            uri="resource://server/image",
            mime_type="image/png",
            blob_saved_to="/tmp/blob.png",
            text="Saved to /tmp/blob.png",
        )
        assert rc.uri == "resource://server/image"
        assert rc.blob_saved_to == "/tmp/blob.png"


class TestReadMcpResourceToolOutput:
    """Tests for ReadMcpResourceToolOutput dataclass."""

    def test_output_default(self) -> None:
        output = ReadMcpResourceToolOutput()
        assert output.contents == []

    def test_output_with_contents(self) -> None:
        rc = ResourceContent(uri="file:///test", text="data")
        output = ReadMcpResourceToolOutput(contents=[rc])
        assert len(output.contents) == 1
        assert output.contents[0].uri == "file:///test"
