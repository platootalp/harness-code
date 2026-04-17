"""Install GitHub App command for Claude Code.

Set up Claude GitHub Actions for a repository.

TypeScript equivalent: src/commands/install-github-app/index.ts, src/commands/install-github-app/install-github-app.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class InstallGithubAppCommand(BaseCommand):
    """Set up Claude GitHub Actions for a repository.

    TypeScript equivalent: src/commands/install-github-app/index.ts
    """

    name: str = "install-github-app"
    aliases: list[str] = field(default_factory=list)
    description: str = "Set up Claude GitHub Actions for a repository"
    command_type = CommandType.LOCAL
    source: str = "builtin"

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name, *self.aliases}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the install-github-app command.

        Shows information about setting up GitHub Actions with Claude.
        """
        message = (
            "Install Claude GitHub App\n\n"
            "Set up Claude Code to work with your GitHub repositories via GitHub Actions.\n\n"
            "Setup options:\n"
            "1. Local setup: Configure your repository to use Claude with GitHub Actions\n"
            "2. Cloud setup: Connect Claude Code via GitHub App integration\n\n"
            "To set up for a specific repository:\n"
            "1. Navigate to your repository\n"
            "2. Go to Settings > GitHub Apps\n"
            "3. Configure Claude\n\n"
            "GitHub Actions Setup:\n"
            "https://docs.anthropic.com/en/docs/claude-code/github-actions\n\n"
            "This command launches an interactive setup wizard.\n"
            "For manual setup, see the documentation above."
        )
        return CommandResult(type="text", value=message)
