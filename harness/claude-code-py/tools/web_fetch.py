"""
WebFetchTool - Fetch and extract content from URLs.

Migrated from src/tools/WebFetchTool/WebFetchTool.ts.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from ..models.tool import (
    BaseTool,
    ToolResult,
    ToolUseContext,
    ValidationResult,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name & Constants
# =============================================================================

WEB_FETCH_TOOL_NAME = "WebFetch"

# Maximum markdown length for content
MAX_MARKDOWN_LENGTH = 100_000


# =============================================================================
# Output Types
# =============================================================================


@dataclass
class WebFetchToolOutput:
    """Output from the WebFetchTool."""

    bytes: int
    code: int
    code_text: str
    result: str
    duration_ms: float
    url: str


# =============================================================================
# WebFetchTool
# =============================================================================


class WebFetchTool(BaseTool):
    """Tool for fetching and extracting content from URLs.

    Fetches a URL and applies a prompt to extract relevant information.
    Supports redirects and preapproved hosts.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "fetch and extract content from a URL"
    max_result_size_chars: int = 100_000
    strict: bool = False
    should_defer: bool = False
    always_load: bool = False

    def __init__(self) -> None:
        self.should_defer = True

    @property
    def name(self) -> str:
        return WEB_FETCH_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "The URL to fetch content from",
                },
                "prompt": {
                    "type": "string",
                    "description": "The prompt to run on the fetched content",
                },
            },
            "required": ["url", "prompt"],
        }

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def is_open_world(self, input: Any) -> bool:
        return True

    def is_search_or_read_command(self, input: Any) -> dict[str, bool]:
        return {"is_search": False, "is_read": True}

    def to_auto_classifier_input(self, input: Any) -> str:
        url = input.get("url", "")
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            netloc: str = parsed.netloc
            return netloc
        except Exception:
            return str(url)

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate the tool input before execution."""
        url = input.get("url")
        prompt = input.get("prompt")

        if not url:
            return (False, "url is required", 400)

        # Validate URL format
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            if not parsed.scheme:
                return (False, "url must include a scheme (http:// or https://)", 400)
            if parsed.scheme not in ("http", "https"):
                return (False, "url must use http or https scheme", 400)
            if not parsed.netloc:
                return (False, "url must include a host", 400)
        except Exception as e:
            return (False, f"Invalid URL: {e}", 400)

        if not prompt:
            return (False, "prompt is required", 400)

        return True

    async def call(
        self,
        args: Any,
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[WebFetchToolOutput]:
        """Execute the web fetch tool.

        Args:
            args: Tool input with url and prompt.
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with fetched content.
        """
        url = args.get("url", "")
        prompt = args.get("prompt", "")

        start_time = time.perf_counter()
        result_text = ""
        status_code = 0
        status_text = ""
        content_bytes = 0

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                headers={
                    "User-Agent": "Claude Code/1.0",
                    "Accept": "text/html,application/xhtml+xml,text/plain,*/*",
                },
            ) as client:
                response = await client.get(url)
                status_code = response.status_code
                status_text = str(response.reason_phrase)
                content_bytes = len(response.content)

                # Convert to text
                try:
                    text = response.text
                except Exception:
                    text = ""

                # Truncate if too large
                if len(text) > MAX_MARKDOWN_LENGTH:
                    text = text[:MAX_MARKDOWN_LENGTH] + "\n\n[Content truncated]"

                # Apply prompt to content (simplified)
                result_text = self._apply_prompt(text, prompt)

        except httpx.TimeoutException:
            status_code = 408
            status_text = "Request Timeout"
            result_text = f"Request to {url} timed out."
        except httpx.RequestError as e:
            status_code = 500
            status_text = "Error"
            result_text = f"Error fetching {url}: {e}"

        duration_ms = (time.perf_counter() - start_time) * 1000

        output = WebFetchToolOutput(
            bytes=content_bytes,
            code=status_code,
            code_text=status_text,
            result=result_text,
            duration_ms=round(duration_ms, 2),
            url=url,
        )

        return ToolResult(data=output)

    def _apply_prompt(self, content: str, prompt: str) -> str:
        """Apply the user's prompt to the fetched content.

        This is a simplified implementation. In practice, this would use
        a language model to extract relevant information.
        """
        # Simple implementation: just return relevant portions
        prompt_lower = prompt.lower()

        if "summary" in prompt_lower or "summarize" in prompt_lower:
            # Return first 500 chars as summary
            return content[:500] + ("..." if len(content) > 500 else "")

        if "extract" in prompt_lower:
            # Try to find relevant sections
            lines = content.split("\n")
            relevant = [line for line in lines if len(line) > 20][:20]
            return "\n".join(relevant)

        # Default: return the content
        return content

    async def description(self, input: Any, options: dict[str, Any]) -> str:
        url = input.get("url", "") if input else ""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            hostname = parsed.netloc or "this URL"
        except Exception:
            hostname = "this URL"
        return f"Claude wants to fetch content from {hostname}"

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "The WebFetch tool fetches content from URLs and extracts information. "
            "Use it to retrieve web pages, documentation, or any online content. "
            "The prompt guides what information to extract from the fetched page."
        )
