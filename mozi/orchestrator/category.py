"""Category module for Mozi orchestrator.

Provides task categorization based on complexity and type analysis.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class Category(Enum):
    """Task category based on complexity analysis.

    Categories:
        QUICK: Simple tasks that can be completed in single pass
        DEEP: Complex tasks requiring multi-step reasoning
        STRATEGIC: High-impact tasks requiring planning
    """

    QUICK = "quick"
    DEEP = "deep"
    STRATEGIC = "strategic"


class ComplexityScore:
    """Complexity scoring result.

    Attributes:
        score: Numeric complexity score (0-100).
        category: Assigned category based on score.
        factors: List of factors that contributed to the score.
    """

    def __init__(
        self,
        score: float,
        category: Category,
        factors: list[str] | None = None,
    ) -> None:
        """Initialize complexity score.

        Args:
            score: Numeric score between 0-100.
            category: Task category.
            factors: List of scoring factors.
        """
        self.score = score
        self.category = category
        self.factors = factors or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "score": self.score,
            "category": self.category.value,
            "factors": self.factors,
        }


class CategoryRouter:
    """Routes tasks to appropriate handlers based on category.

    Analyzes task complexity and assigns to appropriate category
    for optimal processing strategy.
    """

    # Complexity thresholds
    QUICK_THRESHOLD = 40.0
    DEEP_THRESHOLD = 70.0

    def __init__(
        self,
        quick_threshold: float | None = None,
        deep_threshold: float | None = None,
    ) -> None:
        """Initialize the category router.

        Args:
            quick_threshold: Maximum score for QUICK category.
            deep_threshold: Maximum score for DEEP category.
        """
        self._quick_threshold = quick_threshold or self.QUICK_THRESHOLD
        self._deep_threshold = deep_threshold or self.DEEP_THRESHOLD

    def route(
        self,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> Category:
        """Route a task to appropriate category.

        Analyzes the task description and context to determine
        the appropriate processing category.

        Args:
            task_description: Description of the task.
            context: Optional context information.

        Returns:
            Assigned category for the task.
        """
        score = self._calculate_complexity(task_description, context or {})
        return self._score_to_category(score)

    def analyze(
        self,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> ComplexityScore:
        """Analyze task complexity in detail.

        Args:
            task_description: Description of the task.
            context: Optional context information.

        Returns:
            Detailed complexity analysis result.
        """
        score = self._calculate_complexity(task_description, context or {})
        category = self._score_to_category(score)
        return ComplexityScore(score=score, category=category, factors=self._get_factors())

    def _calculate_complexity(
        self,
        task_description: str,
        context: dict[str, Any],
    ) -> float:
        """Calculate complexity score for a task.

        Args:
            task_description: Task description.
            context: Task context.

        Returns:
            Complexity score (0-100).
        """
        score = 0.0
        self._factors = []

        # Length-based scoring
        desc_len = len(task_description)
        if desc_len > 500:
            score += 20.0
            self._factors.append("long_description")
        elif desc_len > 200:
            score += 10.0
            self._factors.append("medium_description")

        # Context-based scoring
        if context.get("requires_planning"):
            score += 25.0
            self._factors.append("requires_planning")

        if context.get("multi_step"):
            score += 20.0
            self._factors.append("multi_step")

        if context.get("file_operations"):
            score += 10.0
            self._factors.append("file_operations")

        if context.get("code_review"):
            score += 15.0
            self._factors.append("code_review")

        if context.get("testing"):
            score += 10.0
            self._factors.append("testing")

        # Cap at 100
        return min(score, 100.0)

    def _score_to_category(self, score: float) -> Category:
        """Convert score to category.

        Args:
            score: Complexity score.

        Returns:
            Corresponding category.
        """
        if score <= self._quick_threshold:
            return Category.QUICK
        elif score <= self._deep_threshold:
            return Category.DEEP
        else:
            return Category.STRATEGIC

    def _get_factors(self) -> list[str]:
        """Get the scoring factors from last calculation."""
        return getattr(self, "_factors", [])
