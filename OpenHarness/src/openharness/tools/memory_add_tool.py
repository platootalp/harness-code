"""Tool for adding memories to persistent storage."""

from __future__ import annotations

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class MemoryAddInput(BaseModel):
    """Arguments for adding a memory."""

    content: str = Field(description="The memory content to store")
    title: str = Field(default="", description="Short title for the memory")
    memory_type: str = Field(
        default="",
        description="Type of memory: preference, fact, decision, or procedure",
    )


class MemoryAddTool(BaseTool):
    """Store a memory for future sessions."""

    name = "memory_add"
    description = "Store a piece of information in persistent memory for use in future sessions."
    input_model = MemoryAddInput

    def is_read_only(self, arguments: MemoryAddInput) -> bool:
        del arguments
        return False

    async def execute(self, arguments: MemoryAddInput, context: ToolExecutionContext) -> ToolResult:
        from openharness.memory.registry import get_backend

        metadata = context.metadata
        settings = metadata.get("settings")
        if settings is None:
            return ToolResult(output="Memory add unavailable: no settings in context.")

        try:
            backend = get_backend(settings, cwd=context.cwd)
        except (ValueError, ImportError) as exc:
            return ToolResult(output=f"Memory add unavailable: {exc}")

        try:
            entry = await backend.add(
                arguments.content,
                title=arguments.title,
                memory_type=arguments.memory_type,
            )
        except Exception as exc:
            return ToolResult(output=f"Memory add error: {exc}", is_error=True)

        return ToolResult(output=f"Memory stored: {entry.title or entry.id}")
