"""
技能系统 Python 实现

展示 Claude Code 技能系统的核心设计模式在 Python 中的实现：
- 技能定义类型
- Frontmatter 解析
- 工具限制机制
- 条件激活
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)


# =============================================================================
# 1. 技能来源
# =============================================================================

class SkillSource(str, Enum):
    """技能来源"""
    BUNDLED = "bundled"
    MANAGED = "managed"
    SKILLS = "skills"        # ~/.claude/skills/
    PROJECT = "project"     # .claude/skills/
    PLUGIN = "plugin"
    MCP = "mcp"


# =============================================================================
# 2. 技能定义类型
# =============================================================================

@dataclass
class SkillDefinition:
    """
    技能定义

    等价于 TypeScript 的 BundledSkillDefinition
    """
    # 基础信息
    name: str
    description: str
    aliases: List[str] = field(default_factory=list)
    when_to_use: Optional[str] = None
    argument_hint: Optional[str] = None

    # 工具限制
    allowed_tools: Optional[List[str]] = None

    # 模型控制
    model: Optional[str] = None
    disable_model_invocation: bool = False

    # 调用控制
    user_invocable: bool = True
    is_enabled: Optional[Callable[[], bool]] = None

    # 生命周期钩子
    hooks: Optional[Dict[str, Any]] = None

    # 执行上下文
    context: str = "inline"  # 'inline' or 'fork'
    agent: Optional[str] = None
    effort: Optional[str] = None

    # 条件激活
    paths: Optional[List[str]] = None  # glob 模式

    # 资源文件
    files: Optional[Dict[str, str]] = None

    # 来源
    source: SkillSource = SkillSource.BUNDLED
    skill_root: Optional[str] = None


@dataclass
class SkillFrontmatter:
    """技能 Frontmatter"""
    name: Optional[str] = None
    description: Optional[str] = None
    when_to_use: Optional[str] = None
    argument_hint: Optional[str] = None
    allowed_tools: Optional[List[str]] = None
    model: Optional[str] = None
    disable_model_invocation: bool = False
    user_invocable: Optional[bool] = None
    is_enabled: Optional[bool] = None
    context: Optional[str] = None
    agent: Optional[str] = None
    effort: Optional[str] = None
    paths: Optional[List[str]] = None


# =============================================================================
# 3. Frontmatter 解析
# =============================================================================

def parse_frontmatter(content: str) -> Tuple[SkillFrontmatter, str]:
    """
    解析 Frontmatter

    等价于 TypeScript 的 parseFrontmatter()

    支持 YAML frontmatter:
    ---
    name: commit
    description: Create a git commit
    allowedTools:
      - Bash(git *)
    ---
    """
    # 检测 frontmatter
    match = re.match(r'^---\n([\s\S]*?)\n---\n*', content)

    if not match:
        return SkillFrontmatter(), content

    yaml_str = match.group(1)
    body = content[match.end():]

    # 解析 YAML (简化实现)
    frontmatter = _parse_yaml(yaml_str)

    return SkillFrontmatter(**frontmatter), body


def _parse_yaml(yaml_str: str) -> Dict[str, Any]:
    """
    简化的 YAML 解析

    实际应使用 pyyaml 库
    """
    result: Dict[str, Any] = {}

    for line in yaml_str.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            # 去除引号
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            result[key] = value

    return result


# =============================================================================
# 4. Shell 命令执行
# =============================================================================

async def execute_shell_commands(
    prompt: str,
    cwd: str = None
) -> str:
    """
    执行 shell 命令

    语法: !{command}

    等价于 TypeScript 的 executeShellCommands()
    """
    result_lines: List[str] = []

    for line in prompt.split('\n'):
        # 检测 shell 命令
        match = re.match(r'^!\{(.*)\}$', line.strip())

        if match:
            command = match.group(1).strip()

            try:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd
                )
                stdout, stderr = await proc.communicate()

                output = stdout.decode() if stdout else stderr.decode()
                result_lines.append(output.strip())
            except Exception as e:
                result_lines.append(f"[Command failed: {str(e)}]")
        else:
            result_lines.append(line)

    return '\n'.join(result_lines)


# =============================================================================
# 5. 变量替换
# =============================================================================

def substitute_variables(
    content: str,
    variables: Dict[str, str]
) -> str:
    """
    替换变量

    支持的变量:
    - ${CLAUDE_SKILL_DIR} - 技能目录
    - ${CLAUDE_SESSION_ID} - 会话 ID
    - ${1}, ${2}... - 位置参数
    """
    result = content

    # 替换预定义变量
    for var_name, var_value in variables.items():
        result = result.replace(f'${{{var_name}}}', var_value)

    # 替换位置参数 ${1}, ${2}...
    # 需要调用者提供 arg_parts

    return result


def substitute_positional_args(
    content: str,
    args: str
) -> str:
    """替换位置参数"""
    arg_parts = args.split()

    def replace_match(match):
        index = int(match.group(1))
        return arg_parts[index - 1] if index <= len(arg_parts) else ''

    return re.sub(r'\$\{(\d+)\}', replace_match, content)


# =============================================================================
# 6. 技能命令创建
# =============================================================================

@dataclass
class ToolUseContext:
    """工具使用上下文"""
    session_id: Optional[str] = None
    cwd: Optional[str] = None


class SkillCommand:
    """
    技能命令

    等价于 TypeScript 生成的技能命令
    """

    def __init__(self, definition: SkillDefinition):
        self._definition = definition

    @property
    def name(self) -> str:
        return self._definition.name

    @property
    def description(self) -> str:
        return self._definition.description

    @property
    def allowed_tools(self) -> Optional[List[str]]:
        return self._definition.allowed_tools

    @property
    def context(self) -> str:
        return self._definition.context

    @property
    def agent(self) -> Optional[str]:
        return self._definition.agent

    async def get_prompt_for_command(
        self,
        args: str,
        context: ToolUseContext
    ) -> List[Dict[str, Any]]:
        """
        获取命令的提示内容

        等价于 TypeScript 的 getPromptForCommand()
        """
        # 读取技能文件
        skill_path = self._get_skill_path()
        if not skill_path or not os.path.exists(skill_path):
            return [{'type': 'text', 'text': f'Error: Skill file not found'}]

        with open(skill_path, 'r') as f:
            content = f.read()

        # 解析 frontmatter
        frontmatter, body = parse_frontmatter(content)

        # 变量
        variables = {
            'CLAUDE_SKILL_DIR': os.path.dirname(skill_path),
            'CLAUDE_SESSION_ID': context.session_id or 'unknown',
        }

        # 替换变量
        prompt = substitute_variables(body, variables)

        # 替换位置参数
        prompt = substitute_positional_args(prompt, args)

        # 执行 shell 命令
        prompt = await execute_shell_commands(prompt, context.cwd)

        # 添加参数
        if args:
            prompt = f"{prompt}\n\nUser arguments: {args}"

        return [{'type': 'text', 'text': prompt}]

    def _get_skill_path(self) -> Optional[str]:
        """获取技能文件路径"""
        if self._definition.skill_root:
            return os.path.join(
                self._definition.skill_root,
                f"{self._definition.name}.md"
            )
        return None


# =============================================================================
# 7. 工具限制机制
# =============================================================================

@dataclass
class ToolPermissionContext:
    """工具权限上下文"""
    mode: str = "auto"
    rules: List[Dict[str, Any]] = field(default_factory=list)
    always_allow_rules: List[str] = field(default_factory=list)


class ToolRestriction:
    """
    工具限制

    等价于 TypeScript 的 createToolRestrictedContext()
    """

    @staticmethod
    def apply(
        original_context: ToolUseContext,
        allowed_tools: List[str]
    ) -> ToolUseContext:
        """
        创建受限的工具上下文

        等价于 TypeScript 的 createToolRestrictedContext()
        """
        # 合并工具白名单
        return ToolUseContext(
            session_id=original_context.session_id,
            cwd=original_context.cwd
        )


def matches_tool_pattern(tool_name: str, pattern: str) -> bool:
    """
    匹配工具名称模式

    等价于 TypeScript 的 matchesToolPattern()

    模式格式:
    - "Bash" - 精确匹配
    - "Bash(git *)" - 带参数匹配
    """
    # 解析模式
    if '(' in pattern:
        name_part, arg_part = pattern.split('(', 1)
        name_part = name_part.strip()
        arg_part = arg_part.rstrip(')').strip()

        if not glob_match(tool_name, name_part):
            return False

        if arg_part:
            # 简化: 不检查参数匹配
            return True

        return True
    else:
        return glob_match(tool_name, pattern)


def glob_match(text: str, pattern: str) -> bool:
    """Glob 模式匹配"""
    # 将 glob 转换为正则
    regex = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
    return bool(re.match(f'^{regex}$', text))


# =============================================================================
# 8. 条件激活
# =============================================================================

class ConditionalSkill:
    """条件技能"""

    def __init__(
        self,
        name: str,
        paths: List[str],
        skill: SkillCommand
    ):
        self.name = name
        self.paths = paths
        self.skill = skill


def should_activate_skill(
    skill: ConditionalSkill,
    touched_paths: List[str]
) -> bool:
    """
    检查技能是否应该激活

    等价于 TypeScript 的 shouldActivateSkill()
    """
    for touched_path in touched_paths:
        for pattern in skill.paths:
            if path_matches_glob(touched_path, pattern):
                return True

    return False


def path_matches_glob(path: str, pattern: str) -> bool:
    """
    路径 glob 匹配

    简化实现
    """
    # 转换 glob 模式为正则
    # **/*.ts -> .*\.ts
    regex_pattern = pattern
    regex_pattern = regex_pattern.replace('**/', '.*/')
    regex_pattern = regex_pattern.replace('**', '.*')
    regex_pattern = regex_pattern.replace('*', '[^/]*')
    regex_pattern = regex_pattern.replace('?', '[^/]')

    return bool(re.match(f'^{regex_pattern}$', path))


async def discover_skill_dirs_for_paths(
    base_dir: str,
    paths: List[str]
) -> List[str]:
    """
    发现技能目录

    等价于 TypeScript 的 discoverSkillDirsForPaths()
    """
    discovered: Set[str] = set()

    for file_path in paths:
        # 从文件所在目录向上查找 .claude/skills/
        dir_path = os.path.dirname(file_path)

        while True:
            skills_dir = os.path.join(dir_path, '.claude', 'skills')

            if os.path.isdir(skills_dir):
                discovered.add(skills_dir)

            # 到达 base_dir 或根目录停止
            if dir_path == base_dir or dir_path == os.path.dirname(dir_path):
                break

            dir_path = os.path.dirname(dir_path)

    return list(discovered)


# =============================================================================
# 9. 技能加载
# =============================================================================

async def load_skills_from_dir(
    dir_path: str,
    source: SkillSource = SkillSource.SKILLS
) -> List[SkillCommand]:
    """
    从目录加载技能

    等价于 TypeScript 的 loadSkillsDir()
    """
    if not os.path.isdir(dir_path):
        return []

    skills: List[SkillCommand] = []

    # 遍历 .md 文件
    for root, dirs, files in os.walk(dir_path):
        # 忽略 node_modules
        dirs[:] = [d for d in dirs if d != 'node_modules']

        for file in files:
            if not file.endswith('.md'):
                continue

            file_path = os.path.join(root, file)

            # 读取文件
            with open(file_path, 'r') as f:
                content = f.read()

            # 解析 frontmatter
            frontmatter, body = parse_frontmatter(content)

            # 创建技能定义
            name = frontmatter.name or os.path.splitext(file)[0]

            definition = SkillDefinition(
                name=name,
                description=frontmatter.description or '',
                when_to_use=frontmatter.when_to_use,
                argument_hint=frontmatter.argument_hint,
                allowed_tools=frontmatter.allowed_tools,
                model=frontmatter.model,
                disable_model_invocation=frontmatter.disable_model_invocation,
                user_invocable=frontmatter.user_invocable if frontmatter.user_invocable is not None else True,
                context=frontmatter.context or 'inline',
                agent=frontmatter.agent,
                effort=frontmatter.effort,
                paths=frontmatter.paths,
                source=source,
                skill_root=os.path.dirname(file_path)
            )

            skills.append(SkillCommand(definition))

    return skills


# =============================================================================
# 10. 技能注册表
# =============================================================================

class SkillRegistry:
    """技能注册表"""

    _instance: Optional['SkillRegistry'] = None
    _skills: Dict[str, SkillCommand] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'SkillRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, skill: SkillCommand) -> None:
        """注册技能"""
        self._skills[skill.name] = skill
        for alias in skill._definition.aliases:
            self._skills[alias] = skill

    def get(self, name: str) -> Optional[SkillCommand]:
        """获取技能"""
        return self._skills.get(name)

    def get_all(self) -> List[SkillCommand]:
        """获取所有技能"""
        return list(self._skills.values())

    def clear(self) -> None:
        """清空注册表"""
        self._skills.clear()


# =============================================================================
# 11. 示例技能文件
# =============================================================================

SKILL_EXAMPLE = '''---
name: commit
description: Create a git commit with a descriptive message
whenToUse: When you want to commit staged changes
argumentHint: [-m <message>]
allowedTools:
  - Bash(git status:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Read(*)
  - Glob(*)
---

# Git Commit Skill

Create a thoughtful git commit with the following steps:

1. Run \`git status\` to see staged files
2. Review the changes to understand what was modified
3. Create a descriptive commit message

Example usage: /commit -m "fix: resolve authentication bug"
'''


# =============================================================================
# 12. 示例用法
# =============================================================================

async def main():
    """示例用法"""

    # 1. 解析 frontmatter
    frontmatter, body = parse_frontmatter(SKILL_EXAMPLE)
    print(f"Name: {frontmatter.name}")
    print(f"Description: {frontmatter.description}")
    print(f"Allowed tools: {frontmatter.allowed_tools}")

    # 2. 变量替换
    content = "Skill dir: ${CLAUDE_SKILL_DIR}\nSession: ${CLAUDE_SESSION_ID}"
    variables = {
        'CLAUDE_SKILL_DIR': '/home/user/.claude/skills',
        'CLAUDE_SESSION_ID': 'sess-123'
    }
    result = substitute_variables(content, variables)
    print(f"\nVariable substitution:\n{result}")

    # 3. 位置参数替换
    content = "Arg 1: ${1}\nArg 2: ${2}\nArg 3: ${3}"
    result = substitute_positional_args(content, "first second")
    print(f"\nPositional args substitution:\n{result}")

    # 4. 工具模式匹配
    tests = [
        ("Bash", "Bash"),
        ("Bash", "Read"),
        ("Bash(git commit)", "Bash(git *)"),
        ("Read", "Read(*.py)"),
    ]

    print("\nTool pattern matching:")
    for tool_name, pattern in tests:
        result = matches_tool_pattern(tool_name, pattern)
        print(f"  {tool_name} vs {pattern}: {result}")

    # 5. 条件激活
    skill = ConditionalSkill(
        name="python-helper",
        paths=["**/*.py", "**/*.pyi"],
        skill=SkillCommand(SkillDefinition(
            name="python-helper",
            description="Python helper skill"
        ))
    )

    test_paths = ["src/main.py", "src/utils.py", "src/app.js"]
    print(f"\nConditional activation for {skill.name}:")
    for path in test_paths:
        result = should_activate_skill(skill, [path])
        print(f"  {path}: {result}")

    # 6. 创建技能
    definition = SkillDefinition(
        name="test",
        description="Test skill",
        context="inline",
        skill_root="/tmp"
    )

    # 保存示例技能文件
    import tempfile
    temp_dir = tempfile.mkdtemp()
    skill_path = os.path.join(temp_dir, "test.md")
    with open(skill_path, 'w') as f:
        f.write(SKILL_EXAMPLE)

    definition.skill_root = temp_dir
    skill_cmd = SkillCommand(definition)

    # 执行技能
    context = ToolUseContext(
        session_id="sess-456",
        cwd="/tmp"
    )

    prompt = await skill_cmd.get_prompt_for_command("test args", context)
    print(f"\nSkill prompt:\n{prompt}")


if __name__ == "__main__":
    asyncio.run(main())
