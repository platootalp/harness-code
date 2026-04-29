"""
SSE (Server-Sent Events) parser for Claude Code streaming.

Provides SSE frame parsing for the CCR v2 event stream protocol.
SSE is used for reading streaming events from the Claude API while
HTTP POST is used for writing events back.

Based on the TypeScript SSETransport implementation in:
  src/cli/transports/SSETransport.ts

SSE format reference: https://html.spec.whatwg.org/multipage/server-sent-events.html
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# =============================================================================
# SSE Frame Types
# =============================================================================


@dataclass
class SSEFrame:
    """A parsed SSE frame.

    Attributes:
        event: Optional event type (the part after ``event:``).
        id: Optional event ID (the part after ``id:``).
        data: Optional data content (concatenated from all ``data:`` lines,
            joined by newlines per SSE spec).
    """

    event: str | None = None
    id: str | None = None
    data: str | None = None


# =============================================================================
# Stream Client Event (CCR v2 protocol)
# =============================================================================


@dataclass
class StreamClientEvent:
    """Payload for ``event: client_event`` SSE frames.

    This matches the StreamClientEvent proto message in session_stream.proto.
    It is the event type sent to worker subscribers on the CCR v2 stream.

    Attributes:
        event_id: Unique identifier for this event.
        sequence_num: Monotonically increasing sequence number.
        event_type: Type string for the inner event.
        source: Source of the event (e.g., "cloud", "bridge").
        payload: The actual event payload (proto JSON).
        created_at: ISO 8601 timestamp when the event was created.
    """

    event_id: str
    sequence_num: int
    event_type: str
    source: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "sequence_num": self.sequence_num,
            "event_type": self.event_type,
            "source": self.source,
            "payload": self.payload,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamClientEvent:
        """Deserialize from dictionary."""
        return cls(
            event_id=data.get("event_id", ""),
            sequence_num=data.get("sequence_num", 0),
            event_type=data.get("event_type", ""),
            source=data.get("source", ""),
            payload=data.get("payload", {}),
            created_at=data.get("created_at", ""),
        )


# =============================================================================
# SSE Frame Parser
# =============================================================================


def parse_sse_frames(buffer: str) -> tuple[list[SSEFrame], str]:
    """Parse SSE frames incrementally from a text buffer.

    This function implements the SSE frame parsing algorithm per the SSE spec.
    It splits the buffer on double newlines (``\\n\\n``) to separate frames,
    then parses each frame's lines to extract ``event:``, ``id:``, and ``data:``
    fields.

    Multiple ``data:`` lines within the same frame are concatenated with
    newlines (per SSE spec). Lines starting with ``:`` are treated as comments
    and ignored (except they do reset liveness tracking).

    Args:
        buffer: The accumulated text buffer from the SSE stream.

    Returns:
        A tuple of (frames, remaining) where:
        - frames: List of parsed SSEFrame objects
        - remaining: The portion of the buffer that doesn't yet form a
          complete frame (should be kept for the next call)

    Example:
        >>> frames, remaining = parse_sse_frames("data: hello\\n\\ndata: world\\n\\n")
        >>> len(frames)
        2
        >>> frames[0].data
        'hello'
        >>> frames[1].data
        'world'
        >>> remaining
        ''

        >>> # Multi-line data
        >>> frames, _ = parse_sse_frames("data: line1\\ndata: line2\\n\\n")
        >>> frames[0].data
        'line1\\nline2'
    """
    frames: list[SSEFrame] = []
    pos = 0

    while True:
        idx = buffer.find("\n\n", pos)
        if idx == -1:
            break

        raw_frame = buffer[pos:idx]
        pos = idx + 2

        if not raw_frame.strip():
            continue

        frame = SSEFrame()
        is_comment = False

        for line in raw_frame.split("\n"):
            if line.startswith(":"):
                # SSE comment line (e.g., ":keepalive")
                is_comment = True
                continue

            colon_idx = line.find(":")
            if colon_idx == -1:
                continue

            field_name = line[:colon_idx]
            # Per SSE spec: strip one leading space after colon if present
            if len(line) > colon_idx + 1 and line[colon_idx + 1] == " ":
                value = line[colon_idx + 2 :]
            else:
                value = line[colon_idx + 1 :]

            if field_name == "event":
                frame.event = value
            elif field_name == "id":
                frame.id = value
            elif field_name == "data":
                # Per SSE spec: multiple data: lines are concatenated with \n
                if frame.data:
                    frame.data = frame.data + "\n" + value
                else:
                    frame.data = value
            # Ignore other fields (retry:, etc.)

        # Only emit frames that have data (or are pure comments which reset liveness)
        if frame.data is not None or is_comment:
            frames.append(frame)

    remaining = buffer[pos:]
    return frames, remaining


def parse_stream_client_event(data: str) -> StreamClientEvent:
    """Parse a JSON string into a StreamClientEvent.

    Args:
        data: JSON string containing a StreamClientEvent.

    Returns:
        A StreamClientEvent instance.

    Raises:
        json.JSONDecodeError: If the data is not valid JSON.
        ValueError: If the parsed JSON is not a dict.
    """
    parsed = json.loads(data)
    if not isinstance(parsed, dict):
        raise ValueError(f"StreamClientEvent must be a dict, got {type(parsed).__name__}")
    return StreamClientEvent.from_dict(parsed)


# =============================================================================
# SSE Parser (Async Streaming)
# =============================================================================


class SSEParser:
    """Incremental SSE parser for async byte streams.

    This class wraps an async byte stream and yields parsed SSE frames.
    It handles the complexity of buffering incomplete frames, decoding
    chunks, and extracting complete SSE events.

    This is a stateful parser — create one per SSE connection. It is
    designed to work with httpx.AsyncResponse.acontent流() or similar
    async byte iterators.

    Example:
        async def consume_sse(response: httpx.Response) -> AsyncGenerator[SSEFrame, None]:
            parser = SSEParser()
            async for chunk in response.aiter_text():
                async for frame in parser.feed(chunk):
                    yield frame

    Attributes:
        buffer: Current unprocessed text buffer.
        sequence_num: Last seen sequence number (from ``id:`` field).
        seen_sequence_nums: Set of all seen sequence numbers (for dedup).
    """

    def __init__(self) -> None:
        self.buffer: str = ""
        self.sequence_num: int = 0
        self.seen_sequence_nums: set[int] = set()

    def feed(self, chunk: str) -> AsyncGenerator[SSEFrame, None]:
        """Feed a text chunk and yield any complete SSE frames.

        This is a synchronous method that should be called from an async
        context. For a fully async version, use ``feed_async()``.

        Args:
            chunk: A text chunk from the SSE stream.

        Yields:
            SSEFrame objects for each complete frame found in the chunk.
        """
        self.buffer += chunk
        frames, remaining = parse_sse_frames(self.buffer)
        self.buffer = remaining

        for frame in frames:
            # Update sequence number tracking
            if frame.id is not None:
                try:
                    seq_num = int(frame.id)
                    if seq_num not in self.seen_sequence_nums:
                        self.seen_sequence_nums.add(seq_num)
                        # Prune old sequence numbers to prevent unbounded growth
                        if len(self.seen_sequence_nums) > 1000:
                            threshold = self.sequence_num - 200
                            self.seen_sequence_nums = {
                                s for s in self.seen_sequence_nums if s >= threshold
                            }
                    if seq_num > self.sequence_num:
                        self.sequence_num = seq_num
                except ValueError:
                    pass  # Non-numeric id field, ignore

            yield frame

    async def feed_async(
        self, iterator: AsyncIterator[str]
    ) -> AsyncGenerator[SSEFrame, None]:
        """Feed chunks from an async iterator and yield SSE frames.

        This is the fully async version of ``feed()`` that consumes
        text chunks from an async iterator.

        Args:
            iterator: Async iterator yielding text chunks.

        Yields:
            SSEFrame objects for each complete frame found.
        """
        async for chunk in iterator:
            for frame in self.feed(chunk):
                yield frame

    def parse_frame_data(self, frame: SSEFrame) -> dict[str, Any] | None:
        """Parse the ``data:`` field of a frame as JSON.

        If the data field is empty or not valid JSON, returns None.

        Args:
            frame: The SSEFrame to parse.

        Returns:
            The parsed JSON dict, or None if parsing fails.
        """
        if frame.data is None:
            return None
        try:
            parsed = json.loads(frame.data)
            if isinstance(parsed, dict):
                return parsed
            return None
        except json.JSONDecodeError:
            return None

    def reset(self) -> None:
        """Reset the parser state.

        Clears the buffer, sequence number, and seen sequence numbers.
        Use this when starting a new SSE stream.
        """
        self.buffer = ""
        self.sequence_num = 0
        self.seen_sequence_nums.clear()


# =============================================================================
# Blocking / Convenience Parsers
# =============================================================================


def parse_sse_event(data: str) -> SSEFrame | None:
    """Parse a single SSE-formatted event string into an SSEFrame.

    This is a convenience function for parsing a complete SSE event
    (everything after ``data:`` up to the next ``\\n\\n``).

    If the input contains multiple events (separated by ``\\n\\n``),
    only the first one is parsed. Frames without a ``data:`` field
    (e.g., pure comment lines) return None.

    Args:
        data: A string containing an SSE-formatted event. May include
            or omit the trailing double newline.

    Returns:
        An SSEFrame with data, or None if the input is empty,
        only contains comments, or has no data field.
    """
    frames, _ = parse_sse_frames(data)
    if not frames:
        return None
    frame = frames[0]
    return frame if frame.data is not None else None


def parse_ndjson(data: str) -> list[dict[str, Any]]:
    """Parse newline-delimited JSON (NDJSON) from an SSE data field.

    NDJSON is commonly used for streaming JSON where each line is a
    separate JSON object. This is the format used by Claude Code's
    SSE stream payloads.

    Args:
        data: A string containing NDJSON data (one JSON object per line).

    Returns:
        A list of parsed JSON dictionaries.

    Example:
        >>> lines = ' {"type": "assistant"}\\n {"type": "tool_use"}\\n'
        >>> parse_ndjson(lines)
        [{'type': 'assistant'}, {'type': 'tool_use'}]
    """
    result: list[dict[str, Any]] = []
    for line in data.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                result.append(parsed)
        except json.JSONDecodeError:
            pass
    return result
