# 权限模式说明

## 概述

OpenHarness 提供多级权限系统，确保操作安全可控。权限模式控制哪些操作需要用户确认。

## 权限模式

| 模式 | 说明 |
|------|------|
| `default` | 默认模式，修改操作需用户确认 |
| `plan` | 计划模式，只读操作可用，阻止修改操作 |
| `full_auto` | 全自动模式，所有操作直接执行 |

### default 模式

默认模式，对危险操作进行确认：

- **只读操作** - 自动允许（文件读取、搜索等）
- **修改操作** - 需要用户确认（文件编辑、删除、shell 命令等）
- **敏感操作** - 始终拒绝（访问 SSH 密钥、AWS 凭据等）

### plan 模式

计划模式，冻结所有修改操作：

- 所有修改操作被阻止
- 适合制定计划、审查代码
- 使用 `/plan` 命令进入计划模式
- 使用 `/exit-plan` 退出计划模式

### full_auto 模式

全自动模式，所有操作直接执行：

- 适合自动化脚本
- 无需任何确认
- **警告**：请确保了解操作风险后再使用

## 切换权限模式

### 在 TUI 中切换

```
/permissions
```

选择所需的权限模式。

### 命令行指定

```bash
oh -p "任务" --permission-mode full_auto
oh --permission-mode plan
```

## 路径规则

除了权限模式，OpenHarness 还支持路径级别的访问控制。

### 配置路径规则

在 `settings.json` 中配置：

```json
{
  "permission_mode": "default",
  "path_rules": [
    {"pattern": "**/node_modules/**", "allow": true},
    {"pattern": "**/.git/**", "allow": false},
    {"pattern": "**/secrets/**", "allow": false}
  ]
}
```

### 规则说明

- `pattern` - fnmatch 格式的路径模式
- `allow` - true 允许访问，false 拒绝访问

### 示例

| 模式 | 说明 |
|------|------|
| `**/node_modules/**` | node_modules 目录下的所有文件 |
| `**/.git/**` | .git 目录下的所有文件 |
| `src/**/*.py` | src 目录下所有 Python 文件 |
| `/tmp/*` | /tmp 目录下的直接文件 |

## 工具黑名单/白名单

### 禁用特定工具

```json
{
  "denied_tools": ["bash", "write"]
}
```

### 仅允许特定工具

```json
{
  "allowed_tools": ["read", "glob", "grep"]
}
```

**注意**：`allowed_tools` 和 `denied_tools` 不要同时使用。

## 命令拒绝模式

可以拒绝特定的命令模式：

```json
{
  "denied_commands": [
    "rm -rf /*",
    "dd if=* of=/dev/*",
    "mkfs.*"
  ]
}
```

使用 fnmatch 格式匹配。

## 敏感路径保护

OpenHarness 内置了对敏感路径的保护，这些路径无论在什么权限模式下都无法访问：

| 路径模式 | 保护内容 |
|----------|----------|
| `*/.ssh/*` | SSH 密钥 |
| `*/.aws/credentials` | AWS 凭据 |
| `*/.aws/config` | AWS 配置 |
| `*/.config/gcloud/*` | GCP 凭据 |
| `*/.azure/*` | Azure 凭据 |
| `*/.gnupg/*` | GPG 密钥 |
| `*/.docker/config.json` | Docker 凭据 |
| `*/.kube/config` | Kubernetes 凭据 |
| `*/.openharness/credentials.json` | OpenHarness 凭据 |

## 交互式确认

在 default 模式下，遇到修改操作会显示：

```
确认操作

工具：bash
命令：rm -rf __pycache__
目录：/path/to/project

是否允许执行？ [y/n]
```

- `y` - 允许执行
- `n` - 拒绝执行
- `a` - 允许本次会话所有后续操作（危险）

## MCP 工具权限

MCP 服务器提供的工具也受权限模式控制：

- 只读 MCP 工具通常自动允许
- 修改性 MCP 工具需要确认
- 可通过 `allowed_tools` / `denied_tools` 精细控制

## 权限模式适用场景

| 场景 | 推荐模式 |
|------|----------|
| 日常开发 | `default` |
| 代码审查 | `plan` |
| 自动化脚本 | `full_auto` |
| 首次使用 | `default` |
| 演示/教学 | `plan` |

## 配置文件示例

完整的权限配置：

```json
{
  "permission_mode": "default",
  "allowed_tools": [],
  "denied_tools": ["dangerous_tool"],
  "path_rules": [
    {"pattern": "**/node_modules/**", "allow": true},
    {"pattern": "**/.git/**", "allow": false},
    {"pattern": "**/secrets/**", "allow": false}
  ],
  "denied_commands": [
    "rm -rf /*",
    "sudo *"
  ]
}
```

## 最佳实践

1. **日常开发** - 使用 `default` 模式
2. **不熟悉的代码** - 先用 `plan` 模式审查
3. **自动化** - 使用 `full_auto` 但确保输入可信
4. **共享环境** - 配置严格的 `path_rules`
5. **敏感项目** - 添加项目特定的路径规则
