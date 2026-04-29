"""
ToolSearchTool - Search for deferred tools by keyword.

Migrated from src/tools/ToolSearchTool/ToolSearchTool.ts.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name
# =============================================================================

TOOL_SEARCH_TOOL_NAME = "ToolSearch"

# =============================================================================
# Tool search helpers (imported from utils, mocked in tests)
# =============================================================================


def is_tool_search_enabled_optimistic() -> bool:
    """Check if tool search is enabled (optimistic check)."""
    from claude_code.utils.tool_search import is_tool_search_enabled_optimistic as _fn

    return _fn()


def is_deferred_tool(tool: Any) -> bool:
    """Check if a tool should be deferred."""
    should_defer = getattr(tool, "should_defer", False)
    if should_defer is True:
        return True
    # Also check if tool has should_defer attribute at all
    return hasattr(tool, "should_defer")


def find_tool_by_name(tools: list[Any], name: str) -> Any | None:
    """Find a tool by name or alias from a list of tools."""
    for tool in tools:
        if tool.name == name:
            return tool
        aliases = getattr(tool, "aliases", None)
        if aliases is not None and name in aliases:
            return tool
    return None


# =============================================================================
# ToolSearchTool
# =============================================================================


class ToolSearchTool:
    """Tool for searching deferred tools by keyword.

    Allows the model to discover and select deferred tools using natural
    language queries. Supports direct selection via "select:" prefix,
    keyword search across tool names, search hints, and descriptions,
    and includes MCP server connection status in results.
    """

    name: str = TOOL_SEARCH_TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "search for deferred tools by keyword"
    should_defer: bool = False
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return (
            "A tool for searching and selecting deferred tools by keyword. "
            "Use this to find tools that match a query. "
            "Supports 'select:<name>' for direct tool selection."
        )

    @property
    def prompt_text(self) -> str:
        return (
            "The ToolSearch tool helps find deferred tools by keyword. "
            "Search by tool name, action (e.g., 'read', 'search'), or capability. "
            "Use 'select:<tool_name>' to directly load a specific tool. "
            "Use 'mcp:' prefix to find MCP server tools. "
            "Only deferred tools (should_defer=true) are searched."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Query to find deferred tools. "
                        'Use "select:<tool_name>" for direct selection, '
                        "or keywords to search."
                    ),
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results to return (default: 5)",
                },
            },
            "required": ["query"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "query": {"type": "string"},
                "total_deferred_tools": {"type": "number"},
                "pending_mcp_servers": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return ""

    def is_enabled(self) -> bool:
        return is_tool_search_enabled_optimistic()

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        return str(input.get("query", ""))

    async def validate_input(
        self, input: Any, context: Any
    ) -> tuple[bool, str, int] | bool:
        """ToolSearch does not need input validation."""
        return True

    async def call(
        self,
        args: dict[str, Any],
        context: Any,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        query = args.get("query", "")
        max_results = args.get("maxResults", 5)

        # Get tools from context - handle both direct attribute and options pattern
        tools: list[Any] = []
        if hasattr(context, "tools"):
            tools = context.tools or []
        elif hasattr(context, "options"):
            tools = context.options.get("tools", [])

        # Get MCP clients from context
        mcp_clients: list[Any] = []
        if hasattr(context, "options"):
            mcp_clients = context.options.get("mcp_clients", [])
        elif hasattr(context, "mcp_clients"):
            mcp_clients = context.mcp_clients or []

        # Filter to deferred tools only
        deferred_tools = [t for t in tools if is_deferred_tool(t)]

        # Get pending MCP servers
        pending_servers: list[str] = []
        for client in mcp_clients:
            if getattr(client, "type", None) == "pending":
                name = getattr(client, "name", "")
                if name:
                    pending_servers.append(name)

        # Check for select: prefix — direct tool selection
        select_match = re.match(r"^select:(.+)$", query, re.IGNORECASE)
        if select_match:
            requested = [
                s.strip()
                for s in select_match.group(1).split(",")
                if s.strip()
            ]

            found: list[str] = []
            missing: list[str] = []
            for tool_name in requested:
                tool = (
                    find_tool_by_name(deferred_tools, tool_name)
                    or find_tool_by_name(tools, tool_name)
                )
                if tool:
                    if tool.name not in found:
                        found.append(tool.name)
                else:
                    missing.append(tool_name)

            return {
                "matches": found,
                "query": query,
                "total_deferred_tools": len(deferred_tools),
                **({"pending_mcp_servers": pending_servers} if len(found) == 0 and missing else {}),
            }

        # Keyword search
        matches = _search_tools_with_keywords(
            query,
            deferred_tools,
            tools,
            max_results,
        )

        return {
            "matches": matches,
            "query": query,
            "total_deferred_tools": len(deferred_tools),
            **({"pending_mcp_servers": pending_servers} if len(matches) == 0 else {}),
        }

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        matches = content.get("matches", [])
        pending_servers = content.get("pending_mcp_servers")

        if len(matches) == 0:
            text = "No matching deferred tools found"
            if pending_servers and len(pending_servers) > 0:
                text += (
                    f". Some MCP servers are still connecting: "
                    f"{', '.join(pending_servers)}. "
                    f"Their tools will become available shortly — try searching again."
                )
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": text,
            }

        # Return tool_reference blocks
        tool_names: list[str] = []
        for match in matches:
            if isinstance(match, str):
                tool_names.append(match)
            elif isinstance(match, dict):
                name = match.get("name")
                if isinstance(name, str):
                    tool_names.append(name)

        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": tool_names,
        }


# =============================================================================
# Helper Functions
# =============================================================================


def _build_search_result(
    matches: list[str],
    query: str,
    total_deferred: int,
    pending_servers: list[str] | None = None,
) -> dict[str, Any]:
    """Build the search result output structure."""
    data: dict[str, Any] = {
        "matches": matches,
        "query": query,
        "total_deferred_tools": total_deferred,
    }
    if pending_servers:
        data["pending_mcp_servers"] = pending_servers
    return {"data": data}


def _parse_tool_name(name: str) -> dict[str, Any]:
    """Parse tool name into searchable parts.

    Handles both MCP tools (mcp__server__action) and regular tools (CamelCase).
    """
    # Check if it's an MCP tool
    if name.startswith("mcp__"):
        without_prefix = name[4:].lower()
        parts = without_prefix.replace("__", " ").replace("_", " ").split()
        return {
            "parts": [p for p in parts if p],
            "full": without_prefix.replace("__", " ").replace("_", " "),
            "is_mcp": True,
        }

    # Regular tool - split by CamelCase and underscores
    import re as _re
    parts = _re.sub(r"([a-z])([A-Z])", r"\1 \2", name.replace("_", " ")).lower().split()
    return {
        "parts": [p for p in parts if p],
        "full": " ".join(parts),
        "is_mcp": False,
    }


def _search_tools_with_keywords(
    query: str,
    deferred_tools: list[Any],
    all_tools: list[Any],
    max_results: int,
) -> list[str]:
    """Search deferred tools by keyword using scoring."""
    query_lower = query.lower().strip()

    # Fast path: exact match on tool name
    for tool in deferred_tools:
        if tool.name.lower() == query_lower:
            return [tool.name]

    # MCP prefix search
    if query_lower.startswith("mcp__") and len(query_lower) > 5:
        prefix_matches = [
            tool.name
            for tool in deferred_tools
            if tool.name.lower().startswith(query_lower)
        ]
        if prefix_matches:
            return prefix_matches[:max_results]

    # Keyword search
    query_terms = [t for t in query_lower.split() if t]

    scored: list[tuple[str, int]] = []
    for tool in deferred_tools:
        parsed = _parse_tool_name(tool.name)
        description = _get_tool_description(tool)
        search_hint = getattr(tool, "search_hint", None) or ""

        desc_lower = description.lower()
        hint_lower = str(search_hint).lower() if search_hint else ""

        score = 0
        for term in query_terms:
            # Exact part match
            if term in parsed["parts"]:
                score += 12 if parsed["is_mcp"] else 10
            elif any(term in part for part in parsed["parts"]):
                score += 6 if parsed["is_mcp"] else 5

            # searchHint match
            if re.search(rf"\b{re.escape(term)}\b", hint_lower):
                score += 4

            # Description match with word boundaries
            if re.search(rf"\b{re.escape(term)}\b", desc_lower):
                score += 2

        if score > 0:
            scored.append((tool.name, score))

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    return [name for name, _ in scored[:max_results]]


def _get_tool_description(tool: Any) -> str:
    """Get the description for a tool, trying multiple approaches."""
    # Try description_text property
    if hasattr(tool, "description_text"):
        desc = tool.description_text
        if isinstance(desc, str):
            return desc

    # Try description method (async)
    if hasattr(tool, "description"):
        desc = tool.description
        if callable(desc):
            return ""
        if isinstance(desc, str):
            return desc

    return ""
