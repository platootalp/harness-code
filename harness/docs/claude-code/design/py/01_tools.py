"""
工具系统 Python 实现

展示 Claude Code 工具系统的核心设计模式在 Python 中的实现：
- 工厂模式 (buildTool)
- 权限检查
- 并发控制
- Zod Schema 的 Python 等价物 (Pydantic)
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
    Protocol,
    runtime_checkable,
)
from functools import wraps
import re


# =============================================================================
# 1. 类型系统 - Pydantic 等价于 Zod
# =============================================================================

from pydantic import BaseModel, Field, ValidationError
from pydantic.fields import FieldInfo


def lazy_schema(schema_factory: Callable[[], type[BaseModel]]):
    """
    懒加载 Schema - 避免循环导入时的解析延迟

    等价于 TypeScript 的 lazySchema()
    """
    _schema: type[BaseModel] | None = None

    class LazyModel(BaseModel):
        @classmethod
        def model_validate(cls, data, **kwargs):
            nonlocal _schema
            if _schema is None:
                _schema = schema_factory()
            return _schema.model_validate(data, **kwargs)

        @classmethod
        def parse_obj(cls, data: Dict[str, Any]):
            nonlocal _schema
            if _schema is None:
                _schema = schema_factory()
            return _schema.parse_obj(data)

    return LazyModel


# =============================================================================
# 2. 权限决策类型
# =============================================================================

class PermissionBehavior(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    PASSTHROUGH = "passthrough"


@dataclass
class PermissionDecision:
    behavior: PermissionBehavior
    message: Optional[str] = None
    updated_input: Optional[Dict[str, Any]] = None
    decision_reason: Optional[str] = None


# =============================================================================
# 3. 工具结果类型
# =============================================================================

@dataclass
class ToolResultContent:
    type: str
    text: Optional[str] = None
    tool_use_id: Optional[str] = None


@dataclass
class ToolResult:
    content: List[ToolResultContent]
    suppressed: bool = False
    error: Optional[str] = None


# =============================================================================
# 4. 工具基类 - 工厂模式
# =============================================================================

T = TypeVar('T')
InputT = TypeVar('InputT', bound=BaseModel)
OutputT = TypeVar('OutputT')
ProgressT = TypeVar('ProgressT')


class ToolCallbacks(Protocol):
    """工具执行回调协议"""
    def set_tool_jsx(self, tool_use_id: str, jsx: Any) -> None: ...
    def on_progress(self, progress: Any) -> None: ...


@dataclass
class ToolUseContext:
    """工具执行上下文"""
    tools: List['BaseTool']
    abort_controller: 'AbortController'
    read_file_state: Dict[str, 'FileState']
    callbacks: Optional[ToolCallbacks] = None

    # 权限上下文
    tool_permission_context: 'ToolPermissionContext' = field(
        default_factory=lambda: ToolPermissionContext()
    )

    # 会话信息
    session_id: Optional[str] = None
    access_token: Optional[str] = None


@dataclass
class ToolPermissionContext:
    """工具权限上下文"""
    mode: str = "auto"  # auto, bypass, acceptEdits, plan, review
    rules: List['PermissionRule'] = field(default_factory=list)
    always_allow_rules: List[str] = field(default_factory=list)


@dataclass
class PermissionRule:
    """权限规则"""
    pattern: str  # e.g., "Bash(git *)" or "Read(*.env)"
    behavior: PermissionBehavior
    reason: Optional[str] = None


@dataclass
class FileState:
    """文件状态"""
    path: str
    exists: bool = True
    last_read: Optional[float] = None
    last_modified: Optional[float] = None


# =============================================================================
# 5. 工具默认配置
# =============================================================================

@dataclass
class ToolDefaults:
    """工具默认配置 - 等价于 TypeScript 的 TOOL_DEFAULTS"""
    is_enabled: Callable[[], bool] = field(default_factory=lambda: True)
    is_concurrency_safe: Callable[[Any], bool] = field(
        default_factory=lambda _: False  # 保守策略：默认非并发安全
    )
    is_read_only: Callable[[Any], bool] = field(default_factory=lambda _: False)
    is_destructive: Callable[[Any], bool] = field(default_factory=lambda _: False)
    max_result_size_chars: int = 50000

    def check_permissions(
        self,
        input_data: Any,
        context: ToolUseContext
    ) -> PermissionDecision:
        return PermissionDecision(behavior=PermissionBehavior.ALLOW)

    def get_path(self, input_data: Any) -> Optional[str]:
        return None


# =============================================================================
# 6. BaseTool - 工具基类
# =============================================================================

@runtime_checkable
class BaseTool(ABC, Generic[InputT, OutputT, ProgressT]):
    """
    工具基类

    使用泛型和 ABC 实现等价于 TypeScript 的 Tool 接口
    """

    name: str
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    max_result_size_chars: int = 50000

    # Schema (子类设置)
    input_schema: type[BaseModel] = Field(default_factory=lambda: BaseModel)

    # 默认值
    _defaults: ToolDefaults = field(default_factory=ToolDefaults, init=False)

    # 可选方法
    _is_concurrency_safe: Optional[Callable[[InputT], bool]] = None
    _is_read_only: Optional[Callable[[InputT], bool]] = None
    _is_destructive: Optional[Callable[[InputT], bool]] = None
    _validate_input: Optional[Callable[[InputT, ToolUseContext], bool]] = None
    _check_permissions: Optional[
        Callable[[InputT, ToolUseContext], PermissionDecision]
    ] = None
    _get_path: Optional[Callable[[InputT], str | List[str]]] = None

    def __init__(
        self,
        name: str,
        input_schema: type[BaseModel],
        **kwargs
    ):
        self.name = name
        self.input_schema = input_schema
        for key, value in kwargs.items():
            setattr(self, key, value)

    def is_enabled(self) -> bool:
        return getattr(self, '_is_enabled', lambda: True)()

    def is_concurrency_safe(self, input_data: InputT) -> bool:
        if self._is_concurrency_safe:
            return self._is_concurrency_safe(input_data)
        return self._defaults.is_concurrency_safe(input_data)

    def is_read_only(self, input_data: InputT) -> bool:
        if self._is_read_only:
            return self._is_read_only(input_data)
        return self._defaults.is_read_only(input_data)

    def is_destructive(self, input_data: InputT) -> bool:
        if self._is_destructive:
            return self._is_destructive(input_data)
        return self._defaults.is_destructive(input_data)

    async def check_permissions(
        self,
        input_data: InputT,
        context: ToolUseContext
    ) -> PermissionDecision:
        if self._check_permissions:
            return self._check_permissions(input_data, context)
        return self._defaults.check_permissions(input_data, context)

    def get_path(self, input_data: InputT) -> Optional[str]:
        if self._get_path:
            result = self._get_path(input_data)
            return result if isinstance(result, str) else result[0] if result else None
        return self._defaults.get_path(input_data)

    @abstractmethod
    async def call(
        self,
        input_data: InputT,
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Optional[Dict] = None,
        on_progress: Optional[Callable[[ProgressT], None]] = None,
    ) -> ToolResult:
        """工具执行入口 - 子类必须实现"""
        pass

    def render_tool_use_message(
        self,
        input_data: InputT,
        options: Dict[str, Any]
    ) -> str:
        """工具使用的文本表示"""
        return f"{self.name}: {input_data}"

    def render_tool_result_message(
        self,
        content: Any,
        progress_messages: List[Any] = None,
        options: Dict[str, Any] = None
    ) -> str:
        """工具结果的文本表示"""
        if isinstance(content, str):
            return content
        return str(content)


# =============================================================================
# 7. 工具注册表
# =============================================================================

class ToolRegistry:
    """工具注册表 - 单例模式"""

    _instance: Optional['ToolRegistry'] = None
    _tools: Dict[str, 'BaseTool'] = {}
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'ToolRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
        for alias in tool.aliases:
            self._tools[alias] = tool
        self._initialized = True

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def get_all(self) -> List[BaseTool]:
        """获取所有工具"""
        return list(self._tools.values())

    def get_enabled(self) -> List[BaseTool]:
        """获取已启用的工具"""
        return [t for t in self._tools.values() if t.is_enabled()]


# =============================================================================
# 8. 工具工厂函数 - buildTool 等价
# =============================================================================

def build_tool(
    name: str,
    input_schema: type[BaseModel],
    call_fn: Callable,
    description: str = "",
    **kwargs
) -> BaseTool:
    """
    工具工厂函数

    等价于 TypeScript 的 buildTool<D>() 函数
    """

    class ConcreteTool(BaseTool):
        def __init__(self):
            super().__init__(
                name=name,
                input_schema=input_schema,
                description=description,
                **kwargs
            )
            self._call_fn = call_fn

        async def call(
            self,
            input_data: InputT,
            context: ToolUseContext,
            can_use_tool: Callable = None,
            parent_message: Optional[Dict] = None,
            on_progress: Optional[Callable[[ProgressT], None]] = None,
        ) -> ToolResult:
            return await self._call_fn(
                input_data,
                context,
                can_use_tool,
                parent_message,
                on_progress,
            )

    tool = ConcreteTool()
    ToolRegistry.get_instance().register(tool)
    return tool


# =============================================================================
# 9. 权限检查
# =============================================================================

class PermissionChecker:
    """权限检查器"""

    def __init__(self, context: ToolPermissionContext):
        self.context = context

    def check(self, tool_name: str, input_data: Any) -> PermissionDecision:
        """检查工具权限"""
        # 1. 检查绕过模式
        if self.context.mode == "bypass":
            return PermissionDecision(
                behavior=PermissionBehavior.ALLOW,
                decision_reason="bypass_enabled"
            )

        # 2. 检查 always_allow 规则
        for pattern in self.context.always_allow_rules:
            if self._matches_pattern(tool_name, pattern):
                return PermissionDecision(
                    behavior=PermissionBehavior.ALLOW,
                    decision_reason="always_allow_rule"
                )

        # 3. 检查拒绝规则
        for rule in self.context.rules:
            if self._matches_pattern(tool_name, rule.pattern):
                if rule.behavior == PermissionBehavior.DENY:
                    return PermissionDecision(
                        behavior=PermissionBehavior.DENY,
                        message=f"Denied by rule: {rule.reason or rule.pattern}",
                        decision_reason="denied_rule"
                    )

        # 4. 检查询问规则
        for rule in self.context.rules:
            if self._matches_pattern(tool_name, rule.pattern):
                if rule.behavior == PermissionBehavior.ASK:
                    return PermissionDecision(
                        behavior=PermissionBehavior.ASK,
                        message=f"Ask for permission: {rule.reason or rule.pattern}",
                        decision_reason="ask_rule"
                    )

        # 5. 默认询问
        return PermissionDecision(
            behavior=PermissionBehavior.ASK,
            decision_reason="default_ask"
        )

    def _matches_pattern(self, tool_name: str, pattern: str) -> bool:
        """匹配工具名称模式"""
        # 解析模式: "ToolName" 或 "ToolName(arg:*)"
        if '(' not in pattern:
            # 简单名称匹配
            return tool_name == pattern

        # 解析带参数的名称
        name_part, arg_part = pattern.split('(', 1)
        arg_part = arg_part.rstrip(')')

        if not self._glob_match(tool_name, name_part):
            return False

        if arg_part:
            # 需要检查参数匹配 (简化实现)
            return True

        return True

    def _glob_match(self, text: str, pattern: str) -> bool:
        """Glob 模式匹配"""
        # 将 glob 模式转换为正则
        regex = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
        return bool(re.match(f'^{regex}$', text))


# =============================================================================
# 10. 工具执行器
# =============================================================================

class ToolExecutor:
    """工具执行器 - 支持并发控制"""

    def __init__(
        self,
        max_concurrency: int = 10,
        permission_checker: Optional[PermissionChecker] = None
    ):
        self.max_concurrency = max_concurrency
        self.permission_checker = permission_checker

    async def execute(
        self,
        tool_use_blocks: List[Dict[str, Any]],
        context: ToolUseContext
    ) -> List[ToolResult]:
        """
        执行工具调用

        等价于 TypeScript 的 runTools() 函数
        """
        # 1. 分区工具调用 (按并发安全性)
        batches = self._partition_by_concurrency(tool_use_blocks, context)

        results: List[ToolResult] = []

        # 2. 逐批执行
        for batch in batches:
            if batch['is_concurrency_safe']:
                # 并发执行
                batch_results = await self._execute_batch_concurrent(
                    batch['blocks'],
                    context
                )
            else:
                # 串行执行
                batch_results = await self._execute_batch_serial(
                    batch['blocks'],
                    context
                )
            results.extend(batch_results)

        return results

    def _partition_by_concurrency(
        self,
        tool_use_blocks: List[Dict[str, Any]],
        context: ToolUseContext
    ) -> List[Dict[str, Any]]:
        """按并发安全性分区"""
        batches: List[Dict[str, Any]] = []

        for block in tool_use_blocks:
            tool = ToolRegistry.get_instance().get(block['name'])
            if not tool:
                continue

            # 解析输入
            try:
                input_data = tool.input_schema.model_validate(block.get('input', {}))
                is_safe = tool.is_concurrency_safe(input_data)
            except ValidationError:
                is_safe = False  # 失败时保守处理

            # 合并连续的并发安全批次
            if is_safe and batches and batches[-1]['is_concurrency_safe']:
                batches[-1]['blocks'].append(block)
            else:
                batches.append({
                    'is_concurrency_safe': is_safe,
                    'blocks': [block]
                })

        return batches

    async def _execute_batch_concurrent(
        self,
        blocks: List[Dict[str, Any]],
        context: ToolUseContext
    ) -> List[ToolResult]:
        """并发执行一批工具"""
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def execute_with_semaphore(block: Dict[str, Any]) -> ToolResult:
            async with semaphore:
                return await self._execute_single(block, context)

        tasks = [execute_with_semaphore(block) for block in blocks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results: List[ToolResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ToolResult(
                    content=[ToolResultContent(
                        type='tool_result',
                        text=f"Error: {str(result)}"
                    )],
                    error=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    async def _execute_batch_serial(
        self,
        blocks: List[Dict[str, Any]],
        context: ToolUseContext
    ) -> List[ToolResult]:
        """串行执行一批工具"""
        results: List[ToolResult] = []

        for block in blocks:
            try:
                result = await self._execute_single(block, context)
                results.append(result)
            except Exception as e:
                results.append(ToolResult(
                    content=[ToolResultContent(
                        type='tool_result',
                        text=f"Error: {str(e)}"
                    )],
                    error=str(e)
                ))

        return results

    async def _execute_single(
        self,
        block: Dict[str, Any],
        context: ToolUseContext
    ) -> ToolResult:
        """执行单个工具"""
        tool = ToolRegistry.get_instance().get(block['name'])

        if not tool:
            return ToolResult(
                content=[ToolResultContent(
                    type='tool_result',
                    tool_use_id=block.get('id'),
                    text=f"Tool not found: {block['name']}"
                )],
                error=f"Tool not found: {block['name']}"
            )

        # 1. Schema 验证
        try:
            input_data = tool.input_schema.model_validate(block.get('input', {}))
        except ValidationError as e:
            return ToolResult(
                content=[ToolResultContent(
                    type='tool_result',
                    tool_use_id=block.get('id'),
                    text=f"Invalid input: {e}"
                )],
                error="validation_failed"
            )

        # 2. 权限检查
        if self.permission_checker:
            decision = self.permission_checker.check(tool.name, input_data)

            if decision.behavior == PermissionBehavior.DENY:
                return ToolResult(
                    content=[ToolResultContent(
                        type='tool_result',
                        tool_use_id=block.get('id'),
                        text=decision.message or f"Permission denied for {tool.name}"
                    )],
                    suppressed=True,
                    error="permission_denied"
                )

            if decision.behavior == PermissionBehavior.ASK:
                # 暂停等待用户确认 (简化实现)
                return ToolResult(
                    content=[ToolResultContent(
                        type='tool_result',
                        tool_use_id=block.get('id'),
                        text=decision.message or f"Permission required for {tool.name}"
                    )],
                    error="permission_required"
                )

        # 3. 执行工具
        try:
            result = await tool.call(input_data, context, None, None, None)
            # 确保 tool_use_id 被设置
            if result.content and not result.content[0].tool_use_id:
                result.content[0].tool_use_id = block.get('id')
            return result
        except Exception as e:
            return ToolResult(
                content=[ToolResultContent(
                    type='tool_result',
                    tool_use_id=block.get('id'),
                    text=f"Execution error: {str(e)}"
                )],
                error="execution_failed"
            )


# =============================================================================
# 11. 工具实现示例
# =============================================================================

class BashTool(BaseTool):
    """Bash 工具 - 展示完整实现"""

    name = "Bash"
    aliases = ["Shell", "Command"]
    max_result_size_chars = 10000

    def __init__(self):
        super().__init__(
            name="Bash",
            input_schema=self._create_schema()
        )
        self._setup_permissions()

    @staticmethod
    def _create_schema() -> type[BaseModel]:
        class BashInput(BaseModel):
            command: str = Field(description="要执行的命令")
            context: Optional[str] = Field(
                default="execute",
                description="execute, interactive, login"
            )
            timeout: Optional[int] = Field(default=60000, description="超时(ms)")
            current_dir: Optional[str] = Field(default=None, description="工作目录")

        return BashInput

    def _setup_permissions(self):
        """设置权限规则"""
        self._check_permissions = self._bash_check_permissions

    def _bash_check_permissions(
        self,
        input_data: 'BashInput',
        context: ToolUseContext
    ) -> PermissionDecision:
        checker = PermissionChecker(context.tool_permission_context)
        return checker.check(self.name, input_data.model_dump())

    async def call(
        self,
        input_data: 'BashInput',
        context: ToolUseContext,
        can_use_tool: Callable = None,
        parent_message: Optional[Dict] = None,
        on_progress: Optional[Callable] = None
    ) -> ToolResult:
        import subprocess

        try:
            result = subprocess.run(
                input_data.command,
                shell=True,
                cwd=input_data.current_dir or context.session_id,
                capture_output=True,
                text=True,
                timeout=input_data.timeout / 1000 if input_data.timeout else 60
            )

            output = result.stdout or result.stderr
            return ToolResult(
                content=[ToolResultContent(
                    type='tool_result',
                    text=output or "(no output)"
                )]
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                content=[ToolResultContent(
                    type='tool_result',
                    text=f"Command timed out after {input_data.timeout}ms"
                )],
                error="timeout"
            )
        except Exception as e:
            return ToolResult(
                content=[ToolResultContent(
                    type='tool_result',
                    text=f"Error: {str(e)}"
                )],
                error="execution_failed"
            )


class ReadTool(BaseTool):
    """Read 工具 - 展示只读工具"""

    name = "Read"

    def __init__(self):
        super().__init__(
            name="Read",
            input_schema=self._create_schema()
        )

    @staticmethod
    def _create_schema() -> type[BaseModel]:
        class ReadInput(BaseModel):
            file_path: str = Field(description="要读取的文件路径")
            offset: Optional[int] = Field(default=None, description="字节偏移量")
            limit: Optional[int] = Field(default=None, description="读取字节数限制")
            show_line_numbers: bool = Field(default=False)

        return ReadInput

    async def call(
        self,
        input_data: 'ReadInput',
        context: ToolUseContext,
        can_use_tool: Callable = None,
        parent_message: Optional[Dict] = None,
        on_progress: Optional[Callable] = None
    ) -> ToolResult:
        import os

        try:
            with open(input_data.file_path, 'r') as f:
                if input_data.offset:
                    f.seek(input_data.offset)
                content = f.read(
                    input_data.limit if input_data.limit else -1
                )

            if input_data.show_line_numbers:
                lines = content.split('\n')
                content = '\n'.join(
                    f"{i+1}: {line}" for i, line in enumerate(lines)
                )

            return ToolResult(
                content=[ToolResultContent(
                    type='tool_result',
                    text=content
                )]
            )
        except FileNotFoundError:
            return ToolResult(
                content=[ToolResultContent(
                    type='tool_result',
                    text=f"File not found: {input_data.file_path}"
                )],
                error="file_not_found"
            )
        except Exception as e:
            return ToolResult(
                content=[ToolResultContent(
                    type='tool_result',
                    text=f"Error reading file: {str(e)}"
                )],
                error="read_error"
            )


# =============================================================================
# 12. 示例用法
# =============================================================================

async def main():
    """示例用法"""
    # 创建工具
    bash_tool = BashTool()
    read_tool = ReadTool()

    # 注册工具
    registry = ToolRegistry.get_instance()
    registry.register(bash_tool)
    registry.register(read_tool)

    print(f"Registered tools: {[t.name for t in registry.get_all()]}")

    # 创建上下文
    context = ToolUseContext(
        tools=registry.get_all(),
        abort_controller='AbortController',  # 简化
        read_file_state={},
        tool_permission_context=ToolPermissionContext(
            mode="auto",
            rules=[
                PermissionRule(
                    pattern="Bash(rm *)",
                    behavior=PermissionBehavior.DENY,
                    reason="Dangerous command"
                ),
                PermissionRule(
                    pattern="Bash(git *)",
                    behavior=PermissionBehavior.ALLOW,
                    reason="Git commands are allowed"
                ),
            ]
        )
    )

    # 创建执行器
    executor = ToolExecutor(
        max_concurrency=10,
        permission_checker=PermissionChecker(context.tool_permission_context)
    )

    # 执行工具
    tool_use_blocks = [
        {
            'id': '1',
            'name': 'Bash',
            'input': {'command': 'echo "Hello, World!"'}
        },
        {
            'id': '2',
            'name': 'Read',
            'input': {'file_path': '/tmp/test.txt'}
        }
    ]

    results = await executor.execute(tool_use_blocks, context)

    for result in results:
        print(f"Result: {result.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
