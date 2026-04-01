# v1.1 Litellm 重构开发计划

> **版本**: v1.0
> **日期**: 2026-04-02
> **负责人**: 待定
> **计划周期**: 5 天

---

## 1. 概述

### 1.1 目标

将 `mozi/core/model/` 模块从直接 HTTP 调用重构为使用 litellm 统一网关，消除重复代码，统一模型调用接口。

### 1.2 范围

- 新增 `LitellmGateway` 替代 `OpenAIAdapter` 和 `AnthropicAdapter`
- 更新 `ModelRegistry` 注册逻辑
- 更新 `errors.py` 添加 litellm 错误映射
- 删除 `circuit_breaker.py` 和 `retry.py`
- 确保上游代码（如 `ModelService`）无需修改

---

## 2. 任务分解

### Phase 1: 基础设施（第 1-2 天）

#### Task 1.1: 添加 litellm 依赖

| 字段 | 内容 |
|------|------|
| **任务ID** | `v1.1-model-litellm-001` |
| **标题** | 添加 litellm 依赖 |
| **类型** | chore |
| **预估时间** | 0.5 小时 |
| **验收标准** | litellm 已添加到 pyproject.toml dependencies |

**操作步骤**:
1. 编辑 `pyproject.toml`
2. 添加 `"litellm>=1.0.0"` 到 dependencies

---

#### Task 1.2: 创建 LitellmGateway 类

| 字段 | 内容 |
|------|------|
| **任务ID** | `v1.1-model-litellm-002` |
| **标题** | 创建 LitellmGateway 类 |
| **类型** | feat |
| **预估时间** | 4 小时 |
| **验收标准** | LitellmGateway 继承 ModelAdapter，实现所有抽象方法 |

**操作步骤**:
1. 创建 `mozi/core/model/litellm_gateway.py`
2. 实现 `__init__` - 初始化 litellm 客户端
3. 实现 `provider` property - 返回 ModelProvider
4. 实现 `supported_models` property - 返回支持的模型列表
5. 实现 `get_model_info()` - 获取模型信息
6. 实现 `validate_request()` - 请求验证
7. 实现 `_format_messages()` - 消息格式转换
8. 实现 `_parse_response()` - 响应解析
9. 添加 `SUPPORTED_MODELS` 字典配置

**依赖**: `v1.1-model-litellm-001`

---

#### Task 1.3: 更新 errors.py 添加错误映射

| 字段 | 内容 |
|------|------|
| **任务ID** | `v1.1-model-litellm-003` |
| **标题** | 更新 errors.py 添加 litellm 错误映射 |
| **类型** | refactor |
| **预估时间** | 1 小时 |
| **验收标准** | LITELLM_ERROR_MAP 已定义，map_litellm_error() 函数可用 |

**操作步骤**:
1. 编辑 `mozi/core/model/errors.py`
2. 添加 `LITELLM_ERROR_MAP` 字典
3. 添加 `map_litellm_error()` 函数

**依赖**: 无

---

### Phase 2: 适配器替换（第 3-4 天）

#### Task 2.1: 替换 OpenAIAdapter

| 字段 | 内容 |
|------|------|
| **任务ID** | `v1.1-model-litellm-004` |
| **标题** | 替换 OpenAIAdapter 为 LitellmGateway |
| **类型** | refactor |
| **预估时间** | 2 小时 |
| **验收标准** | OpenAI 模型调用通过 LitellmGateway |

**操作步骤**:
1. 编辑 `mozi/core/model/__init__.py`
2. 替换 `OpenAIAdapter` import 为 `LitellmGateway`
3. 编辑 `mozi/core/model/registry.py` 或初始化代码
4. 使用 `LitellmGateway(provider=ModelProvider.OPENAI, api_key=...)` 替换

**依赖**: `v1.1-model-litellm-002`, `v1.1-model-litellm-003`

---

#### Task 2.2: 替换 AnthropicAdapter

| 字段 | 内容 |
|------|------|
| **任务ID** | `v1.1-model-litellm-005` |
| **标题** | 替换 AnthropicAdapter 为 LitellmGateway |
| **类型** | refactor |
| **预估时间** | 2 小时 |
| **验收标准** | Anthropic 模型调用通过 LitellmGateway |

**操作步骤**:
1. 替换 `AnthropicAdapter` import
2. 使用 `LitellmGateway(provider=ModelProvider.ANTHROPIC, api_key=...)` 替换

**依赖**: `v1.1-model-litellm-004`

---

#### Task 2.3: 删除废弃文件

| 字段 | 内容 |
|------|------|
| **任务ID** | `v1.1-model-litellm-006` |
| **标题** | 删除废弃的适配器文件 |
| **类型** | chore |
| **预估时间** | 0.5 小时 |
| **验收标准** | openai.py、anthropic.py、circuit_breaker.py、retry.py 已删除 |

**操作步骤**:
1. 删除 `mozi/core/model/openai.py`
2. 删除 `mozi/core/model/anthropic.py`
3. 删除 `mozi/core/model/circuit_breaker.py`
4. 删除 `mozi/core/model/retry.py`
5. 更新 `__init__.py` 中的 exports

**依赖**: `v1.1-model-litellm-005`

---

### Phase 3: 测试与验收（第 5 天）

#### Task 3.1: 运行质量检查

| 字段 | 内容 |
|------|------|
| **任务ID** | `v1.1-model-litellm-007` |
| **标题** | 运行 ruff、mypy 检查 |
| **类型** | chore |
| **预估时间** | 1 小时 |
| **验收标准** | ruff 和 mypy 检查全部通过 |

**操作步骤**:
```bash
ruff check mozi/core/model/
mypy mozi/core/model/ --strict
```

**依赖**: `v1.1-model-litellm-006`

---

#### Task 3.2: 运行单元测试

| 字段 | 内容 |
|------|------|
| **任务ID** | `v1.1-model-litellm-008` |
| **标题** | 运行单元测试 |
| **类型** | test |
| **预估时间** | 2 小时 |
| **验收标准** | 单元测试覆盖率 ≥ 80%，全部通过 |

**操作步骤**:
```bash
pytest tests/unit/test_model/ -v --cov=mozi.core.model --cov-report=term-missing
```

**依赖**: `v1.1-model-litellm-007`

---

#### Task 3.3: 更新依赖导入

| 字段 | 内容 |
|------|------|
| **任务ID** | `v1.1-model-litellm-009` |
| **标题** | 更新所有依赖 ModelAdapter 的代码 |
| **类型** | refactor |
| **预估时间** | 1 小时 |
| **验收标准** | 无 import 错误 |

**操作步骤**:
1. 检查所有 import `openai.py`、`anthropic.py`、`circuit_breaker.py`、`retry.py` 的文件
2. 更新 import 路径
3. 确认无遗漏

**依赖**: `v1.1-model-litellm-006`

---

## 3. 任务依赖关系

```
[v1.1-model-litellm-001] litellm 依赖
           │
           ▼
[v1.1-model-litellm-002] LitellmGateway 类
           │
           ▼
[v1.1-model-litellm-003] 错误映射
           │
           ├──────────────────┐
           ▼                  ▼
[v1.1-model-litellm-004]  [v1.1-model-litellm-005]
   替换 OpenAI            替换 Anthropic
           │                  │
           └────────┬─────────┘
                    ▼
        [v1.1-model-litellm-006] 删除废弃文件
                    │
                    ▼
        [v1.1-model-litellm-009] 更新依赖导入
                    │
                    ▼
        [v1.1-model-litellm-007] 质量检查
                    │
                    ▼
        [v1.1-model-litellm-008] 单元测试
```

---

## 4. 里程碑

| 里程碑 | 日期 | 说明 |
|--------|------|------|
| M1: 基础设施完成 | 第 2 天 | LitellmGateway 核心实现完成 |
| M2: 适配器替换完成 | 第 4 天 | OpenAI/Anthropic 全部迁移完成 |
| M3: 发布验收 | 第 5 天 | 测试通过，可以合并 |

---

## 5. 资源分配

| 角色 | 职责 |
|------|------|
| 开发 | 实现 LitellmGateway、替换适配器、清理废弃代码 |
| 测试 | 编写/运行单元测试、集成测试 |

---

## 6. 风险登记

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|---------|
| litellm API 变更 | 中 | 低 | 版本锁定，发现问题及时回滚 |
| 上游代码不兼容 | 高 | 中 | 保持 ModelAdapter 接口不变 |
| 测试覆盖率不足 | 中 | 中 | 提前编写测试用例 |

---

## 7. 验收标准

| 标准 | 指标 |
|------|------|
| 功能 | OpenAI 和 Anthropic 模型调用正常 |
| 质量 | ruff、mypy 检查通过 |
| 测试 | 单元测试覆盖率 ≥ 80% |
| 代码 | 无废弃文件残留 |
| 文档 | 设计文档已更新 |

---

_版本: v1.0_
_更新日期: 2026-04-02_

## 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-04-02 | 初始版本 |
