"""
CronDeleteTool - Cancel a scheduled cron job.

Migrated from src/tools/ScheduleCronTool/CronDeleteTool.ts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


TOOL_NAME = "CronDelete"


class CronDeleteTool:
    """Cancel a scheduled cron job.

    Validates job exists and owned by caller. Teammates can only delete their own crons.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "cancel a scheduled cron job"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Cancel a scheduled cron job"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to cancel a scheduled cron job by its ID. "
            "You can only delete jobs you created (or all if you are the team lead)."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Job ID returned by CronCreate.",
                },
            },
            "required": ["id"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return ""

    def is_enabled(self) -> bool:
        from ..utils.cron import is_kairos_cron_enabled
        return is_kairos_cron_enabled()

    def to_auto_classifier_input(self, input: Any) -> str:
        return str(input.get("id", ""))

    def validate_input(self, input: Any, context: Any) -> tuple[bool, str, int] | bool:
        from ..utils.cron_tasks import list_all_cron_tasks
        from ..utils.teammate_context import get_teammate_context

        job_id = input.get("id", "")
        tasks = list_all_cron_tasks()
        task = None
        for t in tasks:
            if t.get("id") == job_id:
                task = t
                break

        if task is None:
            return (False, f"No scheduled job with id '{job_id}'", 1)

        # Teammates may only delete their own crons
        teammate_ctx = get_teammate_context()
        if teammate_ctx and task.get("agent_id") != teammate_ctx.get("agent_id"):
            return (
                False,
                f"Cannot delete cron job '{job_id}': owned by another agent",
                2,
            )

        return True

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": f"Cancelled job {content['id']}.",
        }

    async def call(
        self,
        args: dict[str, Any],
        context: Any,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        from ..utils.cron_tasks import remove_cron_tasks

        job_id = args.get("id", "")
        remove_cron_tasks([job_id])
        return {"data": {"id": job_id}}
