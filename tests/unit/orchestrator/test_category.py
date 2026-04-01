"""Tests for the category module."""

from __future__ import annotations

import pytest

from mozi.orchestrator.category import Category, CategoryRouter, ComplexityScore


class TestCategory:
    """Tests for Category enum."""

    def test_category_values(self) -> None:
        """Test Category enum values."""
        assert Category.QUICK.value == "quick"
        assert Category.DEEP.value == "deep"
        assert Category.STRATEGIC.value == "strategic"

    def test_category_comparison(self) -> None:
        """Test Category comparison."""
        assert Category.QUICK == Category.QUICK
        assert Category.DEEP != Category.QUICK


class TestComplexityScore:
    """Tests for ComplexityScore dataclass."""

    def test_create_with_defaults(self) -> None:
        """Test creating ComplexityScore with defaults."""
        score = ComplexityScore(score=50.0, category=Category.DEEP)
        assert score.score == 50.0
        assert score.category == Category.DEEP
        assert score.factors == []

    def test_create_with_factors(self) -> None:
        """Test creating ComplexityScore with factors."""
        factors = ["multi_step", "requires_planning"]
        score = ComplexityScore(score=75.0, category=Category.STRATEGIC, factors=factors)
        assert score.score == 75.0
        assert score.category == Category.STRATEGIC
        assert score.factors == factors

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        score = ComplexityScore(score=50.0, category=Category.DEEP, factors=["test"])
        result = score.to_dict()
        assert result["score"] == 50.0
        assert result["category"] == "deep"
        assert result["factors"] == ["test"]


class TestCategoryRouter:
    """Tests for CategoryRouter."""

    def test_default_thresholds(self) -> None:
        """Test default threshold values."""
        router = CategoryRouter()
        assert router._quick_threshold == 40.0
        assert router._deep_threshold == 70.0

    def test_custom_thresholds(self) -> None:
        """Test custom threshold values."""
        router = CategoryRouter(quick_threshold=30.0, deep_threshold=60.0)
        assert router._quick_threshold == 30.0
        assert router._deep_threshold == 60.0

    @pytest.mark.asyncio
    async def test_route_quick_task(self) -> None:
        """Test routing a quick task."""
        router = CategoryRouter()
        category = router.route("Fix typo in variable name")
        assert category == Category.QUICK

    @pytest.mark.asyncio
    async def test_route_deep_task(self) -> None:
        """Test routing a deep task."""
        router = CategoryRouter()
        context = {"multi_step": True, "requires_planning": True}
        category = router.route("Implement authentication system", context=context)
        assert category == Category.DEEP

    @pytest.mark.asyncio
    async def test_route_strategic_task(self) -> None:
        """Test routing a strategic task."""
        router = CategoryRouter()
        context = {
            "requires_planning": True,
            "multi_step": True,
            "file_operations": True,
            "code_review": True,
            "testing": True,
        }
        description = "A" * 600
        category = router.route(description, context=context)
        assert category == Category.STRATEGIC

    @pytest.mark.asyncio
    async def test_route_long_description(self) -> None:
        """Test routing with long description."""
        router = CategoryRouter()
        description = "A" * 600 + " with multi-step planning"
        context = {"multi_step": True, "requires_planning": True}
        category = router.route(description, context=context)
        assert category == Category.DEEP

    @pytest.mark.asyncio
    async def test_analyze_returns_complexity_score(self) -> None:
        """Test analyze returns ComplexityScore."""
        router = CategoryRouter()
        result = router.analyze("Fix typo")
        assert isinstance(result, ComplexityScore)
        assert result.score == 0.0
        assert result.category == Category.QUICK

    @pytest.mark.asyncio
    async def test_analyze_with_context(self) -> None:
        """Test analyze with context."""
        router = CategoryRouter()
        context = {"requires_planning": True, "multi_step": True}
        result = router.analyze("Build system", context=context)
        assert result.score >= 45.0
        assert "requires_planning" in result.factors
        assert "multi_step" in result.factors

    def test_score_to_category_boundaries(self) -> None:
        """Test score to category boundaries."""
        router = CategoryRouter()
        assert router._score_to_category(0.0) == Category.QUICK
        assert router._score_to_category(40.0) == Category.QUICK
        assert router._score_to_category(41.0) == Category.DEEP
        assert router._score_to_category(70.0) == Category.DEEP
        assert router._score_to_category(71.0) == Category.STRATEGIC
        assert router._score_to_category(100.0) == Category.STRATEGIC
