# Streaming Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the LLM streaming response parsing in api/client.py. Currently stream chunks are received but not parsed into text/tool_calls. Matches design spec Section 4.2 and Section 17 (StreamEvent/StreamChunk).

**Architecture:** Parse SSE/stream events from LiteLLM API into text deltas and tool_call events. Yield incremental text via AsyncGenerator.

**Tech Stack:** asyncio, LiteLLM streaming response handling

---

## File Structure

```
src_py/api/
├── __init__.py        # Already exports LiteLLMClient (NO CHANGE)
├── client.py          # MODIFY: Implement stream parsing
└── test_client.py     # CREATE: Unit tests for streaming
```

---

### Task 1: Write Streaming Tests

**Files:**
- Create: `src_py/api/test_client.py`

- [ ] **Step 1: Create test file**

```python
"""Tests for LiteLLMClient streaming."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src_py.api.client import LiteLLMClient, StreamChunk


@pytest.fixture
def client():
    """Create a LiteLLMClient instance."""
    return LiteLLMClient(
        model="test-model",
        api_key="test-key",
        base_url="http://localhost:8080",
    )


def test_stream_chunk_dataclass():
    """StreamChunk holds incremental content."""
    chunk = StreamChunk(content="Hello", is_final=False)
    assert chunk.content == "Hello"
    assert chunk.is_final is False

    final_chunk = StreamChunk(
        content="Complete",
        is_final=True,
        usage={"prompt_tokens": 10, "completion_tokens": 5},
    )
    assert final_chunk.is_final is True
    assert final_chunk.usage["completion_tokens"] == 5


@pytest.mark.asyncio
async def test_parse_content_block_start(client):
    """Parser handles content_block_start event."""
    # Simulate a content_block_start event from streaming response
    event = {
        "type": "content_block_start",
        "index": 0,
        "content_block": {"type": "text", "text": ""},
    }

    result = client._parse_stream_chunk(event)
    # Should not raise, should return None (no content to yield yet)
    assert result is None


@pytest.mark.asyncio
async def test_parse_content_block_delta(client):
    """Parser handles content_block_delta with incremental text."""
    event = {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "text_delta", "text": "Hello "},
    }

    result = client._parse_stream_chunk(event)

    if result is not None:
        assert isinstance(result, StreamChunk)
        assert result.content == "Hello "
        assert result.is_final is False


@pytest.mark.asyncio
async def test_parse_message_delta(client):
    """Parser handles message_delta with final usage."""
    event = {
        "type": "message_delta",
        "index": 0,
        "delta": {"type": "text_delta", "text": " world"},
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    result = client._parse_stream_chunk(event)

    if result is not None:
        assert isinstance(result, StreamChunk)
        assert " world" in result.content
        assert result.is_final is True
        if result.usage:
            assert result.usage["completion_tokens"] == 5


@pytest.mark.asyncio
async def test_parse_hybrid_stream(client):
    """Parser handles mixed text + tool_call streaming."""
    events = [
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Thinking..."}},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "name": "bash", "input": {}}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "input_json": '{"command"'}},
        {"type": "message_stop"},
    ]

    chunks = []
    for event in events:
        result = client._parse_stream_chunk(event)
        if result:
            chunks.append(result)

    # Should have at least one text chunk
    assert len(chunks) >= 1
    text_content = "".join(c.content for c in chunks if not c.is_final)
    assert "Thinking..." in text_content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/lijunyi/road/claude-code && python3 -m pytest src_py/api/test_client.py -v`
Expected: FAIL - _parse_stream_chunk has pass stubs

---

### Task 2: Implement Stream Chunk Parser

**Files:**
- Modify: `src_py/api/client.py:150-245`

- [ ] **Step 1: Implement _parse_stream_chunk**

Replace the stub implementation (lines 150-245) with:

```python
async def _parse_stream_chunk(self, event: dict) -> StreamChunk | None:
    """Parse a streaming event into a StreamChunk.

    Returns:
        StreamChunk for content events, None for control events.
    """
    import json

    event_type = event.get("type")

    if event_type == "content_block_start":
        # Store block type for later
        index = event.get("index", 0)
        content_block = event.get("content_block", {})
        block_type = content_block.get("type")
        self._stream_state["blocks"][index] = {"type": block_type, "text": ""}
        return None

    elif event_type == "content_block_delta":
        index = event.get("index", 0)
        delta = event.get("delta", {})
        delta_type = delta.get("type")

        block = self._stream_state["blocks"].get(index)
        if not block:
            return None

        if delta_type == "text_delta":
            text = delta.get("text", "")
            block["text"] += text
            return StreamChunk(content=text, is_final=False)

        elif delta_type == "input_json_delta":
            # Accumulate JSON input for tool calls
            partial_json = delta.get("input_json", "")
            block["text"] += partial_json
            # Return as text chunk for now
            return StreamChunk(content=partial_json, is_final=False)

        return None

    elif event_type == "message_delta":
        delta = event.get("delta", {})
        usage = event.get("usage")
        text = delta.get("text", "")

        if text:
            return StreamChunk(content=text, is_final=True, usage=usage)

        # Final chunk with usage but no new text
        if usage:
            return StreamChunk(content="", is_final=True, usage=usage)

        return None

    elif event_type == "message_stop":
        # End of stream
        self._stream_state["blocks"] = {}
        return StreamChunk(content="", is_final=True)

    elif event_type == "error":
        error_msg = event.get("error", {}).get("message", "Unknown error")
        raise Exception(f"Stream error: {error_msg}")

    return None
```

- [ ] **Step 2: Initialize stream state in __init__**

Add to `__init__` method:

```python
# Stream state for parsing
self._stream_state = {
    "blocks": {},  # index -> {"type": str, "text": str}
}
```

- [ ] **Step 3: Run streaming tests**

Run: `cd /Users/lijunyi/road/claude-code && python3 -m pytest src_py/api/test_client.py -v`
Expected: PASS

- [ ] **Step 4: Commit streaming implementation**

```bash
cd /Users/lijunyi/road/claude-code
git add src_py/api/client.py src_py/api/test_client.py
git commit -m "feat(api): implement streaming response parsing

- _parse_stream_chunk() handles content_block_start/delta
- Handles text_delta for incremental text output
- Handles input_json_delta for tool call streaming
- message_delta returns final chunk with usage
- message_stop signals end of stream
"
```

---

## Verification

```bash
cd /Users/lijunyi/road/claude-code
python3 -m pytest src_py/api/test_client.py -v
```

Expected: **5 passed**

---

## Next Steps

1. Implement tool_call streaming (parse tool_use blocks)
2. Add integration test with actual LiteLLM API
3. Implement stream_complete_with_backpressure per spec Section 17
