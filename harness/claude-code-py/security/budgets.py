"""
Budget tracking for token usage and tool result sizes.

This module provides:
- Token budget parsing from user prompts (e.g., "+500k tokens")
- Token budget decision logic (continue vs stop)
- Tool result size budget constants and helpers
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# =============================================================================
# Token Budget Parsing
# =============================================================================

# Shorthand (+500k) anchored to start/end to avoid false positives in natural language.
# Verbose (use/spend 2M tokens) matches anywhere.
_SHORTHAND_START_RE = re.compile(r"^\s*\+(\d+(?:\.\d+)?)\s*(k|m|b)\b", re.IGNORECASE)
# Lookbehind is avoided — it defeats YARR JIT in JSC, and the interpreter
# scans O(n) even with the $ anchor. Capture the whitespace instead.
_SHORTHAND_END_RE = re.compile(r"\s\+(\d+(?:\.\d+)?)\s*(k|m|b)\s*[.!?]?\s*$", re.IGNORECASE)
_VERBOSE_RE = re.compile(r"\b(?:use|spend)\s+(\d+(?:\.\d+)?)\s*(k|m|b)\s*tokens?\b", re.IGNORECASE)

_MULTIPLIERS: dict[str, int] = {
    "k": 1_000,
    "m": 1_000_000,
    "b": 1_000_000_000,
}


def _parse_budget_match(value: str, suffix: str) -> int:
    """Parse a matched budget value with its suffix into a token count."""
    return int(float(value) * _MULTIPLIERS[suffix.lower()])


def parse_token_budget(text: str) -> int | None:
    """Parse a token budget from text.

    Supports formats:
    - "+500k" at start (shorthand)
    - "+500k" at end with punctuation (shorthand)
    - "use 2M tokens" (verbose)

    Args:
        text: Input text that may contain a budget specification.

    Returns:
        Token count as an integer, or None if no budget found.
    """
    start_match = _SHORTHAND_START_RE.match(text)
    if start_match:
        return _parse_budget_match(start_match.group(1), start_match.group(2))

    end_match = _SHORTHAND_END_RE.search(text)
    if end_match:
        return _parse_budget_match(end_match.group(1), end_match.group(2))

    verbose_match = _VERBOSE_RE.search(text)
    if verbose_match:
        return _parse_budget_match(verbose_match.group(1), verbose_match.group(2))

    return None


def find_token_budget_positions(
    text: str,
) -> list[dict[str, int]]:
    """Find positions of all token budget mentions in text.

    Args:
        text: Input text to search.

    Returns:
        List of {start, end} position dicts for each match.
    """
    positions: list[dict[str, int]] = []

    start_match = _SHORTHAND_START_RE.match(text)
    if start_match:
        # Calculate offset to skip leading whitespace
        offset = start_match.start() + len(start_match.group()) - len(
            start_match.group().lstrip()
        )
        positions.append({"start": offset, "end": start_match.end()})

    end_match = _SHORTHAND_END_RE.search(text)
    if end_match:
        # Avoid double-counting when input is just "+500k"
        end_start = end_match.start() + 1  # +1: regex includes leading whitespace
        already_covered = any(
            p["start"] <= end_start < p["end"] for p in positions
        )
        if not already_covered:
            positions.append({"start": end_start, "end": end_match.end()})

    for match in _VERBOSE_RE.finditer(text):
        positions.append({"start": match.start(), "end": match.end()})

    return positions


# =============================================================================
# Tool Result Size Budget
# =============================================================================

# Constants for tool result size limits
DEFAULT_MAX_RESULT_SIZE_CHARS = 50_000
"""Default max characters before persisting to disk."""

MAX_TOOL_RESULT_TOKENS = 100_000
"""Max tokens for tool results (~400KB text at 4 bytes/token)."""

BYTES_PER_TOKEN = 4
"""Conservative bytes-per-token estimate."""

MAX_TOOL_RESULT_BYTES = MAX_TOOL_RESULT_TOKENS * BYTES_PER_TOKEN
"""Max bytes for tool results."""

MAX_TOOL_RESULTS_PER_MESSAGE_CHARS = 200_000
"""Max aggregate chars for all tool_result blocks in one message."""

TOOL_SUMMARY_MAX_LENGTH = 50
"""Max chars for tool summary strings in compact views."""


# =============================================================================
# Token Budget Tracker & Decision
# =============================================================================

COMPLETION_THRESHOLD = 0.9
"""Continue until 90% of budget is used."""

DIMINISHING_THRESHOLD = 500
"""Stop if gaining fewer than 500 tokens per continuation."""


@dataclass
class BudgetTracker:
    """Tracks token budget state across continuations."""

    continuation_count: int = 0
    last_delta_tokens: int = 0
    last_global_turn_tokens: int = 0
    started_at: float = 0.0


def create_budget_tracker() -> BudgetTracker:
    """Create a new budget tracker initialized to starting state."""
    return BudgetTracker(
        continuation_count=0,
        last_delta_tokens=0,
        last_global_turn_tokens=0,
        started_at=_current_time_ms(),
    )


def _current_time_ms() -> float:
    """Get current time in milliseconds."""
    import time

    return time.time() * 1000


@dataclass
class ContinueDecision:
    """Decision to continue with nudge message."""

    action: str = "continue"
    nudge_message: str = ""
    continuation_count: int = 0
    pct: int = 0
    turn_tokens: int = 0
    budget: int = 0


@dataclass
class StopDecision:
    """Decision to stop with optional completion event."""

    action: str = "stop"
    completion_event: dict | None = None


TokenBudgetDecision = ContinueDecision | StopDecision


def get_budget_continuation_message(
    pct: int,
    turn_tokens: int,
    budget: int,
) -> str:
    """Generate the nudge message when approaching token budget.

    Args:
        pct: Percentage of budget used.
        turn_tokens: Total tokens in current turn.
        budget: Maximum token budget.

    Returns:
        Nudge message for the model.
    """
    return (
        f"Stopped at {pct}% of token target ({turn_tokens:,} / {budget:,}). "
        "Keep working \u2014 do not summarize."
    )


def check_token_budget(
    tracker: BudgetTracker,
    agent_id: str | None,
    budget: int | None,
    global_turn_tokens: int,
) -> TokenBudgetDecision:
    """Check if the session should continue or stop based on token budget.

    Args:
        tracker: Budget tracker with continuation history.
        agent_id: Non-None for subagents (always stop).
        budget: Token budget limit, or None to disable.
        global_turn_tokens: Current total tokens for the turn.

    Returns:
        ContinueDecision or StopDecision.
    """
    if agent_id is not None or budget is None or budget <= 0:
        return StopDecision(action="stop", completion_event=None)

    turn_tokens = global_turn_tokens
    pct = int((turn_tokens / budget) * 100)
    delta_since_last = global_turn_tokens - tracker.last_global_turn_tokens

    is_diminishing = (
        tracker.continuation_count >= 3
        and delta_since_last < DIMINISHING_THRESHOLD
        and tracker.last_delta_tokens < DIMINISHING_THRESHOLD
    )

    if not is_diminishing and turn_tokens < budget * COMPLETION_THRESHOLD:
        tracker.continuation_count += 1
        tracker.last_delta_tokens = delta_since_last
        tracker.last_global_turn_tokens = global_turn_tokens
        return ContinueDecision(
            action="continue",
            nudge_message=get_budget_continuation_message(pct, turn_tokens, budget),
            continuation_count=tracker.continuation_count,
            pct=pct,
            turn_tokens=turn_tokens,
            budget=budget,
        )

    if is_diminishing or tracker.continuation_count > 0:
        return StopDecision(
            action="stop",
            completion_event={
                "continuation_count": tracker.continuation_count,
                "pct": pct,
                "turn_tokens": turn_tokens,
                "budget": budget,
                "diminishing_returns": is_diminishing,
                "duration_ms": _current_time_ms() - tracker.started_at,
            },
        )

    return StopDecision(action="stop", completion_event=None)
