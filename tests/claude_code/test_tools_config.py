"""
Tests for ConfigTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_code.tools.config import ConfigTool


@pytest.fixture
def config_tool() -> ConfigTool:
    return ConfigTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    return ctx


class TestConfigTool:
    """Tests for ConfigTool."""

    def test_name(self, config_tool: ConfigTool) -> None:
        assert config_tool.name == "Config"

    def test_aliases(self, config_tool: ConfigTool) -> None:
        assert config_tool.aliases is None

    def test_search_hint(self, config_tool: ConfigTool) -> None:
        assert "setting" in config_tool.search_hint.lower()

    def test_should_defer(self, config_tool: ConfigTool) -> None:
        assert config_tool.should_defer is True

    def test_always_load(self, config_tool: ConfigTool) -> None:
        assert config_tool.always_load is False

    def test_max_result_size_chars(self, config_tool: ConfigTool) -> None:
        assert config_tool.max_result_size_chars == 100_000

    def test_strict(self, config_tool: ConfigTool) -> None:
        assert config_tool.strict is False

    def test_description_text(self, config_tool: ConfigTool) -> None:
        assert "config" in config_tool.description_text.lower()
        assert "setting" in config_tool.description_text.lower()

    def test_prompt_text(self, config_tool: ConfigTool) -> None:
        assert "setting" in config_tool.prompt_text.lower()

    def test_input_schema(self, config_tool: ConfigTool) -> None:
        schema = config_tool.input_schema
        assert schema["type"] == "object"
        assert "setting" in schema["required"]
        props = schema["properties"]
        assert "setting" in props
        assert "value" in props

    def test_output_schema(self, config_tool: ConfigTool) -> None:
        schema = config_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "success" in props
        assert "operation" in props
        assert "setting" in props
        assert "value" in props
        assert "error" in props

    def test_user_facing_name(self, config_tool: ConfigTool) -> None:
        assert config_tool.user_facing_name({}) == "Config"

    def test_is_enabled(self, config_tool: ConfigTool) -> None:
        assert config_tool.is_enabled() is True

    def test_is_concurrency_safe(self, config_tool: ConfigTool) -> None:
        assert config_tool.is_concurrency_safe({}) is True

    def test_is_read_only_get(self, config_tool: ConfigTool) -> None:
        # Without value, it's a read operation
        assert config_tool.is_read_only({"setting": "theme"}) is True

    def test_is_read_only_set(self, config_tool: ConfigTool) -> None:
        # With value, it's a write operation
        assert config_tool.is_read_only({"setting": "theme", "value": "dark"}) is False

    def test_to_auto_classifier_input_get(self, config_tool: ConfigTool) -> None:
        result = config_tool.to_auto_classifier_input({"setting": "theme"})
        assert result == "theme"

    def test_to_auto_classifier_input_set(self, config_tool: ConfigTool) -> None:
        result = config_tool.to_auto_classifier_input({
            "setting": "theme",
            "value": "dark",
        })
        assert "theme" in result
        assert "dark" in result

    @pytest.mark.asyncio
    async def test_validate_input_not_needed(
        self, config_tool: ConfigTool, mock_context: MagicMock
    ) -> None:
        # Config tool uses schema validation for required fields
        result = await config_tool.validate_input(
            {"setting": "theme", "value": "dark"},
            mock_context,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_get_unknown_setting(
        self, config_tool: ConfigTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claude_code.tools.config.is_supported",
            return_value=False,
        ):
            result = await config_tool.call(
                {"setting": "unknown-setting"},
                mock_context,
                AsyncMock(),
                None,
            )

        assert result["data"]["success"] is False
        assert "Unknown setting" in result["data"]["error"]
        assert "unknown-setting" in result["data"]["error"]

    @pytest.mark.asyncio
    async def test_call_get_valid_setting(
        self, config_tool: ConfigTool, mock_context: MagicMock
    ) -> None:
        mock_config = MagicMock()
        mock_config.source = "global"
        mock_config.format_on_read = None

        with patch(
            "claude_code.tools.config.is_supported",
            return_value=True,
        ):
            with patch(
                "claude_code.tools.config.get_config",
                return_value=mock_config,
            ):
                with patch(
                    "claude_code.tools.config.get_path",
                    return_value=["theme"],
                ):
                    with patch(
                        "claude_code.tools.config.get_global_config",
                        return_value={"theme": "dark"},
                    ):
                        result = await config_tool.call(
                            {"setting": "theme"},
                            mock_context,
                            AsyncMock(),
                            None,
                        )

        assert result["data"]["success"] is True
        assert result["data"]["operation"] == "get"
        assert result["data"]["setting"] == "theme"
        assert result["data"]["value"] == "dark"

    @pytest.mark.asyncio
    async def test_call_get_with_format_on_read(
        self, config_tool: ConfigTool, mock_context: MagicMock
    ) -> None:
        def format_fn(v):
            return f"formatted-{v}"

        mock_config = MagicMock()
        mock_config.source = "global"
        mock_config.format_on_read = format_fn

        with patch(
            "claude_code.tools.config.is_supported",
            return_value=True,
        ):
            with patch(
                "claude_code.tools.config.get_config",
                return_value=mock_config,
            ):
                with patch(
                    "claude_code.tools.config.get_path",
                    return_value=["model"],
                ):
                    with patch(
                        "claude_code.tools.config.get_global_config",
                        return_value={"model": "sonnet"},
                    ):
                        result = await config_tool.call(
                            {"setting": "model"},
                            mock_context,
                            AsyncMock(),
                            None,
                        )

        assert result["data"]["success"] is True
        assert result["data"]["value"] == "formatted-sonnet"

    @pytest.mark.asyncio
    async def test_call_set_unknown_setting(
        self, config_tool: ConfigTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claude_code.tools.config.is_supported",
            return_value=False,
        ):
            result = await config_tool.call(
                {"setting": "unknown-setting", "value": "somevalue"},
                mock_context,
                AsyncMock(),
                None,
            )

        assert result["data"]["success"] is False
        assert "Unknown setting" in result["data"]["error"]

    @pytest.mark.asyncio
    async def test_call_set_valid_setting(
        self, config_tool: ConfigTool, mock_context: MagicMock
    ) -> None:
        mock_config = MagicMock()
        mock_config.source = "global"
        mock_config.type = "string"
        mock_config.validate_on_write = None
        mock_config.app_state_key = None

        with patch(
            "claude_code.tools.config.is_supported",
            return_value=True,
        ):
            with patch(
                "claude_code.tools.config.get_config",
                return_value=mock_config,
            ):
                with patch(
                    "claude_code.tools.config.get_path",
                    return_value=["theme"],
                ):
                    with patch(
                        "claude_code.tools.config.get_global_config",
                        return_value={"theme": "light"},
                    ):
                        with patch(
                            "claude_code.tools.config.save_global_config",
                        ):
                            result = await config_tool.call(
                                {"setting": "theme", "value": "dark"},
                                mock_context,
                                AsyncMock(),
                                None,
                            )

        assert result["data"]["success"] is True
        assert result["data"]["operation"] == "set"
        assert result["data"]["setting"] == "theme"
        assert result["data"]["previousValue"] == "light"
        assert result["data"]["newValue"] == "dark"

    @pytest.mark.asyncio
    async def test_call_set_boolean_coercion(
        self, config_tool: ConfigTool, mock_context: MagicMock
    ) -> None:
        mock_config = MagicMock()
        mock_config.source = "global"
        mock_config.type = "boolean"
        mock_config.validate_on_write = None
        mock_config.app_state_key = None

        with patch(
            "claude_code.tools.config.is_supported",
            return_value=True,
        ):
            with patch(
                "claude_code.tools.config.get_config",
                return_value=mock_config,
            ):
                with patch(
                    "claude_code.tools.config.get_path",
                    return_value=["verbose"],
                ):
                    with patch(
                        "claude_code.tools.config.get_global_config",
                        return_value={"verbose": False},
                    ):
                        with patch(
                            "claude_code.tools.config.save_global_config",
                        ):
                            result = await config_tool.call(
                                {"setting": "verbose", "value": "true"},
                                mock_context,
                                AsyncMock(),
                                None,
                            )

        assert result["data"]["success"] is True
        assert result["data"]["newValue"] is True

    @pytest.mark.asyncio
    async def test_call_set_boolean_invalid(
        self, config_tool: ConfigTool, mock_context: MagicMock
    ) -> None:
        mock_config = MagicMock()
        mock_config.source = "global"
        mock_config.type = "boolean"
        mock_config.validate_on_write = None
        mock_config.app_state_key = None

        with patch(
            "claude_code.tools.config.is_supported",
            return_value=True,
        ):
            with patch(
                "claude_code.tools.config.get_config",
                return_value=mock_config,
            ):
                with patch(
                    "claude_code.tools.config.get_path",
                    return_value=["verbose"],
                ):
                    with patch(
                        "claude_code.tools.config.get_global_config",
                        return_value={"verbose": False},
                    ):
                        result = await config_tool.call(
                            {"setting": "verbose", "value": "notaboolean"},
                            mock_context,
                            AsyncMock(),
                            None,
                        )

        assert result["data"]["success"] is False
        assert "true or false" in result["data"]["error"]

    def test_map_tool_result_get_success(self, config_tool: ConfigTool) -> None:
        content = {
            "success": True,
            "operation": "get",
            "setting": "theme",
            "value": "dark",
        }
        result = config_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert result["tool_use_id"] == "tool-use-1"
        assert result["type"] == "tool_result"
        assert "theme" in result["content"]
        assert "dark" in result["content"]

    def test_map_tool_result_set_success(self, config_tool: ConfigTool) -> None:
        content = {
            "success": True,
            "operation": "set",
            "setting": "theme",
            "previousValue": "light",
            "newValue": "dark",
        }
        result = config_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-2"
        )
        assert result["tool_use_id"] == "tool-use-2"
        assert result["type"] == "tool_result"
        assert "Set theme" in result["content"]
        assert "dark" in result["content"]

    def test_map_tool_result_error(self, config_tool: ConfigTool) -> None:
        content = {
            "success": False,
            "setting": "unknown",
            "error": "Unknown setting: unknown",
        }
        result = config_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-3"
        )
        assert result["tool_use_id"] == "tool-use-3"
        assert result["type"] == "tool_result"
        assert result.get("is_error", False) is True
        assert "Error" in result["content"]
        assert "Unknown setting" in result["content"]
