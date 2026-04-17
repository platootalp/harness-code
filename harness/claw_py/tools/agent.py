"""
AgentTool - Spawn and run a sub-agent.

This tool allows spawning sub-agents to perform tasks in parallel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.tool import ToolUseContext


TOOL_NAME = "Agent"
LEGACY_TOOL_NAME = "Subagent"


# Builtin agent types
BUILTIN_AGENT_TYPES = {
    "general-purpose": {
        "name": "general-purpose",
        "description": "General purpose agent for any task",
        "model": "sonnet",
    },
    "explore": {
        "name": "explore",
        "description": "Fast agent specialized for exploring codebases",
        "model": "sonnet",
    },
    "plan": {
        "name": "plan",
        "description": "Software architect agent for designing implementation plans",
        "model": "opus",
    },
    "code-review": {
        "name": "code-review",
        "description": "Agent for reviewing code against design documents",
        "model": "sonnet",
    },
}


class AgentTool:
    """Spawn and run a sub-agent to perform a task.

    Allows running agents in foreground (blocking) or background (async).
    Supports named agents for in-process communication.

    Attributes:
        name: The tool's unique identifier.
        aliases: Legacy alias names.
        description: Human-readable description of the tool.
        input_schema: JSON Schema for the tool's input parameters.
        output_schema: JSON Schema for the tool's output.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = [LEGACY_TOOL_NAME]
    search_hint: str | None = "spawn a sub-agent to perform a task in parallel"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Spawn a sub-agent to perform a task"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to spawn a sub-agent to perform a task. "
            "The agent runs with the same tools and permissions as the parent. "
            "Set run_in_background=true to run asynchronously. "
            "Named agents can receive messages via SendMessage while running."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "A short (3-5 word) description of the task",
                },
                "prompt": {
                    "type": "string",
                    "description": "The task for the agent to perform",
                },
                "subagent_type": {
                    "type": "string",
                    "description": "The type of specialized agent to use (e.g., general-purpose, explore, plan)",
                },
                "model": {
                    "type": "string",
                    "enum": ["sonnet", "opus", "haiku"],
                    "description": "Optional model override for this agent",
                },
                "run_in_background": {
                    "type": "boolean",
                    "description": "Set to true to run this agent in the background",
                },
                "name": {
                    "type": "string",
                    "description": "Name for the spawned agent. Makes it addressable via SendMessage.",
                },
            },
            "required": ["description", "prompt"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["completed", "async_launched"]},
                "agentId": {"type": "string"},
                "description": {"type": "string"},
                "prompt": {"type": "string"},
                "result": {"type": "string"},
                "error": {"type": "string"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "Agent"

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        return f"{input.get('subagent_type', 'general-purpose')}: {input.get('description', '')}"

    def render_tool_use_message(self, input: Any) -> str | None:
        desc = input.get("description", "")
        return f"Running agent: {desc}"

    def render_tool_use_progress_message(self, input: Any) -> str | None:
        return None

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        status = content.get("status")
        result = content.get("result", "")
        error = content.get("error")

        if error:
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": f"Agent error: {error}",
                "is_error": True,
            }

        if status == "async_launched":
            agent_id = content.get("agentId", "")
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": f"Agent launched in background. ID: {agent_id}",
            }

        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": result or "Agent completed",
        }

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        description = args.get("description", "")
        prompt = args.get("prompt", "")
        subagent_type = args.get("subagent_type", "general-purpose")
        model = args.get("model")
        run_in_background = args.get("run_in_background", False)
        name = args.get("name")

        get_app_state = context.get_app_state
        set_app_state = context.set_app_state

        if not get_app_state or not set_app_state:
            return {
                "data": {
                    "status": "completed",
                    "description": description,
                    "prompt": prompt,
                    "result": "Agent context not available",
                },
            }

        app_state = get_app_state()
        getattr(app_state, "tasks", {})

        # Generate agent ID
        import secrets

        agent_id = f"agent-{secrets.token_hex(4)}"
        if name:
            agent_id = f"agent-{name}"

        if run_in_background:
            # Create async agent task
            from ..models.task import Task, TaskStatus, TaskType

            new_task = Task(
                id=agent_id,
                type=TaskType.SUB_AGENT,
                status=TaskStatus.RUNNING,
                input={"prompt": prompt, "subagent_type": subagent_type, "model": model},
                metadata={"description": description, "name": name},
            )

            def _add_agent_task(prev: Any) -> Any:
                if prev is None:
                    return None
                tasks_dict = getattr(prev, "tasks", {})
                new_tasks = {**tasks_dict, agent_id: new_task}
                return {**vars(prev), "tasks": new_tasks}

            set_app_state(_add_agent_task)

            return {
                "data": {
                    "status": "async_launched",
                    "agentId": agent_id,
                    "description": description,
                    "prompt": prompt,
                },
            }

        # Synchronous execution (simplified - actual implementation would
        # run the agent through the engine)
        return {
            "data": {
                "status": "completed",
                "description": description,
                "prompt": prompt,
                "result": "Agent execution completed",
            },
        }
