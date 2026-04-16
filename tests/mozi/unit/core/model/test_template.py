"""Unit tests for PromptTemplateManager."""

from __future__ import annotations

import pytest

from mozi.core.model.template import (
    DEFAULT_TEMPLATES,
    VARIABLE_PATTERN,
    PromptTemplateManager,
    RenderResult,
)


class TestVariablePattern:
    """Tests for variable pattern regex."""

    def test_single_variable(self) -> None:
        """Test matching a single variable."""
        match = VARIABLE_PATTERN.search("Hello {{name}}")
        assert match is not None
        assert match.group(1) == "name"

    def test_multiple_variables(self) -> None:
        """Test matching multiple variables."""
        matches = VARIABLE_PATTERN.findall("{{a}} and {{b}} and {{c}}")
        assert matches == ["a", "b", "c"]

    def test_no_variables(self) -> None:
        """Test no variables in template."""
        matches = VARIABLE_PATTERN.findall("Hello world")
        assert matches == []

    def test_variable_with_underscore(self) -> None:
        """Test variable with underscore in name."""
        match = VARIABLE_PATTERN.search("{{user_id}}")
        assert match is not None
        assert match.group(1) == "user_id"

    def test_consecutive_variables(self) -> None:
        """Test consecutive variables without space."""
        matches = VARIABLE_PATTERN.findall("{{a}}{{b}}")
        assert matches == ["a", "b"]


class TestRenderResult:
    """Tests for RenderResult dataclass."""

    def test_render_result_creation(self) -> None:
        """Test creating a RenderResult."""
        result = RenderResult(content="Hello world", missing_variables=[])
        assert result.content == "Hello world"
        assert result.missing_variables == []

    def test_render_result_with_missing(self) -> None:
        """Test RenderResult with missing variables."""
        result = RenderResult(content="Hello {{name}}", missing_variables=["name"])
        assert result.missing_variables == ["name"]


class TestPromptTemplateManager:
    """Tests for PromptTemplateManager."""

    @pytest.fixture
    def manager(self) -> PromptTemplateManager:
        """Create a fresh manager instance."""
        return PromptTemplateManager()

    def test_register_and_load_template(self, manager: PromptTemplateManager) -> None:
        """Test registering and loading a template."""
        manager.register_template("greeting", "Hello {{name}}!")
        template = manager.load_template("greeting")
        assert template == "Hello {{name}}!"

    def test_load_nonexistent_template(self, manager: PromptTemplateManager) -> None:
        """Test loading a template that doesn't exist."""
        template = manager.load_template("nonexistent")
        assert template is None

    def test_render_simple(self, manager: PromptTemplateManager) -> None:
        """Test rendering a simple template."""
        result = manager.render("Hello {{name}}!", {"name": "Alice"})
        assert result.content == "Hello Alice!"
        assert result.missing_variables == []

    def test_render_multiple_variables(
        self, manager: PromptTemplateManager
    ) -> None:
        """Test rendering with multiple variables."""
        result = manager.render(
            "{{greeting}} {{name}}!",
            {"greeting": "Hello", "name": "Bob"},
        )
        assert result.content == "Hello Bob!"
        assert result.missing_variables == []

    def test_render_missing_variable(self, manager: PromptTemplateManager) -> None:
        """Test rendering with missing variable."""
        result = manager.render("Hello {{name}}!", {})
        assert result.content == "Hello {{name}}!"
        assert result.missing_variables == ["name"]

    def test_render_missing_variables(
        self, manager: PromptTemplateManager
    ) -> None:
        """Test rendering with multiple missing variables."""
        result = manager.render("{{a}} and {{b}}", {})
        assert result.content == "{{a}} and {{b}}"
        assert result.missing_variables == ["a", "b"]

    def test_render_strict_mode_raises(
        self, manager: PromptTemplateManager
    ) -> None:
        """Test that strict mode raises on missing variables."""
        with pytest.raises(ValueError, match="Missing template variables"):
            manager.render("Hello {{name}}!", {}, strict=True)

    def test_render_strict_mode_passes(
        self, manager: PromptTemplateManager
    ) -> None:
        """Test that strict mode passes when all variables provided."""
        result = manager.render("Hello {{name}}!", {"name": "Alice"}, strict=True)
        assert result.content == "Hello Alice!"
        assert result.missing_variables == []

    def test_render_template(self, manager: PromptTemplateManager) -> None:
        """Test rendering a registered template."""
        manager.register_template("greeting", "Hello {{name}}!")
        result = manager.render_template("greeting", {"name": "Charlie"})
        assert result is not None
        assert result.content == "Hello Charlie!"
        assert result.missing_variables == []

    def test_render_template_not_found(
        self, manager: PromptTemplateManager
    ) -> None:
        """Test rendering a template that doesn't exist."""
        result = manager.render_template("nonexistent", {})
        assert result is None

    def test_validate_template(self, manager: PromptTemplateManager) -> None:
        """Test extracting variables from template."""
        variables = manager.validate_template("{{a}} and {{b}} and {{c}}")
        assert variables == ["a", "b", "c"]

    def test_validate_template_empty(self, manager: PromptTemplateManager) -> None:
        """Test validating template with no variables."""
        variables = manager.validate_template("No variables here")
        assert variables == []


class TestDefaultTemplates:
    """Tests for default templates."""

    def test_system_default_has_variables(self) -> None:
        """Test system_default template has expected variables."""
        template = DEFAULT_TEMPLATES["system_default"]
        variables = VARIABLE_PATTERN.findall(template)
        assert "user_id" in variables
        assert "session_id" in variables
        assert "working_dir" in variables

    def test_code_generation_has_variables(self) -> None:
        """Test code_generation template has expected variables."""
        template = DEFAULT_TEMPLATES["code_generation"]
        variables = VARIABLE_PATTERN.findall(template)
        assert "language" in variables
        assert "action" in variables
        assert "requirements" in variables
        assert "code" in variables

    def test_debugging_has_variables(self) -> None:
        """Test debugging template has expected variables."""
        template = DEFAULT_TEMPLATES["debugging"]
        variables = VARIABLE_PATTERN.findall(template)
        assert "error_message" in variables
        assert "code" in variables
        assert "context" in variables

    def test_all_default_templates_exist(self) -> None:
        """Test all expected default templates exist."""
        expected = [
            "system_default",
            "code_generation",
            "code_review",
            "debugging",
            "test_generation",
        ]
        for name in expected:
            assert name in DEFAULT_TEMPLATES
            assert DEFAULT_TEMPLATES[name]
