# Phase 3: 命令系统设计

> 日期：2026-04-05
> 状态：设计阶段
> 对应 TypeScript：`src/commands.ts`, `src/commands/*/`

---

## 1. 命令系统架构

### 1.1 命令类型

| Type | 说明 | 返回值 |
|------|------|--------|
| `prompt` | 展开为发送给模型的文本 | `ContentBlock[]` |
| `local` | 本地执行，返回文本 | `LocalCommandResult` |
| `local-jsx` | 渲染 React/Ink UI | `ReactNode` |

### 1.2 核心组件

```
CommandSystem
├── BaseCommand (abstract)
│   ├── name: str
│   ├── aliases: list[str]
│   ├── description: str
│   ├── argument_hint: str
│   ├── availability: list[str]
│   ├── execute() [abstract]
│   └── get_help()
├── CommandRegistry
│   ├── register()
│   ├── get()
│   ├── list_commands()
│   └── execute()
└── CommandLoader
    └── load_all_commands()
```

---

## 2. 命令基类设计

### 2.1 BaseCommand

对应 TypeScript：`src/commands.ts` Command type

```python
"""Base command class."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable
from enum import Enum


class CommandType(str, Enum):
    """Command execution type."""
    PROMPT = "prompt"       # Expands to text sent to model
    LOCAL = "local"         # Executes locally, returns text
    LOCAL_JSX = "local-jsx"  # Renders UI component


class Availability(str, Enum):
    """Where command is available."""
    CLAUDE_AI = "claude-ai"  # Claude.ai subscriber only
    CONSOLE = "console"      # CLI console only
    ALL = "all"             # Everywhere


@dataclass
class CommandResult:
    """Result from command execution."""
    type: str  # "text", "content", "jsx"
    value: str | None = None
    content: list[dict[str, Any]] | None = None
    node: Any = None  # For JSX commands


@dataclass
class BaseCommand(ABC):
    """Base class for all commands.

    TypeScript equivalent: src/commands.ts Command interface
    """

    # Basic metadata
    name: str
    description: str
    aliases: list[str] = field(default_factory=list)
    argument_hint: str | None = None

    # Execution type
    command_type: CommandType = CommandType.LOCAL

    # Availability
    availability: list[str] = field(default_factory=lambda: [Availability.ALL.value])

    # Flags
    is_hidden: bool = False
    immediate: bool = False  # Execute without waiting for stop point
    supports_non_interactive: bool = False

    # Source tracking
    source: str = "builtin"  # builtin, plugin, bundled, mcp

    # Dynamic enable check
    is_enabled: Callable[[], bool] | None = None

    def __post_init__(self):
        # Build lookup set for aliases
        self._all_names = {self.name, *self.aliases}

    @abstractmethod
    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the command with given arguments.

        Args:
            args: Raw argument string
            context: Execution context (settings, state, etc.)

        Returns:
            CommandResult with output
        """
        ...

    def get_help(self) -> str:
        """Get help text for this command."""
        hint = f" {self.argument_hint}" if self.argument_hint else ""
        return f"/{self.name}{hint}: {self.description}"

    def check_availability(self, auth_type: str) -> bool:
        """Check if command is available for given auth type."""
        if Availability.ALL.value in self.availability:
            return True
        return auth_type in self.availability

    def check_enabled(self) -> bool:
        """Check if command is enabled."""
        if self.is_enabled:
            return self.is_enabled()
        return True


class PromptCommand(BaseCommand):
    """Command that expands to prompt content sent to model."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs, command_type=CommandType.PROMPT)

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        # Subclasses implement get_prompt_content()
        content = await self.get_prompt_content(args, context)
        return CommandResult(
            type="content",
            content=[{"type": "text", "text": content}],
        )

    @abstractmethod
    async def get_prompt_content(
        self,
        args: str,
        context: dict[str, Any],
    ) -> str:
        """Generate the prompt content."""
        ...
```

---

## 3. 命令实现详细设计

### 3.1 ClearCommand

对应 TypeScript：`src/commands/clear/clear.ts`

```python
"""Clear command - clears conversation history."""
from __future__ import annotations
from typing import Any

from .base import BaseCommand, CommandResult, CommandType


class ClearCommand(BaseCommand):
    """Clear conversation history and free context.

    TypeScript equivalent: src/commands/clear/clear.ts
    Aliases: reset, new
    """

    def __init__(self):
        super().__init__(
            name="clear",
            description="Clear conversation history to free context. " +
                       "A new conversation starts.",
            aliases=["reset", "new"],
            command_type=CommandType.LOCAL,
            supports_non_interactive=True,
        )

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        # Clear messages from state
        # In production: state_store.set_state(...)
        return CommandResult(
            type="text",
            value="Conversation cleared. Starting fresh.",
        )
```

### 3.2 CommitCommand

对应 TypeScript：`src/commands/commit.ts`

```python
"""Git commit command."""
from __future__ import annotations
import subprocess
from typing import Any

from .base import BaseCommand, CommandResult, CommandType


class CommitCommand(BaseCommand):
    """Create a git commit.

    TypeScript equivalent: src/commands/commit.ts
    Internal/ANT-only in TypeScript
    """

    def __init__(self):
        super().__init__(
            name="commit",
            description="Create a git commit with the current changes",
            command_type=CommandType.LOCAL,
        )

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        # Parse arguments
        if args.strip():
            message = args.strip()
            cmd_args = ["git", "commit", "-m", message]
        else:
            # Interactive commit (opens editor)
            cmd_args = ["git", "commit"]

        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return CommandResult(
                    type="text",
                    value=result.stdout or "Commit created successfully.",
                )
            else:
                return CommandResult(
                    type="text",
                    value=f"Error: {result.stderr}",
                )

        except FileNotFoundError:
            return CommandResult(
                type="text",
                value="Error: git not found. Is Git installed?",
            )
        except Exception as e:
            return CommandResult(
                type="text",
                value=f"Error creating commit: {str(e)}",
            )
```

### 3.3 BranchCommand

对应 TypeScript：`src/commands/branch/branch.ts`

```python
"""Git branch command."""
from __future__ import annotations
import subprocess
from typing import Any

from .base import BaseCommand, CommandResult, CommandType


class BranchCommand(BaseCommand):
    """List, create, or delete git branches.

    TypeScript equivalent: src/commands/branch/branch.ts
    """

    def __init__(self):
        super().__init__(
            name="branch",
            description="List, create, or delete branches",
            command_type=CommandType.LOCAL,
        )

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        parts = args.strip().split()
        subcommand = parts[0] if parts else ""

        if not subcommand:
            # List branches
            cmd_args = ["git", "branch", "-a"]
        elif subcommand == "-d" or subcommand == "-D":
            # Delete branch
            branch_name = parts[1] if len(parts) > 1 else ""
            if not branch_name:
                return CommandResult(type="text", value="Error: branch name required")
            cmd_args = ["git", "branch", subcommand, branch_name]
        elif subcommand == "-c" or subcommand == "-C":
            # Copy/rename branch
            old_name = parts[1] if len(parts) > 1 else ""
            new_name = parts[2] if len(parts) > 2 else ""
            if not old_name or not new_name:
                return CommandResult(type="text", value="Error: old and new branch names required")
            cmd_args = ["git", "branch", subcommand, old_name, new_name]
        else:
            # Create new branch
            cmd_args = ["git", "branch", args.strip()]

        try:
            result = subprocess.run(cmd_args, capture_output=True, text=True)
            return CommandResult(
                type="text",
                value=result.stdout or result.stderr or "Done.",
            )
        except Exception as e:
            return CommandResult(type="text", value=f"Error: {str(e)}")
```

### 3.4 ConfigCommand

对应 TypeScript：`src/commands/config/config.tsx`

```python
"""Config command - manage settings."""
from __future__ import annotations
from typing import Any

from .base import BaseCommand, CommandResult, CommandType


class ConfigCommand(BaseCommand):
    """Open config panel or get/set settings.

    TypeScript equivalent: src/commands/config/config.tsx
    Alias: settings
    """

    def __init__(self):
        super().__init__(
            name="config",
            description="Manage Claude Code settings and configuration",
            aliases=["settings"],
            command_type=CommandType.LOCAL_JSX,  # Opens UI panel
        )

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        # In production, this would return JSX to render config panel
        # For now, handle non-interactive get/set
        if args.strip():
            # Get or set a specific setting
            parts = args.strip().split(maxsplit=1)
            key = parts[0]
            value = parts[1] if len(parts) > 1 else None

            # In production: read/write settings
            if value is None:
                # Get setting
                return CommandResult(type="text", value=f"Setting '{key}': <value>")
            else:
                # Set setting
                return CommandResult(type="text", value=f"Setting '{key}' updated.")
        else:
            # Open full config panel
            return CommandResult(type="jsx", value=None)
```

### 3.5 CompactCommand

对应 TypeScript：`src/commands/compact/compact.ts`

```python
"""Compact command - summarize and clear history."""
from __future__ import annotations
from typing import Any

from .base import BaseCommand, CommandResult, CommandType


class CompactCommand(BaseCommand):
    """Clear history but keep a summary.

    TypeScript equivalent: src/commands/compact/compact.ts
    """

    def __init__(self):
        super().__init__(
            name="compact",
            description="Clear history but keep a summary. " +
                       "Frees context while preserving conversation essence.",
            command_type=CommandType.LOCAL,
        )

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        custom_instructions = args.strip() if args.strip() else None

        # In production:
        # 1. Run summarization on current messages
        # 2. Replace messages with summary
        # 3. Return summary

        return CommandResult(
            type="text",
            value="Conversation summarized and compacted. Context freed.",
        )
```

### 3.6 HelpCommand

```python
"""Help command."""
from __future__ import annotations
from typing import Any

from .base import BaseCommand, CommandResult, CommandType


class HelpCommand(BaseCommand):
    """Show help and available commands.

    TypeScript equivalent: src/commands/help/help.tsx
    """

    def __init__(self, command_registry: Any = None):
        super().__init__(
            name="help",
            description="Show help and available commands",
            command_type=CommandType.LOCAL,
        )
        self._registry = command_registry

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        if args.strip():
            # Get help for specific command
            cmd_name = args.strip().lstrip("/")
            if self._registry:
                cmd = self._registry.get(cmd_name)
                if cmd:
                    return CommandResult(type="text", value=cmd.get_help())
            return CommandResult(type="text", value=f"Unknown command: /{cmd_name}")

        # List all commands
        help_text = """
Claude Code Commands:

Core Commands:
  /clear [reset, new]     Clear conversation history
  /compact               Clear history but keep summary
  /commit                Create a git commit
  /config [settings]     Open config panel
  /help                  Show this help
  /model [model]         Set AI model
  /exit [quit]           Exit Claude Code

File Commands:
  /diff                  View uncommitted changes
  /export [filename]     Export conversation

Session Commands:
  /branch                Manage git branches
  /resume [id]           Resume a previous conversation
  /session               Show remote session URL

Type /help <command> for details on a specific command.
        """.strip()

        return CommandResult(type="text", value=help_text)
```

### 3.7 ModelCommand

```python
"""Model command."""
from __future__ import annotations
from typing import Any

from .base import BaseCommand, CommandResult, CommandType


class ModelCommand(BaseCommand):
    """Set AI model for Claude Code.

    TypeScript equivalent: src/commands/model/model.tsx
    """

    AVAILABLE_MODELS = {
        "claude-opus-4-6": "Claude Opus 4.6 - Most capable",
        "claude-sonnet-4-6": "Claude Sonnet 4.6 - Balanced",
        "claude-haiku-4-5": "Claude Haiku 4.5 - Fast",
        "claude-opus-4-1": "Claude Opus 4.1",
        "claude-sonnet-4-1": "Claude Sonnet 4.1",
    }

    def __init__(self):
        super().__init__(
            name="model",
            description="Set AI model for Claude Code",
            command_type=CommandType.LOCAL,
        )

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        model = args.strip().lower()

        if not model:
            # Show current model
            current = context.get("model", "claude-opus-4-6")
            return CommandResult(
                type="text",
                value=f"Current model: {current}\n\nAvailable models:\n" +
                      "\n".join(f"  {k}: {v}" for k, v in self.AVAILABLE_MODELS.items()),
            )

        if model == "off":
            # Disable model selection (use default)
            return CommandResult(type="text", value="Model selection disabled.")

        # Validate model
        if model not in self.AVAILABLE_MODELS:
            return CommandResult(
                type="text",
                value=f"Unknown model: {model}\n\nAvailable:\n" +
                      "\n".join(self.AVAILABLE_MODELS.keys()),
            )

        # Update model
        # In production: update_app_state(...)
        return CommandResult(
            type="text",
            value=f"Model set to: {model} ({self.AVAILABLE_MODELS[model]})",
        )
```

### 3.8 SessionCommand

```python
"""Session command."""
from __future__ import annotations
from typing import Any

from .base import BaseCommand, CommandResult, CommandType


class SessionCommand(BaseCommand):
    """Show remote session URL and QR code.

    TypeScript equivalent: src/commands/session/session.tsx
    Alias: remote
    """

    def __init__(self):
        super().__init__(
            name="session",
            description="Show remote session URL and QR code for mobile access",
            aliases=["remote"],
            command_type=CommandType.LOCAL_JSX,
        )

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        # In production: generate session URL and QR code
        return CommandResult(type="jsx", value=None)
```

### 3.9 AddDirCommand

对应 TypeScript：`src/commands/add-dir/add-dir.tsx`

```python
"""Add-dir command."""
from __future__ import annotations
import os
from typing import Any

from .base import BaseCommand, CommandResult, CommandType


class AddDirCommand(BaseCommand):
    """Add a new working directory.

    TypeScript equivalent: src/commands/add-dir/add-dir.tsx
    """

    def __init__(self):
        super().__init__(
            name="add-dir",
            description="Add a new working directory to the current session",
            argument_hint="<path>",
            command_type=CommandType.LOCAL_JSX,
        )

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        path = args.strip()

        if not path:
            return CommandResult(
                type="text",
                value="Error: path required. Usage: /add-dir <path>",
            )

        # Validate path
        if not os.path.exists(path):
            return CommandResult(
                type="text",
                value=f"Error: Directory does not exist: {path}",
            )

        if not os.path.isdir(path):
            return CommandResult(
                type="text",
                value=f"Error: Not a directory: {path}",
            )

        # In production: add to context directories
        return CommandResult(
            type="text",
            value=f"Added directory: {os.path.abspath(path)}",
        )
```

---

## 4. 命令注册表

对应 TypeScript：`src/commands.ts`

```python
"""Command registry - manages available commands."""
from __future__ import annotations
from typing import Any

from .base import BaseCommand, CommandResult


class CommandRegistry:
    """Registry for slash commands.

    TypeScript equivalent: src/commands.ts COMMANDS()
    """

    def __init__(self):
        self._commands: dict[str, BaseCommand] = {}

    def register(self, command: BaseCommand) -> None:
        """Register a command and its aliases."""
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command

    def get(self, name: str) -> BaseCommand | None:
        """Get a command by name or alias."""
        return self._commands.get(name)

    def list_commands(
        self,
        include_hidden: bool = False,
        auth_type: str | None = None,
    ) -> list[BaseCommand]:
        """List all registered commands."""
        seen: set[str] = set()
        result: list[BaseCommand] = []

        for cmd in self._commands.values():
            if cmd.name in seen:
                continue
            seen.add(cmd.name)

            # Filter hidden
            if cmd.is_hidden and not include_hidden:
                continue

            # Filter by availability
            if auth_type and not cmd.check_availability(auth_type):
                continue

            # Filter by enabled
            if not cmd.check_enabled():
                continue

            result.append(cmd)

        return result

    async def execute(
        self,
        name: str,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute a command by name."""
        command = self.get(name)
        if not command:
            return CommandResult(
                type="text",
                value=f"Unknown command: /{name}",
            )

        if not command.check_enabled():
            return CommandResult(
                type="text",
                value=f"Command not enabled: /{name}",
            )

        return await command.execute(args, context)

    def get_by_source(self, source: str) -> list[BaseCommand]:
        """Get commands by source (builtin, plugin, bundled, mcp)."""
        return [cmd for cmd in self.list_commands() if cmd.source == source]
```

---

## 5. 命令加载器

对应 TypeScript：`src/commands.ts` loadAllCommands

```python
"""Command loader - loads all commands."""
from __future__ import annotations
from typing import Any

from .registry import CommandRegistry


class CommandLoader:
    """Loads commands from all sources.

    TypeScript equivalent: loadAllCommands() in commands.ts
    """

    def __init__(self, registry: CommandRegistry):
        self._registry = registry

    def load_all_commands(self) -> None:
        """Load all built-in and bundled commands."""
        # Core commands (always available)
        self._load_core_commands()

        # Feature-gated commands
        self._load_feature_gated_commands()

        # Bundled skills
        self._load_bundled_skills()

    def _load_core_commands(self) -> None:
        """Load core commands."""
        from .clear import ClearCommand
        from .compact import CompactCommand
        from .commit import CommitCommand
        from .branch import BranchCommand
        from .config import ConfigCommand
        from .help import HelpCommand
        from .model import ModelCommand
        from .session import SessionCommand
        from .add_dir import AddDirCommand

        # Register commands
        self._registry.register(ClearCommand())
        self._registry.register(CompactCommand())
        self._registry.register(CommitCommand())
        self._registry.register(BranchCommand())
        self._registry.register(ConfigCommand())
        self._registry.register(HelpCommand(self._registry))
        self._registry.register(ModelCommand())
        self._registry.register(SessionCommand())
        self._registry.register(AddDirCommand())

    def _load_feature_gated_commands(self) -> None:
        """Load commands gated by feature flags."""
        # These would check feature flags before loading
        # Example:
        # if feature("VOICE_MODE"):
        #     self._registry.register(VoiceCommand())
        pass

    def _load_bundled_skills(self) -> None:
        """Load bundled skill commands."""
        # Load from skills directory
        pass
```

---

## 6. 完整命令清单

### 核心命令 (Always Available)

| 命令 | 类名 | 类型 | 说明 |
|------|------|------|------|
| `/add-dir` | AddDirCommand | local-jsx | 添加工作目录 |
| `/advisor` | AdvisorCommand | local | 配置 advisor 模型 |
| `/agents` | AgentsCommand | local-jsx | 管理 agent 配置 |
| `/branch` | BranchCommand | local-jsx | Git 分支管理 |
| `/btw` | BtwCommand | local-jsx | 快速侧问 |
| `/clear` | ClearCommand | local | 清空对话历史 |
| `/color` | ColorCommand | local-jsx | 设置提示栏颜色 |
| `/compact` | CompactCommand | local | 压缩历史保留摘要 |
| `/config` | ConfigCommand | local-jsx | 打开配置面板 |
| `/context` | ContextCommand | local-jsx | 可视化上下文使用 |
| `/copy` | CopyCommand | local-jsx | 复制上次响应 |
| `/cost` | CostCommand | local | 显示会话成本 |
| `/diff` | DiffCommand | local-jsx | 查看未提交更改 |
| `/doctor` | DoctorCommand | local-jsx | 诊断安装/设置 |
| `/effort` | EffortCommand | local-jsx | 设置努力级别 |
| `/exit` | ExitCommand | local-jsx | 退出 REPL |
| `/export` | ExportCommand | local-jsx | 导出会话 |
| `/fast` | FastCommand | local-jsx | 切换快速模式 |
| `/feedback` | FeedbackCommand | local-jsx | 提交反馈 |
| `/files` | FilesCommand | local | 列出上下文中的文件 |
| `/help` | HelpCommand | local | 显示帮助 |
| `/hooks` | HooksCommand | local-jsx | 查看 hook 配置 |
| `/ide` | IdeCommand | local-jsx | 管理 IDE 集成 |
| `/init` | InitCommand | local-jsx | 初始化 CLAUDE.md |
| `/insights` | InsightsCommand | prompt | 生成会话分析报告 |
| `/keybindings` | KeybindingsCommand | local | 键盘绑定配置 |
| `/login` | LoginCommand | local-jsx | 登录 Anthropic 账户 |
| `/logout` | LogoutCommand | local-jsx | 登出 |
| `/mcp` | McpCommand | local-jsx | 管理 MCP 服务器 |
| `/memory` | MemoryCommand | local-jsx | 编辑记忆文件 |
| `/model` | ModelCommand | local-jsx | 设置 AI 模型 |
| `/mobile` | MobileCommand | local-jsx | 显示移动端二维码 |
| `/passes` | PassesCommand | local-jsx | 分享免费周 |
| `/permissions` | PermissionsCommand | local-jsx | 管理权限规则 |
| `/plan` | PlanCommand | local-jsx | 启用计划模式 |
| `/privacy-settings` | PrivacySettingsCommand | local-jsx | 隐私设置 |
| `/release-notes` | ReleaseNotesCommand | local | 查看发布说明 |
| `/reload-plugins` | ReloadPluginsCommand | local | 重新加载插件 |
| `/remote-env` | RemoteEnvCommand | local-jsx | 配置远程环境 |
| `/rename` | RenameCommand | local-jsx | 重命名会话 |
| `/resume` | ResumeCommand | local-jsx | 恢复会话 |
| `/rewind` | RewindCommand | local | 回溯到之前状态 |
| `/session` | SessionCommand | local-jsx | 显示远程会话 URL |
| `/skills` | SkillsCommand | local-jsx | 列出可用技能 |
| `/stats` | StatsCommand | local-jsx | 显示使用统计 |
| `/status` | StatusCommand | local-jsx | 显示版本/状态 |
| `/statusline` | StatuslineCommand | prompt | 设置状态行 UI |
| `/stickers` | StickersCommand | local | 订购贴纸 |
| `/summary` | SummaryCommand | local | 总结会话 |
| `/tag` | TagCommand | local-jsx | 标记会话 |
| `/tasks` | TasksCommand | local-jsx | 管理后台任务 |
| `/terminal-setup` | TerminalSetupCommand | local-jsx | 终端设置 |
| `/theme` | ThemeCommand | local-jsx | 更改主题 |
| `/think-back` | ThinkbackCommand | local-jsx | 年度回顾 |
| `/upgrade` | UpgradeCommand | local-jsx | 升级到 Max |
| `/usage` | UsageCommand | local-jsx | 显示使用限额 |
| `/vim` | VimCommand | local | 切换 Vim 模式 |
| `/voice` | VoiceCommand | local | 切换语音模式 |
| `/sandbox` | SandboxCommand | local-jsx | 切换沙箱模式 |

### Feature-Gated 命令

| 命令 | Feature Gate | 说明 |
|------|-------------|------|
| `/web-setup` | CCR_REMOTE_SETUP | Web 设置 |
| `/fork` | FORK_SUBAGENT | Fork 子代理 |
| `/buddy` | BUDDY | Buddy 功能 |
| `/proactive` | PROACTIVE/KAIROS | 主动模式 |
| `/brief` | KAIROS/KAIROS_BRIEF | Brief 模式 |
| `/assistant` | KAIROS | Assistant 功能 |
| `/bridge` | BRIDGE_MODE | 桥接模式 |
| `/remote-control-server` | DAEMON+BRIDGE_MODE | 远程控制服务器 |
| `/voice` | VOICE_MODE | 语音模式 |
| `/workflows` | WORKFLOW_SCRIPTS | 工作流脚本 |
| `/ultrareview` | GrowthBook gate | 10-20min bug 发现 |
| `/ultraplan` | ULTRAPLAN | Ultra 计划模式 |

### Internal/ANT-Only 命令

| 命令 | 说明 |
|------|------|
| `/commit` | 创建 git 提交 |
| `/commit-push-pr` | 提交、推送并打开 PR |
| `/autofix-pr` | Autofix PR 功能 |
| `/backfill-sessions` | 回填会话 |
| `/break-cache` | 打破缓存 |
| `/bridge-kick` | 注入桥接故障状态 |
| `/bughunter` | Bug hunter 功能 |
| `/ctx-viz` | 上下文可视化 |
| `/debug-tool-call` | 调试工具调用 |
| `/env` | 环境管理 |
| `/good-claude` | Good Claude 功能 |
| `/insider` | Insider 功能 |
| `/issue` | Issue 跟踪 |
| `/mock-limits` | 模拟限制 |
| `/oauth-refresh` | OAuth 刷新 |
| `/perf-issue` | 性能问题跟踪 |
| `/reset-limits` | 重置使用限额 |
| `/ant-trace` | Ant trace 功能 |
| `/onboarding` | 用户入职 |
| `/share` | 分享功能 |
| `/teleport` | 传送到远程环境 |

---

## 7. 实施任务清单

### Phase 3.1: 命令框架
- [ ] 实现 `commands/base.py` - BaseCommand
- [ ] 实现 `commands/registry.py` - CommandRegistry
- [ ] 实现 `commands/loader.py` - CommandLoader

### Phase 3.2: 核心命令
- [ ] 实现 ClearCommand
- [ ] 实现 CompactCommand
- [ ] 实现 CommitCommand
- [ ] 实现 BranchCommand
- [ ] 实现 ConfigCommand
- [ ] 实现 HelpCommand
- [ ] 实现 ModelCommand
- [ ] 实现 SessionCommand
- [ ] 实现 AddDirCommand

### Phase 3.3: 文件命令
- [ ] 实现 DiffCommand
- [ ] 实现 ExportCommand
- [ ] 实现 FilesCommand

### Phase 3.4: 会话命令
- [ ] 实现 ResumeCommand
- [ ] 实现 RewindCommand
- [ ] 实现 RenameCommand

### Phase 3.5: 设置命令
- [ ] 实现 ColorCommand
- [ ] 实现 ThemeCommand
- [ ] 实现 FastCommand
- [ ] 实现 EffortCommand
- [ ] 实现 VimCommand

### Phase 3.6: 工具命令
- [ ] 实现 CostCommand
- [ ] 实现 StatsCommand
- [ ] 实现 StatusCommand
- [ ] 实现 UsageCommand
- [ ] 实现 DoctorCommand

### Phase 3.7: 账户命令
- [ ] 实现 LoginCommand
- [ ] 实现 LogoutCommand
- [ ] 实现 UpgradeCommand
- [ ] 实现 PassesCommand

### Phase 3.8: 集成命令
- [ ] 实现 McpCommand
- [ ] 实现 HooksCommand
- [ ] 实现 IdeCommand
- [ ] 实现 InitCommand
- [ ] 实现 MemoryCommand
- [ ] 实现 SkillsCommand

### Phase 3.9: 其他命令
- [ ] 实现 AdvisorCommand
- [ ] 实现 AgentsCommand
- [ ] 实现 BtwCommand
- [ ] 实现 ContextCommand
- [ ] 实现 CopyCommand
- [ ] 实现 ExitCommand
- [ ] 实现 FeedbackCommand
- [ ] 实现 KeybindingsCommand
- [ ] 实现 MobileCommand
- [ ] 实现 PermissionsCommand
- [ ] 实现 PlanCommand
- [ ] 实现 PrivacySettingsCommand
- [ ] 实现 ReleaseNotesCommand
- [ ] 实现 ReloadPluginsCommand
- [ ] 实现 RemoteEnvCommand
- [ ] 实现 StatuslineCommand
- [ ] 实现 StickersCommand
- [ ] 实现 SummaryCommand
- [ ] 实现 TagCommand
- [ ] 实现 TasksCommand
- [ ] 实现 TerminalSetupCommand
- [ ] 实现 ThinkbackCommand
- [ ] 实现 VoiceCommand
- [ ] 实现 InsightsCommand
- [ ] 实现 SandboxCommand
