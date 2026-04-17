"""Prompt template manager.

Provides simple template rendering with variable substitution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Pattern to match {{variable}} placeholders
VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


@dataclass
class RenderResult:
    """Result of template rendering.

    Attributes:
        content: Rendered template content.
        missing_variables: Variables that were not provided.
    """

    content: str
    missing_variables: list[str]


class PromptTemplateManager:
    """Manager for prompt templates.

    Supports simple {{variable}} placeholder syntax for variable substitution.
    """

    def __init__(self) -> None:
        """Initialize prompt template manager."""
        self._templates: dict[str, str] = {}

    def register_template(self, name: str, template: str) -> None:
        """Register a template.

        Args:
            name: Template name.
            template: Template content with {{variable}} placeholders.
        """
        self._templates[name] = template

    def load_template(self, name: str) -> str | None:
        """Load a registered template.

        Args:
            name: Template name.

        Returns:
            Template content if found, None otherwise.
        """
        return self._templates.get(name)

    def render(
        self,
        template: str,
        variables: dict[str, Any],
        strict: bool = False,
    ) -> RenderResult:
        """Render a template with variable substitution.

        Args:
            template: Template content with {{variable}} placeholders.
            variables: Dictionary of variable values.
            strict: If True, raise error on missing variables.

        Returns:
            RenderResult with rendered content and missing variables.

        Raises:
            ValueError: If strict=True and variables are missing.
        """
        missing: list[str] = []

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            if var_name in variables:
                return str(variables[var_name])
            missing.append(var_name)
            return match.group(0)  # Keep placeholder if not found

        content = VARIABLE_PATTERN.sub(replace_var, template)

        if strict and missing:
            raise ValueError(f"Missing template variables: {', '.join(missing)}")

        return RenderResult(content=content, missing_variables=missing)

    def render_template(
        self,
        name: str,
        variables: dict[str, Any],
        strict: bool = False,
    ) -> RenderResult | None:
        """Render a registered template.

        Args:
            name: Template name.
            variables: Dictionary of variable values.
            strict: If True, raise error on missing variables.

        Returns:
            RenderResult if template exists, None otherwise.

        Raises:
            ValueError: If strict=True and variables are missing.
        """
        template = self._templates.get(name)
        if template is None:
            return None

        return self.render(template, variables, strict=strict)

    def validate_template(self, template: str) -> list[str]:
        """Get list of variables in a template.

        Args:
            template: Template content.

        Returns:
            List of variable names found in template.
        """
        return VARIABLE_PATTERN.findall(template)


# Predefined templates
DEFAULT_TEMPLATES = {
    "system_default": """You are a professional AI coding assistant.
Current user: {{user_id}}
Session: {{session_id}}
Working directory: {{working_dir}}

Provide helpful, accurate, and secure assistance.""",
    "code_generation": """Generate {{language}} code for the following task:
{{action}}

Requirements:
{{requirements}}

Code to work with:
{{code}}""",
    "code_review": """Review the following {{language}} code:

{{code}}

Focus areas: {{focus_areas}}""",
    "debugging": """Debug the following error:

Error message:
{{error_message}}

Code context:
{{code}}

Additional context:
{{context}}""",
    "test_generation": """Generate tests for the following code:

{{code}}

Test framework: {{test_framework}}
Coverage target: {{coverage_target}}""",
}
