"""
Context management for Claude Code.

Provides context window management, message compression, system/user context
injection, and context usage tracking.

Context flow:
1. System context (git status, cache breaker) - prepended to each conversation
2. User context (CLAUDE.md files, current date) - prepended to each conversation
3. Session messages - conversation history with tools and responses
4. Compact boundaries - markers for compressed context regions
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# =============================================================================
# Context Window Constants
# =============================================================================

MODEL_CONTEXT_WINDOW_DEFAULT = 200_000
"""Default model context window size in tokens (200k for all models currently)."""

COMPACT_MAX_OUTPUT_TOKENS = 20_000
"""Maximum output tokens for compact/summarize operations."""

CAPPED_DEFAULT_MAX_TOKENS = 8_000
"""Capped default max output tokens for slot-reservation optimization."""

ESCALATED_MAX_TOKENS = 64_000
"""Escalated max output tokens for retry on capped requests."""

MAX_STATUS_CHARS = 2000
"""Maximum characters for truncated git status output."""

# =============================================================================
# 1M Context Support
# =============================================================================

# Environment variable to disable 1M context (for C4E admins, HIPAA compliance)
_DISABLED_1M_ENV = "CLAUDE_CODE_DISABLE_1M_CONTEXT"


def is_1m_context_disabled() -> bool:
    """Check if 1M context is disabled via environment variable.

    Used by C4E admins to disable 1M context for HIPAA compliance.
    """
    import os

    return os.environ.get(_DISABLED_1M_ENV, "").lower() in ("1", "true", "yes")


def has_1m_context(model: str) -> bool:
    """Check if model name explicitly requests 1M context via [1m] suffix."""
    if is_1m_context_disabled():
        return False
    return "[1m]" in model.lower()


# =============================================================================
# Model Context Window
# =============================================================================

# Model context windows by family
_MODEL_CONTEXT_WINDOWS: dict[str, int] = {
    "claude-sonnet-4": 200_000,
    "claude-opus-4-6": 1_000_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
}


def get_context_window_for_model(model: str) -> int:
    """Get the context window size for a model.

    Args:
        model: Model name (may include [1m] suffix).

    Returns:
        Context window size in tokens.
    """
    # [1m] suffix takes precedence
    if has_1m_context(model):
        return 1_000_000

    model_lower = model.lower()

    # Check for explicit 1M capable models
    if "sonnet-4-6" in model_lower or "opus-4-6" in model_lower:
        if not is_1m_context_disabled():
            return 1_000_000

    # Default context window
    return MODEL_CONTEXT_WINDOW_DEFAULT


# =============================================================================
# Model Max Output Tokens
# =============================================================================

@dataclass
class ModelMaxOutputTokens:
    """Output token limits for a model."""

    default: int
    upper_limit: int


_MODEL_MAX_OUTPUT_TOKENS: dict[str, ModelMaxOutputTokens] = {
    # Opus 4.6: 128k max output
    "opus-4-6": ModelMaxOutputTokens(default=64_000, upper_limit=128_000),
    # Sonnet 4.6: 128k max output
    "sonnet-4-6": ModelMaxOutputTokens(default=32_000, upper_limit=128_000),
    # Claude 3.5/4 Sonnet family
    "sonnet-4": ModelMaxOutputTokens(default=32_000, upper_limit=64_000),
    "haiku-4": ModelMaxOutputTokens(default=32_000, upper_limit=64_000),
    # Opus 4.x
    "opus-4-1": ModelMaxOutputTokens(default=32_000, upper_limit=32_000),
    "opus-4": ModelMaxOutputTokens(default=32_000, upper_limit=32_000),
    # Claude 3 family
    "claude-3-opus": ModelMaxOutputTokens(default=4_096, upper_limit=4_096),
    "claude-3-sonnet": ModelMaxOutputTokens(default=8_192, upper_limit=8_192),
    "claude-3-haiku": ModelMaxOutputTokens(default=4_096, upper_limit=4_096),
    # Claude 3.5 family
    "3-5-sonnet": ModelMaxOutputTokens(default=8_192, upper_limit=8_192),
    "3-5-haiku": ModelMaxOutputTokens(default=8_192, upper_limit=8_192),
    # Claude 3.7
    "3-7-sonnet": ModelMaxOutputTokens(default=32_000, upper_limit=64_000),
}


def get_model_max_output_tokens(model: str) -> ModelMaxOutputTokens:
    """Get the default and upper limit for max output tokens.

    Args:
        model: Model name.

    Returns:
        ModelMaxOutputTokens with default and upper_limit.
    """
    model_lower = model.lower()

    for key, limits in _MODEL_MAX_OUTPUT_TOKENS.items():
        if key in model_lower:
            return limits

    # Default for unknown models
    return ModelMaxOutputTokens(
        default=32_000,
        upper_limit=64_000,
    )


def get_max_thinking_tokens_for_model(model: str) -> int:
    """Get the max thinking budget tokens for a model.

    The max thinking tokens should be strictly less than the max output tokens.
    """
    return get_model_max_output_tokens(model).upper_limit - 1


# =============================================================================
# Context Percentage Calculation
# =============================================================================


@dataclass
class ContextPercentages:
    """Context window usage percentages."""

    used: int | None = None
    remaining: int | None = None


def calculate_context_percentages(
    current_usage: dict[str, int] | None,
    context_window_size: int,
) -> ContextPercentages:
    """Calculate context window usage percentage from token usage data.

    Args:
        current_usage: Dict with input_tokens, cache_creation_input_tokens,
            cache_read_input_tokens.
        context_window_size: Total context window size.

    Returns:
        ContextPercentages with used and remaining percentages.
    """
    if not current_usage:
        return ContextPercentages(used=None, remaining=None)

    total_input_tokens = (
        current_usage.get("input_tokens", 0)
        + current_usage.get("cache_creation_input_tokens", 0)
        + current_usage.get("cache_read_input_tokens", 0)
    )

    used_percentage = int(
        round((total_input_tokens / context_window_size) * 100)
    )
    clamped_used = max(0, min(100, used_percentage))

    return ContextPercentages(
        used=clamped_used,
        remaining=100 - clamped_used,
    )


# =============================================================================
# Git Status Context
# =============================================================================

# Maximum status characters before truncation
MAX_GIT_STATUS_CHARS = MAX_STATUS_CHARS


@lru_cache(maxsize=1)
def get_git_status() -> str | None:
    """Get git status formatted as context for the system prompt.

    Returns None if not in a git repository.

    Cached for the duration of the process.
    """
    try:
        cwd = Path.cwd()

        # Check if in a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout.strip() != "true":
            return None

        # Get git info in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def run_git_cmd(cmd: list[str]) -> str:
            try:
                result = subprocess.run(
                    ["git"] + cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.stdout.strip()
            except (subprocess.TimeoutExpired, OSError):
                return ""

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(run_git_cmd, ["branch", "--show-current"]): "branch",
                executor.submit(
                    run_git_cmd,
                    ["rev-parse", "--verify", "--quiet", "HEAD"],
                ): "main_check",
                executor.submit(
                    run_git_cmd,
                    [
                        "--no-pager",
                        "log",
                        "--oneline",
                        "-n",
                        "5",
                    ],
                ): "log",
                executor.submit(
                    run_git_cmd,
                    [
                        "--no-optional-locks",
                        "status",
                        "--short",
                    ],
                ): "status",
                executor.submit(
                    run_git_cmd,
                    ["config", "user.name"],
                ): "user_name",
            }

            results: dict[str, str] = {}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception:
                    results[key] = ""

        branch = results.get("branch", "")
        main_branch = "main"  # Could be enhanced to detect default branch
        log = results.get("log", "(no commits)")
        status = results.get("status", "")
        user_name = results.get("user_name", "")

        # Truncate if needed
        truncated_status = status
        if len(status) > MAX_GIT_STATUS_CHARS:
            truncated_status = (
                status[:MAX_GIT_STATUS_CHARS]
                + f"\n... (truncated because it exceeds {MAX_GIT_STATUS_CHARS} chars. "
                + 'If you need more information, run "git status" using BashTool)'
            )

        parts = [
            "This is the git status at the start of the conversation. "
            "Note that this status is a snapshot in time, "
            "and will not update during the conversation.",
            f"Current branch: {branch}",
            f"Main branch (you will usually use this for PRs): {main_branch}",
        ]

        if user_name:
            parts.append(f"Git user: {user_name}")

        parts.append(f"Status:\n{truncated_status or '(clean)'}")
        parts.append(f"Recent commits:\n{log}")

        return "\n\n".join(parts)

    except Exception:
        # Not in a git repo or git not available
        return None


# =============================================================================
# Date Context
# =============================================================================

def get_current_date_string() -> str:
    """Get the current date formatted for context injection."""
    return f"Today's date is {datetime.now(UTC).strftime('%Y-%m-%d')}."


# =============================================================================
# Context Manager
# =============================================================================


@dataclass
class ContextStats:
    """Statistics about context usage."""

    total_tokens: int = 0
    input_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    context_window: int = MODEL_CONTEXT_WINDOW_DEFAULT
    used_percentage: int = 0

    @property
    def remaining_percentage(self) -> int:
        """Percentage of context window remaining."""
        return 100 - self.used_percentage

    @property
    def is_near_limit(self) -> bool:
        """Check if context is near its limit (>80% used)."""
        return self.used_percentage > 80

    @property
    def is_at_limit(self) -> bool:
        """Check if context is at its limit (>95% used)."""
        return self.used_percentage > 95


@dataclass
class ContextConfig:
    """Configuration for context management."""

    model: str = "claude-sonnet-4-7"
    context_window: int | None = None
    max_output_tokens: int | None = None
    include_git_status: bool = True
    include_date: bool = True
    include_claude_md: bool = True


@dataclass
class ContextManager:
    """Manages conversation context including system prompt, user context, and compression.

    Responsibilities:
    - Build system context (git status, date, cache breaker)
    - Build user context (CLAUDE.md files)
    - Track context usage and trigger compression
    - Manage compact boundaries
    """

    config: ContextConfig = field(default_factory=ContextConfig)
    _stats: ContextStats = field(default_factory=ContextStats)
    _system_context: dict[str, str] = field(default_factory=dict)
    _user_context: dict[str, str] = field(default_factory=dict)
    _compact_boundaries: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize context manager with configuration."""
        if self.config.context_window is None:
            self.config.context_window = get_context_window_for_model(
                self.config.model
            )
        self._stats.context_window = self.config.context_window

    def build_system_context(self) -> dict[str, str]:
        """Build system context for the prompt.

        Returns:
            Dict with context sections (gitStatus, cacheBreaker, etc.).
        """
        context: dict[str, str] = {}

        # Git status
        if self.config.include_git_status:
            git_status = get_git_status()
            if git_status:
                context["gitStatus"] = git_status

        # Date
        if self.config.include_date:
            context["currentDate"] = get_current_date_string()

        self._system_context = context
        return context

    def build_user_context(self, claude_md_content: str | None = None) -> dict[str, str]:
        """Build user context for the prompt.

        Args:
            claude_md_content: Optional CLAUDE.md content. If None, will be
                looked up from filesystem.

        Returns:
            Dict with user context sections (claudeMd, currentDate).
        """
        context: dict[str, str] = {}

        # CLAUDE.md content
        if self.config.include_claude_md and claude_md_content:
            context["claudeMd"] = claude_md_content

        # Date
        if self.config.include_date:
            context["currentDate"] = get_current_date_string()

        self._user_context = context
        return context

    def update_stats(
        self,
        input_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> None:
        """Update context statistics from API usage.

        Args:
            input_tokens: Tokens in the input message.
            cache_creation_tokens: Tokens used for cache creation.
            cache_read_tokens: Tokens read from cache.
        """
        self._stats.input_tokens = input_tokens
        self._stats.cache_creation_tokens = cache_creation_tokens
        self._stats.cache_read_tokens = cache_read_tokens
        self._stats.total_tokens = (
            input_tokens + cache_creation_tokens + cache_read_tokens
        )

        if self._stats.context_window > 0:
            self._stats.used_percentage = int(
                round((self._stats.total_tokens / self._stats.context_window) * 100)
            )

    def should_compact(self, threshold_percentage: int = 80) -> bool:
        """Check if context should be compacted.

        Args:
            threshold_percentage: Usage percentage that triggers compaction.

        Returns:
            True if compaction should be considered.
        """
        return self._stats.used_percentage >= threshold_percentage

    def add_compact_boundary(self, message_index: int) -> None:
        """Add a compact boundary at a message index.

        Args:
            message_index: Index of the boundary message.
        """
        if message_index not in self._compact_boundaries:
            self._compact_boundaries.append(message_index)
            self._compact_boundaries.sort()

    def get_compact_boundaries(self) -> list[int]:
        """Get all compact boundary indices."""
        return list(self._compact_boundaries)

    def clear_compact_boundaries(self) -> None:
        """Clear all compact boundaries."""
        self._compact_boundaries.clear()

    @property
    def stats(self) -> ContextStats:
        """Get current context statistics."""
        return self._stats

    @property
    def system_context(self) -> dict[str, str]:
        """Get built system context."""
        return self._system_context

    @property
    def user_context(self) -> dict[str, str]:
        """Get built user context."""
        return self._user_context

    @property
    def context_window(self) -> int:
        """Get configured context window size."""
        return self.config.context_window or MODEL_CONTEXT_WINDOW_DEFAULT


# =============================================================================
# Cache Breaker (for debugging/testing)
# =============================================================================

_cache_breaker: str | None = None


def get_cache_breaker() -> str | None:
    """Get the current cache breaker value."""
    return _cache_breaker


def set_cache_breaker(value: str | None) -> None:
    """Set the cache breaker value.

    Setting this value will cause context caches to be invalidated.
    """
    global _cache_breaker
    _cache_breaker = value


def get_cache_breaker_context() -> dict[str, str]:
    """Get cache breaker as a context dict if set."""
    if _cache_breaker:
        return {"cacheBreaker": f"[CACHE_BREAKER: {_cache_breaker}]"}
    return {}


# =============================================================================
# Helper Functions
# =============================================================================

def format_context_for_prompt(
    system_context: dict[str, str],
    user_context: dict[str, str],
) -> str:
    """Format context sections into a prompt string.

    Args:
        system_context: System context dict.
        user_context: User context dict.

    Returns:
        Formatted context string.
    """
    parts: list[str] = []

    for section in system_context.values():
        if section:
            parts.append(section)

    for section in user_context.values():
        if section:
            parts.append(section)

    return "\n\n".join(parts)


def estimate_tokens_for_text(text: str) -> int:
    """Estimate token count for text.

    Uses a rough approximation: ~4 characters per token.

    Args:
        text: Text to estimate.

    Returns:
        Estimated token count.
    """
    return len(text) // 4


def tokens_to_chars(tokens: int, chars_per_token: int = 4) -> int:
    """Convert token count to character count.

    Args:
        tokens: Number of tokens.
        chars_per_token: Characters per token (default 4).

    Returns:
        Approximate character count.
    """
    return tokens * chars_per_token
