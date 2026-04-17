# Memory Store Implementation Plan (Mem0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement MemoryStore using Mem0 client interface per design spec Section 13. Mem0 provides semantic memory storage with vector search. Milvus provides the vector database backend.

**Architecture:** Per spec Section 13:
- `Mem0Client(config)` - Memory storage client
- `MilvusClient(config.milvus_uri)` - Vector database client
- Text chunking already implemented in `_chunk_text()`

**Note:** For MVP without running Mem0/Milvus services, implement using an in-memory backend that follows the Mem0 interface. The interface is designed for easy swap to real Mem0 + Milvus.

---

## File Structure

```
src_py/memory/
├── __init__.py              # Already exports (NO CHANGE)
├── models.py                 # Already has MemoryConfig, MemoryResult (NO CHANGE)
├── store.py                  # MODIFY: Implement Mem0Client, MilvusClient, update MemoryStore
└── test_memory_store.py     # CREATE: Unit tests
```

---

## Mem0 Interface (per spec Section 13)

```python
class Mem0Client:
    """Mem0 memory client - stores and retrieves memories."""
    def __init__(self, config: MemoryConfig): ...
    async def add(self, text: str, user_id: str, metadata: dict) -> str: ...
    async def search(self, query: str, user_id: str, limit: int, filters: dict) -> list[MemoryResult]: ...
    async def get(self, memory_id: str) -> MemoryResult | None: ...
    async def delete(self, memory_id: str) -> None: ...
    async def count(self, user_id: str) -> int: ...
    async def get_oldest(self, user_id: str, limit: int) -> list[MemoryResult]: ...

class MilvusClient:
    """Milvus vector database client - handles embeddings."""
    def __init__(self, uri: str): ...
    async def search(self, collection: str, query_vector: list[float], limit: int) -> list[str]: ...
    async def insert(self, collection: str, memory_id: str, vector: list[float]) -> None: ...
```

---

### Task 1: Write Mem0Client and MilvusClient Tests

**Files:**
- Create: `src_py/memory/test_memory_store.py`

- [ ] **Step 1: Create comprehensive test file**

```python
"""Tests for MemoryStore with Mem0 interface."""
import pytest
from datetime import datetime
from src_py.memory.store import MemoryStore, Mem0Client, MilvusClient, AgentMemory
from src_py.memory.models import MemoryConfig, MemoryResult


@pytest.fixture
def config():
    """Memory config for testing."""
    return MemoryConfig(
        provider="mem0",
        vector_store="milvus",
        milvus_uri="http://localhost:19530",
        max_memories_per_user=5,  # Small for testing eviction
        chunk_size=100,
        chunk_overlap=20,
    )


@pytest.fixture
def memory_store(config):
    """Create a MemoryStore instance."""
    return MemoryStore(config)


@pytest.fixture
def user_id():
    return "test_user_123"


# === Mem0Client Tests ===

@pytest.mark.asyncio
async def test_mem0_client_initialization(config):
    """Mem0Client initializes with config."""
    client = Mem0Client(config)
    assert client.config == config
    assert client._storage == {}


@pytest.mark.asyncio
async def test_mem0_add_returns_memory_id(config):
    """Mem0Client.add() stores memory and returns ID."""
    client = Mem0Client(config)
    memory_id = await client.add(
        text="Test memory content",
        user_id="user1",
        metadata={"source": "test"},
    )
    assert memory_id.startswith("mem_")
    assert "user1" in memory_id


@pytest.mark.asyncio
async def test_mem0_search_returns_results(config):
    """Mem0Client.search() finds memories."""
    client = Mem0Client(config)
    await client.add(text="Python is awesome", user_id="user1", metadata={})
    await client.add(text="JavaScript is for web", user_id="user1", metadata={})
    await client.add(text="Python async features", user_id="user1", metadata={})

    results = await client.search(query="Python", user_id="user1", limit=10, filters=None)

    assert len(results) >= 2  # Found both Python memories
    # Results should be ordered by relevance
    for r in results:
        assert "python" in r.content.lower()


@pytest.mark.asyncio
async def test_mem0_get_returns_memory(config):
    """Mem0Client.get() retrieves by ID."""
    client = Mem0Client(config)
    memory_id = await client.add(text="Specific memory", user_id="user1", metadata={})

    result = await client.get(memory_id)
    assert result is not None
    assert result.content == "Specific memory"
    assert result.id == memory_id


@pytest.mark.asyncio
async def test_mem0_delete_removes_memory(config):
    """Mem0Client.delete() removes memory."""
    client = Mem0Client(config)
    memory_id = await client.add(text="To be deleted", user_id="user1", metadata={})

    await client.delete(memory_id)
    result = await client.get(memory_id)
    assert result is None


@pytest.mark.asyncio
async def test_mem0_count_returns_count(config):
    """Mem0Client.count() returns number of memories."""
    client = Mem0Client(config)
    await client.add(text="Memory 1", user_id="user1", metadata={})
    await client.add(text="Memory 2", user_id="user1", metadata={})

    count = await client.count("user1")
    assert count == 2


# === MilvusClient Tests ===

@pytest.mark.asyncio
async def test_milvus_client_initialization():
    """MilvusClient initializes with URI."""
    client = MilvusClient("http://localhost:19530")
    assert client.uri == "http://localhost:19530"


@pytest.mark.asyncio
async def test_milvus_insert_and_search():
    """MilvusClient stores and searches vectors."""
    client = MilvusClient("http://localhost:19530")

    # Insert vectors
    await client.insert(collection="test", memory_id="mem1", vector=[0.1, 0.2, 0.3])
    await client.insert(collection="test", memory_id="mem2", vector=[0.4, 0.5, 0.6])

    # Search (will use in-memory fallback since no real Milvus)
    results = await client.search(collection="test", query_vector=[0.15, 0.25, 0.35], limit=2)

    assert isinstance(results, list)
    assert len(results) <= 2


# === MemoryStore Integration Tests ===

@pytest.mark.asyncio
async def test_memory_store_add(memory_store, user_id):
    """MemoryStore.add() creates memories."""
    memory_id = await memory_store.add(
        content="Important information about Python.",
        user_id=user_id,
        metadata={"topic": "python"},
    )
    assert memory_id.startswith(f"mem_{user_id}_")


@pytest.mark.asyncio
async def test_memory_store_search(memory_store, user_id):
    """MemoryStore.search() finds relevant memories."""
    await memory_store.add(content="Python has async/await.", user_id=user_id)
    await memory_store.add(content="JavaScript runs in browser.", user_id=user_id)
    await memory_store.add(content="Python decorators are powerful.", user_id=user_id)

    results = await memory_store.search(query="Python decorators", user_id=user_id, limit=10)

    assert len(results) >= 1
    # Most relevant result should be about Python decorators
    assert results[0].score >= results[1].score if len(results) > 1 else True


@pytest.mark.asyncio
async def test_memory_store_lru_eviction(memory_store, user_id):
    """MemoryStore evicts oldest memories when limit reached."""
    # config max_memories_per_user = 5
    for i in range(10):
        await memory_store.add(content=f"Memory {i}", user_id=user_id)

    count = await memory_store.count(user_id)
    assert count == 5


@pytest.mark.asyncio
async def test_agent_memory_recall_and_memorize(memory_store, user_id):
    """AgentMemory correctly wraps MemoryStore."""
    agent_memory = AgentMemory(agent_id=user_id, memory_store=memory_store)

    await agent_memory.memorize(content="Learned about pytest fixtures")
    await agent_memory.memorize(content="Python dataclasses simplify code")

    results = await agent_memory.recall(query="pytest", limit=5)

    assert len(results) >= 1
    assert "pytest" in results[0].content.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/lijunyi/road/claude-code && python3 -m pytest src_py/memory/test_memory_store.py -v`
Expected: FAIL - methods return None/[]

---

### Task 2: Implement Mem0Client

**Files:**
- Modify: `src_py/memory/store.py`

- [ ] **Step 1: Add Mem0Client class after imports**

Insert after line 9 (after models import):

```python
class Mem0Client:
    """Mem0 memory client interface - per design spec Section 13.

    This implementation uses in-memory storage for MVP.
    To use real Mem0, replace with: from mem0ai import Mem0Client
    """

    def __init__(self, config: MemoryConfig):
        self.config = config
        self._storage: dict[str, dict] = {}  # memory_id -> {"content": str, "user_id": str, "metadata": dict, "created_at": datetime}
        self._vectors: dict[str, list[float]] = {}  # memory_id -> embedding vector

    async def add(self, text: str, user_id: str, metadata: dict) -> str:
        """Add a memory and return memory_id."""
        import hashlib

        memory_id = f"mem_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self._storage[memory_id] = {
            "content": text,
            "user_id": user_id,
            "metadata": metadata,
            "created_at": datetime.now(),
        }
        # Generate embedding vector
        self._vectors[memory_id] = self._embed_text(text)
        return memory_id

    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[MemoryResult]:
        """Search memories by semantic similarity."""
        if not self._vectors:
            return []

        query_vector = self._embed_text(query)
        query_words = set(query.lower().split())
        results = []

        for memory_id, data in self._storage.items():
            if data["user_id"] != user_id:
                continue

            content = data["content"]
            content_words = set(content.lower().split())

            # Jaccard similarity on words
            if query_words and content_words:
                intersection = query_words & content_words
                union = query_words | content_words
                score = len(intersection) / len(union) if union else 0
            else:
                score = 0

            if score > 0 or not query_words:
                results.append(MemoryResult(
                    id=memory_id,
                    content=content,
                    score=score,
                    metadata=data.get("metadata", {}),
                    created_at=data.get("created_at", datetime.now()),
                ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def get(self, memory_id: str) -> MemoryResult | None:
        """Get a memory by ID."""
        data = self._storage.get(memory_id)
        if not data:
            return None

        return MemoryResult(
            id=memory_id,
            content=data["content"],
            score=1.0,
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now()),
        )

    async def delete(self, memory_id: str) -> None:
        """Delete a memory."""
        self._storage.pop(memory_id, None)
        self._vectors.pop(memory_id, None)

    async def count(self, user_id: str) -> int:
        """Count memories for a user."""
        return sum(1 for d in self._storage.values() if d["user_id"] == user_id)

    async def get_oldest(self, user_id: str, limit: int) -> list[MemoryResult]:
        """Get oldest memories for eviction."""
        user_memories = [
            (mid, data) for mid, data in self._storage.items()
            if data["user_id"] == user_id
        ]
        user_memories.sort(key=lambda x: x[1]["created_at"])

        results = []
        for memory_id, data in user_memories[:limit]:
            results.append(MemoryResult(
                id=memory_id,
                content=data["content"],
                score=1.0,
                metadata=data.get("metadata", {}),
                created_at=data["created_at"],
            ))
        return results

    def _embed_text(self, text: str) -> list[float]:
        """Generate embedding vector using word hashing (TF-IDF style)."""
        words = text.lower().split()
        vector = [0.0] * 128
        for word in words:
            h = hash(word) % 128
            vector[h] += 1.0
        # Normalize
        magnitude = sum(v * v for v in vector) ** 0.5
        if magnitude > 0:
            vector = [v / magnitude for v in vector]
        return vector
```

- [ ] **Step 2: Run Mem0Client tests**

Run: `cd /Users/lijunyi/road/claude-code && python3 -m pytest src_py/memory/test_memory_store.py::test_mem0 -v`
Expected: PASS

- [ ] **Step 3: Commit Mem0Client**

```bash
cd /Users/lijunyi/road/claude-code
git add src_py/memory/store.py
git commit -m "feat(memory): implement Mem0Client with in-memory storage

- Mem0Client.add() stores memories with auto-embedding
- Mem0Client.search() uses Jaccard similarity on words
- Mem0Client.get/delete/count/get_oldest implemented
- _embed_text() generates hash-based vectors
"
```

---

### Task 3: Implement MilvusClient

**Files:**
- Modify: `src_py/memory/store.py`

- [ ] **Step 1: Add MilvusClient class**

Insert after Mem0Client class:

```python
class MilvusClient:
    """Milvus vector database client - per design spec Section 13.

    This implementation uses in-memory storage for MVP.
    To use real Milvus, replace with: from pymilvus import MilvusClient
    """

    def __init__(self, uri: str):
        self.uri = uri
        self._vectors: dict[str, dict] = {}  # memory_id -> {"collection": str, "vector": list[float]}

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 10,
    ) -> list[str]:
        """Search vectors by similarity, return memory_ids."""
        if not self._vectors or not query_vector:
            return []

        # Compute cosine similarity
        results = []
        for memory_id, data in self._vectors.items():
            if data["collection"] != collection:
                continue

            vector = data["vector"]
            # Cosine similarity
            dot = sum(q * v for q, v in zip(query_vector, vector))
            query_mag = sum(q * q for q in query_vector) ** 0.5
            vec_mag = sum(v * v for v in vector) ** 0.5
            if query_mag > 0 and vec_mag > 0:
                similarity = dot / (query_mag * vec_mag)
                results.append((memory_id, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return [mid for mid, _ in results[:limit]]

    async def insert(
        self,
        collection: str,
        memory_id: str,
        vector: list[float],
    ) -> None:
        """Insert a vector into the collection."""
        self._vectors[memory_id] = {
            "collection": collection,
            "vector": vector,
        }

    async def delete(self, memory_id: str) -> None:
        """Delete a vector."""
        self._vectors.pop(memory_id, None)
```

- [ ] **Step 2: Run MilvusClient tests**

Run: `cd /Users/lijunyi/road/claude-code && python3 -m pytest src_py/memory/test_memory_store.py::test_milvus -v`
Expected: PASS

- [ ] **Step 3: Commit MilvusClient**

```bash
cd /Users/lijunyi/road/claude-code
git add src_py/memory/store.py
git commit -m "feat(memory): implement MilvusClient with in-memory vectors

- MilvusClient uses in-memory dict storage for MVP
- search() computes cosine similarity
- insert()/delete() manage vector storage
"
```

---

### Task 4: Update MemoryStore to Use Mem0Client and MilvusClient

**Files:**
- Modify: `src_py/memory/store.py`

- [ ] **Step 1: Update MemoryStore.__init__**

Replace lines 11-32 with:

```python
class MemoryStore:
    """Memory store with Mem0 + Milvus - matches design spec Section 13."""

    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        self.client = Mem0Client(self.config)
        self.vector_store = MilvusClient(self.config.milvus_uri)
        self._lru_cache: dict[str, datetime] = {}
```

- [ ] **Step 2: Update add() method**

Replace lines 34-57 with:

```python
async def add(
    self,
    content: str,
    user_id: str,
    metadata: dict[str, Any] | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> str:
    """Add a memory with automatic chunking."""
    chunk_size = chunk_size or self.config.chunk_size
    chunk_overlap = chunk_overlap or self.config.chunk_overlap
    metadata = metadata or {}

    # 1. Auto chunking (already implemented)
    chunks = self._chunk_text(content, chunk_size, chunk_overlap)

    # 2. Store to Mem0 via client
    memory_ids = []
    for i, chunk in enumerate(chunks):
        meta = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
        memory_id = await self.client.add(
            text=chunk,
            user_id=user_id,
            metadata=meta,
        )
        memory_ids.append(memory_id)
        self._lru_cache[memory_id] = datetime.now()

    # 3. Eviction check
    await self._check_eviction(user_id)

    return memory_ids[0] if memory_ids else ""
```

- [ ] **Step 3: Update search(), get(), list_by_user(), delete() methods**

Replace search() body (lines 59-68):

```python
async def search(
    self,
    query: str,
    user_id: str,
    limit: int = 10,
    filters: dict | None = None,
) -> list[MemoryResult]:
    """Search memories by semantic similarity."""
    return await self.client.search(query=query, user_id=user_id, limit=limit, filters=filters)
```

Replace get() body (lines 70-77):

```python
async def get(self, memory_id: str) -> MemoryResult | None:
    """Get a memory by ID."""
    if memory_id in self._lru_cache:
        self._lru_cache[memory_id] = datetime.now()
    return await self.client.get(memory_id)
```

Replace list_by_user() body (lines 88-90):

```python
async def list_by_user(self, user_id: str, limit: int = 100) -> list[MemoryResult]:
    """List all memories for a user."""
    results = []
    for memory_id in list(self._lru_cache.keys()):
        if memory_id.startswith(f"mem_{user_id}_"):
            result = await self.client.get(memory_id)
            if result:
                results.append(result)
    results.sort(key=lambda x: x.created_at, reverse=True)
    return results[:limit]
```

Replace delete() body (lines 84-86):

```python
async def delete(self, memory_id: str) -> None:
    """Delete a memory."""
    self._lru_cache.pop(memory_id, None)
    await self.client.delete(memory_id)
```

- [ ] **Step 4: Update count() method**

Replace lines 92-94:

```python
async def count(self, user_id: str) -> int:
    """Count memories for a user."""
    return await self.client.count(user_id)
```

- [ ] **Step 5: Update _check_eviction() to use client.get_oldest()**

Replace lines 102-114:

```python
async def _check_eviction(self, user_id: str) -> None:
    """Check and execute eviction policy."""
    if self.config.eviction_policy != "lru":
        return

    count = await self.client.count(user_id)
    if count > self.config.max_memories_per_user:
        victims = await self.client.get_oldest(
            user_id=user_id,
            limit=count - self.config.max_memories_per_user,
        )
        for victim in victims:
            await self.client.delete(victim.id)
            self._lru_cache.pop(victim.id, None)
```

- [ ] **Step 6: Run all memory tests**

Run: `cd /Users/lijunyi/road/claude-code && python3 -m pytest src_py/memory/test_memory_store.py -v`
Expected: **13 passed**

- [ ] **Step 7: Commit MemoryStore updates**

```bash
cd /Users/lijunyi/road/claude-code
git add src_py/memory/store.py src_py/memory/test_memory_store.py
git commit -m "feat(memory): update MemoryStore to use Mem0Client and MilvusClient

- MemoryStore now delegates to Mem0Client for storage
- MilvusClient used for vector operations (future embedding)
- _check_eviction() uses client.get_oldest() for LRU
- All 13 tests passing
"
```

---

## Verification

```bash
cd /Users/lijunyi/road/claude-code
python3 -m pytest src_py/memory/test_memory_store.py -v
```

Expected output: **13 passed**

---

## Next Steps (Future Enhancement)

1. **Real Mem0**: Replace `Mem0Client` with `from mem0ai import Mem0Client`
2. **Real Milvus**: Replace `MilvusClient` with `from pymilvus import MilvusClient`
3. **Real Embeddings**: Use `sentence-transformers` or OpenAI embeddings instead of hash-based

To enable real Mem0 + Milvus:
```bash
pip install mem0ai pymilvus sentence-transformers
# Run Mem0 and Milvus services
```
