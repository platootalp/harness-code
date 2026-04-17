"""
Plugin manifest parsing and validation.

Handles reading plugin.json files and validating their structure.

TypeScript equivalent: src/utils/plugins/schemas.ts
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .base import PluginManifest

# =============================================================================
# Exceptions
# =============================================================================


class ManifestParseError(Exception):
    """Raised when a plugin manifest cannot be parsed or validated."""

    pass


# =============================================================================
# Validation
# =============================================================================

# Valid semantic version pattern (MAJOR.MINOR.PATCH)
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def validate_manifest(manifest: PluginManifest) -> list[str]:
    """Validate a plugin manifest.

    Args:
        manifest: The manifest to validate.

    Returns:
        List of validation error messages. Empty if valid.
    """
    errors: list[str] = []

    # Validate name
    if not manifest.name:
        errors.append("Manifest must have a non-empty 'name' field")
    elif not manifest.name.strip():
        errors.append("Manifest 'name' cannot be whitespace-only")
    elif " " in manifest.name:
        errors.append("Manifest 'name' cannot contain whitespace")

    # Validate version
    if manifest.version and not _VERSION_RE.match(manifest.version):
        errors.append(f"Manifest 'version' must be a valid semver string, got: {manifest.version}")

    return errors


# =============================================================================
# Parsing
# =============================================================================


def parse_manifest(manifest_path: Path) -> PluginManifest:
    """Parse a plugin.json manifest file.

    Args:
        manifest_path: Path to the plugin.json file.

    Returns:
        Parsed PluginManifest.

    Raises:
        ManifestParseError: If the file cannot be read or parsed.
    """
    if not manifest_path.exists():
        raise ManifestParseError(
            f"Manifest file not found: {manifest_path}"
        )

    try:
        data = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        raise ManifestParseError(
            f"Manifest parse error in {manifest_path}: {e}"
        ) from e

    if not isinstance(data, dict):
        raise ManifestParseError(
            f"Manifest must be a JSON object in {manifest_path}"
        )

    # Validate required fields
    if not data.get("name"):
        raise ManifestParseError(
            f"Manifest missing required field 'name' in {manifest_path}"
        )

    # Build manifest with defaults
    manifest = PluginManifest(
        name=data.get("name", ""),
        version=data.get("version", "1.0.0"),
        description=data.get("description", ""),
        author=_parse_author(data.get("author")),
        homepage=data.get("homepage"),
        repository=data.get("repository"),
        license=data.get("license", "MIT"),
        keywords=list(data.get("keywords", [])),
        dependencies=list(data.get("dependencies", [])),
        commands=_maybe_list(data.get("commands")),
        agents=_maybe_list(data.get("agents")),
        skills=_maybe_list(data.get("skills")),
        hooks=data.get("hooks"),
        output_styles=_maybe_list(data.get("outputStyles")),
        mcp_servers=data.get("mcpServers"),
        lsp_servers=data.get("lspServers"),
        user_config=data.get("userConfig"),
    )

    # Validate the parsed manifest
    errors = validate_manifest(manifest)
    if errors:
        raise ManifestParseError(
            f"Manifest validation failed for {manifest_path}: {'; '.join(errors)}"
        )

    return manifest


def _parse_author(value: Any) -> dict[str, str] | None:
    """Parse author field from manifest data."""
    if value is None:
        return None
    if isinstance(value, dict):
        return dict(value)
    return None


def _maybe_list(value: Any) -> list[str] | None:
    """Return list if value is a list, else None."""
    if isinstance(value, list):
        return [str(v) for v in value]
    return None
