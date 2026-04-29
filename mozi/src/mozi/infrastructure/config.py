"""Configuration loader for Mozi.

Provides secure configuration loading with environment variable overrides.
Supports reading from JSON config files and environment variable substitution.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Environment variable pattern: ${VAR_NAME} or ${VAR_NAME:default_value}
ENV_VAR_PATTERN = "${"
SECRET_MASK = "***"


@dataclass
class ModelConfig:
    """Model provider configuration."""

    name: str
    enabled: bool = True
    api_key_env: str | None = None
    base_url: str | None = None
    models: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RetryConfig:
    """Retry configuration."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


@dataclass
class DefaultsConfig:
    """Default configuration."""

    provider: str = "anthropic"
    model: str = "claude-sonnet-4-7"
    temperature: float = 1.0
    max_tokens: int = 4096


@dataclass
class Config:
    """Root configuration object."""

    providers: dict[str, ModelConfig] = field(default_factory=dict)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)


class ConfigLoader:
    """Loads and manages configuration with environment variable overrides.

    Supports:
    - Loading configuration from JSON files
    - Environment variable substitution for API keys and secrets
    - Default values for missing environment variables
    - Secure handling of sensitive configuration values
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        """Initialize config loader.

        Args:
            config_path: Path to config file. Defaults to config/model.json
                         in the project root.
        """
        if config_path is None:
            # Default to config/model.json in project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "model.json"
        self._config_path = Path(config_path)
        self._config: Config | None = None

    def load(self) -> Config:
        """Load configuration from file with environment variable substitution.

        Returns:
            Loaded and processed configuration object.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            json.JSONDecodeError: If config file is invalid JSON.
        """
        if not self._config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self._config_path}")

        with open(self._config_path, encoding="utf-8") as f:
            raw_config = json.load(f)

        # Process environment variables
        processed_config = self._substitute_env_vars(raw_config)

        return self._parse_config(processed_config)

    def _substitute_env_vars(self, obj: Any) -> Any:
        """Recursively substitute environment variables in config.

        Looks for patterns like ${VAR_NAME} or ${VAR_NAME:default}.

        Args:
            obj: Object to process (dict, list, str, or primitive).

        Returns:
            Object with environment variables substituted.
        """
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            if ENV_VAR_PATTERN in obj:
                return self._substitute_string_env_vars(obj)
            return obj
        return obj

    def _substitute_string_env_vars(self, value: str) -> str:
        """Substitute environment variables in a string.

        Args:
            value: String potentially containing ${VAR_NAME} or ${VAR_NAME:default}.

        Returns:
            String with environment variables substituted.
        """
        pattern = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")

        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default_value = match.group(2)

            env_value = os.environ.get(var_name)

            if env_value is not None:
                return env_value
            if default_value is not None:
                return default_value
            if "_ENV" in var_name:
                # For API key env vars without defaults, return empty string
                # This allows providers to be disabled when keys aren't set
                return ""
            return match.group(0)  # Keep original if not found

        return pattern.sub(replace, value)

    def _parse_config(self, raw: dict[str, Any]) -> Config:
        """Parse raw config dict into Config object.

        Args:
            raw: Raw configuration dictionary.

        Returns:
            Parsed Config object.
        """
        # Parse providers
        providers: dict[str, ModelConfig] = {}
        for name, provider_data in raw.get("providers", {}).items():
            providers[name] = ModelConfig(
                name=name,
                enabled=provider_data.get("enabled", True),
                api_key_env=provider_data.get("api_key_env"),
                base_url=provider_data.get("base_url"),
                models=provider_data.get("models", []),
            )

        # Parse defaults
        defaults_data = raw.get("defaults", {})
        defaults = DefaultsConfig(
            provider=defaults_data.get("provider", "anthropic"),
            model=defaults_data.get("model", "claude-sonnet-4-7"),
            temperature=float(defaults_data.get("temperature", 1.0)),
            max_tokens=int(defaults_data.get("max_tokens", 4096)),
        )

        # Parse retry config
        retry_data = raw.get("retry", {})
        retry = RetryConfig(
            max_retries=int(retry_data.get("max_retries", 3)),
            base_delay=float(retry_data.get("base_delay", 1.0)),
            max_delay=float(retry_data.get("max_delay", 60.0)),
            exponential_base=float(retry_data.get("exponential_base", 2.0)),
            jitter=bool(retry_data.get("jitter", True)),
        )

        # Parse circuit breaker config
        cb_data = raw.get("circuit_breaker", {})
        circuit_breaker = CircuitBreakerConfig(
            failure_threshold=int(cb_data.get("failure_threshold", 5)),
            recovery_timeout=float(cb_data.get("recovery_timeout", 60.0)),
            half_open_max_calls=int(cb_data.get("half_open_max_calls", 3)),
        )

        return Config(
            providers=providers,
            defaults=defaults,
            retry=retry,
            circuit_breaker=circuit_breaker,
        )

    def get_api_key(self, provider: str) -> str | None:
        """Get API key for a provider from environment variables.

        Args:
            provider: Provider name (e.g., 'anthropic', 'openai').

        Returns:
            API key if found in environment, None otherwise.
        """
        if self._config is None:
            self._config = self.load()

        provider_config = self._config.providers.get(provider)
        if provider_config is None or provider_config.api_key_env is None:
            return None

        return os.environ.get(provider_config.api_key_env)

    def get_provider_config(self, provider: str) -> ModelConfig | None:
        """Get configuration for a specific provider.

        Args:
            provider: Provider name.

        Returns:
            ModelConfig for the provider, None if not found.
        """
        if self._config is None:
            self._config = self.load()

        return self._config.providers.get(provider)

    def get_enabled_providers(self) -> list[str]:
        """Get list of enabled provider names.

        Returns:
            List of enabled provider names.
        """
        if self._config is None:
            self._config = self.load()

        return [
            name
            for name, config in self._config.providers.items()
            if config.enabled
        ]

    def mask_secrets(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive values in configuration data.

        Args:
            data: Configuration dictionary.

        Returns:
            Configuration with sensitive values masked.
        """
        result: dict[str, Any] = {}
        for key, value in data.items():
            if "key" in key.lower() or "secret" in key.lower():
                result[key] = SECRET_MASK
            elif isinstance(value, dict):
                result[key] = self.mask_secrets(value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                result[key] = [self.mask_secrets(item) for item in value]
            else:
                result[key] = value
        return result


# Global config loader instance
_loader: ConfigLoader | None = None


def get_config_loader() -> ConfigLoader:
    """Get the global config loader instance.

    Returns:
        ConfigLoader instance.
    """
    global _loader
    if _loader is None:
        _loader = ConfigLoader()
    return _loader


def load_config() -> Config:
    """Load configuration using the global loader.

    Returns:
        Loaded configuration.
    """
    return get_config_loader().load()
