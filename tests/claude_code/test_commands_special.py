"""
Tests for special commands - plan, thinkback, output_style, privacy_settings,
rate_limit_options, remote_env, remote_setup, tag, sandbox_toggle, terminal_setup,
extra_usage, chrome, mobile, desktop, install_github_app.

TypeScript equivalent: src/commands/{plan,thinkback,output-style,...}/index.ts
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from claude_code.commands.base import CommandType


# =============================================================================
# PlanCommand tests
# =============================================================================
class TestPlanCommand:
    """Tests for PlanCommand."""

    def test_name(self) -> None:
        from claude_code.commands.plan import PlanCommand

        assert PlanCommand().name == "plan"

    def test_description(self) -> None:
        from claude_code.commands.plan import PlanCommand

        assert "plan" in PlanCommand().description.lower()

    def test_argument_hint(self) -> None:
        from claude_code.commands.plan import PlanCommand

        assert "[open|" in PlanCommand().argument_hint

    def test_source(self) -> None:
        from claude_code.commands.plan import PlanCommand

        assert PlanCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.plan import PlanCommand

        assert "/plan" in PlanCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_without_repl_state_returns_error(self) -> None:
        """execute returns error without context."""
        from claude_code.commands.plan import PlanCommand

        cmd = PlanCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert "Error" in result.value

    @pytest.mark.asyncio
    async def test_execute_with_open_arg(self) -> None:
        """execute with 'open' argument opens plan in editor."""
        from claude_code.commands.plan import PlanCommand

        cmd = PlanCommand()

        with patch.object(cmd, "_get_plan_file_path") as mock_get_path:
            mock_get_path.return_value = None  # No existing plan file
            repl_state = MagicMock()
            repl_state.session = MagicMock()
            repl_state.session.session_id = "sess-123"
            result = await cmd.execute("open", {"_repl_state": repl_state})

        assert result.type == "text"

    @pytest.mark.asyncio
    async def test_execute_enable_plan_mode(self) -> None:
        """execute enables plan mode when no plan file exists."""
        from claude_code.commands.plan import PlanCommand

        cmd = PlanCommand()
        repl_state = MagicMock()
        repl_state.session = MagicMock()
        repl_state.session.session_id = "sess-123"

        with patch.object(cmd, "_get_plan_file_path") as mock_get_path:
            mock_get_path.return_value = None  # No existing plan file
            result = await cmd.execute("my feature", {"_repl_state": repl_state})

        assert result.type == "text"


# =============================================================================
# ThinkbackCommand tests
# =============================================================================
class TestThinkbackCommand:
    """Tests for ThinkbackCommand."""

    def test_name(self) -> None:
        from claude_code.commands.thinkback import ThinkbackCommand

        assert ThinkbackCommand().name == "think-back"

    def test_description(self) -> None:
        from claude_code.commands.thinkback import ThinkbackCommand

        assert "2025" in ThinkbackCommand().description or "review" in ThinkbackCommand().description.lower()

    def test_source(self) -> None:
        from claude_code.commands.thinkback import ThinkbackCommand

        assert ThinkbackCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.thinkback import ThinkbackCommand

        assert "/think-back" in ThinkbackCommand().get_help()


# =============================================================================
# OutputStyleCommand tests
# =============================================================================
class TestOutputStyleCommand:
    """Tests for OutputStyleCommand."""

    def test_name(self) -> None:
        from claude_code.commands.output_style import OutputStyleCommand

        assert OutputStyleCommand().name == "output-style"

    def test_is_hidden(self) -> None:
        from claude_code.commands.output_style import OutputStyleCommand

        assert OutputStyleCommand().is_hidden is True

    def test_description_deprecated(self) -> None:
        from claude_code.commands.output_style import OutputStyleCommand

        assert "deprecated" in OutputStyleCommand().description.lower()

    def test_get_help(self) -> None:
        from claude_code.commands.output_style import OutputStyleCommand

        help_text = OutputStyleCommand().get_help()
        assert "/output-style" in help_text or "output-style" in help_text

    @pytest.mark.asyncio
    async def test_execute_returns_deprecated_message(self) -> None:
        """execute returns deprecated message."""
        from claude_code.commands.output_style import OutputStyleCommand

        cmd = OutputStyleCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert "deprecated" in result.value.lower()
        assert "config" in result.value.lower()


# =============================================================================
# PrivacySettingsCommand tests
# =============================================================================
class TestPrivacySettingsCommand:
    """Tests for PrivacySettingsCommand."""

    def test_name(self) -> None:
        from claude_code.commands.privacy_settings import PrivacySettingsCommand

        assert PrivacySettingsCommand().name == "privacy-settings"

    def test_description(self) -> None:
        from claude_code.commands.privacy_settings import PrivacySettingsCommand

        assert "privacy" in PrivacySettingsCommand().description.lower()

    def test_source(self) -> None:
        from claude_code.commands.privacy_settings import PrivacySettingsCommand

        assert PrivacySettingsCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.privacy_settings import PrivacySettingsCommand

        assert "/privacy-settings" in PrivacySettingsCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """execute returns JSX node."""
        from claude_code.commands.privacy_settings import PrivacySettingsCommand

        cmd = PrivacySettingsCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None


# =============================================================================
# RateLimitOptionsCommand tests
# =============================================================================
class TestRateLimitOptionsCommand:
    """Tests for RateLimitOptionsCommand."""

    def test_name(self) -> None:
        from claude_code.commands.rate_limit_options import RateLimitOptionsCommand

        assert RateLimitOptionsCommand().name == "rate-limit-options"

    def test_is_hidden(self) -> None:
        from claude_code.commands.rate_limit_options import RateLimitOptionsCommand

        assert RateLimitOptionsCommand().is_hidden is True

    def test_description(self) -> None:
        from claude_code.commands.rate_limit_options import RateLimitOptionsCommand

        assert "rate" in RateLimitOptionsCommand().description.lower()

    def test_get_help(self) -> None:
        from claude_code.commands.rate_limit_options import RateLimitOptionsCommand

        help_text = RateLimitOptionsCommand().get_help()
        assert "rate" in help_text.lower()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """execute returns JSX node."""
        from claude_code.commands.rate_limit_options import RateLimitOptionsCommand

        cmd = RateLimitOptionsCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None


# =============================================================================
# RemoteEnvCommand tests
# =============================================================================
class TestRemoteEnvCommand:
    """Tests for RemoteEnvCommand."""

    def test_name(self) -> None:
        from claude_code.commands.remote_env import RemoteEnvCommand

        assert RemoteEnvCommand().name == "remote-env"

    def test_description(self) -> None:
        from claude_code.commands.remote_env import RemoteEnvCommand

        assert "remote" in RemoteEnvCommand().description.lower()

    def test_source(self) -> None:
        from claude_code.commands.remote_env import RemoteEnvCommand

        assert RemoteEnvCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.remote_env import RemoteEnvCommand

        assert "/remote-env" in RemoteEnvCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """execute returns JSX node."""
        from claude_code.commands.remote_env import RemoteEnvCommand

        cmd = RemoteEnvCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None


# =============================================================================
# RemoteSetupCommand tests
# =============================================================================
class TestRemoteSetupCommand:
    """Tests for RemoteSetupCommand."""

    def test_name(self) -> None:
        from claude_code.commands.remote_setup import RemoteSetupCommand

        assert RemoteSetupCommand().name == "remote-setup"

    def test_description(self) -> None:
        from claude_code.commands.remote_setup import RemoteSetupCommand

        assert "setup" in RemoteSetupCommand().description.lower() or "web" in RemoteSetupCommand().description.lower()

    def test_source(self) -> None:
        from claude_code.commands.remote_setup import RemoteSetupCommand

        assert RemoteSetupCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.remote_setup import RemoteSetupCommand

        assert "/remote-setup" in RemoteSetupCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """execute returns JSX node."""
        from claude_code.commands.remote_setup import RemoteSetupCommand

        cmd = RemoteSetupCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None


# =============================================================================
# TagCommand tests
# =============================================================================
class TestTagCommand:
    """Tests for TagCommand."""

    def test_name(self) -> None:
        from claude_code.commands.tag import TagCommand

        assert TagCommand().name == "tag"

    def test_description(self) -> None:
        from claude_code.commands.tag import TagCommand

        assert "tag" in TagCommand().description.lower()

    def test_argument_hint(self) -> None:
        from claude_code.commands.tag import TagCommand

        assert "<tag-name>" in TagCommand().argument_hint

    def test_source(self) -> None:
        from claude_code.commands.tag import TagCommand

        assert TagCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.tag import TagCommand

        assert "/tag" in TagCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_with_no_args_returns_help(self) -> None:
        """execute without args returns usage message."""
        from claude_code.commands.tag import TagCommand

        cmd = TagCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert "tag" in result.value.lower()

    @pytest.mark.asyncio
    async def test_execute_with_tag_name(self) -> None:
        """execute with tag name returns message."""
        from claude_code.commands.tag import TagCommand

        cmd = TagCommand()
        repl_state = MagicMock()
        repl_state.session = MagicMock()
        repl_state.session.session_id = "sess-123"

        with patch.object(cmd, "_save_tag") as mock_save:
            mock_save.return_value = True
            result = await cmd.execute("bugfix", {"_repl_state": repl_state})

        assert result.type == "text"

    @pytest.mark.asyncio
    async def test_execute_with_help_arg(self) -> None:
        """execute with --help returns help message."""
        from claude_code.commands.tag import TagCommand

        cmd = TagCommand()
        result = await cmd.execute("--help", {})

        assert result.type == "text"


# =============================================================================
# SandboxToggleCommand tests
# =============================================================================
class TestSandboxToggleCommand:
    """Tests for SandboxToggleCommand."""

    def test_name(self) -> None:
        from claude_code.commands.sandbox_toggle import SandboxToggleCommand

        assert SandboxToggleCommand().name == "sandbox"

    def test_description(self) -> None:
        from claude_code.commands.sandbox_toggle import SandboxToggleCommand

        desc = SandboxToggleCommand().description
        assert "sandbox" in desc.lower()

    def test_argument_hint(self) -> None:
        from claude_code.commands.sandbox_toggle import SandboxToggleCommand

        hint = SandboxToggleCommand().argument_hint
        assert hint is not None
        assert "exclude" in hint

    def test_source(self) -> None:
        from claude_code.commands.sandbox_toggle import SandboxToggleCommand

        assert SandboxToggleCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.sandbox_toggle import SandboxToggleCommand

        assert "/sandbox" in SandboxToggleCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_status(self) -> None:
        """execute returns sandbox status."""
        from claude_code.commands.sandbox_toggle import SandboxToggleCommand

        cmd = SandboxToggleCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert "sandbox" in result.value.lower()


# =============================================================================
# TerminalSetupCommand tests
# =============================================================================
class TestTerminalSetupCommand:
    """Tests for TerminalSetupCommand."""

    def test_name(self) -> None:
        from claude_code.commands.terminal_setup import TerminalSetupCommand

        assert TerminalSetupCommand().name == "terminal-setup"

    def test_description(self) -> None:
        from claude_code.commands.terminal_setup import TerminalSetupCommand

        desc = TerminalSetupCommand().description
        assert "terminal" in desc.lower() or "key" in desc.lower()

    def test_source(self) -> None:
        from claude_code.commands.terminal_setup import TerminalSetupCommand

        assert TerminalSetupCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.terminal_setup import TerminalSetupCommand

        assert "/terminal-setup" in TerminalSetupCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_setup_info(self) -> None:
        """execute returns setup information."""
        from claude_code.commands.terminal_setup import TerminalSetupCommand

        cmd = TerminalSetupCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert len(result.value) > 0


# =============================================================================
# ExtraUsageCommand tests
# =============================================================================
class TestExtraUsageCommand:
    """Tests for ExtraUsageCommand."""

    def test_name(self) -> None:
        from claude_code.commands.extra_usage import ExtraUsageCommand

        assert ExtraUsageCommand().name == "extra-usage"

    def test_description(self) -> None:
        from claude_code.commands.extra_usage import ExtraUsageCommand

        assert "extra" in ExtraUsageCommand().description.lower()
        assert "usage" in ExtraUsageCommand().description.lower()

    def test_source(self) -> None:
        from claude_code.commands.extra_usage import ExtraUsageCommand

        assert ExtraUsageCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.extra_usage import ExtraUsageCommand

        assert "/extra-usage" in ExtraUsageCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_message(self) -> None:
        """execute returns a message about extra usage."""
        from claude_code.commands.extra_usage import ExtraUsageCommand

        cmd = ExtraUsageCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert len(result.value) > 0


# =============================================================================
# ChromeCommand tests
# =============================================================================
class TestChromeCommand:
    """Tests for ChromeCommand."""

    def test_name(self) -> None:
        from claude_code.commands.chrome import ChromeCommand

        assert ChromeCommand().name == "chrome"

    def test_description(self) -> None:
        from claude_code.commands.chrome import ChromeCommand

        desc = ChromeCommand().description
        assert "chrome" in desc.lower()

    def test_source(self) -> None:
        from claude_code.commands.chrome import ChromeCommand

        assert ChromeCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.chrome import ChromeCommand

        assert "/chrome" in ChromeCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_message(self) -> None:
        """execute returns chrome info."""
        from claude_code.commands.chrome import ChromeCommand

        cmd = ChromeCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert len(result.value) > 0


# =============================================================================
# MobileCommand tests
# =============================================================================
class TestMobileCommand:
    """Tests for MobileCommand."""

    def test_name(self) -> None:
        from claude_code.commands.mobile import MobileCommand

        assert MobileCommand().name == "mobile"

    def test_aliases(self) -> None:
        from claude_code.commands.mobile import MobileCommand

        cmd = MobileCommand()
        assert "ios" in cmd.aliases
        assert "android" in cmd.aliases

    def test_description(self) -> None:
        from claude_code.commands.mobile import MobileCommand

        assert "mobile" in MobileCommand().description.lower() or "app" in MobileCommand().description.lower()

    def test_source(self) -> None:
        from claude_code.commands.mobile import MobileCommand

        assert MobileCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.mobile import MobileCommand

        assert "/mobile" in MobileCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_qr_info(self) -> None:
        """execute returns mobile app info."""
        from claude_code.commands.mobile import MobileCommand

        cmd = MobileCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert len(result.value) > 0


# =============================================================================
# DesktopCommand tests
# =============================================================================
class TestDesktopCommand:
    """Tests for DesktopCommand."""

    def test_name(self) -> None:
        from claude_code.commands.desktop import DesktopCommand

        assert DesktopCommand().name == "desktop"

    def test_aliases(self) -> None:
        from claude_code.commands.desktop import DesktopCommand

        cmd = DesktopCommand()
        assert "app" in cmd.aliases

    def test_description(self) -> None:
        from claude_code.commands.desktop import DesktopCommand

        assert "desktop" in DesktopCommand().description.lower() or "claude" in DesktopCommand().description.lower()

    def test_source(self) -> None:
        from claude_code.commands.desktop import DesktopCommand

        assert DesktopCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.desktop import DesktopCommand

        assert "/desktop" in DesktopCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_message(self) -> None:
        """execute returns desktop info."""
        from claude_code.commands.desktop import DesktopCommand

        cmd = DesktopCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert len(result.value) > 0


# =============================================================================
# InstallGithubAppCommand tests
# =============================================================================
class TestInstallGithubAppCommand:
    """Tests for InstallGithubAppCommand."""

    def test_name(self) -> None:
        from claude_code.commands.install_github_app import InstallGithubAppCommand

        assert InstallGithubAppCommand().name == "install-github-app"

    def test_description(self) -> None:
        from claude_code.commands.install_github_app import InstallGithubAppCommand

        desc = InstallGithubAppCommand().description
        assert "github" in desc.lower()

    def test_source(self) -> None:
        from claude_code.commands.install_github_app import InstallGithubAppCommand

        assert InstallGithubAppCommand().source == "builtin"

    def test_get_help(self) -> None:
        from claude_code.commands.install_github_app import InstallGithubAppCommand

        assert "/install-github-app" in InstallGithubAppCommand().get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_message(self) -> None:
        """execute returns GitHub App install info."""
        from claude_code.commands.install_github_app import InstallGithubAppCommand

        cmd = InstallGithubAppCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert len(result.value) > 0
