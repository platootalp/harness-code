# ohmo 整体架构

ohmo 是 OpenHarness 的个人 Agent 应用，基于 OpenHarness 构建，提供 workspace、gateway、channels 三个子系统的整合。

## 架构概览

```
ohmo/
├── __init__.py
├── __main__.py          # 入口点: python -m ohmo
├── cli.py               # CLI 命令定义
├── workspace.py         # Workspace 初始化和路径管理
├── memory.py            # 个人记忆系统
├── prompts.py           # Prompt 模板构建
├── runtime.py           # Runtime 配置
├── session_storage.py   # 会话持久化
└── gateway/
    ├── __init__.py
    ├── service.py        # Gateway 服务生命周期
    ├── runtime.py        # OhmoSessionRuntimePool
    ├── bridge.py         # OhmoGatewayBridge
    ├── router.py         # session_key 路由
    ├── config.py         # 配置加载/保存
    └── models.py         # GatewayConfig / GatewayState
```

## 核心设计

### Workspace 目录结构

```
~/.ohmo/  (或 OHMO_WORKSPACE 环境变量指定)
├── soul.md          # ohmo 的人设定义
├── user.md          # 用户画像
├── identity.md      # ohmo 身份标识
├── BOOTSTRAP.md     # 首次启动引导
├── state.json       # 应用状态
├── gateway.json     # Gateway 配置
├── memory/          # 持久化记忆
│   └── MEMORY.md
├── skills/          # 个人技能
├── plugins/         # 个人插件
├── sessions/         # 会话历史
├── logs/            # 日志文件
│   └── gateway.log
└── attachments/     # 渠道附件下载
```

### Workspace 模板文件

| 文件 | 用途 |
|------|------|
| `soul.md` | 定义 ohmo 的核心人设和价值观 |
| `user.md` | 学习用户的偏好、工作习惯 |
| `identity.md` | ohmo 的名称、风格、签名 |
| `BOOTSTRAP.md` | 首次启动的引导对话 |
| `gateway.json` | Gateway 配置（Provider、渠道等） |

## 三子系统关系

```
┌──────────────────────────────────────────────────────┐
│                    ohmo CLI                          │
└──────────────────────────────────────────────────────┘
           │                           │
           ▼                           ▼
┌─────────────────────┐      ┌─────────────────────┐
│      Workspace      │      │       Gateway        │
│  - soul.md          │      │  - OhmoGatewayService│
│  - user.md          │◄────►│  - OhmoGatewayBridge │
│  - memory/          │      │  - RuntimePool       │
│  - skills/          │      │  - ChannelManager    │
└─────────────────────┘      └─────────────────────┘
                                         │
                                         ▼
                               ┌─────────────────────┐
                               │      Channels       │
                               │  Telegram/Slack/    │
                               │  Discord/Feishu/... │
                               └─────────────────────┘
```

## Workspace 初始化

源码：`ohmo/workspace.py`

```python
def initialize_workspace(workspace: str | Path | None = None) -> Path:
    """创建 workspace 并在缺失时填充模板文件"""
    root = ensure_workspace(workspace)
    
    # 模板文件: soul.md, user.md, identity.md, BOOTSTRAP.md, memory/MEMORY.md
    for path, content in templates.items():
        if not path.exists():
            path.write_text(...)
    
    # 创建 gateway.json（如果不存在）
    if not gateway_path.exists():
        gateway_path.write_text(json.dumps({
            "provider_profile": "codex",
            "enabled_channels": [],
            ...
        }))
    
    return root
```

## Prompt 构建

源码：`ohmo/prompts.py`

```python
def build_ohmo_system_prompt(
    cwd: str | Path,
    *,
    workspace: str | Path | None = None,
    extra_prompt: str | None = None,
    include_project_memory: bool = False,
) -> str:
    """构建 ohmo session 的 system prompt"""
    sections = [get_base_system_prompt()]
    
    # 按顺序拼接: soul → identity → user → bootstrap → workspace info → memory
    if soul := _read_text(get_soul_path(root)):
        sections.extend(["# ohmo Soul", soul])
    if identity := _read_text(get_identity_path(root)):
        sections.extend(["# ohmo Identity", identity])
    if user := _read_text(get_user_path(root)):
        sections.extend(["# User Profile", user])
    if bootstrap := _read_text(get_bootstrap_path(root)):
        sections.extend(["# First-Run Bootstrap", bootstrap])
    
    return "\n\n".join(section for section in sections if section)
```

## Session 持久化

源码：`ohmo/session_storage.py`

`OhmoSessionBackend` 负责：
- 保存会话快照（消息历史、usage、系统 prompt）
- 按 `session_key` 恢复会话
- 清理过期会话

## CLI 命令

源码：`ohmo/cli.py`

```bash
ohmo start              # 启动 ohmo 对话
ohmo gateway           # Gateway 管理
ohmo gateway run       # 运行 Gateway（前台）
ohmo gateway start     # 后台启动 Gateway
ohmo gateway stop      # 停止 Gateway
ohmo gateway status    # 查看 Gateway 状态
ohmo config            # 配置 ohmo
ohmo workspace health  # 检查 workspace 状态
```

## 与 OpenHarness 的关系

- **Runtime 复用**：ohmo 使用 `openharness.ui.runtime` 中的 `RuntimeBundle`
- **Channels 复用**：ohmo gateway 使用 `openharness.channels` 中的所有渠道
- **工具/技能复用**：ohmo 从 workspace 的 `skills/` 和 `plugins/` 加载扩展

## 扩展指南

### 自定义人设

编辑 `~/.ohmo/soul.md`，定义 ohmo 的行为准则和风格。

### 添加个人技能

在 `~/.ohmo/skills/` 添加 `.md` 技能文件（兼容 Claude Code 格式）。

### 添加个人插件

在 `~/.ohmo/plugins/` 添加插件代码（遵循 OpenHarness 插件接口）。

### 修改 Gateway 配置

编辑 `~/.ohmo/gateway.json`：
```json
{
    "provider_profile": "anthropic",
    "enabled_channels": ["telegram", "slack"],
    "session_routing": "chat-thread",
    "send_progress": true,
    "send_tool_hints": true
}
```

## 关键文件

| 文件 | 职责 |
|------|------|
| `workspace.py` | Workspace 初始化、路径管理、模板 |
| `prompts.py` | ohmo 专属 prompt 构建 |
| `session_storage.py` | 会话快照持久化 |
| `runtime.py` | Runtime 配置 |
| `memory.py` | 个人记忆系统 |
| `cli.py` | CLI 命令入口 |
| `gateway/service.py` | Gateway 服务生命周期 |
| `gateway/runtime.py` | Session Runtime Pool |
| `gateway/bridge.py` | Gateway Bridge |
| `gateway/router.py` | Session 路由 |
| `gateway/config.py` | Gateway 配置管理 |
