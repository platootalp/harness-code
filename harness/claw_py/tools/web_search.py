"""
WebSearchTool - Search the web using Anthropic's web search.

Migrated from src/tools/WebSearchTool/WebSearchTool.ts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..models.tool import (
    BaseTool,
    ToolResult,
    ToolUseContext,
    ValidationResult,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name
# =============================================================================

WEB_SEARCH_TOOL_NAME = "WebSearch"

# Hardcoded maximum uses per session
MAX_SEARCH_USES = 8


# =============================================================================
# Output Types
# =============================================================================


@dataclass
class SearchHit:
    """A single search result."""

    title: str
    url: str


@dataclass
class SearchResult:
    """A search result with its tool use ID."""

    tool_use_id: str
    content: list[SearchHit]


@dataclass
class WebSearchToolOutput:
    """Output from the WebSearchTool."""

    query: str
    results: list[SearchResult | str]
    duration_seconds: float


# =============================================================================
# WebSearchTool
# =============================================================================


class WebSearchTool(BaseTool):
    """Tool for searching the web.

    Uses Anthropic SDK's web_search_20250305 tool type under the hood.
    This tool accesses external resources and is not read-only.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "search the web for information"
    max_result_size_chars: int = 100_000
    strict: bool = False
    should_defer: bool = False
    always_load: bool = False

    def __init__(self) -> None:
        self.should_defer = True

    @property
    def name(self) -> str:
        return WEB_SEARCH_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to use (minimum 2 characters)",
                    "minLength": 2,
                },
                "allowed_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Only include search results from these domains",
                },
                "blocked_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Never include search results from these domains",
                },
            },
            "required": ["query"],
        }

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return False

    def is_open_world(self, input: Any) -> bool:
        return True

    def is_search_or_read_command(self, input: Any) -> dict[str, bool]:
        return {"is_search": True, "is_read": False}

    def to_auto_classifier_input(self, input: Any) -> str:
        return str(input.get("query", ""))

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate the tool input before execution."""
        query = input.get("query")
        if not query:
            return (False, "query is required", 400)
        if len(query) < 2:
            return (False, "query must be at least 2 characters", 400)
        return True

    async def call(
        self,
        args: Any,
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[WebSearchToolOutput]:
        """Execute the web search tool.

        Note: This is a simplified implementation. Full web search requires
        integration with the Anthropic API or a search API client.

        Args:
            args: Tool input with query and optional domain filters.
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with search results.
        """
        query = args.get("query", "")
        args.get("allowed_domains")
        args.get("blocked_domains")

        start_time = time.perf_counter()

        # Report progress
        if on_progress:
            progress_data = {"type": "websearch", "query": query}
            on_progress(progress_data)

        # In a full implementation, this would call the Anthropic SDK
        # or a search API. For now, return a placeholder result.
        # The actual search would use BetaWebSearchTool20250305.
        output = WebSearchToolOutput(
            query=query,
            results=[],
            duration_seconds=round(time.perf_counter() - start_time, 3),
        )

        return ToolResult(data=output)

    async def description(self, input: Any, options: dict[str, Any]) -> str:
        query = input.get("query", "") if input else ""
        return f"Claude wants to search the web for: {query}"

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "The WebSearch tool searches the web for information. "
            "Use it to find current events, factual information, "
            "or anything that requires up-to-date data from the internet. "
            f"Maximum {MAX_SEARCH_USES} searches per session."
        )
