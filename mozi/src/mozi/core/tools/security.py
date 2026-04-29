"""Security components for tools - Dangerous function detection and path validation."""

from dataclasses import dataclass, field
from enum import Enum
from re import Pattern
from typing import Any


class PermissionLevel(Enum):
    """Permission levels for tool execution.

    LEVEL_0: No special permissions, sandboxed.
    LEVEL_1: Basic file read access.
    LEVEL_2: File write access.
    LEVEL_3: System command execution.
    LEVEL_4: Full access (dangerous).
    """

    LEVEL_0 = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4


class ViolationSeverity(Enum):
    """Severity level for security violations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityViolation:
    """Represents a security violation detected during tool execution.

    Attributes:
        severity: How severe the violation is.
        message: Human-readable description.
        function_name: Name of the dangerous function detected.
        details: Additional context about the violation.
    """

    severity: ViolationSeverity
    message: str
    function_name: str | None = None
    details: dict[str, Any] | None = None


# Dangerous function patterns that should be blocked
DANGEROUS_FUNCTIONS: list[str] = [
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "breakpoint",
    "exit",
    "quit",
    "license",
    "help",
    "dir",
    "vars",
    "globals",
    "locals",
    "reload",
    "memoryview",
    "settrace",
    "sys.settrace",
    "os.system",
    "os.popen",
    "subprocess.call",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.shell",
]


@dataclass
class DangerousFunctionDetector:
    """Detects dangerous function usage in code.

    This class provides static analysis to detect potentially
    dangerous function calls that could compromise security.
    """

    patterns: list[Pattern[str]] = field(default_factory=list)
    _initialized: bool = False

    def __post_init__(self) -> None:
        """Initialize regex patterns for dangerous functions."""
        if not self._initialized:
            import re

            self.patterns = [
                re.compile(rf"\b{func}\s*\(")
                for func in DANGEROUS_FUNCTIONS
                if func.isidentifier() or "." in func
            ]
            self._initialized = True

    def detect(self, code: str) -> list[SecurityViolation]:
        """Scan code for dangerous function usage.

        Args:
            code: Source code to scan.

        Returns:
            List of detected security violations.
        """
        violations: list[SecurityViolation] = []

        for pattern in self.patterns:
            for match in pattern.finditer(code):
                func_name = match.group(0).rstrip("(").strip()
                violations.append(
                    SecurityViolation(
                        severity=ViolationSeverity.HIGH,
                        message=f"Dangerous function detected: {func_name}",
                        function_name=func_name,
                        details={"position": match.start()},
                    )
                )

        return violations


def path_whitelist_validation(
    file_path: str, allowed_paths: list[str]
) -> tuple[bool, str | None]:
    """Validate that a file path is within allowed paths.

    Args:
        file_path: Path to validate.
        allowed_paths: List of allowed base paths.

    Returns:
        Tuple of (is_valid, error_message).
    """
    import os

    if not allowed_paths:
        return True, None

    # Normalize the path
    abs_path = os.path.abspath(os.path.expanduser(file_path))

    for allowed in allowed_paths:
        allowed_abs = os.path.abspath(os.path.expanduser(allowed))
        if abs_path.startswith(allowed_abs) or abs_path == allowed_abs:
            return True, None

    return False, f"Path '{file_path}' is not within allowed paths"
