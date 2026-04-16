"""Conditional skills with path-based activation.

Corresponds to TypeScript's conditional skill activation in
src/skills/loadSkillsDir.ts (activateConditionalSkillsForPaths).
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .definition import SkillDefinition, path_matches_glob

if TYPE_CHECKING:
    pass


# =============================================================================
# Conditional Skill
# =============================================================================


@dataclass
class ConditionalSkill:
    """A skill with path-based activation conditions.

    Skills with `paths` frontmatter are conditionally activated when
    matching files are touched during file operations.

    Corresponds to the TypeScript concept of conditional skills stored
    in the conditionalSkills Map.
    """

    definition: SkillDefinition
    paths: list[str] = field(default_factory=list)
    is_activated: bool = False
    activated_at: str | None = None

    @property
    def name(self) -> str:
        """Skill name."""
        return self.definition.name

    @property
    def description(self) -> str:
        """Skill description."""
        return self.definition.description

    def matches_path(self, file_path: str, cwd: str) -> bool:
        """Check if a file path matches any of this skill's patterns.

        Args:
            file_path: The file path to check.
            cwd: Current working directory for relative matching.

        Returns:
            True if the path matches any pattern.
        """
        # Compute relative path for matching
        rel_path = self._to_relative_path(file_path, cwd)

        return any(path_matches_glob(rel_path, pattern) for pattern in self.paths)

    def _to_relative_path(self, file_path: str, cwd: str) -> str:
        """Convert an absolute path to relative from cwd.

        Args:
            file_path: Absolute or relative file path.
            cwd: Current working directory.

        Returns:
            Path relative to cwd.
        """
        if os.path.isabs(file_path):
            try:
                return os.path.relpath(file_path, cwd)
            except ValueError:
                # Different drives on Windows
                return file_path
        return file_path

    def activate(self) -> None:
        """Activate this conditional skill."""
        import datetime

        self.is_activated = True
        self.activated_at = datetime.datetime.now(datetime.UTC).isoformat()

    def __repr__(self) -> str:
        """String representation."""
        status = "activated" if self.is_activated else "pending"
        return f"ConditionalSkill({self.name}, {status})"


# =============================================================================
# Conditional Skill Store
# =============================================================================


class ConditionalSkillStore:
    """Store for managing conditional skills.

    Maintains pending conditional skills and activates them when
    matching file paths are operated on.
    """

    def __init__(self) -> None:
        """Initialize the conditional skill store."""
        self._skills: dict[str, ConditionalSkill] = {}
        self._activated_names: set[str] = set()
        self._activation_callbacks: list[
            Callable[[str, ConditionalSkill], None]
        ] = []

    def add(self, skill: SkillDefinition) -> None:
        """Add a conditional skill to the store.

        Args:
            skill: Skill definition with paths frontmatter.
        """
        if not skill.paths:
            return

        if skill.name in self._skills:
            return  # Already added

        conditional = ConditionalSkill(
            definition=skill,
            paths=list(skill.paths),
        )
        self._skills[skill.name] = conditional

    def remove(self, name: str) -> None:
        """Remove a conditional skill from the store.

        Args:
            name: Skill name.
        """
        if name in self._skills:
            del self._skills[name]

    def get(self, name: str) -> ConditionalSkill | None:
        """Get a conditional skill by name.

        Args:
            name: Skill name.

        Returns:
            Conditional skill or None.
        """
        return self._skills.get(name)

    def get_all(self) -> list[ConditionalSkill]:
        """Get all conditional skills.

        Returns:
            List of all conditional skills (pending and activated).
        """
        return list(self._skills.values())

    def get_pending(self) -> list[ConditionalSkill]:
        """Get all pending (not yet activated) conditional skills.

        Returns:
            List of pending conditional skills.
        """
        return [s for s in self._skills.values() if not s.is_activated]

    def get_activated(self) -> list[ConditionalSkill]:
        """Get all activated conditional skills.

        Returns:
            List of activated conditional skills.
        """
        return [s for s in self._skills.values() if s.is_activated]

    def activate_for_paths(
        self,
        file_paths: list[str],
        cwd: str,
    ) -> list[str]:
        """Activate conditional skills whose paths match.

        Checks each pending conditional skill against the given file paths.
        Activates any skill whose patterns match at least one path.

        Args:
            file_paths: File paths being operated on.
            cwd: Current working directory.

        Returns:
            List of newly activated skill names.

        Corresponds to TypeScript's activateConditionalSkillsForPaths().
        """
        activated: list[str] = []

        for name, skill in list(self._skills.items()):
            if skill.is_activated:
                continue

            if not skill.paths:
                continue

            # Check if any path matches
            for file_path in file_paths:
                if skill.matches_path(file_path, cwd):
                    skill.activate()
                    self._activated_names.add(name)
                    activated.append(name)

                    # Fire callbacks
                    for callback in self._activation_callbacks:
                        with contextlib.suppress(Exception):
                            callback(name, skill)

                    break

        return activated

    def is_activated(self, name: str) -> bool:
        """Check if a conditional skill has been activated.

        Args:
            name: Skill name.

        Returns:
            True if the skill has been activated.
        """
        return name in self._activated_names

    def on_activate(
        self,
        callback: Callable[[str, ConditionalSkill], None],
    ) -> Callable[[], None]:
        """Register a callback for skill activation events.

        Args:
            callback: Function called when a skill is activated.

        Returns:
            Unsubscribe function.
        """
        self._activation_callbacks.append(callback)

        def unsubscribe() -> None:
            self._activation_callbacks.remove(callback)

        return unsubscribe

    def clear(self) -> None:
        """Clear all conditional skills."""
        self._skills.clear()
        self._activated_names.clear()
        self._activation_callbacks.clear()

    def __len__(self) -> int:
        """Number of conditional skills."""
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        """Check if a skill is in the store."""
        return name in self._skills


# =============================================================================
# Helper Functions
# =============================================================================


def should_activate_skill(
    skill: ConditionalSkill,
    touched_paths: list[str],
    cwd: str,
) -> bool:
    """Check if a conditional skill should be activated.

    Args:
        skill: The conditional skill to check.
        touched_paths: File paths being operated on.
        cwd: Current working directory.

    Returns:
        True if the skill should be activated.

    Corresponds to TypeScript's shouldActivateSkill logic.
    """
    if skill.is_activated:
        return False

    return any(skill.matches_path(path, cwd) for path in touched_paths)


def create_conditional_skill(
    skill: SkillDefinition,
) -> ConditionalSkill | None:
    """Create a conditional skill from a skill definition.

    Args:
        skill: Skill definition with paths frontmatter.

    Returns:
        ConditionalSkill if the definition has paths, None otherwise.
    """
    if not skill.paths:
        return None

    return ConditionalSkill(
        definition=skill,
        paths=list(skill.paths),
    )


def normalize_path_patterns(patterns: list[str]) -> list[str]:
    """Normalize path patterns for matching.

    Removes trailing /** suffix since the library treats 'path' as
    matching both the path itself and everything inside it.

    Args:
        patterns: List of glob patterns.

    Returns:
        Normalized patterns.

    Example:
        >>> normalize_path_patterns(["**/*.py", "src/**/*.ts"])
        ['*.py', 'src/**/*.ts']
    """
    normalized: list[str] = []
    for pattern in patterns:
        # Remove trailing /** for match-all
        if pattern.endswith("/**"):
            pattern = pattern[:-3]
        normalized.append(pattern)
    return normalized


# =============================================================================
# Global Store
# =============================================================================

_global_store: ConditionalSkillStore | None = None


def get_conditional_store() -> ConditionalSkillStore:
    """Get the global conditional skill store.

    Returns:
        The global ConditionalSkillStore singleton.
    """
    global _global_store
    if _global_store is None:
        _global_store = ConditionalSkillStore()
    return _global_store
