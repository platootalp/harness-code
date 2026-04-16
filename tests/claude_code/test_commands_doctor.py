"""
Tests for commands/doctor.py - Doctor command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.doctor import DoctorCommand
from claude_code.commands.base import CommandType


class TestDoctorCommand:
    """Tests for DoctorCommand."""

    def test_create(self) -> None:
        """Test creating DoctorCommand."""
        cmd = DoctorCommand()
        assert cmd.name == "doctor"
        assert cmd.description == "Diagnose and verify your Claude Code installation and settings"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.supports_non_interactive is True

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = DoctorCommand()
        assert "/doctor" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = DoctorCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "Doctor"
        assert "onDone" in result.node["props"]
