"""
Commands module for Claude Code slash commands.

Provides base classes, registry, loader, and implementations for built-in commands.
"""

from claude_code.commands.add_dir import AddDirCommand
from claude_code.commands.advisor import AdvisorCommand
from claude_code.commands.agents import AgentsCommand
from claude_code.commands.base import (
    Availability,
    BaseCommand,
    CommandResult,
    CommandType,
    PromptCommand,
)
from claude_code.commands.btw import BtwCommand
from claude_code.commands.chrome import ChromeCommand
from claude_code.commands.clear import (
    ClearCommand,
    CompactCommand,
    HelpCommand,
    ModelCommand,
    get_all_commands,
    register_builtin_commands,
)
from claude_code.commands.color import ColorCommand
from claude_code.commands.config import ConfigCommand
from claude_code.commands.context import ContextCommand
from claude_code.commands.copy import CopyCommand
from claude_code.commands.cost import CostCommand
from claude_code.commands.desktop import DesktopCommand
from claude_code.commands.doctor import DoctorCommand
from claude_code.commands.effort import EffortCommand
from claude_code.commands.exit import ExitCommand
from claude_code.commands.export import ExportCommand
from claude_code.commands.extra_usage import ExtraUsageCommand
from claude_code.commands.fast import FastCommand
from claude_code.commands.feedback import FeedbackCommand
from claude_code.commands.files import FilesCommand
from claude_code.commands.git import (
    BranchCommand,
    CommitCommand,
    DiffCommand,
)
from claude_code.commands.hooks import HooksCommand
from claude_code.commands.ide import IDECommand
from claude_code.commands.init import InitCommand
from claude_code.commands.install_github_app import InstallGithubAppCommand
from claude_code.commands.loader import (
    CommandSource,
    LoadAllOptions,
    LoaderResult,
    MCPServerInfo,
    load_all_commands,
    load_builtin_commands,
    load_mcp_commands,
    load_plugin_commands,
    load_skill_dir_commands,
)
from claude_code.commands.login import LoginCommand
from claude_code.commands.logout import LogoutCommand
from claude_code.commands.mcp import McpCommand
from claude_code.commands.memory import MemoryCommand
from claude_code.commands.mobile import MobileCommand
from claude_code.commands.output_style import OutputStyleCommand
from claude_code.commands.passes import PassesCommand
from claude_code.commands.plan import PlanCommand
from claude_code.commands.privacy_settings import PrivacySettingsCommand
from claude_code.commands.rate_limit_options import RateLimitOptionsCommand
from claude_code.commands.registry import (
    CommandFilter,
    CommandRegistry,
    get_builtin_command,
    get_builtin_registry,
    list_builtin_commands,
    register_builtin,
)
from claude_code.commands.remote_env import RemoteEnvCommand
from claude_code.commands.remote_setup import RemoteSetupCommand
from claude_code.commands.rename import RenameCommand
from claude_code.commands.resume import ResumeCommand
from claude_code.commands.rewind import RewindCommand
from claude_code.commands.sandbox_toggle import SandboxToggleCommand
from claude_code.commands.session import SessionCommand
from claude_code.commands.skills_cmd import SkillsCommand
from claude_code.commands.stats import StatsCommand
from claude_code.commands.status import StatusCommand
from claude_code.commands.tag import TagCommand
from claude_code.commands.terminal_setup import TerminalSetupCommand
from claude_code.commands.theme import ThemeCommand
from claude_code.commands.thinkback import ThinkbackCommand
from claude_code.commands.upgrade import UpgradeCommand
from claude_code.commands.usage import UsageCommand
from claude_code.commands.vim import VimCommand

__all__ = [
    # Base
    "Availability",
    "BaseCommand",
    "CommandResult",
    "CommandType",
    "PromptCommand",
    # Registry
    "CommandFilter",
    "CommandRegistry",
    "get_builtin_command",
    "get_builtin_registry",
    "list_builtin_commands",
    "register_builtin",
    # Loader
    "CommandSource",
    "LoadAllOptions",
    "LoaderResult",
    "MCPServerInfo",
    "load_all_commands",
    "load_builtin_commands",
    "load_mcp_commands",
    "load_plugin_commands",
    "load_skill_dir_commands",
    # Builtin commands
    "ClearCommand",
    "CompactCommand",
    "HelpCommand",
    "ModelCommand",
    "get_all_commands",
    "register_builtin_commands",
    # Git commands
    "CommitCommand",
    "BranchCommand",
    "DiffCommand",
    # Additional commands
    "AddDirCommand",
    "AdvisorCommand",
    "AgentsCommand",
    "BtwCommand",
    "ColorCommand",
    "ConfigCommand",
    "ContextCommand",
    "CopyCommand",
    "DoctorCommand",
    "EffortCommand",
    "ExitCommand",
    "ExportCommand",
    "FastCommand",
    "FeedbackCommand",
    "FilesCommand",
    "HooksCommand",
    "IDECommand",
    "InitCommand",
    "LoginCommand",
    "LogoutCommand",
    "McpCommand",
    "MemoryCommand",
    "PassesCommand",
    "RenameCommand",
    "ResumeCommand",
    "RewindCommand",
    "SessionCommand",
    "SkillsCommand",
    "StatsCommand",
    "StatusCommand",
    "ThemeCommand",
    "UpgradeCommand",
    "UsageCommand",
    "VimCommand",
    # Special commands
    "ChromeCommand",
    "DesktopCommand",
    "ExtraUsageCommand",
    "InstallGithubAppCommand",
    "MobileCommand",
    "OutputStyleCommand",
    "PlanCommand",
    "PrivacySettingsCommand",
    "RateLimitOptionsCommand",
    "RemoteEnvCommand",
    "RemoteSetupCommand",
    "SandboxToggleCommand",
    "TagCommand",
    "TerminalSetupCommand",
    "ThinkbackCommand",
]
