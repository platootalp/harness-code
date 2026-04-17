"""
Tests for plugins/manifest.py - Plugin manifest parsing and validation.
"""

from __future__ import annotations

import pytest

from src.claude_code.plugins.base import PluginManifest


# =============================================================================
# Minimal Manifest Tests
# =============================================================================


class TestParseManifest:
    """Tests for parse_manifest()."""

    def test_parse_minimal_manifest(self, tmp_path: pytest.TempPathFactory) -> None:
        """Parse a minimal valid manifest."""
        import json

        plugin_dir = tmp_path / "my-plugin"
        plugin_dir.mkdir()
        manifest_path = plugin_dir / "plugin.json"
        manifest_path.write_text(
            json.dumps({"name": "test-plugin", "version": "1.0.0"})
        )

        from src.claude_code.plugins.manifest import parse_manifest

        manifest = parse_manifest(manifest_path)
        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"

    def test_parse_full_manifest(self, tmp_path: pytest.TempPathFactory) -> None:
        """Parse a manifest with all fields."""
        import json

        plugin_dir = tmp_path / "full-plugin"
        plugin_dir.mkdir()
        manifest_path = plugin_dir / "plugin.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "name": "full-plugin",
                    "version": "2.1.0",
                    "description": "A fully featured plugin",
                    "author": {"name": "Jane Doe", "email": "jane@example.com"},
                    "homepage": "https://example.com",
                    "repository": "https://github.com/example/plugin",
                    "license": "Apache-2.0",
                    "keywords": ["ai", "productivity"],
                    "dependencies": ["other-plugin"],
                    "commands": ["commands/*.md"],
                    "agents": ["agents/*.md"],
                    "skills": ["skills/**/*.md"],
                    "hooks": {"PreToolUse": []},
                }
            )
        )

        from src.claude_code.plugins.manifest import parse_manifest

        manifest = parse_manifest(manifest_path)
        assert manifest.name == "full-plugin"
        assert manifest.version == "2.1.0"
        assert manifest.description == "A fully featured plugin"
        assert manifest.author == {"name": "Jane Doe", "email": "jane@example.com"}
        assert manifest.homepage == "https://example.com"
        assert manifest.repository == "https://github.com/example/plugin"
        assert manifest.license == "Apache-2.0"
        assert manifest.keywords == ["ai", "productivity"]
        assert manifest.dependencies == ["other-plugin"]
        assert manifest.commands == ["commands/*.md"]
        assert manifest.agents == ["agents/*.md"]
        assert manifest.skills == ["skills/**/*.md"]
        assert manifest.hooks == {"PreToolUse": []}

    def test_parse_manifest_missing_required_field(self, tmp_path: pytest.TempPathFactory) -> None:
        """Parse fails when name is missing."""
        import json

        manifest_path = tmp_path / "plugin.json"
        manifest_path.write_text(json.dumps({"version": "1.0.0"}))

        from src.claude_code.plugins.manifest import (
            ManifestParseError,
            parse_manifest,
        )

        with pytest.raises(ManifestParseError) as exc_info:
            parse_manifest(manifest_path)
        assert "name" in str(exc_info.value)

    def test_parse_manifest_missing_version(self, tmp_path: pytest.TempPathFactory) -> None:
        """Version field defaults to 1.0.0 when missing."""
        import json

        manifest_path = tmp_path / "plugin.json"
        manifest_path.write_text(json.dumps({"name": "no-version-plugin"}))

        from src.claude_code.plugins.manifest import parse_manifest

        manifest = parse_manifest(manifest_path)
        assert manifest.version == "1.0.0"

    def test_parse_manifest_file_not_found(self, tmp_path: pytest.TempPathFactory) -> None:
        """Parse fails when file does not exist."""
        from src.claude_code.plugins.manifest import (
            ManifestParseError,
            parse_manifest,
        )

        nonexistent = tmp_path / "does-not-exist.json"
        with pytest.raises(ManifestParseError) as exc_info:
            parse_manifest(nonexistent)
        assert "not found" in str(exc_info.value)

    def test_parse_manifest_invalid_json(self, tmp_path: pytest.TempPathFactory) -> None:
        """Parse fails on invalid JSON."""
        manifest_path = tmp_path / "plugin.json"
        manifest_path.write_text("{ not json }")

        from src.claude_code.plugins.manifest import (
            ManifestParseError,
            parse_manifest,
        )

        with pytest.raises(ManifestParseError) as exc_info:
            parse_manifest(manifest_path)
        assert "parse" in str(exc_info.value).lower()


class TestValidateManifest:
    """Tests for validate_manifest()."""

    def test_validate_valid_manifest(self) -> None:
        """Valid manifest passes validation."""
        from src.claude_code.plugins.manifest import validate_manifest

        manifest = PluginManifest(name="valid", version="1.0.0")
        errors = validate_manifest(manifest)
        assert errors == []

    def test_validate_empty_name(self) -> None:
        """Empty name fails validation."""
        from src.claude_code.plugins.manifest import validate_manifest

        manifest = PluginManifest(name="", version="1.0.0")
        errors = validate_manifest(manifest)
        assert any("name" in e.lower() for e in errors)

    def test_validate_invalid_version_format(self) -> None:
        """Invalid version format fails validation."""
        from src.claude_code.plugins.manifest import validate_manifest

        manifest = PluginManifest(name="test", version="not-a-version")
        errors = validate_manifest(manifest)
        assert any("version" in e.lower() for e in errors)

    def test_validate_whitespace_name(self) -> None:
        """Name with whitespace fails validation."""
        from src.claude_code.plugins.manifest import validate_manifest

        manifest = PluginManifest(name="has space", version="1.0.0")
        errors = validate_manifest(manifest)
        assert any("name" in e.lower() for e in errors)

    def test_validate_all_errors_collected(self) -> None:
        """Multiple errors are all collected."""
        from src.claude_code.plugins.manifest import validate_manifest

        manifest = PluginManifest(name="", version="bad")
        errors = validate_manifest(manifest)
        assert len(errors) >= 2


class TestManifestDefaults:
    """Tests for manifest default values."""

    def test_default_license(self, tmp_path: pytest.TempPathFactory) -> None:
        """License defaults to MIT."""
        import json

        manifest_path = tmp_path / "plugin.json"
        manifest_path.write_text(
            json.dumps({"name": "mit-plugin", "version": "1.0.0"})
        )

        from src.claude_code.plugins.manifest import parse_manifest

        manifest = parse_manifest(manifest_path)
        assert manifest.license == "MIT"

    def test_default_keywords(self, tmp_path: pytest.TempPathFactory) -> None:
        """Keywords defaults to empty list."""
        import json

        manifest_path = tmp_path / "plugin.json"
        manifest_path.write_text(
            json.dumps({"name": "kw-plugin", "version": "1.0.0"})
        )

        from src.claude_code.plugins.manifest import parse_manifest

        manifest = parse_manifest(manifest_path)
        assert manifest.keywords == []

    def test_default_dependencies(self, tmp_path: pytest.TempPathFactory) -> None:
        """Dependencies defaults to empty list."""
        import json

        manifest_path = tmp_path / "plugin.json"
        manifest_path.write_text(
            json.dumps({"name": "dep-plugin", "version": "1.0.0"})
        )

        from src.claude_code.plugins.manifest import parse_manifest

        manifest = parse_manifest(manifest_path)
        assert manifest.dependencies == []
