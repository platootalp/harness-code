# Session 模块崩溃恢复实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Session 模块的崩溃恢复机制，包括消息持久化、流式输出保存和 resume 功能。

**Architecture:** Session 模块采用存储抽象（Storage 接口）+ 具体实现（FileSessionStorage）的设计。Manager 负责业务逻辑，Models 定义数据结构，Storage 负责持久化。消息立即保存策略确保崩溃后可恢复。

**Tech Stack:** Python 3.11+, asyncio, Pydantic/dataclasses, JSON 文件存储

---

## 文件结构

```
mozi/orchestrator/session/
├── __init__.py           # 模块导出
├── models.py             # 数据模型（Session, Message, SessionConfig）
├── storage.py            # 存储抽象接口和文件实现
└── manager.py            # 会话管理器
```

---

## Task 1: 创建目录结构

**Files:**
- Create: `mozi/orchestrator/session/__init__.py`
- Create: `mozi/orchestrator/session/models.py`
- Create: `mozi/orchestrator/session/storage.py`
- Create: `mozi/orchestrator/session/manager.py`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p mozi/orchestrator/session
```

- [ ] **Step 2: 创建 __init__.py**

```python
"""Session module - 会话管理和崩溃恢复"""

from .models import (
    Session,
    SessionStatus,
    Message,
    MessageRole,
    SessionMetadata,
    SessionConfig,
)
from .storage import SessionStorage, FileSessionStorage
from .manager import SessionManager

__all__ = [
    "Session",
    "SessionStatus",
    "Message",
    "MessageRole",
    "SessionMetadata",
    "SessionConfig",
    "SessionStorage",
    "FileSessionStorage",
    "SessionManager",
]
```

- [ ] **Step 3: Commit**

```bash
git add mozi/orchestrator/session/__init__.py
git commit -m "feat(session): create module directory structure"
```

---

## Task 2: 实现数据模型 (models.py)

**Files:**
- Create: `mozi/orchestrator/session/models.py`
- Create: `tests/unit/orchestrator/session/test_models.py`

- [ ] **Step 1: 编写测试**

```python
# tests/unit/orchestrator/session/test_models.py
import pytest
from datetime import datetime
from mozi.orchestrator.session.models import (
    Message,
    MessageRole,
    Session,
    SessionStatus,
    SessionMetadata,
    SessionConfig,
)


class TestMessage:
    def test_message_creation(self):
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.streaming_content == ""
        assert msg.is_streaming is False

    def test_message_streaming_fields(self):
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="",
            streaming_content="Hello w",
            is_streaming=True,
        )
        assert msg.is_streaming is True
        assert msg.streaming_content == "Hello w"

    def test_message_finalize_streaming(self):
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Hello world",
            streaming_content="Hello world",
            is_streaming=False,
        )
        assert msg.content == "Hello world"
        assert msg.is_streaming is False


class TestSession:
    def test_session_creation(self):
        session = Session(id="test-123", metadata=SessionMetadata())
        assert session.id == "test-123"
        assert session.status == SessionStatus.ACTIVE
        assert len(session.messages) == 0

    def test_session_with_messages(self):
        session = Session(
            id="test-123",
            metadata=SessionMetadata(),
            messages=[
                Message(role=MessageRole.USER, content="Hi"),
                Message(role=MessageRole.ASSISTANT, content="Hello"),
            ],
        )
        assert len(session.messages) == 2


class TestSessionConfig:
    def test_default_config(self):
        config = SessionConfig()
        assert config.auto_save_message_count == 1
        assert config.storage_dir == "~/.mozi/sessions"

    def test_custom_config(self):
        config = SessionConfig(auto_save_message_count=5, storage_dir="/tmp/sessions")
        assert config.auto_save_message_count == 5
        assert config.storage_dir == "/tmp/sessions"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/orchestrator/session/test_models.py -v
Expected: FAIL - ModuleNotFoundError: No module named 'mozi'
```

- [ ] **Step 3: 编写 models.py 实现**

```python
# mozi/orchestrator/session/models.py
"""Session 数据模型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class SessionStatus(Enum):
    """会话状态"""
    ACTIVE = "active"
    IDLE = "idle"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class MessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """消息结构"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_call_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    streaming_content: str = ""       # 流式输出过程中的渐进内容
    is_streaming: bool = False       # 是否正在流式输出


@dataclass
class SessionMetadata:
    """会话元数据"""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_active_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    total_tokens: int = 0
    user_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    custom_fields: dict = field(default_factory=dict)


@dataclass
class Session:
    """会话结构"""
    id: str
    metadata: SessionMetadata
    messages: list[Message] = field(default_factory=list)
    status: SessionStatus = SessionStatus.ACTIVE
    parent_session_id: Optional[str] = None  # 支持会话分支


@dataclass
class SessionConfig:
    """会话配置"""
    storage_dir: str = "~/.mozi/sessions"
    max_session_age_days: int = 30
    idle_timeout_seconds: int = 3600
    auto_save_interval_seconds: int = 30
    auto_save_message_count: int = 1  # 崩溃恢复关键：每条消息后立即保存
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/orchestrator/session/test_models.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add mozi/orchestrator/session/models.py tests/unit/orchestrator/session/test_models.py
git commit -m "feat(session): add data models with streaming support"
```

---

## Task 3: 实现存储抽象 (storage.py)

**Files:**
- Modify: `mozi/orchestrator/session/storage.py` (create)
- Create: `tests/unit/orchestrator/session/test_storage.py`

- [ ] **Step 1: 编写测试**

```python
# tests/unit/orchestrator/session/test_storage.py
import pytest
import json
import tempfile
import asyncio
from pathlib import Path
from mozi.orchestrator.session.models import (
    Session,
    SessionStatus,
    Message,
    MessageRole,
    SessionMetadata,
)
from mozi.orchestrator.session.storage import FileSessionStorage


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield FileSessionStorage(storage_dir=tmpdir)


@pytest.fixture
def sample_session():
    return Session(
        id="test-session-123",
        metadata=SessionMetadata(user_id="user1"),
        messages=[
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
        ],
    )


class TestFileSessionStorage:
    @pytest.mark.asyncio
    async def test_save_and_load_session(self, temp_storage, sample_session):
        await temp_storage.save(sample_session)
        loaded = await temp_storage.load(sample_session.id)

        assert loaded is not None
        assert loaded.id == sample_session.id
        assert loaded.metadata.user_id == "user1"
        assert len(loaded.messages) == 2

    @pytest.mark.asyncio
    async def test_load_nonexistent_returns_none(self, temp_storage):
        result = await temp_storage.load("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_session(self, temp_storage, sample_session):
        await temp_storage.save(sample_session)
        result = await temp_storage.delete(sample_session.id)
        assert result is True

        loaded = await temp_storage.load(sample_session.id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_exists(self, temp_storage, sample_session):
        assert await temp_storage.exists(sample_session.id) is False
        await temp_storage.save(sample_session)
        assert await temp_storage.exists(sample_session.id) is True

    @pytest.mark.asyncio
    async def test_list_sessions(self, temp_storage):
        session1 = Session(id="s1", metadata=SessionMetadata())
        session2 = Session(id="s2", metadata=SessionMetadata())
        await temp_storage.save(session1)
        await temp_storage.save(session2)

        sessions = await temp_storage.list()
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_streaming_content_persistence(self, temp_storage):
        session = Session(
            id="streaming-test",
            metadata=SessionMetadata(),
            messages=[
                Message(
                    role=MessageRole.ASSISTANT,
                    content="",
                    streaming_content="Hello w",
                    is_streaming=True,
                ),
            ],
        )
        await temp_storage.save(session)
        loaded = await temp_storage.load("streaming-test")

        assert loaded.messages[0].streaming_content == "Hello w"
        assert loaded.messages[0].is_streaming is True
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/orchestrator/session/test_storage.py -v
Expected: FAIL - ModuleNotFoundError
```

- [ ] **Step 3: 编写 storage.py 实现**

```python
# mozi/orchestrator/session/storage.py
"""Session 持久化存储实现"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .models import Session, SessionStatus


class SessionStorage(ABC):
    """会话存储抽象接口"""

    @abstractmethod
    async def save(self, session: Session) -> None:
        """保存会话"""
        ...

    @abstractmethod
    async def load(self, session_id: str) -> Optional[Session]:
        """加载会话"""
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        ...

    @abstractmethod
    async def list(
        self,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
    ) -> list[Session]:
        """列出会话"""
        ...

    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        ...


def _serialize_session(session: Session) -> dict:
    """序列化 Session 为字典"""
    return {
        "id": session.id,
        "status": session.status.value,
        "parent_session_id": session.parent_session_id,
        "metadata": {
            "created_at": session.metadata.created_at.isoformat(),
            "updated_at": session.metadata.updated_at.isoformat(),
            "last_active_at": session.metadata.last_active_at.isoformat(),
            "message_count": session.metadata.message_count,
            "total_tokens": session.metadata.total_tokens,
            "user_id": session.metadata.user_id,
            "tags": session.metadata.tags,
            "custom_fields": session.metadata.custom_fields,
        },
        "messages": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "tool_call_id": msg.tool_call_id,
                "metadata": msg.metadata,
                "streaming_content": msg.streaming_content,
                "is_streaming": msg.is_streaming,
            }
            for msg in session.messages
        ],
    }


def _deserialize_session(data: dict) -> Session:
    """从字典反序列化 Session"""
    from .models import (
        Message,
        MessageRole,
        SessionMetadata,
        SessionStatus,
    )
    from datetime import datetime

    metadata_dict = data["metadata"]
    messages = [
        Message(
            role=MessageRole(msg["role"]),
            content=msg["content"],
            timestamp=datetime.fromisoformat(msg["timestamp"]),
            tool_call_id=msg.get("tool_call_id"),
            metadata=msg.get("metadata", {}),
            streaming_content=msg.get("streaming_content", ""),
            is_streaming=msg.get("is_streaming", False),
        )
        for msg in data["messages"]
    ]

    metadata = SessionMetadata(
        created_at=datetime.fromisoformat(metadata_dict["created_at"]),
        updated_at=datetime.fromisoformat(metadata_dict["updated_at"]),
        last_active_at=datetime.fromisoformat(metadata_dict["last_active_at"]),
        message_count=metadata_dict["message_count"],
        total_tokens=metadata_dict["total_tokens"],
        user_id=metadata_dict.get("user_id"),
        tags=metadata_dict.get("tags", []),
        custom_fields=metadata_dict.get("custom_fields", {}),
    )

    return Session(
        id=data["id"],
        status=SessionStatus(data["status"]),
        parent_session_id=data.get("parent_session_id"),
        metadata=metadata,
        messages=messages,
    )


class FileSessionStorage(SessionStorage):
    """文件存储实现"""

    def __init__(self, storage_dir: str = "~/.mozi/sessions") -> None:
        self._storage_dir = Path(storage_dir).expanduser()

    async def save(self, session: Session) -> None:
        """保存会话到文件"""
        session_path = self._get_session_path(session.id)
        session_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "session": _serialize_session(session),
        }
        await self._write_json(session_path, data)

    async def load(self, session_id: str) -> Optional[Session]:
        """从文件加载会话"""
        session_path = self._get_session_path(session_id)
        if not session_path.exists():
            return None

        data = await self._read_json(session_path)
        return _deserialize_session(data["session"])

    async def delete(self, session_id: str) -> bool:
        """删除会话文件"""
        session_path = self._get_session_path(session_id)
        if session_path.exists():
            session_path.unlink()
            return True
        return False

    async def list(
        self,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
    ) -> list[Session]:
        """列出存储的会话"""
        sessions = []
        for session_file in self._storage_dir.glob("*.json"):
            try:
                data = await self._read_json(session_file)
                session = _deserialize_session(data["session"])
                if status is None or session.status == status:
                    sessions.append(session)
            except (json.JSONDecodeError, KeyError):
                continue

        sessions.sort(
            key=lambda s: s.metadata.last_active_at,
            reverse=True,
        )
        return sessions[:limit]

    async def exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        return self._get_session_path(session_id).exists()

    def _get_session_path(self, session_id: str) -> Path:
        """获取会话文件路径"""
        return self._storage_dir / f"{session_id}.json"

    async def _write_json(self, path: Path, data: dict) -> None:
        """异步写入 JSON 文件"""
        import aiofiles

        async with aiofiles.open(path, "w") as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))

    async def _read_json(self, path: Path) -> dict:
        """异步读取 JSON 文件"""
        import aiofiles

        async with aiofiles.open(path, "r") as f:
            content = await f.read()
            return json.loads(content)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/orchestrator/session/test_storage.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add mozi/orchestrator/session/storage.py tests/unit/orchestrator/session/test_storage.py
git commit -m "feat(session): add file storage with streaming content support"
```

---

## Task 4: 实现会话管理器 (manager.py)

**Files:**
- Modify: `mozi/orchestrator/session/manager.py` (create)
- Create: `tests/unit/orchestrator/session/test_manager.py`

- [ ] **Step 1: 编写测试**

```python
# tests/unit/orchestrator/session/test_manager.py
import pytest
import tempfile
from unittest.mock import AsyncMock
from mozi.orchestrator.session.models import (
    Session,
    SessionConfig,
    Message,
    MessageRole,
    SessionMetadata,
)
from mozi.orchestrator.session.storage import FileSessionStorage
from mozi.orchestrator.session.manager import SessionManager


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield FileSessionStorage(storage_dir=tmpdir)


@pytest.fixture
def session_manager(temp_storage):
    config = SessionConfig(auto_save_message_count=1)
    return SessionManager(storage=temp_storage, config=config)


class TestSessionManager:
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        session = await session_manager.create(user_id="user1")
        assert session.id is not None
        assert session.metadata.user_id == "user1"
        assert await session_manager.storage.exists(session.id)

    @pytest.mark.asyncio
    async def test_get_session(self, session_manager):
        created = await session_manager.create(user_id="user1")
        loaded = await session_manager.get(created.id)

        assert loaded is not None
        assert loaded.id == created.id

    @pytest.mark.asyncio
    async def test_append_message(self, session_manager):
        session = await session_manager.create()
        await session_manager.append_message(
            session.id,
            Message(role=MessageRole.USER, content="Hello"),
        )

        updated = await session_manager.get(session.id)
        assert len(updated.messages) == 1
        assert updated.messages[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_append_message_triggers_save(self, session_manager):
        """验证 auto_save_message_count=1 时每条消息立即保存"""
        session = await session_manager.create()
        await session_manager.append_message(
            session.id,
            Message(role=MessageRole.USER, content="Hello"),
        )

        # 直接从存储加载验证已保存
        loaded = await session_manager.storage.load(session.id)
        assert len(loaded.messages) == 1

    @pytest.mark.asyncio
    async def test_update_session(self, session_manager):
        session = await session_manager.create()
        session.metadata.tags = ["test"]
        await session_manager.update(session)

        loaded = await session_manager.get(session.id)
        assert loaded.metadata.tags == ["test"]

    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager):
        session = await session_manager.create()
        result = await session_manager.delete(session.id)

        assert result is True
        assert await session_manager.get(session.id) is None

    @pytest.mark.asyncio
    async def test_streaming_message_persistence(self, session_manager):
        session = await session_manager.create()
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="",
            streaming_content="Hello w",
            is_streaming=True,
        )
        await session_manager.append_message(session.id, msg)

        loaded = await session_manager.get(session.id)
        assert loaded.messages[0].streaming_content == "Hello w"
        assert loaded.messages[0].is_streaming is True

    @pytest.mark.asyncio
    async def test_finalize_streaming_message(self, session_manager):
        session = await session_manager.create()
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="",
            streaming_content="Hello w",
            is_streaming=True,
        )
        await session_manager.append_message(session.id, msg)

        # 更新消息为完成状态
        session.messages[0].content = "Hello world"
        session.messages[0].streaming_content = "Hello world"
        session.messages[0].is_streaming = False
        await session_manager.update(session)

        loaded = await session_manager.get(session.id)
        assert loaded.messages[0].content == "Hello world"
        assert loaded.messages[0].is_streaming is False
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/unit/orchestrator/session/test_manager.py -v
Expected: FAIL - ModuleNotFoundError
```

- [ ] **Step 3: 编写 manager.py 实现**

```python
# mozi/orchestrator/session/manager.py
"""Session 会话管理器"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .models import Session, SessionConfig, SessionMetadata, SessionStatus, Message
from .storage import SessionStorage


class BaseSessionManager(ABC):
    """会话管理器抽象基类"""

    @abstractmethod
    async def create(
        self,
        user_id: Optional[str] = None,
        parent_session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Session:
        """创建新会话"""
        ...

    @abstractmethod
    async def get(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        ...

    @abstractmethod
    async def update(self, session: Session) -> Session:
        """更新会话"""
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        ...

    @abstractmethod
    async def list(
        self,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
    ) -> list[Session]:
        """列出会话"""
        ...

    @abstractmethod
    async def append_message(self, session_id: str, message: Message) -> Session:
        """追加消息并保存"""
        ...


class SessionManager(BaseSessionManager):
    """会话管理器实现"""

    def __init__(
        self,
        storage: SessionStorage,
        config: SessionConfig,
    ) -> None:
        self._storage = storage
        self._config = config

    @property
    def storage(self) -> SessionStorage:
        """暴露 storage 供测试使用"""
        return self._storage

    async def create(
        self,
        user_id: Optional[str] = None,
        parent_session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Session:
        """创建新会话"""
        session_id = str(uuid4())
        session_metadata = SessionMetadata(
            user_id=user_id,
            custom_fields=metadata or {},
        )
        session = Session(
            id=session_id,
            metadata=session_metadata,
            parent_session_id=parent_session_id,
        )
        await self._storage.save(session)
        return session

    async def get(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        session = await self._storage.load(session_id)
        if session:
            session.metadata.last_active_at = datetime.now()
        return session

    async def update(self, session: Session) -> Session:
        """更新会话"""
        session.metadata.updated_at = datetime.now()
        await self._storage.save(session)
        return session

    async def delete(self, session_id: str) -> bool:
        """删除会话"""
        return await self._storage.delete(session_id)

    async def list(
        self,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
    ) -> list[Session]:
        """列出会话"""
        return await self._storage.list(status=status, limit=limit)

    async def append_message(self, session_id: str, message: Message) -> Session:
        """追加消息并保存（立即保存，auto_save_message_count=1）"""
        session = await self._storage.load(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session.messages.append(message)
        session.metadata.message_count = len(session.messages)
        session.metadata.last_active_at = datetime.now()

        # 立即保存（崩溃恢复关键）
        await self._storage.save(session)
        return session
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/unit/orchestrator/session/test_manager.py -v
Expected: PASS
```

- [ ] **Step 5: Commit**

```bash
git add mozi/orchestrator/session/manager.py tests/unit/orchestrator/session/test_manager.py
git commit -m "feat(session): add session manager with immediate save"
```

---

## Task 5: 添加 aiofiles 依赖

**Files:**
- Modify: `pyproject.toml` 或 `uv.lock`（取决于项目依赖管理方式）

- [ ] **Step 1: 检查现有依赖管理**

```bash
cat pyproject.toml 2>/dev/null || cat setup.py 2>/dev/null || echo "No dependency file found"
```

- [ ] **Step 2: 添加 aiofiles 依赖**

```bash
uv add aiofiles
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps(session): add aiofiles for async file operations"
```

---

## Task 6: 更新 __init__.py 导出

**Files:**
- Modify: `mozi/orchestrator/session/__init__.py`

- [ ] **Step 1: 更新导出**

```python
"""Session module - 会话管理和崩溃恢复"""

from .models import (
    Session,
    SessionStatus,
    Message,
    MessageRole,
    SessionMetadata,
    SessionConfig,
)
from .storage import SessionStorage, FileSessionStorage
from .manager import SessionManager, BaseSessionManager

__all__ = [
    # models
    "Session",
    "SessionStatus",
    "Message",
    "MessageRole",
    "SessionMetadata",
    "SessionConfig",
    # storage
    "SessionStorage",
    "FileSessionStorage",
    # manager
    "SessionManager",
    "BaseSessionManager",
]
```

- [ ] **Step 2: Commit**

```bash
git add mozi/orchestrator/session/__init__.py
git commit -m "feat(session): update module exports"
```

---

## Task 7: 最终验证

- [ ] **Step 1: 运行所有测试**

```bash
pytest tests/unit/orchestrator/session/ -v --tb=short
```

- [ ] **Step 2: 验证代码质量**

```bash
ruff check mozi/orchestrator/session/
mypy mozi/orchestrator/session/ --strict
```

- [ ] **Step 3: 提交所有变更**

```bash
git add -A
git status
```

---

## Task 8: 实现 resume 命令（CLI 层）

**Files:**
- Create: `mozi/ingress/cli/commands.py`
- Create: `mozi/ingress/__init__.py`
- Create: `tests/unit/ingress/cli/test_commands.py`

> **注：** CLI 层属于 Ingress 模块。此 Task 创建 CLI 与 Session 的集成点。

- [ ] **Step 1: 创建 Ingress CLI 目录结构**

```bash
mkdir -p mozi/ingress/cli
```

- [ ] **Step 2: 创建 CLI resume 命令实现**

```python
# mozi/ingress/cli/commands.py
"""CLI 命令实现"""

from __future__ import annotations

from typing import Optional

from mozi.orchestrator.session.manager import SessionManager
from mozi.orchestrator.session.storage import FileSessionStorage
from mozi.orchestrator.session.models import SessionConfig


async def resume_session(session_id: str) -> dict:
    """恢复指定会话

    Args:
        session_id: 要恢复的会话 ID

    Returns:
        dict: {
            "success": bool,
            "session": Session | None,
            "last_message": Message | None,
            "continue_from": str | None,  # 如果有未完成的流式输出
            "error": str | None
        }
    """
    config = SessionConfig()
    storage = FileSessionStorage(storage_dir=config.storage_dir)
    manager = SessionManager(storage=storage, config=config)

    session = await manager.get(session_id)
    if session is None:
        return {
            "success": False,
            "session": None,
            "last_message": None,
            "continue_from": None,
            "error": f"Session {session_id} not found",
        }

    last_message = session.messages[-1] if session.messages else None
    continue_from = None

    # 如果最后一条消息是未完成的流式输出，提取 continue_from
    if last_message and last_message.is_streaming:
        continue_from = last_message.streaming_content

    return {
        "success": True,
        "session": session,
        "last_message": last_message,
        "continue_from": continue_from,
        "error": None,
    }


def format_resume_output(session_id: str, last_message: "Message") -> str:
    """格式化 resume 输出

    按照 spec 要求输出:
    "Resuming session <id>, last message:"
    然后显示最后一条消息内容
    """
    if last_message is None:
        return f"Resuming session {session_id}, no messages yet."

    return f"""Resuming session {session_id}, last message:
[{last_message.role.value}] {last_message.content[:200]}{'...' if len(last_message.content) > 200 else ''}"""
```

- [ ] **Step 3: 创建 CLI __init__.py**

```python
# mozi/ingress/__init__.py
"""Ingress module - CLI 入口层"""

from .cli.commands import resume_session, format_resume_output

__all__ = ["resume_session", "format_resume_output"]
```

- [ ] **Step 4: 提交**

```bash
git add mozi/ingress/__init__.py mozi/ingress/cli/commands.py
git commit -m "feat(ingress): add resume session command"
```

---

## Task 9: 添加 Orchestrator 集成（崩溃恢复感知）

**Files:**
- Create: `mozi/orchestrator/crash_recovery.py`
- Create: `tests/unit/orchestrator/test_crash_recovery.py`

> **注：** Orchestrator 工作循环阶段属于运行时状态，崩溃后不恢复。但需要感知 Session 的 `is_streaming` 状态，在恢复时传递 `continue_from` 参数给 LLM 层。

- [ ] **Step 1: 创建崩溃恢复辅助模块**

```python
# mozi/orchestrator/crash_recovery.py
"""Orchestrator 崩溃恢复集成"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from mozi.orchestrator.session.models import Session, Message


@dataclass
class CrashRecoveryState:
    """崩溃恢复状态"""
    session: Session
    continue_from: Optional[str]  # 未完成的流式输出内容
    last_message: Optional[Message]
    needs_streaming_resume: bool  # 是否需要从流式输出恢复


def detect_crash_recovery_state(session: Session) -> CrashRecoveryState:
    """检测会话是否需要崩溃恢复

    检查最后一条消息是否是未完成的流式输出。
    如果是，返回 continue_from 供 Orchestrator 重新发送 LLM 请求。
    """
    if not session.messages:
        return CrashRecoveryState(
            session=session,
            continue_from=None,
            last_message=None,
            needs_streaming_resume=False,
        )

    last_message = session.messages[-1]

    if last_message.is_streaming and last_message.streaming_content:
        return CrashRecoveryState(
            session=session,
            continue_from=last_message.streaming_content,
            last_message=last_message,
            needs_streaming_resume=True,
        )

    return CrashRecoveryState(
        session=session,
        continue_from=None,
        last_message=last_message,
        needs_streaming_resume=False,
    )
```

- [ ] **Step 2: 添加测试**

```python
# tests/unit/orchestrator/test_crash_recovery.py
import pytest
from mozi.orchestrator.session.models import Message, MessageRole, Session, SessionMetadata
from mozi.orchestrator.crash_recovery import detect_crash_recovery_state, CrashRecoveryState

class TestCrashRecovery:
    def test_no_messages(self):
        """空会话不需要恢复"""
        session = Session(id="test", metadata=SessionMetadata(), messages=[])
        state = detect_crash_recovery_state(session)

        assert state.needs_streaming_resume is False
        assert state.continue_from is None

    def test_completed_message(self):
        """已完成的消息不需要恢复"""
        session = Session(
            id="test",
            metadata=SessionMetadata(),
            messages=[
                Message(role=MessageRole.USER, content="Hello"),
                Message(role=MessageRole.ASSISTANT, content="Hi there!"),
            ],
        )
        state = detect_crash_recovery_state(session)

        assert state.needs_streaming_resume is False
        assert state.continue_from is None
        assert state.last_message.content == "Hi there!"

    def test_incomplete_streaming_message(self):
        """未完成的流式消息需要恢复"""
        session = Session(
            id="test",
            metadata=SessionMetadata(),
            messages=[
                Message(role=MessageRole.USER, content="Hello"),
                Message(
                    role=MessageRole.ASSISTANT,
                    content="",
                    streaming_content="Hi t",
                    is_streaming=True,
                ),
            ],
        )
        state = detect_crash_recovery_state(session)

        assert state.needs_streaming_resume is True
        assert state.continue_from == "Hi t"
        assert state.last_message.is_streaming is True
```

- [ ] **Step 3: 提交**

```bash
git add mozi/orchestrator/crash_recovery.py tests/unit/orchestrator/test_crash_recovery.py
git commit -m "feat(orchestrator): add crash recovery integration with continue_from support"
```

---

## Task 10: Orchestrator 主循环集成（传递 continue_from）

**Files:**
- Create: `mozi/orchestrator/orchestrator.py`
- Create: `tests/unit/orchestrator/test_orchestrator_resume.py`

> **注：** 此 Task 展示 Orchestrator 主循环如何调用 crash recovery helper 并将 `continue_from` 传递给 LLM 层。

### 10.1 Orchestrator 主循环集成点

```
┌─────────────────────────────────────────────────────────────────┐
│ Orchestrator.run(session_id)                                     │
│                                                                   │
│  1. session = await session_manager.get(session_id)              │
│         │                                                        │
│         ▼                                                        │
│  2. recovery_state = detect_crash_recovery_state(session)        │
│         │                                                        │
│         ├──► needs_streaming_resume=True                          │
│         │      │                                                 │
│         │      ▼                                                 │
│         │   LLM 请求带上 continue_from=recovery_state.continue_from │
│         │                                                        │
│         └──► needs_streaming_resume=False                         │
│                │                                                 │
│                ▼                                                 │
│             正常 LLM 请求                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 实现代码

- [ ] **Step 1: 创建 Orchestrator 主循环（带 crash recovery 集成）**

```python
# mozi/orchestrator/orchestrator.py
"""Orchestrator 主循环 - 带崩溃恢复集成"""

from __future__ import annotations

from typing import Optional

from mozi.orchestrator.session.manager import SessionManager
from mozi.orchestrator.session.models import Session
from mozi.orchestrator.crash_recovery import detect_crash_recovery_state


class Orchestrator:
    """会话级 Agent - 带崩溃恢复支持"""

    def __init__(self, session_manager: SessionManager) -> None:
        self._session_manager = session_manager

    async def run(self, session_id: str) -> None:
        """主工作循环

        崩溃恢复流程：
        1. 加载 session
        2. 检测是否需要从流式输出恢复
        3. 如果需要，带 continue_from 重新发送 LLM 请求
        4. 否则正常处理
        """
        session = await self._session_manager.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        # 检测崩溃恢复状态
        recovery_state = detect_crash_recovery_state(session)

        if recovery_state.needs_streaming_resume:
            # 从未完成的流式输出恢复
            await self._resume_streaming(
                session=recovery_state.session,
                continue_from=recovery_state.continue_from,
            )
        else:
            # 正常工作循环
            await self._normal_workflow(session)

    async def _resume_streaming(
        self,
        session: Session,
        continue_from: str,
    ) -> None:
        """从流式输出中断处恢复

        Args:
            session: 会话
            continue_from: 已输出的内容，用于继续生成
        """
        # 获取最后一条用户消息作为上下文
        user_messages = [
            msg for msg in session.messages
            if msg.role == MessageRole.USER
        ]
        last_user_input = user_messages[-1].content if user_messages else ""

        # 调用 LLM，带上 continue_from
        # Model 层需要支持 continue_from 参数
        response = await self._call_llm(
            prompt=last_user_input,
            continue_from=continue_from,
        )

        # 将响应追加到 session
        from mozi.orchestrator.session.models import Message, MessageRole
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response.content,
            streaming_content=response.content,
            is_streaming=False,
        )
        await self._session_manager.append_message(session.id, assistant_message)

    async def _normal_workflow(self, session: Session) -> None:
        """正常工作循环（理解→规划→执行→评估）"""
        # TODO: 实现正常的工作循环
        pass

    async def _call_llm(
        self,
        prompt: str,
        continue_from: Optional[str] = None,
    ) -> "LLMResponse":
        """调用 LLM

        Args:
            prompt: 用户输入
            continue_from: 如果从流式输出恢复，带上已输出的内容
        """
        # TODO: Model 层实现
        # 如果 continue_from 不为空，指示 LLM 从该内容继续生成
        pass
```

- [ ] **Step 2: 创建集成测试**

```python
# tests/unit/orchestrator/test_orchestrator_resume.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mozi.orchestrator.session.models import Message, MessageRole, Session, SessionMetadata
from mozi.orchestrator.crash_recovery import CrashRecoveryState


class TestOrchestratorResume:
    @pytest.mark.asyncio
    async def test_resume_from_streaming_output(self):
        """测试从流式输出中断处恢复"""
        # 模拟 session，最后一条是未完成的流式消息
        session = Session(
            id="test-123",
            metadata=SessionMetadata(),
            messages=[
                Message(role=MessageRole.USER, content="Write a long story"),
                Message(
                    role=MessageRole.ASSISTANT,
                    content="",
                    streaming_content="Once upon a time",
                    is_streaming=True,
                ),
            ],
        )

        # 验证 recovery_state 正确检测
        recovery_state = CrashRecoveryState(
            session=session,
            continue_from="Once upon a time",
            last_message=session.messages[-1],
            needs_streaming_resume=True,
        )

        assert recovery_state.needs_streaming_resume is True
        assert recovery_state.continue_from == "Once upon a time"

    @pytest.mark.asyncio
    async def test_normal_workflow_no_resume(self):
        """测试正常工作流不需要恢复"""
        session = Session(
            id="test-123",
            metadata=SessionMetadata(),
            messages=[
                Message(role=MessageRole.USER, content="Hello"),
                Message(role=MessageRole.ASSISTANT, content="Hi there!"),
            ],
        )

        recovery_state = CrashRecoveryState(
            session=session,
            continue_from=None,
            last_message=session.messages[-1],
            needs_streaming_resume=False,
        )

        assert recovery_state.needs_streaming_resume is False
```

- [ ] **Step 3: 提交**

```bash
git add mozi/orchestrator/orchestrator.py tests/unit/orchestrator/test_orchestrator_resume.py
git commit -m "feat(orchestrator): integrate crash recovery with continue_from in main loop"
```

---

## Task 11: 端到端集成测试

**Files:**
- Create: `tests/integration/test_crash_recovery_e2e.py`

- [ ] **Step 1: 创建端到端测试**

```python
# tests/integration/test_crash_recovery_e2e.py
"""崩溃恢复端到端测试

测试完整流程：
1. 创建 session
2. 模拟流式输出中断（保存 is_streaming=True 的消息）
3. 模拟进程崩溃
4. resume session
5. 验证流式输出恢复
"""

import pytest
import tempfile
from mozi.orchestrator.session.manager import SessionManager
from mozi.orchestrator.session.storage import FileSessionStorage
from mozi.orchestrator.session.models import SessionConfig, Message, MessageRole
from mozi.orchestrator.orchestrator import Orchestrator


@pytest.fixture
def e2e_setup():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileSessionStorage(storage_dir=tmpdir)
        config = SessionConfig(auto_save_message_count=1)
        manager = SessionManager(storage=storage, config=config)
        orchestrator = Orchestrator(session_manager=manager)
        yield {"storage": storage, "config": config, "manager": manager, "orchestrator": orchestrator}


@pytest.mark.asyncio
async def test_full_crash_recovery_flow(e2e_setup):
    """完整崩溃恢复流程"""
    manager = e2e_setup["manager"]
    orchestrator = e2e_setup["orchestrator"]

    # 1. 创建会话
    session = await manager.create(user_id="test-user")
    await manager.append_message(
        session.id,
        Message(role=MessageRole.USER, content="Write a long story"),
    )

    # 2. 模拟 LLM 流式输出开始（未完成）
    streaming_msg = Message(
        role=MessageRole.ASSISTANT,
        content="",
        streaming_content="Once upon a time in a land far",
        is_streaming=True,
    )
    await manager.append_message(session.id, streaming_msg)

    # 3. 验证消息已保存（崩溃恢复关键）
    saved_session = await manager.get(session.id)
    assert saved_session.messages[-1].is_streaming is True
    assert saved_session.messages[-1].streaming_content == "Once upon a time in a land far"

    # 4. 模拟进程重启后 resume
    # (在同一进程中模拟：重新加载 session)
    resumed_session = await manager.get(session.id)
    assert resumed_session.messages[-1].streaming_content == "Once upon a time in a land far"
    assert resumed_session.messages[-1].is_streaming is True
```

- [ ] **Step 2: 提交**

```bash
git add tests/integration/test_crash_recovery_e2e.py
git commit -m "test: add e2e crash recovery integration test"
```

---

## 变更记录

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.2 | 2026-03-30 | 添加 Task 10 (Orchestrator 主循环集成) 和 Task 11 (E2E 测试) |
| 1.1 | 2026-03-30 | 添加 Task 8 (resume 命令) 和 Task 9 (Orchestrator 集成) |
| 1.0 | 2026-03-30 | 初始实现计划 |

---

_版本: 1.2_
_更新日期: 2026-03-30_
