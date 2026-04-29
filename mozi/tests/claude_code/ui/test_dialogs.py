"""Tests for UI dialog components."""

from __future__ import annotations

import pytest

from claude_code.ui.dialogs import (
    AgentMemoryScope,
    ConfirmDialog,
    ConfirmDialogResult,
    CostThresholdDialog,
    CostThresholdDialogResult,
    DialogColor,
    DialogResult,
    DialogStyle,
    InvalidSettingsDialog,
    InvalidSettingsDialogResult,
    PermissionDialog,
    PermissionRequest,
    SelectOption,
    SelectionDialog,
    SelectionDialogResult,
    SnapshotUpdateDialog,
    SnapshotUpdateDialogResult,
    TrustDialog,
    TrustDialogDangerousItem,
    TrustDialogResult,
    ValidationError,
    format_validation_errors,
)


class TestValidationError:
    """Tests for ValidationError."""

    def test_creation(self) -> None:
        """ValidationError can be created."""
        err = ValidationError(path="name", message="Required field")
        assert err.path == "name"
        assert err.message == "Required field"
        assert err.file is None
        assert err.expected is None
        assert err.invalid_value is None

    def test_to_dict(self) -> None:
        """to_dict returns correct structure."""
        err = ValidationError(
            path="settings.permissions[0]",
            message="Invalid tool name",
            file="settings.json",
            expected="string",
            invalid_value=123,
        )
        d = err.to_dict()
        assert d["path"] == "settings.permissions[0]"
        assert d["message"] == "Invalid tool name"
        assert d["file"] == "settings.json"
        assert d["expected"] == "string"
        assert d["invalidValue"] == 123

    def test_from_dict(self) -> None:
        """from_dict creates correct instance."""
        d = {
            "path": "test",
            "message": "Error",
            "file": "test.json",
            "expected": "string",
            "invalidValue": "bad",
        }
        err = ValidationError.from_dict(d)
        assert err.path == "test"
        assert err.message == "Error"
        assert err.file == "test.json"
        assert err.expected == "string"
        assert err.invalid_value == "bad"


class TestDialogResult:
    """Tests for DialogResult."""

    def test_base_class(self) -> None:
        """DialogResult can be instantiated."""
        result = DialogResult()
        assert isinstance(result, DialogResult)


class TestConfirmDialogResult:
    """Tests for ConfirmDialogResult."""

    def test_default_confirmed(self) -> None:
        """Default is not confirmed."""
        result = ConfirmDialogResult()
        assert result.confirmed is False

    def test_confirmed(self) -> None:
        """Can set confirmed."""
        result = ConfirmDialogResult(confirmed=True)
        assert result.confirmed is True


class TestSelectionDialogResult:
    """Tests for SelectionDialogResult."""

    def test_default_selected(self) -> None:
        """Default selected is None."""
        result = SelectionDialogResult()
        assert result.selected is None

    def test_selected(self) -> None:
        """Can set selected value."""
        result = SelectionDialogResult(selected="option1")
        assert result.selected == "option1"


class TestConfirmDialog:
    """Tests for ConfirmDialog."""

    def test_creation(self) -> None:
        """ConfirmDialog can be created."""
        dialog = ConfirmDialog(
            title="Confirm Delete",
            message="Are you sure?",
        )
        assert dialog.title == "Confirm Delete"
        assert dialog.message == "Are you sure?"
        assert dialog.yes_label == "Yes"
        assert dialog.no_label == "No"
        assert dialog.default_cancel is True

    def test_custom_labels(self) -> None:
        """Custom labels work."""
        dialog = ConfirmDialog(
            title="Continue?",
            message="Proceed?",
            yes_label="OK",
            no_label="Cancel",
        )
        assert dialog.yes_label == "OK"
        assert dialog.no_label == "Cancel"

    def test_open_close(self) -> None:
        """Open and close work."""
        dialog = ConfirmDialog(title="Test", message="Test?")
        assert dialog.is_open() is False
        dialog.open()
        assert dialog.is_open() is True
        dialog.close()
        assert dialog.is_open() is False


class TestSelectionDialog:
    """Tests for SelectionDialog."""

    def test_creation(self) -> None:
        """SelectionDialog can be created."""
        options = [
            SelectOption(label="Option 1", value="opt1"),
            SelectOption(label="Option 2", value="opt2"),
        ]
        dialog = SelectionDialog(title="Choose", options=options)
        assert dialog.title == "Choose"
        assert len(dialog.options) == 2
        assert dialog.allow_cancel is True

    def test_options_with_descriptions(self) -> None:
        """Options can have descriptions."""
        options = [
            SelectOption(label="A", value="a", description="First option"),
        ]
        dialog = SelectionDialog(title="Test", options=options)
        assert dialog.options[0].description == "First option"


class TestInvalidSettingsDialog:
    """Tests for InvalidSettingsDialog."""

    def test_creation(self) -> None:
        """InvalidSettingsDialog can be created."""
        errors = [
            ValidationError(path="test", message="Error"),
        ]
        dialog = InvalidSettingsDialog(settings_errors=errors)
        assert len(dialog.settings_errors) == 1
        assert dialog.title == "Settings Error"

    def test_handle_continue(self) -> None:
        """handle_continue completes with correct result."""
        errors = [ValidationError(path="test", message="Error")]
        callback_called: list[DialogResult] = []

        def on_done(result: DialogResult) -> None:
            callback_called.append(result)

        dialog = InvalidSettingsDialog(settings_errors=errors)
        dialog.on_done(on_done)
        dialog.handle_continue()
        assert len(callback_called) == 1
        assert isinstance(callback_called[0], InvalidSettingsDialogResult)
        assert callback_called[0].continue_without_settings is True


class TestCostThresholdDialog:
    """Tests for CostThresholdDialog."""

    def test_creation(self) -> None:
        """CostThresholdDialog can be created."""
        dialog = CostThresholdDialog(amount="$10")
        assert "$10" in dialog.title
        assert dialog.amount == "$10"


class TestTrustDialog:
    """Tests for TrustDialog."""

    def test_creation(self) -> None:
        """TrustDialog can be created."""
        dialog = TrustDialog(
            commands=["rm -rf /"],
            mcp_servers=["server1"],
        )
        assert len(dialog.commands) == 1
        assert len(dialog.mcp_servers) == 1
        assert dialog.title == "Trust & Safety"

    def test_dangerous_items(self) -> None:
        """Dangerous items can be set."""
        item = TrustDialogDangerousItem(
            category="Dangerous env vars",
            sources=["settings.json"],
        )
        dialog = TrustDialog(dangerous_env_vars=[item])
        assert len(dialog.dangerous_env_vars) == 1
        assert dialog.dangerous_env_vars[0].category == "Dangerous env vars"


class TestSnapshotUpdateDialog:
    """Tests for SnapshotUpdateDialog."""

    def test_creation(self) -> None:
        """SnapshotUpdateDialog can be created."""
        dialog = SnapshotUpdateDialog(
            agent_type="researcher",
            scope=AgentMemoryScope.PROJECT,
            snapshot_timestamp="2024-01-01T00:00:00Z",
        )
        assert dialog.agent_type == "researcher"
        assert dialog.scope == AgentMemoryScope.PROJECT
        assert "researcher" in dialog.title

    def test_handle_merge(self) -> None:
        """handle_merge completes with correct result."""
        dialog = SnapshotUpdateDialog(
            agent_type="test",
            scope=AgentMemoryScope.LOCAL,
            snapshot_timestamp="2024-01-01T00:00:00Z",
        )
        results: list[DialogResult] = []
        dialog.on_done(lambda r: results.append(r))
        dialog.handle_merge()
        assert len(results) == 1
        assert isinstance(results[0], SnapshotUpdateDialogResult)
        assert results[0].action == "merge"


class TestPermissionDialog:
    """Tests for PermissionDialog."""

    def test_creation(self) -> None:
        """PermissionDialog can be created."""
        request = PermissionRequest(
            tool_name="Bash",
            command="rm -rf /",
            risk_level="HIGH",
        )
        dialog = PermissionDialog(request=request)
        assert dialog.request.tool_name == "Bash"
        assert dialog.request.risk_level == "HIGH"


class TestFormatValidationErrors:
    """Tests for format_validation_errors."""

    def test_empty_list(self) -> None:
        """Empty list returns empty string."""
        result = format_validation_errors([])
        assert result == ""

    def test_single_error(self) -> None:
        """Single error formats correctly."""
        errors = [
            ValidationError(path="name", message="Required"),
        ]
        result = format_validation_errors(errors)
        assert "name" in result
        assert "Required" in result

    def test_multiple_errors(self) -> None:
        """Multiple errors format correctly."""
        errors = [
            ValidationError(path="name", message="Required", file="settings.json"),
            ValidationError(
                path="port",
                message="Must be a number",
                expected="integer",
                invalid_value="abc",
            ),
        ]
        result = format_validation_errors(errors)
        assert "settings.json" in result
        assert "Required" in result
        assert "Must be a number" in result
        assert "integer" in result


class TestDialogStyle:
    """Tests for DialogStyle."""

    def test_border_color_for(self) -> None:
        """border_color_for returns correct colors."""
        assert DialogStyle.border_color_for(DialogColor.PERMISSION) == "cyan"
        assert DialogStyle.border_color_for(DialogColor.WARNING) == "yellow"
        assert DialogStyle.border_color_for(DialogColor.ERROR) == "red"
        assert DialogStyle.border_color_for(DialogColor.SUCCESS) == "green"
        assert DialogStyle.border_color_for(DialogColor.INFO) == "blue"
