"""
Tests for skills/builtin.py - Bundled skills registration.
"""

from __future__ import annotations

import pytest

from src.claude_code.skills.builtin import (
    BundledSkillDefinition,
    clear_bundled_skills,
    get_bundled_skills,
    init_bundled_skills,
    register_all_bundled_skills_from_registry,
    register_simplify_skill,
)
from src.claude_code.skills.definition import SkillDefinition, SkillSource
from src.claude_code.skills.registry import SkillRegistry


class TestBundledSkillDefinition:
    """Tests for BundledSkillDefinition."""

    def test_required_fields(self) -> None:
        """BundledSkillDefinition requires name and description."""
        defn = BundledSkillDefinition(name="test", description="A test")
        assert defn.name == "test"
        assert defn.description == "A test"

    def test_defaults(self) -> None:
        """BundledSkillDefinition has correct defaults."""
        defn = BundledSkillDefinition(name="test", description="Desc")
        assert defn.aliases == []
        assert defn.allowed_tools == []
        assert defn.user_invocable is True
        assert defn.disable_model_invocation is False
        assert defn.context == "inline"
        assert defn.agent is None
        assert defn.effort is None
        assert defn.model is None
        assert defn.hooks is None
        assert defn.files is None
        assert defn.get_prompt_for_command is None


class TestGetBundledSkills:
    """Tests for get_bundled_skills."""

    def setup_method(self) -> None:
        """Clear bundled skills before each test."""
        clear_bundled_skills()

    def teardown_method(self) -> None:
        """Clear bundled skills after each test."""
        clear_bundled_skills()

    def test_empty_initially(self) -> None:
        """get_bundled_skills returns empty list initially."""
        assert get_bundled_skills() == []

    def test_returns_copy(self) -> None:
        """get_bundled_skills returns a copy."""
        skills = get_bundled_skills()
        skills.append(SkillDefinition(name="fake"))
        assert len(get_bundled_skills()) == 0


class TestRegisterBundledSkill:
    """Tests for register_simplify_skill and _register_bundled_skill."""

    def setup_method(self) -> None:
        clear_bundled_skills()

    def teardown_method(self) -> None:
        clear_bundled_skills()

    def test_register_simplify_skill(self) -> None:
        """register_simplify_skill adds simplify to bundled skills."""
        register_simplify_skill()
        skills = get_bundled_skills()
        assert len(skills) == 1
        assert skills[0].name == "simplify"
        assert skills[0].source == SkillSource.BUNDLED

    def test_bundled_skill_properties(self) -> None:
        """bundled skills have correct properties."""
        register_simplify_skill()
        skill = get_bundled_skills()[0]
        assert skill.user_invocable is True
        assert skill.is_hidden is False
        assert "Read" in skill.allowed_tools
        assert "Glob" in skill.allowed_tools


class TestInitBundledSkills:
    """Tests for init_bundled_skills."""

    def setup_method(self) -> None:
        clear_bundled_skills()

    def teardown_method(self) -> None:
        clear_bundled_skills()

    def test_init_bundled_skills(self) -> None:
        """init_bundled_skills registers all 10 bundled skills."""
        init_bundled_skills()
        skills = get_bundled_skills()
        assert len(skills) == 10

    def test_init_bundled_skills_idempotent(self) -> None:
        """init_bundled_skills is idempotent."""
        init_bundled_skills()
        init_bundled_skills()
        skills = get_bundled_skills()
        # Should not double-register
        assert len(skills) == 10

    def test_all_expected_skills_present(self) -> None:
        """init_bundled_skills registers all expected skill names."""
        init_bundled_skills()
        names = {s.name for s in get_bundled_skills()}
        expected = {
            "simplify",
            "verify",
            "debug",
            "stuck",
            "remember",
            "keybindings",
            "update-config",
            "lorem-ipsum",
            "skillify",
            "batch",
        }
        assert expected.issubset(names)


class TestClearBundledSkills:
    """Tests for clear_bundled_skills."""

    def setup_method(self) -> None:
        clear_bundled_skills()

    def teardown_method(self) -> None:
        clear_bundled_skills()

    def test_clear_removes_all(self) -> None:
        """clear_bundled_skills removes all skills."""
        init_bundled_skills()
        assert len(get_bundled_skills()) == 10
        clear_bundled_skills()
        assert get_bundled_skills() == []


class TestRegisterAllBundledSkillsFromRegistry:
    """Tests for register_all_bundled_skills_from_registry."""

    def setup_method(self) -> None:
        clear_bundled_skills()

    def teardown_method(self) -> None:
        clear_bundled_skills()

    def test_registers_into_registry(self) -> None:
        """register_all_bundled_skills_from_registry registers into registry."""
        reg = SkillRegistry()
        register_all_bundled_skills_from_registry(reg)
        assert len(reg) == 10

    def test_registers_with_correct_source(self) -> None:
        """registered skills have BUNDLED source."""
        reg = SkillRegistry()
        register_all_bundled_skills_from_registry(reg)
        skills = reg.list_by_source(SkillSource.BUNDLED)
        assert len(skills) == 10


class TestBundledSkillSources:
    """Tests for bundled skill source tracking."""

    def setup_method(self) -> None:
        clear_bundled_skills()

    def teardown_method(self) -> None:
        clear_bundled_skills()

    def test_fork_context_skills(self) -> None:
        """fork context skills have context='fork'."""
        init_bundled_skills()
        stuck = next(s for s in get_bundled_skills() if s.name == "stuck")
        assert stuck.context == "fork"
        assert stuck.agent == "general-purpose"

        batch = next(s for s in get_bundled_skills() if s.name == "batch")
        assert batch.context == "fork"

    def test_inline_context_skills(self) -> None:
        """inline context skills have context='inline'."""
        init_bundled_skills()
        simplify = next(s for s in get_bundled_skills() if s.name == "simplify")
        assert simplify.context == "inline"
