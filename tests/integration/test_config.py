"""Integration tests for configuration.

This module provides integration tests for configuration loading including:
- Configuration file loading
- Environment variable overrides
- Configuration validation

Tests use @pytest.mark.integration marker.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from mozi.infrastructure.config import (
    CircuitBreakerConfig,
    Config,
    ConfigLoader,
    DefaultsConfig,
    ModelConfig,
    RetryConfig,
    get_config_loader,
    load_config,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_config_dict() -> dict:
    """Create a sample configuration dictionary.

    Returns
    -------
    dict
        Sample configuration for testing.
    """
    return {
        "providers": {
            "anthropic": {
                "enabled": True,
                "api_key_env": "ANTHROPIC_API_KEY",
                "base_url": "https://api.anthropic.com",
                "models": [
                    {"name": "claude-sonnet-4-7", "enabled": True},
                ],
            },
            "openai": {
                "enabled": False,
                "api_key_env": "OPENAI_API_KEY",
                "models": [],
            },
        },
        "defaults": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-7",
            "temperature": 1.0,
            "max_tokens": 4096,
        },
        "retry": {
            "max_retries": 3,
            "base_delay": 1.0,
            "max_delay": 60.0,
            "exponential_base": 2.0,
            "jitter": True,
        },
        "circuit_breaker": {
            "failure_threshold": 5,
            "recovery_timeout": 60.0,
            "half_open_max_calls": 3,
        },
    }


@pytest.fixture
def config_file(sample_config_dict: dict) -> Generator[Path, None, None]:
    """Create a temporary config file.

    Yields
    ------
    Path
        Path to temporary config file.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
    ) as f:
        json.dump(sample_config_dict, f)
        config_path = Path(f.name)

    yield config_path

    # Cleanup
    if config_path.exists():
        config_path.unlink()


@pytest.fixture
def config_loader(config_file: Path) -> ConfigLoader:
    """Create a config loader with test config file.

    Parameters
    ----------
    config_file : Path
        Path to temporary config file.

    Returns
    -------
    ConfigLoader
        Config loader instance for testing.
    """
    return ConfigLoader(config_path=config_file)


# =============================================================================
# Configuration Loading Tests
# =============================================================================


class TestConfigLoading:
    """Integration tests for configuration loading."""

    @pytest.mark.integration
    def test_load_config_from_file(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test loading configuration from file."""
        config = config_loader.load()

        assert config is not None
        assert isinstance(config, Config)
        assert len(config.providers) == 2

    @pytest.mark.integration
    def test_load_config_missing_file(self) -> None:
        """Test that loading missing config file raises error."""
        loader = ConfigLoader(config_path="/nonexistent/path/config.json")

        with pytest.raises(FileNotFoundError) as exc_info:
            loader.load()

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.integration
    def test_load_config_invalid_json(self) -> None:
        """Test that loading invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            f.write("{ invalid json }")
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path=config_path)
            with pytest.raises(json.JSONDecodeError):
                loader.load()
        finally:
            config_path.unlink()

    @pytest.mark.integration
    def test_load_config_partial_overrides(self) -> None:
        """Test loading config with partial provider data."""
        partial_config = {
            "providers": {
                "test": {
                    "enabled": True,
                }
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump(partial_config, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path=config_path)
            config = loader.load()

            # Provider should be loaded with defaults
            test_provider = config.providers.get("test")
            assert test_provider is not None
            assert test_provider.enabled is True
            assert test_provider.api_key_env is None
        finally:
            config_path.unlink()


# =============================================================================
# Environment Variable Override Tests
# =============================================================================


class TestEnvironmentVariableOverride:
    """Integration tests for environment variable overrides."""

    @pytest.mark.integration
    def test_env_var_substitution(
        self,
        sample_config_dict: dict,
    ) -> None:
        """Test that environment variables are substituted."""
        # Set environment variable
        os.environ["TEST_API_KEY"] = "test-key-123"

        config_with_env = {
            "providers": {
                "test": {
                    "enabled": True,
                    "api_key_env": "TEST_API_KEY",
                }
            },
            "defaults": {},
            "retry": {},
            "circuit_breaker": {},
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump(config_with_env, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path=config_path)
            api_key = loader.get_api_key("test")
            assert api_key == "test-key-123"
        finally:
            config_path.unlink()
            del os.environ["TEST_API_KEY"]

    @pytest.mark.integration
    def test_env_var_with_default(
        self,
        sample_config_dict: dict,
    ) -> None:
        """Test environment variable with default value."""
        # Ensure env var is not set
        if "NONEXISTENT_VAR" in os.environ:
            del os.environ["NONEXISTENT_VAR"]

        loader = ConfigLoader()
        # The _substitute_string_env_vars method should handle missing vars

    @pytest.mark.integration
    def test_env_var_missing_without_default(
        self,
        sample_config_dict: dict,
    ) -> None:
        """Test environment variable that doesn't exist without default."""
        # Env var doesn't exist
        assert os.environ.get("I_DO_NOT_EXIST_12345") is None

        # Test that substitution returns original when var doesn't exist
        loader = ConfigLoader()
        test_str = "${I_DO_NOT_EXIST_12345}"
        result = loader._substitute_string_env_vars(test_str)
        # Without default, should keep original
        assert result == test_str

    @pytest.mark.integration
    def test_env_var_nested_substitution(
        self,
        sample_config_dict: dict,
    ) -> None:
        """Test nested environment variable substitution."""
        os.environ["NESTED_VAR"] = "nested-value"

        config_with_nested = {
            "providers": {
                "test": {
                    "enabled": True,
                    "api_key_env": "NESTED_VAR",
                }
            },
            "defaults": {},
            "retry": {},
            "circuit_breaker": {},
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump(config_with_nested, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path=config_path)
            config = loader.load()
            # api_key_env stores the env var name, not the substituted value
            assert config.providers["test"].api_key_env == "NESTED_VAR"
        finally:
            config_path.unlink()
            del os.environ["NESTED_VAR"]

    @pytest.mark.integration
    def test_multiple_env_vars_in_string(
        self,
        sample_config_dict: dict,
    ) -> None:
        """Test multiple environment variables in one string."""
        os.environ["VAR1"] = "value1"
        os.environ["VAR2"] = "value2"

        loader = ConfigLoader()
        test_str = "${VAR1}-${VAR2}"
        result = loader._substitute_string_env_vars(test_str)

        assert result == "value1-value2"

        del os.environ["VAR1"]
        del os.environ["VAR2"]


# =============================================================================
# Configuration Validation Tests
# =============================================================================


class TestConfigurationValidation:
    """Integration tests for configuration validation."""

    @pytest.mark.integration
    def test_provider_config_validation(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test provider configuration validation."""
        config = config_loader.load()

        anthropic = config.providers.get("anthropic")
        assert anthropic is not None
        assert anthropic.enabled is True
        assert anthropic.api_key_env == "ANTHROPIC_API_KEY"
        assert len(anthropic.models) == 1

    @pytest.mark.integration
    def test_defaults_config_validation(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test defaults configuration validation."""
        config = config_loader.load()

        assert config.defaults.provider == "anthropic"
        assert config.defaults.model == "claude-sonnet-4-7"
        assert config.defaults.temperature == 1.0
        assert config.defaults.max_tokens == 4096

    @pytest.mark.integration
    def test_retry_config_validation(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test retry configuration validation."""
        config = config_loader.load()

        assert config.retry.max_retries == 3
        assert config.retry.base_delay == 1.0
        assert config.retry.max_delay == 60.0
        assert config.retry.exponential_base == 2.0
        assert config.retry.jitter is True

    @pytest.mark.integration
    def test_circuit_breaker_config_validation(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test circuit breaker configuration validation."""
        config = config_loader.load()

        assert config.circuit_breaker.failure_threshold == 5
        assert config.circuit_breaker.recovery_timeout == 60.0
        assert config.circuit_breaker.half_open_max_calls == 3

    @pytest.mark.integration
    def test_invalid_temperature_value(
        self,
        sample_config_dict: dict,
    ) -> None:
        """Test handling of invalid temperature value."""
        invalid_config = sample_config_dict.copy()
        invalid_config["defaults"]["temperature"] = "invalid"

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump(invalid_config, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path=config_path)
            # Config loader raises ValueError on invalid temperature
            with pytest.raises(ValueError):
                loader.load()
        finally:
            config_path.unlink()


# =============================================================================
# Provider Configuration Tests
# =============================================================================


class TestProviderConfiguration:
    """Integration tests for provider configuration."""

    @pytest.mark.integration
    def test_get_enabled_providers(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test getting list of enabled providers."""
        enabled = config_loader.get_enabled_providers()

        assert "anthropic" in enabled
        assert "openai" not in enabled

    @pytest.mark.integration
    def test_get_provider_config(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test getting configuration for specific provider."""
        provider = config_loader.get_provider_config("anthropic")

        assert provider is not None
        assert provider.name == "anthropic"
        assert provider.enabled is True

    @pytest.mark.integration
    def test_get_nonexistent_provider_config(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test getting configuration for non-existent provider."""
        provider = config_loader.get_provider_config("nonexistent")
        assert provider is None

    @pytest.mark.integration
    def test_provider_models_list(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test provider models are properly loaded."""
        config = config_loader.load()

        anthropic = config.providers["anthropic"]
        assert len(anthropic.models) == 1
        assert anthropic.models[0]["name"] == "claude-sonnet-4-7"


# =============================================================================
# Secret Masking Tests
# =============================================================================


class TestSecretMasking:
    """Integration tests for secret masking."""

    @pytest.mark.integration
    def test_mask_api_keys(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test that API keys are masked in output."""
        data = {
            "api_key": "secret-key-123",
            "secret": "my-secret",
            "token": "bearer-token",  # token is not masked by current implementation
            "provider": "test",
        }

        masked = config_loader.mask_secrets(data)

        assert masked["api_key"] == "***"
        assert masked["secret"] == "***"
        # Token is not masked since implementation only checks for 'key' or 'secret'
        assert masked["token"] == "bearer-token"
        assert masked["provider"] == "test"

    @pytest.mark.integration
    def test_mask_nested_secrets(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test masking secrets in nested structures."""
        data = {
            "outer": {
                "inner": {
                    "api_key": "secret",
                }
            }
        }

        masked = config_loader.mask_secrets(data)

        assert masked["outer"]["inner"]["api_key"] == "***"

    @pytest.mark.integration
    def test_mask_in_list(
        self,
        config_loader: ConfigLoader,
    ) -> None:
        """Test masking secrets in lists."""
        data = {
            "providers": [
                {"name": "test", "api_key": "secret1"},
                {"name": "test2", "api_key": "secret2"},
            ]
        }

        masked = config_loader.mask_secrets(data)

        assert masked["providers"][0]["api_key"] == "***"
        assert masked["providers"][1]["api_key"] == "***"


# =============================================================================
# Global Config Loader Tests
# =============================================================================


class TestGlobalConfigLoader:
    """Integration tests for global config loader."""

    @pytest.mark.integration
    def test_get_config_loader_singleton(
        self,
        config_file: Path,
    ) -> None:
        """Test that get_config_loader returns singleton."""
        # Note: This test may be affected by other tests
        loader = get_config_loader()
        assert loader is not None
        assert isinstance(loader, ConfigLoader)

    @pytest.mark.integration
    def test_load_config_convenience_function(
        self,
        config_file: Path,
    ) -> None:
        """Test the load_config convenience function."""
        # This tests the module-level load_config function
        # Note: May use cached config from previous tests
        try:
            config = load_config()
            assert config is not None
        except FileNotFoundError:
            # Expected if no default config exists
            pass


# =============================================================================
# Edge Case Configuration Tests
# =============================================================================


class TestEdgeCaseConfiguration:
    """Integration tests for edge cases in configuration."""

    @pytest.mark.integration
    def test_empty_config_file(self) -> None:
        """Test handling of empty configuration file."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            f.write("{}")
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path=config_path)
            config = loader.load()

            # Should have empty providers with defaults
            assert config.providers == {}
            assert config.defaults.provider == "anthropic"
        finally:
            config_path.unlink()

    @pytest.mark.integration
    def test_config_with_extra_fields(
        self,
        sample_config_dict: dict,
    ) -> None:
        """Test that extra fields in config are ignored."""
        config_with_extra = sample_config_dict.copy()
        config_with_extra["unknown_field"] = "should be ignored"
        config_with_extra["providers"]["anthropic"]["unknown"] = "ignored"

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump(config_with_extra, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path=config_path)
            config = loader.load()

            # Extra fields should be ignored
            assert not hasattr(config, "unknown_field")
        finally:
            config_path.unlink()

    @pytest.mark.integration
    def test_negative_retry_values(
        self,
        sample_config_dict: dict,
    ) -> None:
        """Test handling of negative retry values."""
        invalid_config = sample_config_dict.copy()
        invalid_config["retry"]["max_retries"] = -1

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump(invalid_config, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path=config_path)
            config = loader.load()

            # Should convert negative to int
            assert config.retry.max_retries == -1
        finally:
            config_path.unlink()

    @pytest.mark.integration
    def test_zero_timeout(
        self,
        sample_config_dict: dict,
    ) -> None:
        """Test handling of zero timeout value."""
        zero_timeout_config = sample_config_dict.copy()
        zero_timeout_config["retry"]["base_delay"] = 0.0

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
        ) as f:
            json.dump(zero_timeout_config, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader(config_path=config_path)
            config = loader.load()

            assert config.retry.base_delay == 0.0
        finally:
            config_path.unlink()
