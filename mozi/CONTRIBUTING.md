# Contributing to Mozi

Thank you for your interest in contributing to Mozi. This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.11+
- uv package manager
- Git

### Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/mozi.git
   cd mozi
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/original-org/mozi.git
   ```
4. Install dependencies:
   ```bash
   uv sync --dev
   ```
5. Install pre-commit hooks:
   ```bash
   uv run pre-commit install
   ```

## Development Workflow

### Branch Naming

Branches must follow the naming convention:
- `feature/[name]` - New features
- `fix/[name]` - Bug fixes
- `docs/[name]` - Documentation updates
- `refactor/[name]` - Code refactoring
- `test/[name]` - Test additions
- `ci/[name]` - CI/CD changes
- `security/[name]` - Security improvements
- `hotfix/[name]` - Urgent fixes

### Creating a Feature Branch

```bash
# Ensure you're on develop
git checkout develop

# Update to latest
git pull upstream develop

# Create feature branch
git checkout -b feature/my-new-feature

# Make your changes
# ...

# Push to your fork
git push origin feature/my-new-feature
```

### Commit Guidelines

Commits must follow the format:
```
<type>: <subject>

<body>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring (no functional changes)
- `test`: Adding or updating tests
- `ci`: CI/CD changes
- `security`: Security improvements
- `chore`: Maintenance tasks

**Rules:**
- Subject uses imperative mood, first letter capitalized, no period, max 50 characters
- Body explains "what" and "why", not "how"
- Break long lines at 100 characters
- Separate subject from body with a blank line

**Examples:**
```
feat: add complexity-based task routing

Implement routing logic that routes tasks to appropriate workers
based on complexity score: Explorer (0-40), Planner (41-70), Coder (71-100).

fix: resolve session timeout race condition

When session expires during active task execution, the task result
was being written to an invalid session. Added session validation
before writing results.
```

### Rebasing

Before submitting a PR, rebase your branch onto the latest `develop`:

```bash
git fetch upstream
git rebase upstream/develop

# If conflicts occur, resolve them and continue:
git rebase --continue

# Verify the rebase was successful
git log --oneline -5
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=mozi --cov-report=term-missing

# Run specific test categories
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m e2e           # E2E tests only

# Run a specific test file
uv run pytest tests/unit/core/model/test_retry.py

# Run with verbose output
uv run pytest -v
```

### Code Quality Checks

All checks must pass before submitting a PR:

```bash
# Lint
uv run ruff check .

# Type check
uv run mypy mozi

# Security scan
uv run bandit -r mozi

# All checks at once
uv run ruff check . && uv run mypy mozi && uv run bandit -r mozi
```

## Pull Request Process

### Before Submitting

1. Ensure all tests pass
2. Ensure code quality checks pass
3. Update documentation if needed
4. Add tests for new functionality
5. Keep coverage at ≥80%

### PR Description

Include the following in your PR description:

- **Summary**: Brief description of changes
- **Test Plan**: How the changes were tested
- **Checklist**:
  - [ ] Tests added/updated
  - [ ] Documentation updated
  - [ ] Code follows style guidelines
  - [ ] No hardcoded secrets

### Review Process

1. Maintainers will review your PR
2. Address any feedback
3. Once approved, a maintainer will merge

## Code Standards

### Python

- Use Python 3.11+
- Line length: 100 characters
- Use double quotes
- Indentation: 4 spaces
- Import order: stdlib → third-party → local
- No wildcard imports (`from module import *`)
- Type annotations required for:
  - Function parameters
  - Function return values
  - Class attributes
  - Module-level constants
- Public functions must have docstrings
- Use `async`/`await`, no callback style
- Custom exceptions inherit from `MoziError`
- No bare `except Exception`

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Modules | snake_case | `session_manager.py` |
| Classes | PascalCase | `SessionManager` |
| Functions | snake_case | `create_session()` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Private | Leading underscore | `_internal_method()` |

### Testing

- Use AAA structure (Arrange, Act, Assert)
- Descriptive test names
- Test both normal and edge cases
- Test error handling
- Use `@pytest.mark.parametrize` for multiple test cases
- Mock external services
- No `sleep` statements
- No test order dependencies

## Reporting Issues

When reporting issues, include:

- **Environment**: OS, Python version, package versions
- **Description**: Clear description of the issue
- **Steps to Reproduce**: Minimal steps to reproduce
- **Expected vs Actual**: What you expected vs what happened
- **Logs**: Relevant error messages or logs

## Questions?

Feel free to:
- Open an issue for bugs or feature requests
- Join project discussions
- Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
