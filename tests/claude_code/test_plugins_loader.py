"""
Tests for plugins/loader.py - Plugin loading from various sources.
"""

from __future__ import annotations

import pytest

from src.claude_code.plugins.base import PluginSource
from src.claude_code.plugins.loader import (
    ParsedSource,
    _parse_git_source,
    _parse_github_source,
    _parse_npm_source,
    _parse_pip_source,
    parse_source,
)


class TestParseSource:
    """Tests for parse_source()."""

    def test_npm_source(self) -> None:
        """Parse npm: source."""
        result = parse_source("npm:my-plugin@1.0.0")
        assert result.source_type == PluginSource.NPM
        assert result.name == "my-plugin"
        assert result.version == "1.0.0"
        assert result.url is None

    def test_npm_source_without_version(self) -> None:
        """Parse npm: source without version."""
        result = parse_source("npm:my-plugin")
        assert result.source_type == PluginSource.NPM
        assert result.name == "my-plugin"
        assert result.version is None

    def test_pip_source(self) -> None:
        """Parse pip: source."""
        result = parse_source("pip:my-plugin==1.0.0")
        assert result.source_type == PluginSource.PIP
        assert result.name == "my-plugin"
        assert result.version == "1.0.0"

    def test_pip_source_without_version(self) -> None:
        """Parse pip: source without version."""
        result = parse_source("pip:my-plugin")
        assert result.source_type == PluginSource.PIP
        assert result.name == "my-plugin"
        assert result.version is None

    def test_git_source(self) -> None:
        """Parse git: source."""
        result = parse_source("git:https://github.com/user/repo.git")
        assert result.source_type == PluginSource.GIT
        assert "github.com" in (result.url or "")

    def test_git_source_with_ref(self) -> None:
        """Parse git: source with ref using #."""
        result = parse_source("git:https://github.com/user/repo.git#develop")
        assert result.source_type == PluginSource.GIT
        assert result.ref == "develop"

    def test_github_source(self) -> None:
        """Parse github: source shorthand."""
        result = parse_source("github:user/repo")
        assert result.source_type == PluginSource.GITHUB
        assert result.url == "https://github.com/user/repo"

    def test_github_source_with_ref(self) -> None:
        """Parse github: source with ref."""
        result = parse_source("github:user/repo@v2.0.0")
        assert result.source_type == PluginSource.GITHUB
        assert result.url == "https://github.com/user/repo"
        assert result.ref == "v2.0.0"

    def test_local_relative_path(self) -> None:
        """Parse local relative path."""
        result = parse_source("./my-local-plugin")
        assert result.source_type == PluginSource.LOCAL
        assert result.name == "my-local-plugin"
        assert result.url == "./my-local-plugin"

    def test_local_absolute_path(self) -> None:
        """Parse absolute local path."""
        result = parse_source("/absolute/path/to/plugin")
        assert result.source_type == PluginSource.LOCAL
        assert result.url == "/absolute/path/to/plugin"

    def test_npm_scoped_package(self) -> None:
        """Parse npm source with @ symbol for scoped packages."""
        result = parse_source("npm:@scope/my-plugin@1.0.0")
        assert result.source_type == PluginSource.NPM
        assert result.name == "@scope/my-plugin"
        assert result.version == "1.0.0"


class TestParseNpmSource:
    """Tests for _parse_npm_source()."""

    def test_simple_package(self) -> None:
        """Parse simple npm package name."""
        result = _parse_npm_source("my-plugin")
        assert result.source_type == PluginSource.NPM
        assert result.name == "my-plugin"
        assert result.version is None

    def test_package_with_version(self) -> None:
        """Parse package with version."""
        result = _parse_npm_source("my-plugin@1.2.3")
        assert result.name == "my-plugin"
        assert result.version == "1.2.3"

    def test_scoped_package(self) -> None:
        """Parse scoped npm package."""
        result = _parse_npm_source("@org/my-plugin@2.0.0")
        assert result.name == "@org/my-plugin"
        assert result.version == "2.0.0"


class TestParsePipSource:
    """Tests for _parse_pip_source()."""

    def test_simple_package(self) -> None:
        """Parse simple pip package name."""
        result = _parse_pip_source("my-plugin")
        assert result.source_type == PluginSource.PIP
        assert result.name == "my-plugin"
        assert result.version is None

    def test_package_with_version(self) -> None:
        """Parse package with double-equals version."""
        result = _parse_pip_source("my-plugin==1.2.3")
        assert result.name == "my-plugin"
        assert result.version == "1.2.3"

    def test_package_with_version_specifier(self) -> None:
        """Parse package with version specifier."""
        result = _parse_pip_source("my-plugin>=1.0.0,<2.0.0")
        assert result.name == "my-plugin"
        assert result.version == "1.0.0,<2.0.0"


class TestParseGitSource:
    """Tests for _parse_git_source()."""

    def test_https_url(self) -> None:
        """Parse HTTPS git URL."""
        result = _parse_git_source("git:https://github.com/user/repo.git")
        assert result.source_type == PluginSource.GIT
        assert "github.com" in (result.url or "")

    def test_ssh_url(self) -> None:
        """Parse SSH git URL."""
        result = _parse_git_source("git:git@github.com:user/repo.git")
        assert result.source_type == PluginSource.GIT
        assert "github.com" in (result.url or "")

    def test_url_with_ref(self) -> None:
        """Parse git URL with ref using #."""
        result = _parse_git_source("git:https://github.com/user/repo.git#develop")
        assert result.ref == "develop"

    def test_url_with_branch(self) -> None:
        """Parse git URL with branch using #."""
        result = _parse_git_source("git:https://github.com/user/repo.git#main")
        assert result.ref == "main"


class TestParseGithubSource:
    """Tests for _parse_github_source()."""

    def test_simple_owner_repo(self) -> None:
        """Parse owner/repo shorthand."""
        result = _parse_github_source("user/repo")
        assert result.source_type == PluginSource.GITHUB
        assert result.name == "repo"
        assert result.url == "https://github.com/user/repo"

    def test_with_ref(self) -> None:
        """Parse owner/repo with ref."""
        result = _parse_github_source("user/repo@main")
        assert result.source_type == PluginSource.GITHUB
        assert result.name == "repo"
        assert result.ref == "main"

    def test_with_version(self) -> None:
        """Parse owner/repo with version tag."""
        result = _parse_github_source("user/repo@v1.0.0")
        assert result.name == "repo"
        assert result.ref == "v1.0.0"

    def test_single_name(self) -> None:
        """Parse single name without slash."""
        result = _parse_github_source("just-a-name")
        assert result.source_type == PluginSource.GITHUB
        assert result.name == "just-a-name"
        assert result.url == "https://github.com/just-a-name"


class TestParsedSourceDataclass:
    """Tests for ParsedSource dataclass fields."""

    def test_all_optional_fields_default_none(self) -> None:
        """All optional fields default to None."""
        result = parse_source("npm:pkg")
        assert result.version is None
        assert result.url is None
        assert result.ref is None
        assert result.subdir is None
        assert result.registry is None

    def test_npm_fields(self) -> None:
        """NPM source populates name and version."""
        result = parse_source("npm:pkg@1.0.0")
        assert result.name == "pkg"
        assert result.version == "1.0.0"

    def test_github_url_construction(self) -> None:
        """GitHub source constructs HTTPS URL."""
        result = parse_source("github:user/repo@v1.0")
        assert result.source_type == PluginSource.GITHUB
        assert result.url == "https://github.com/user/repo"
