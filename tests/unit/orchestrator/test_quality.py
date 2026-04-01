"""Tests for the quality checker."""

from __future__ import annotations

import pytest

from mozi.orchestrator.quality import (
    CheckType,
    QualityChecker,
    QualityIssue,
    QualityLevel,
    QualityResult,
)


class TestQualityLevel:
    """Tests for QualityLevel enum."""

    def test_level_values(self) -> None:
        """Test QualityLevel values."""
        assert QualityLevel.EXCELLENT.value == "excellent"
        assert QualityLevel.GOOD.value == "good"
        assert QualityLevel.ACCEPTABLE.value == "acceptable"
        assert QualityLevel.POOR.value == "poor"
        assert QualityLevel.FAIL.value == "fail"


class TestQualityIssue:
    """Tests for QualityIssue dataclass."""

    def test_create_issue(self) -> None:
        """Test creating a QualityIssue."""
        issue = QualityIssue(
            check_type=CheckType.SYNTAX,
            severity="error",
            message="Syntax error",
            line=10,
        )
        assert issue.check_type == CheckType.SYNTAX
        assert issue.severity == "error"
        assert issue.line == 10

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        issue = QualityIssue(
            check_type=CheckType.STYLE,
            severity="warning",
            message="Line too long",
            location="main.py",
            line=5,
            rule_id="E501",
        )
        result = issue.to_dict()
        assert result["check_type"] == "style"
        assert result["severity"] == "warning"
        assert result["rule_id"] == "E501"


class TestQualityResult:
    """Tests for QualityResult dataclass."""

    def test_create_result(self) -> None:
        """Test creating a QualityResult."""
        result = QualityResult(
            level=QualityLevel.GOOD,
            score=85.0,
            passed_checks=4,
            failed_checks=1,
        )
        assert result.level == QualityLevel.GOOD
        assert result.score == 85.0
        assert result.passed_checks == 4
        assert result.failed_checks == 1

    def test_is_acceptable(self) -> None:
        """Test is_acceptable property."""
        excellent = QualityResult(level=QualityLevel.EXCELLENT, score=95.0)
        good = QualityResult(level=QualityLevel.GOOD, score=85.0)
        acceptable = QualityResult(level=QualityLevel.ACCEPTABLE, score=65.0)
        poor = QualityResult(level=QualityLevel.POOR, score=45.0)
        fail = QualityResult(level=QualityLevel.FAIL, score=20.0)

        assert excellent.is_acceptable is True
        assert good.is_acceptable is True
        assert acceptable.is_acceptable is True
        assert poor.is_acceptable is False
        assert fail.is_acceptable is False


class TestQualityChecker:
    """Tests for QualityChecker."""

    def test_default_thresholds(self) -> None:
        """Test default threshold values."""
        checker = QualityChecker()
        assert checker._thresholds["complexity"] == 15.0
        assert checker._thresholds["coverage"] == 80.0
        assert checker._thresholds["max_line_length"] == 100

    def test_custom_thresholds(self) -> None:
        """Test custom threshold values."""
        checker = QualityChecker(thresholds={"max_line_length": 80})
        assert checker._thresholds["max_line_length"] == 80

    @pytest.mark.asyncio
    async def test_check_syntax_valid_python(self) -> None:
        """Test checking valid Python syntax."""
        checker = QualityChecker()
        result = await checker.check_syntax("def foo():\n    pass", "python")
        assert result.level == QualityLevel.EXCELLENT
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_check_syntax_invalid_python(self) -> None:
        """Test checking invalid Python syntax."""
        checker = QualityChecker()
        result = await checker.check_syntax("def foo(:\n    pass", "python")
        assert result.level == QualityLevel.FAIL
        assert result.score == 0.0
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_check_style_valid(self) -> None:
        """Test checking valid style."""
        checker = QualityChecker()
        content = "def foo():\n    pass\n"
        result = await checker.check_style(content)
        assert result.score >= 80.0

    @pytest.mark.asyncio
    async def test_check_style_long_line(self) -> None:
        """Test checking long lines."""
        checker = QualityChecker()
        long_line = "x" * 150 + "\n"
        result = await checker.check_style(long_line)
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_check_style_wildcard_import(self) -> None:
        """Test checking wildcard imports."""
        checker = QualityChecker()
        content = "from os import *\n"
        result = await checker.check_style(content)
        assert any("Wildcard" in issue.message for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_security_clean(self) -> None:
        """Test checking clean code."""
        checker = QualityChecker()
        content = "def foo():\n    return 42\n"
        result = await checker.check_security(content)
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_check_security_eval(self) -> None:
        """Test checking dangerous eval."""
        checker = QualityChecker()
        content = "eval('print(1)')\n"
        result = await checker.check_security(content)
        assert result.score < 100.0
        assert any("eval" in issue.message for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_security_hardcoded_password(self) -> None:
        """Test checking hardcoded passwords."""
        checker = QualityChecker()
        content = "password = 'secret123'\n"
        result = await checker.check_security(content)
        assert result.score < 100.0
        assert any("password" in issue.message.lower() for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_complexity_simple(self) -> None:
        """Test checking simple code complexity."""
        checker = QualityChecker()
        content = "def foo():\n    return 1\n"
        result = await checker.check_complexity(content)
        assert result.score >= 80.0

    def test_score_to_level(self) -> None:
        """Test score to level conversion."""
        checker = QualityChecker()
        assert checker._score_to_level(100) == QualityLevel.EXCELLENT
        assert checker._score_to_level(95) == QualityLevel.EXCELLENT
        assert checker._score_to_level(90) == QualityLevel.GOOD
        assert checker._score_to_level(85) == QualityLevel.GOOD
        assert checker._score_to_level(70) == QualityLevel.ACCEPTABLE
        assert checker._score_to_level(50) == QualityLevel.POOR
        assert checker._score_to_level(30) == QualityLevel.FAIL
