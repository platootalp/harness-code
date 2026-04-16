# src_py Implementation Plans Index

**Date**: 2026-04-02
**Status**: Ready for Implementation

---

## Active Plans

| Plan | Priority | Tasks | Summary |
|------|----------|-------|---------|
| [Memory Store](2026-04-02-memory-store-implementation.md) | P0 | 4 | In-memory backend for MemoryStore with search, LRU eviction |
| [State Sync WebSocket](2026-04-02-state-sync-websocket-implementation.md) | P0 | 4 | WebSocket/SSE/Polling connections for real-time sync |
| [Streaming Output](2026-04-02-streaming-output-implementation.md) | P1 | 2 | Complete LLM streaming response parsing |
| [Observability](2026-04-02-observability-implementation.md) | P1 | 4 | Add logging to OTLPExporter, evaluator, tracer - fix silent failures |
| [Skills System](2026-04-02-skills-system-implementation.md) | P2 | 3 | Add tests and logging to Skills System |

---

## Quick Start

To implement any plan using subagent-driven development:

1. Read the plan file
2. Use `superpowers:subagent-driven-development` skill
3. Execute tasks one by one
4. Verify with tests after each task

---

## Plan Details

### Memory Store (P0)
**File**: `docs/superpowers/plans/2026-04-02-memory-store-implementation.md`

**Goal**: Implement MemoryStore using Mem0 client interface per spec Section 13

**Architecture** (per spec):
- `Mem0Client(config)` - Memory storage with user_id, content, metadata
- `MilvusClient(uri)` - Vector database client for embeddings
- In-memory storage for MVP, swappable to real Mem0 + Milvus

**Deliverables**:
- `Mem0Client` class with add/search/get/delete/count/get_oldest
- `MilvusClient` class with insert/search/delete
- MemoryStore delegates to Mem0Client
- 13 unit tests

**Files Changed**:
- `src_py/memory/store.py`
- `src_py/memory/test_memory_store.py` (new)

---

### State Sync WebSocket (P0)
**File**: `docs/superpowers/plans/2026-04-02-state-sync-websocket-implementation.md`

**Goal**: Implement real network transport for state sync

**Deliverables**:
- WebSocketConnection using httpx
- PollingConnection with HTTP POST/GET
- SSEConnection with EventSource
- 10 unit tests

**Files Changed**:
- `src_py/state_sync/syncer.py`
- `src_py/state_sync/test_syncer.py` (new)

---

### Streaming Output (P1)
**File**: `docs/superpowers/plans/2026-04-02-streaming-output-implementation.md`

**Goal**: Complete LLM streaming response parsing

**Deliverables**:
- _parse_stream_chunk() implementation
- Text delta accumulation
- Tool call streaming (partial)
- 5 unit tests

**Files Changed**:
- `src_py/api/client.py`
- `src_py/api/test_client.py` (new)

---

### Observability (P1)
**File**: `docs/superpowers/plans/2026-04-02-observability-implementation.md`

**Goal**: Fix silent exception handling in observability components

**Deliverables**:
- Logging added to OTLPExporter.export
- Logging added to _HTTPOTLPExporter.export
- Logging added to evaluator._try_phoenix_eval
- Logging added to tracer._notify_observers
- Unit tests for error logging

**Files Changed**:
- `src_py/observability/span_processors.py`
- `src_py/observability/evaluator.py`
- `src_py/observability/tracer.py`
- `src_py/observability/test_observability.py` (new)

---

### Skills System (P2)
**File**: `docs/superpowers/plans/2026-04-02-skills-system-implementation.md`

**Goal**: Verify and improve Skills System with tests and logging

**Deliverables**:
- Comprehensive unit tests for SkillRegistry, SkillExecutor, SkillTool
- Error logging added to SkillExecutor._sandboxed_execute
- Error logging added to SkillRegistry.discover

**Files Changed**:
- `src_py/skills/registry.py`
- `src_py/skills/test_skills_registry.py` (new)

---

## Estimated Effort

| Plan | Tasks | Estimated Time |
|------|-------|----------------|
| Memory Store | 4 | 40 minutes |
| State Sync WebSocket | 4 | 45 minutes |
| Streaming Output | 2 | 20 minutes |
| Observability | 4 | 20 minutes |
| Skills System | 3 | 25 minutes |
| **Total** | **17** | **~150 minutes** |

---

## Execution Options

### Option 1: Subagent-Driven (Recommended)
- Use `superpowers:subagent-driven-development` skill
- One subagent per task
- Review between tasks
- Best for: Quality critical changes

### Option 2: Inline Execution
- Use `superpowers:executing-plans` skill
- Batch execution with checkpoints
- Best for: Faster completion of well-understood tasks

---

## Dependencies

```
Memory Store
    └── (no dependencies)

State Sync WebSocket
    └── httpx (already in dependencies)

Streaming Output
    └── LiteLLMClient (already in api/client.py)
```

---

## Testing Strategy

Each plan includes:
1. Write failing tests first (TDD)
2. Implement minimal code
3. Verify tests pass
4. Commit

Run all tests after plan completion:
```bash
cd /Users/lijunyi/road/claude-code
python3 -m pytest src_py/memory/test_memory_store.py \
                src_py/state_sync/test_syncer.py \
                src_py/api/test_client.py -v
```
