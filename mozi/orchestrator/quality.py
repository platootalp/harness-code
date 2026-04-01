"""Quality checker for Mozi orchestrator.

Responsible for validating code quality, checking standards,
and ensuring deliverables meet quality thresholds.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class QualityLevel(Enum):
    """Quality level classification."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    FAIL = "fail"


class CheckType(Enum):
    """Type of quality check."""

    SYNTAX = "syntax"
    STYLE = "style"
    COMPLEXITY = "complexity"
    COVERAGE = "coverage"
    SECURITY = "security"
    DOCUMENTATION = "documentation"


@dataclass
class QualityIssue:
    """Represents a quality issue found during checking.

    Attributes:
        check_type: Type of check that found the issue.
        severity: Severity level (error/warning/info).
        message: Description of the issue.
        location: File or location where issue was found.
        line: Line number (if applicable).
        rule_id: Rule that was violated (if applicable).
    """

    check_type: CheckType
    severity: str
    message: str
    location: str = ""
    line: int | None = None
    rule_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_type": self.check_type.value,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
            "line": self.line,
            "rule_id": self.rule_id,
        }


@dataclass
class QualityResult:
    """Result of a quality check operation.

    Attributes:
        level: Overall quality level.
        score: Numeric quality score (0-100).
        issues: List of issues found.
        passed_checks: Number of passed checks.
        failed_checks: Number of failed checks.
        metadata: Additional metadata.
    """

    level: QualityLevel
    score: float
    issues: list[QualityIssue] = field(default_factory=list)
    passed_checks: int = 0
    failed_checks: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "score": self.score,
            "issues": [i.to_dict() for i in self.issues],
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "metadata": self.metadata,
        }

    @property
    def is_acceptable(self) -> bool:
        """Check if quality is acceptable for delivery."""
        return self.level in {
            QualityLevel.EXCELLENT,
            QualityLevel.GOOD,
            QualityLevel.ACCEPTABLE,
        }


class QualityChecker:
    """Checks code quality against defined standards.

    Performs various quality checks including:
    - Syntax validation
    - Style checking
    - Complexity analysis
    - Security scanning
    - Documentation verification
    """

    DEFAULT_THRESHOLDS = {
        "complexity": 15.0,
        "coverage": 80.0,
        "max_line_length": 100,
        "max_function_length": 50,
    }

    def __init__(
        self,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        """Initialize the quality checker.

        Args:
            thresholds: Custom threshold values.
        """
        self._thresholds = {**self.DEFAULT_THRESHOLDS}
        if thresholds:
            self._thresholds.update(thresholds)

    async def check(
        self,
        content: str,
        file_path: str = "",
        file_type: str = "python",
    ) -> QualityResult:
        """Perform quality check on content.

        Args:
            content: Code content to check.
            file_path: Optional file path for context.
            file_type: Type of file (python, typescript, etc.).

        Returns:
            Quality check result.
        """
        issues: list[QualityIssue] = []
        passed = 0
        failed = 0

        syntax_result = await self.check_syntax(content, file_type)
        issues.extend(syntax_result.issues)
        if syntax_result.is_acceptable:
            passed += 1
        else:
            failed += 1

        style_result = await self.check_style(content, file_type)
        issues.extend(style_result.issues)
        if style_result.is_acceptable:
            passed += 1
        else:
            failed += 1

        complexity_result = await self.check_complexity(content)
        issues.extend(complexity_result.issues)
        if complexity_result.is_acceptable:
            passed += 1
        else:
            failed += 1

        security_result = await self.check_security(content)
        issues.extend(security_result.issues)
        if security_result.is_acceptable:
            passed += 1
        else:
            failed += 1

        total_checks = passed + failed
        score = (passed / total_checks * 100) if total_checks > 0 else 0.0

        level = self._score_to_level(score)

        return QualityResult(
            level=level,
            score=score,
            issues=issues,
            passed_checks=passed,
            failed_checks=failed,
            metadata={
                "file_path": file_path,
                "file_type": file_type,
                "thresholds": self._thresholds,
            },
        )

    async def check_syntax(
        self,
        content: str,
        file_type: str = "python",
    ) -> QualityResult:
        """Check syntax validity.

        Args:
            content: Code content to check.
            file_type: Type of file.

        Returns:
            Syntax check result.
        """
        issues: list[QualityIssue] = []
        is_valid = False

        if file_type == "python":
            try:
                import ast

                ast.parse(content)
                is_valid = True
            except SyntaxError as e:
                issues.append(
                    QualityIssue(
                        check_type=CheckType.SYNTAX,
                        severity="error",
                        message=f"Syntax error: {e.msg}",
                        location="",
                        line=e.lineno,
                        rule_id="E999",
                    )
                )
        elif file_type in ("typescript", "javascript"):
            is_valid = True
        else:
            is_valid = True

        return QualityResult(
            level=QualityLevel.EXCELLENT if is_valid else QualityLevel.FAIL,
            score=100.0 if is_valid else 0.0,
            issues=issues,
            passed_checks=1 if is_valid else 0,
            failed_checks=0 if is_valid else 1,
        )

    async def check_style(
        self,
        content: str,
        file_type: str = "python",
    ) -> QualityResult:
        """Check code style.

        Args:
            content: Code content to check.
            file_type: Type of file.

        Returns:
            Style check result.
        """
        issues: list[QualityIssue] = []
        max_len = int(self._thresholds["max_line_length"])
        passed = 0
        failed = 0

        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if len(line) > max_len:
                issues.append(
                    QualityIssue(
                        check_type=CheckType.STYLE,
                        severity="warning",
                        message=f"Line exceeds {max_len} characters ({len(line)} chars)",
                        line=i,
                        rule_id="E501",
                    )
                )
                failed += 1
            elif line.rstrip() != line:
                issues.append(
                    QualityIssue(
                        check_type=CheckType.STYLE,
                        severity="info",
                        message="Trailing whitespace",
                        line=i,
                        rule_id="W291",
                    )
                )

        if file_type == "python":
            if "import *" in content:
                issues.append(
                    QualityIssue(
                        check_type=CheckType.STYLE,
                        severity="warning",
                        message="Wildcard imports are discouraged",
                        rule_id="F403",
                    )
                )
                failed += 1

            if re.search(r"print\s*\(", content) and "__main__" not in content:
                issues.append(
                    QualityIssue(
                        check_type=CheckType.STYLE,
                        severity="info",
                        message="print statement found - consider logging",
                        rule_id="T201",
                    )
                )

        total_lines = len(lines)
        issue_count = len(issues)
        score = max(0.0, 100.0 - (issue_count / max(total_lines, 1) * 100))

        return QualityResult(
            level=self._score_to_level(score),
            score=score,
            issues=issues,
            passed_checks=passed,
            failed_checks=failed,
        )

    async def check_complexity(self, content: str) -> QualityResult:
        """Check code complexity.

        Args:
            content: Code content to check.

        Returns:
            Complexity check result.
        """
        issues: list[QualityIssue] = []
        max_complexity = float(self._thresholds["complexity"])

        if "def " not in content and "function " not in content:
            return QualityResult(
                level=QualityLevel.EXCELLENT,
                score=100.0,
                issues=[],
                passed_checks=1,
                failed_checks=0,
            )

        function_pattern = r"(?:def|function)\s+\w+\s*\([^)]*\):"
        functions = re.findall(function_pattern, content)

        for func in functions:
            func_lines = content.split(func)[1].split("\n\n")[0].count("\n") + 1
            if func_lines > int(self._thresholds["max_function_length"]):
                issues.append(
                    QualityIssue(
                        check_type=CheckType.COMPLEXITY,
                        severity="warning",
                        message=f"Function exceeds {self._thresholds['max_function_length']} lines",
                        rule_id="C901",
                    )
                )

        try:
            import ast

            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = self._calculate_cyclomatic_complexity(node)
                    if complexity > max_complexity:
                        issues.append(
                            QualityIssue(
                                check_type=CheckType.COMPLEXITY,
                                severity="warning",
                                message=f"Function '{node.name}' has complexity {complexity:.1f} "
                                f"(threshold: {max_complexity})",
                                rule_id="CF901",
                            )
                        )
        except Exception:
            pass

        issue_count = len(issues)
        score = max(0.0, 100.0 - (issue_count * 10))

        return QualityResult(
            level=self._score_to_level(score),
            score=score,
            issues=issues,
            passed_checks=1 if issue_count == 0 else 0,
            failed_checks=issue_count,
        )

    async def check_security(self, content: str) -> QualityResult:
        """Check for security issues.

        Args:
            content: Code content to check.

        Returns:
            Security check result.
        """
        issues: list[QualityIssue] = []
        passed = 0
        failed = 0

        dangerous_patterns = [
            (r"eval\s*\(", "Use of eval() is a security risk", "S101"),
            (r"exec\s*\(", "Use of exec() is a security risk", "S102"),
            (r"__import__\s*\(", "Dynamic imports are a security risk", "S104"),
            (r"pickle\.loads?", "Use of pickle is a security risk", "S301"),
            (r"shutil\.rmtree\s*\(", "Recursive deletion is dangerous", "S104"),
            (r"os\.system\s*\(", "Use of os.system() is risky", "S602"),
            (r"subprocess\.shell\s*=\s*True", "shell=True is a security risk", "S602"),
            (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password detected", "S106"),
            (r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key detected", "S106"),
            (r"secret\s*=\s*['\"][^'\"]+['\"]", "Hardcoded secret detected", "S106"),
        ]

        for pattern, message, rule_id in dangerous_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                issues.append(
                    QualityIssue(
                        check_type=CheckType.SECURITY,
                        severity="error",
                        message=message,
                        line=line_num,
                        rule_id=rule_id,
                    )
                )
                failed += 1

        if failed == 0:
            passed = 1

        score = max(0.0, 100.0 - (failed * 20))

        return QualityResult(
            level=self._score_to_level(score),
            score=score,
            issues=issues,
            passed_checks=passed,
            failed_checks=failed,
        )

    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> float:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1.0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1.0
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _score_to_level(self, score: float) -> QualityLevel:
        """Convert numeric score to quality level.

        Args:
            score: Numeric score (0-100).

        Returns:
            Corresponding quality level.
        """
        if score >= 95:
            return QualityLevel.EXCELLENT
        elif score >= 80:
            return QualityLevel.GOOD
        elif score >= 60:
            return QualityLevel.ACCEPTABLE
        elif score >= 40:
            return QualityLevel.POOR
        else:
            return QualityLevel.FAIL
