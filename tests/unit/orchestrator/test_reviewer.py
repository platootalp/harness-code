"""Tests for the reviewer."""

from __future__ import annotations

import pytest

from mozi.orchestrator.reviewer import (
    ReviewComment,
    ReviewCommentType,
    Reviewer,
    ReviewResult,
    ReviewStatus,
)


class TestReviewStatus:
    """Tests for ReviewStatus enum."""

    def test_status_values(self) -> None:
        """Test ReviewStatus values."""
        assert ReviewStatus.PENDING.value == "pending"
        assert ReviewStatus.IN_PROGRESS.value == "in_progress"
        assert ReviewStatus.APPROVED.value == "approved"
        assert ReviewStatus.CHANGES_REQUESTED.value == "changes_requested"
        assert ReviewStatus.REJECTED.value == "rejected"


class TestReviewCommentType:
    """Tests for ReviewCommentType enum."""

    def test_type_values(self) -> None:
        """Test ReviewCommentType values."""
        assert ReviewCommentType.ISSUE.value == "issue"
        assert ReviewCommentType.SUGGESTION.value == "suggestion"
        assert ReviewCommentType.QUESTION.value == "question"
        assert ReviewCommentType.PRAISE.value == "praise"


class TestReviewComment:
    """Tests for ReviewComment dataclass."""

    def test_create_comment(self) -> None:
        """Test creating a ReviewComment."""
        comment = ReviewComment(
            id="1",
            file_path="main.py",
            line=10,
            type=ReviewCommentType.ISSUE,
            message="Fix this",
        )
        assert comment.id == "1"
        assert comment.file_path == "main.py"
        assert comment.line == 10
        assert comment.type == ReviewCommentType.ISSUE

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        comment = ReviewComment(
            id="1",
            file_path="main.py",
            type=ReviewCommentType.SUGGESTION,
            message="Consider refactoring",
        )
        result = comment.to_dict()
        assert result["id"] == "1"
        assert result["file_path"] == "main.py"
        assert result["type"] == "suggestion"


class TestReviewResult:
    """Tests for ReviewResult dataclass."""

    def test_create_result(self) -> None:
        """Test creating a ReviewResult."""
        result = ReviewResult(
            status=ReviewStatus.APPROVED,
            comments=[],
            summary="LGTM",
            approved_by="reviewer",
            score=100.0,
        )
        assert result.status == ReviewStatus.APPROVED
        assert result.is_approved is True

    def test_is_approved(self) -> None:
        """Test is_approved property."""
        approved = ReviewResult(status=ReviewStatus.APPROVED, score=100.0)
        changes = ReviewResult(status=ReviewStatus.CHANGES_REQUESTED, score=80.0)
        rejected = ReviewResult(status=ReviewStatus.REJECTED, score=30.0)

        assert approved.is_approved is True
        assert changes.is_approved is False
        assert rejected.is_approved is False


class TestReviewer:
    """Tests for Reviewer."""

    @pytest.mark.asyncio
    async def test_review_empty_diff(self) -> None:
        """Test reviewing an empty diff."""
        reviewer = Reviewer()
        result = await reviewer.review("")
        assert result.status == ReviewStatus.APPROVED
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_review_large_addition(self) -> None:
        """Test reviewing large additions."""
        reviewer = Reviewer()
        diff = "+++ a/test.py\n" + "\n".join(f"+line {i}" for i in range(250))
        result = await reviewer.review(diff)
        assert len(result.comments) > 0
        assert any("Large addition" in c.message for c in result.comments)

    @pytest.mark.asyncio
    async def test_review_dangerous_patterns(self) -> None:
        """Test reviewing dangerous patterns."""
        reviewer = Reviewer()
        diff = "+++ a/test.py\n+eval('print(1)')\n"
        result = await reviewer.review(diff)
        assert any(c.type == ReviewCommentType.ISSUE for c in result.comments)

    @pytest.mark.asyncio
    async def test_review_wildcard_import(self) -> None:
        """Test reviewing wildcard imports."""
        reviewer = Reviewer()
        diff = "+++ a/test.py\n+from os import *\n"
        result = await reviewer.review(diff)
        assert any("Wildcard" in c.message for c in result.comments)

    @pytest.mark.asyncio
    async def test_review_todo_comment(self) -> None:
        """Test reviewing TODO comments."""
        reviewer = Reviewer()
        diff = "+++ a/test.py\n+# TODO: fix this\n"
        result = await reviewer.review(diff)
        assert any("TODO" in c.message for c in result.comments)

    @pytest.mark.asyncio
    async def test_review_bare_except(self) -> None:
        """Test reviewing bare except clauses."""
        reviewer = Reviewer()
        diff = "+++ a/test.py\n+except:\n+    pass\n"
        result = await reviewer.review(diff)
        assert any("Bare except" in c.message for c in result.comments)

    @pytest.mark.asyncio
    async def test_request_changes(self) -> None:
        """Test requesting changes."""
        reviewer = Reviewer()
        result = await reviewer.request_changes(
            diff="+++ a/test.py\n+print('test')\n",
            reason="Need proper error handling",
        )
        assert result.status == ReviewStatus.CHANGES_REQUESTED
        assert len(result.comments) > 0

    @pytest.mark.asyncio
    async def test_approve(self) -> None:
        """Test approving a diff."""
        reviewer = Reviewer()
        result = await reviewer.approve(diff="+++ a/test.py\n+print('test')\n")
        assert result.status == ReviewStatus.APPROVED
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_get_comments(self) -> None:
        """Test getting review comments."""
        reviewer = Reviewer()
        await reviewer.review("+++ a/test.py\n+eval('x')\n")
        comments = reviewer.get_comments()
        assert len(comments) > 0
