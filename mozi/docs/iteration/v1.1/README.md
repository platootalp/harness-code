# v1.1 版本说明

> **版本状态**: 已完成

## 版本目标

v1.1 版本聚焦于 `mozi/core/model/` 模块的 litellm 重构，提升模型调用层的统一性和可维护性。

## 主要变更

| 变更 | 说明 |
|------|------|
| Litellm 重构 | 将 OpenAIAdapter/AnthropicAdapter 合并为统一的 LitellmGateway |

## 交付物

| 交付物 | 路径 |
|--------|------|
| Litellm 重构设计 | [design/2026-04-02_litellm_refactoring_design.md](./design/2026-04-02_litellm_refactoring_design.md) |
| 开发计划 | [development/2026-04-02_development_plan.md](./development/2026-04-02_development_plan.md) |

## 开发任务

| 任务ID | 标题 | 预估时间 | 状态 |
|--------|------|----------|------|
| v1.1-model-litellm-001 | 添加 litellm 依赖 | 0.5h | ✅ 完成 |
| v1.1-model-litellm-002 | 创建 LitellmGateway 类 | 4h | ✅ 完成 |
| v1.1-model-litellm-003 | 更新 errors.py 添加错误映射 | 1h | ✅ 完成 |
| v1.1-model-litellm-004 | 替换 OpenAIAdapter | 2h | ✅ 完成 |
| v1.1-model-litellm-005 | 替换 AnthropicAdapter | 2h | ✅ 完成 |
| v1.1-model-litellm-006 | 删除废弃文件 | 0.5h | ✅ 完成 |
| v1.1-model-litellm-007 | 运行质量检查 | 1h | ✅ 完成 |
| v1.1-model-litellm-008 | 运行单元测试 | 2h | ✅ 完成 |
| v1.1-model-litellm-009 | 更新依赖导入 | 1h | ✅ 完成 |

## 状态

- [x] Phase 1: 基础设施
- [x] Phase 2: 适配器替换
- [x] Phase 3: 测试与验收

---

_版本: v1.0_
_更新日期: 2026-04-02_
