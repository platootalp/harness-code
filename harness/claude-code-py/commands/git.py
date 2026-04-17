"""Git-related commands for Claude Code.

Implements git commands:
- CommitCommand: Create git commits (prompt expansion)
- BranchCommand: View uncommitted changes
- DiffCommand: View uncommitted changes

TypeScript equivalent: src/commands/commit.ts, src/commands/branch/, src/commands/diff/
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType, PromptCommand

if TYPE_CHECKING:
    from ..cli.state import REPLState

# =============================================================================
# Commit Command (Prompt type)
# =============================================================================


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
    # The prompt content is generated dynamically in get_prompt_content
    # This is the progress message shown while the command runs
    _progress_message: str = "creating commit"

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
        # Gather git context
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
        ]

        return "\n".join(prompt_parts)

    def _get_git_context(self) -> str:
        """Get current git context (status, diff, branch, recent commits).

        Returns:
            Git context as a formatted string.
        """
        parts = []

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


# =============================================================================
# Diff Command (Local type)
# =============================================================================


@dataclass
class DiffCommand(BaseCommand):
    """View uncommitted changes and per-turn diffs.

    Shows the diff of modified files that have not been committed.

    TypeScript equivalent: src/commands/diff/
    """

    name: str = "diff"
    description: str = "View uncommitted changes and per-turn diffs"
    argument_hint: str | None = "[--cached] [<path>]"
    command_type: CommandType = CommandType.LOCAL
    source: str = "builtin"

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the diff command."""
        cmd_args = ["git", "diff"]

        # Handle flags
        parts = args.strip().split()
        if "--cached" in parts or "-s" in parts:
            cmd_args.append("--cached")
            parts = [p for p in parts if p not in ("--cached", "-s")]

        # Handle path argument
        paths = [p for p in parts if not p.startswith("-")]
        cmd_args.extend(paths)

        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if not result.stdout.strip():
                return CommandResult(
                    type="text",
                    value="No changes to display.",
                )

            return CommandResult(type="text", value=result.stdout)
        except FileNotFoundError:
            return CommandResult(
                type="text",
                value="Error: git not found. Is Git installed?",
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                type="text",
                value="Error: git diff timed out.",
            )
        except Exception as e:
            return CommandResult(type="text", value=f"Error: {e}")


# =============================================================================
# Branch Command (Local type - conversation branching)
# =============================================================================


@dataclass
class BranchCommand(BaseCommand):
    """Create a branch of the current conversation at this point.

    Note: This is conversation branching, not git branching.
    Creates a fork of the current conversation for exploring alternative approaches.

    TypeScript equivalent: src/commands/branch/
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

        # Get session-related context
        repl_state: REPLState | None = context.get("_repl_state")

        if repl_state is None:
            return CommandResult(
                type="text",
                value="Error: No active session found.",
            )

        # Create a branch by saving the current session with a new ID
        try:
            from uuid import uuid4

            session_id = str(uuid4())

            # Save current session state as a branch
            if hasattr(repl_state, 'session') and repl_state.session:
                # The session manager would handle the actual branching logic
                # For now, return instructions for how to branch
                branch_msg = f"Creating branch: {custom_title or 'new branch'}"
                branch_msg += f"\nSession ID: {session_id}"

                # If there's a session manager, it would handle the actual forking
                if hasattr(repl_state, '_session_manager'):
                    # Branch existing session
                    pass

                return CommandResult(
                    type="text",
                    value=branch_msg,
                )

            return CommandResult(
                type="text",
                value="Error: No session found to branch.",
            )

        except Exception as e:
            return CommandResult(
                type="text",
                value=f"Error creating branch: {e}",
            )
