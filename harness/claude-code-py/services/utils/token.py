"""Token counting and estimation utilities.

TypeScript equivalent: src/utils/tokens.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TokenUsage:
    """Token usage from API response."""

    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


def get_token_count_from_usage(usage: TokenUsage) -> int:
    """Calculate total context window tokens from usage data.

    Includes input_tokens + cache tokens + output_tokens.

    This represents the full context size at the time of that API call.

    Args:
        usage: Token usage from API response.

    Returns:
        Total context window tokens.
    """
    return (
        usage.input_tokens
        + usage.cache_creation_input_tokens
        + usage.cache_read_input_tokens
        + usage.output_tokens
    )


def get_current_usage(
    messages: list[dict[str, Any]],
) -> TokenUsage | None:
    """Extract usage from the last assistant message.

    Searches backward through messages to find the most recent
    assistant message with usage data.

    Args:
        messages: List of conversation messages.

    Returns:
        TokenUsage from the last assistant message, or None if not found.
    """
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg.get("type") == "assistant":
            msg_content = msg.get("message", {})
            if isinstance(msg_content, dict):
                usage = msg_content.get("usage")
                if usage:
                    return TokenUsage(
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        cache_creation_input_tokens=usage.get(
                            "cache_creation_input_tokens", 0
                        ),
                        cache_read_input_tokens=usage.get("cache_read_input_tokens", 0),
                    )
    return None


def token_count_with_estimation(messages: list[dict[str, Any]]) -> int:
    """Calculate context window size with rough estimation for new messages.

    This is the canonical function for measuring context size when checking
    thresholds (autocompact, session memory init, etc.). Uses the last API
    response's token count plus estimates for any messages added since.

    Args:
        messages: List of conversation messages.

    Returns:
        Estimated total context window tokens.
    """
    usage = get_current_usage(messages)
    if usage:
        usage_count = get_token_count_from_usage(usage)

        # Find the index of the message with usage
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if msg.get("type") == "assistant":
                msg_content = msg.get("message", {})
                if isinstance(msg_content, dict) and msg_content.get("usage"):
                    # Estimate tokens for messages after this one
                    remaining = rough_token_count_estimation_for_messages(messages[i + 1:])
                    return usage_count + remaining

    # No usage found - estimate all messages
    return rough_token_count_estimation_for_messages(messages)


def rough_token_count_estimation(text: str) -> int:
    """Rough token estimation: approximately 4 characters per token.

    This is a simple heuristic. Actual token counts depend on the specific
    tokenizer and content (code vs prose vs special characters).

    Args:
        text: The text to estimate tokens for.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def rough_token_count_estimation_for_messages(
    messages: list[dict[str, Any]],
) -> int:
    """Rough token count for a list of messages.

    Args:
        messages: List of messages to count.

    Returns:
        Estimated total tokens.
    """
    total = 0
    for msg in messages:
        total += rough_token_count_estimation(_message_to_text(msg))
    return total


def _message_to_text(msg: dict[str, Any]) -> str:
    """Extract text content from a message for token counting.

    Args:
        msg: Message dictionary.

    Returns:
        Text content of the message.
    """
    msg_type = msg.get("type", "")
    if msg_type == "user":
        content = msg.get("message", {})
        if isinstance(content, dict):
            content_list = content.get("content", [])
            if isinstance(content_list, list):
                text_parts = []
                for block in content_list:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            # Include tool input in count
                            input_json = block.get("input", {})
                            import json
                            text_parts.append(json.dumps(input_json))
                return " ".join(text_parts)
            elif isinstance(content_list, str):
                return content_list
    elif msg_type == "assistant":
        content = msg.get("message", {})
        if isinstance(content, dict):
            content_list = content.get("content", [])
            if isinstance(content_list, list):
                text_parts = []
                for block in content_list:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "thinking":
                            text_parts.append(block.get("thinking", ""))
                        elif block.get("type") == "redacted_thinking":
                            text_parts.append(block.get("data", ""))
                        elif block.get("type") == "tool_use":
                            input_json = block.get("input", {})
                            import json
                            text_parts.append(json.dumps(input_json))
                return " ".join(text_parts)
    return str(msg)
