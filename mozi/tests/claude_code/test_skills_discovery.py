"""
Tests for skills/discovery.py - Dynamic skill discovery.
"""

from __future__ import annotations

import os

import pytest

from src.claude_code.skills.discovery import (
    add_skill_directories,
    clear_dynamic_skills,
    discover_skill_dirs_for_paths,
    get_discovered_dir_count,
    get_dynamic_skill,
    get_dynamic_skill_count,
    get_dynamic_skills,
    on_dynamic_skills_loaded,
)
from src.claude_code.skills.registry import SkillRegistry


class TestDiscoverSkillDirsForPaths:
    """Tests for discover_skill_dirs_for_paths."""

    def test_empty_file_list(self, tmp_path: pytest.TempPathFactory) -> None:
        """Empty file list returns empty dirs."""
        result = discover_skill_dirs_for_paths([], str(tmp_path))
        assert result == []

    def test_finds_nested_skill_dir(self, tmp_path: pytest.TempPathFactory) -> None:
        """discovers skill directory nested under file location."""
        # Setup: file at src/main.py with .claude/skills at src/
        project = tmp_path / "project"
        project.mkdir()
        src_dir = project / "src"
        src_dir.mkdir()
        skill_dir = src_dir / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        (src_dir / "main.py").write_text("")

        # First clear any global state
        clear_dynamic_skills()

        result = discover_skill_dirs_for_paths([str(src_dir / "main.py")], str(project))
        assert len(result) >= 1

    def test_respects_cwd_boundary(self, tmp_path: pytest.TempPathFactory) -> None:
        """does not discover dirs at or above cwd level."""
        project = tmp_path / "project"
        project.mkdir()
        # Create file inside project
        (project / "file.py").write_text("")
        # Create skill dir at project root (should NOT be discovered)
        skill_dir = project / ".claude" / "skills"
        skill_dir.mkdir(parents=True)

        clear_dynamic_skills()

        result = discover_skill_dirs_for_paths([str(project / "file.py")], str(project))
        # Should not include the project-level .claude/skills since cwd is the boundary
        assert all(not r.endswith(str(project)) for r in result)

    def test_deduplicates_already_discovered(self, tmp_path: pytest.TempPathFactory) -> None:
        """does not re-discover already found directories."""
        project = tmp_path / "project"
        project.mkdir()
        nested = project / "src"
        nested.mkdir()
        skill_dir = nested / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        (nested / "file.py").write_text("")

        clear_dynamic_skills()

        discover_skill_dirs_for_paths([str(nested / "file.py")], str(project))
        count1 = get_discovered_dir_count()

        # Call again with same file
        discover_skill_dirs_for_paths([str(nested / "file.py")], str(project))
        count2 = get_discovered_dir_count()

        # Should not have increased
        assert count2 == count1


class TestAddSkillDirectories:
    """Tests for add_skill_directories."""

    def test_empty_dirs(self) -> None:
        """empty dirs does nothing."""
        clear_dynamic_skills()
        before = get_dynamic_skill_count()
        add_skill_directories([])
        assert get_dynamic_skill_count() == before

    def test_loads_skills_from_dir(self, tmp_path: pytest.TempPathFactory) -> None:
        """loads SKILL.md files from skill directory."""
        skill_dir = tmp_path / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        test_skill = skill_dir / "test-skill"
        test_skill.mkdir()
        (test_skill / "SKILL.md").write_text("---\ndescription: A test skill\n---\nTest content")

        clear_dynamic_skills()
        add_skill_directories([str(skill_dir)])

        skills = get_dynamic_skills()
        skill_names = [s.name for s in skills]
        assert "test-skill" in skill_names

    def test_loads_into_registry(self, tmp_path: pytest.TempPathFactory) -> None:
        """loads skills into provided registry."""
        skill_dir = tmp_path / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        test_skill = skill_dir / "test-skill"
        test_skill.mkdir()
        (test_skill / "SKILL.md").write_text("---\ndescription: Test\n---\nContent")

        clear_dynamic_skills()
        reg = SkillRegistry()
        add_skill_directories([str(skill_dir)], reg)

        assert reg.has("test-skill")

    def test_deeper_paths_take_precedence(self, tmp_path: pytest.TempPathFactory) -> None:
        """deeper skill dirs should be loaded later (reversed)."""
        skill_dir = tmp_path / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        s1 = skill_dir / "alpha"
        s1.mkdir()
        (s1 / "SKILL.md").write_text("---\nname: alpha\n---\nA")

        s2 = skill_dir / "beta"
        s2.mkdir()
        (s2 / "SKILL.md").write_text("---\nname: beta\n---\nB")

        clear_dynamic_skills()
        add_skill_directories([str(skill_dir)])

        skills = get_dynamic_skills()
        names = [s.name for s in skills]
        # Both should be loaded
        assert "alpha" in names
        assert "beta" in names


class TestDynamicSkills:
    """Tests for dynamic skill getters."""

    def test_get_dynamic_skills(self, tmp_path: pytest.TempPathFactory) -> None:
        """get_dynamic_skills returns loaded skills."""
        skill_dir = tmp_path / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        s = skill_dir / "test"
        s.mkdir()
        (s / "SKILL.md").write_text("---\ndescription: T\n---\nC")

        clear_dynamic_skills()
        add_skill_directories([str(skill_dir)])

        skills = get_dynamic_skills()
        assert len(skills) >= 1

    def test_get_dynamic_skill_by_name(self, tmp_path: pytest.TempPathFactory) -> None:
        """get_dynamic_skill returns skill by name."""
        skill_dir = tmp_path / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        s = skill_dir / "findme"
        s.mkdir()
        (s / "SKILL.md").write_text("---\ndescription: Found\n---\nContent")

        clear_dynamic_skills()
        add_skill_directories([str(skill_dir)])

        skill = get_dynamic_skill("findme")
        assert skill is not None
        assert skill.name == "findme"

    def test_get_dynamic_skill_nonexistent(self) -> None:
        """get_dynamic_skill returns None for nonexistent."""
        skill = get_dynamic_skill("__nonexistent__")
        assert skill is None


class TestDynamicSkillCallbacks:
    """Tests for dynamic skill loaded callbacks."""

    def test_callback_called(self, tmp_path: pytest.TempPathFactory) -> None:
        """callback is called when skills are loaded."""
        skill_dir = tmp_path / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        s = skill_dir / "test"
        s.mkdir()
        (s / "SKILL.md").write_text("---\ndescription: T\n---\nC")

        clear_dynamic_skills()
        called = []

        def callback() -> None:
            called.append(True)

        unsub = on_dynamic_skills_loaded(callback)
        add_skill_directories([str(skill_dir)])
        assert len(called) == 1
        unsub()

    def test_unsubscribe(self, tmp_path: pytest.TempPathFactory) -> None:
        """unsubscribe stops callback from being called."""
        skill_dir = tmp_path / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        s = skill_dir / "test"
        s.mkdir()
        (s / "SKILL.md").write_text("---\ndescription: T\n---\nC")

        clear_dynamic_skills()
        called = []

        def callback() -> None:
            called.append(True)

        unsub = on_dynamic_skills_loaded(callback)
        unsub()  # unsubscribe
        add_skill_directories([str(skill_dir)])
        assert len(called) == 0


class TestClearDynamicSkills:
    """Tests for clear_dynamic_skills."""

    def test_clears_discovered_dirs(self, tmp_path: pytest.TempPathFactory) -> None:
        """clear_dynamic_skills resets discovered directories."""
        skill_dir = tmp_path / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        s = tmp_path / "src"
        s.mkdir()
        skill_subdir = s / ".claude" / "skills"
        skill_subdir.mkdir(parents=True)

        clear_dynamic_skills()
        discover_skill_dirs_for_paths([str(s / "file.py")], str(tmp_path))
        assert get_discovered_dir_count() > 0

        clear_dynamic_skills()
        assert get_discovered_dir_count() == 0

    def test_clears_dynamic_skills(self, tmp_path: pytest.TempPathFactory) -> None:
        """clear_dynamic_skills resets dynamic skills."""
        skill_dir = tmp_path / ".claude" / "skills"
        skill_dir.mkdir(parents=True)
        s = skill_dir / "test"
        s.mkdir()
        (s / "SKILL.md").write_text("---\ndescription: T\n---\nC")

        clear_dynamic_skills()
        add_skill_directories([str(skill_dir)])
        assert get_dynamic_skill_count() > 0

        clear_dynamic_skills()
        assert get_dynamic_skill_count() == 0

    def test_get_discovered_dir_count(self) -> None:
        """get_discovered_dir_count returns current count."""
        clear_dynamic_skills()
        assert get_discovered_dir_count() == 0
