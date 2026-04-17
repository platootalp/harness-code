# Skills System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Verify and improve the Skills System integration. The core components are implemented but need verification and better error handling. Per design spec Section 11.

**Status Assessment:**
- SkillDefinition, SkillExecutor, SkillTool, SkillRegistry: ✅ Mostly complete
- ToolRegistryInterface: ⚠️ Returns None/[] by default (intentional for interface)
- Missing: Error logging for silent failures, missing tests

---

## File Structure

```
src_py/skills/
├── __init__.py              # Already exports (NO CHANGE)
├── parser.py                # Already implemented (NO CHANGE)
├── registry.py              # MODIFY: Add logging to silent failures
├── test_skills_registry.py  # CREATE: Unit tests
└── test_skill_executor.py   # CREATE: Unit tests for executor
```

---

### Task 1: Write Skills System Tests

**Files:**
- Create: `src_py/skills/test_skills_registry.py`

```python
"""Tests for Skills System."""
import pytest
import tempfile
import asyncio
from pathlib import Path
from src_py.skills.registry import (
    SkillRegistry,
    SkillDefinition,
    SkillExecutor,
    SkillTool,
    SkillParameter,
    ToolRegistryInterface,
    SkillError,
    SecurityError,
    ToolCall,
)
from src_py.lib.models import ToolContext


@pytest.fixture
def skills_dir():
    """Create a temporary skills directory with test skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_path = Path(tmpdir)

        # Create test skill directory
        skill_dir = skills_path / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: test_skill
description: A test skill for unit testing
allowed-tools: Read Glob
---

# Test Skill

This is a test skill that uses Read and Glob tools.
""")
        yield skills_path


@pytest.fixture
def tool_registry():
    """Create a mock tool registry."""
    registry = ToolRegistryInterface()
    # Add some mock tools
    return registry


@pytest.fixture
def skill_executor(tool_registry):
    return SkillExecutor(tool_registry=tool_registry, timeout=5.0)


@pytest.fixture
def tool_context():
    return ToolContext(
        call_id="test-call-123",
        cwd="/tmp",
        session_id="test-session",
        env={},
    )


# === SkillRegistry Tests ===

def test_skill_registry_initialization():
    """SkillRegistry initializes with empty skills."""
    registry = SkillRegistry()
    assert len(registry.list()) == 0


def test_skill_registry_discover(skills_dir):
    """SkillRegistry.discover finds skills in directory."""
    registry = SkillRegistry()
    discovered = registry.discover(skills_dir)

    assert len(discovered) >= 1
    assert any(s.name == "test_skill" for s in discovered)


def test_skill_registry_register():
    """SkillRegistry.register adds skill to registry."""
    registry = SkillRegistry()

    skill = SkillDefinition(
        name="manual_skill",
        description="Manually registered skill",
    )
    registry.register(skill)

    assert registry.get("manual_skill") is not None
    assert registry.get("manual_skill").name == "manual_skill"


def test_skill_registry_list():
    """SkillRegistry.list returns all registered skills."""
    registry = SkillRegistry()

    skill1 = SkillDefinition(name="skill1", description="First")
    skill2 = SkillDefinition(name="skill2", description="Second")
    registry.register(skill1)
    registry.register(skill2)

    skills = registry.list()
    assert len(skills) == 2


def test_skill_registry_find_by_trigger():
    """SkillRegistry.find_by_trigger finds skills by /name."""
    registry = SkillRegistry()

    skill = SkillDefinition(
        name="brainstorm",
        description="Brainstorming skill",
        metadata={"trigger": "/brainstorm"},
    )
    registry.register(skill)

    # Should find by trigger
    found = registry.find_by_trigger("/brainstorm")
    assert found is not None
    assert found.name == "brainstorm"

    # Should also find by name with /
    found2 = registry.find_by_trigger("/brainstorm")
    assert found2 is not None


def test_skill_registry_get_tool():
    """SkillRegistry.get_tool returns SkillTool wrapper."""
    registry = SkillRegistry()

    skill = SkillDefinition(name="tooled_skill", description="With tool")
    registry.register(skill)

    tool = registry.get_tool("tooled_skill")
    assert tool is not None
    assert tool.name == "skill_tooled_skill"


# === SkillExecutor Tests ===

@pytest.mark.asyncio
async def test_skill_executor_initialization():
    """SkillExecutor initializes with config."""
    executor = SkillExecutor(timeout=10.0, max_memory_mb=128)
    assert executor.timeout == 10.0
    assert executor.max_memory_mb == 128


@pytest.mark.asyncio
async def test_skill_executor_extracts_tool_calls(skill_executor):
    """SkillExecutor._extract_tool_calls finds tool calls in args."""
    args = {
        "tool_calls": [
            {"name": "Read", "input": {"file_path": "/tmp/test.txt"}},
            {"name": "Glob", "input": {"pattern": "*.py"}},
        ]
    }

    tool_calls = skill_executor._extract_tool_calls(args)

    assert len(tool_calls) == 2
    assert tool_calls[0].name == "Read"
    assert tool_calls[1].name == "Glob"


@pytest.mark.asyncio
async def test_skill_executor_check_tool_boundaries_allows():
    """SkillExecutor._check_tool_boundaries allows known tools."""
    skill = SkillDefinition(
        name="test",
        description="test",
        allowed_tools=["Read", "Glob"],
    )

    tool_calls = [
        ToolCall(name="Read", input={}),
        ToolCall(name="Glob", input={}),
    ]

    # Should not raise
    skill_executor._check_tool_boundaries(skill, tool_calls)


@pytest.mark.asyncio
async def test_skill_executor_check_tool_boundaries_rejects():
    """SkillExecutor._check_tool_boundaries rejects unknown tools."""
    skill = SkillDefinition(
        name="test",
        description="test",
        allowed_tools=["Read"],  # Only Read allowed
    )

    tool_calls = [
        ToolCall(name="Bash", input={}),  # Bash not allowed
    ]

    with pytest.raises(SecurityError):
        skill_executor._check_tool_boundaries(skill, tool_calls)


# === SkillTool Tests ===

def test_skill_tool_name():
    """SkillTool.name returns skill_ prefixed name."""
    skill = SkillDefinition(name="brainstorm", description="Brainstorm")
    executor = SkillExecutor()
    tool = SkillTool(skill, executor)

    assert tool.name == "skill_brainstorm"


def test_skill_tool_description():
    """SkillTool.description returns skill description."""
    skill = SkillDefinition(name="test", description="A test skill")
    executor = SkillExecutor()
    tool = SkillTool(skill, executor)

    assert tool.description == "A test skill"


def test_skill_tool_input_schema():
    """SkillTool.input_schema generates JSON Schema."""
    skill = SkillDefinition(
        name="test",
        description="test",
        parameters=[
            SkillParameter(name="input", type="string", description="Input text", required=True),
        ],
    )
    executor = SkillExecutor()
    tool = SkillTool(skill, executor)

    schema = tool.input_schema
    assert schema["type"] == "object"
    assert "input" in schema["properties"]
    assert "input" in schema["required"]
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/lijunyi/road/claude-code && python3 -m pytest src_py/skills/test_skills_registry.py -v
```

Expected: Most tests pass, some may fail if mock setup is incomplete.

---

### Task 2: Add Error Logging to Skills Registry

**Files:**
- Modify: `src_py/skills/registry.py`

- [ ] **Step 1: Add logging import**

Add at top of file:
```python
import logging

logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Add logging to SkillExecutor._sandboxed_execute**

Find the `_sandboxed_execute` method and ensure exceptions are logged:

```python
    async def _sandboxed_execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolContext,
        timeout: float,
        max_memory_mb: int,
    ) -> Any:
        """Sandboxed skill execution with subprocess + resource limits."""
        try:
            return await self._run_skill_script(skill, args, context, timeout, max_memory_mb)
        except asyncio.TimeoutError:
            raise SkillTimeoutError(f"Skill execution timed out after {timeout}s")
        except Exception as e:
            logger.warning(f"Skill '{skill.name}' execution failed: {e}")
            raise SkillExecutionError(f"Skill execution failed: {e}")
```

- [ ] **Step 3: Add logging to SkillRegistry.discover**

```python
        except Exception as e:
            logger.warning(f"Failed to load skill from {skill_path}: {e}")
```

Note: The existing code already has `warnings.warn` - that's fine, but we should also log.

- [ ] **Step 4: Run tests**

```bash
cd /Users/lijunyi/road/claude-code && python3 -m pytest src_py/skills/test_skills_registry.py -v
```

---

### Task 3: Verify ToolRegistryInterface Integration

**Files:**
- Review: `src_py/skills/registry.py:206-216`

- [ ] **Step 1: Verify ToolRegistryInterface is used correctly**

The `ToolRegistryInterface` is a minimal interface. When a real `ToolRegistry` (from `tools/base.py`) is passed to `SkillRegistry.__init__`, the executor uses it properly.

Verify that the interface contract is satisfied:
- `get(name)` -> returns ToolDefinition or None ✓
- `list()` -> returns list of tools ✓

---

## Verification

```bash
cd /Users/lijunyi/road/claude-code
python3 -m pytest src_py/skills/test_skills_registry.py -v
```

Expected: **All tests pass**

---

## Implementation Notes

1. **ToolRegistryInterface is intentional** - It's a minimal interface stub. The real ToolRegistry is in `tools/base.py` and is properly implemented.
2. **Silent failures in _sandboxed_execute** - Add logging to make failures visible.
3. **Progressive loading** - The skills system uses progressive loading (discover only loads name/description, activate loads full content). This is working as designed.
