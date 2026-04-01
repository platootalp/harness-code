# 测试命令

## 结构

- 单元测试放在 `tests/unit/`
- 集成测试放在 `tests/integration/`
- E2E 测试放在 `tests/e2e/`
- 测试文件命名: `test_*.py`
- 测试类命名: `Test*`
- 测试函数命名: `test_*`

## 覆盖率

- 单元测试覆盖率 ≥ 80%
- 整体覆盖率 ≥ 80%
- 核心模块覆盖率 ≥ 90%
- 覆盖率不足阻断 CI

## 编写规范

- 使用 AAA 结构（Arrange, Act, Assert）
- 测试函数必须描述性命名
- 必须测试正常路径
- 必须测试边界条件
- 必须测试错误处理
- 使用 `@pytest.mark.parametrize` 测试多组数据
- 数据库测试使用内存数据库
- 外部服务必须 mock
- 禁止测试私有方法
- 禁止过度 mock
- 禁止使用 `sleep`
- 禁止依赖测试顺序

## 标记

- 单元测试标记 `@pytest.mark.unit`
- 集成测试标记 `@pytest.mark.integration`
- E2E 测试标记 `@pytest.mark.e2e`
- 慢测试标记 `@pytest.mark.slow`
- 跳过测试必须说明原因

---
*版本: 1.0 | 生效: 立即*
