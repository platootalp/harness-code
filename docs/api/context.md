# Context API

## Overview

The Context module manages conversation context and message windowing.

## ContextBuilder

### Methods

#### `build(session_id: str) -> ConversationContext`

Builds context for a session.

**Parameters:**
- `session_id` (str): Session identifier

**Returns:**
- `ConversationContext`: The built context

#### `add_message(message: Message) -> None`

Adds a message to the context.

**Parameters:**
- `message` (Message): Message to add

## ContextWindow

### Methods

#### `get_messages(limit: int | None = None) -> list[Message]`

Gets messages within the window.

**Parameters:**
- `limit` (int, optional): Maximum number of messages

**Returns:**
- `list[Message]`: List of messages

#### `get_token_count() -> int`

Gets total token count.

**Returns:**
- `int`: Token count

## ContextOffloader

Handles offloading context to external storage.

### Methods

#### `offload(messages: list[Message]) -> str`

Offloads messages and returns reference ID.

**Parameters:**
- `messages` (list[Message]): Messages to offload

**Returns:**
- `str`: Reference ID for retrieval

#### `retrieve(reference_id: str) -> list[Message]`

Retrieves offloaded messages.

**Parameters:**
- `reference_id` (str): Reference ID

**Returns:**
- `list[Message]`: Retrieved messages

## Context Models

### ConversationContext

| Attribute | Type | Description |
|-----------|------|-------------|
| `session_id` | `str` | Session identifier |
| `messages` | `list[Message]` | Current messages |
| `token_count` | `int` | Total tokens |
| `is_truncated` | `bool` | Whether context was truncated |

## Usage Example

```python
from mozi.context import ContextBuilder

builder = ContextBuilder()
context = await builder.build(session_id="session-123")
messages = context.get_messages(limit=10)
```
