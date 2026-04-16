"""
ConfigTool - Get or set Claude Code configuration settings.

Migrated from src/tools/ConfigTool/ConfigTool.ts.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name
# =============================================================================

CONFIG_TOOL_NAME = "Config"

# =============================================================================
# Config helpers (imported from utils/config, mocked in tests)
# =============================================================================


def is_supported(setting: str) -> bool:
    """Check if a setting is supported."""
    from claude_code.utils.config import is_supported as _is_supported

    return bool(_is_supported(setting))


def get_config(setting: str) -> Any:
    """Get the config descriptor for a setting."""
    from claude_code.utils.config import get_config as _get_config

    return _get_config(setting)


def get_path(setting: str) -> list[str]:
    """Get the config path for a setting."""
    from claude_code.utils.config import get_path as _get_path

    return list(_get_path(setting))


def get_global_config() -> dict[str, Any]:
    """Get the global config dict."""
    from claude_code.utils.config import get_global_config as _get_global_config

    return dict(_get_global_config())


def save_global_config(updater: Any) -> None:
    """Save the global config after applying an updater function."""
    from claude_code.utils.config import save_global_config as _save_global_config

    _save_global_config(updater)


# =============================================================================
# ConfigTool
# =============================================================================


class ConfigTool:
    """Tool for reading and writing Claude Code configuration settings.

    Supports getting and setting configuration values like theme, model,
    permissions, and other application settings.
    """

    name: str = CONFIG_TOOL_NAME
    aliases: list[str] | None = None
    search_hint: str | None = "get or set Claude Code settings (theme, model)"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    @property
    def description_text(self) -> str:
        return (
            "A tool for reading and modifying Claude Code configuration settings. "
            "Use this to view or change settings like theme, model, and permissions."
        )

    @property
    def prompt_text(self) -> str:
        return (
            "The Config tool lets you read and write Claude Code settings. "
            "Omit the value parameter to read a setting. "
            "Provide a value to update it. "
            "Supported settings include theme, model, permissions.defaultMode, and more."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "setting": {
                    "type": "string",
                    "description": (
                        'The setting key (e.g., "theme", "model", "permissions.defaultMode")'
                    ),
                },
                "value": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "boolean"},
                        {"type": "number"},
                    ],
                    "description": "The new value. Omit to get current value.",
                },
            },
            "required": ["setting"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "operation": {"type": "string", "enum": ["get", "set"]},
                "setting": {"type": "string"},
                "value": {"type": "unknown"},
                "previousValue": {"type": "unknown"},
                "newValue": {"type": "unknown"},
                "error": {"type": "string"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "Config"

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        """Returns True for GET operations (no value), False for SET operations."""
        return input.get("value") is None

    def to_auto_classifier_input(self, input: Any) -> str:
        setting = str(input.get("setting", ""))
        value = input.get("value")
        if value is None:
            return setting
        return f"{setting} = {value}"

    async def validate_input(
        self, input: Any, context: Any
    ) -> tuple[bool, str, int] | bool:
        """Config tool uses schema validation for required fields."""
        return True

    async def call(
        self,
        args: dict[str, Any],
        context: Any,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> dict[str, Any]:
        setting = args.get("setting", "")
        value = args.get("value")

        # 1. Check if setting is supported
        if not is_supported(setting):
            return {
                "data": {
                    "success": False,
                    "error": f'Unknown setting: "{setting}"',
                },
            }

        config = get_config(setting)
        path = get_path(setting)

        # 2. GET operation
        if value is None:
            global_config = get_global_config()
            current_value = _get_value_from_path(global_config, path)

            # Apply format_on_read if present
            display_value = current_value
            if config.format_on_read is not None:
                display_value = config.format_on_read(current_value)

            return {
                "data": {
                    "success": True,
                    "operation": "get",
                    "setting": setting,
                    "value": display_value,
                },
            }

        # 3. SET operation
        final_value: Any = value

        # Coerce and validate boolean values
        if config.type == "boolean":
            if isinstance(value, str):
                lower = value.lower().strip()
                if lower == "true":
                    final_value = True
                elif lower == "false":
                    final_value = False
            if not isinstance(final_value, bool):
                return {
                    "data": {
                        "success": False,
                        "operation": "set",
                        "setting": setting,
                        "error": f"{setting} requires true or false.",
                    },
                }

        # Async validation
        if config.validate_on_write is not None:
            result = await config.validate_on_write(final_value)
            if not result.valid:
                return {
                    "data": {
                        "success": False,
                        "operation": "set",
                        "setting": setting,
                        "error": result.error,
                    },
                }

        # Get previous value
        global_config = get_global_config()
        previous_value = _get_value_from_path(global_config, path)

        # Write to storage
        try:
            if config.source == "global":
                key = path[0]
                if not key:
                    return {
                        "data": {
                            "success": False,
                            "operation": "set",
                            "setting": setting,
                            "error": "Invalid setting path",
                        },
                    }

                def _updater(prev: dict[str, Any]) -> dict[str, Any]:
                    if prev.get(key) == final_value:
                        return prev
                    return {**prev, key: final_value}

                save_global_config(_updater)
            else:
                # For settings source, build nested object
                update = _build_nested_object(path, final_value)
                # Use context.set_app_state for settings-based configs
                if context.set_app_state:
                    def _settings_updater(prev: Any) -> Any:
                        if prev is None:
                            return None
                        return {**vars(prev), **update}

                    context.set_app_state(_settings_updater)

            # Sync to AppState if needed
            if config.app_state_key is not None and context.set_app_state:
                app_key = config.app_state_key

                def _appstate_updater(prev: Any) -> Any:
                    if prev is None:
                        return None
                    prev_dict = {**vars(prev)} if hasattr(prev, "__dict__") else dict(prev)
                    if prev_dict.get(app_key) == final_value:
                        return prev
                    return type(prev)(**{**prev_dict, app_key: final_value}) if hasattr(prev, "__dict__") else {**prev_dict, app_key: final_value}

                context.set_app_state(_appstate_updater)

            return {
                "data": {
                    "success": True,
                    "operation": "set",
                    "setting": setting,
                    "previousValue": previous_value,
                    "newValue": final_value,
                },
            }
        except Exception as e:
            return {
                "data": {
                    "success": False,
                    "operation": "set",
                    "setting": setting,
                    "error": str(e),
                },
            }

    def map_tool_result_to_tool_result_block_param(
        self, content: dict[str, Any], tool_use_id: str
    ) -> dict[str, Any]:
        if content.get("success"):
            if content.get("operation") == "get":
                return {
                    "tool_use_id": tool_use_id,
                    "type": "tool_result",
                    "content": f'{content["setting"]} = {json.dumps(content.get("value"))}',
                }
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": f'Set {content["setting"]} to {json.dumps(content.get("newValue"))}',
            }
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": f'Error: {content.get("error", "Unknown error")}',
            "is_error": True,
        }


# =============================================================================
# Helper Functions
# =============================================================================


def _get_value_from_path(config: dict[str, Any], path: list[str]) -> Any:
    """Get a value from a config dict following the given path."""
    if not path:
        return None
    key = path[0]
    if key not in config:
        return None
    current = config[key]
    for part in path[1:]:
        if current is None:
            return None
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _build_nested_object(path: list[str], value: Any) -> dict[str, Any]:
    """Build a nested dict from a path and value."""
    if not path:
        return {}
    key = path[0]
    if len(path) == 1:
        return {key: value}
    return {key: _build_nested_object(path[1:], value)}
