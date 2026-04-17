"""
BriefTool - Send a proactive message to the user.

This tool is the primary visible output channel for sending messages to the user,
particularly for proactive notifications when the user is away.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "Brief"
LEGACY_TOOL_NAME = "SendUserMessage"


class BriefTool:
    """Send a proactive message to the user.

    This tool is the primary visible output channel for sending messages to the user.
    Used for proactive notifications, status updates, and task completion messages.
    Supports optional file attachments.

    Attributes:
        name: The tool's unique identifier.
        aliases: Legacy alias names.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = [LEGACY_TOOL_NAME]
    search_hint: str | None = "send a message to the user — your primary visible output channel"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Send a message to the user"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to send a message to the user. "
            "This is your primary visible output channel. "
            "Use status='proactive' when surfacing something the user hasn't asked for "
            "(task completion, blockers, unsolicited status updates). "
            "Use status='normal' when replying to something the user just said."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message for the user. Supports markdown formatting.",
                },
                "attachments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional file paths to attach (screenshots, diffs, logs)"
                    ),
                },
                "status": {
                    "type": "string",
                    "enum": ["normal", "proactive"],
                    "description": (
                        "Use 'proactive' for surfacing something the user hasn't asked for. "
                        "Use 'normal' when replying to the user."
                    ),
                },
            },
            "required": ["message"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "size": {"type": "integer"},
                            "isImage": {"type": "boolean"},
                        },
                    },
                },
                "sentAt": {"type": "string"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return ""

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        return str(input.get("message", ""))

    def validate_input(self, input: Any, context: ToolUseContext) -> tuple[bool, str, int] | bool:
        attachments = input.get("attachments", [])
        if attachments:
            # Basic path validation - files should exist
            import os

            for path in attachments:
                if not os.path.exists(path):
                    return (False, f"Attachment file not found: {path}", 1)
        return True

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        attachments = content.get("attachments", [])
        n = len(attachments) if attachments else 0
        suffix = f" ({n} attachment{'s' if n != 1 else ''} included)" if n > 0 else ""
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": f"Message delivered to user.{suffix}",
        }

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        import os
        from datetime import UTC, datetime

        message = args.get("message", "")
        attachments = args.get("attachments")
        args.get("status", "normal")

        sent_at = datetime.now(UTC).isoformat()

        if not attachments:
            return {"data": {"message": message, "sentAt": sent_at}}

        # Resolve attachments

        resolved = []
        for path in attachments:
            if os.path.exists(path):
                stat = os.stat(path)
                is_image = path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
                resolved.append({
                    "path": path,
                    "size": stat.st_size,
                    "isImage": is_image,
                })

        return {"data": {"message": message, "attachments": resolved, "sentAt": sent_at}}
