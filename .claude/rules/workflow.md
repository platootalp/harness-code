# Git 工作流命令

## 分支

- 禁止直接推送到 `main` 和 `develop`
- 禁止 `--force` 推送，允许 `--force-with-lease`
- 禁止 `git rebase --skip`
- 功能分支必须从 `develop` 检出
- 分支命名必须符合 `^(feature|fix|docs|refactor|hotfix)/[a-z0-9-]+$`
- 合并前必须 rebase 到最新 `develop`
- 使用线性历史（禁止 merge commit）

## 提交

- 提交信息格式: `type: subject`
- type 必须是: feat, fix, docs, refactor, test, ci, security, chore
- subject 使用祈使句，首字母大写，不超过 50 字符，无句号
- 禁止混合功能修改和格式化到同一提交

## PR

- 必须填完 PR 模板中的所有检查项
- `main` 需要 2 人审查，`develop` 需要 1 人
- 敏感配置变更需要 2 位 Maintainer
- CI 全绿才能合并
- 审查者必须勾选所有检查项才能批准

## 权限

- Owner: 修改保护规则
- Maintainer: 合并到 main/develop
- Contributor: 提交 PR

---
*版本: 1.0 | 生效: 立即*
