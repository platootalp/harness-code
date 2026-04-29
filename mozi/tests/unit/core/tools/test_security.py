"""Unit tests for security module."""


from mozi.core.tools.security import (
    DangerousFunctionDetector,
    PermissionLevel,
    SecurityViolation,
    ViolationSeverity,
    path_whitelist_validation,
)


class TestPermissionLevel:
    """Tests for PermissionLevel enum."""

    def test_permission_levels_exist(self) -> None:
        """Test all permission levels are defined."""
        assert PermissionLevel.LEVEL_0.value == 0
        assert PermissionLevel.LEVEL_1.value == 1
        assert PermissionLevel.LEVEL_2.value == 2
        assert PermissionLevel.LEVEL_3.value == 3
        assert PermissionLevel.LEVEL_4.value == 4

    def test_permission_level_comparison_by_value(self) -> None:
        """Test permission levels can be compared by their integer values."""
        assert PermissionLevel.LEVEL_0.value < PermissionLevel.LEVEL_1.value
        assert PermissionLevel.LEVEL_3.value > PermissionLevel.LEVEL_2.value


class TestViolationSeverity:
    """Tests for ViolationSeverity enum."""

    def test_severity_levels_exist(self) -> None:
        """Test all severity levels are defined."""
        assert ViolationSeverity.LOW.value == "low"
        assert ViolationSeverity.MEDIUM.value == "medium"
        assert ViolationSeverity.HIGH.value == "high"
        assert ViolationSeverity.CRITICAL.value == "critical"


class TestSecurityViolation:
    """Tests for SecurityViolation dataclass."""

    def test_security_violation_creation(self) -> None:
        """Test creating a SecurityViolation."""
        violation = SecurityViolation(
            severity=ViolationSeverity.HIGH,
            message="Dangerous function detected",
            function_name="eval",
        )
        assert violation.severity == ViolationSeverity.HIGH
        assert violation.message == "Dangerous function detected"
        assert violation.function_name == "eval"
        assert violation.details is None

    def test_security_violation_with_details(self) -> None:
        """Test creating a SecurityViolation with details."""
        violation = SecurityViolation(
            severity=ViolationSeverity.CRITICAL,
            message="Critical issue",
            function_name="exec",
            details={"line": 42, "column": 10},
        )
        assert violation.details == {"line": 42, "column": 10}


class TestDangerousFunctionDetector:
    """Tests for DangerousFunctionDetector class."""

    def test_detector_finds_eval(self) -> None:
        """Test detector finds eval function."""
        detector = DangerousFunctionDetector()
        violations = detector.detect("result = eval(code)")
        assert len(violations) > 0
        assert any(v.function_name == "eval" for v in violations)

    def test_detector_finds_exec(self) -> None:
        """Test detector finds exec function."""
        detector = DangerousFunctionDetector()
        violations = detector.detect("exec('print(1)')")
        assert len(violations) > 0
        assert any(v.function_name == "exec" for v in violations)

    def test_detector_finds_os_system(self) -> None:
        """Test detector finds os.system."""
        detector = DangerousFunctionDetector()
        violations = detector.detect("os.system('ls')")
        assert len(violations) > 0
        assert any(v.function_name == "os.system" for v in violations)

    def test_detector_no_violations_in_safe_code(self) -> None:
        """Test detector returns empty list for safe code."""
        detector = DangerousFunctionDetector()
        code = """
def calculate(x):
    return x * 2

result = calculate(10)
"""
        violations = detector.detect(code)
        assert len(violations) == 0


class TestPathWhitelistValidation:
    """Tests for path_whitelist_validation function."""

    def test_empty_whitelist_allows_all(self) -> None:
        """Test that empty whitelist allows all paths."""
        is_valid, error = path_whitelist_validation("/any/path", [])
        assert is_valid is True
        assert error is None

    def test_path_within_whitelist(self) -> None:
        """Test path within whitelist is allowed."""
        is_valid, error = path_whitelist_validation(
            "/Users/lijunyi/road/src/src/file.py",
            ["/Users/lijunyi/road/src"],
        )
        assert is_valid is True
        assert error is None

    def test_path_outside_whitelist(self) -> None:
        """Test path outside whitelist is denied."""
        is_valid, error = path_whitelist_validation(
            "/etc/passwd",
            ["/Users/lijunyi/road/src"],
        )
        assert is_valid is False
        assert "/etc/passwd" in error

    def test_exact_match(self) -> None:
        """Test exact path match is allowed."""
        is_valid, error = path_whitelist_validation(
            "/Users/lijunyi/road/src",
            ["/Users/lijunyi/road/src"],
        )
        assert is_valid is True
