"""Plugin loader for discovering and loading plugins from various sources.

Handles loading plugins from:
- npm packages
- pip (Python) packages
- git repositories
- GitHub repositories
- Local filesystem paths

TypeScript equivalent: src/utils/plugins/pluginLoader.ts
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import LoadedPlugin, PluginManifest, PluginScope, PluginSource
from .manager import (
    PluginError,
    PluginLoadResult,
)
from .manifest import ManifestParseError, parse_manifest

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Source Parsing
# =============================================================================


@dataclass
class ParsedSource:
    """Parsed plugin source identifier.

    Attributes:
        source_type: The type of source (npm, pip, git, github, local).
        name: The plugin/package name.
        version: Optional version specifier.
        url: Full URL for git/github sources.
        ref: Branch, tag, or commit SHA for git sources.
        subdir: Subdirectory path for git-subdir sources.
        registry: Package registry URL for npm/pip sources.
    """

    source_type: PluginSource
    name: str
    version: str | None = None
    url: str | None = None
    ref: str | None = None
    subdir: str | None = None
    registry: str | None = None


def parse_source(source: str) -> ParsedSource:
    """Parse a plugin source string into a ParsedSource.

    Supported formats:
    - ``npm:package-name[@version]`` — NPM package
    - ``pip:package-name[==version]`` — Python package
    - ``git:https://...`` — Git repository
    - ``github:owner/repo[@ref]`` — GitHub repository
    - ``/path/to/plugin`` — Local path
    - ``name@marketplace`` — Marketplace plugin

    Args:
        source: The source string to parse.

    Returns:
        A ParsedSource with the decomposed source information.
    """
    source = source.strip()

    # npm: prefix
    if source.startswith("npm:"):
        return _parse_npm_source(source[4:])

    # pip: prefix
    if source.startswith("pip:"):
        return _parse_pip_source(source[4:])

    # git: prefix
    if source.startswith("git:"):
        return _parse_git_source(source)

    # github: prefix
    if source.startswith("github:"):
        return _parse_github_source(source[7:])

    # Local path
    if os.path.sep in source or source.startswith("."):
        return ParsedSource(
            source_type=PluginSource.LOCAL,
            name=os.path.basename(source.rstrip("/\\")),
            url=source,
        )

    # Marketplace plugin (name@marketplace)
    if "@" in source:
        parts = source.rsplit("@", 1)
        if len(parts) == 2 and "/" not in parts[1] and parts[1] != "builtin":
            # name@marketplace format
            return ParsedSource(
                source_type=PluginSource.MANAGED,
                name=parts[0],
                url=source,
            )

    # Default: treat as local path or managed plugin name
    return ParsedSource(
        source_type=PluginSource.LOCAL,
        name=os.path.basename(source.rstrip("/\\")) if os.path.sep in source else source,
        url=source,
    )


def _parse_npm_source(rest: str) -> ParsedSource:
    """Parse an npm: source string."""
    # package@version or just package
    at_pos = rest.rfind("@")
    if at_pos > 0:
        name = rest[:at_pos]
        version = rest[at_pos + 1:]
    else:
        name = rest
        version = None

    # Check for custom registry
    registry_match = re.search(r"--registry=(.+?)(?:\s|$)", name)
    if registry_match:
        registry = registry_match.group(1).rstrip("/")
        name = name.replace(f"--registry={registry}", "").strip()

    return ParsedSource(
        source_type=PluginSource.NPM,
        name=name,
        version=version,
        registry=registry_match.group(1).rstrip("/") if registry_match else None,
    )


def _parse_pip_source(rest: str) -> ParsedSource:
    """Parse a pip: source string."""
    # package==version or package>=version or just package
    version_match = re.search(r"(==|>=|<=|~=|>)", rest)
    if version_match:
        name = rest[:version_match.start()]
        version = rest[version_match.end():]
    else:
        name = rest
        version = None

    # Check for custom index URL
    index_match = re.search(r"--index-url=(.+?)(?:\s|--)", rest)
    registry = index_match.group(1).rstrip("/") if index_match else None

    return ParsedSource(
        source_type=PluginSource.PIP,
        name=name,
        version=version,
        registry=registry,
    )


def _parse_git_source(source: str) -> ParsedSource:
    """Parse a git: source string."""
    rest = source[4:]  # strip "git:"
    ref: str | None = None
    subdir: str | None = None

    # Extract ref (branch, tag, SHA) after '#'
    if "#" in rest:
        rest, ref = rest.rsplit("#", 1)

    # Extract subdirectory after "::"
    if "::" in rest:
        rest, subdir = rest.split("::", 1)

    # Extract version from name if present (e.g., package@version)
    name = os.path.basename(rest.rstrip("/\\"))
    if "@" in name and not name.startswith("@"):
        name = name.rsplit("@", 1)[0]

    return ParsedSource(
        source_type=PluginSource.GIT,
        name=name,
        url=rest,
        ref=ref,
        subdir=subdir,
    )


def _parse_github_source(rest: str) -> ParsedSource:
    """Parse a github: source string (owner/repo[@ref])."""
    ref: str | None = None

    # Extract ref after @
    if "@" in rest:
        rest, ref = rest.rsplit("@", 1)

    # Must be owner/repo format
    if "/" not in rest:
        return ParsedSource(
            source_type=PluginSource.GITHUB,
            name=rest,
            url=f"https://github.com/{rest}",
            ref=ref,
        )

    return ParsedSource(
        source_type=PluginSource.GITHUB,
        name=rest.split("/")[-1],
        url=f"https://github.com/{rest}",
        ref=ref,
    )


# =============================================================================
# Plugin Loader
# =============================================================================


class PluginLoader:
    """Loads plugins from various sources.

    Handles discovery, validation, and loading of plugins from
    npm, pip, git, GitHub, and local filesystem sources.

    Example:
        loader = PluginLoader(cache_dir="/path/to/cache")
        result = await loader.load_plugin("npm:my-plugin@1.0.0")
        if result.errors:
            for err in result.errors:
                print(f"Error: {err}")
        else:
            plugin = result.enabled[0]
    """

    def __init__(
        self,
        cache_dir: str | None = None,
        plugin_dir: str | None = None,
        *,
        timeout: float = 60.0,
    ) -> None:
        """Initialize the plugin loader.

        Args:
            cache_dir: Directory for cached plugin downloads. Defaults to
                ``~/.claude/plugins/cache/``.
            plugin_dir: Directory for installed plugins. Defaults to
                ``~/.claude/plugins/``.
            timeout: Timeout for network operations in seconds.
        """
        self._cache_dir = cache_dir or os.path.join(
            os.path.expanduser("~"), ".claude", "plugins", "cache"
        )
        self._plugin_dir = plugin_dir or os.path.join(
            os.path.expanduser("~"), ".claude", "plugins"
        )
        self._timeout = timeout
        self._loaded: dict[str, LoadedPlugin] = {}

    @property
    def cache_dir(self) -> str:
        """Return the cache directory path."""
        return self._cache_dir

    @property
    def plugin_dir(self) -> str:
        """Return the plugin directory path."""
        return self._plugin_dir

    # -------------------------------------------------------------------------
    # Source Loading
    # -------------------------------------------------------------------------

    async def load_plugin(self, source: str) -> PluginLoadResult:
        """Load a plugin from a source string.

        Args:
            source: Plugin source (e.g., ``npm:my-plugin@1.0.0``).

        Returns:
            PluginLoadResult with loaded plugin or errors.
        """
        parsed = parse_source(source)

        if parsed.source_type == PluginSource.NPM:
            return await self._load_npm_plugin(parsed)
        elif parsed.source_type == PluginSource.PIP:
            return await self._load_pip_plugin(parsed)
        elif parsed.source_type == PluginSource.GIT:
            return await self._load_git_plugin(parsed)
        elif parsed.source_type == PluginSource.GITHUB:
            return await self._load_github_plugin(parsed)
        elif parsed.source_type == PluginSource.LOCAL:
            return await self._load_local_plugin(parsed)
        else:
            return PluginLoadResult(
                errors=[self._make_error("generic-error", source, f"Unknown source type: {source}")]
            )

    async def load_plugin_from_path(self, path: str) -> PluginLoadResult:
        """Load a plugin from a filesystem path.

        Args:
            path: Absolute path to the plugin directory.

        Returns:
            PluginLoadResult with loaded plugin or errors.
        """
        parsed = ParsedSource(
            source_type=PluginSource.LOCAL,
            name=os.path.basename(path.rstrip("/\\")),
            url=path,
        )
        return await self._load_local_plugin(parsed)

    async def _load_npm_plugin(self, parsed: ParsedSource) -> PluginLoadResult:
        """Load a plugin from an npm package."""
        # npm packages need to be resolved through a marketplace.
        # For direct npm loading, we delegate to npm install.
        try:
            import subprocess

            pkg_name = parsed.name
            version = parsed.version or "latest"
            target_dir = self._get_cache_path(
                f"npm-{pkg_name}",
                version,
            )

            if os.path.exists(target_dir):
                return await self._load_from_dir(target_dir, parsed)

            # Run npm pack to download the package
            npm_args = ["npm", "pack", f"{pkg_name}@{version}"]
            if parsed.registry:
                npm_args.extend(["--registry", parsed.registry])

            result = subprocess.run(
                npm_args,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=self._cache_dir,
            )

            if result.returncode != 0:
                return PluginLoadResult(
                    errors=[self._make_error(
                        "network-error",
                        parsed.name,
                        f"npm: {parsed.name}",
                        f"https://registry.npmjs.org/{parsed.name}",
                        result.stderr or "npm install failed",
                    )]
                )

            # Extract the tarball
            tarball = result.stdout.strip().split("\n")[-1]
            tarball_path = os.path.join(self._cache_dir, tarball)

            try:
                os.makedirs(target_dir, exist_ok=True)
                subprocess.run(
                    ["tar", "-xzf", tarball_path, "-C", target_dir, "--strip-components=1"],
                    check=True,
                    capture_output=True,
                )
            finally:
                if os.path.exists(tarball_path):
                    os.remove(tarball_path)

            return await self._load_from_dir(target_dir, parsed)

        except subprocess.TimeoutExpired:
            return PluginLoadResult(
                errors=[self._make_error(
                    "git-timeout",
                    parsed.name,
                    f"pip: {parsed.name}",
                    parsed.url or "",
                    "install",
                )]
            )
        except Exception as e:
            return PluginLoadResult(
                errors=[self._make_error("generic-error", parsed.name, str(e))]
            )

    async def _load_pip_plugin(self, parsed: ParsedSource) -> PluginLoadResult:
        """Load a plugin from a pip package."""
        try:
            pkg_name = parsed.name
            version = parsed.version or ""
            target_dir = self._get_cache_path(f"pip-{pkg_name}", version)

            if os.path.exists(target_dir):
                return await self._load_from_dir(target_dir, parsed)

            # Use pip download to get the package
            pip_args = ["pip", "download", pkg_name]
            if version:
                pip_args.append(version)
            if parsed.registry:
                pip_args.extend(["--index-url", parsed.registry])

            result = subprocess.run(
                pip_args,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=self._cache_dir,
            )

            if result.returncode != 0:
                return PluginLoadResult(
                    errors=[self._make_error(
                        "network-error",
                        parsed.name,
                        f"pip: {parsed.name}",
                        parsed.registry or "https://pypi.org",
                        result.stderr or "pip download failed",
                    )]
                )

            return await self._load_from_dir(target_dir, parsed)

        except subprocess.TimeoutExpired:
            return PluginLoadResult(
                errors=[self._make_error(
                    "git-timeout",
                    parsed.name,
                    f"pip: {parsed.name}",
                    parsed.url or "",
                    "install",
                )]
            )
        except Exception as e:
            return PluginLoadResult(
                errors=[self._make_error("generic-error", parsed.name, str(e))]
            )

    async def _load_git_plugin(self, parsed: ParsedSource) -> PluginLoadResult:
        """Load a plugin from a git repository."""
        if not parsed.url:
            return PluginLoadResult(
                errors=[self._make_error("generic-error", parsed.name, "git URL required")]
            )

        target_dir = self._get_cache_path(
            f"git-{parsed.name}",
            parsed.ref or "latest",
        )

        if os.path.exists(target_dir):
            return await self._load_from_dir(target_dir, parsed)

        try:
            # Clone the repository
            git_args = ["git", "clone"]
            if parsed.ref:
                git_args.extend(["--branch", parsed.ref])
            git_args.extend(["--depth", "1", parsed.url, target_dir])

            result = subprocess.run(
                git_args,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )

            if result.returncode != 0:
                if "authentication" in result.stderr.lower():
                    return PluginLoadResult(
                        errors=[self._make_error(
                            "git-auth-failed",
                            parsed.name,
                            f"git: {parsed.url}",
                            parsed.url,
                            "https",
                        )]
                    )
                return PluginLoadResult(
                    errors=[self._make_error(
                        "network-error",
                        parsed.name,
                        f"git: {parsed.url}",
                        parsed.url,
                        result.stderr or "git clone failed",
                    )]
                )

            # Handle subdirectory
            if parsed.subdir:
                subdir_path = os.path.join(target_dir, parsed.subdir)
                if not os.path.exists(subdir_path):
                    return PluginLoadResult(
                        errors=[self._make_error(
                            "path-not-found",
                            parsed.name,
                            f"git: {parsed.url}::{parsed.subdir}",
                            subdir_path,
                            "subdir",
                        )]
                    )
                target_dir = subdir_path

            return await self._load_from_dir(target_dir, parsed)

        except subprocess.TimeoutExpired:
            return PluginLoadResult(
                errors=[self._make_error(
                    "git-timeout",
                    parsed.name,
                    f"git: {parsed.url}",
                    parsed.url,
                    "clone",
                )]
            )
        except Exception as e:
            return PluginLoadResult(
                errors=[self._make_error("generic-error", parsed.name, str(e))]
            )

    async def _load_github_plugin(self, parsed: ParsedSource) -> PluginLoadResult:
        """Load a plugin from a GitHub repository."""
        if not parsed.url:
            return PluginLoadResult(
                errors=[self._make_error("generic-error", parsed.name, "GitHub URL required")]
            )

        # Convert github:owner/repo[@ref] to git URL
        git_source = ParsedSource(
            source_type=PluginSource.GITHUB,
            name=parsed.name,
            url=parsed.url,
            ref=parsed.ref,
            subdir=parsed.subdir,
        )
        return await self._load_git_plugin(git_source)

    async def _load_local_plugin(self, parsed: ParsedSource) -> PluginLoadResult:
        """Load a plugin from a local filesystem path."""
        path = parsed.url or parsed.name

        if not os.path.exists(path):
            return PluginLoadResult(
                errors=[self._make_error(
                    "path-not-found",
                    parsed.name,
                    f"local: {path}",
                    path,
                    "root",
                )]
            )

        if not os.path.isdir(path):
            return PluginLoadResult(
                errors=[self._make_error(
                    "path-not-found",
                    parsed.name,
                    f"local: {path}",
                    path,
                    "root",
                )]
            )

        return await self._load_from_dir(path, parsed)

    # -------------------------------------------------------------------------
    # Manifest Loading
    # -------------------------------------------------------------------------

    async def _load_from_dir(
        self,
        path: str,
        parsed: ParsedSource,
    ) -> PluginLoadResult:
        """Load a plugin from a directory.

        Args:
            path: Path to the plugin directory.
            parsed: The parsed source information.

        Returns:
            PluginLoadResult with loaded plugin or errors.
        """
        manifest_path = os.path.join(path, "plugin.json")

        if not os.path.exists(manifest_path):
            # No manifest — treat directory as plugin root with minimal manifest
            manifest = PluginManifest(
                name=parsed.name,
                description="",
            )
        else:
            # Load and parse manifest
            manifest_result = self._load_manifest(manifest_path, parsed.name)
            if isinstance(manifest_result, PluginError):
                return PluginLoadResult(errors=[manifest_result])
            manifest = manifest_result

        plugin = LoadedPlugin(
            name=manifest.name,
            manifest=manifest,
            path=path,
            source=parsed.url or parsed.name,
            repository=parsed.url or parsed.name,
            enabled=True,
            is_builtin=False,
            scope=PluginScope.USER,
            source_type=parsed.source_type,
        )

        return PluginLoadResult(enabled=[plugin])

    def _load_manifest(
        self,
        manifest_path: str,
        plugin_name: str,
    ) -> PluginManifest | PluginError:
        """Load and parse a plugin.json manifest.

        Args:
            manifest_path: Path to the plugin.json file.
            plugin_name: Plugin name for error messages.

        Returns:
            Parsed PluginManifest or a PluginError.
        """
        try:
            return parse_manifest(Path(manifest_path))
        except ManifestParseError as e:
            msg = str(e)
            if "validation failed" in msg:
                return self._make_error(
                    "manifest-validation-error",
                    plugin_name,
                    manifest_path,
                    [msg],
                )
            return self._make_error(
                "manifest-parse-error",
                plugin_name,
                manifest_path,
                msg,
            )

    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------

    def _get_cache_path(self, prefix: str, version: str | None) -> str:
        """Get the cache path for a downloaded plugin.

        Args:
            prefix: Cache key prefix (e.g., npm-package-name).
            version: Version string.

        Returns:
            Absolute path to the cache directory.
        """
        sanitized = re.sub(r"[^a-zA-Z0-9\-_.]", "-", f"{prefix}-{version or 'latest'}")
        return os.path.join(self._cache_dir, sanitized)

    def clear_cache(self, plugin_name: str | None = None) -> None:
        """Clear the plugin cache.

        Args:
            plugin_name: If provided, only clear cache for this plugin.
                If None, clear the entire cache directory.
        """
        if plugin_name:
            # Clear specific plugin cache
            for item in os.listdir(self._cache_dir):
                if plugin_name in item:
                    path = os.path.join(self._cache_dir, item)
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        os.remove(path)
        else:
            # Clear entire cache
            if os.path.exists(self._cache_dir):
                shutil.rmtree(self._cache_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Error Factory
    # -------------------------------------------------------------------------

    def _make_error(
        self,
        error_type: str,
        plugin: str | None,
        *args: Any,
    ) -> PluginError:
        """Create a plugin error of the appropriate type."""
        error: dict[str, Any] = {
            "type": error_type,
            "source": "plugin-loader",
            "plugin": plugin,
        }

        if error_type == "generic-error":
            error["error"] = args[0] if args else "Unknown error"
        elif error_type == "path-not-found":
            error["source"] = args[0] if args else error["source"]
            error["path"] = args[1] if len(args) > 1 else ""
            error["component"] = args[2] if len(args) > 2 else ""
        elif error_type == "git-auth-failed":
            error["git_url"] = args[0] if args else ""
            error["auth_type"] = args[1] if len(args) > 1 else "https"
        elif error_type == "git-timeout":
            error["git_url"] = args[0] if args else ""
            error["operation"] = args[1] if len(args) > 1 else "clone"
        elif error_type == "network-error":
            error["url"] = args[0] if args else ""
            error["details"] = args[1] if len(args) > 1 else ""
        elif error_type == "manifest-parse-error":
            error["manifest_path"] = args[0] if args else ""
            error["parse_error"] = args[1] if len(args) > 1 else ""
        elif error_type == "manifest-validation-error":
            error["manifest_path"] = args[0] if args else ""
            error["validation_errors"] = args[1] if len(args) > 1 and isinstance(args[1], list) else []

        return error  # type: ignore[return-value]
