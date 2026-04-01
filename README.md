# Mozi AI Coding Agent

Mozi is an AI Coding Agent designed to help developers build software more efficiently. It uses a four-layer architecture (Ingress → Orchestrator → Capabilities → Infrastructure) with intelligent task routing based on complexity.

## Features

- **Intelligent Task Routing**: Automatically routes tasks to appropriate workers based on complexity
  - SIMPLE (0-40): Explorer Worker for exploratory tasks
  - MEDIUM (41-70): Planner Worker for planning tasks
  - COMPLEX (71-100): Coder Worker for complex coding tasks

- **Memory Management**: Short-term and long-term memory for context preservation
- **Tool Framework**: Secure tool execution with permission levels (0-4)
- **Session Management**: Persistent session state with SQLite storage
- **Model Abstraction**: Multi-model support (OpenAI, Anthropic) with circuit breakers and retry logic

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         1. Ingress Layer                         │
│                    CLI (REPL) │  IDE Plugin  │  REST API        │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                         2. Session Layer                         │
│              Session Manager │  Concurrency Control │  Auth      │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                         3. Orchestrator Layer                     │
│  ┌─────────────────┐    ┌─────────────────────────────────────┐  │
│  │  Orchestrator   │    │  Worker Pool                        │  │
│  │  - ReAct Loop   │───▶│  Explorer │ Planner │ Coder │ QA  │  │
│  │  - State Store  │    │                                  │  │
│  └─────────────────┘    └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                         4. Core Layer                            │
│          Model Gateway │  Tool Registry │  MCP Client           │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                         5. Knowledge Layer                       │
│     Short-term Context │  Long-term Memory │  Vector Store     │
└─────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────┐
│                      6. Infrastructure Layer                     │
│            SQLite │ Milvus │ Phoenix │  Event Bus              │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### Requirements

- Python 3.11+
- uv package manager

### Using uv

```bash
# Clone the repository
git clone https://github.com/your-org/mozi.git
cd mozi

# Install dependencies
uv sync

# Install development dependencies
uv sync --dev

# Run in development mode
uv run mozi
```

### Using pip

```bash
pip install -e .
```

## Quick Start

### CLI Usage

```bash
# Start interactive REPL
mozi

# Run a single command
mozi run "Implement a login feature"

# Ask a question
mozi ask "How do I implement authentication?"
```

### Python API

```python
from mozi.ingress import CLI
from mozi.orchestrator import Orchestrator
from mozi.session import SessionManager

# Using CLI
cli = CLI()
await cli.run("ask How do I implement a login feature?")

# Using Orchestrator directly
orchestrator = Orchestrator()
result = await orchestrator.execute_task(
    task="Implement a login feature",
    session_id="session-123"
)
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest -m unit

# Run integration tests
uv run pytest -m integration

# Run with coverage
uv run pytest --cov=mozi --cov-report=term-missing
```

### Code Quality

```bash
# Lint with ruff
uv run ruff check .

# Type check with mypy
uv run mypy mozi

# Security scan with bandit
uv run bandit -r mozi
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install
```

## Project Structure

```
mozi/
├── core/
│   ├── model/          # Model abstraction layer
│   ├── tools/          # Tool framework and built-in tools
│   ├── session/        # Session management
│   ├── context/        # Context management
│   ├── memory/         # Memory stores
│   └── ingress/        # CLI and REPL
├── orchestrator/
│   ├── main.py         # Main orchestrator
│   ├── workers/        # Worker implementations
│   ├── quality/        # Quality assurance
│   └── state/          # State management
└── infrastructure/
    ├── database/       # Database layer
    ├── eventbus/       # Event bus
    └── vectordb/       # Vector database
```

## Documentation

- [API Documentation](docs/api/)
- [Architecture Design](docs/foundation/architecture/)
- [Module Designs](docs/init/module/)

## Version

Current version: 1.0.0

## License

MIT License
