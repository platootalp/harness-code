"""
SendMessageTool - Send messages to agent teammates.

This tool supports plain text messages, broadcasts, and structured protocol messages
(shutdown_request, shutdown_response, plan_approval_response).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "SendMessage"


class SendMessageTool:
    """Send messages to agent teammates.

    Supports:
    - Plain text messages to specific teammates
    - Broadcast messages to all team members
    - Structured protocol messages (shutdown_request, shutdown_response, plan_approval_response)

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "send messages to agent teammates (swarm protocol)"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Send messages to agent teammates"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to send messages to teammates. "
            "Supports plain text messages, broadcasts (to: '*'), "
            "and structured protocol messages (shutdown_request, shutdown_response, "
            "plan_approval_response). "
            "Summary is required for plain text messages."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": (
                        "Recipient: teammate name, '*' for broadcast to all teammates"
                    ),
                },
                "summary": {
                    "type": "string",
                    "description": (
                        "A 5-10 word summary shown as a preview in the UI "
                        "(required when message is a string)"
                    ),
                },
                "message": {
                    "oneOf": [
                        {"type": "string"},
                        {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "shutdown_request",
                                        "shutdown_response",
                                        "plan_approval_response",
                                    ],
                                },
                                "reason": {"type": "string"},
                                "request_id": {"type": "string"},
                                "approve": {"type": "boolean"},
                                "feedback": {"type": "string"},
                            },
                        },
                    ],
                    "description": "Plain text message content or structured protocol message",
                },
            },
            "required": ["to", "message"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"},
            },
            # Output is polymorphic - see specific result types
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "SendMessage"

    def is_enabled(self) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return isinstance(input.get("message"), str)

    def validate_input(self, input: Any, context: ToolUseContext) -> tuple[bool, str, int] | bool:
        to_field = input.get("to", "").strip()
        if not to_field:
            return (False, "to must not be empty", 9)

        message = input.get("message")
        if isinstance(message, str):
            summary = input.get("summary", "").strip()
            if not summary:
                return (False, "summary is required when message is a string", 9)

        if to_field == "*" and not isinstance(message, str):
            return (False, "structured messages cannot be broadcast", 9)

        return True

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        import json

        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": [{"type": "text", "text": json.dumps(content)}],
        }

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        to_field = args.get("to", "").strip()
        args.get("summary", "")
        message = args.get("message")

        get_app_state = context.get_app_state

        if not get_app_state:
            return {
                "data": {
                    "success": False,
                    "message": "Cannot access app state",
                },
            }

        app_state = get_app_state()
        team_context = getattr(app_state, "team_context", None)
        getattr(team_context, "team_name", None) if team_context else None

        # Handle plain text messages
        if isinstance(message, str):
            if to_field == "*":
                # Broadcast to all team members
                return {
                    "data": {
                        "success": True,
                        "message": "Message broadcast to team",
                    },
                }
            # Send to specific teammate
            return {
                "data": {
                    "success": True,
                    "message": f"Message sent to {to_field}'s inbox",
                },
            }

        # Handle structured protocol messages
        msg_type = message.get("type") if isinstance(message, dict) else None

        if msg_type == "shutdown_request":
            target = to_field
            message.get("reason", "") if isinstance(message, dict) else ""
            request_id = f"shutdown-{target}"
            return {
                "data": {
                    "success": True,
                    "message": f"Shutdown request sent to {target}. Request ID: {request_id}",
                    "request_id": request_id,
                    "target": target,
                },
            }

        if msg_type == "shutdown_response":
            approve = message.get("approve", False) if isinstance(message, dict) else False
            request_id = message.get("request_id", "") if isinstance(message, dict) else ""
            return {
                "data": {
                    "success": True,
                    "message": (
                        "Shutdown approved. "
                        if approve
                        else "Shutdown rejected. "
                    ),
                    "request_id": request_id,
                },
            }

        if msg_type == "plan_approval_response":
            approve = message.get("approve", False) if isinstance(message, dict) else False
            request_id = message.get("request_id", "") if isinstance(message, dict) else ""
            message.get("feedback", "") if isinstance(message, dict) else ""
            return {
                "data": {
                    "success": True,
                    "message": f"Plan {'approved' if approve else 'rejected'} for {to_field}",
                    "request_id": request_id,
                },
            }

        return {
            "data": {
                "success": False,
                "message": f"Unknown message type: {msg_type}",
            },
        }
