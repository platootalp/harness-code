# 技能使用指南

## 什么是技能（Skills）

技能是 Markdown 格式的文档，用于扩展 OpenHarness 的能力。技能可以被按需加载，兼容 Claude Code 的技能格式。

## 技能存放位置

技能可以从以下位置加载：

1. **内置技能** - `openharness/skills/bundled/`
2. **用户技能** - `~/.config/openharness/skills/`
3. **项目技能** - `.openharness/skills/`（项目目录内）
4. **插件技能** - 插件提供的技能

## 技能目录结构

用户技能目录结构：

```
~/.config/openharness/skills/
├── my-skill/
│   └── SKILL.md
└── another-skill/
    └── SKILL.md
```

## 使用技能

在 TUI 中使用 `/` 命令选择器来访问技能：

```
/my-skill
```

或使用技能工具：

```
/skill my-skill
```

## 创建自定义技能

创建技能只需要一个 `SKILL.md` 文件：

```markdown
---
name: my-custom-skill
description: 这是一个自定义技能的简短描述
---

# 我的自定义技能

这是技能的正文内容。

## 使用方法

当用户需要执行某些任务时调用此技能。
```

### frontmatter 字段

| 字段 | 说明 |
|------|------|
| `name` | 技能名称 |
| `description` | 简短描述（用于命令选择器显示） |
| `allowed-tools` | 允许使用的工具列表 |
| `disallowed-tools` | 禁止使用的工具列表 |

## 技能与插件的区别

| 特性 | 技能 | 插件 |
|------|------|------|
| 格式 | Markdown 文件 | 包含 plugin.json 的目录 |
| 复杂度 | 简单 | 复杂（可包含工具、命令、agent 等） |
| 加载方式 | 按需加载 | 启动时加载 |
| 适用场景 | 知识库、指南 | 扩展工具和命令 |

## 常用内置技能

OpenHarness 内置以下技能：

- `read` - 文件阅读技能
- `write` - 文件写作技能
- `search` - 搜索技能
- `bash` - Shell 命令技能

## 查看可用技能

```bash
# 在 TUI 中输入 / 即可看到技能列表
oh
```

## 技能最佳实践

1. **描述清晰** - 在 description 中准确描述技能用途
2. **命名规范** - 使用小写字母和连字符
3. **内容结构化** - 使用标题和列表提高可读性
4. **示例丰富** - 包含常见使用场景的示例

## 故障排除

### 技能不显示

1. 检查技能文件名是否为 `SKILL.md`
2. 确认技能目录在正确位置
3. 验证 frontmatter 格式正确
