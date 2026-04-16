# Changelog

All notable changes to Mozi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-01

### Added

#### Core Architecture
- **Four-layer architecture**: Ingress → Orchestrator → Capabilities → Infrastructure
- **Orchestrator-Worker pattern**: Intelligent task routing with ReAct loop engine
- **Complexity-based routing**: Tasks automatically routed by complexity score (0-100)
  - Explorer Worker: SIMPLE (0-40)
  - Planner Worker: MEDIUM (41-70)
  - Coder Worker: COMPLEX (71-100)

#### Session Management
- `SessionManager`: Session lifecycle management (create, destroy, route)
- `SessionStorage`: SQLite-based persistent storage with async support
- Session state tracking and concurrency control

#### Context Management
- `ContextBuilder`: Builds conversation context for sessions
- `ContextWindow`: Sliding window for message management
- `ContextOffloader`: Offloads context to external storage with reference IDs
- Token count tracking and truncation

#### Memory System
- `ShortTermMemory`: In-memory context storage
- `LongTermMemory`: Persistent memory with vector store support
- `MemoryRetriever`: Semantic search for memories
- Memory types: EPISODIC, SEMANTIC, PROCEDURAL

#### Model Abstraction
- `ModelRegistry`: Multi-model support with dynamic registration
- `OpenAIAdapter`: OpenAI API integration
- `AnthropicAdapter`: Anthropic API integration
- `CircuitBreaker`: Failure handling with configurable thresholds
- `RetryStrategy`: Configurable retry with exponential backoff
- Error classification and handling

#### Tools Framework
- `Tool` base class with `ToolContext` and `ToolResult`
- `ToolRegistry`: Tool registration and execution
- Built-in tools:
  - `ReadFileTool`: File reading with path validation
  - `WriteFileTool`: Atomic file writes
  - `EditFileTool`: String/regex-based editing
  - `BashTool`: Shell command execution with security controls
  - `GrepTool`: Pattern-based file searching
  - `GlobTool`: Glob pattern file matching
- Security features:
  - Permission levels (0-4: Sandbox to Full access)
  - `DangerousFunctionDetector`: Blocks dangerous function calls
  - Path whitelist validation
  - Working directory restrictions

#### Ingress Layer
- `CLI`: Command-line interface with REPL support
- `CommandParser`: Natural language command parsing
- `OutputHandler`: Response formatting and display
- Command types: ask, execute, session, context, exit

#### Quality Assurance
- `QualityChecker`: Code quality validation
- Syntax checking, style checking, security scanning
- `Reviewer`: Code review automation

#### Infrastructure
- Async SQLite database layer
- Event bus for module communication
- Vector database integration (Milvus)
- Observability with Phoenix/OpenTelemetry

### Testing
- Unit test coverage ≥80% per file
- Integration test suite
- E2E workflow tests
- 622+ unit tests passing

### Documentation
- API documentation for all modules
- Architecture design documents
- Module design specifications
- Contribution guidelines

## [0.1.0] - 2026-03-29

### Added
- Initial project skeleton
- Basic project structure
- Configuration system
