"""Git commit command for Claude Code.

This command creates a git commit by generating a rich prompt with git context
and safety protocol, then sending it to the model for analysis and execution.

TypeScript equivalent: src/commands/commit.ts
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import PromptCommand

if TYPE_CHECKING:
    pass


@dataclass
class CommitCommand(PromptCommand):
    """Create a git commit.

    This is a prompt-type command that generates rich git context
    and safety protocol, then sends it to the model for analysis.

    TypeScript equivalent: src/commands/commit.ts
    """

    name: str = "commit"
    description: str = "Create a git commit"
    argument_hint: str | None = None
    source: str = "builtin"
    _progress_message: str = "creating commit"

    # Tools allowed for this command
    _allowed_tools: list[str] = field(
        default_factory=lambda: [
            "Bash(git add:*)",
            "Bash(git status:*)",
            "Bash(git commit:*)",
        ]
    )

    async def get_prompt_content(
        self,
        args: str,
        context: dict[str, Any],
    ) -> str:
        """Generate the git commit prompt content.

        Args:
            args: Command arguments (unused for commit).
            context: Execution context.

        Returns:
            Rich prompt content with git context and safety protocol.
        """
        git_context = self._get_git_context()
        safety_protocol = self._get_safety_protocol()

        # Build the prompt
        prompt_parts = [
            "## Context",
            "",
            git_context,
            "",
            safety_protocol,
            "",
            "## Your task",
            "",
            "Based on the above changes, create a single git commit:",
            "",
            "1. Analyze all staged changes and draft a commit message:",
            "   - Look at the recent commits above to follow this repository's commit message style",
            "   - Summarize the nature of the changes (new feature, enhancement, bug fix, refactoring, test, docs, etc.)",
            "   - Ensure the message accurately reflects the changes and their purpose",
            "   - Draft a concise (1-2 sentences) commit message that focuses on the \"why\" rather than the \"what\"",
            "",
            "2. Stage relevant files and create the commit using HEREDOC syntax:",
            "```",
            "git commit -m \"$(cat <<'EOF'",
            "Commit message here.",
            "EOF",
            ")\"",
            "```",
            "",
            "You have the capability to call multiple tools in a single response. ",
            "Stage and create the commit using a single message. Do not use any other tools or do anything else. ",
            "Do not send any other text or messages besides these tool calls.",
        ]

        return "\n".join(prompt_parts)

    def _get_git_context(self) -> str:
        """Get current git context (status, diff, branch, recent commits).

        Returns:
            Git context as a formatted string.
        """
        parts: list[str] = []

        # Current git status
        status = self._run_git(["git", "status", "--porcelain"])
        if status:
            parts.append(f"- Current git status:\n```\n{status}\n```")

        # Current git diff
        diff = self._run_git(["git", "diff", "HEAD"])
        if diff:
            parts.append(f"- Current git diff (staged and unstaged changes):\n```\n{diff}\n```")

        # Current branch
        branch = self._run_git(["git", "branch", "--show-current"])
        if branch:
            parts.append(f"- Current branch: {branch}")

        # Recent commits
        log = self._run_git(["git", "log", "--oneline", "-10"])
        if log:
            parts.append(f"- Recent commits:\n```\n{log}\n```")

        return "\n\n".join(parts) if parts else "No git repository found."

    def _get_safety_protocol(self) -> str:
        """Get the git safety protocol.

        Returns:
            Safety protocol as a formatted string.
        """
        return """## Git Safety Protocol

- NEVER update the git config
- NEVER skip hooks (--no-verify, --no-gpg-sign, etc) unless the user explicitly requests it
- CRITICAL: ALWAYS create NEW commits. NEVER use git commit --amend, unless the user explicitly requests it
- Do not commit files that likely contain secrets (.env, credentials.json, etc). Warn the user if they specifically request to commit those files
- If there are no changes to commit (i.e., no untracked files and no modifications), do not create an empty commit
- Never use git commands with the -i flag (like git rebase -i or git add -i) since they require interactive input which is not supported"""

    def _run_git(self, cmd: list[str]) -> str:
        """Run a git command and return its output.

        Args:
            cmd: Command and arguments as a list.

        Returns:
            Command output, or empty string on error.
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            return ""
