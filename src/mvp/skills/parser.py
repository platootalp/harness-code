"""SKILL.md parser - parses YAML frontmatter + Markdown content."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Pattern to match YAML frontmatter: --- ... ---
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class SkillParameter:
    """A skill parameter definition."""
    name: str
    type: str  # string, number, boolean
    description: str = ""
    required: bool = False


@dataclass
class SkillDefinition:
    """Parsed skill definition from SKILL.md."""
    name: str
    description: str
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # allowed-tools: list of pre-approved tools for this skill
    allowed_tools: list[str] = field(default_factory=list)

    # Full content (loaded on activation)
    instructions: str = ""

    # Progressive loading: only loaded on activation
    _loaded: bool = False

    # Optional parameters for skill invocation
    parameters: list[SkillParameter] = field(default_factory=list)

    # Optional scripts/references/assets paths
    scripts_path: Path | None = None
    references_path: Path | None = None
    assets_path: Path | None = None


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from SKILL.md content.

    Args:
        content: Raw SKILL.md file content.

    Returns:
        Tuple of (frontmatter dict, remaining markdown content).
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    import yaml
    fm_text = match.group(1)
    frontmatter = yaml.safe_load(fm_text) or {}
    markdown = content[match.end():]
    return frontmatter, markdown


def parse_skill_md(skill_path: Path) -> SkillDefinition:
    """
    Parse a SKILL.md file into a SkillDefinition.

    Performs progressive loading:
    - Phase 1 (always): name, description, allowed-tools, metadata
    - Phase 2 (on activate): full instructions content

    Args:
        skill_path: Path to the skill directory (contains SKILL.md).

    Returns:
        A partially-loaded SkillDefinition (instructions loaded on demand).
    """
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

    raw_content = skill_md.read_text()
    frontmatter, markdown = parse_frontmatter(raw_content)

    name = frontmatter.get("name", skill_path.name)
    description = frontmatter.get("description", "")
    license = frontmatter.get("license")
    compatibility = frontmatter.get("compatibility")
    metadata = frontmatter.get("metadata", {})

    # Parse allowed-tools: space-separated in the frontmatter string
    allowed_tools_raw = frontmatter.get("allowed-tools", "")
    if isinstance(allowed_tools_raw, str):
        # e.g., "Bash(git:*) Read Glob"
        allowed_tools = _parse_allowed_tools(allowed_tools_raw)
    else:
        allowed_tools = list(allowed_tools_raw) if allowed_tools_raw else []

    # Parse optional parameters from metadata
    parameters = []
    for p in metadata.get("parameters", []):
        parameters.append(SkillParameter(
            name=p.get("name", ""),
            type=p.get("type", "string"),
            description=p.get("description", ""),
            required=p.get("required", False),
        ))

    skill = SkillDefinition(
        name=name,
        description=description,
        license=license,
        compatibility=compatibility,
        metadata=metadata,
        allowed_tools=allowed_tools,
        instructions="",  # loaded on activation
        _loaded=False,
        parameters=parameters,
    )

    # Set optional subdirectory paths
    if (skill_path / "scripts").exists():
        skill.scripts_path = skill_path / "scripts"
    if (skill_path / "references").exists():
        skill.references_path = skill_path / "references"
    if (skill_path / "assets").exists():
        skill.assets_path = skill_path / "assets"

    return skill


def _parse_allowed_tools(raw: str) -> list[str]:
    """
    Parse allowed-tools string into a list of tool names.

    Examples:
        "Bash(git:*) Read Glob"  -> ["Bash", "Read", "Glob"]
        "Bash(git:*) Read"       -> ["Bash", "Read"]
        "Read Glob"              -> ["Read", "Glob"]

    Supports glob patterns inside parentheses as filters.
    """
    if not raw.strip():
        return []

    import re
    tools = []
    # Match tool names optionally followed by (glob_pattern)
    pattern = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\([^)]*\))?")
    for match in pattern.finditer(raw):
        tools.append(match.group(1))
    return tools


def load_full_skill(skill_def: SkillDefinition, skill_path: Path) -> SkillDefinition:
    """
    Load the full skill content (instructions + references) on activation.

    Args:
        skill_def: The partially-loaded skill definition.
        skill_path: Path to the skill directory.

    Returns:
        The fully-loaded SkillDefinition.
    """
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        raw_content = skill_md.read_text()
        _, markdown = parse_frontmatter(raw_content)
        skill_def.instructions = markdown.strip()
    skill_def._loaded = True
    return skill_def
