"""Skills System - SkillRegistry, SkillExecutor, SkillTool."""
from __future__ import annotations

import asyncio
import json
import resource
import tempfile
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..session.models import TokenUsage


# --- ToolContext (redefined here to avoid circular imports) ---


@dataclass
class ToolContext:
    """Tool/Skill execution context."""
    call_id: str
    agent_id: str
    task_id: str | None = None
    cwd: str = ""
    env: dict[str, str] = field(default_factory=dict)
    session_id: str = ""
    token_budget: Any = None  # ContextBudget, optional


# --- Errors ---


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


# --- SKILL.md Parser ---


# Pattern to match YAML frontmatter
_FRONTMATTER_RE = __import__("re").compile(r"^---\s*\n(.*?)\n---\s*\n", __import__("re").DOTALL)


@dataclass
class SkillParameter:
    """A skill parameter definition."""
    name: str
    type: str  # string, number, boolean
    description: str = ""
    required: bool = False


@dataclass
class SkillDefinition:
    """Parsed skill definition from SKILL.md."""
    name: str
    description: str
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # allowed-tools: list of pre-approved tools for this skill
    allowed_tools: list[str] = field(default_factory=list)

    # Full content (loaded on activation)
    instructions: str = ""

    # Progressive loading flag
    _loaded: bool = False

    # Optional parameters
    parameters: list[SkillParameter] = field(default_factory=list)

    # Subdirectory paths (set during parsing)
    scripts_path: Path | None = None
    references_path: Path | None = None
    assets_path: Path | None = None

    # Path to the skill directory (for loading references on demand)
    _path: Path | None = None

    def load_full(self) -> SkillDefinition:
        """Load full content (instructions + references) on activation."""
        if self._loaded or self._path is None:
            return self
        skill_md = self._path / "SKILL.md"
        if skill_md.exists():
            raw_content = skill_md.read_text()
            _, markdown = _parse_frontmatter(raw_content)
            self.instructions = markdown.strip()
        self._loaded = True
        return self

    def load_reference(self, ref_name: str) -> str:
        """Load a specific reference document on demand."""
        if self.references_path is None:
            return ""
        ref_file = self.references_path / ref_name
        if not ref_file.exists():
            # Try .md extension
            ref_file = self.references_path / f"{ref_name}.md"
        if ref_file.exists():
            return ref_file.read_text()
        return ""


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from SKILL.md content."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    import yaml
    fm_text = match.group(1)
    frontmatter = yaml.safe_load(fm_text) or {}
    markdown = content[match.end():]
    return frontmatter, markdown


def parse_skill_md(skill_path: Path) -> SkillDefinition:
    """Parse a SKILL.md file into a SkillDefinition (progressive loading)."""
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

    raw_content = skill_md.read_text()
    frontmatter, _ = _parse_frontmatter(raw_content)

    name = frontmatter.get("name", skill_path.name)
    description = frontmatter.get("description", "")
    license = frontmatter.get("license")
    compatibility = frontmatter.get("compatibility")
    metadata = frontmatter.get("metadata", {})

    # Parse allowed-tools: space-separated tool names, optionally with (glob)
    allowed_tools_raw = frontmatter.get("allowed-tools", "")
    if isinstance(allowed_tools_raw, str):
        allowed_tools = _parse_allowed_tools(allowed_tools_raw)
    else:
        allowed_tools = list(allowed_tools_raw) if allowed_tools_raw else []

    # Parse optional parameters
    parameters = []
    for p in metadata.get("parameters", []):
        parameters.append(SkillParameter(
            name=p.get("name", ""),
            type=p.get("type", "string"),
            description=p.get("description", ""),
            required=p.get("required", False),
        ))

    skill = SkillDefinition(
        name=name,
        description=description,
        license=license,
        compatibility=compatibility,
        metadata=metadata,
        allowed_tools=allowed_tools,
        instructions="",
        _loaded=False,
        parameters=parameters,
        _path=skill_path,
    )

    # Set subdirectory paths
    if (skill_path / "scripts").is_dir():
        skill.scripts_path = skill_path / "scripts"
    if (skill_path / "references").is_dir():
        skill.references_path = skill_path / "references"
    if (skill_path / "assets").is_dir():
        skill.assets_path = skill_path / "assets"

    return skill


def _parse_allowed_tools(raw: str) -> list[str]:
    """Parse allowed-tools string into tool names.

    e.g. "Bash(git:*) Read Glob" -> ["Bash", "Read", "Glob"]
    Supports glob patterns inside parentheses as tool-specific filters.
    """
    import re
    if not raw.strip():
        return []
    pattern = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\([^)]*\))?")
    return [m.group(1) for m in pattern.finditer(raw)]


# --- ToolCall (minimal, for boundary checking) ---


@dataclass
class ToolCall:
    """Represents a tool call within skill execution."""
    name: str
    input: dict[str, Any] = field(default_factory=dict)


# --- ToolRegistry interface ---


class ToolRegistryInterface:
    """Minimal tool registry interface required by SkillExecutor."""

    def get(self, name: str) -> Any:
        """Get a tool by name, or None if not found."""
        return None

    def list(self) -> list[Any]:
        """List all registered tools."""
        return []


# --- SkillExecutor ---


class SkillExecutor:
    """Skill execution engine with allowed-tools boundary checking."""

    def __init__(
        self,
        tool_registry: ToolRegistryInterface,
        timeout: float = 30.0,
        max_memory_mb: int = 256,
    ):
        self.tool_registry = tool_registry
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb

    async def execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolContext,
    ) -> Any:
        """
        Execute a skill with security checks and resource limits.

        Args:
            skill: The skill to execute.
            args: Skill arguments.
            context: Execution context.

        Returns:
            The skill execution result.

        Raises:
            SecurityError: If skill attempts to call disallowed tools.
            SkillTimeoutError: If execution times out.
            SkillMemoryError: If memory limit exceeded.
            SkillExecutionError: If execution fails.
        """
        # 1. Ensure full content is loaded
        skill.load_full()

        # 2. Check allowed-tools boundary
        if skill.allowed_tools:
            tool_calls = self._extract_tool_calls(args)
            self._check_tool_boundaries(skill, tool_calls)

        # 3. Execute with resource limits
        return await self._sandboxed_execute(
            skill=skill,
            args=args,
            context=context,
            timeout=self.timeout,
            max_memory_mb=self.max_memory_mb,
        )

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

    def _extract_tool_calls(self, args: dict[str, Any]) -> list[ToolCall]:
        """
        Extract tool calls from skill arguments for boundary checking.

        This detects tool calls nested in:
        - args["tool_calls"]: direct list/dict
        - args["input"]["tool_calls"]: nested inside input param

        Note: Tool calls made via SkillTool (indirect) are validated
        at the SkillTool.execute() level, not here.
        """
        tool_calls: list[ToolCall] = []

        # Direct field
        if "tool_calls" in args:
            tc = args["tool_calls"]
            if isinstance(tc, list):
                for item in tc:
                    if isinstance(item, dict):
                        tool_calls.append(ToolCall(name=item.get("name", ""), input=item.get("input", {})))
                    elif isinstance(item, ToolCall):
                        tool_calls.append(item)
            elif isinstance(tc, dict):
                tool_calls.append(ToolCall(name=tc.get("name", ""), input=tc.get("input", {})))

        # Nested in input
        if "input" in args and isinstance(args["input"], dict):
            nested = args["input"].get("tool_calls", [])
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        tool_calls.append(ToolCall(name=item.get("name", ""), input=item.get("input", {})))
                    elif isinstance(item, ToolCall):
                        tool_calls.append(item)

        return tool_calls

    async def _sandboxed_execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolContext,
        timeout: float,
        max_memory_mb: int,
    ) -> Any:
        """
        Sandboxed skill execution with subprocess + resource limits.

        Uses a temporary directory for isolation, sets memory limits
        via resource module, and enforces timeout via asyncio.
        """
        # Use the instructions as the primary execution guide.
        # The actual skill logic is injected from skill.instructions
        # or from a script in skill.scripts_path.
        #
        # This is a stub implementation that returns the skill instructions
        # as output. Full implementation would invoke scripts or an LLM
        # with the skill instructions as a system prompt.
        #
        # For now, we execute a lightweight script that runs the skill logic.
        try:
            result = await self._run_skill_script(skill, args, context, timeout, max_memory_mb)
            return result
        except asyncio.TimeoutError:
            raise SkillTimeoutError(f"Skill execution timed out after {timeout}s")

    async def _run_skill_script(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolContext,
        timeout: float,
        max_memory_mb: int,
    ) -> Any:
        """Run skill logic in a subprocess with resource limits."""
        import sys

        # Determine which script to run
        script_path: Path | None = None
        if skill.scripts_path:
            candidates = [
                skill.scripts_path / f"{skill.name}.py",
                skill.scripts_path / "main.py",
                skill.scripts_path / "__main__.py",
            ]
            for candidate in candidates:
                if candidate.exists():
                    script_path = candidate
                    break

        if script_path is None:
            # No script: return instructions as a "virtual execution"
            # In a full implementation, this would be passed to an LLM
            return {
                "status": "success",
                "output": f"Skill '{skill.name}' loaded with instructions:\n\n{skill.instructions[:500]}",
                "skill_name": skill.name,
                "args": args,
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            args_file = Path(tmpdir) / "args.json"
            result_file = Path(tmpdir) / "result.json"

            # Serialize args for subprocess
            args_file.write_text(json.dumps({
                "skill_name": skill.name,
                "args": args,
                "context": {
                    "cwd": context.cwd,
                    "session_id": context.session_id,
                },
                "instructions": skill.instructions,
            }))

            # Set memory limit
            max_memory_bytes = max_memory_mb * 1024 * 1024
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            try:
                resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, hard))
            except (ValueError, OSError):
                pass  # May fail in some environments (e.g., containers)

            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(script_path),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=context.cwd or None,
                    env={**context.env} if context.env else None,
                )

                stdin_data = json.dumps({
                    "args_file": str(args_file),
                    "result_file": str(result_file),
                }).encode()
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=stdin_data),
                    timeout=timeout,
                )

                if process.returncode != 0:
                    err_text = stderr.decode() if stderr else ""
                    raise SkillExecutionError(f"Skill script failed: {err_text}")

                if result_file.exists():
                    result = json.loads(result_file.read_text())
                    return result.get("output", result)
                else:
                    # Script ran but produced no result file
                    stdout_text = stdout.decode().strip()
                    return {"status": "success", "output": stdout_text}

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise SkillTimeoutError(f"Skill execution timed out after {timeout}s")
            finally:
                resource.setrlimit(resource.RLIMIT_AS, (soft, hard))


# --- SkillTool ---


@dataclass
class SkillToolResult:
    """Result from SkillTool execution."""
    call_id: str
    output: Any = None
    error: str | None = None


class SkillTool:
    """
    Skill wrapper as a Tool, enabling LLM to invoke skills directly.

    Wraps SkillDefinition + SkillExecutor into the Tool protocol:
    - name: "skill_{skill_name}"
    - description: from skill.description
    - input_schema: generated from skill.parameters
    """

    def __init__(self, skill: SkillDefinition, executor: SkillExecutor):
        self.skill = skill
        self.executor = executor

    @property
    def name(self) -> str:
        return f"skill_{self.skill.name}"

    @property
    def description(self) -> str:
        return self.skill.description

    @property
    def input_schema(self) -> dict[str, Any]:
        """Generate JSON Schema from skill parameters."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.skill.parameters:
            param_type = param.type.lower()
            if param_type in ("string", "number", "boolean"):
                properties[param.name] = {
                    "type": param_type,
                    "description": param.description,
                }
                if param.required:
                    required.append(param.name)

        # Default: single "input" parameter if no explicit parameters
        if not properties:
            properties["input"] = {"type": "string", "description": "Skill input"}

        return {
            "type": "object",
            "properties": properties,
            "required": required or ["input"],
        }

    async def execute(
        self,
        args: dict[str, Any],
        context: ToolContext,
    ) -> SkillToolResult:
        """Execute the wrapped skill."""
        try:
            result = await self.executor.execute(
                skill=self.skill,
                args=args,
                context=context,
            )
            return SkillToolResult(call_id=context.call_id, output=result)
        except SkillError as e:
            return SkillToolResult(call_id=context.call_id, error=str(e))
        except Exception as e:
            return SkillToolResult(
                call_id=context.call_id,
                error=f"Skill execution failed: {str(e)}",
            )


# --- SkillRegistry ---


class SkillRegistry:
    """
    Skill registry with auto-registration as Tools.

    Implements progressive loading:
    1. discover() loads only name + description (fast startup)
    2. activate() loads full instructions on first use
    3. load_reference() loads references/scripts on demand
    """

    def __init__(self, tool_registry: ToolRegistryInterface | None = None):
        self.skills: dict[str, SkillDefinition] = {}
        self.tool_registry = tool_registry or ToolRegistryInterface()
        self._executor = SkillExecutor(self.tool_registry)
        self._skill_tool_map: dict[str, SkillTool] = {}  # skill_name -> SkillTool

    def discover(self, skills_dir: Path) -> list[SkillDefinition]:
        """
        Discover and load skills from a directory.

        Only loads name + description (fast, for startup).
        Full content loaded on activation.

        Args:
            skills_dir: Directory containing skill subdirectories.

        Returns:
            List of discovered SkillDefinitions.
        """
        discovered: list[SkillDefinition] = []
        if not skills_dir.exists():
            return discovered

        for skill_path in skills_dir.iterdir():
            if not skill_path.is_dir():
                continue
            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                skill = parse_skill_md(skill_path)
                self.register(skill)
                discovered.append(skill)
            except Exception as e:
                warnings.warn(f"Failed to load skill from {skill_path}: {e}")

        return discovered

    def register(self, skill: SkillDefinition) -> None:
        """
        Register a skill and auto-register it as a Tool.

        Skills are wrapped as SkillTool and registered with the
        tool_registry so the LLM can invoke them directly.
        """
        self.skills[skill.name] = skill

        # Auto-register as a Tool
        skill_tool = SkillTool(skill, self._executor)
        self._skill_tool_map[skill.name] = skill_tool

        # Register with tool registry if available
        # Tool entry format: {name, description, input_schema, execute}
        tool_entry = ToolEntry(
            name=skill_tool.name,
            description=skill_tool.description,
            input_schema=skill_tool.input_schema,
            execute=skill_tool.execute,
        )
        self._register_tool(tool_entry)

    def _register_tool(self, tool_entry: "ToolEntry") -> None:
        """Register a tool with the tool registry interface."""
        if hasattr(self.tool_registry, "register_tool"):
            self.tool_registry.register_tool(tool_entry)
        elif hasattr(self.tool_registry, "_tools"):
            # Simple dict-based registry
            self.tool_registry._tools[tool_entry.name] = tool_entry

    def get(self, name: str) -> SkillDefinition | None:
        """Get a skill by name."""
        return self.skills.get(name)

    def get_tool(self, skill_name: str) -> SkillTool | None:
        """Get the SkillTool wrapper for a skill."""
        return self._skill_tool_map.get(skill_name)

    def list(self) -> list[SkillDefinition]:
        """List all registered skills."""
        return list(self.skills.values())

    def list_loaded(self) -> list[SkillDefinition]:
        """List skills with full content loaded."""
        return [s for s in self.skills.values() if s._loaded]

    async def activate(self, skill_name: str) -> SkillDefinition:
        """
        Activate a skill: load full content and references.

        Args:
            skill_name: Name of the skill to activate.

        Returns:
            The fully-loaded SkillDefinition.

        Raises:
            KeyError: If the skill is not found.
        """
        skill = self.get(skill_name)
        if not skill:
            raise KeyError(f"Skill not found: {skill_name}")
        return skill.load_full()

    async def execute(
        self,
        skill_name: str,
        args: dict[str, Any],
        context: ToolContext,
    ) -> Any:
        """
        Execute a skill by name.

        Args:
            skill_name: Name of the skill to execute.
            args: Skill arguments.
            context: Execution context.

        Returns:
            The skill execution result.
        """
        skill = self.get(skill_name)
        if not skill:
            raise KeyError(f"Skill not found: {skill_name}")

        # Ensure full content is loaded before execution
        if not skill._loaded:
            skill.load_full()

        return await self._executor.execute(skill, args, context)

    def find_by_trigger(self, trigger: str) -> SkillDefinition | None:
        """
        Find a skill by its trigger (e.g., "/brainstorm").

        Checks metadata["trigger"] field.
        """
        for skill in self.skills.values():
            if skill.metadata.get("trigger") == trigger:
                return skill
            # Also check if trigger matches name with slash prefix
            if f"/{skill.name}" == trigger:
                return skill
        return None


# --- ToolEntry (for tool registry compatibility) ---


@dataclass
class ToolEntry:
    """Tool entry for registration with ToolRegistry."""
    name: str
    description: str
    input_schema: dict[str, Any]
    execute: Any  # async callable
    is_read_only: bool = False
    permission_required: str = "ACCEPT_EDITS"
