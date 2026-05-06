"""Tool for searching persistent memory."""

from __future__ import annotations

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class MemorySearchInput(BaseModel):
    """Arguments for memory search."""

    query: str = Field(description="Search query to find relevant memories")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results to return")


class MemorySearchTool(BaseTool):
    """Search persistent memory for relevant context."""

    name = "memory_search"
    description = "Search persistent memory for relevant context, preferences, and past decisions."
    input_model = MemorySearchInput

    def is_read_only(self, arguments: MemorySearchInput) -> bool:
        del arguments
        return True

    async def execute(self, arguments: MemorySearchInput, context: ToolExecutionContext) -> ToolResult:
        from openharness.memory.registry import get_backend

        metadata = context.metadata
        settings = metadata.get("settings")
        if settings is None:
            return ToolResult(output="Memory search unavailable: no settings in context.")

        try:
            backend = get_backend(settings, cwd=context.cwd)
        except (ValueError, ImportError) as exc:
            return ToolResult(output=f"Memory search unavailable: {exc}")

        try:
            entries = await backend.search(arguments.query, max_results=arguments.max_results)
        except Exception as exc:
            return ToolResult(output=f"Memory search error: {exc}", is_error=True)

        if not entries:
            return ToolResult(output="No relevant memories found.")

        lines: list[str] = []
        for entry in entries:
            score = f" (score: {entry.score:.2f})" if entry.score is not None else ""
            type_tag = f" [{entry.memory_type}]" if entry.memory_type else ""
            lines.append(f"- {entry.title or entry.id}{type_tag}{score}: {entry.content[:500]}")
        return ToolResult(output="\n".join(lines))
