# Memory API

## Overview

The Memory module provides short-term and long-term memory storage and retrieval.

## ShortTermMemory

### Methods

#### `add(key: str, value: Any) -> None`

Adds an item to short-term memory.

**Parameters:**
- `key` (str): Memory key
- `value` (Any): Value to store

#### `get(key: str) -> Any | None`

Retrieves an item.

**Parameters:**
- `key` (str): Memory key

**Returns:**
- `Any | None`: The value if found

#### `clear() -> None`

Clears all short-term memory.

## LongTermMemory

### Methods

#### `store(session_id: str, memory_type: MemoryType, content: str, metadata: dict | None = None) -> str`

Stores a memory entry.

**Parameters:**
- `session_id` (str): Session identifier
- `memory_type` (MemoryType): Type of memory
- `content` (str): Memory content
- `metadata` (dict, optional): Additional metadata

**Returns:**
- `str`: Memory ID

#### `retrieve(query: str, limit: int = 10) -> list[MemoryEntry]`

Retrieves memories matching a query.

**Parameters:**
- `query` (str): Search query
- `limit` (int): Maximum results

**Returns:**
- `list[MemoryEntry]`: Matching memories

## MemoryRetriever

### Methods

#### `semantic_search(query: str, limit: int = 5) -> list[RetrievalResult]`

Performs semantic search on memories.

**Parameters:**
- `query` (str): Search query
- `limit` (int): Maximum results

**Returns:**
- `list[RetrievalResult]`: Search results

## Memory Types

| Type | Description |
|------|-------------|
| `EPISODIC` | Event-based memories |
| `SEMANTIC` | Knowledge-based memories |
| `PROCEDURAL` | Task and skill memories |

## Usage Example

```python
from mozi.memory import ShortTermMemory, LongTermMemory

# Short-term
stm = ShortTermMemory()
stm.add("last_task", "implement login")

# Long-term
ltm = LongTermMemory()
memory_id = await ltm.store(
    session_id="session-123",
    memory_type=MemoryType.EPISODIC,
    content="User asked to implement login feature"
)
```
