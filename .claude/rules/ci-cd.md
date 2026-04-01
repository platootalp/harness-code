# CI/CD 命令

## 质量门禁（阻断性）

- Python 代码必须通过 Ruff 格式检查
- Python 代码必须通过 mypy 严格类型检查
- TypeScript 代码必须通过 ESLint 检查
- TypeScript 代码必须通过 Prettier 检查
- TypeScript 代码必须通过 tsc 严格类型检查
- 单元测试覆盖率必须 ≥ 80%
- 整体测试覆盖率必须 ≥ 80%
- 核心模块覆盖率必须 ≥ 90%

## 安全扫描（阻断性）

- 禁止提交任何密钥或密码（truffleHog 扫描）
- Python 代码必须通过 bandit 安全扫描
- 依赖必须通过 pip-audit 扫描
- 依赖必须通过 npm audit 扫描
- 高危漏洞阻断合并

## CI 流程

- PR 触发完整 CI
- 代码检查失败阻断后续流程
- 安全检查失败阻断后续流程
- 测试失败阻断合并
- 覆盖率不足阻断合并

## 分支保护

- `main`: 要求 2 人审查 + CODEOWNERS + 线性历史
- `develop`: 要求 1 人审查 + 线性历史
- 两者都禁止强制推送和直接删除

## 发布

- 版本号遵循语义化版本
- `develop` 到 `main` 必须通过 PR
- 发布前必须完成文档同步

---
*版本: 1.0 | 生效: 立即*
