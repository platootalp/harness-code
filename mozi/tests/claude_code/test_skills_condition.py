"""
Tests for skills/condition.py - Conditional skills.
"""

from __future__ import annotations

import pytest

from src.claude_code.skills.condition import (
    ConditionalSkill,
    ConditionalSkillStore,
    create_conditional_skill,
    get_conditional_store,
    normalize_path_patterns,
    should_activate_skill,
)
from src.claude_code.skills.definition import SkillDefinition


@pytest.fixture
def conditional_skill() -> ConditionalSkill:
    """Create a conditional skill."""
    definition = SkillDefinition(name="test-py", paths=["**/*.py"])
    return ConditionalSkill(definition=definition, paths=["**/*.py"])


class TestConditionalSkill:
    """Tests for ConditionalSkill."""

    def test_name_property(self, conditional_skill: ConditionalSkill) -> None:
        """name property returns skill name."""
        assert conditional_skill.name == "test-py"

    def test_description_property(self, conditional_skill: ConditionalSkill) -> None:
        """description property returns skill description."""
        assert conditional_skill.description == ""

    def test_matches_path_exact(self, conditional_skill: ConditionalSkill) -> None:
        """matches_path returns True for matching path."""
        assert conditional_skill.matches_path("src/main.py", "/project") is True

    def test_matches_path_no_match(self, conditional_skill: ConditionalSkill) -> None:
        """matches_path returns False for non-matching path."""
        assert conditional_skill.matches_path("src/main.js", "/project") is False

    def test_matches_path_with_glob(self, conditional_skill: ConditionalSkill) -> None:
        """matches_path handles glob patterns."""
        # ** at start matches any depth
        skill = ConditionalSkill(
            definition=SkillDefinition(name="test"),
            paths=["**/*.py"],
        )
        assert skill.matches_path("src/util.py", "/project") is True
        assert skill.matches_path("src/lib/util.py", "/project") is True
        assert skill.matches_path("src/lib/deep/util.py", "/project") is True
        assert skill.matches_path("src/util.js", "/project") is False

    def test_matches_path_converts_to_relative(self, conditional_skill: ConditionalSkill) -> None:
        """matches_path converts absolute paths to relative."""
        assert conditional_skill.matches_path("/project/src/main.py", "/project") is True

    def test_activate(self, conditional_skill: ConditionalSkill) -> None:
        """activate sets is_activated and records timestamp."""
        assert conditional_skill.is_activated is False
        conditional_skill.activate()
        assert conditional_skill.is_activated is True
        assert conditional_skill.activated_at is not None

    def test_repr(self, conditional_skill: ConditionalSkill) -> None:
        """__repr__ includes name and status."""
        r = repr(conditional_skill)
        assert "test-py" in r
        assert "pending" in r
        conditional_skill.activate()
        r = repr(conditional_skill)
        assert "activated" in r


class TestConditionalSkillStore:
    """Tests for ConditionalSkillStore."""

    @pytest.fixture
    def store(self) -> ConditionalSkillStore:
        return ConditionalSkillStore()

    def test_add_skill(self, store: ConditionalSkillStore) -> None:
        """add stores conditional skill."""
        skill = SkillDefinition(name="test", paths=["*.py"])
        store.add(skill)
        assert "test" in store

    def test_add_skill_without_paths_ignored(self, store: ConditionalSkillStore) -> None:
        """add ignores skills without paths."""
        skill = SkillDefinition(name="test")
        store.add(skill)
        assert "test" not in store

    def test_add_duplicate_ignored(self, store: ConditionalSkillStore) -> None:
        """add ignores duplicate skill names."""
        skill = SkillDefinition(name="test", paths=["*.py"])
        store.add(skill)
        store.add(skill)
        assert len(store) == 1

    def test_remove(self, store: ConditionalSkillStore) -> None:
        """remove deletes conditional skill."""
        skill = SkillDefinition(name="test", paths=["*.py"])
        store.add(skill)
        store.remove("test")
        assert "test" not in store

    def test_get(self, store: ConditionalSkillStore) -> None:
        """get returns conditional skill."""
        skill = SkillDefinition(name="test", paths=["*.py"])
        store.add(skill)
        result = store.get("test")
        assert result is not None
        assert result.name == "test"

    def test_get_nonexistent(self, store: ConditionalSkillStore) -> None:
        """get returns None for nonexistent."""
        assert store.get("nonexistent") is None

    def test_get_all(self, store: ConditionalSkillStore) -> None:
        """get_all returns all skills."""
        s1 = SkillDefinition(name="a", paths=["*.py"])
        s2 = SkillDefinition(name="b", paths=["*.ts"])
        store.add(s1)
        store.add(s2)
        all_skills = store.get_all()
        assert len(all_skills) == 2

    def test_get_pending(self, store: ConditionalSkillStore) -> None:
        """get_pending returns only pending skills."""
        s1 = SkillDefinition(name="a", paths=["*.py"])
        s2 = SkillDefinition(name="b", paths=["*.ts"])
        store.add(s1)
        store.add(s2)
        store.activate_for_paths(["a.py"], "/project")
        pending = store.get_pending()
        assert len(pending) == 1
        assert pending[0].name == "b"

    def test_get_activated(self, store: ConditionalSkillStore) -> None:
        """get_activated returns only activated skills."""
        s1 = SkillDefinition(name="a", paths=["*.py"])
        s2 = SkillDefinition(name="b", paths=["*.ts"])
        store.add(s1)
        store.add(s2)
        store.activate_for_paths(["a.py"], "/project")
        activated = store.get_activated()
        assert len(activated) == 1
        assert activated[0].name == "a"

    def test_activate_for_paths_single_match(self, store: ConditionalSkillStore) -> None:
        """activate_for_paths activates matching skills."""
        s1 = SkillDefinition(name="py", paths=["**/*.py"])
        s2 = SkillDefinition(name="ts", paths=["**/*.ts"])
        store.add(s1)
        store.add(s2)
        activated = store.activate_for_paths(["src/main.py"], "/project")
        assert "py" in activated
        assert "ts" not in activated

    def test_activate_for_paths_no_match(self, store: ConditionalSkillStore) -> None:
        """activate_for_paths returns empty when no matches."""
        skill = SkillDefinition(name="py", paths=["**/*.py"])
        store.add(skill)
        activated = store.activate_for_paths(["src/main.js"], "/project")
        assert activated == []

    def test_activate_for_paths_callbacks(self, store: ConditionalSkillStore) -> None:
        """activate_for_paths fires callbacks."""
        skill = SkillDefinition(name="py", paths=["**/*.py"])
        store.add(skill)
        events: list[tuple] = []

        def callback(name: str, cs: ConditionalSkill) -> None:
            events.append((name, cs))

        store.on_activate(callback)
        store.activate_for_paths(["main.py"], "/project")
        assert len(events) == 1
        assert events[0][0] == "py"

    def test_is_activated_true(self, store: ConditionalSkillStore) -> None:
        """is_activated returns True after activation."""
        skill = SkillDefinition(name="py", paths=["**/*.py"])
        store.add(skill)
        store.activate_for_paths(["main.py"], "/project")
        assert store.is_activated("py") is True

    def test_is_activated_false(self, store: ConditionalSkillStore) -> None:
        """is_activated returns False before activation."""
        skill = SkillDefinition(name="py", paths=["**/*.py"])
        store.add(skill)
        assert store.is_activated("py") is False

    def test_is_activated_nonexistent(self, store: ConditionalSkillStore) -> None:
        """is_activated returns False for nonexistent."""
        assert store.is_activated("nonexistent") is False

    def test_clear(self, store: ConditionalSkillStore) -> None:
        """clear removes all skills."""
        skill = SkillDefinition(name="test", paths=["*.py"])
        store.add(skill)
        store.clear()
        assert len(store) == 0


class TestConditionalHelpers:
    """Tests for helper functions."""

    def test_create_conditional_skill_with_paths(self) -> None:
        """create_conditional_skill returns ConditionalSkill when paths exist."""
        skill = SkillDefinition(name="test", paths=["*.py"])
        result = create_conditional_skill(skill)
        assert result is not None
        assert result.name == "test"

    def test_create_conditional_skill_without_paths(self) -> None:
        """create_conditional_skill returns None when no paths."""
        skill = SkillDefinition(name="test")
        result = create_conditional_skill(skill)
        assert result is None

    def test_should_activate_skill_true(self) -> None:
        """should_activate_skill returns True when path matches."""
        skill = SkillDefinition(name="test", paths=["**/*.py"])
        cs = ConditionalSkill(definition=skill, paths=["**/*.py"])
        assert should_activate_skill(cs, ["main.py"], "/project") is True

    def test_should_activate_skill_already_activated(self) -> None:
        """should_activate_skill returns False when already activated."""
        skill = SkillDefinition(name="test", paths=["**/*.py"])
        cs = ConditionalSkill(definition=skill, paths=["**/*.py"])
        cs.activate()
        assert should_activate_skill(cs, ["main.py"], "/project") is False

    def test_should_activate_skill_no_match(self) -> None:
        """should_activate_skill returns False when no path matches."""
        skill = SkillDefinition(name="test", paths=["**/*.py"])
        cs = ConditionalSkill(definition=skill, paths=["**/*.py"])
        assert should_activate_skill(cs, ["main.js"], "/project") is False


class TestNormalize_path_patterns:
    """Tests for normalize_path_patterns function."""

    def test_removes_trailing_double_star(self) -> None:
        """normalize_path_patterns removes trailing /**."""
        result = normalize_path_patterns(["src/**", "lib/**"])
        assert result == ["src", "lib"]

    def test_preserves_patterns_without_trailing(self) -> None:
        """normalize_path_patterns preserves patterns without trailing /**."""
        result = normalize_path_patterns(["**/*.py", "src/**/*.ts"])
        assert result == ["**/*.py", "src/**/*.ts"]


class TestGlobalConditionalStore:
    """Tests for global conditional store."""

    def test_get_conditional_store_singleton(self) -> None:
        """get_conditional_store returns the same instance."""
        store1 = get_conditional_store()
        store2 = get_conditional_store()
        assert store1 is store2
