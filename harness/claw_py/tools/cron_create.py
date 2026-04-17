"""
CronCreateTool - Schedule a recurring or one-shot prompt.

Migrated from src/tools/ScheduleCronTool/CronCreateTool.ts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


TOOL_NAME = "CronCreate"
MAX_JOBS = 50
DEFAULT_MAX_AGE_DAYS = 7


class CronCreateTool:
    """Schedule a recurring or one-shot prompt.

    Validates cron expression, checks job limit. Supports durable (persisted)
    and session-only jobs. Teammates cannot create durable crons.
    """

    name: str = TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "schedule a recurring or one-shot prompt"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return "Schedule a recurring or one-shot cron job"

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to schedule a prompt to be enqueued at a specific time. "
            "Supports standard 5-field cron expressions. "
            "Set recurring=false for one-shot tasks. "
            "Set durable=true to persist across sessions."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cron": {
                    "type": "string",
                    "description": (
                        'Standard 5-field cron expression in local time: "M H DoM Mon DoW" '
                        '(e.g. "*/5 * * * *" = every 5 minutes, "30 14 28 2 *" = Feb 28 at 2:30pm local once).'
                    ),
                },
                "prompt": {
                    "type": "string",
                    "description": "The prompt to enqueue at each fire time.",
                },
                "recurring": {
                    "type": "boolean",
                    "description": (
                        f"true (default) = fire on every cron match until deleted or auto-expired after {DEFAULT_MAX_AGE_DAYS} days. "
                        'false = fire once at the next match, then auto-delete. Use false for "remind me at X" one-shot requests.'
                    ),
                },
                "durable": {
                    "type": "boolean",
                    "description": (
                        "true = persist to .claude/scheduled_tasks.json and survive restarts. "
                        "false (default) = in-memory only, dies when this Claude session ends. "
                        "Use true only when the user asks the task to survive across sessions."
                    ),
                },
            },
            "required": ["cron", "prompt"],
            "additionalProperties": False,
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "humanSchedule": {"type": "string"},
                "recurring": {"type": "boolean"},
                "durable": {"type": "boolean"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return ""

    def is_enabled(self) -> bool:
        from ..utils.cron import is_kairos_cron_enabled
        return is_kairos_cron_enabled()

    def to_auto_classifier_input(self, input: Any) -> str:
        cron = input.get("cron", "")
        prompt = input.get("prompt", "")
        return f"{cron}: {prompt}"

    def validate_input(self, input: Any, context: Any) -> tuple[bool, str, int] | bool:
        from ..utils.cron import next_cron_run_ms, parse_cron_expression
        from ..utils.cron_tasks import list_all_cron_tasks
        from ..utils.teammate_context import get_teammate_context

        cron = input.get("cron", "")
        durable = input.get("durable", False)

        if not parse_cron_expression(cron):
            return (
                False,
                f"Invalid cron expression '{cron}'. Expected 5 fields: M H DoM Mon DoW.",
                1,
            )

        from datetime import UTC, datetime
        now_ms = int(datetime.now(UTC).timestamp() * 1000)
        if next_cron_run_ms(cron, now_ms) is None:
            return (
                False,
                f"Cron expression '{cron}' does not match any calendar date in the next year.",
                2,
            )

        # Check job limit
        tasks: list[dict[str, Any]] = list_all_cron_tasks()
        if len(tasks) >= MAX_JOBS:
            return (
                False,
                f"Too many scheduled jobs (max {MAX_JOBS}). Cancel one first.",
                3,
            )

        # Teammates don't persist across sessions, so a durable teammate cron
        # would orphan on restart
        if durable and get_teammate_context():
            return (
                False,
                "durable crons are not supported for teammates (teammates do not persist across sessions)",
                4,
            )

        return True

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        job_id = content.get("id")
        human_schedule = content.get("humanSchedule")
        recurring = content.get("recurring", True)
        durable = content.get("durable", False)

        where = (
            "Persisted to .claude/scheduled_tasks.json"
            if durable
            else "Session-only (not written to disk, dies when Claude exits)"
        )

        if recurring:
            msg = (
                f"Scheduled recurring job {job_id} ({human_schedule}). {where}. "
                f"Auto-expires after {DEFAULT_MAX_AGE_DAYS} days. Use CronDelete to cancel sooner."
            )
        else:
            msg = (
                f"Scheduled one-shot task {job_id} ({human_schedule}). {where}. "
                "It will fire once then auto-delete."
            )

        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": msg,
        }

    async def call(
        self,
        args: dict[str, Any],
        context: Any,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        from ..utils.cron import cron_to_human, is_durable_cron_enabled
        from ..utils.cron_tasks import add_cron_task
        from ..utils.teammate_context import get_teammate_context

        cron = args.get("cron", "")
        prompt = args.get("prompt", "")
        recurring = args.get("recurring", True)
        durable = args.get("durable", False)

        # Kill switch forces session-only
        effective_durable = durable and is_durable_cron_enabled()

        teammate_ctx = get_teammate_context()
        metadata: dict[str, Any] = {}
        if teammate_ctx and teammate_ctx.get("agent_id"):
            metadata["agent_id"] = teammate_ctx["agent_id"]

        job_id = add_cron_task(
            cron, prompt, recurring, effective_durable, metadata if metadata else None
        )

        return {
            "data": {
                "id": job_id,
                "humanSchedule": cron_to_human(cron),
                "recurring": recurring,
                "durable": effective_durable,
            }
        }
