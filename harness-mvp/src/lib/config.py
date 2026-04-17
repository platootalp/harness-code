"""Configuration loader from file and environment."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load configuration from file and environment variables.

    Config file priority (first found):
    1. --config CLI argument
    2. .mvpai.json in current directory
    3. .mvpai.json in home directory
    4. Environment variables

    Config file format (JSON):
    {
        "ANTHROPIC_AUTH_TOKEN": "sk-...",
        "ANTHROPIC_BASE_URL": "https://api.minimaxi.com/anthropic",
        "ANTHROPIC_MODEL": "MiniMax-M2.7",
        "API_TIMEOUT_MS": "300000"
    }
    """
    config = {}

    # Search for config file
    search_paths = []
    if config_path:
        search_paths.append(Path(config_path))
    search_paths.extend([
        Path.cwd() / '.mvpai.json',
        Path.home() / '.mvpai.json',
    ])

    for path in search_paths:
        if path.exists():
            print(f"Loading config from: {path}")
            with open(path) as f:
                config = json.load(f)
            break

    # Environment variables override config file
    env_mappings = {
        'ANTHROPIC_AUTH_TOKEN': 'ANTHROPIC_AUTH_TOKEN',
        'ANTHROPIC_BASE_URL': 'ANTHROPIC_BASE_URL',
        'ANTHROPIC_MODEL': 'ANTHROPIC_MODEL',
        'API_TIMEOUT_MS': 'API_TIMEOUT_MS',
        'ANTHROPIC_SMALL_FAST_MODEL': 'ANTHROPIC_SMALL_FAST_MODEL',
        'ANTHROPIC_DEFAULT_SONNET_MODEL': 'ANTHROPIC_DEFAULT_SONNET_MODEL',
        'ANTHROPIC_DEFAULT_OPUS_MODEL': 'ANTHROPIC_DEFAULT_OPUS_MODEL',
        'ANTHROPIC_DEFAULT_HAIKU_MODEL': 'ANTHROPIC_DEFAULT_HAIKU_MODEL',
    }

    for env_key in env_mappings:
        if env_key in os.environ:
            config[env_key] = os.environ[env_key]

    return config


def apply_config(config: dict[str, Any]) -> None:
    """Apply configuration to environment variables."""
    for key, value in config.items():
        if key.startswith('ANTHROPIC_') or key.startswith('API_'):
            os.environ.setdefault(key, str(value))
