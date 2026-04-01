"""Coder worker for Mozi orchestrator.

Responsible for code editing operations including
applying diffs and validating changes.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from mozi.orchestrator.state import TodoItem


class CoderWorker:
    """Worker that handles code editing operations.

    Responsible for:
    - Applying diffs to files
    - Validating code changes
    - Managing code modifications
    """

    def __init__(self) -> None:
        """Initialize the coder worker."""
        self._applied_diffs: list[dict[str, Any]] = []

    async def execute(
        self,
        todo: TodoItem,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute the coder task.

        Args:
            todo: The todo item to process.
            context: Optional context information.

        Returns:
            Execution result with applied diff or validation result.
        """
        context = context or {}
        action = context.get("action", "apply_diff")

        if action == "apply_diff":
            return await self.apply_diff(
                file_path=context.get("file_path", ""),
                diff=context.get("diff", ""),
                dry_run=context.get("dry_run", False),
            )
        elif action == "validate_change":
            return await self.validate_change(
                file_path=context.get("file_path", ""),
                change=context.get("change", ""),
            )
        elif action == "create_file":
            return await self.create_file(
                file_path=context.get("file_path", ""),
                content=context.get("content", ""),
            )
        else:
            return {"status": "unknown_action", "action": action}

    async def apply_diff(
        self,
        file_path: str,
        diff: str,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Apply a diff to a file.

        Args:
            file_path: Path to the file to modify.
            diff: The diff to apply.
            dry_run: If True, don't actually modify the file.

        Returns:
            Result of the diff application.
        """
        path = Path(file_path)

        if not path.exists():
            return {
                "status": "error",
                "message": f"File not found: {file_path}",
                "applied": False,
            }

        try:
            with open(path, encoding="utf-8") as f:
                original_content = f.read()
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read file: {e}",
                "applied": False,
            }

        modified_content = self._apply_diff_to_content(original_content, diff)

        if modified_content is None:
            return {
                "status": "error",
                "message": "Failed to parse diff",
                "applied": False,
            }

        if modified_content == original_content:
            return {
                "status": "no_changes",
                "message": "No changes were made",
                "applied": False,
                "file": file_path,
            }

        if dry_run:
            return {
                "status": "dry_run",
                "message": "Dry run - no changes applied",
                "applied": False,
                "file": file_path,
                "original_content": original_content,
                "modified_content": modified_content,
            }

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(modified_content)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to write file: {e}",
                "applied": False,
            }

        lines_changed = len(modified_content.splitlines()) - len(original_content.splitlines())
        diff_record = {
            "id": str(uuid.uuid4()),
            "file_path": file_path,
            "timestamp": str(uuid.uuid4()),
            "lines_changed": lines_changed,
        }
        self._applied_diffs.append(diff_record)

        return {
            "status": "success",
            "message": "Diff applied successfully",
            "applied": True,
            "file": file_path,
            "diff_id": diff_record["id"],
        }

    async def validate_change(
        self,
        file_path: str,
        change: str,
    ) -> dict[str, Any]:
        """Validate a proposed code change.

        Args:
            file_path: Path to the file to validate.
            change: The proposed change (can be diff or new content).

        Returns:
            Validation result with any issues found.
        """
        path = Path(file_path)

        if not path.exists():
            return {
                "status": "error",
                "message": f"File not found: {file_path}",
                "valid": False,
                "issues": [f"File does not exist: {file_path}"],
            }

        issues: list[str] = []
        warnings: list[str] = []

        try:
            with open(path, encoding="utf-8") as f:
                current_content = f.read()
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to read file: {e}",
                "valid": False,
                "issues": [f"Cannot read file: {e}"],
            }

        if path.suffix == ".py":
            issues.extend(self._validate_python_syntax(current_content + "\n" + change))

        if "import *" in change:
            warnings.append("Wildcard imports are discouraged")

        dangerous_patterns = [
            (r"eval\s*\(", "Use of eval() is dangerous"),
            (r"exec\s*\(", "Use of exec() is dangerous"),
            (r"__import__\s*\(", "Dynamic imports are risky"),
            (r"shutil\.rmtree", "Recursive deletion is dangerous"),
            (r"os\.system\s*\(", "Use of os.system() is risky"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, change):
                issues.append(message)

        if change.count("\n") > 500:
            warnings.append("Large change (>500 lines) may be difficult to review")

        return {
            "status": "success",
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "file": file_path,
        }

    async def create_file(
        self,
        file_path: str,
        content: str,
    ) -> dict[str, Any]:
        """Create a new file with given content.

        Args:
            file_path: Path for the new file.
            content: Content to write to the file.

        Returns:
            Result of file creation.
        """
        path = Path(file_path)

        if path.exists():
            return {
                "status": "error",
                "message": f"File already exists: {file_path}",
                "created": False,
            }

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create file: {e}",
                "created": False,
            }

        return {
            "status": "success",
            "message": "File created successfully",
            "created": True,
            "file": file_path,
            "size": len(content),
        }

    def _apply_diff_to_content(
        self,
        original: str,
        diff: str,
    ) -> str | None:
        """Apply a unified diff to content.

        Args:
            original: Original content.
            diff: Unified diff string.

        Returns:
            Modified content or None if diff is invalid.
        """
        original_lines = original.splitlines(keepends=True)
        new_lines: list[str] = []

        try:
            diff_lines = diff.splitlines(keepends=True)
        except Exception:
            return None

        i = 0
        j = 0
        line_idx = 0

        while i < len(diff_lines):
            line = diff_lines[i]

            if line.startswith("@@"):
                match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                if match:
                    line_idx = int(match.group(1)) - 1
                    j = line_idx
                i += 1
                continue

            if line.startswith("-"):
                if j < len(original_lines):
                    j += 1
            elif line.startswith("+"):
                new_lines.append(line[1:])
                j += 1
            elif line.startswith(" "):
                if j < len(original_lines):
                    new_lines.append(original_lines[j])
                    j += 1
            else:
                if j < len(original_lines):
                    new_lines.append(original_lines[j])
                    j += 1

            i += 1

        while j < len(original_lines):
            new_lines.append(original_lines[j])
            j += 1

        return "".join(new_lines)

    def _validate_python_syntax(self, content: str) -> list[str]:
        """Validate Python syntax.

        Args:
            content: Python code to validate.

        Returns:
            List of issues found.
        """
        issues: list[str] = []
        try:
            import ast

            ast.parse(content)
        except SyntaxError as e:
            issues.append(f"Syntax error at line {e.lineno}: {e.msg}")
        except Exception as e:
            issues.append(f"Parse error: {e}")
        return issues

    def get_applied_diffs(self) -> list[dict[str, Any]]:
        """Get list of applied diffs in this session."""
        return self._applied_diffs
