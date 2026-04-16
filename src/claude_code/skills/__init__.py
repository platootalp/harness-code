"""Skills system for Claude Code.

Provides skill registration, discovery, and execution capabilities.
"""

from __future__ import annotations

from .definition import (
    SkillDefinition,
    SkillFrontmatter,
    SkillParameter,
    SkillSource,
)
from .executor import SkillExecutor
from .registry import SkillRegistry, get_global_registry

__all__ = [
    "SkillDefinition",
    "SkillFrontmatter",
    "SkillParameter",
    "SkillSource",
    "SkillExecutor",
    "SkillRegistry",
    "get_global_registry",
]
