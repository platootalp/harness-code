---
name: create-rule
description: Use when creating new project rules or rule documentation files for Claude Code
---

# Create Rule

## Overview

Create consistent, high-quality rule documentation for Claude Code projects. Ensures all rules follow the standard format with proper frontmatter, structure, and content organization.

## Brevity Guidelines

**Keep rules concise and focused:**

- **Target length**: 50-100 lines (max 150)
- **Max sections**: 4 main sections, avoid `####` headers
- **Focus**: What makes this project *different* from standard practices
- **Omit**: Tutorials, code examples, edge cases, "nice to have" suggestions

**Writing style - Use imperative mood (祈使句):**
- ✅ DO: "使用环境变量存储密钥"
- ✅ DO: "禁止直接推送到 main 分支"
- ❌ DON'T: "你应该考虑使用环境变量..."
- ❌ DON'T: "建议避免直接推送..."

**Before adding content, ask:**
1. Will Claude forget this without being told?
2. Is this specific to this project (not general best practice)?
3. Can this be expressed in a table instead of paragraphs?

**Anti-patterns to avoid:**
- ❌ Explaining *why* a practice exists (Claude knows)
- ❌ Code examples (rules are instructions, not tutorials)
- ❌ "Consider..." or "You might want..." suggestions
- ❌ Deep nesting (1.1.1 subsections)

## When to Use

- Adding a new rule to `.claude/rules/`
- Creating project-specific guidelines
- Documenting coding standards, workflows, or conventions
- Migrating existing documentation to rule format

## Quick Reference

| Element | Required | Format |
|---------|----------|--------|
| Frontmatter | Yes | YAML with `name`, `description`, `triggers` |
| Title | Yes | Chinese, with (强制) or (推荐) suffix |
| Version footer | Yes | Rule version + update date |
| Tables | Common | For structured data like checklists |
| Code blocks | As needed | Must specify language |

## Rule Template

### Concise Template (Recommended)

```markdown
---
name: rule-name
description: One-line description of what this rule governs
triggers: ["keyword1", "keyword2"]
---

# 规则标题（强制/推荐）

## 1. 概述

1-2 句话说明规则目的和适用范围。

## 2. 具体要求

| 要求 | 说明 |
|------|------|
| 使用环境变量存储密钥 | 禁止硬编码任何敏感信息 |
| 推送前必须通过 CI 检查 | 禁止强制推送 |

## 3. 检查清单（如适用）

- [ ] 所有密钥通过环境变量注入
- [ ] CI 配置已启用

---

*规则版本: 1.0*
*更新日期: YYYY-MM-DD*
```

### Detailed Template (For Complex Rules)

```markdown
---
name: rule-name
description: Brief description of what this rule governs
triggers: ["keyword1", "keyword2", "keyword3"]
---

# 规则标题（强制/推荐）

## 1. 第一节标题

简要说明。

### 1.1 子节标题

| 列A | 列B |
|-----|-----|
| 值1 | 值2 |

---

## 2. 第二节标题

| 要求 | 说明 |
|------|------|
| 规定 1 | 使用祈使句描述 |
| 规定 2 | 禁止代码示例 |

---

*规则版本: 1.0*
*更新日期: YYYY-MM-DD*
```

## Frontmatter Requirements

**Required fields:**

```yaml
---
name: rule-name          # 小写，连字符分隔，无特殊字符
description: 一句话描述规则用途
triggers:                # 触发关键词数组
  - "keyword1"
  - "keyword2"
---
```

**Naming conventions:**
- `name`: 仅使用小写字母、数字、连字符
- `description`: 第三人称，简洁明了
- `triggers`: 3-5 个常用关键词

## Structure Guidelines

### 1. Title Format

```markdown
# 规则名称（强制）
# 或
# 规则名称（推荐）
```

- **强制**: CI 会检查并阻断不合规情况
- **推荐**: 建议遵循，但不会阻断 CI

### 2. Section Numbering

| 级别 | 格式 | 示例 |
|------|------|------|
| 一级 | `#` | 仅标题使用 |
| 二级 | `## N.` | `## 1. 分支模型` |
| 三级 | `### N.N.` | `### 1.1 分支定义` |
| 四级 | `####` | 尽量少用 |

### 3. Required Sections

For **强制** rules (minimum):
1. 规则概述（1-2 句话说明目的）
2. 具体要求（表格形式，核心规定）
3. 版本信息

For **推荐** rules (minimum):
1. 规则概述
2. 关键要点

### 4. Tables

Use tables for:
- 检查清单
- 对比信息
- 配置选项
- 权限分级

**Table style - imperative descriptions:**
| 检查项 | 要求 |
|--------|------|
| 代码格式检查 | 使用 Ruff 进行格式化 |
| 类型检查 | 使用 mypy 进行静态分析 |

## Content Patterns (Use Sparingly)

**Checklist** - For 3-5 critical items only, use imperative language:
- [ ] 配置 Ruff 进行代码格式化
- [ ] 启用 mypy 类型检查
- [ ] 设置 CI 自动检查

**Simple Table** - For requirements:
| 要求 | 处理方式 |
|------|----------|
| 禁止硬编码密钥 | 使用环境变量注入 |
| 禁止直接推送 main | 启用分支保护规则 |

**No code examples** - Rules are instructions, not tutorials. Claude already knows how to implement these practices.

Avoid: Deep permission matrices, severity tables unless absolutely necessary.

## File Location

```
project/
├── .claude/
│   └── rules/
│       ├── workflow.md      # Git 工作流
│       ├── ci-cd.md         # CI/CD 规范
│       ├── coding-style.md  # 代码风格
│       ├── testing.md       # 测试规范
│       └── documentation.md # 文档规范
```

## Version Footer

Every rule MUST end with:

```markdown
---

*规则版本: 1.0*
*更新日期: YYYY-MM-DD*
```

Update version when making significant changes.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Missing frontmatter | Add YAML header with name, description, triggers |
| No (强制)/(推荐) suffix | Add to title |
| Inconsistent numbering | Use `N.` and `N.N.` format |
| Missing version footer | Add at end of file |
| Broken table formatting | Ensure `|` alignment |

## Workflow

```
1. Determine rule scope → 强制 or 推荐
2. Create file in .claude/rules/
3. Write frontmatter
4. Add structured content
5. ⚠️ Review: Is it under 100 lines? Can any section be removed?
6. Add version footer
7. Test by asking Claude to follow the rule
```
