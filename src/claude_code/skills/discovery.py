"""Dynamic skill discovery during file operations.

Corresponds to TypeScript's dynamic skill discovery in
src/skills/loadSkillsDir.ts (discoverSkillDirsForPaths, addSkillDirectories).
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from .definition import SkillDefinition, SkillSource
from .parser import parse_frontmatter
from .registry import SkillRegistry

if TYPE_CHECKING:
    pass


# =============================================================================
# State
# =============================================================================

# Track discovered skill directories
_discovered_dirs: set[str] = set()

# Dynamic skills discovered during file operations
_dynamic_skills: dict[str, SkillDefinition] = {}

# Callbacks for when dynamic skills are loaded
_load_callbacks: list[Callable[[], None]] = []


# =============================================================================
# Discovery
# =============================================================================


def discover_skill_dirs_for_paths(
    file_paths: list[str],
    cwd: str,
) -> list[str]:
    """Discover skill directories by walking up from file paths.

    Only discovers directories below cwd. CWD-level skills are
    loaded at startup, so we only discover nested ones.

    Args:
        file_paths: File paths to check for nearby skill directories.
        cwd: Current working directory (upper bound for discovery).

    Returns:
        List of newly discovered skill directory paths, sorted deepest first.

    Corresponds to TypeScript's discoverSkillDirsForPaths().
    """
    new_dirs: list[str] = []
    cwd_normalized = os.path.abspath(cwd)

    for file_path in file_paths:
        # Start from the file's parent directory
        current_dir = os.path.dirname(os.path.abspath(file_path))

        # Walk up to cwd but NOT including cwd itself
        while current_dir.startswith(cwd_normalized + os.sep) or current_dir == cwd_normalized:
            # Stop at cwd level
            if current_dir == cwd_normalized:
                break

            skill_dir = os.path.join(current_dir, ".claude", "skills")

            # Skip if we've already checked this path
            if skill_dir in _discovered_dirs:
                break

            _discovered_dirs.add(skill_dir)

            if os.path.isdir(skill_dir):
                # Check if gitignored (simplified: just check existence)
                if not _is_gitignored(current_dir, cwd_normalized):
                    new_dirs.append(skill_dir)

            # Move to parent
            parent = os.path.dirname(current_dir)
            if parent == current_dir:
                break
            current_dir = parent

    # Sort by path depth (deepest first)
    new_dirs.sort(key=lambda d: d.count(os.sep), reverse=True)
    return new_dirs


def _is_gitignored(dir_path: str, cwd: str) -> bool:
    """Check if a directory is gitignored.

    Simplified implementation - the TypeScript version uses git check-ignore.

    Args:
        dir_path: Directory path to check.
        cwd: Current working directory.

    Returns:
        True if the directory is gitignored.
    """
    # Try to use git check-ignore if available
    try:
        import subprocess

        result = subprocess.run(
            ["git", "check-ignore", "-q", dir_path],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        # Fall through to False
        pass

    return False


def add_skill_directories(
    dirs: list[str],
    registry: SkillRegistry | None = None,
) -> None:
    """Load skills from the given directories and merge into dynamic skills.

    Skills from directories closer to the file (deeper paths) take precedence.

    Args:
        dirs: Skill directory paths to load from (should be sorted deepest first).
        registry: Optional registry to also register skills into.

    Corresponds to TypeScript's addSkillDirectories().
    """
    if not dirs:
        return

    previous_count = len(_dynamic_skills)

    for dir_path in reversed(dirs):
        skills = _load_skills_from_dir(dir_path)
        for skill in skills:
            _dynamic_skills[skill.name] = skill
            if registry is not None:
                registry.register(skill)

    new_count = len(_dynamic_skills)
    if new_count > previous_count:
        _emit_skills_loaded()


def _load_skills_from_dir(dir_path: str) -> list[SkillDefinition]:
    """Load skills from a .claude/skills/ directory.

    Supports directory format: skill-name/SKILL.md

    Args:
        dir_path: Path to the skills directory.

    Returns:
        List of loaded skill definitions.
    """
    skills: list[SkillDefinition] = []
    base_path = Path(dir_path)

    if not base_path.is_dir():
        return skills

    try:
        entries = list(base_path.iterdir())
    except OSError:
        return skills

    for entry in entries:
        if not entry.is_dir():
            continue

        skill_file = entry / "SKILL.md"
        if not skill_file.is_file():
            continue

        try:
            content = skill_file.read_text()
        except OSError:
            continue

        skill = _parse_skill_file(skill_file, content, SkillSource.PROJECT)
        if skill:
            skills.append(skill)

    return skills


def _parse_skill_file(
    skill_file: Path,
    content: str,
    source: SkillSource,
) -> SkillDefinition | None:
    """Parse a SKILL.md file into a SkillDefinition.

    Args:
        skill_file: Path to the SKILL.md file.
        content: File content.
        source: Skill source type.

    Returns:
        Parsed skill definition or None.
    """
    fm, markdown = parse_frontmatter(content)

    skill_name = skill_file.parent.name
    skill_root = str(skill_file.parent)

    # Parse paths for conditional activation
    paths_raw = fm.get("paths")
    paths: list[str] | None = (
        [str(p) for p in paths_raw] if isinstance(paths_raw, list) else paths_raw.split()
    ) if paths_raw else None

    # Parse allowed tools
    allowed_tools_raw = fm.get("allowed-tools")
    allowed_tools: list[str] = []
    if allowed_tools_raw:
        if isinstance(allowed_tools_raw, list):
            allowed_tools = [str(t) for t in allowed_tools_raw]
        else:
            allowed_tools = allowed_tools_raw.split()

    skill = SkillDefinition(
        name=skill_name,
        description=str(fm.get("description", "")),
        when_to_use=fm.get("when_to_use"),
        argument_hint=fm.get("argument-hint"),
        allowed_tools=allowed_tools,
        instructions=markdown.strip(),
        _path=skill_file.parent,
        _loaded=True,
        source=source,
        skill_root=skill_root,
        loaded_from="skills",
        user_invocable=fm.get("user-invocable", True),
        model=fm.get("model"),
        disable_model_invocation=fm.get("disable-model-invocation", False),
        context=fm.get("context", "inline"),
        agent=fm.get("agent"),
        effort=fm.get("effort"),
        paths=paths,
        hooks=fm.get("hooks"),
        version=fm.get("version"),
        content_length=len(markdown.strip()),
    )

    return skill


def get_dynamic_skills() -> list[SkillDefinition]:
    """Get all dynamically discovered skills.

    Returns:
        List of dynamic skill definitions.

    Corresponds to TypeScript's getDynamicSkills().
    """
    return list(_dynamic_skills.values())


def get_dynamic_skill(name: str) -> SkillDefinition | None:
    """Get a dynamically discovered skill by name.

    Args:
        name: Skill name.

    Returns:
        Skill definition or None.
    """
    return _dynamic_skills.get(name)


def on_dynamic_skills_loaded(callback: Callable[[], None]) -> Callable[[], None]:
    """Register a callback to be invoked when dynamic skills are loaded.

    Args:
        callback: Function to call when skills are loaded.

    Returns:
        Unsubscribe function.

    Corresponds to TypeScript's onDynamicSkillsLoaded().
    """
    _load_callbacks.append(callback)

    def unsubscribe() -> None:
        _load_callbacks.remove(callback)

    return unsubscribe


def _emit_skills_loaded() -> None:
    """Emit the skills-loaded event to all callbacks."""
    for callback in _load_callbacks:
        with contextlib.suppress(Exception):
            callback()


# =============================================================================
# Clear State (for testing)
# =============================================================================


def clear_dynamic_skills() -> None:
    """Clear all dynamic skill state (for testing).

    Corresponds to TypeScript's clearDynamicSkills().
    """
    global _discovered_dirs, _dynamic_skills
    _discovered_dirs.clear()
    _dynamic_skills.clear()
    _load_callbacks.clear()


def get_discovered_dir_count() -> int:
    """Get the number of discovered skill directories.

    Returns:
        Number of directories in the discovery cache.
    """
    return len(_discovered_dirs)


def get_dynamic_skill_count() -> int:
    """Get the number of dynamic skills.

    Returns:
        Number of dynamically loaded skills.
    """
    return len(_dynamic_skills)
