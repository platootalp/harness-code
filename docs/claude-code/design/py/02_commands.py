"""
命令系统 Python 实现

展示 Claude Code 命令系统的核心设计模式在 Python 中的实现：
- 命令类型层次
- 斜杠命令解析
- 命令执行流程
- 工具限制机制
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    TypeVar,
    Generic,
    Protocol,
    Awaitable,
)
from functools import wraps
import importlib.util


# =============================================================================
# 1. 命令来源
# =============================================================================

class CommandSource(str, Enum):
    COMMANDS_DEPRECATED = "commands_DEPRECATED"
    SKILLS = "skills"
    PLUGIN = "plugin"
    MANAGED = "managed"
    BUNDLED = "bundled"
    MCP = "mcp"


class CommandAvailability(str, Enum):
    CLAUDE_AI = "claude-ai"
    CONSOLE = "console"


# =============================================================================
# 2. 命令类型
# =============================================================================

class CommandType(str, Enum):
    PROMPT = "prompt"      # 技能类型命令
    LOCAL = "local"        # 简单本地命令
    LOCAL_JSX = "local-jsx"  # UI 命令


# =============================================================================
# 3. 命令结果类型
# =============================================================================

@dataclass
class LocalCommandResult:
    """Local 命令结果"""
    type: str  # 'text', 'compact', 'skip'
    value: Optional[str] = None
    compaction_result: Optional[Any] = None
    display_text: Optional[str] = None


# =============================================================================
# 4. 命令基类
# =============================================================================

@dataclass
class CommandBase:
    """命令基础属性"""
    name: str
    description: str
    aliases: List[str] = field(default_factory=list)
    is_enabled: Callable[[], bool] = field(default_factory=lambda: True)
    is_hidden: bool = False
    user_invokable: bool = True  # 是否允许 /command 语法
    argument_hint: Optional[str] = None
    when_to_use: Optional[str] = None
    availability: List[CommandAvailability] = field(default_factory=list)
    version: Optional[str] = None
    is_mcp: bool = False
    disable_model_invocation: bool = False
    loaded_from: CommandSource = CommandSource.BUNDLED
    kind: Optional[str] = None
    immediate: bool = False
    is_sensitive: bool = False


@dataclass
class PromptCommand(CommandBase):
    """Prompt 命令 - 等价于 TypeScript 的 PromptCommand"""
    type: CommandType = CommandType.PROMPT
    progress_message: str = ""
    content_length: int = 0
    arg_names: Optional[List[str]] = None
    allowed_tools: Optional[List[str]] = None  # 工具白名单
    model: Optional[str] = None
    disable_non_interactive: bool = False
    source: str = "bundled"
    hooks: Optional[Dict[str, Any]] = None
    skill_root: Optional[str] = None
    context: str = "inline"  # 'inline' or 'fork'
    agent: Optional[str] = None
    effort: Optional[str] = None
    paths: Optional[List[str]] = None  # 条件激活的文件模式

    async def get_prompt_for_command(
        self,
        args: str,
        context: 'ToolUseContext'
    ) -> List[Dict[str, Any]]:
        """获取命令的提示内容 - 子类实现"""
        raise NotImplementedError


@dataclass
class LocalCommand(CommandBase):
    """Local 命令 - 等价于 TypeScript 的 LocalCommand"""
    type: CommandType = CommandType.LOCAL
    supports_non_interactive: bool = True
    _call_fn: Optional[Callable] = None

    async def call(
        self,
        args: str,
        context: 'ToolUseContext'
    ) -> LocalCommandResult:
        """执行本地命令"""
        if self._call_fn:
            return await self._call_fn(args, context)
        return LocalCommandResult(type="text", value="Not implemented")


@dataclass
class LocalJSXCommand(CommandBase):
    """Local JSX 命令 - 等价于 TypeScript 的 LocalJSXCommand"""
    type: CommandType = CommandType.LOCAL_JSX
    _component_loader: Optional[Callable] = None

    async def load(self) -> Any:
        """懒加载组件"""
        if self._component_loader:
            return await self._component_loader()
        return None


# Union 类型
Command = PromptCommand | LocalCommand | LocalJSXCommand


# =============================================================================
# 5. 斜杠命令解析
# =============================================================================

@dataclass
class ParsedSlashCommand:
    """解析后的斜杠命令"""
    command_name: str
    args: str
    is_mcp: bool = False


def parse_slash_command(input_str: str) -> Optional[ParsedSlashCommand]:
    """
    解析斜杠命令输入

    等价于 TypeScript 的 parseSlashCommand()

    示例:
        "/commit -m 'fix bug'" → ParsedSlashCommand(
            command_name='commit',
            args="-m 'fix bug'",
            is_mcp=False
        )
        "/mcp:tool (MCP) arg" → ParsedSlashCommand(
            command_name='mcp:tool (MCP)',
            args='arg',
            is_mcp=True
        )
    """
    trimmed = input_str.strip()

    if not trimmed.startswith('/'):
        return None

    without_slash = trimmed[1:]

    # 按空白分割
    words = without_slash.split()

    if not words:
        return None

    command_name = words[0]
    is_mcp = False
    args_start_index = 1

    # 检查 MCP 命令格式: "/mcp:tool (MCP) arg1 arg2"
    if len(words) > 1 and words[1] == '(MCP)':
        command_name = command_name + ' (MCP)'
        is_mcp = True
        args_start_index = 2

    args = ' '.join(words[args_start_index:]) if args_start_index < len(words) else ''

    return ParsedSlashCommand(
        command_name=command_name,
        args=args,
        is_mcp=is_mcp
    )


# =============================================================================
# 6. 命令注册表
# =============================================================================

class CommandRegistry:
    """命令注册表 - 单例模式"""

    _instance: Optional['CommandRegistry'] = None
    _commands: Dict[str, Command] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'CommandRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, command: Command) -> None:
        """注册命令"""
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command

    def get(self, name: str) -> Optional[Command]:
        """获取命令"""
        return self._commands.get(name)

    def find(self, name: str) -> Optional[Command]:
        """查找命令 (按名称或别名)"""
        return self._commands.get(name)

    def get_all(self) -> List[Command]:
        """获取所有命令"""
        return list(self._commands.values())

    def get_enabled(self) -> List[Command]:
        """获取已启用的命令"""
        return [
            cmd for cmd in self._commands.values()
            if cmd.is_enabled()
        ]

    def clear(self) -> None:
        """清空注册表"""
        self._commands.clear()


# =============================================================================
# 7. 命令执行器
# =============================================================================

@dataclass
class CommandResult:
    """命令执行结果"""
    command: Command
    messages: List[Dict[str, Any]] = field(default_factory=list)
    should_query: bool = True  # 是否需要发送到模型
    allowed_tools: Optional[List[str]] = None
    result_text: Optional[str] = None


class CommandExecutor:
    """命令执行器"""

    def __init__(self, context: 'ToolUseContext'):
        self.context = context
        self.registry = CommandRegistry.get_instance()

    async def execute(
        self,
        input_str: str,
        preceding_input_blocks: List[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        执行斜杠命令

        等价于 TypeScript 的 processSlashCommand()
        """
        preceding_input_blocks = preceding_input_blocks or []

        # 1. 解析输入
        parsed = parse_slash_command(input_str)
        if not parsed:
            raise ValueError("Not a slash command")

        # 2. 查找命令
        command = self.registry.find(parsed.command_name)
        if not command:
            raise ValueError(f"Command not found: {parsed.command_name}")

        # 3. 验证调用权限
        if not command.user_invokable and not parsed.is_mcp:
            raise ValueError(
                f"Command not user-invocable: {parsed.command_name}"
            )

        # 4. 检查启用状态
        if not command.is_enabled():
            raise ValueError(f"Command disabled: {parsed.command_name}")

        # 5. 根据类型执行
        if isinstance(command, LocalJSXCommand):
            return await self._execute_local_jsx(command, parsed.args)

        elif isinstance(command, PromptCommand):
            return await self._execute_prompt(command, parsed.args)

        elif isinstance(command, LocalCommand):
            return await self._execute_local(command, parsed.args)

        else:
            raise ValueError(f"Unknown command type: {type(command)}")

    async def _execute_prompt(
        self,
        command: PromptCommand,
        args: str
    ) -> CommandResult:
        """执行 Prompt 命令"""

        # Fork 模式
        if command.context == "fork":
            return await self._execute_forked(command, args)

        # Inline 模式
        return await self._execute_inline(command, args)

    async def _execute_inline(
        self,
        command: PromptCommand,
        args: str
    ) -> CommandResult:
        """Inline 执行 - 直接获取 prompt 内容"""
        # 应用工具限制
        context = self.context
        if command.allowed_tools:
            context = self._apply_tool_restrictions(
                self.context,
                command.allowed_tools
            )

        # 获取 prompt 内容
        content_blocks = await command.get_prompt_for_command(args, context)

        return CommandResult(
            command=command,
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": args}]
                },
                *content_blocks
            ],
            should_query=True,
            allowed_tools=command.allowed_tools
        )

    async def _execute_forked(
        self,
        command: PromptCommand,
        args: str
    ) -> CommandResult:
        """Fork 执行 - 在子 Agent 中执行"""
        # 构建子 Agent 配置
        agent_config = {
            "agent_type": command.agent or "GeneralPurpose",
            "tools": command.allowed_tools,
            "permission_mode": "auto",
            "isolation": "worktree"
        }

        # 获取初始 prompt
        content_blocks = await command.get_prompt_for_command(args, self.context)

        # 派生子 Agent (简化实现)
        # 在实际实现中，这里会调用 run_agent()
        result_messages = await self._run_forked_agent(
            agent_config,
            content_blocks
        )

        return CommandResult(
            command=command,
            messages=result_messages,
            should_query=False
        )

    async def _run_forked_agent(
        self,
        config: Dict[str, Any],
        initial_messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """运行 Forked Agent (简化实现)"""
        # 这里简化处理，实际会调用完整的 Agent 系统
        await asyncio.sleep(0.1)
        return initial_messages

    async def _execute_local(
        self,
        command: LocalCommand,
        args: str
    ) -> CommandResult:
        """执行 Local 命令"""
        result = await command.call(args, self.context)

        return CommandResult(
            command=command,
            messages=[],
            should_query=False,
            result_text=result.value
        )

    async def _execute_local_jsx(
        self,
        command: LocalJSXCommand,
        args: str
    ) -> CommandResult:
        """执行 Local JSX 命令"""
        # 懒加载组件
        component = await command.load()

        return CommandResult(
            command=command,
            messages=[],
            should_query=False,
            result_text=f"JSX Component: {component}"
        )

    def _apply_tool_restrictions(
        self,
        context: 'ToolUseContext',
        allowed_tools: List[str]
    ) -> 'ToolUseContext':
        """应用工具限制"""
        # 创建受限的权限上下文
        restricted_context = ToolUseContext(
            tools=context.tools,
            abort_controller=context.abort_controller,
            read_file_state=context.read_file_state,
            callbacks=context.callbacks,
            tool_permission_context=ToolPermissionContext(
                mode=context.tool_permission_context.mode,
                rules=context.tool_permission_context.rules,
                always_allow_rules=[
                    *context.tool_permission_context.always_allow_rules,
                    *allowed_tools  # 添加命令级别的工具白名单
                ]
            ),
            session_id=context.session_id
        )

        return restricted_context


# =============================================================================
# 8. 工具上下文 (简化版)
# =============================================================================

@dataclass
class ToolUseContext:
    """工具执行上下文"""
    tools: List[Any] = field(default_factory=list)
    abort_controller: Any = None
    read_file_state: Dict[str, Any] = field(default_factory=dict)
    callbacks: Optional[Any] = None
    tool_permission_context: Optional['ToolPermissionContext'] = None
    session_id: Optional[str] = None


@dataclass
class ToolPermissionContext:
    """工具权限上下文"""
    mode: str = "auto"
    rules: List[Any] = field(default_factory=list)
    always_allow_rules: List[str] = field(default_factory=list)


# =============================================================================
# 9. 内置命令示例
# =============================================================================

class CommitCommand(PromptCommand):
    """Git Commit 命令"""

    def __init__(self):
        super().__init__(
            name="commit",
            description="Create a git commit with a descriptive message",
            aliases=["ci"],
            argument_hint="[-m <message>]",
            when_to_use="When you want to commit staged changes",
            allowed_tools=[
                "Bash(git status:*)",
                "Bash(git add:*)",
                "Bash(git commit:*)",
                "Read(*)",
                "Glob(*)"
            ],
            progress_message="Creating commit..."
        )

    async def get_prompt_for_command(
        self,
        args: str,
        context: ToolUseContext
    ) -> List[Dict[str, Any]]:
        # 解析参数
        message = self._extract_commit_message(args)

        return [{
            "type": "text",
            "text": (
                "Create a git commit. Use git status to see staged files.\n"
                f"Commit message: {message or 'Provide a descriptive message'}\n"
                "After staging files, use: git commit -m '<message>'"
            )
        }]

    def _extract_commit_message(self, args: str) -> Optional[str]:
        """提取 commit message"""
        # 简化实现
        if "-m" in args:
            parts = args.split("-m", 1)
            if len(parts) > 1:
                return parts[1].strip().strip("'\"")
        return None


class ClearCommand(LocalCommand):
    """Clear 命令 - 清空对话"""

    def __init__(self):
        super().__init__(
            name="clear",
            description="Clear the conversation history",
            aliases=["cl"],
            user_invokable=True,
            supports_non_interactive=True
        )

    async def call(
        self,
        args: str,
        context: ToolUseContext
    ) -> LocalCommandResult:
        # 清空消息 (简化)
        return LocalCommandResult(
            type="text",
            value="Conversation cleared"
        )


class HelpCommand(LocalJSXCommand):
    """Help 命令 - 显示帮助"""

    def __init__(self):
        super().__init__(
            name="help",
            description="Show help information",
            aliases=["h", "?"],
            user_invokable=True
        )

    async def load(self) -> str:
        # 懒加载帮助组件
        return "HelpScreenComponent"


# =============================================================================
# 10. 示例用法
# =============================================================================

async def main():
    """示例用法"""

    # 创建命令
    commit_cmd = CommitCommand()
    clear_cmd = ClearCommand()
    help_cmd = HelpCommand()

    # 注册命令
    registry = CommandRegistry.get_instance()
    registry.register(commit_cmd)
    registry.register(clear_cmd)
    registry.register(help_cmd)

    print(f"Registered commands: {[cmd.name for cmd in registry.get_all()]}")

    # 解析命令
    tests = [
        "/commit -m 'fix bug'",
        "/clear",
        "/help",
        "not a command",
    ]

    for test in tests:
        result = parse_slash_command(test)
        print(f"Input: '{test}' -> {result}")


if __name__ == "__main__":
    asyncio.run(main())
