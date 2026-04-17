"""Commit command - create git commit."""
from __future__ import annotations

import subprocess

commit_command = {
    'name': 'commit',
    'description': 'Create a git commit',
    'command_type': 'prompt',
    'progress_message': 'creating commit',

    'get_prompt_for_command': lambda args, ctx: _get_commit_prompt(args, ctx),
}


async def _get_commit_prompt(args: str, ctx) -> list[str]:
    """Get the commit prompt for the model."""
    # Get git status and diff
    status = subprocess.run(
        ['git', 'status', '--short'],
        capture_output=True,
        text=True,
        cwd=ctx.get('cwd', '.'),
    )

    diff = subprocess.run(
        ['git', 'diff', '--staged'],
        capture_output=True,
        text=True,
        cwd=ctx.get('cwd', '.'),
    )

    prompt = f"""Analyze the following git status and staged changes to create a proper commit message.

Git status:
{status.stdout or '(no changes)'}

Staged changes:
{diff.stdout or '(no staged changes)'}

Create a concise commit message following conventional commit format (type: description).
If there are no staged changes, suggest which files should be staged."""

    return [prompt]
