"""
Tests for ListMcpResourcesTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.list_mcp_resources import (
    ListMcpResourcesTool,
    ListMcpResourcesToolOutput,
)


@pytest.fixture
def list_mcp_tool() -> ListMcpResourcesTool:
    return ListMcpResourcesTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.mcp_clients = []
    return ctx


class TestListMcpResourcesTool:
    """Tests for ListMcpResourcesTool."""

    def test_name(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert list_mcp_tool.name == "ListMcpResources"

    def test_aliases(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert list_mcp_tool.aliases is None

    def test_search_hint(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert "mcp" in str(list_mcp_tool.search_hint).lower()
        assert "resource" in str(list_mcp_tool.search_hint).lower()

    def test_should_defer(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert list_mcp_tool.should_defer is True

    def test_always_load(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert list_mcp_tool.always_load is False

    def test_max_result_size_chars(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert list_mcp_tool.max_result_size_chars == 100_000

    def test_strict(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert list_mcp_tool.strict is False

    def test_input_schema(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        schema = list_mcp_tool.input_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "server" in props
        assert schema.get("required", []) == []

    def test_output_schema(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        schema = list_mcp_tool.output_schema
        assert schema is not None
        assert schema["type"] == "array"

    def test_user_facing_name(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert list_mcp_tool.user_facing_name({}) == "ListMcpResources"

    def test_is_enabled(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert list_mcp_tool.is_enabled() is True

    def test_is_concurrency_safe(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert list_mcp_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        assert list_mcp_tool.is_read_only({}) is True

    def test_to_auto_classifier_input(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        result = list_mcp_tool.to_auto_classifier_input({"server": "myserver"})
        assert result == "myserver"

    def test_to_auto_classifier_input_empty(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        result = list_mcp_tool.to_auto_classifier_input({})
        assert result == ""

    @pytest.mark.asyncio
    async def test_validate_input(
        self, list_mcp_tool: ListMcpResourcesTool, mock_context: MagicMock
    ) -> None:
        result = await list_mcp_tool.validate_input({}, mock_context)
        assert result is True

    @pytest.mark.asyncio
    async def test_call_no_clients(
        self, list_mcp_tool: ListMcpResourcesTool, mock_context: MagicMock
    ) -> None:
        result = await list_mcp_tool.call({}, mock_context, AsyncMock(), None)
        assert isinstance(result.data, ListMcpResourcesToolOutput)
        assert result.data.resources == []
        assert result.data.server_filter is None

    @pytest.mark.asyncio
    async def test_call_empty_client_list(
        self, list_mcp_tool: ListMcpResourcesTool, mock_context: MagicMock
    ) -> None:
        mock_context.mcp_clients = []
        result = await list_mcp_tool.call({}, mock_context, AsyncMock(), None)
        assert isinstance(result.data, ListMcpResourcesToolOutput)
        assert result.data.resources == []

    @pytest.mark.asyncio
    async def test_call_server_not_found_returns_empty(
        self, list_mcp_tool: ListMcpResourcesTool, mock_context: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.name = "other-server"
        mock_context.mcp_clients = [mock_client]

        # Server not found is caught internally, returns empty list
        result = await list_mcp_tool.call(
            {"server": "nonexistent-server"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, ListMcpResourcesToolOutput)
        # Returns empty since the server was not found
        assert result.data.resources == []

    def test_find_server(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        mock_client = MagicMock()
        mock_client.name = "my-server"
        clients = [mock_client]

        result = list_mcp_tool._find_server("my-server", clients)
        assert result is mock_client

        with pytest.raises(Exception) as exc_info:
            list_mcp_tool._find_server("nonexistent", clients)
        assert "nonexistent" in str(exc_info.value)
        assert "my-server" in str(exc_info.value)

    def test_client_has_resources(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        mock_client = MagicMock()
        mock_client.capabilities = MagicMock()
        mock_client.capabilities.resources = True
        assert list_mcp_tool._client_has_resources(mock_client) is True

        mock_client2 = MagicMock()
        mock_client2.capabilities = MagicMock()
        mock_client2.capabilities.resources = False
        assert list_mcp_tool._client_has_resources(mock_client2) is False

        mock_client3 = MagicMock()
        mock_client3.capabilities = None
        assert list_mcp_tool._client_has_resources(mock_client3) is False

    def test_format_resource(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        mock_resource = MagicMock()
        mock_resource.uri = "file:///test.txt"
        mock_resource.name = "test.txt"
        mock_resource.mimeType = "text/plain"
        mock_resource.description = "A test file"

        result = list_mcp_tool._format_resource(mock_resource, "my-server")

        assert result["uri"] == "file:///test.txt"
        assert result["name"] == "test.txt"
        assert result["server"] == "my-server"
        assert result["mimeType"] == "text/plain"
        assert result["description"] == "A test file"

    def test_format_resource_minimal(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        mock_resource = MagicMock(spec=[])
        mock_resource.uri = "file:///other.txt"

        result = list_mcp_tool._format_resource(mock_resource, "server2")

        assert result["uri"] == "file:///other.txt"
        assert result["server"] == "server2"

    @pytest.mark.asyncio
    async def test_description(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        desc = await list_mcp_tool.description({}, {})
        assert "MCP resources" in desc or "resource" in desc.lower()

    @pytest.mark.asyncio
    async def test_prompt(self, list_mcp_tool: ListMcpResourcesTool) -> None:
        p = await list_mcp_tool.prompt({})
        assert "MCP" in p or "server" in p.lower()


class TestListMcpResourcesToolOutput:
    """Tests for ListMcpResourcesToolOutput dataclass."""

    def test_output_creation(self) -> None:
        output = ListMcpResourcesToolOutput(
            resources=[{"uri": "file:///test", "name": "test"}],
            server_filter="my-server",
        )
        assert len(output.resources) == 1
        assert output.server_filter == "my-server"

    def test_output_default(self) -> None:
        output = ListMcpResourcesToolOutput()
        assert output.resources == []
        assert output.server_filter is None
