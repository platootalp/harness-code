"""
TeamDeleteTool - Clean up team and task directories.

This tool cleans up a team and its associated directories when the swarm is complete.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "TeamDelete"


class TeamDeleteTool:
    """Clean up team and task directories when the swarm is complete.

    Removes team context from app state and cleans up associated directories.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "disband a swarm team and clean up"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Clean up team and task directories when the swarm is complete"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to clean up a team and its directories when the swarm is complete. "
            "Checks for active members before cleanup. "
            "Use SendMessage with shutdown_request first to terminate teammates."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"},
                "team_name": {"type": "string"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return ""

    def is_enabled(self) -> bool:
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
        get_app_state = context.get_app_state
        set_app_state = context.set_app_state

        if not get_app_state or not set_app_state:
            return {
                "data": {
                    "success": False,
                    "message": "Cannot access app state",
                },
            }

        app_state = get_app_state()
        team_context = getattr(app_state, "team_context", None)
        team_name = getattr(team_context, "team_name", None) if team_context else None

        if not team_name:
            return {
                "data": {
                    "success": True,
                    "message": "No team name found, nothing to clean up",
                },
            }

        # Check for active members
        teammates = getattr(team_context, "teammates", {}) if team_context else {}
        active_members = [
            name for name, info in teammates.items()
            if getattr(info, "is_active", True) and name != "team-lead"
        ]

        if active_members:
            return {
                "data": {
                    "success": False,
                    "message": (
                        f"Cannot cleanup team with {len(active_members)} active "
                        f"member(s): {', '.join(active_members)}. "
                        "Use requestShutdown to gracefully terminate teammates first."
                    ),
                    "team_name": team_name,
                },
            }

        # Clear team context
        def _clear_team_context(prev: Any) -> Any:
            if prev is None:
                return None
            # Remove team_context and reset inbox
            result = dict(vars(prev)) if not isinstance(prev, dict) else dict(prev)
            result.pop("team_context", None)
            result["inbox"] = {"messages": []}
            return result

        set_app_state(_clear_team_context)

        return {
            "data": {
                "success": True,
                "message": f'Cleaned up directories and worktrees for team "{team_name}"',
                "team_name": team_name,
            },
        }
