# Phase 11: Plugins 系统设计

> 日期：2026-04-06
> 状态：设计完成
> 对应 TypeScript：`src/plugins/*`, `src/utils/plugins/*`, `src/services/plugins/*`

---

## 1. 插件架构概览

### 1.1 核心组件

```
Plugin System
├── PluginLoader - 插件加载和缓存
├── PluginRegistry - 插件注册表
├── PluginOperations - 安装/卸载/启用/禁用
├── HookManager - 生命周期钩子管理
└── PluginManifest - 插件清单格式
```

### 1.2 插件来源类型

| 类型 | 说明 |
|------|------|
| **npm** | NPM 包作为插件源 |
| **pip** | Python 包作为插件源 |
| **git** | Git 仓库 URL (https:// 或 git@) |
| **github** | GitHub 仓库 (owner/repo 简写) |
| **相对路径** | 相对于市场的路径 |

### 1.3 插件安装作用域

| 作用域 | 说明 |
|--------|------|
| **managed** | 企业/系统范围 (只读) |
| **user** | 用户全局设置 (~/.claude/settings.json) |
| **project** | 共享项目设置 ($project/.claude/settings.json) |
| **local** | 个人项目覆盖 |

---

## 2. 插件清单格式

### 2.1 plugin.json 结构

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Plugin description",
  "author": {
    "name": "Author Name",
    "email": "author@example.com",
    "url": "https://example.com"
  },
  "homepage": "https://github.com/example/plugin",
  "repository": "https://github.com/example/plugin",
  "license": "MIT",
  "keywords": ["productivity", "development"],
  "dependencies": ["other-plugin@marketplace"]
}
```

### 2.2 扩展清单字段

```json
{
  "commands": ["commands/*.md"],
  "agents": ["agents/*.md"],
  "skills": ["skills/**/*.md"],
  "hooks": "hooks/hooks.json",
  "outputStyles": ["output-styles/*.md"],
  "mcpServers": {},
  "lspServers": {},
  "userConfig": {}
}
```

### 2.3 标准目录结构

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # 插件清单
├── commands/
│   ├── hello.md             # /hello 命令
│   └── subdir/
│       └── world.md         # /subdir:world 命令
├── agents/
│   └── developer.md         # Agent 定义
├── skills/
│   └── code-review/
│       └── SKILL.md         # Skill 定义
├── hooks/
│   └── hooks.json           # 钩子定义
├── output-styles/
│   └── custom-style.md      # 自定义输出样式
└── .mcp.json               # MCP 服务器配置
```

---

## 3. 钩子系统

### 3.1 钩子事件类型 (25 种)

| 类别 | 事件 |
|------|------|
| **工具生命周期** | `PreToolUse`, `PostToolUse`, `PostToolUseFailure` |
| **会话生命周期** | `SessionStart`, `SessionEnd`, `Setup` |
| **Agent 生命周期** | `SubagentStart`, `SubagentStop`, `TeammateIdle` |
| **任务生命周期** | `TaskCreated`, `TaskCompleted` |
| **压缩** | `PreCompact`, `PostCompact` |
| **权限** | `PermissionRequest`, `PermissionDenied` |
| **用户交互** | `UserPromptSubmit`, `Notification`, `Elicitation` |
| **控制流** | `Stop`, `StopFailure` |
| **配置** | `ConfigChange` |
| **工作区** | `WorktreeCreate`, `WorktreeRemove`, `InstructionsLoaded` |

### 3.2 钩子类型

```python
# 命令钩子 - 运行 shell 命令
{"type": "command", "command": "echo 'Running'", "if": "tool.name == 'Bash'"}

# 提示钩子 - LLM 评估
{"type": "prompt", "prompt": "Evaluate this: {input}", "if": "tool.name == 'Bash'"}

# HTTP 钩子 - POST 到 URL
{"type": "http", "url": "https://example.com/hook", "if": "tool.name == 'Bash'"}

# Agent 钩子 - Agentic 验证器
{"type": "agent", "prompt": "Verify this is safe: {input}", "timeout": 30}
```

### 3.3 钩子匹配器配置

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash(git *)"
      hooks:
        - type: command
          command: "echo 'Running git command'"
```

---

## 4. Python 实现设计

### 4.1 插件基类

```python
"""Plugin base class."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum


class PluginScope(str, Enum):
    MANAGED = "managed"
    USER = "user"
    PROJECT = "project"
    LOCAL = "local"


@dataclass
class PluginManifest:
    """Plugin manifest data."""
    name: str
    version: str
    description: str
    author: dict[str, str] | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str = "MIT"
    keywords: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    commands: list[str] | None = None
    agents: list[str] | None = None
    skills: list[str] | None = None
    hooks: dict[str, Any] | None = None


class BasePlugin(ABC):
    """Base class for all plugins.

    TypeScript equivalent: Plugin interface in types/plugin.ts
    """

    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self._enabled = False

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    @abstractmethod
    async def on_load(self) -> None:
        """Called when plugin is loaded."""
        ...

    @abstractmethod
    async def on_enable(self) -> None:
        """Called when plugin is enabled."""
        ...

    @abstractmethod
    async def on_disable(self) -> None:
        """Called when plugin is disabled."""
        ...

    def is_enabled(self) -> bool:
        return self._enabled
```

### 4.2 插件注册表

```python
"""Plugin registry."""
from __future__ import annotations
from typing import Any
from .base import BasePlugin, PluginManifest


class PluginRegistry:
    """Registry for plugins.

    TypeScript equivalent: PluginLoader in utils/plugins/
    """

    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}
        self._hooks: dict[str, list[tuple[str, callable]]] = {}

    def register(self, plugin: BasePlugin) -> None:
        """Register a plugin."""
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> BasePlugin | None:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_enabled(self) -> list[BasePlugin]:
        """List all enabled plugins."""
        return [p for p in self._plugins.values() if p.is_enabled()]

    def register_hook(
        self,
        event: str,
        plugin_name: str,
        handler: callable,
    ) -> None:
        """Register a hook handler for an event."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append((plugin_name, handler))

    async def trigger_hook(
        self,
        event: str,
        context: dict[str, Any],
    ) -> list[Any]:
        """Trigger all handlers for an event."""
        results = []
        handlers = self._hooks.get(event, [])
        for plugin_name, handler in handlers:
            try:
                result = await handler(context)
                results.append(result)
            except Exception as e:
                # Log error but continue
                print(f"Hook error in {plugin_name}.{event}: {e}")
        return results
```

### 4.3 钩子管理器

```python
"""Hook manager for plugin lifecycle hooks."""
from __future__ import annotations
from typing import Any, Callable
from dataclasses import dataclass


@dataclass
class HookDefinition:
    """Definition of a hook."""
    event: str  # PreToolUse, PostToolUse, etc.
    hook_type: str  # command, prompt, http, agent
    command: str | None = None
    prompt: str | None = None
    url: str | None = None
    condition: str | None = None  # if clause


class HookManager:
    """Manages plugin hooks.

    TypeScript equivalent: loadPluginHooks in utils/plugins/
    """

    def __init__(self):
        self._hooks: dict[str, list[HookDefinition]] = {}

    def register_hook(self, definition: HookDefinition) -> None:
        """Register a hook definition."""
        if definition.event not in self._hooks:
            self._hooks[definition.event] = []
        self._hooks[definition.event].append(definition)

    async def execute_pre_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Execute PreToolUse hooks.

        Returns (allowed, error_message).
        """
        hooks = self._hooks.get("PreToolUse", [])
        for hook in hooks:
            if not self._matches_condition(hook, tool_name, tool_input):
                continue

            result = await self._execute_hook(hook, tool_name, tool_input)
            if result and result.get("blocked"):
                return False, result.get("message")

        return True, None

    async def execute_post_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_result: str,
    ) -> None:
        """Execute PostToolUse hooks."""
        hooks = self._hooks.get("PostToolUse", [])
        for hook in hooks:
            if not self._matches_condition(hook, tool_name, tool_input):
                continue
            await self._execute_hook(hook, tool_name, tool_input, tool_result)

    def _matches_condition(
        self,
        hook: HookDefinition,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> bool:
        """Check if hook condition matches."""
        if not hook.condition:
            return True

        # Simple condition matching
        # In production: parse and evaluate condition expression
        return True

    async def _execute_hook(
        self,
        hook: HookDefinition,
        *args,
        **kwargs,
    ) -> dict[str, Any] | None:
        """Execute a hook."""
        match hook.hook_type:
            case "command":
                return await self._execute_command_hook(hook, *args, **kwargs)
            case "prompt":
                return await self._execute_prompt_hook(hook, *args, **kwargs)
            case "http":
                return await self._execute_http_hook(hook, *args, **kwargs)
            case "agent":
                return await self._execute_agent_hook(hook, *args, **kwargs)
            case _:
                return None
```

### 4.4 插件操作

```python
"""Plugin operations - install, uninstall, enable, disable."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from enum import Enum

from .base import PluginScope, PluginManifest
from .registry import PluginRegistry


class PluginOperation(str, Enum):
    INSTALL = "install"
    UNINSTALL = "uninstall"
    ENABLE = "enable"
    DISABLE = "disable"
    UPDATE = "update"


class PluginOperations:
    """Handles plugin operations.

    TypeScript equivalent: pluginOperations.ts
    """

    def __init__(
        self,
        registry: PluginRegistry,
        config_path: Path | None = None,
    ):
        self.registry = registry
        self.config_path = config_path or Path.home() / ".claude" / "settings.json"

    async def install_plugin(
        self,
        plugin_id: str,
        source: str,
        scope: PluginScope = PluginScope.USER,
    ) -> None:
        """Install a plugin.

        TypeScript equivalent: installPluginOp()
        """
        # 1. Search marketplaces for plugin
        # 2. Write settings (declares intent)
        # 3. Materialize plugin to cache

        config = await self._load_config()
        if "plugins" not in config:
            config["plugins"] = {}

        config["plugins"][plugin_id] = {
            "source": source,
            "scope": scope.value,
            "enabled": True,
        }

        await self._save_config(config)

    async def uninstall_plugin(
        self,
        plugin_id: str,
        remove_data: bool = False,
    ) -> None:
        """Uninstall a plugin."""
        config = await self._load_config()
        if "plugins" in config and plugin_id in config["plugins"]:
            del config["plugins"][plugin_id]
            await self._save_config(config)

        # Optionally remove plugin data
        if remove_data:
            data_dir = Path.home() / ".claude" / "plugins" / "data" / plugin_id
            if data_dir.exists():
                import shutil
                shutil.rmtree(data_dir)

    async def enable_plugin(self, plugin_id: str) -> None:
        """Enable a plugin."""
        config = await self._load_config()
        if "plugins" in config and plugin_id in config["plugins"]:
            config["plugins"][plugin_id]["enabled"] = True
            await self._save_config(config)

        # Trigger plugin on_enable
        plugin = self.registry.get(plugin_id)
        if plugin:
            await plugin.on_enable()

    async def disable_plugin(self, plugin_id: str) -> None:
        """Disable a plugin."""
        config = await self._load_config()
        if "plugins" in config and plugin_id in config["plugins"]:
            config["plugins"][plugin_id]["enabled"] = False
            await self._save_config(config)

        # Trigger plugin on_disable
        plugin = self.registry.get(plugin_id)
        if plugin:
            await plugin.on_disable()

    async def _load_config(self) -> dict[str, Any]:
        """Load configuration."""
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return {}

    async def _save_config(self, config: dict[str, Any]) -> None:
        """Save configuration."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(config, indent=2))
```

---

## 5. 内置插件

### 5.1 内置插件注册表

```python
"""Built-in plugins registry."""
from __future__ import annotations
from typing import Any


BUILTIN_MARKETPLACE_NAME = "builtin"


class BuiltinPluginRegistry:
    """Registry for built-in plugins.

    TypeScript equivalent: bundled/index.ts
    """

    def __init__(self):
        self._plugins: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        definition: dict[str, Any],
    ) -> None:
        """Register a built-in plugin.

        Plugin ID format: {name}@builtin
        """
        plugin_id = f"{name}@{BUILTIN_MARKETPLACE_NAME}"
        self._plugins[plugin_id] = definition

    def get(self, plugin_id: str) -> dict[str, Any] | None:
        """Get built-in plugin definition."""
        return self._plugins.get(plugin_id)

    def list_all(self) -> list[dict[str, Any]]:
        """List all built-in plugins."""
        return list(self._plugins.values())


# Global registry
builtin_plugins = BuiltinPluginRegistry()


# Register built-in plugins
builtin_plugins.register("skill-brainstorm", {
    "name": "skill-brainstorm",
    "description": "Brainstorming skill for feature design",
    "version": "1.0.0",
    "skills": ["skills/brainstorm/SKILL.md"],
})

builtin_plugins.register("skill-debugging", {
    "name": "skill-debugging",
    "description": "Systematic debugging skill",
    "version": "1.0.0",
    "skills": ["skills/debugging/SKILL.md"],
})
```

---

## 6. 完整插件清单

| 组件 | 路径 | 说明 |
|------|------|------|
| **commands/** | `commands/*.md` | 斜杠命令 (Markdown 文件) |
| **agents/** | `agents/*.md` | Agent 定义 (Markdown 文件) |
| **skills/** | `skills/**/*.md` | 可复用技能目录 |
| **hooks/** | `hooks/hooks.json` | 生命周期钩子 |
| **output-styles/** | `output-styles/*.md` | 自定义输出样式 |
| **.mcp.json** | - | MCP 服务器配置 |

---

## 7. 实施任务清单

### Phase 11.1: 插件基础设施
- [ ] 实现 `plugins/base.py` - BasePlugin, PluginManifest
- [ ] 实现 `plugins/registry.py` - PluginRegistry
- [ ] 实现 `plugins/manifest.py` - 清单解析和验证

### Phase 11.2: 钩子系统
- [ ] 实现 `plugins/hooks/manager.py` - HookManager
- [ ] 实现 `plugins/hooks/definitions.py` - Hook 定义
- [ ] 实现 PreToolUse/PostToolUse 钩子
- [ ] 实现其他 25 种钩子类型

### Phase 11.3: 插件操作
- [ ] 实现 `plugins/operations.py` - PluginOperations
- [ ] 实现 install/uninstall/enable/disable
- [ ] 实现配置管理

### Phase 11.4: 内置插件
- [ ] 实现 `plugins/builtin.py` - BuiltinPluginRegistry
- [ ] 注册内置插件

### Phase 11.5: 插件加载器
- [ ] 实现 `plugins/loader.py` - PluginLoader
- [ ] 实现 npm/pip/git/github 源加载
- [ ] 实现版本缓存管理
