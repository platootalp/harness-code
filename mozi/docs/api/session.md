# Session API

## Overview

The Session module manages conversation sessions for the Mozi AI coding agent.

## SessionManager

### Methods

#### `create_session(working_dir: str, user_id: str | None = None, name: str | None = None) -> Session`

Creates a new session.

**Parameters:**
- `working_dir` (str): Working directory for the session
- `user_id` (str, optional): User identifier
- `name` (str, optional): Session name

**Returns:**
- `Session`: The created session object

#### `get_session(session_id: str) -> Session | None`

Retrieves a session by ID.

**Parameters:**
- `session_id` (str): Session identifier

**Returns:**
- `Session | None`: The session if found, None otherwise

#### `delete_session(session_id: str) -> bool`

Deletes a session.

**Parameters:**
- `session_id` (str): Session identifier

**Returns:**
- `bool`: True if deleted, False if not found

## Session Model

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Unique session identifier |
| `name` | `str` | Session name |
| `user_id` | `str | None` | User identifier |
| `working_dir` | `str` | Working directory |
| `status` | `SessionStatus` | Current session status |
| `metadata` | `dict[str, Any]` | Additional metadata |
| `tags` | `list[str]` | Session tags |
| `created_at` | `datetime` | Creation timestamp |
| `updated_at` | `datetime` | Last update timestamp |

### SessionStatus Enum

- `ACTIVE`: Session is active
- `IDLE`: Session is idle
- `COMPLETED`: Session is completed
- `ABANDONED`: Session was abandoned

## Usage Example

```python
from mozi.session import SessionManager

manager = SessionManager()
session = await manager.create_session(
    working_dir="/path/to/project",
    user_id="user123",
    name="My Session"
)
```
