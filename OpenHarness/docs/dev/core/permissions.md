# 权限系统 (Permissions System)

## 概述

OpenHarness 权限系统提供多层次的安全控制，确保 Agent 操作符合用户意图。系统支持权限模式、路径规则、命令模式匹配等多维度控制，并与工具执行流程深度集成。

## 权限模式 (`permissions/modes.py`)

```python
class PermissionMode(str, Enum):
    """支持的权限模式"""
    DEFAULT = "default"    # 默认模式：只读自动放行，写操作需确认
    PLAN = "plan"          # 计划模式：阻止所有写操作
    FULL_AUTO = "full_auto" # 完全自动：允许所有操作
```

### 权限模式对比

| 模式 | 读操作 | 写操作 | 使用场景 |
|------|--------|--------|----------|
| `default` | 自动放行 | 需确认 | 日常开发 |
| `plan` | 自动放行 | 阻止 | 大型重构、审查优先 |
| `full_auto` | 自动放行 | 自动放行 | 沙箱环境 |

## PermissionChecker (`permissions/checker.py`)

权限检查器是权限系统的核心组件：

```python
class PermissionChecker:
    def __init__(self, settings: PermissionSettings) -> None:
        self._settings = settings
        self._path_rules: list[PathRule] = []

    def evaluate(
        self,
        tool_name: str,
        *,
        is_read_only: bool,
        file_path: str | None = None,
        command: str | None = None,
    ) -> PermissionDecision:
```

### PermissionDecision

```python
@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool                        # 是否允许执行
    requires_confirmation: bool = False  # 是否需要用户确认
    reason: str = ""                    # 原因描述
```

## 敏感路径保护

内置的敏感路径模式始终生效，无法被用户配置覆盖：

```python
SENSITIVE_PATH_PATTERNS: tuple[str, ...] = (
    # SSH 密钥
    "*/.ssh/*",
    # AWS 凭证
    "*/.aws/credentials",
    "*/.aws/config",
    # GCP 凭证
    "*/.config/gcloud/*",
    # Azure 凭证
    "*/.azure/*",
    # GPG 密钥
    "*/.gnupg/*",
    # Docker 凭证
    "*/.docker/config.json",
    # Kubernetes 凭证
    "*/.kube/config",
    # OpenHarness 自身凭证存储
    "*/.openharness/credentials.json",
    "*/.openharness/copilot_auth.json",
)
```

## 权限检查流程

```
PermissionChecker.evaluate()
        │
        ▼
┌───────────────────────────┐
│ 1. 敏感路径检查            │ ← 内置、不可覆盖
│    fnmatch(file_path,     │
│    SENSITIVE_PATH_PATTERNS)│
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│ 2. 显式工具拒绝列表        │
│    denied_tools          │
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│ 3. 显式工具允许列表        │
│    allowed_tools         │
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│ 4. 路径规则匹配           │
│    path_rules (glob)     │
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│ 5. 命令模式匹配           │
│    denied_commands        │
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│ 6. 权限模式评估            │
│    default / plan /       │
│    full_auto              │
└───────────────────────────┘
```

## 路径规则 (`PathRule`)

```python
@dataclass(frozen=True)
class PathRule:
    pattern: str   # glob 模式
    allow: bool    # True = 允许, False = 拒绝
```

### 配置示例

```json
{
  "permission": {
    "mode": "default",
    "path_rules": [
      {"pattern": "/etc/*", "allow": false},
      {"pattern": "~/projects/safe/*", "allow": true},
      {"pattern": "*.md", "allow": true}
    ],
    "denied_commands": [
      "rm -rf /*",
      "DROP TABLE *"
    ]
  }
}
```

## PermissionSettings

```python
class PermissionSettings(BaseModel):
    mode: PermissionMode = PermissionMode.DEFAULT
    allowed_tools: list[str] = []        # 显式允许的工具列表
    denied_tools: list[str] = []         # 显式拒绝的工具列表
    path_rules: list[PathRuleConfig] = [] # glob 路径规则
    denied_commands: list[str] = []    # 命令模式拒绝列表
```

## 与工具执行的集成

在 `_execute_tool_call()` 中的调用流程：

```python
# 1. 路径解析
_file_path = _resolve_permission_file_path(context.cwd, tool_input, parsed_input)
_command = _extract_permission_command(tool_input, parsed_input)

# 2. 权限评估
decision = context.permission_checker.evaluate(
    tool_name,
    is_read_only=tool.is_read_only(parsed_input),
    file_path=_file_path,
    command=_command,
)

# 3. 处理决策
if not decision.allowed:
    if decision.requires_confirmation:
        # 需要用户确认
        confirmed = await context.permission_prompt(tool_name, decision.reason)
        if not confirmed:
            return ToolResultBlock(content=f"Permission denied for {tool_name}", is_error=True)
    else:
        # 直接拒绝
        return ToolResultBlock(content=decision.reason, is_error=True)
```

## 命令模式匹配

使用 `fnmatch` 进行 shell 风格模式匹配：

```python
# denied_commands 示例
"rm -rf /*"          # 匹配确切的 rm -rf /
"rm -rf *"           # 匹配任意 rm -rf
"DROP TABLE *"        # 匹配 DROP TABLE 命令
```

## 权限模式切换

通过命令切换权限模式：

```bash
/permissions set default  # 默认模式
/permissions set plan      # 计划模式
/permissions set full_auto # 完全自动

/plan on                   # 进入计划模式
/plan off                  # 退出计划模式
```

## 设计决策

### 1. 敏感路径不可覆盖

内置的 `SENSITIVE_PATH_PATTERNS` 是防御纵深措施，即使管理员配置错误也不会被覆盖。

### 2. 显式优于隐式

拒绝列表和允许列表的优先级高于权限模式，确保细粒度控制始终生效。

### 3. 路径规范化

所有路径在检查前都会被规范化为绝对路径：
- 展开 `~` 到用户主目录
- 相对路径相对于 `cwd` 解析
- 使用 `Path.resolve()` 获取规范路径

## 扩展点

### 1. 添加新的权限模式

```python
class PermissionMode(str, Enum):
    DEFAULT = "default"
    PLAN = "plan"
    FULL_AUTO = "full_auto"
    STRICT = "strict"  # 新模式：所有操作需确认
```

### 2. 自定义敏感路径

```python
# 在 PermissionChecker.__init__ 中添加
self._extra_sensitive_patterns = extra_patterns
```

### 3. 自定义命令匹配器

```python
def _matches_command(command: str, pattern: str) -> bool:
    # 支持正则表达式匹配
    import re
    return re.match(pattern, command) is not None
```

## 关键文件

| 文件 | 职责 |
|------|------|
| `permissions/modes.py` | PermissionMode 枚举定义 |
| `permissions/checker.py` | PermissionChecker 权限检查器 |
| `permissions/__init__.py` | 公共导出 |
| `config/settings.py` | PermissionSettings 配置模型 |
