"""
CronListTool - List active cron jobs.

Migrated from src/tools/ScheduleCronTool/CronListTool.ts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


TOOL_NAME = "CronList"


class CronListTool:
    """List active cron jobs.

    Returns all scheduled cron tasks. Teammates see only their own crons;
    team lead sees all.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "list active cron jobs"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "List all scheduled cron jobs"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to list all active scheduled cron jobs. "
            "Returns job IDs, schedules, and prompts for each job."
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
                "jobs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "cron": {"type": "string"},
                            "humanSchedule": {"type": "string"},
                            "prompt": {"type": "string"},
                            "recurring": {"type": "boolean"},
                            "durable": {"type": "boolean"},
                        },
                    },
                },
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return ""

    def is_enabled(self) -> bool:
        from ..utils.cron import is_kairos_cron_enabled
        return is_kairos_cron_enabled()

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        return ""

    def validate_input(self, input: Any, context: Any) -> tuple[bool, str, int] | bool:
        return True

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        jobs = content.get("jobs", [])
        if not jobs:
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": "No scheduled jobs.",
            }

        lines = []
        for job in jobs:
            recurring = " (recurring)" if job.get("recurring") else " (one-shot)"
            durable = " [session-only]" if job.get("durable") is False else ""
            prompt = job.get("prompt", "")[:80]
            if len(job.get("prompt", "")) > 80:
                prompt += "..."
            lines.append(
                f"{job['id']} — {job['humanSchedule']}{recurring}{durable}: {prompt}"
            )

        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": "\n".join(lines),
        }

    async def call(
        self,
        args: dict[str, Any],
        context: Any,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        from ..utils.cron import cron_to_human
        from ..utils.cron_tasks import list_all_cron_tasks
        from ..utils.teammate_context import get_teammate_context

        all_tasks: list[dict[str, Any]] = list_all_cron_tasks()

        # Teammates only see their own crons; team lead sees all
        teammate_ctx = get_teammate_context()
        if teammate_ctx:
            tasks = [t for t in all_tasks if t.get("agent_id") == teammate_ctx.get("agent_id")]
        else:
            tasks = all_tasks

        jobs = []
        for t in tasks:
            job = {
                "id": t["id"],
                "cron": t["cron"],
                "humanSchedule": cron_to_human(t["cron"]),
                "prompt": t["prompt"],
            }
            if t.get("recurring"):
                job["recurring"] = True
            if t.get("durable") is False:
                job["durable"] = False
            jobs.append(job)

        return {"data": {"jobs": jobs}}
