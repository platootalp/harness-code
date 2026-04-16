"""Tag command for Claude Code.

Toggle a searchable tag on the current session.

TypeScript equivalent: src/commands/tag/index.ts, src/commands/tag/tag.tsx
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


HELP_TEXT = """Usage: /tag <tag-name>

Toggle a searchable tag on the current session.
Run the same command again to remove the tag.
Tags are displayed after the branch name in /resume and can be searched with /.

Examples:
  /tag bugfix        # Add tag
  /tag bugfix        # Remove tag (toggle)
  /tag feature-auth
  /tag wip"""


@dataclass
class TagCommand(BaseCommand):
    """Toggle a searchable tag on the current session.

    TypeScript equivalent: src/commands/tag/index.ts, src/commands/tag/tag.tsx
    """

    name: str = "tag"
    aliases: list[str] = field(default_factory=list)
    description: str = "Toggle a searchable tag on the current session"
    argument_hint: str | None = "<tag-name>"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the tag command.

        Tags the current session with a searchable label.
        Running the same command again removes the tag.
        """
        trimmed = args.strip()

        # Show help if no args or help flag
        if not trimmed or trimmed in ("--help", "-h", "help"):
            return CommandResult(type="text", value=HELP_TEXT)

        # Normalize the tag (remove leading # if present, collapse whitespace)
        tag_name = " ".join(trimmed.split()).strip()
        if tag_name.startswith("#"):
            tag_name = tag_name[1:]
        tag_name = tag_name.strip()

        if not tag_name:
            return CommandResult(
                type="text",
                value="Tag name cannot be empty. Usage: /tag <tag-name>",
            )

        repl_state: Any = context.get("_repl_state")
        session_id = None
        if repl_state is not None and hasattr(repl_state, "session"):
            session = repl_state.session
            if session is not None and hasattr(session, "session_id"):
                session_id = session.session_id

        if not session_id:
            return CommandResult(
                type="text",
                value="No active session to tag.",
            )

        # Get current tag for this session
        current_tag = self._get_current_tag(session_id)

        # If same tag, this is a toggle-off request
        if current_tag == tag_name:
            # Remove the tag
            self._save_tag(session_id, "", context)
            return CommandResult(
                type="text",
                value=f"Removed tag #{tag_name}",
            )

        # Save the new tag
        self._save_tag(session_id, tag_name, context)
        is_replacing = current_tag != "" if current_tag else False
        if is_replacing:
            return CommandResult(
                type="text",
                value=f"Updated tag from #{current_tag} to #{tag_name}",
            )
        return CommandResult(
            type="text",
            value=f"Tagged session with #{tag_name}",
        )

    def _get_current_tag(self, session_id: str) -> str:
        """Get the current tag for a session."""
        tags_file = self._get_tags_file()
        if not tags_file or not tags_file.exists():
            return ""

        try:
            with open(tags_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry: dict[str, Any] = json.loads(line)
                    if entry.get("sessionId") == session_id:
                        return str(entry.get("tag", ""))
        except (OSError, json.JSONDecodeError):
            pass
        return ""

    def _get_tags_file(self) -> Path | None:
        """Get the path to the tags storage file."""
        return Path.home() / ".claude" / "session-tags.jsonl"

    def _save_tag(self, session_id: str, tag: str, context: dict[str, Any]) -> bool:
        """Save a tag for a session."""
        tags_file = self._get_tags_file()
        if tags_file is None:
            return False

        try:
            tags_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

            # Read existing entries
            entries: list[dict[str, Any]] = []
            if tags_file.exists():
                with open(tags_file, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if entry.get("sessionId") != session_id:
                                entries.append(entry)
                        except json.JSONDecodeError:
                            pass

            # Add new entry
            if tag:
                entries.append({
                    "sessionId": session_id,
                    "tag": tag,
                })

            # Write back
            with open(tags_file, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")

            return True
        except OSError:
            return False
