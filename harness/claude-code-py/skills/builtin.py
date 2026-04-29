"""Built-in skills registration.

Corresponds to TypeScript's registerBundledSkill() and bundled skill
registration in src/skills/bundledSkills.ts and src/skills/bundled/index.ts.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .definition import SkillDefinition, SkillSource, ToolUseContext

if TYPE_CHECKING:
    from ..models.message import ContentBlock


# =============================================================================
# Bundled Skill Definition
# =============================================================================


@dataclass
class BundledSkillDefinition:
    """Definition for a bundled skill that ships with the CLI.

    Corresponds to TypeScript's BundledSkillDefinition in bundledSkills.ts.
    """

    name: str
    description: str
    aliases: list[str] = field(default_factory=list)
    when_to_use: str | None = None
    argument_hint: str | None = None
    allowed_tools: list[str] = field(default_factory=list)
    model: str | None = None
    disable_model_invocation: bool = False
    user_invocable: bool = True
    is_enabled: Callable[[], bool] | None = None
    hooks: dict[str, Any] | None = None
    context: str = "inline"
    agent: str | None = None
    effort: str | None = None
    files: dict[str, str] | None = None
    get_prompt_for_command: Callable[
        [str, ToolUseContext], list[ContentBlock]
    ] | None = None


# =============================================================================
# Internal Registry
# =============================================================================

# Internal registry for bundled skills (matches TypeScript's bundledSkills[])
_bundled_skills: list[SkillDefinition] = []
_bundled_initialized: bool = False


def _register_bundled_skill(definition: BundledSkillDefinition) -> None:
    """Register a bundled skill that will be available to the model.

    Args:
        definition: The bundled skill definition.
    """
    skill = SkillDefinition(
        name=definition.name,
        description=definition.description,
        aliases=list(definition.aliases),
        when_to_use=definition.when_to_use,
        argument_hint=definition.argument_hint,
        allowed_tools=list(definition.allowed_tools),
        model=definition.model,
        disable_model_invocation=definition.disable_model_invocation,
        user_invocable=definition.user_invocable,
        is_enabled_fn=definition.is_enabled,
        hooks=definition.hooks,
        context=definition.context,
        agent=definition.agent,
        effort=definition.effort,
        source=SkillSource.BUNDLED,
        loaded_from="bundled",
        is_hidden=not definition.user_invocable,
        progress_message="running",
        get_prompt_for_command=definition.get_prompt_for_command,
    )

    _bundled_skills.append(skill)


def get_bundled_skills() -> list[SkillDefinition]:
    """Get all registered bundled skills.

    Returns:
        Copy of bundled skills list.
    """
    return list(_bundled_skills)


def clear_bundled_skills() -> None:
    """Clear bundled skills registry (for testing)."""
    global _bundled_skills, _bundled_initialized
    _bundled_skills.clear()
    _bundled_initialized = False


# =============================================================================
# Built-in Skill Registration Functions
# =============================================================================


def register_simplify_skill() -> None:
    """Register the built-in simplify skill.

    Review changed code for reuse, quality, and efficiency.
    """
    _register_bundled_skill(
        BundledSkillDefinition(
            name="simplify",
            description="Review changed code for reuse, quality, and efficiency, "
            "then fix any issues found.",
            when_to_use="Use when the user wants to simplify or improve code quality.",
            user_invocable=True,
            allowed_tools=["Read", "Glob", "Grep"],
            get_prompt_for_command=_simplify_prompt,  # type: ignore[arg-type]
        )
    )


def register_verify_skill() -> None:
    """Register the built-in verify skill.

    Verify code changes meet acceptance criteria.
    """
    _register_bundled_skill(
        BundledSkillDefinition(
            name="verify",
            description="Verify that code changes meet acceptance criteria.",
            when_to_use="Use when the user wants to verify their changes.",
            user_invocable=True,
            allowed_tools=["Read", "Glob", "Grep", "Bash"],
            get_prompt_for_command=_verify_prompt,  # type: ignore[arg-type]
        )
    )


def register_debug_skill() -> None:
    """Register the built-in debug skill.

    Help diagnose and fix bugs.
    """
    _register_bundled_skill(
        BundledSkillDefinition(
            name="debug",
            description="Help diagnose and fix bugs in the codebase.",
            when_to_use="Use when the user encounters a bug or unexpected behavior.",
            user_invocable=True,
            allowed_tools=["Read", "Glob", "Grep", "Bash"],
            get_prompt_for_command=_debug_prompt,  # type: ignore[arg-type]
        )
    )


def register_stuck_skill() -> None:
    """Register the built-in stuck skill.

    Help when the agent is stuck or blocked.
    """
    _register_bundled_skill(
        BundledSkillDefinition(
            name="stuck",
            description="Help when you're stuck or blocked on a problem.",
            when_to_use="Use when the agent reports being stuck or unable to proceed.",
            user_invocable=True,
            context="fork",
            agent="general-purpose",
            get_prompt_for_command=_stuck_prompt,  # type: ignore[arg-type]
        )
    )


def register_remember_skill() -> None:
    """Register the built-in remember skill.

    Review auto-memory entries and promote to CLAUDE.md.
    """
    _register_bundled_skill(
        BundledSkillDefinition(
            name="remember",
            description="Review auto-memory entries and propose promotions to "
            "CLAUDE.md, CLAUDE.local.md, or shared memory.",
            when_to_use="Use when the user wants to review or organize auto-memory entries.",
            user_invocable=True,
            get_prompt_for_command=_remember_prompt,  # type: ignore[arg-type]
        )
    )


def register_keybindings_skill() -> None:
    """Register the built-in keybindings skill.

    Configure keyboard shortcuts.
    """
    _register_bundled_skill(
        BundledSkillDefinition(
            name="keybindings",
            description="Configure keyboard shortcuts and keybindings.",
            when_to_use="Use when the user wants to set up or modify keybindings.",
            user_invocable=True,
            get_prompt_for_command=_keybindings_prompt,  # type: ignore[arg-type]
        )
    )


def register_update_config_skill() -> None:
    """Register the built-in update-config skill.

    Configure Claude Code via settings.json.
    """
    _register_bundled_skill(
        BundledSkillDefinition(
            name="update-config",
            description="Configure Claude Code settings via settings.json.",
            when_to_use="Use when the user wants to configure Claude Code behavior.",
            user_invocable=True,
            get_prompt_for_command=_update_config_prompt,  # type: ignore[arg-type]
        )
    )


def register_lorem_ipsum_skill() -> None:
    """Register the built-in lorem-ipsum skill.

    Generate placeholder text.
    """
    _register_bundled_skill(
        BundledSkillDefinition(
            name="lorem-ipsum",
            description="Generate lorem ipsum placeholder text.",
            argument_hint="[paragraphs=3]",
            when_to_use="Use when the user needs placeholder text.",
            user_invocable=True,
            get_prompt_for_command=_lorem_ipsum_prompt,  # type: ignore[arg-type]
        )
    )


def register_skillify_skill() -> None:
    """Register the built-in skillify skill.

    Convert a workflow into a reusable skill.
    """
    _register_bundled_skill(
        BundledSkillDefinition(
            name="skillify",
            description="Convert a workflow into a reusable skill.",
            when_to_use="Use when the user wants to create a new skill from a workflow.",
            user_invocable=True,
            context="fork",
            agent="general-purpose",
            get_prompt_for_command=_skillify_prompt,  # type: ignore[arg-type]
        )
    )


def register_batch_skill() -> None:
    """Register the built-in batch skill.

    Execute a task across multiple items in parallel.
    """
    _register_bundled_skill(
        BundledSkillDefinition(
            name="batch",
            description="Execute a task across multiple items in parallel.",
            argument_hint="<items> <task>",
            when_to_use="Use when the user wants to run a task on multiple items.",
            user_invocable=True,
            context="fork",
            get_prompt_for_command=_batch_prompt,  # type: ignore[arg-type]
        )
    )


# =============================================================================
# Prompt Generators (bundled skill content)
# =============================================================================


async def _simplify_prompt(
    args: str,
    context: ToolUseContext,
) -> list[ContentBlock]:
    """Generate prompt for simplify skill."""
    base = """Review changed code for reuse, quality, and efficiency.

Look for:
- Duplicated code that could be extracted into shared functions
- Overly complex logic that could be simplified
- Inefficient patterns that could be optimized
- Unnecessary abstractions or premature optimization

Suggest concrete fixes with explanations."""
    if args:
        base += f"\n\nAdditional context:\n{args}"
    return [{"type": "text", "text": base}]  # type: ignore[list-item]


async def _verify_prompt(
    args: str,
    context: ToolUseContext,
) -> list[ContentBlock]:
    """Generate prompt for verify skill."""
    base = """Verify that code changes meet acceptance criteria.

Steps:
1. Read the relevant code and understand what it does
2. Check that edge cases are handled
3. Verify error handling is appropriate
4. Confirm the changes don't introduce regressions
5. Report any issues found with specific fix suggestions."""
    if args:
        base += f"\n\nVerification focus:\n{args}"
    return [{"type": "text", "text": base}]  # type: ignore[list-item]


async def _debug_prompt(
    args: str,
    context: ToolUseContext,
) -> list[ContentBlock]:
    """Generate prompt for debug skill."""
    base = """Help diagnose and fix bugs.

Steps:
1. Gather information about the bug (error messages, logs, reproduction)
2. Identify the root cause through systematic analysis
3. Propose and verify fixes
4. Ensure the fix doesn't introduce new bugs"""
    if args:
        base += f"\n\nBug description:\n{args}"
    return [{"type": "text", "text": base}]  # type: ignore[list-item]


async def _stuck_prompt(
    args: str,
    context: ToolUseContext,
) -> list[ContentBlock]:
    """Generate prompt for stuck skill."""
    base = """You're working to help a coding assistant that reports being stuck.

Common causes of getting stuck:
- Uncertainty about the correct approach
- Facing a complex refactoring
- Unclear requirements
- Technical blockers

Help by:
1. Asking clarifying questions to understand the situation
2. Suggesting alternative approaches
3. Breaking down complex tasks into smaller steps
4. Providing concrete next steps to try"""
    if args:
        base += f"\n\nContext:\n{args}"
    return [{"type": "text", "text": base}]  # type: ignore[list-item]


async def _remember_prompt(
    args: str,
    context: ToolUseContext,
) -> list[ContentBlock]:
    """Generate prompt for remember skill."""
    base = """Review auto-memory entries and organize them.

Look at the auto-memory file and:
1. Identify entries worth promoting to CLAUDE.md
2. Identify entries that belong in project-specific config
3. Identify entries that should be forgotten
4. Propose specific promotions with rationale"""
    if args:
        base += f"\n\nAdditional context:\n{args}"
    return [{"type": "text", "text": base}]  # type: ignore[list-item]


async def _keybindings_prompt(
    args: str,
    context: ToolUseContext,
) -> list[ContentBlock]:
    """Generate prompt for keybindings skill."""
    return [
        {  # type: ignore[list-item]
            "type": "text",
            "text": "Configure keyboard shortcuts for Claude Code.\n\n"
            "Review current keybindings and suggest improvements.\n\n"
            "Common shortcuts to configure:\n"
            "- Stop assistant (/stop)\n"
            "- Resume agent (/resume)\n"
            "- Quick commands\n"
            "- Navigation shortcuts",
        }
    ]


async def _update_config_prompt(
    args: str,
    context: ToolUseContext,
) -> list[ContentBlock]:
    """Generate prompt for update-config skill."""
    base = """Configure Claude Code via settings.json.

Help the user configure:
- Permissions
- Environment variables
- Hooks
- Custom behaviors
- Model preferences"""
    if args:
        base += f"\n\nRequested configuration:\n{args}"
    return [{"type": "text", "text": base}]  # type: ignore[list-item]


async def _lorem_ipsum_prompt(
    args: str,
    context: ToolUseContext,
) -> list[ContentBlock]:
    """Generate prompt for lorem-ipsum skill."""
    paragraphs = 3
    if args:
        with contextlib.suppress(ValueError):
            paragraphs = int(args.strip())

    text = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
        "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris "
        "nisi ut aliquip ex ea commodo consequat. "
    )

    content = " ".join([text] * paragraphs)
    return [
        {  # type: ignore[list-item]
            "type": "text",
            "text": f"Generate {paragraphs} paragraphs of lorem ipsum:\n\n{content}",
        }
    ]


async def _skillify_prompt(
    args: str,
    context: ToolUseContext,
) -> list[ContentBlock]:
    """Generate prompt for skillify skill."""
    base = """Convert a workflow into a reusable skill.

Steps:
1. Identify the workflow pattern being used
2. Extract the reusable components
3. Create a SKILL.md with proper frontmatter
4. Define allowed-tools restrictions
5. Test the skill"""
    if args:
        base += f"\n\nWorkflow to convert:\n{args}"
    return [{"type": "text", "text": base}]  # type: ignore[list-item]


async def _batch_prompt(
    args: str,
    context: ToolUseContext,
) -> list[ContentBlock]:
    """Generate prompt for batch skill."""
    base = """Execute a task across multiple items in parallel.

1. Parse the items and task from arguments
2. Execute the task on each item
3. Aggregate results
4. Report summary"""
    if args:
        base += f"\n\nBatch task:\n{args}"
    return [{"type": "text", "text": base}]  # type: ignore[list-item]


# =============================================================================
# Initialize All Bundled Skills
# =============================================================================


def init_bundled_skills() -> None:
    """Initialize all bundled skills.

    Called at startup to register skills that ship with the CLI.
    Corresponds to TypeScript's initBundledSkills() in bundled/index.ts.
    """
    global _bundled_initialized

    if _bundled_initialized:
        return

    register_simplify_skill()
    register_verify_skill()
    register_debug_skill()
    register_stuck_skill()
    register_remember_skill()
    register_keybindings_skill()
    register_update_config_skill()
    register_lorem_ipsum_skill()
    register_skillify_skill()
    register_batch_skill()

    _bundled_initialized = True


def register_bundled_skill_with_callback(
    definition: BundledSkillDefinition,
) -> None:
    """Register a bundled skill with a custom prompt callback.

    This is the main public API for registering bundled skills.

    Args:
        definition: The bundled skill definition with get_prompt_for_command.
    """
    _register_bundled_skill(definition)


def register_all_bundled_skills_from_registry(
    registry: Any,
    executor: Any | None = None,
) -> None:
    """Register all bundled skills from a registry into a skill registry.

    Args:
        registry: SkillRegistry to register bundled skills into.
        executor: Optional skill executor.
    """
    init_bundled_skills()

    for skill in get_bundled_skills():
        registry.register(skill)
