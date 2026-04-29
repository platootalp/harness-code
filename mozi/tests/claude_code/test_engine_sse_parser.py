"""
Tests for engine/sse_parser.py - SSE parsing.
"""

from __future__ import annotations

import pytest
from claude_code.engine.sse_parser import (
    SSEFrame,
    SSEParser,
    StreamClientEvent,
    parse_ndjson,
    parse_sse_event,
    parse_sse_frames,
    parse_stream_client_event,
)


class TestParseSSEFrames:
    """Tests for the parse_sse_frames function."""

    def test_empty_buffer(self) -> None:
        """Empty buffer returns no frames and empty remaining."""
        frames, remaining = parse_sse_frames("")
        assert frames == []
        assert remaining == ""

    def test_single_frame(self) -> None:
        """A single complete frame is parsed correctly."""
        frames, remaining = parse_sse_frames("data: hello\n\n")
        assert len(frames) == 1
        assert frames[0].data == "hello"
        assert frames[0].event is None
        assert frames[0].id is None
        assert remaining == ""

    def test_multiple_frames(self) -> None:
        """Multiple complete frames are all returned."""
        buffer = "data: first\n\ndata: second\n\ndata: third\n\n"
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 3
        assert frames[0].data == "first"
        assert frames[1].data == "second"
        assert frames[2].data == "third"
        assert remaining == ""

    def test_event_field(self) -> None:
        """The event field is extracted correctly."""
        frames, remaining = parse_sse_frames("event: client_event\ndata: payload\n\n")
        assert len(frames) == 1
        assert frames[0].event == "client_event"
        assert frames[0].data == "payload"

    def test_id_field(self) -> None:
        """The id field is extracted correctly."""
        frames, remaining = parse_sse_frames("id: 42\ndata: msg\n\n")
        assert len(frames) == 1
        assert frames[0].id == "42"
        assert frames[0].data == "msg"

    def test_all_fields(self) -> None:
        """Frames with all fields are parsed correctly."""
        buffer = "id: 7\nevent: client_event\ndata: hello world\n\n"
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 1
        assert frames[0].id == "7"
        assert frames[0].event == "client_event"
        assert frames[0].data == "hello world"

    def test_multiline_data_concatenation(self) -> None:
        """Multiple data: lines are concatenated with newlines."""
        buffer = "data: line1\ndata: line2\ndata: line3\n\n"
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 1
        assert frames[0].data == "line1\nline2\nline3"

    def test_multiline_data_preserves_exact_newlines(self) -> None:
        """Concatenation preserves the exact newlines between data lines."""
        buffer = "data: a\ndata: b\n\n"
        frames, remaining = parse_sse_frames(buffer)
        assert frames[0].data == "a\nb"

    def test_leading_space_after_colon_stripped(self) -> None:
        """One leading space after colon is stripped per SSE spec."""
        frames, _ = parse_sse_frames("data: hello world\n\n")
        assert frames[0].data == "hello world"

    def test_no_space_after_colon_preserved(self) -> None:
        """Values without a space after colon are preserved."""
        frames, _ = parse_sse_frames("data:hello\n\n")
        assert frames[0].data == "hello"

    def test_colon_at_start_is_value(self) -> None:
        """A colon at the start of a value is preserved."""
        frames, _ = parse_sse_frames("data::emotion:\n\n")
        assert frames[0].data == ":emotion:"

    def test_comment_lines_ignored(self) -> None:
        """Lines starting with colon (comments) are ignored."""
        buffer = ": this is a comment\ndata: actual data\n\n"
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 1
        assert frames[0].data == "actual data"

    def test_pure_comment_frame_emitted(self) -> None:
        """Pure comment frames (no data) are still emitted for liveness."""
        buffer = ":keepalive\n\n"
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 1
        assert frames[0].data is None

    def test_ignore_retry_field(self) -> None:
        """The retry field is ignored (not an error)."""
        buffer = "retry: 5000\ndata: after retry\n\n"
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 1
        assert frames[0].data == "after retry"

    def test_ignore_unknown_fields(self) -> None:
        """Unknown fields are silently ignored."""
        buffer = "unknown: value\ndata: real\n\n"
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 1
        assert frames[0].data == "real"

    def test_empty_line_in_frame_skipped(self) -> None:
        """Empty lines within a frame are skipped."""
        buffer = "data: before\n\ndata: after\n\n"
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 2
        assert frames[0].data == "before"
        assert frames[1].data == "after"

    def test_incomplete_frame_remaining(self) -> None:
        """An incomplete frame (no double newline) is left as remaining."""
        buffer = "data: incomplete"
        frames, remaining = parse_sse_frames(buffer)
        assert frames == []
        assert remaining == "data: incomplete"

    def test_incomplete_frame_with_partial_double_newline(self) -> None:
        """Buffer with single newline keeps looking for double newline."""
        buffer = "data: first\n\ndata: second\n"
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 1
        assert frames[0].data == "first"
        assert remaining == "data: second\n"

    def test_incremental_parsing(self) -> None:
        """Frames can be parsed incrementally across multiple calls."""
        # First chunk: partial frame (no \n\n yet)
        frames, remaining = parse_sse_frames("data: first\n")
        assert frames == []
        assert remaining == "data: first\n"

        # Second chunk: adds \n\n after "data: first" - so now it becomes
        # "data: first\ndata: second\n\n" which is ONE complete frame
        # (the second "data: first" line is treated as continuation)
        frames, remaining = parse_sse_frames(remaining + "data: second\n\n")
        assert len(frames) == 1
        # The two data: lines are concatenated per SSE spec
        assert frames[0].data == "first\nsecond"

        # Third chunk: a standalone complete frame
        frames2, remaining2 = parse_sse_frames("data: third\n\n")
        assert len(frames2) == 1
        assert frames2[0].data == "third"

        # For two complete frames in one parse call, we need \n\n\n between them
        frames3, _ = parse_sse_frames("data: a\n\ndata: b\n\n")
        assert len(frames3) == 2
        assert frames3[0].data == "a"
        assert frames3[1].data == "b"

    def test_whitespace_only_frame_skipped(self) -> None:
        """Frames containing only whitespace are skipped."""
        buffer = "   \n\ndata: real\n\n"
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 1
        assert frames[0].data == "real"

    def test_id_with_prefix(self) -> None:
        """ID values with any content are preserved."""
        frames, _ = parse_sse_frames("id: seq_123\ndata: msg\n\n")
        assert frames[0].id == "seq_123"

    def test_multiple_frames_mixed_fields(self) -> None:
        """Frames with varying field sets are parsed correctly."""
        buffer = (
            "data: simple\n\n"
            "event: custom\ndata: with event\n\n"
            "id: 5\nevent: both\ndata: full\n\n"
        )
        frames, remaining = parse_sse_frames(buffer)
        assert len(frames) == 3
        assert frames[0].data == "simple"
        assert frames[0].event is None
        assert frames[1].event == "custom"
        assert frames[2].id == "5"
        assert frames[2].event == "both"


class TestParseSSEEvent:
    """Tests for the parse_sse_event convenience function."""

    def test_single_event(self) -> None:
        """Single event string is parsed correctly."""
        frame = parse_sse_event("data: hello\n\n")
        assert frame is not None
        assert frame.data == "hello"

    def test_no_data_returns_none(self) -> None:
        """Event string with only comments returns None."""
        frame = parse_sse_event(":comment\n\n")
        assert frame is None

    def test_no_data_with_only_comment_line(self) -> None:
        """Pure comment frame (no data) returns None."""
        frame = parse_sse_event(":keepalive\n\n")
        assert frame is None

    def test_multiple_events_returns_first(self) -> None:
        """Multiple events: only the first is returned."""
        frame = parse_sse_event("data: first\n\ndata: second\n\n")
        assert frame is not None
        assert frame.data == "first"

    def test_trailing_newline_ok(self) -> None:
        """Trailing newlines are handled."""
        frame = parse_sse_event("data: test\n\n\n\n")
        assert frame is not None
        assert frame.data == "test"


class TestParseNDJSON:
    """Tests for the parse_ndjson function."""

    def test_empty_string(self) -> None:
        """Empty string returns empty list."""
        assert parse_ndjson("") == []

    def test_single_object(self) -> None:
        """Single JSON object is parsed correctly."""
        result = parse_ndjson('{"type": "assistant"}')
        assert len(result) == 1
        assert result[0] == {"type": "assistant"}

    def test_multiple_objects(self) -> None:
        """Multiple JSON objects (one per line) are parsed."""
        data = ' {"type": "a"}\n {"type": "b"}\n {"type": "c"} '
        result = parse_ndjson(data)
        assert len(result) == 3
        assert result[0] == {"type": "a"}
        assert result[1] == {"type": "b"}
        assert result[2] == {"type": "c"}

    def test_empty_lines_skipped(self) -> None:
        """Empty lines are skipped."""
        result = parse_ndjson('{"a":1}\n\n{"b":2}\n   \n{"c":3}')
        assert len(result) == 3
        assert result[0] == {"a": 1}
        assert result[1] == {"b": 2}
        assert result[2] == {"c": 3}

    def test_non_dict_lines_skipped(self) -> None:
        """Lines that are valid JSON but not dicts are skipped."""
        result = parse_ndjson('{"a":1}\n"string"\n[1,2,3]\n{"b":2}')
        assert len(result) == 2
        assert result[0] == {"a": 1}
        assert result[1] == {"b": 2}

    def test_invalid_json_lines_skipped(self) -> None:
        """Invalid JSON lines are skipped gracefully."""
        result = parse_ndjson('{"a":1}\nnot json\n{"b":2}')
        assert len(result) == 2
        assert result[0] == {"a": 1}
        assert result[1] == {"b": 2}

    def test_nested_objects(self) -> None:
        """Nested JSON objects are parsed correctly."""
        data = '{"outer": {"inner": 42}}\n{"list": [1, 2, 3]}'
        result = parse_ndjson(data)
        assert len(result) == 2
        assert result[0] == {"outer": {"inner": 42}}
        assert result[1] == {"list": [1, 2, 3]}


class TestSSEParser:
    """Tests for the SSEParser class."""

    def test_initial_state(self) -> None:
        """Parser starts with empty buffer and zero sequence number."""
        parser = SSEParser()
        assert parser.buffer == ""
        assert parser.sequence_num == 0
        assert len(parser.seen_sequence_nums) == 0

    def test_feed_single_chunk(self) -> None:
        """Single chunk yields all complete frames."""
        parser = SSEParser()
        frames = list(parser.feed("data: hello\ndata: world\n\n"))
        assert len(frames) == 1
        assert frames[0].data == "hello\nworld"

    def test_feed_incremental_chunks(self) -> None:
        """Frames are yielded as chunks arrive."""
        parser = SSEParser()

        # Feed first complete frame
        frames1 = list(parser.feed("data: first\n\n"))
        assert len(frames1) == 1
        assert frames1[0].data == "first"

        # Feed incomplete frame (no \n\n yet)
        frames2 = list(parser.feed("data: second"))
        assert frames2 == []

        # Feed rest: the buffer becomes "data: second\ndata: third\n\n"
        # which is ONE frame with concatenated data per SSE spec
        frames3 = list(parser.feed("\ndata: third\n\n"))
        assert len(frames3) == 1
        assert frames3[0].data == "second\nthird"

        # Feed a complete second frame
        frames4 = list(parser.feed("data: fourth\n\n"))
        assert len(frames4) == 1
        assert frames4[0].data == "fourth"

    def test_feed_sequence_number_tracking(self) -> None:
        """Sequence numbers from id: fields are tracked."""
        parser = SSEParser()
        list(parser.feed("id: 10\ndata: msg\n\n"))
        assert parser.sequence_num == 10
        assert 10 in parser.seen_sequence_nums

    def test_feed_duplicate_sequence_skipped(self) -> None:
        """Duplicate sequence numbers are tracked but don't update sequence_num."""
        parser = SSEParser()
        list(parser.feed("id: 5\ndata: first\n\n"))
        list(parser.feed("id: 5\ndata: dup\n\n"))
        assert parser.sequence_num == 5
        assert 5 in parser.seen_sequence_nums

    def test_feed_non_numeric_id_ignored(self) -> None:
        """Non-numeric id values don't affect sequence tracking."""
        parser = SSEParser()
        list(parser.feed("id: abc123\ndata: msg\n\n"))
        assert parser.sequence_num == 0

    def test_feed_prunes_old_sequence_nums(self) -> None:
        """Old sequence numbers are pruned to prevent unbounded growth."""
        parser = SSEParser()
        # Feed many sequence numbers
        for i in range(500):
            parser.feed(f"id: {i}\ndata: msg{i}\n\n")
        # Old ones should be pruned when we go above threshold
        list(parser.feed("id: 800\ndata: msg800\n\n"))
        # The old sequence nums should have been pruned
        assert len(parser.seen_sequence_nums) < 500
        assert 800 in parser.seen_sequence_nums
        assert parser.sequence_num == 800

    def test_parse_frame_data_json(self) -> None:
        """parse_frame_data returns parsed JSON from frame data."""
        parser = SSEParser()
        frames = list(parser.feed('data: {"type": "test"}\n\n'))
        result = parser.parse_frame_data(frames[0])
        assert result == {"type": "test"}

    def test_parse_frame_data_invalid_json(self) -> None:
        """parse_frame_data returns None for invalid JSON."""
        parser = SSEParser()
        frames = list(parser.feed("data: not json\n\n"))
        result = parser.parse_frame_data(frames[0])
        assert result is None

    def test_parse_frame_data_none(self) -> None:
        """parse_frame_data returns None for frames without data."""
        parser = SSEParser()
        frame = SSEFrame()
        result = parser.parse_frame_data(frame)
        assert result is None

    def test_reset(self) -> None:
        """reset() clears all state."""
        parser = SSEParser()
        list(parser.feed("id: 42\ndata: msg\n\n"))
        list(parser.feed("id: 43\ndata: msg2\n\n"))
        assert parser.sequence_num == 43
        assert len(parser.seen_sequence_nums) == 2

        parser.reset()
        assert parser.buffer == ""
        assert parser.sequence_num == 0
        assert len(parser.seen_sequence_nums) == 0

        # After reset, parser should work normally again
        frames = list(parser.feed("id: 1\ndata: fresh\n\n"))
        assert len(frames) == 1
        assert parser.sequence_num == 1


class TestStreamClientEvent:
    """Tests for StreamClientEvent."""

    def test_create(self) -> None:
        """StreamClientEvent can be constructed with required fields."""
        event = StreamClientEvent(
            event_id="evt_001",
            sequence_num=10,
            event_type="message_start",
            source="cloud",
        )
        assert event.event_id == "evt_001"
        assert event.sequence_num == 10
        assert event.event_type == "message_start"
        assert event.source == "cloud"
        assert event.payload == {}
        assert event.created_at == ""

    def test_to_dict(self) -> None:
        """to_dict serializes all fields."""
        event = StreamClientEvent(
            event_id="evt_002",
            sequence_num=20,
            event_type="content_block_delta",
            source="bridge",
            payload={"type": "text_delta", "text": "Hello"},
            created_at="2024-01-01T00:00:00Z",
        )
        d = event.to_dict()
        assert d["event_id"] == "evt_002"
        assert d["sequence_num"] == 20
        assert d["event_type"] == "content_block_delta"
        assert d["source"] == "bridge"
        assert d["payload"] == {"type": "text_delta", "text": "Hello"}
        assert d["created_at"] == "2024-01-01T00:00:00Z"

    def test_from_dict(self) -> None:
        """from_dict reconstructs from dictionary."""
        data = {
            "event_id": "evt_003",
            "sequence_num": 30,
            "event_type": "message_delta",
            "source": "cloud",
            "payload": {"usage": {"output_tokens": 50}},
            "created_at": "2024-01-02T00:00:00Z",
        }
        event = StreamClientEvent.from_dict(data)
        assert event.event_id == "evt_003"
        assert event.sequence_num == 30
        assert event.event_type == "message_delta"
        assert event.source == "cloud"
        assert event.payload == {"usage": {"output_tokens": 50}}

    def test_roundtrip(self) -> None:
        """to_dict + from_dict roundtrip preserves data."""
        original = StreamClientEvent(
            event_id="evt_round",
            sequence_num=100,
            event_type="tool_use",
            source="bridge",
            payload={"name": "bash", "args": {}},
            created_at="2024-03-15T12:00:00Z",
        )
        restored = StreamClientEvent.from_dict(original.to_dict())
        assert restored.event_id == original.event_id
        assert restored.sequence_num == original.sequence_num
        assert restored.event_type == original.event_type
        assert restored.source == original.source
        assert restored.payload == original.payload
        assert restored.created_at == original.created_at


class TestParseStreamClientEvent:
    """Tests for parse_stream_client_event."""

    def test_valid_json(self) -> None:
        """Valid JSON is parsed into StreamClientEvent."""
        data = '{"event_id": "e1", "sequence_num": 1, "event_type": "test", "source": "s"}'
        event = parse_stream_client_event(data)
        assert event.event_id == "e1"
        assert event.sequence_num == 1
        assert event.event_type == "test"
        assert event.source == "s"

    def test_invalid_json(self) -> None:
        """Invalid JSON raises JSONDecodeError."""
        import json

        with pytest.raises(json.JSONDecodeError):
            parse_stream_client_event("not json")

    def test_non_dict_json(self) -> None:
        """Non-dict JSON raises ValueError."""
        with pytest.raises(ValueError, match="must be a dict"):
            parse_stream_client_event('"just a string"')

    def test_partial_dict(self) -> None:
        """Partial dict with missing fields uses defaults."""
        data = '{"event_id": "e2", "sequence_num": 5}'
        event = parse_stream_client_event(data)
        assert event.event_id == "e2"
        assert event.sequence_num == 5
        assert event.event_type == ""
        assert event.source == ""


class TestSSEFrame:
    """Tests for SSEFrame dataclass."""

    def test_default_fields(self) -> None:
        """SSEFrame has all fields as None by default."""
        frame = SSEFrame()
        assert frame.event is None
        assert frame.id is None
        assert frame.data is None

    def test_all_fields_set(self) -> None:
        """SSEFrame can be constructed with all fields."""
        frame = SSEFrame(event="custom", id="123", data="payload")
        assert frame.event == "custom"
        assert frame.id == "123"
        assert frame.data == "payload"
