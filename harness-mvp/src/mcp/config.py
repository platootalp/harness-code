"""MCP configuration loader."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import MCPServerConfig


def load_mcp_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """
    Load MCP configuration from file.

    Expected format:
    {
        "mcp_servers": {
            "filesystem": {
                "command": "fastmcp",
                "args": ["run", "/path/to/filesystem-server.py"]
            },
            "git": {
                "command": "npx",
                "args": ["@modelcontextprotocol/server-git"]
            }
        },
        "exposed_tools": ["LocalBash", "LocalRead", "LocalEdit"],
        "exposed_resources": ["file://workspace/*"]
    }

    Args:
        config_path: Path to MCP config file. If None, searches:
            - .mcp.json in current directory
            - .mcp.json in home directory
            - MCP_CONFIG_PATH environment variable

    Returns:
        Loaded MCP configuration dict.
    """
    import os

    if config_path is None:
        search_paths = [
            Path.cwd() / ".mcp.json",
            Path.home() / ".mcp.json",
        ]
        env_path = os.environ.get("MCP_CONFIG_PATH")
        if env_path:
            search_paths.insert(0, Path(env_path))

        for path in search_paths:
            if path.exists():
                config_path = path
                break

    if config_path is None:
        return {}

    if isinstance(config_path, str):
        config_path = Path(config_path)

    if not config_path.exists():
        return {}

    with open(config_path) as f:
        config = json.load(f)

    return config


def parse_mcp_servers(config: dict[str, Any]) -> dict[str, MCPServerConfig]:
    """
    Parse MCP server configurations into MCPServerConfig objects.

    Args:
        config: MCP configuration dict with "mcp_servers" key.

    Returns:
        Dict mapping server name -> MCPServerConfig.
    """
    servers: dict[str, MCPServerConfig] = {}
    mcp_servers = config.get("mcp_servers", {})

    for name, server_config in mcp_servers.items():
        if isinstance(server_config, dict):
            servers[name] = MCPServerConfig(
                name=name,
                command=server_config.get("command", ""),
                args=server_config.get("args", []),
                env=server_config.get("env"),
            )
        elif isinstance(server_config, str):
            # Simple string format: just the command
            servers[name] = MCPServerConfig(
                name=name,
                command=server_config,
                args=[],
            )

    return servers
