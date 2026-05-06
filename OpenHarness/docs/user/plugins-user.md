# 插件使用指南

## 什么是插件

插件是 OpenHarness 的扩展系统，可以提供：
- 工具（Tools）
- 命令（Commands）
- 代理（Agents）
- Hooks
- MCP 服务器配置
- 技能（Skills）

插件兼容 Claude-style plugins 和 anthropics/skills 格式。

## 插件存放位置

1. **用户插件** - `~/.config/openharness/plugins/`
2. **项目插件** - `.openharness/plugins/`（项目目录内）
3. **额外插件根目录** - 可通过配置指定

## 管理插件

### 列出插件

```bash
oh plugin list
```

输出示例：

```
my-plugin [enabled] - 这是一个示例插件
another-plugin [disabled] - 另一个插件
```

### 安装插件

```bash
oh plugin install /path/to/plugin
oh plugin install https://github.com/user/plugin-repo
```

### 卸载插件

```bash
oh plugin uninstall my-plugin
```

## 插件结构

一个完整的插件目录结构：

```
my-plugin/
├── plugin.json          # 插件清单（必需）
├── skills/              # 技能目录
│   └── my-skill/
│       └── SKILL.md
├── commands/            # 命令目录
│   └── my-command.md
├── agents/              # 代理定义目录
│   └── my-agent.md
├── hooks/               # Hooks 配置
│   └── hooks.json
└── .mcp.json           # MCP 服务器配置
```

## plugin.json 清单

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "插件描述",
  "enabled_by_default": true,
  "skills_dir": "skills",
  "hooks_file": "hooks/hooks.json",
  "mcp_file": ".mcp.json",
  "commands": "commands",
  "agents": "agents"
}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `name` | 插件唯一名称 |
| `version` | 版本号 |
| `description` | 插件描述 |
| `enabled_by_default` | 是否默认启用 |
| `skills_dir` | 技能目录 |
| `hooks_file` | Hooks 配置文件路径 |
| `mcp_file` | MCP 服务器配置路径 |
| `commands` | 命令目录或命令映射 |
| `agents` | 代理定义目录 |

## 插件命令

插件可以提供 Markdown 格式的命令。

命令文件格式 (`my-command.md`)：

```markdown
---
name: my-command
description: 这是一个插件命令
argument-hint: <arg> [optional]
---

# 我的命令

这是命令的详细描述和使用说明。

## 使用示例

执行某个操作。
```

### 命令名称

命令名称格式：`plugin-name:namespace:command-name`

例如：`my-plugin:utils:deploy`

## 插件代理

插件可以定义自定义代理。

代理文件格式 (`my-agent.md`)：

```markdown
---
name: my-agent
description: 这是一个自定义代理
model: claude-sonnet-4
effort: medium
permissionMode: default
tools:
  - bash
  - read
  - write
skills:
  - my-skill
---

# 我的代理

这是代理的系统提示。
```

### 代理 frontmatter 字段

| 字段 | 说明 |
|------|------|
| `name` | 代理名称 |
| `description` | 代理描述 |
| `model` | 使用的模型（inherit 表示继承） |
| `effort` | 工作量级别：low、medium、high |
| `permissionMode` | 权限模式 |
| `tools` | 允许使用的工具列表 |
| `disallowedTools` | 禁止使用的工具列表 |
| `skills` | 附加的技能列表 |
| `maxTurns` | 最大对话轮数 |
| `background` | 是否以后台模式运行 |

## Hooks

插件可以定义 hooks 来拦截事件。

hooks.json 格式：

```json
{
  "on_tool_call": [
    {
      "type": "command",
      "command": "echo 'tool called: {tool_name}'"
    }
  ],
  "after_tool_call": [
    {
      "type": "prompt",
      "prompt": "添加后续提示"
    }
  ]
}
```

### 支持的 Hook 事件

- `before_agent_start` - Agent 启动前
- `after_agent_end` - Agent 结束后
- `on_tool_call` - 工具调用时
- `after_tool_call` - 工具调用后
- `on_command` - 命令执行时

## MCP 服务器配置

插件可以提供 MCP 服务器配置。

`.mcp.json` 格式：

```json
{
  "mcpServers": {
    "my-server": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    }
  }
}
```

## 插件开发

1. 创建插件目录结构
2. 编写 `plugin.json` 清单
3. 添加技能、命令、代理等组件
4. 测试插件功能
5. 安装并验证

## 常见问题

### 插件不加载

1. 检查 `plugin.json` 是否存在且格式正确
2. 确认插件目录在正确位置
3. 查看错误日志

### 插件命令不显示

1. 确认命令文件格式正确
2. 检查文件名是否为 `.md`
3. 验证 frontmatter 字段完整
