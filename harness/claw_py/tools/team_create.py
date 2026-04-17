"""
TeamCreateTool - Create a new team for coordinating multiple agents.

This tool creates a team with a name, description, and agent type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "TeamCreate"


class TeamCreateTool:
    """Create a new team for coordinating multiple agents.

    Creates a team with a name, optional description, and optional agent type.
    The team lead becomes the first member.

    Attributes:
        name: The tool's unique identifier.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "create a multi-agent swarm team"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Create a new team for coordinating multiple agents"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to create a new team for coordinating multiple agents. "
            "Provide a team name, optional description, and optional agent type. "
            "The team lead becomes the first member of the team."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "team_name": {
                    "type": "string",
                    "description": "Name for the new team to create",
                },
                "description": {
                    "type": "string",
                    "description": "Team description/purpose",
                },
                "agent_type": {
                    "type": "string",
                    "description": "Type/role of the team lead (e.g., 'researcher', 'test-runner')",
                },
            },
            "required": ["team_name"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "team_name": {"type": "string"},
                "team_file_path": {"type": "string"},
                "lead_agent_id": {"type": "string"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return ""

    def is_enabled(self) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        return str(input.get("team_name", ""))

    def validate_input(self, input: Any, context: ToolUseContext) -> tuple[bool, str, int] | bool:
        team_name = input.get("team_name", "").strip()
        if not team_name:
            return (False, "team_name is required for TeamCreate", 9)
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
        team_name = args.get("team_name", "").strip()
        args.get("description", "")
        agent_type = args.get("agent_type", "team-lead")

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

        # Check if already in a team
        team_context = getattr(app_state, "team_context", None)
        if team_context:
            existing_name = getattr(team_context, "team_name", None)
            if existing_name:
                return {
                    "data": {
                        "success": False,
                        "message": f'Already leading team "{existing_name}". A leader can only manage one team at a time.',
                    },
                }

        # Generate lead agent ID
        lead_agent_id = f"team-lead@{team_name}"

        # Update app state with team context
        def _set_team_context(prev: Any) -> Any:
            if prev is None:
                return None
            return {
                **vars(prev),
                "team_context": {
                    "team_name": team_name,
                    "lead_agent_id": lead_agent_id,
                    "teammates": {
                        lead_agent_id: {
                            "name": "team-lead",
                            "agent_type": agent_type,
                            "color": "#4A90D9",
                            "spawned_at": None,
                        },
                    },
                },
            }

        set_app_state(_set_team_context)

        return {
            "data": {
                "team_name": team_name,
                "team_file_path": f"~/.claude/teams/{team_name}.json",
                "lead_agent_id": lead_agent_id,
            },
        }
