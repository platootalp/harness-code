"""Reviewer for Mozi orchestrator.

Responsible for reviewing code changes, providing feedback,
and making approval decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ReviewStatus(Enum):
    """Status of a review."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class ReviewCommentType(Enum):
    """Type of review comment."""

    ISSUE = "issue"
    SUGGESTION = "suggestion"
    QUESTION = "question"
    PRAISE = "praise"


@dataclass
class ReviewComment:
    """A comment in a code review.

    Attributes:
        id: Unique identifier for the comment.
        file_path: File the comment refers to.
        line: Line number (if applicable).
        type: Type of comment.
        message: The comment text.
        author: Who made the comment.
        created_at: When the comment was created.
        resolved: Whether the comment has been resolved.
    """

    id: str
    file_path: str
    line: int | None = None
    type: ReviewCommentType = ReviewCommentType.ISSUE
    message: str = ""
    author: str = "reviewer"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "line": self.line,
            "type": self.type.value,
            "message": self.message,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved,
        }


@dataclass
class ReviewResult:
    """Result of a code review.

    Attributes:
        status: Overall review status.
        comments: List of review comments.
        summary: Summary of the review.
        approved_by: Who approved (if approved).
        requested_changes: Number of changes requested.
        score: Review score (0-100).
    """

    status: ReviewStatus
    comments: list[ReviewComment] = field(default_factory=list)
    summary: str = ""
    approved_by: str | None = None
    requested_changes: int = 0
    score: float = 0.0
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "comments": [c.to_dict() for c in self.comments],
            "summary": self.summary,
            "approved_by": self.approved_by,
            "requested_changes": self.requested_changes,
            "score": self.score,
            "reviewed_at": self.reviewed_at.isoformat(),
        }

    @property
    def is_approved(self) -> bool:
        """Check if review resulted in approval."""
        return self.status == ReviewStatus.APPROVED


class Reviewer:
    """Reviews code changes and provides feedback.

    Responsible for:
    - Reviewing code diffs
    - Providing constructive feedback
    - Making approval decisions
    - Tracking review comments
    """

    def __init__(self) -> None:
        """Initialize the reviewer."""
        self._comments: list[ReviewComment] = []

    async def review(
        self,
        diff: str,
        context: dict[str, Any] | None = None,
    ) -> ReviewResult:
        """Review code changes.

        Args:
            diff: The diff to review.
            context: Optional context (session info, author, etc.).

        Returns:
            Review result with comments and decision.
        """
        context = context or {}
        author = context.get("author", "anonymous")
        self._comments = []

        await self._analyze_diff(diff, author)

        return self._generate_review_result(context)

    async def _analyze_diff(
        self,
        diff: str,
        author: str,
    ) -> None:
        """Analyze a diff and add review comments.

        Args:
            diff: The diff to analyze.
            author: Author of the changes.
        """
        import re

        lines = diff.split("\n")
        file_changes: dict[str, dict[str, Any]] = {}

        current_file = None
        for line in lines:
            if line.startswith("--- ") or line.startswith("+++ "):
                match = re.match(r"^[+-]{3}\s+[ab]?/?(\S+)", line)
                if match:
                    current_file = match.group(1)
                    if current_file not in file_changes:
                        file_changes[current_file] = {"additions": 0, "deletions": 0}

            if current_file and line.startswith("+") and not line.startswith("+++"):
                file_changes[current_file]["additions"] += 1
            elif current_file and line.startswith("-") and not line.startswith("---"):
                file_changes[current_file]["deletions"] += 1

        for file_path, changes in file_changes.items():
            if changes["additions"] > 200:
                self._add_comment(
                    file_path=file_path,
                    type=ReviewCommentType.SUGGESTION,
                    message=f"Large addition ({changes['additions']} lines) - "
                    "consider breaking into smaller changes",
                )

            if changes["deletions"] > 200:
                self._add_comment(
                    file_path=file_path,
                    type=ReviewCommentType.SUGGESTION,
                    message=f"Large deletion ({changes['deletions']} lines) - "
                    "ensure no needed code is removed",
                )

        dangerous_patterns = [
            (r"eval\s*\(", "Use of eval() detected - security risk", ReviewCommentType.ISSUE),
            (r"exec\s*\(", "Use of exec() detected - security risk", ReviewCommentType.ISSUE),
            (
                r"import\s+\*",
                "Wildcard import detected - use explicit imports",
                ReviewCommentType.SUGGESTION,
            ),
            (
                r"print\s*\(",
                "print statement found - use logging instead",
                ReviewCommentType.SUGGESTION,
            ),
            (
                r"#\s*TODO",
                "TODO comment found - should be addressed or tracked",
                ReviewCommentType.QUESTION,
            ),
            (r"#\s*FIXME", "FIXME comment found - should be addressed", ReviewCommentType.ISSUE),
            (
                r"except\s*:\s*$",
                "Bare except clause - catch specific exceptions",
                ReviewCommentType.ISSUE,
            ),
            (
                r"pass\s*$",
                "Empty except/pass block - needs implementation",
                ReviewCommentType.ISSUE,
            ),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, message, comment_type in dangerous_patterns:
                if re.search(pattern, line):
                    self._add_comment(
                        file_path="",
                        line=line_num,
                        type=comment_type,
                        message=message,
                    )

    async def request_changes(
        self,
        diff: str,
        reason: str,
        context: dict[str, Any] | None = None,
    ) -> ReviewResult:
        """Request changes to a diff.

        Args:
            diff: The diff to review.
            reason: Reason for requesting changes.
            context: Optional context.

        Returns:
            Review result requesting changes.
        """
        context = context or {}

        self._add_comment(
            file_path="",
            type=ReviewCommentType.ISSUE,
            message=f"Changes requested: {reason}",
        )

        return ReviewResult(
            status=ReviewStatus.CHANGES_REQUESTED,
            comments=self._comments,
            summary=f"Changes requested: {reason}",
            requested_changes=len(self._comments),
            score=self._calculate_score(),
        )

    async def approve(
        self,
        diff: str,
        context: dict[str, Any] | None = None,
    ) -> ReviewResult:
        """Approve a diff.

        Args:
            diff: The diff to approve.
            context: Optional context.

        Returns:
            Review result with approval.
        """
        context = context or {}
        approver = context.get("approver", "reviewer")

        return ReviewResult(
            status=ReviewStatus.APPROVED,
            comments=self._comments,
            summary="Code approved",
            approved_by=approver,
            requested_changes=0,
            score=100.0,
        )

    def _add_comment(
        self,
        file_path: str,
        type: ReviewCommentType,
        message: str,
        line: int | None = None,
    ) -> None:
        """Add a review comment.

        Args:
            file_path: File the comment refers to.
            type: Type of comment.
            message: Comment text.
            line: Optional line number.
        """
        import uuid

        comment = ReviewComment(
            id=str(uuid.uuid4()),
            file_path=file_path,
            line=line,
            type=type,
            message=message,
        )
        self._comments.append(comment)

    def _generate_review_result(self, context: dict[str, Any]) -> ReviewResult:
        """Generate final review result.

        Args:
            context: Review context.

        Returns:
            Complete review result.
        """
        status: ReviewStatus
        if len(self._comments) == 0:
            status = ReviewStatus.APPROVED
        elif any(c.type == ReviewCommentType.ISSUE for c in self._comments):
            status = ReviewStatus.CHANGES_REQUESTED
        else:
            status = ReviewStatus.APPROVED

        score = self._calculate_score()

        return ReviewResult(
            status=status,
            comments=self._comments,
            summary=self._generate_summary(),
            approved_by="reviewer" if status == ReviewStatus.APPROVED else None,
            requested_changes=len([c for c in self._comments if c.type == ReviewCommentType.ISSUE]),
            score=score,
        )

    def _calculate_score(self) -> float:
        """Calculate review score based on comments."""
        if not self._comments:
            return 100.0

        issue_count = len([c for c in self._comments if c.type == ReviewCommentType.ISSUE])
        suggestion_count = len(
            [c for c in self._comments if c.type == ReviewCommentType.SUGGESTION]
        )
        question_count = len([c for c in self._comments if c.type == ReviewCommentType.QUESTION])

        deduction = (issue_count * 15) + (suggestion_count * 5) + (question_count * 3)
        return max(0.0, 100.0 - deduction)

    def _generate_summary(self) -> str:
        """Generate review summary text."""
        issue_count = len([c for c in self._comments if c.type == ReviewCommentType.ISSUE])
        suggestion_count = len(
            [c for c in self._comments if c.type == ReviewCommentType.SUGGESTION]
        )

        parts = []
        if issue_count > 0:
            parts.append(f"{issue_count} issue(s)")
        if suggestion_count > 0:
            parts.append(f"{suggestion_count} suggestion(s)")

        if not parts:
            return "No issues found - code looks good!"

        return " and ".join(parts)

    def get_comments(self) -> list[ReviewComment]:
        """Get all review comments."""
        return self._comments
