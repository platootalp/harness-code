# Mozi 功能测试问题记录

## 测试执行结果

| 测试类型 | 数量 | 通过 | 失败 | 覆盖率 |
|---------|-----|------|------|--------|
| 单元测试 | 555 | 555 | 0 | - |
| 集成测试 | 133 | 133 | 0 | - |
| E2E测试 | 14 | 14 | 0 | - |
| **总计** | **702** | **702** | **0** | **90%** |

## 代码质量检查

- [x] ruff check - 通过
- [x] mypy - 通过

---

## 测试覆盖率缺口 (按严重程度排序)

### 高优先级 - 核心功能未测试

#### 1. `mozi/core/model/litellm_gateway.py` - 67%

| 缺失代码 | 行号 | 原因 |
|---------|------|------|
| `invoke()` 方法整体 | 119-159 | 无测试 - 需要 mock litellm |
| `_parse_response` 异常处理 | 274-275 | ResponseParseError 未测试 |
| `LiteLLMAuthError` 处理 | 152-153 | 未测试 |
| `LiteLLMRateLimitError` 处理 | 154-155 | 未测试 |
| `LiteLLMInvalidRequestError` 处理 | 156-157 | 未测试 |
| 通用异常处理 | 158-159 | 未测试 |
| `_format_messages` name 字段 | 186-187 | message.name 属性未测试 |

#### 2. `mozi/orchestrator/integration.py` - 63%

| 缺失代码 | 行号 | 原因 |
|---------|------|------|
| `add_session_message()` 整体 | 437-480 | **无测试存在** |
| `get_session_messages()` 整体 | 482-517 | **无测试存在** |
| `get_integration()` 单例 | 524-552 | **无测试存在** |
| `publish_context_built` | 263-283 | 未直接测试 |
| `publish_memory_retrieved` | 285-305 | 未直接测试 |
| `build_context` 错误路径 | 337-341 | 未测试 |
| `build_context` context_builder=None | 321-322 | 未测试 |
| `store_memory` 错误路径 | 431-435 | 未测试 |
| `retrieve_memories` 错误路径 | 381-386 | 未测试 |

### 中优先级 - 功能部分覆盖

#### 3. `mozi/orchestrator/workers/explorer.py` - 70%

| 缺失代码 | 行号 | 原因 |
|---------|------|------|
| `"search_codebase"` action | 46-51 | 只测试了 fallback |
| `"get_file_info"` action | 52-53 | 未测试 |
| `"explore_structure"` action | 54-55 | 未测试 |
| `get_file_info` - 目录情况 | 137-141 | 只测试了不存在的情况 |
| `explore_structure` PermissionError | 234-235 | 未测试 |

#### 4. `mozi/orchestrator/workers/coder.py` - 78%

| 缺失代码 | 行号 | 原因 |
|---------|------|------|
| `apply_diff` 实际写入路径 | 128-136 | 只测了 dry_run=True |
| `validate_change` 大变更警告 (>500行) | 211-212 | 未测试 |
| `validate_change` `import *` 警告 | 196-197 | 未测试 |
| `validate_change` 仅警告无问题 | 214-219 | 未测试 |
| `_apply_diff_to_content` 整体 | 264-322 | **无直接测试** |
| `_validate_python_syntax` 整体 | 324-342 | **无直接测试** |

#### 5. `mozi/session/storage.py` - 72%

| 缺失代码 | 行号 | 原因 |
|---------|------|------|
| 抽象基类接口直接测试 | - | 72% 通过实现测试间接覆盖 |

---

## 迭代计划

### 迭代 1: 补全 integration.py 测试 ✅ 完成
- [x] `add_session_message()` 测试 (5 tests)
- [x] `get_session_messages()` 测试 (4 tests)
- [x] `get_integration()` 单例测试 (3 tests)
- [x] 错误路径测试 (已包含在上述测试中)
- **结果**: 25 个新测试，覆盖率 63% → 100%

### 迭代 2: 补全 coder.py 测试 ✅ 完成
- [x] `_apply_diff_to_content` 直接测试 (4 tests)
- [x] `apply_diff` 实际写入测试 (dry_run=False)
- [x] `validate_change` 各种警告路径测试
- [x] 新增 17 个测试，覆盖率 78% → 90%
- **发现 bug**: `_apply_diff_to_content` 没有正确跳过 diff header 行

### 迭代 3: 补全 explorer.py 测试 ✅ 完成
- [x] `execute()` 各 action 处理测试 (3 tests)
- [x] PermissionError 测试
- [x] 各种文件类型测试
- [x] 新增 11 个测试，覆盖率 70% → 94%

### 剩余缺口 (中低优先级)

#### `mozi/core/model/litellm_gateway.py` - 67%
- `invoke()` 方法需要 mock litellm 库
- 建议后续迭代解决

#### `mozi/session/storage.py` - 72%
- 抽象基类，72% 覆盖通过实现测试间接覆盖

#### 基础设施模块
- `infrastructure/database.py` - 84%
- `infrastructure/vector_db.py` - 84%

### 迭代 2: 补全 litellm_gateway.py 测试
- [ ] `invoke()` 方法 mock 测试
- [ ] 各异常处理路径测试

### 迭代 3: 补全 coder.py 测试
- [ ] `_apply_diff_to_content` 直接测试
- [ ] `apply_diff` 实际写入测试 (dry_run=False)
- [ ] 各种警告路径测试

### 迭代 4: 补全 explorer.py 测试
- [ ] 各 action 处理测试
- [ ] 权限错误测试

---

## 更新记录

- 2026-04-02: 初始测试执行，发现 90% 覆盖率，启动迭代 1
- 2026-04-02: 迭代 1 完成 - integration.py 100%，新增 25 个测试
- 2026-04-02: 迭代 2 完成 - coder.py 90%，新增 17 个测试，发现 bug
- 2026-04-02: 迭代 3 完成 - explorer.py 94%，新增 11 个测试
- **当前总计**: 755 测试，覆盖率 93%
