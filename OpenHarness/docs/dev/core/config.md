# 配置系统

本文档介绍 OpenHarness 的配置系统，包括多层配置、Schema 和迁移。

## 概述

OpenHarness 使用多层配置系统，支持：
- 默认配置
- 配置文件 (`settings.json`)
- 环境变量
- CLI 参数

## 架构概览

```
src/openharness/config/
├── __init__.py          # 包初始化
├── paths.py             # 路径管理
├── schema.py            # 配置 Schema
├── settings.py          # 设置加载和解析
└── migrations.py        # 配置迁移
```

## 配置加载优先级

```
CLI 参数 > 环境变量 > 配置文件 (~/.openharness/settings.json) > 默认值
```

## 核心设置 (Settings)

### 主配置模型

```python
class Settings(BaseModel):
    # API 配置
    api_key: str = ""
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 16384
    base_url: str | None = None
    api_format: str = "anthropic"  # "anthropic", "openai", "copilot"
    provider: str = ""
    active_profile: str = "claude-api"
    profiles: dict[str, ProviderProfile] = Field(default_factory=default_provider_profiles)
    max_turns: int = 200

    # 行为配置
    system_prompt: str | None = None
    permission: PermissionSettings = Field(default_factory=PermissionSettings)
    hooks: dict[str, list[HookDefinition]] = Field(default_factory=dict)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    sandbox: SandboxSettings = Field(default_factory=SandboxSettings)
    enabled_plugins: dict[str, bool] = Field(default_factory=dict)
    mcp_servers: dict[str, McpServerConfig] = Field(default_factory=dict)

    # UI 配置
    theme: str = "default"
    output_style: str = "default"
    vim_mode: bool = False
    voice_mode: bool = False
    fast_mode: bool = False
    effort: str = "medium"
    passes: int = 1
    verbose: bool = False
```

## 权限设置 (PermissionSettings)

```python
class PermissionSettings(BaseModel):
    mode: PermissionMode = PermissionMode.DEFAULT
    allowed_tools: list[str] = []
    denied_tools: list[str] = []
    path_rules: list[PathRuleConfig] = []
    denied_commands: list[str] = []
```

## 记忆设置 (MemorySettings)

```python
class MemorySettings(BaseModel):
    enabled: bool = True
    max_files: int = 5
    max_entrypoint_lines: int = 200
```

## MCP 服务器配置 (McpServerConfig)

```python
class McpServerConfig(BaseModel):
    type: str = "stdio"  # "stdio" or "http"
    command: str | None = None
    args: list[str] = []
    env: dict[str, str] | None = None
    cwd: str | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
```

## 提供者配置 (ProviderProfile)

```python
class ProviderProfile(BaseModel):
    label: str
    provider: str
    api_format: str
    auth_source: str
    default_model: str
    base_url: str | None = None
    last_model: str | None = None
    credential_slot: str | None = None
    allowed_models: list[str] = []

    @property
    def resolved_model(self) -> str:
        return resolve_model_setting(...)
```

## 内置提供者

```python
def default_provider_profiles() -> dict[str, ProviderProfile]:
    return {
        "claude-api": ProviderProfile(
            label="Anthropic-Compatible API",
            provider="anthropic",
            api_format="anthropic",
            auth_source="anthropic_api_key",
            default_model="claude-sonnet-4-6",
        ),
        "claude-subscription": ProviderProfile(
            label="Claude Subscription",
            provider="anthropic_claude",
            api_format="anthropic",
            auth_source="claude_subscription",
            default_model="claude-sonnet-4-6",
        ),
        "openai-compatible": ProviderProfile(
            label="OpenAI-Compatible API",
            provider="openai",
            api_format="openai",
            auth_source="openai_api_key",
            default_model="gpt-5.4",
        ),
        "codex": ProviderProfile(
            label="Codex Subscription",
            provider="openai_codex",
            api_format="openai",
            auth_source="codex_subscription",
            default_model="gpt-5.4",
        ),
        "copilot": ProviderProfile(
            label="GitHub Copilot",
            provider="copilot",
            api_format="copilot",
            auth_source="copilot_oauth",
            default_model="gpt-5.4",
        ),
        "moonshot": ProviderProfile(
            label="Moonshot (Kimi)",
            provider="moonshot",
            api_format="openai",
            auth_source="moonshot_api_key",
            default_model="kimi-k2.5",
            base_url="https://api.moonshot.cn/v1",
        ),
    }
```

## 配置加载

### load_settings

```python
def load_settings(config_path: Path | None = None) -> Settings:
    """从配置文件加载设置"""
    if config_path is None:
        from openharness.config.paths import get_config_file_path
        config_path = get_config_file_path()

    if config_path.exists():
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        settings = Settings.model_validate(raw)

        # 兼容旧格式
        if "profiles" not in raw or "active_profile" not in raw:
            profile_name, profile = _profile_from_flat_settings(settings)
            merged_profiles = settings.merged_profiles()
            merged_profiles[profile_name] = profile
            settings = settings.model_copy(update={
                "active_profile": profile_name,
                "profiles": merged_profiles,
            })

        return _apply_env_overrides(settings.materialize_active_profile())

    return _apply_env_overrides(Settings().materialize_active_profile())
```

### 环境变量覆盖

```python
def _apply_env_overrides(settings: Settings) -> Settings:
    updates = {}

    if os.environ.get("ANTHROPIC_MODEL") or os.environ.get("OPENHARNESS_MODEL"):
        updates["model"] = ...

    if os.environ.get("ANTHROPIC_BASE_URL"):
        updates["base_url"] = ...

    # ... 更多环境变量

    if updates:
        return settings.model_copy(update=updates)

    return settings
```

### CLI 参数覆盖

```python
def merge_cli_overrides(self, **overrides: Any) -> Settings:
    """应用 CLI 参数覆盖"""
    updates = {k: v for k, v in overrides.items() if v is not None}
    return self.model_copy(update=updates)
```

## 配置保存

### save_settings

```python
def save_settings(settings: Settings, config_path: Path | None = None) -> None:
    """保存设置到配置文件"""
    if config_path is None:
        config_path = get_config_file_path()

    settings = settings.sync_active_profile_from_flat_fields()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        settings.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
```

## 路径管理

### 配置文件路径

```python
def get_config_dir() -> Path:
    """返回配置目录"""
    return Path(os.path.expanduser("~/.openharness"))


def get_config_file_path() -> Path:
    """返回配置文件路径"""
    return get_config_dir() / "settings.json"


def get_tasks_dir() -> Path:
    """返回任务目录"""
    return get_config_dir() / "tasks"


def get_memory_dir() -> Path:
    """返回记忆目录"""
    return get_config_dir() / "memory"


def get_plugins_dir() -> Path:
    """返回插件目录"""
    return get_config_dir() / "plugins"


def get_skills_dir() -> Path:
    """返回技能目录"""
    return get_config_dir() / "skills"
```

## 配置文件格式

### settings.json 示例

```json
{
  "active_profile": "claude-api",
  "profiles": {
    "claude-api": {
      "label": "Anthropic-Compatible API",
      "provider": "anthropic",
      "api_format": "anthropic",
      "auth_source": "anthropic_api_key",
      "default_model": "claude-sonnet-4-6"
    }
  },
  "permission": {
    "mode": "default",
    "path_rules": [
      {"pattern": "/etc/*", "allow": false}
    ]
  },
  "mcp_servers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"]
    }
  },
  "enabled_plugins": {
    "commit-commands": true
  }
}
```

## 配置迁移

### 迁移检查

```python
def migrate_if_needed(settings: Settings) -> Settings:
    """检查并执行配置迁移"""
    version = getattr(settings, "config_version", 1)

    if version < 2:
        settings = _migrate_v1_to_v2(settings)

    return settings


def _migrate_v1_to_v2(settings: Settings) -> Settings:
    """v1 到 v2 的迁移"""
    # 重命名字段
    # 更新默认值
    # 转换格式
    return settings.model_copy(update={"config_version": 2})
```

## 模型解析

### resolve_model_setting

```python
def resolve_model_setting(
    model_setting: str,
    provider: str,
    *,
    default_model: str | None = None,
    permission_mode: str | None = None,
) -> str:
    """解析用户模型设置为实际模型 ID"""
    configured = model_setting.strip()
    normalized = configured.lower()

    if not configured or normalized == "default":
        if is_claude_family_provider(provider):
            return "claude-sonnet-4-6"
        return "gpt-5.4"

    if is_claude_family_provider(provider):
        aliases = {
            "sonnet": "claude-sonnet-4-6",
            "opus": "claude-opus-4-6",
            "haiku": "claude-haiku-4-5",
            "best": "claude-opus-4-6",
        }
        if normalized in aliases:
            return aliases[normalized]

    return configured
```

## 与其他模块的关系

- **QueryEngine**: 使用配置创建引擎
- **PermissionChecker**: 权限设置
- **McpClientManager**: MCP 服务器配置
- **HookExecutor**: 钩子配置
- **PluginLoader**: 插件启用配置
