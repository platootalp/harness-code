"""Skill registry for managing skill discovery, registration, and lookup.

Corresponds to TypeScript's skills registry in src/skills/loadSkillsDir.ts.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .definition import SkillDefinition, SkillSource
from .parser import parse_allowed_tools, parse_argument_names, parse_frontmatter

# =============================================================================
# Skill Registry
# =============================================================================


class SkillRegistry:
    """Registry for managing skills with progressive loading.

    Supports discovery from directories, registration, lookup, and execution.
    Handles conditional skills (path-based activation) and dynamic discovery.

    Corresponds to TypeScript's getSkillDirCommands() and related functions
    in src/skills/loadSkillsDir.ts.
    """

    def __init__(
        self,
        tool_registry: Any | None = None,
        executor: Any | None = None,
    ) -> None:
        """Initialize the skill registry.

        Args:
            tool_registry: Optional tool registry for integration.
            executor: Optional skill executor for running skills.
        """
        self._skills: dict[str, SkillDefinition] = {}
        self._aliases: dict[str, str] = {}
        self._tool_registry = tool_registry
        self._executor = executor
        self._conditional_skills: dict[str, SkillDefinition] = {}
        self._activated_conditional_names: set[str] = set()
        self._discovered_dirs: set[str] = set()

    # -------------------------------------------------------------------------
    # Discovery
    # -------------------------------------------------------------------------

    def discover(self, skills_dir: Path | str) -> list[SkillDefinition]:
        """Discover skills from a directory.

        Supports both directory format (skill-name/SKILL.md) and
        legacy single .md file format.

        Args:
            skills_dir: Path to skills directory.

        Returns:
            List of discovered skill definitions.
        """
        skills_dir = Path(skills_dir)

        if not skills_dir.is_dir():
            return []

        discovered: list[SkillDefinition] = []

        try:
            entries = list(skills_dir.iterdir())
        except OSError:
            return []

        for entry in entries:
            if entry.is_dir():
                # Directory format: skill-name/SKILL.md
                skill_file = entry / "SKILL.md"
                if skill_file.is_file():
                    skill = self._load_skill_from_file(
                        skill_file, SkillSource.PROJECT
                    )
                    if skill:
                        discovered.append(skill)
            elif entry.is_file() and entry.suffix == ".md":
                # Legacy single file format
                skill = self._load_skill_from_file(entry, SkillSource.PROJECT)
                if skill:
                    discovered.append(skill)

        return discovered

    def _load_skill_from_file(
        self,
        skill_file: Path,
        source: SkillSource,
        loaded_from: str | None = None,
    ) -> SkillDefinition | None:
        """Load a skill definition from a SKILL.md file.

        Args:
            skill_file: Path to the SKILL.md file.
            source: Source type for the skill.
            loaded_from: Optional loaded_from sub-type.

        Returns:
            Loaded skill definition or None on error.
        """
        try:
            content = skill_file.read_text()
        except OSError:
            return None

        fm, markdown = parse_frontmatter(content)

        # Determine skill name from directory or filename
        if source == SkillSource.PROJECT:
            skill_name = skill_file.parent.name
        else:
            skill_name = fm.get("name") or skill_file.stem

        # Parse fields
        allowed_tools_raw = fm.get("allowed-tools")
        allowed_tools = parse_allowed_tools(allowed_tools_raw) if allowed_tools_raw else []
        arguments_raw = fm.get("arguments")
        arguments = parse_argument_names(arguments_raw) if arguments_raw else []

        # Determine skill root (parent directory)
        skill_root = str(skill_file.parent) if source == SkillSource.PROJECT else None

        # Parse paths for conditional activation
        paths_raw = fm.get("paths")
        paths: list[str] | None = None
        if paths_raw:
            if isinstance(paths_raw, list):
                paths = [str(p) for p in paths_raw]
            else:
                paths = paths_raw.split()

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
            loaded_from=loaded_from or source.value,
            user_invocable=fm.get("user-invocable", True),
            model=fm.get("model"),
            disable_model_invocation=fm.get("disable-model-invocation", False),
            context=fm.get("context", "inline"),
            agent=fm.get("agent"),
            effort=fm.get("effort"),
            paths=paths,
            hooks=fm.get("hooks"),
            version=fm.get("version"),
            arguments=arguments,
            content_length=len(markdown.strip()),
        )

        # Handle conditional skills
        if paths and skill_name not in self._activated_conditional_names:
            self._conditional_skills[skill_name] = skill
        else:
            self.register(skill)

        return skill

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register(self, skill: SkillDefinition) -> None:
        """Register a skill and its aliases.

        Args:
            skill: The skill definition to register.
        """
        if skill.name in self._skills:
            # Skip duplicate
            return

        self._skills[skill.name] = skill

        # Register aliases
        for alias in skill.aliases:
            self._aliases[alias] = skill.name

    def register_alias(self, skill_name: str, alias: str) -> None:
        """Register an alias for an existing skill.

        Args:
            skill_name: The skill name to alias.
            alias: The alias name.
        """
        if skill_name not in self._skills:
            raise KeyError(f"Skill not registered: {skill_name}")
        self._aliases[alias] = skill_name

    def unregister(self, name: str) -> SkillDefinition:
        """Unregister a skill by name.

        Args:
            name: Skill name or alias.

        Returns:
            The unregistered skill definition.
        """
        # Resolve alias
        if name in self._aliases:
            name = self._aliases.pop(name)

        # Remove from aliases
        to_remove = [a for a, n in self._aliases.items() if n == name]
        for alias in to_remove:
            del self._aliases[alias]

        return self._skills.pop(name)

    # -------------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------------

    def get(self, name: str) -> SkillDefinition | None:
        """Look up a skill by name or alias.

        Args:
            name: Skill name or alias.

        Returns:
            The skill definition or None if not found.
        """
        # Direct lookup
        if name in self._skills:
            return self._skills[name]

        # Alias lookup
        resolved = self._aliases.get(name)
        if resolved is not None:
            return self._skills.get(resolved)

        return None

    def has(self, name: str) -> bool:
        """Check if a skill is registered.

        Args:
            name: Skill name or alias.

        Returns:
            True if the skill is registered.
        """
        return self.get(name) is not None

    def get_required(self, name: str) -> SkillDefinition:
        """Look up a skill, raising if not found.

        Args:
            name: Skill name or alias.

        Returns:
            The skill definition.

        Raises:
            KeyError: If the skill is not registered.
        """
        skill = self.get(name)
        if skill is None:
            raise KeyError(f"Skill not registered: {name}")
        return skill

    # -------------------------------------------------------------------------
    # Listing
    # -------------------------------------------------------------------------

    def list_all(self) -> list[SkillDefinition]:
        """List all registered skills.

        Returns:
            List of skill definitions.
        """
        return list(self._skills.values())

    def list_names(self) -> list[str]:
        """List all registered skill names.

        Returns:
            List of skill names (not aliases).
        """
        return list(self._skills.keys())

    def list_enabled(self) -> list[SkillDefinition]:
        """List all enabled skills.

        Returns:
            List of enabled skill definitions.
        """
        return [s for s in self._skills.values() if s.check_enabled()]

    def list_user_invocable(self) -> list[SkillDefinition]:
        """List all user-invocable skills.

        Returns:
            List of user-invocable skill definitions.
        """
        return [
            s for s in self._skills.values() if s.user_invocable and not s.is_hidden
        ]

    def list_by_source(self, source: SkillSource) -> list[SkillDefinition]:
        """List skills by source.

        Args:
            source: The source type to filter by.

        Returns:
            List of skills from the specified source.
        """
        return [s for s in self._skills.values() if s.source == source]

    def filter(
        self,
        predicate: Callable[[SkillDefinition], bool],
    ) -> list[SkillDefinition]:
        """Filter skills by a predicate.

        Args:
            predicate: Function that takes a skill and returns bool.

        Returns:
            List of matching skill definitions.
        """
        return [s for s in self._skills.values() if predicate(s)]

    # -------------------------------------------------------------------------
    # Activation
    # -------------------------------------------------------------------------

    def activate(self, skill_name: str) -> SkillDefinition:
        """Activate a skill (load full content if lazy).

        Args:
            skill_name: Name of the skill to activate.

        Returns:
            The activated skill definition.

        Raises:
            KeyError: If the skill is not found.
        """
        skill = self.get(skill_name)
        if skill is None:
            raise KeyError(f"Skill not found: {skill_name}")

        skill.load_full()
        return skill

    def activate_conditional_for_paths(
        self, file_paths: list[str], cwd: str
    ) -> list[str]:
        """Activate conditional skills whose paths match.

        Args:
            file_paths: File paths being operated on.
            cwd: Current working directory (for relative matching).

        Returns:
            List of newly activated skill names.
        """
        activated: list[str] = []
        from .definition import path_matches_glob

        for name, skill in list(self._conditional_skills.items()):
            if not skill.paths:
                continue

            for file_path in file_paths:
                # Compute relative path
                if os.path.isabs(file_path):
                    try:
                        rel_path = os.path.relpath(file_path, cwd)
                    except ValueError:
                        rel_path = file_path
                else:
                    rel_path = file_path

                for pattern in skill.paths:
                    if path_matches_glob(rel_path, pattern):
                        # Activate this skill
                        skill.load_full()
                        self._skills[name] = skill
                        del self._conditional_skills[name]
                        self._activated_conditional_names.add(name)
                        activated.append(name)
                        break

        return activated

    def add_dynamic_skills(self, skills: list[SkillDefinition]) -> None:
        """Add dynamically discovered skills.

        Args:
            skills: List of skill definitions to add.
        """
        for skill in skills:
            self._skills[skill.name] = skill

    def clear_dynamic(self) -> None:
        """Clear all dynamic skill state (for testing)."""
        self._conditional_skills.clear()
        self._activated_conditional_names.clear()
        self._discovered_dirs.clear()

    # -------------------------------------------------------------------------
    # Schema Export
    # -------------------------------------------------------------------------

    def get_schemas(self) -> list[dict[str, Any]]:
        """Get JSON schemas for skill tools.

        Returns:
            List of skill tool input schemas.
        """
        schemas: list[dict[str, Any]] = []
        for skill in self._skills.values():
            if skill.user_invocable and not skill.is_hidden:
                schemas.append(
                    {
                        "name": skill.name,
                        "description": skill.description,
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "skill": {
                                    "type": "string",
                                    "description": f"Skill name. E.g., '{skill.name}'",
                                },
                                "args": {
                                    "type": "string",
                                    "description": "Optional arguments for the skill",
                                },
                            },
                            "required": ["skill"],
                        },
                    },
                )
        return schemas

    # -------------------------------------------------------------------------
    # Bulk Operations
    # -------------------------------------------------------------------------

    def merge(self, other: SkillRegistry) -> None:
        """Merge another registry into this one.

        Args:
            other: The other registry to merge.
        """
        for skill in other.list_all():
            self.register(skill)

    def clear(self) -> None:
        """Clear all registered skills."""
        self._skills.clear()
        self._aliases.clear()
        self._conditional_skills.clear()
        self._activated_conditional_names.clear()
        self._discovered_dirs.clear()

    def __len__(self) -> int:
        """Return the number of registered skills."""
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        """Check if a skill is registered."""
        return self.has(name)

    def __iter__(self):
        """Iterate over skill names."""
        return iter(self._skills)

    def __repr__(self) -> str:
        """String representation."""
        return f"SkillRegistry({len(self._skills)} skills)"


# =============================================================================
# Global Registry
# =============================================================================

_global_registry: SkillRegistry | None = None


def get_global_registry() -> SkillRegistry:
    """Get the global skill registry instance.

    Returns:
        The global SkillRegistry singleton.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry


def register_skill(skill: SkillDefinition) -> None:
    """Register a skill with the global registry.

    Args:
        skill: The skill definition to register.
    """
    get_global_registry().register(skill)


def get_skill(name: str) -> SkillDefinition | None:
    """Look up a skill from the global registry.

    Args:
        name: Skill name or alias.

    Returns:
        The skill definition or None if not found.
    """
    return get_global_registry().get(name)
