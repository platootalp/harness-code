"""Branch command for Claude Code.

Creates a fork of the current conversation at this point, allowing users to
explore alternative approaches without losing the original conversation.

TypeScript equivalent: src/commands/branch/branch.ts, src/commands/branch/index.ts
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    from ..cli.state import REPLState


def derive_first_prompt(
    first_user_message: dict[str, Any] | None,
) -> str:
    """Derive a single-line title base from the first user message.

    Collapses whitespace — multiline first messages (pasted stacks, code)
    otherwise flow into the saved title and break the resume hint.

    Args:
        first_user_message: The first user message dict.

    Returns:
        A truncated, single-line title string.
    """
    if not first_user_message:
        return "Branched conversation"

    msg_content = first_user_message.get("message", {}).get("content")
    if not msg_content:
        return "Branched conversation"

    if isinstance(msg_content, str):
        raw = msg_content
    elif isinstance(msg_content, list):
        for block in msg_content:
            if isinstance(block, dict) and block.get("type") == "text":
                raw = block.get("text", "")
                break
        else:
            return "Branched conversation"
    else:
        return "Branched conversation"

    collapsed = " ".join(raw.split()).strip()
    return collapsed[:100] if collapsed else "Branched conversation"


def get_unique_fork_name(base_name: str) -> str:
    """Generate a unique fork name by checking for collisions.

    If "baseName (Branch)" already exists, tries "baseName (Branch 2)",
    "baseName (Branch 3)", etc.

    Args:
        base_name: The base name for the fork.

    Returns:
        A unique fork name string.
    """
    import re
    from pathlib import Path

    candidate = f"{base_name} (Branch)"
    custom_titles_dir = Path.home() / ".claude" / "sessions"

    if not custom_titles_dir.is_dir():
        return candidate

    # Check if exact name already exists
    existing_files = list(custom_titles_dir.glob("*.jsonl"))
    existing_titles: set[str] = set()
    for f in existing_files:
        try:
            with open(f) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if isinstance(entry, dict) and "customTitle" in entry:
                        existing_titles.add(entry["customTitle"])
        except (OSError, json.JSONDecodeError):
            pass

    if candidate not in existing_titles:
        return candidate

    # Find existing branch numbers
    used_numbers: set[int] = {1}
    pattern = re.compile(rf"^{re.escape(base_name)} \(Branch(?: (\d+))?\)$")
    for title in existing_titles:
        m = pattern.match(title)
        if m:
            if m.group(1):
                used_numbers.add(int(m.group(1)))
            else:
                used_numbers.add(1)

    next_num = 2
    while next_num in used_numbers:
        next_num += 1

    return f"{base_name} (Branch {next_num})"


@dataclass
class BranchCommand(BaseCommand):
    """Create a branch of the current conversation at this point.

    Creates a fork of the current conversation for exploring alternative
    approaches without losing the original session.

    TypeScript equivalent: src/commands/branch/branch.ts, src/commands/branch/index.ts
    """

    name: str = "branch"
    aliases: list[str] = field(default_factory=lambda: [])
    description: str = "Create a branch of the current conversation at this point"
    argument_hint: str | None = "[name]"
    command_type: CommandType = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        # Build lookup set for aliases
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the branch command.

        Creates a fork of the current conversation.
        """
        custom_title = args.strip() if args.strip() else None

        repl_state: REPLState | None = context.get("_repl_state")

        if repl_state is None:
            return CommandResult(
                type="text",
                value="Error: No active session found.",
            )

        try:
            fork_session_id = str(uuid4())

            if not hasattr(repl_state, "session") or not repl_state.session:
                return CommandResult(
                    type="text",
                    value="Error: No session found to branch.",
                )

            original_session_id = repl_state.session.session_id or ""

            # Build session data for the fork
            messages = repl_state.messages if hasattr(repl_state, "messages") else []

            # Serialize messages
            serialized_messages: list[dict[str, Any]] = []
            for msg in messages:
                if hasattr(msg, "model_dump"):
                    serialized_messages.append(msg.model_dump())
                elif isinstance(msg, dict):
                    serialized_messages.append(msg)

            # Get fork title
            base_name = custom_title or "Branched conversation"
            effective_title = get_unique_fork_name(base_name)

            # Save fork metadata
            self._save_fork_metadata(
                fork_session_id,
                original_session_id,
                effective_title,
                serialized_messages,
            )

            branch_msg = "Branched conversation"
            if custom_title:
                branch_msg = f'Branched conversation "{custom_title}"'

            if original_session_id:
                branch_msg += "\nYou are now in the branch.\n"
                branch_msg += f"To resume the original: claude -r {original_session_id}"
            else:
                branch_msg += f"\nResume with: /resume {fork_session_id}"

            return CommandResult(type="text", value=branch_msg)

        except Exception as e:
            return CommandResult(
                type="text",
                value=f"Failed to branch conversation: {e}",
            )

    def _save_fork_metadata(
        self,
        fork_session_id: str,
        original_session_id: str,
        title: str,
        messages: list[dict[str, Any]],
    ) -> None:
        """Save fork session metadata to disk.

        Args:
            fork_session_id: The new session ID for the fork.
            original_session_id: The original session ID.
            title: The custom title for the fork.
            messages: Serialized messages to save.
        """
        from pathlib import Path

        sessions_dir = Path.home() / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        fork_path = sessions_dir / f"{fork_session_id}.jsonl"

        # Write messages as JSONL
        try:
            with open(fork_path, "w", encoding="utf-8") as f:
                for msg in messages:
                    # Add session metadata
                    entry = {
                        **msg,
                        "sessionId": fork_session_id,
                        "parentUuid": msg.get("uuid"),
                        "isSidechain": False,
                        "forkedFrom": {
                            "sessionId": original_session_id,
                            "messageUuid": msg.get("uuid"),
                        },
                    }
                    f.write(json.dumps(entry) + "\n")

                # Write title metadata entry
                title_entry = {
                    "type": "session-title",
                    "sessionId": fork_session_id,
                    "customTitle": title,
                }
                f.write(json.dumps(title_entry) + "\n")
        except OSError:
            # Non-fatal: fork metadata save failed, continue anyway
            pass
