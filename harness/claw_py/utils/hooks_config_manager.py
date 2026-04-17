"""Hook configuration loading and management."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import UTC
from typing import TYPE_CHECKING

from claude_code.utils.hooks import HookCommand, HookEvent, register_hook, unregister_hook

if TYPE_CHECKING:
    pass

# =============================================================================
# Hook Configuration
# =============================================================================


@dataclass
class HookConfig:
    """Configuration for a single hook."""

    name: str
    event: str
    command: str
    args: list[str] = field(default_factory=list)
    timeout_ms: int = 30000
    enabled: bool = True
    env: dict[str, str] | None = None


@dataclass
class HooksConfig:
    """Root hooks configuration."""

    hooks: list[HookConfig] = field(default_factory=list)
    version: str = "1.0"


# =============================================================================
# Config File Paths
# =============================================================================


def get_hooks_config_path() -> str | None:
    """Get the hooks configuration file path.

    Returns:
        Path to hooks.json if found, or None.
    """
    config_home = os.environ.get(
        "CLAUDE_CONFIG_HOME",
        os.path.join(os.path.expanduser("~"), ".config", "claude"),
    )
    hooks_path = os.path.join(config_home, "hooks.json")
    if os.path.exists(hooks_path):
        return hooks_path

    # Also check project-level config
    cwd = os.getcwd()
    project_hooks = os.path.join(cwd, ".claude", "hooks.json")
    if os.path.exists(project_hooks):
        return project_hooks

    return None


def get_default_hooks_dir() -> str:
    """Get the default hooks directory path.

    Returns:
        Path to the hooks directory.
    """
    config_home = os.environ.get(
        "CLAUDE_CONFIG_HOME",
        os.path.join(os.path.expanduser("~"), ".config", "claude"),
    )
    return os.path.join(config_home, "hooks")


# =============================================================================
# Config Loading
# =============================================================================


def load_hooks_config(config_path: str | None = None) -> HooksConfig:
    """Load hooks configuration from file.

    Args:
        config_path: Path to config file. If None, uses default lookup.

    Returns:
        Loaded HooksConfig.
    """
    if config_path is None:
        config_path = get_hooks_config_path()
        if config_path is None:
            return HooksConfig()

    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)

        hooks: list[HookConfig] = []
        for hook_data in data.get("hooks", []):
            try:
                hook_config = HookConfig(
                    name=hook_data["name"],
                    event=hook_data["event"],
                    command=hook_data["command"],
                    args=hook_data.get("args", []),
                    timeout_ms=hook_data.get("timeout_ms", 30000),
                    enabled=hook_data.get("enabled", True),
                    env=hook_data.get("env"),
                )
                hooks.append(hook_config)
            except KeyError:
                continue

        return HooksConfig(
            hooks=hooks,
            version=data.get("version", "1.0"),
        )
    except (OSError, json.JSONDecodeError, KeyError):
        return HooksConfig()


def merge_hooks_configs(*configs: HooksConfig) -> HooksConfig:
    """Merge multiple hook configs into one.

    Later configs override earlier ones for hooks with the same name.

    Args:
        *configs: HooksConfig instances to merge.

    Returns:
        Merged HooksConfig.
    """
    hooks_by_name: dict[str, HookConfig] = {}
    for config in configs:
        for hook in config.hooks:
            hooks_by_name[hook.name] = hook
    return HooksConfig(hooks=list(hooks_by_name.values()))


# =============================================================================
# Config Validation
# =============================================================================


def validate_hook_config(hook: HookConfig) -> list[str]:
    """Validate a hook configuration.

    Args:
        hook: The hook to validate.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors: list[str] = []

    if not hook.name:
        errors.append("Hook name is required")
    elif not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", hook.name):
        errors.append(f"Hook name '{hook.name}' contains invalid characters")

    try:
        HookEvent(hook.event)
    except ValueError:
        valid_events = [e.value for e in HookEvent]
        errors.append(f"Invalid event '{hook.event}'. Valid events: {', '.join(valid_events)}")

    if not hook.command:
        errors.append("Hook command is required")

    if hook.timeout_ms <= 0:
        errors.append(f"timeout_ms must be positive, got {hook.timeout_ms}")

    return errors


# =============================================================================
# Hook Registration
# =============================================================================


def register_hooks_from_config(config: HooksConfig) -> None:
    """Register all enabled hooks from a config.

    Args:
        config: The hooks configuration.
    """
    for hook_config in config.hooks:
        if not hook_config.enabled:
            continue
        errors = validate_hook_config(hook_config)
        if errors:
            continue
        try:
            event = HookEvent(hook_config.event)
        except ValueError:
            continue
        hook_cmd = HookCommand(
            command=hook_config.command,
            args=hook_config.args,
            timeout_ms=hook_config.timeout_ms,
            env=hook_config.env,
        )
        register_hook(event, hook_cmd)


def unregister_hooks_from_config(config: HooksConfig) -> None:
    """Unregister all hooks from a config.

    Args:
        config: The hooks configuration.
    """
    for hook_config in config.hooks:
        try:
            event = HookEvent(hook_config.event)
        except ValueError:
            continue
        hook_cmd = HookCommand(
            command=hook_config.command,
            args=hook_config.args,
            timeout_ms=hook_config.timeout_ms,
            env=hook_config.env,
        )
        unregister_hook(event, hook_cmd)


# =============================================================================
# Config Snapshot
# =============================================================================


@dataclass
class HooksConfigSnapshot:
    """Snapshot of loaded hooks configuration for a session."""

    config: HooksConfig
    loaded_at: str
    config_path: str | None


def create_config_snapshot(
    config: HooksConfig | None = None,
    config_path: str | None = None,
) -> HooksConfigSnapshot:
    """Create a snapshot of the current hooks configuration.

    Args:
        config: The config to snapshot. If None, loads from default path.
        config_path: Path used for the config.

    Returns:
        A HooksConfigSnapshot.
    """
    from datetime import datetime
    if config is None:
        config = load_hooks_config(config_path)
        if config_path is None:
            config_path = get_hooks_config_path()
    return HooksConfigSnapshot(
        config=config,
        loaded_at=datetime.now(UTC).isoformat(),
        config_path=config_path,
    )


# =============================================================================
# Hooks Manager
# =============================================================================


class HooksConfigManager:
    """Manages hook configuration loading and registration."""

    _current_snapshot: HooksConfigSnapshot | None = None

    def __init__(self) -> None:
        self._snapshot: HooksConfigSnapshot | None = None

    def load(self, config_path: str | None = None) -> HooksConfig:
        """Load and register hooks from a config file.

        Args:
            config_path: Path to config file.

        Returns:
            The loaded configuration.
        """
        from claude_code.utils.hooks import clear_hooks
        config = load_hooks_config(config_path)
        clear_hooks()
        register_hooks_from_config(config)
        self._snapshot = create_config_snapshot(config, config_path)
        return config

    def reload(self) -> HooksConfig:
        """Reload the current configuration.

        Returns:
            The reloaded configuration.
        """
        config_path = self._snapshot.config_path if self._snapshot else None
        return self.load(config_path)

    def get_snapshot(self) -> HooksConfigSnapshot | None:
        """Get the current configuration snapshot.

        Returns:
            Current snapshot, or None if not loaded.
        """
        return self._snapshot

    def clear(self) -> None:
        """Clear all registered hooks."""
        from claude_code.utils.hooks import clear_hooks
        clear_hooks()
        self._snapshot = None
