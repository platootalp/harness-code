# Phase 10: Skills System Design

**Date:** 2026-04-06
**Status:** Design Complete
**Source:** Analysis of `src/skills/`, `src/commands/skills/`, `src/tools/SkillTool/`, and `src_py/skills/` in the TypeScript/Python codebases

---

## 1. Skills System Architecture Overview

### 1.1 Core Concept

The Skills System provides a mechanism for extending Claude Code's capabilities through reusable, self-contained workflow definitions. Skills are invoked via slash commands (e.g., `/brainstorm`, `/verify`) and can execute either inline (expanding into the current conversation) or as forked sub-agents (with separate context and token budget).

### 1.2 Skills vs Commands Distinction

| Aspect | Command | Skill |
|--------|---------|-------|
| **Definition** | Generic term for any invocable entity | Specialized workflow definition with metadata |
| **Invocation** | Via slash commands or tools | Via slash commands, SkillTool, or auto-invocation |
| **Structure** | Can be any type: `prompt`, `local`, `local-jsx` | Always `prompt` type with rich metadata |
| **Metadata** | Basic (name, description) | Rich (allowed-tools, when_to_use, arguments, hooks) |
| **Content** | Single markdown or code | Directory with SKILL.md + optional scripts/references/assets |

**Command Type Union:**
```typescript
type Command = CommandBase & (PromptCommand | LocalCommand | LocalJSXCommand)

type PromptCommand = {
  type: 'prompt'
  progressMessage: string
  contentLength: number
  argNames?: string[]
  allowedTools?: string[]
  model?: string
  source: SettingSource | 'builtin' | 'mcp' | 'plugin' | 'bundled'
  hooks?: HooksSettings
  skillRoot?: string
  context?: 'inline' | 'fork'
  agent?: string
  effort?: EffortValue
  paths?: string[]
  getPromptForCommand(args: string, context: ToolUseContext): Promise<ContentBlockParam[]>
}
```

---

## 2. Skill Definition Format (SKILL.md)

### 2.1 File Structure

Skills use a directory-based format:

```
skill-name/
├── SKILL.md           # Required: Main skill definition
├── scripts/           # Optional: Executable scripts
│   ├── main.py       # Entry point
│   └── helpers.py
├── references/        # Optional: Reference documents
│   └── api-docs.md
└── assets/           # Optional: Static assets
    └── template.txt
```

### 2.2 SKILL.md Format

```markdown
---
name: skill-name
description: One-line description of what this skill does
allowed-tools: Read Glob Bash(git:*) Grep
when_to_use: |
  Use when the user wants to brainstorm ideas.
  Examples: 'brainstorm features', '/brainstorm', 'brainstorm'
argument-hint: "[topic to brainstorm]"
arguments:
  - topic
context: inline
agent: general-purpose
model: opus
disable-model-invocation: false
user-invocable: true
version: "1.0.0"
paths:
  - "**/*.py"
  - "**/*.ts"
---

# Skill Title

Detailed description of the skill workflow.

## Goal

Clearly state what this skill accomplishes.

## Steps

### 1. Step Name

Action to perform.

**Success criteria**: What proves this step is complete.

### 2. Step with Parameters

Use $variable_name for argument substitution.

**Success criteria**: ...

## Rules

- Rule 1
- Rule 2
```

### 2.3 Frontmatter Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Skill identifier (directory name used if omitted) |
| `description` | string | One-line description shown in typeahead |
| `allowed-tools` | string | Space-separated list of permitted tools with optional glob patterns (e.g., `Read Glob Bash(git:*)`) |
| `when_to_use` | string | Detailed usage scenarios for auto-invocation hints |
| `argument-hint` | string | Hint text shown for arguments (e.g., `"[PR number]"`) |
| `arguments` | list | Named arguments for substitution |
| `context` | `inline` \| `fork` | Execution context (default: `inline`) |
| `agent` | string | Agent type for forked execution (e.g., `Task`, `general-purpose`) |
| `model` | string | Model override for this skill |
| `disable-model-invocation` | boolean | Prevent model from auto-invoking this skill |
| `user-invocable` | boolean | Whether user can invoke via slash command (default: true) |
| `version` | string | Skill version |
| `paths` | list | Glob patterns for conditional activation |
| `hooks` | dict | Hook definitions (see Hooks system) |

---

## 3. Skill Loading Architecture

### 3.1 Skill Sources

Skills are loaded from multiple sources in priority order:

| Source | Path | Description |
|--------|------|-------------|
| **Bundled** | Compiled into CLI | Built-in skills (verify, debug, simplify, etc.) |
| **Managed** | `~/.claude/.claude/skills/` | Enterprise-managed skills |
| **User** | `~/.claude/skills/` | User-defined personal skills |
| **Project** | `.claude/skills/` | Project-specific skills |
| **Additional** | Custom `--add-dir` paths | User-specified additional directories |
| **Legacy Commands** | `commands/` directories | Deprecated, supports old format |
| **MCP** | From MCP servers | Skills provided by MCP tools |
| **Plugin** | From plugin manifests | Skills bundled with plugins |

### 3.2 Loading Process

```
getSkillDirCommands(cwd)
├── loadSkillsFromSkillsDir(managedSkillsDir)
├── loadSkillsFromSkillsDir(userSkillsDir)
├── loadSkillsFromSkillsDir(projectSkillsDirs)  // Parallel
├── loadSkillsFromSkillsDir(additionalDirs)    // Parallel
└── loadSkillsFromCommandsDir(cwd)              // Legacy
    │
    ├── Deduplicate by resolved path (realpath)
    ├── Separate conditional vs unconditional
    └── Return Command[]
```

**Key Files:**
- `src/skills/loadSkillsDir.ts`: Main loading logic
- `src/skills/bundledSkills.ts`: Bundled skill registration

### 3.3 Progressive Loading

Skills use progressive loading for fast startup:

1. **Discover (fast)**: Only loads name + description from frontmatter
2. **Activate (lazy)**: Full content loaded on first invocation
3. **Reference (on-demand)**: Scripts/references loaded when accessed

```python
class SkillDefinition:
    _loaded: bool = False
    instructions: str = ""

    def load_full(self) -> SkillDefinition:
        """Load full content (instructions + references) on activation."""
        if self._loaded or self._path is None:
            return self
        skill_md = self._path / "SKILL.md"
        if skill_md.exists():
            raw_content = skill_md.read_text()
            _, markdown = parse_frontmatter(raw_content)
            self.instructions = markdown.strip()
        self._loaded = True
        return self
```

### 3.4 Dynamic Skill Discovery

Skills can be discovered dynamically during file operations:

```typescript
export async function discoverSkillDirsForPaths(
  filePaths: string[],
  cwd: string,
): Promise<string[]>

export async function addSkillDirectories(dirs: string[]): Promise<void>
```

### 3.5 Conditional Skills (Path-Based Activation)

Skills with `paths` frontmatter are conditionally activated:

```yaml
---
name: python-refactor
paths:
  - "**/*.py"
---
```

---

## 4. Skill Invocation Patterns

### 4.1 Via SkillTool

The primary programmatic invocation mechanism:

```typescript
inputSchema = z.object({
  skill: z.string().describe('The skill name. E.g., "commit", "review-pr"'),
  args: z.string().optional().describe('Optional arguments for the skill'),
})
```

### 4.2 Via Slash Commands

User types `/skill-name` to invoke:

```
/brainstorm feature ideas
```

### 4.3 Inline vs Forked Execution

**Inline Execution:**
- Skill content expands into current conversation
- Shares context with main agent
- Default behavior

**Forked Execution:**
- Runs in sub-agent with separate context
- Has own token budget
- Specified via `context: fork` in frontmatter

---

## 5. Built-in Skills Registry

### 5.1 Bundled Skills

From `src/skills/bundled/index.ts`:

```typescript
export function initBundledSkills(): void {
  registerUpdateConfigSkill()
  registerKeybindingsSkill()
  registerVerifySkill()
  registerDebugSkill()
  registerLoremIpsumSkill()
  registerSkillifySkill()
  registerRememberSkill()
  registerSimplifySkill()
  registerBatchSkill()
  registerStuckSkill()
}
```

### 5.2 Example Bundled Skill

From `src/skills/bundled/remember.ts`:

```typescript
export function registerRememberSkill(): void {
  registerBundledSkill({
    name: 'remember',
    description: 'Review auto-memory entries and propose promotions to CLAUDE.md, CLAUDE.local.md, or shared memory.',
    whenToUse: 'Use when the user wants to review, organize, or promote their auto-memory entries.',
    userInvocable: true,
    isEnabled: () => isAutoMemoryEnabled(),
    async getPromptForCommand(args) {
      let prompt = SKILL_PROMPT
      if (args) {
        prompt += `\n## Additional context from user\n\n${args}`
      }
      return [{ type: 'text', text: prompt }]
    },
  })
}
```

---

## 6. Python Implementation

### 6.1 File Structure

```
src_py/skills/
├── __init__.py              # Public exports
├── parser.py                # SKILL.md parsing
├── registry.py              # SkillRegistry, SkillExecutor, SkillTool
└── test_skills_registry.py  # Unit tests
```

### 6.2 Core Classes

```python
@dataclass
class SkillParameter:
    name: str
    type: str  # string, number, boolean
    description: str = ""
    required: bool = False

@dataclass
class SkillDefinition:
    name: str
    description: str
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    allowed_tools: list[str] = field(default_factory=list)
    instructions: str = ""
    _loaded: bool = False
    parameters: list[SkillParameter] = field(default_factory=list)
    scripts_path: Path | None = None
    references_path: Path | None = None
    assets_path: Path | None = None
    _path: Path | None = None

class SkillExecutor:
    """Skill execution engine with allowed-tools boundary checking."""

    def __init__(
        self,
        tool_registry: ToolRegistryInterface | None = None,
        timeout: float = 30.0,
        max_memory_mb: int = 256,
    ): ...

    async def execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolContext,
    ) -> Any: ...

class SkillTool:
    """Skill wrapper as a Tool, enabling LLM to invoke skills directly."""

    @property
    def name(self) -> str: ...

    @property
    def input_schema(self) -> dict[str, Any]: ...

    async def execute(
        self,
        args: dict[str, Any],
        context: ToolContext,
    ) -> SkillToolResult: ...

class SkillRegistry:
    """Skill registry with progressive loading and auto-registration."""

    def discover(self, skills_dir: Path) -> list[SkillDefinition]: ...
    def register(self, skill: SkillDefinition) -> None: ...
    def get(self, name: str) -> SkillDefinition | None: ...
    async def activate(self, skill_name: str) -> SkillDefinition: ...
    async def execute(
        self,
        skill_name: str,
        args: dict[str, Any],
        context: ToolContext,
    ) -> Any: ...
    def find_by_trigger(self, trigger: str) -> SkillDefinition | None: ...
```

### 6.3 SKILL.md Parser

```python
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from SKILL.md content."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    fm_text = match.group(1)
    frontmatter = yaml.safe_load(fm_text) or {}
    markdown = content[match.end():]
    return frontmatter, markdown

def parse_allowed_tools(raw: str) -> list[str]:
    """Parse allowed-tools string into tool names."""
    if not raw.strip():
        return []
    pattern = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\([^)]*\))?")
    return [m.group(1) for m in pattern.finditer(raw)]
```

### 6.4 Error Handling

```python
class SkillError(Exception):
    """Base exception for skill-related errors."""
    pass

class SecurityError(SkillError):
    """Raised when a skill attempts to call a disallowed tool."""
    pass

class SkillTimeoutError(SkillError):
    """Raised when skill execution times out."""
    pass

class SkillExecutionError(SkillError):
    """Raised when skill execution fails."""
    pass

class SkillMemoryError(SkillError):
    """Raised when skill exceeds memory limit."""
    pass
```

---

## 7. Allowed-Tools Boundary Checking

### 7.1 Purpose

Security mechanism to restrict which tools a skill can use.

### 7.2 Format

```yaml
allowed-tools: Read Glob Grep Bash(git:*) Bash(npm:*)
```

Tool patterns:
- Exact name: `Read`, `Glob`
- Namespaced: `Bash(git:*)` - Bash tool with git subcommand
- Glob patterns: `Bash(git:*)` matches any git command

### 7.3 Implementation

```python
class SkillExecutor:
    def _check_tool_boundaries(
        self,
        skill: SkillDefinition,
        tool_calls: list[ToolCall],
    ) -> None:
        """Verify all tool calls are within allowed-tools boundary."""
        allowed_set = set(skill.allowed_tools)
        for tc in tool_calls:
            if tc.name not in allowed_set:
                raise SecurityError(
                    f"Skill '{skill.name}' attempted to call tool '{tc.name}' "
                    f"which is not in allowed-tools: {sorted(allowed_set)}"
                )
```

---

## 8. Integration Points

### 8.1 With Tool Registry

Skills auto-register as Tools when added to registry:

```python
class SkillRegistry:
    def register(self, skill: SkillDefinition) -> None:
        self.skills[skill.name] = skill
        skill_tool = SkillTool(skill, self._executor)
        self._skill_tool_map[skill.name] = skill_tool
```

### 8.2 With Orchestrator

```python
class SkillRegistry(Protocol):
    def get(self, name: str) -> SkillDefinition | None: ...
    def list(self) -> list[SkillDefinition]: ...
    async def execute(self, skill_name: str, args: dict, context: ToolContext) -> Any: ...
```

### 8.3 With MCP

MCP skills use same loading mechanism but from MCP server manifests.

### 8.4 With Plugins

Plugin skills declared in `plugin.json`:

```json
{
  "skills": ["skills/**/*.md"]
}
```

---

## 9. Implementation Status

### 9.1 Completed
- [x] `SkillDefinition` dataclass with progressive loading
- [x] `SkillRegistry` with discover/register/get/list
- [x] `SkillExecutor` with boundary checking
- [x] `SkillTool` wrapper for tool protocol
- [x] `parse_frontmatter()` for SKILL.md parsing
- [x] `parse_allowed_tools()` for tool pattern parsing
- [x] Unit tests

### 9.2 TODO
- [ ] Bundled skills registration (Python equivalent of `registerBundledSkill`)
- [ ] Shell command execution in prompts (`!` syntax)
- [ ] Dynamic skill discovery during file operations
- [ ] Conditional skills with path-based activation
- [ ] Full hooks integration
- [ ] Forked execution support (sub-agent)
- [ ] Skill caching and invalidation

---

## 10. Reference Implementation

### TypeScript References
- `src/skills/loadSkillsDir.ts` - Main loading logic
- `src/skills/bundledSkills.ts` - Bundled skill registration
- `src/skills/bundled/*.ts` - Individual bundled skills
- `src/tools/SkillTool/SkillTool.ts` - SkillTool implementation
- `src/types/command.ts` - Command type definitions
- `src/utils/processUserInput/processSlashCommand.tsx` - Slash command processing

### Python References
- `src_py/skills/registry.py` - Core classes
- `src_py/skills/parser.py` - SKILL.md parsing
- `src_py/skills/test_skills_registry.py` - Tests
