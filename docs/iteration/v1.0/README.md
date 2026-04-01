# Mozi v1.0.0

> **Release Date**: 2026-04-01
> **Status**: Released

## Overview

Mozi v1.0.0 is the first major release of the Mozi AI Coding Agent. This release delivers a complete four-layer architecture with intelligent task routing, session management, memory systems, and a secure tools framework.

## Major Features

### Orchestrator-Worker Architecture
- ReAct loop engine for intelligent task decomposition
- Complexity-based routing (Explorer/Planner/Coder workers)
- State management with persistent storage

### Session Management
- SQLite-based persistent session storage
- Session lifecycle management
- Concurrency control

### Memory System
- Short-term context with sliding window
- Long-term memory with vector store support
- Semantic retrieval

### Tools Framework
- Secure tool execution with permission levels
- Built-in file, bash, grep, and glob tools
- Path validation and dangerous function detection

### Model Abstraction
- Multi-model support (OpenAI, Anthropic)
- Circuit breaker and retry strategies
- Error classification

## What's New

| Feature | Description |
|---------|-------------|
| CLI/REPL | Interactive command-line interface |
| Session Persistence | SQLite-based storage |
| Context Window | Sliding window for message management |
| Memory Stores | Short-term and long-term memory |
| Tool Security | Permission levels 0-4 |
| Quality Checker | Code syntax, style, and security validation |

## Installation

```bash
# Using uv
uv sync

# Using pip
pip install -e .
```

## Upgrade from v0.1.0

This is the first stable release. See [CHANGELOG.md](../../CHANGELOG.md) for detailed changes.

## Documentation

- [API Documentation](../../api/)
- [Architecture Design](../../foundation/architecture/)
- [Contributing Guide](../../CONTRIBUTING.md)

## Known Issues

None.

## Breaking Changes

None (initial stable release).

## Deprecations

None.

## Security

- All tool executions are sandboxed with permission levels
- Path validation prevents directory traversal
- Dangerous function detection blocks unsafe operations

## Contributors

This release was built by the Mozi development team.

## License

MIT License
