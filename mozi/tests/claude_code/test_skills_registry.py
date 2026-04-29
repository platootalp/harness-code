"""
Tests for skills/registry.py - SkillRegistry.
"""

from __future__ import annotations

import pytest

from src.claude_code.skills.definition import SkillDefinition, SkillSource
from src.claude_code.skills.registry import (
    SkillRegistry,
    get_skill,
    get_global_registry,
    register_skill,
)


@pytest.fixture
def registry() -> SkillRegistry:
    """Create a fresh SkillRegistry."""
    return SkillRegistry()


@pytest.fixture
def sample_skill() -> SkillDefinition:
    """Create a sample skill."""
    return SkillDefinition(
        name="simplify",
        description="Simplify code",
        aliases=["improve", "clean"],
        allowed_tools=["Read", "Glob"],
        source=SkillSource.BUNDLED,
    )


class TestSkillRegistryInit:
    """Tests for SkillRegistry initialization."""

    def test_empty_registry(self) -> None:
        """Empty registry starts with no skills."""
        reg = SkillRegistry()
        assert len(reg) == 0
        assert reg.list_all() == []
        assert reg.list_names() == []

    def test_with_optional_args(self) -> None:
        """SkillRegistry accepts optional tool_registry and executor."""
        reg = SkillRegistry(tool_registry={}, executor={})
        assert len(reg) == 0


class TestSkillRegistryRegister:
    """Tests for SkillRegistry.register."""

    def test_register_single_skill(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """register adds a skill to the registry."""
        registry.register(sample_skill)
        assert len(registry) == 1
        assert registry.get("simplify") is sample_skill

    def test_register_aliases(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """register maps aliases to the skill."""
        registry.register(sample_skill)
        assert registry.get("improve") is sample_skill
        assert registry.get("clean") is sample_skill

    def test_register_duplicate_ignored(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """register ignores duplicate skill names."""
        registry.register(sample_skill)
        registry.register(sample_skill)
        assert len(registry) == 1

    def test_register_second_different_skill(self, registry: SkillRegistry) -> None:
        """register allows different skill names."""
        s1 = SkillDefinition(name="simplify", description="S1")
        s2 = SkillDefinition(name="verify", description="S2")
        registry.register(s1)
        registry.register(s2)
        assert len(registry) == 2
        assert registry.get("simplify") is s1
        assert registry.get("verify") is s2


class TestSkillRegistryUnregister:
    """Tests for SkillRegistry.unregister."""

    def test_unregister_by_name(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """unregister removes skill by name."""
        registry.register(sample_skill)
        removed = registry.unregister("simplify")
        assert removed is sample_skill
        assert len(registry) == 0
        assert registry.get("simplify") is None

    def test_unregister_by_alias(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """unregister removes skill by alias."""
        registry.register(sample_skill)
        removed = registry.unregister("improve")
        assert removed is sample_skill
        assert len(registry) == 0
        assert registry.get("simplify") is None

    def test_unregister_nonexistent(self, registry: SkillRegistry) -> None:
        """unregister raises KeyError for nonexistent skill."""
        with pytest.raises(KeyError):
            registry.unregister("nonexistent")


class TestSkillRegistryLookup:
    """Tests for SkillRegistry.get and related lookups."""

    def test_get_existing(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """get returns skill if it exists."""
        registry.register(sample_skill)
        assert registry.get("simplify") is sample_skill

    def test_get_nonexistent(self, registry: SkillRegistry) -> None:
        """get returns None for nonexistent skill."""
        assert registry.get("nonexistent") is None

    def test_get_by_alias(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """get resolves aliases."""
        registry.register(sample_skill)
        assert registry.get("improve") is sample_skill

    def test_has_true(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """has returns True for existing skill."""
        registry.register(sample_skill)
        assert registry.has("simplify") is True

    def test_has_false(self, registry: SkillRegistry) -> None:
        """has returns False for nonexistent skill."""
        assert registry.has("nonexistent") is False

    def test_has_alias(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """has resolves aliases."""
        registry.register(sample_skill)
        assert registry.has("improve") is True

    def test_get_required_found(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """get_required returns skill if found."""
        registry.register(sample_skill)
        assert registry.get_required("simplify") is sample_skill

    def test_get_required_not_found(self, registry: SkillRegistry) -> None:
        """get_required raises KeyError if not found."""
        with pytest.raises(KeyError):
            registry.get_required("nonexistent")


class TestSkillRegistryListing:
    """Tests for SkillRegistry listing methods."""

    def test_list_all(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """list_all returns all registered skills."""
        registry.register(sample_skill)
        assert sample_skill in registry.list_all()

    def test_list_names(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """list_names returns skill names."""
        registry.register(sample_skill)
        assert "simplify" in registry.list_names()

    def test_list_enabled(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """list_enabled returns enabled skills."""
        registry.register(sample_skill)
        enabled = registry.list_enabled()
        assert sample_skill in enabled

    def test_list_enabled_with_disabled(self, registry: SkillRegistry) -> None:
        """list_enabled filters by is_enabled_fn."""
        enabled_skill = SkillDefinition(name="enabled")
        disabled_skill = SkillDefinition(name="disabled", is_enabled_fn=lambda: False)
        registry.register(enabled_skill)
        registry.register(disabled_skill)
        enabled = registry.list_enabled()
        assert enabled_skill in enabled
        assert disabled_skill not in enabled

    def test_list_user_invocable(self, registry: SkillRegistry) -> None:
        """list_user_invocable returns user-invocable non-hidden skills."""
        invocable = SkillDefinition(name="invocable", user_invocable=True)
        hidden = SkillDefinition(name="hidden", user_invocable=True, is_hidden=True)
        non_invocable = SkillDefinition(name="non_invocable", user_invocable=False)
        registry.register(invocable)
        registry.register(hidden)
        registry.register(non_invocable)
        result = registry.list_user_invocable()
        assert invocable in result
        assert hidden not in result
        assert non_invocable not in result

    def test_list_by_source(self, registry: SkillRegistry) -> None:
        """list_by_source filters by source."""
        bundled = SkillDefinition(name="bundled", source=SkillSource.BUNDLED)
        project = SkillDefinition(name="project", source=SkillSource.PROJECT)
        registry.register(bundled)
        registry.register(project)
        result = registry.list_by_source(SkillSource.BUNDLED)
        assert bundled in result
        assert project not in result

    def test_filter(self, registry: SkillRegistry) -> None:
        """filter applies predicate to all skills."""
        s1 = SkillDefinition(name="a", description="First")
        s2 = SkillDefinition(name="b", description="Second")
        registry.register(s1)
        registry.register(s2)
        result = registry.filter(lambda s: "First" in s.description)
        assert len(result) == 1
        assert result[0] is s1


class TestSkillRegistryAliases:
    """Tests for SkillRegistry alias management."""

    def test_register_alias(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """register_alias adds an alias to existing skill."""
        registry.register(sample_skill)
        registry.register_alias("simplify", "opt")
        assert registry.get("opt") is sample_skill

    def test_register_alias_nonexistent_raises(self, registry: SkillRegistry) -> None:
        """register_alias raises KeyError for nonexistent skill."""
        with pytest.raises(KeyError):
            registry.register_alias("nonexistent", "alias")


class TestSkillRegistryActivation:
    """Tests for SkillRegistry activation methods."""

    def test_activate_existing(self, registry: SkillRegistry, tmp_path: pytest.TempPathFactory) -> None:
        """activate loads skill full content."""
        skill_path = tmp_path / "test"
        skill_path.mkdir()
        skill_path.joinpath("SKILL.md").write_text("Full instructions")
        skill = SkillDefinition(name="test", _path=skill_path, _loaded=False)
        registry.register(skill)
        activated = registry.activate("test")
        assert activated._loaded is True
        assert activated.instructions == "Full instructions"

    def test_activate_nonexistent_raises(self, registry: SkillRegistry) -> None:
        """activate raises KeyError for nonexistent skill."""
        with pytest.raises(KeyError):
            registry.activate("nonexistent")


class TestSkillRegistryDynamic:
    """Tests for SkillRegistry dynamic skill methods."""

    def test_add_dynamic_skills(self, registry: SkillRegistry) -> None:
        """add_dynamic_skills adds skills to registry."""
        skills = [
            SkillDefinition(name="d1"),
            SkillDefinition(name="d2"),
        ]
        registry.add_dynamic_skills(skills)
        assert registry.get("d1") is skills[0]
        assert registry.get("d2") is skills[1]

    def test_clear_dynamic(self, registry: SkillRegistry) -> None:
        """clear_dynamic clears conditional state."""
        skill = SkillDefinition(name="test", paths=["*.py"])
        registry.register(skill)
        registry.clear_dynamic()
        assert registry.get("test") is skill  # still registered


class TestSkillRegistrySchema:
    """Tests for SkillRegistry schema export."""

    def test_get_schemas(self, registry: SkillRegistry) -> None:
        """get_schemas returns JSON schemas for invocable skills."""
        skill = SkillDefinition(
            name="simplify",
            description="Simplify code",
            user_invocable=True,
        )
        registry.register(skill)
        schemas = registry.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "simplify"
        assert "input_schema" in schemas[0]

    def test_get_schemas_excludes_hidden(self, registry: SkillRegistry) -> None:
        """get_schemas excludes hidden skills."""
        skill = SkillDefinition(name="hidden", user_invocable=True, is_hidden=True)
        registry.register(skill)
        schemas = registry.get_schemas()
        assert len(schemas) == 0


class TestSkillRegistryMerge:
    """Tests for SkillRegistry merge."""

    def test_merge(self, registry: SkillRegistry) -> None:
        """merge adds all skills from another registry."""
        other = SkillRegistry()
        s1 = SkillDefinition(name="a")
        s2 = SkillDefinition(name="b")
        registry.register(s1)
        other.register(s2)
        registry.merge(other)
        assert registry.get("a") is s1
        assert registry.get("b") is s2

    def test_merge_duplicate_skipped(self, registry: SkillRegistry) -> None:
        """merge skips duplicate skill names."""
        other = SkillRegistry()
        s1 = SkillDefinition(name="a")
        s2 = SkillDefinition(name="a")  # same name
        registry.register(s1)
        other.register(s2)
        registry.merge(other)
        assert registry.get("a") is s1  # original kept


class TestSkillRegistryClear:
    """Tests for SkillRegistry clear."""

    def test_clear(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """clear removes all skills."""
        registry.register(sample_skill)
        registry.clear()
        assert len(registry) == 0
        assert registry.get("simplify") is None


class TestSkillRegistryIteration:
    """Tests for SkillRegistry iteration."""

    def test_len(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """len returns count of registered skills."""
        registry.register(sample_skill)
        assert len(registry) == 1

    def test_contains_true(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """contains returns True for registered skill."""
        registry.register(sample_skill)
        assert "simplify" in registry

    def test_contains_false(self, registry: SkillRegistry) -> None:
        """contains returns False for unregistered skill."""
        assert "nonexistent" not in registry

    def test_iter(self, registry: SkillRegistry, sample_skill: SkillDefinition) -> None:
        """iter yields skill names."""
        registry.register(sample_skill)
        names = list(iter(registry))
        assert "simplify" in names


class TestGlobalRegistry:
    """Tests for global registry functions."""

    def test_get_global_registry_returns_singleton(self) -> None:
        """get_global_registry returns the same instance."""
        reg1 = get_global_registry()
        reg2 = get_global_registry()
        assert reg1 is reg2

    def test_register_skill_global(self) -> None:
        """register_skill registers with global registry."""
        skill = SkillDefinition(name="__test_global__", description="test")
        # Clean up first
        global_reg = get_global_registry()
        if global_reg.has("__test_global__"):
            global_reg.unregister("__test_global__")
        register_skill(skill)
        assert get_skill("__test_global__") is skill
        # Clean up
        global_reg.unregister("__test_global__")

    def test_get_skill_nonexistent(self) -> None:
        """get_skill returns None for nonexistent."""
        assert get_skill("__nonexistent__") is None
