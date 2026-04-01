# Mozi 项目开发任务分解

> **版本**: v1.0
> **日期**: 2026-03-31
> **状态**: 规划中

---

## 任务分解原则

- **原子性**: 每个任务不可再分，可在 1-2 天内完成
- **可验证**: 每个任务有明确的验收标准
- **可追踪**: 每个任务关联里程碑和迭代

---

## Phase 0: 基础设施搭建（第 1-2 周）

### M0.1: 项目骨架完成（第 1 周）

#### T0.1.1: 目录结构创建

**任务**: 创建项目目录结构

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T0.1.1.1 | 创建 mozi 包目录 | `mozi/__init__.py` | 包可导入 |
| T0.1.1.2 | 创建 ingress 目录 | `mozi/ingress/__init__.py` | 包可导入 |
| T0.1.1.3 | 创建 session 目录 | `mozi/session/__init__.py` | 包可导入 |
| T0.1.1.4 | 创建 orchestrator 目录 | `mozi/orchestrator/__init__.py` | 包可导入 |
| T0.1.1.5 | 创建 orchestrator/core 目录 | `mozi/orchestrator/core/__init__.py` | 包可导入 |
| T0.1.1.6 | 创建 orchestrator/workers 目录 | `mozi/orchestrator/workers/__init__.py` | 包可导入 |
| T0.1.1.7 | 创建 core 目录 | `mozi/core/__init__.py` | 包可导入 |
| T0.1.1.8 | 创建 core/model 目录 | `mozi/core/model/__init__.py` | 包可导入 |
| T0.1.1.9 | 创建 core/tools 目录 | `mozi/core/tools/__init__.py` | 包可导入 |
| T0.1.1.10 | 创建 core/tools/builtin 目录 | `mozi/core/tools/builtin/__init__.py` | 包可导入 |
| T0.1.1.11 | 创建 core/tools/analysis 目录 | `mozi/core/tools/analysis/__init__.py` | 包可导入 |
| T0.1.1.12 | 创建 core/tools/external 目录 | `mozi/core/tools/external/__init__.py` | 包可导入 |
| T0.1.1.13 | 创建 core/mcp 目录 | `mozi/core/mcp/__init__.py` | 包可导入 |
| T0.1.1.14 | 创建 core/skills 目录 | `mozi/core/skills/__init__.py` | 包可导入 |
| T0.1.1.15 | 创建 context 目录 | `mozi/context/__init__.py` | 包可导入 |
| T0.1.1.16 | 创建 memory 目录 | `mozi/memory/__init__.py` | 包可导入 |
| T0.1.1.17 | 创建 memory/stores 目录 | `mozi/memory/stores/__init__.py` | 包可导入 |
| T0.1.1.18 | 创建 infrastructure 目录 | `mozi/infrastructure/__init__.py` | 包可导入 |
| T0.1.1.19 | 创建 tests/unit 目录 | `tests/unit/__init__.py` | 测试可运行 |
| T0.1.1.20 | 创建 tests/integration 目录 | `tests/integration/__init__.py` | 测试可运行 |
| T0.1.1.21 | 创建 tests/e2e 目录 | `tests/e2e/__init__.py` | 测试可运行 |
| T0.1.1.22 | 创建 docs 目录结构 | `docs/foundation/architecture/` 等 | 目录完整 |

#### T0.1.2: 项目配置

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T0.1.2.1 | 创建 pyproject.toml | `pyproject.toml` | 依赖版本锁定 |
| T0.1.2.2 | 创建 ruff 配置文件 | `ruff.toml` | 格式化规则生效 |
| T0.1.2.3 | 创建 mypy 配置文件 | `mypy.ini` | 类型检查生效 |
| T0.1.2.4 | 创建 pytest 配置 | `pytest.ini` | 测试框架生效 |
| T0.1.2.5 | 创建 uv.lock | `uv.lock` | 依赖版本锁定 |
| T0.1.2.6 | 创建 .gitignore | `.gitignore` | 临时文件忽略 |
| T0.1.2.7 | 创建 mozi 版本文件 | `mozi/__version__.py` | 版本可获取 |

#### T0.1.3: 规则文件配置

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T0.1.3.1 | 代码风格规则 | `.claude/rules/coding-style.md` | 已创建 |
| T0.1.3.2 | CI/CD 规则 | `.claude/rules/ci-cd.md` | 已创建 |
| T0.1.3.3 | 测试规则 | `.claude/rules/testing.md` | 已创建 |
| T0.1.3.4 | Git 工作流规则 | `.claude/rules/workflow.md` | 已创建 |
| T0.1.3.5 | 安全规范 | `.claude/rules/security.md` | 已创建 |
| T0.1.3.6 | 文档规范 | `.claude/rules/documentation.md` | 已创建 |

#### T0.1.4: Git Hooks 配置

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T0.1.4.1 | pre-commit 配置 | `.pre-commit-config.yaml` | Hook 生效 |
| T0.1.4.2 | 安装 pre-commit hooks | - | Hook 可触发 |

#### T0.1.5: 基础异常类创建

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T0.1.5.1 | 创建 MoziError 基类 | `mozi/exceptions.py` | 所有模块可导入 |
| T0.1.5.2 | 创建通用异常类 | `mozi/exceptions.py` | 异常可抛出 |

---

### M0.2: CI/CD 流水线完成（第 2 周）

#### T0.2.1: GitHub Actions 配置

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T0.2.1.1 | 创建 CI workflow | `.github/workflows/ci.yml` | PR 触发 CI |
| T0.2.1.2 | 创建代码检查 job | `.github/workflows/ci.yml` | Ruff/mypy/lint 检查 |
| T0.2.1.3 | 创建安全扫描 job | `.github/workflows/ci.yml` | bandit/pip-audit |
| T0.2.1.4 | 创建测试 job | `.github/workflows/ci.yml` | pytest + coverage |
| T0.2.1.5 | 创建构建 job | `.github/workflows/ci.yml` | 构建成功 |

#### T0.2.2: CI 质量门禁验证

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T0.2.2.1 | Ruff 格式化检查 | 无格式错误 |
| T0.2.2.2 | mypy 严格类型检查 | 无类型错误 |
| T0.2.2.3 | pytest 单元测试 | 测试通过 |
| T0.2.2.4 | 覆盖率检查 | ≥ 80% |

#### T0.2.3: 安全扫描配置

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T0.2.3.1 | bandit 配置 | `bandit.toml` | 安全扫描生效 |
| T0.2.3.2 | truffleHog 配置 | `.github/workflows/security.yml` | 密钥扫描生效 |
| T0.2.3.3 | pip-audit 配置 | `.github/workflows/security.yml` | 依赖扫描生效 |
| T0.2.3.4 | npm audit 配置 | `.github/workflows/security.yml` | 前端依赖扫描 |

---

## Phase 1: 核心模块实现（第 3-6 周）

### M1.1: Storage 模块完成（第 3 周）

#### T1.1.1: 基础设施层 - database.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.1.1.1 | 创建 SQLiteSessionStorage 类 | `infrastructure/database.py` | WAL 模式支持 |
| T1.1.1.2 | 实现 init_db 方法 | `infrastructure/database.py` | 表创建成功 |
| T1.1.1.3 | 实现 save_session 方法 | `infrastructure/database.py` | 会话保存成功 |
| T1.1.1.4 | 实现 load_session 方法 | `infrastructure/database.py` | 会话加载成功 |
| T1.1.1.5 | 实现 delete_session 方法 | `infrastructure/database.py` | 会话删除成功 |
| T1.1.1.6 | 实现 list_sessions 方法 | `infrastructure/database.py` | 会话列表成功 |
| T1.1.1.7 | 实现 save_message 方法 | `infrastructure/database.py` | 消息保存成功 |
| T1.1.1.8 | 实现 load_messages 方法 | `infrastructure/database.py` | 消息加载成功 |
| T1.1.1.9 | 实现大结果文件存储 | `infrastructure/database.py` | >4KB 存文件 |
| T1.1.1.10 | 编写 database 单元测试 | `tests/unit/infrastructure/test_database.py` | 覆盖率 ≥ 80% |

#### T1.1.2: 基础设施层 - vector_db.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.1.2.1 | 创建 VectorStore 抽象基类 | `infrastructure/vector_db.py` | 接口定义完整 |
| T1.1.2.2 | 创建 MilvusVectorStore | `infrastructure/vector_db.py` | Milvus 连接成功 |
| T1.1.2.3 | 创建 PGVectorStore | `infrastructure/vector_db.py` | PGVector 连接成功 |
| T1.1.2.4 | 实现 upsert 方法 | `infrastructure/vector_db.py` | 向量插入成功 |
| T1.1.2.5 | 实现 search 方法 | `infrastructure/vector_db.py` | 向量检索成功 |
| T1.1.2.6 | 实现 delete 方法 | `infrastructure/vector_db.py` | 向量删除成功 |
| T1.1.2.7 | 实现 hybrid_search 方法 | `infrastructure/vector_db.py` | 混合检索成功 |
| T1.1.2.8 | 编写 vector_db 单元测试 | `tests/unit/infrastructure/test_vector_db.py` | 覆盖率 ≥ 80% |

#### T1.1.3: 基础设施层 - event_bus.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.1.3.1 | 创建 EventBus 类 | `infrastructure/event_bus.py` | 事件发布订阅 |
| T1.1.3.2 | 实现 publish 方法（同步） | `infrastructure/event_bus.py` | 同步发布成功 |
| T1.1.3.3 | 实现 publish 方法（异步） | `infrastructure/event_bus.py` | 异步发布成功 |
| T1.1.3.4 | 实现 subscribe 方法 | `infrastructure/event_bus.py` | 订阅成功 |
| T1.1.3.5 | 实现 unsubscribe 方法 | `infrastructure/event_bus.py` | 取消订阅成功 |
| T1.1.3.6 | 实现事件过滤 | `infrastructure/event_bus.py` | 过滤生效 |
| T1.1.3.7 | 编写 event_bus 单元测试 | `tests/unit/infrastructure/test_event_bus.py` | 覆盖率 ≥ 80% |

---

### M1.2: Session 模块完成（第 4 周）

#### T1.2.1: session/models.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.2.1.1 | 创建 MessageRole 枚举 | `session/models.py` | 枚举值正确 |
| T1.2.1.2 | 创建 SessionStatus 枚举 | `session/models.py` | 枚举值正确 |
| T1.2.1.3 | 创建 Message 数据类 | `session/models.py` | Pydantic 模型正确 |
| T1.2.1.4 | 创建 Session 数据类 | `session/models.py` | Pydantic 模型正确 |
| T1.2.1.5 | 添加类型注解 | `session/models.py` | mypy 检查通过 |
| T1.2.1.6 | 编写 models 单元测试 | `tests/unit/session/test_models.py` | 覆盖率 ≥ 80% |

#### T1.2.2: session/storage.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.2.2.1 | 创建 SessionStorage 抽象接口 | `session/storage.py` | 接口定义完整 |
| T1.2.2.2 | 定义 save_session 签名 | `session/storage.py` | 方法签名正确 |
| T1.2.2.3 | 定义 load_session 签名 | `session/storage.py` | 方法签名正确 |
| T1.2.2.4 | 定义 save_message 签名 | `session/storage.py` | 方法签名正确 |
| T1.2.2.5 | 编写 storage 接口测试 | `tests/unit/session/test_storage.py` | 接口测试通过 |

#### T1.2.3: session/database.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.2.3.1 | 创建 SQLiteSessionStorage 实现 | `session/database.py` | 继承 storage 接口 |
| T1.2.3.2 | 实现 init 方法（建表） | `session/database.py` | 表创建成功 |
| T1.2.3.3 | 实现 save_session | `session/database.py` | 会话保存成功 |
| T1.2.3.4 | 实现 load_session | `session/database.py` | 会话加载成功 |
| T1.2.3.5 | 实现 update_session | `session/database.py` | 会话更新成功 |
| T1.2.3.6 | 实现 delete_session | `session/database.py` | 会话删除成功 |
| T1.2.3.7 | 实现 list_sessions | `session/database.py` | 会话列表成功 |
| T1.2.3.8 | 实现 save_message | `session/database.py` | 消息保存成功 |
| T1.2.3.9 | 实现 load_messages | `session/database.py` | 消息加载成功 |
| T1.2.3.10 | 实现 update_message | `session/database.py` | 消息更新成功 |
| T1.2.3.11 | 实现流式输出持久化 | `session/database.py` | streaming_content 保存 |
| T1.2.3.12 | 编写 database 单元测试 | `tests/unit/session/test_database.py` | 覆盖率 ≥ 80% |

#### T1.2.4: session/manager.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.2.4.1 | 创建 BaseSessionManager 抽象基类 | `session/manager.py` | 接口定义完整 |
| T1.2.4.2 | 创建 SessionManager 实现 | `session/manager.py` | CRUD 操作正常 |
| T1.2.4.3 | 实现 create 方法 | `session/manager.py` | 会话创建成功 |
| T1.2.4.4 | 实现 get 方法 | `session/manager.py` | 会话获取成功 |
| T1.2.4.5 | 实现 update 方法 | `session/manager.py` | 会话更新成功 |
| T1.2.4.6 | 实现 delete 方法 | `session/manager.py` | 会话删除成功 |
| T1.2.4.7 | 实现 list 方法 | `session/manager.py` | 会话列表成功 |
| T1.2.4.8 | 实现 append_message 方法 | `session/manager.py` | 消息追加成功 |
| T1.2.4.9 | 实现状态机转换逻辑 | `session/manager.py` | ACTIVE→IDLE→ARCHIVED→EXPIRED |
| T1.2.4.10 | 编写 manager 单元测试 | `tests/unit/session/test_manager.py` | 覆盖率 ≥ 80% |

#### T1.2.5: Session 模块集成

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T1.2.5.1 | resume 命令功能 | 崩溃后上下文恢复正确 |
| T1.2.5.2 | 多会话并发测试 | 数据不混淆 |
| T1.2.5.3 | 流式输出恢复测试 | streaming_content 正确恢复 |

---

### M1.3: Model 模块核心完成（第 5 周）

#### T1.3.1: core/model/adapter.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.3.1.1 | 创建 ModelProvider 枚举 | `core/model/adapter.py` | 枚举值正确 |
| T1.3.1.2 | 创建 MessageRole 枚举 | `core/model/adapter.py` | 枚举值正确 |
| T1.3.1.3 | 创建 Message 数据类 | `core/model/adapter.py` | Pydantic 模型正确 |
| T1.3.1.4 | 创建 ToolCall 数据类 | `core/model/adapter.py` | Pydantic 模型正确 |
| T1.3.1.5 | 创建 ModelRequest 数据类 | `core/model/adapter.py` | Pydantic 模型正确 |
| T1.3.1.6 | 创建 ModelResponse 数据类 | `core/model/adapter.py` | Pydantic 模型正确 |
| T1.3.1.7 | 创建 ModelUsage 数据类 | `core/model/adapter.py` | Pydantic 模型正确 |
| T1.3.1.8 | 创建 ModelInfo 数据类 | `core/model/adapter.py` | Pydantic 模型正确 |
| T1.3.1.9 | 创建 ModelAdapter 抽象基类 | `core/model/adapter.py` | 抽象方法定义完整 |
| T1.3.1.10 | 定义 invoke 抽象方法 | `core/model/adapter.py` | 方法签名正确 |
| T1.3.1.11 | 定义 invoke_stream 抽象方法 | `core/model/adapter.py` | 方法签名正确 |
| T1.3.1.12 | 编写 adapter 单元测试 | `tests/unit/core/model/test_adapter.py` | 覆盖率 ≥ 80% |

#### T1.3.2: core/model/anthropic.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.3.2.1 | 创建 AnthropicAdapter 类 | `core/model/anthropic.py` | 继承 ModelAdapter |
| T1.3.2.2 | 实现 provider 属性 | `core/model/anthropic.py` | 返回 ANTHROPIC |
| T1.3.2.3 | 实现 supported_models 属性 | `core/model/anthropic.py` | 返回支持模型列表 |
| T1.3.2.4 | 实现 validate_request 方法 | `core/model/anthropic.py` | 参数验证通过 |
| T1.3.2.5 | 实现 parse_response 方法 | `core/model/anthropic.py` | 响应解析正确 |
| T1.3.2.6 | 实现 invoke 方法 | `core/model/anthropic.py` | Claude 调用成功 |
| T1.3.2.7 | 实现 invoke_stream 方法 | `core/model/anthropic.py` | 流式调用成功 |
| T1.3.2.8 | 编写 anthropic 单元测试 | `tests/unit/core/model/test_anthropic.py` | 覆盖率 ≥ 80% |

#### T1.3.3: core/model/openai.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.3.3.1 | 创建 OpenAIAdapter 类 | `core/model/openai.py` | 继承 ModelAdapter |
| T1.3.3.2 | 实现 provider 属性 | `core/model/openai.py` | 返回 OPENAI |
| T1.3.3.3 | 实现 supported_models 属性 | `core/model/openai.py` | 返回支持模型列表 |
| T1.3.3.4 | 实现 validate_request 方法 | `core/model/openai.py` | 参数验证通过 |
| T1.3.3.5 | 实现 parse_response 方法 | `core/model/openai.py` | 响应解析正确 |
| T1.3.3.6 | 实现 invoke 方法 | `core/model/openai.py` | GPT 调用成功 |
| T1.3.3.7 | 实现 invoke_stream 方法 | `core/model/openai.py` | 流式调用成功 |
| T1.3.3.8 | 编写 openai 单元测试 | `tests/unit/core/model/test_openai.py` | 覆盖率 ≥ 80% |

#### T1.3.4: core/model/registry.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.3.4.1 | 创建 ModelRegistry 类 | `core/model/registry.py` | 单例模式 |
| T1.3.4.2 | 实现 register_adapter 方法 | `core/model/registry.py` | 适配器注册成功 |
| T1.3.4.3 | 实现 get_adapter 方法 | `core/model/registry.py` | 获取适配器成功 |
| T1.3.4.4 | 实现 get_adapter_by_model 方法 | `core/model/registry.py` | 根据模型名获取成功 |
| T1.3.4.5 | 编写 registry 单元测试 | `tests/unit/core/model/test_registry.py` | 覆盖率 ≥ 80% |

#### T1.3.5: core/model/template.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.3.5.1 | 创建 PromptTemplateManager 类 | `core/model/template.py` | 模板管理正常 |
| T1.3.5.2 | 实现 load_template 方法 | `core/model/template.py` | 模板加载成功 |
| T1.3.5.3 | 实现 render 方法 | `core/model/template.py` | 变量替换正确 |
| T1.3.5.4 | 实现 validate_template 方法 | `core/model/template.py` | 模板验证通过 |
| T1.3.5.5 | 预定义模板创建 | `core/model/templates/` | 模板文件存在 |
| T1.3.5.6 | 编写 template 单元测试 | `tests/unit/core/model/test_template.py` | 覆盖率 ≥ 80% |

#### T1.3.6: core/model/errors.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.3.6.1 | 创建 ModelInvocationError | `core/model/errors.py` | 异常类定义正确 |
| T1.3.6.2 | 创建 ModelNotFoundError | `core/model/errors.py` | 异常类定义正确 |
| T1.3.6.3 | 创建 InvalidRequestError | `core/model/errors.py` | 异常类定义正确 |
| T1.3.6.4 | 创建 ResponseParseError | `core/model/errors.py` | 异常类定义正确 |
| T1.3.6.5 | 创建 RateLimitError | `core/model/errors.py` | 异常类定义正确 |
| T1.3.6.6 | 创建 AuthenticationError | `core/model/errors.py` | 异常类定义正确 |
| T1.3.6.7 | 创建 CircuitBreakerOpenError | `core/model/errors.py` | 异常类定义正确 |

#### T1.3.7: core/model/retry.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.3.7.1 | 创建 RetryStrategy 类 | `core/model/retry.py` | 重试策略正确 |
| T1.3.7.2 | 实现 should_retry 方法 | `core/model/retry.py` | 判断逻辑正确 |
| T1.3.7.3 | 实现 calculate_delay 方法 | `core/model/retry.py` | 指数退避正确 |
| T1.3.7.4 | 实现 execute_with_retry 方法 | `core/model/retry.py` | 重试执行正常 |
| T1.3.7.5 | 编写 retry 单元测试 | `tests/unit/core/model/test_retry.py` | 覆盖率 ≥ 80% |

#### T1.3.8: core/model/circuit_breaker.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.3.8.1 | 创建 CircuitState 枚举 | `core/model/circuit_breaker.py` | 枚举值正确 |
| T1.3.8.2 | 创建 CircuitBreaker 类 | `core/model/circuit_breaker.py` | 熔断逻辑正确 |
| T1.3.8.3 | 实现 call 方法 | `core/model/circuit_breaker.py` | 带熔断调用 |
| T1.3.8.4 | 实现 _should_attempt_reset 方法 | `core/model/circuit_breaker.py` | 恢复判断正确 |
| T1.3.8.5 | 实现 _on_success 方法 | `core/model/circuit_breaker.py` | 成功处理正确 |
| T1.3.8.6 | 实现 _on_failure 方法 | `core/model/circuit_breaker.py` | 失败处理正确 |
| T1.3.8.7 | 编写 circuit_breaker 单元测试 | `tests/unit/core/model/test_circuit_breaker.py` | 覆盖率 ≥ 80% |

---

### M1.4: Model 模块集成（第 6 周）

#### T1.4.1: Model 配置管理

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T1.4.1.1 | 创建 config/model.json | `config/model.json` | 配置文件存在 |
| T1.4.1.2 | 实现 ConfigLoader | `infrastructure/config.py` | 配置加载成功 |
| T1.4.1.3 | 实现环境变量覆盖 | `infrastructure/config.py` | 环境变量生效 |
| T1.4.1.4 | 实现密钥安全读取 | `infrastructure/config.py` | API 密钥不泄露 |
| T1.4.1.5 | 编写 config 单元测试 | `tests/unit/infrastructure/test_config.py` | 覆盖率 ≥ 80% |

#### T1.4.2: Model 与 EventBus 集成

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T1.4.2.1 | model_invoked 事件发布 | 事件正确发布 |
| T1.4.2.2 | model_error 事件发布 | 事件正确发布 |
| T1.4.2.3 | 事件 payload 正确 | 包含 model/tokens/latency |

#### T1.4.3: Model 与 Session 集成

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T1.4.3.1 | 模型响应追加到会话 | 消息历史包含模型响应 |
| T1.4.3.2 | 工具调用结果追加到会话 | 消息历史包含工具结果 |
| T1.4.3.3 | 集成测试通过 | 端到端调用正常 |

---

## Phase 2: 编排层实现（第 7-10 周）

### M2.1: Memory 模块完成（第 7 周）

#### T2.1.1: memory/short_term.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.1.1.1 | 创建 ShortTermMemory 类 | `memory/short_term.py` | 滑动窗口实现 |
| T2.1.1.2 | 实现 add 方法 | `memory/short_term.py` | 添加记忆成功 |
| T2.1.1.3 | 实现 get_recent 方法 | `memory/short_term.py` | 获取最近 N 条 |
| T2.1.1.4 | 实现 trim 方法 | `memory/short_term.py` | 窗口裁剪正确 |
| T2.1.1.5 | 编写 short_term 单元测试 | `tests/unit/memory/test_short_term.py` | 覆盖率 ≥ 80% |

#### T2.1.2: memory/long_term.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.1.2.1 | 创建 MemoryType 枚举 | `memory/long_term.py` | 枚举值正确 |
| T2.1.2.2 | 创建 MemoryBlock 数据类 | `memory/long_term.py` | Pydantic 模型正确 |
| T2.1.2.3 | 创建 LongTermMemory 类 | `memory/long_term.py` | 向量存储实现 |
| T2.1.2.4 | 实现 add 方法 | `memory/long_term.py` | 添加记忆成功 |
| T2.1.2.5 | 实现 search 方法 | `memory/long_term.py` | 向量检索成功 |
| T2.1.2.6 | 实现 delete 方法 | `memory/long_term.py` | 删除记忆成功 |
| T2.1.2.7 | 实现 update_importance 方法 | `memory/long_term.py` | 重要性更新 |
| T2.1.2.8 | 编写 long_term 单元测试 | `tests/unit/memory/test_long_term.py` | 覆盖率 ≥ 80% |

#### T2.1.3: memory/retriever.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.1.3.1 | 创建 MemoryRetriever 类 | `memory/retriever.py` | 检索逻辑正确 |
| T2.1.3.2 | 实现 recall 方法 | `memory/retriever.py` | 记忆召回成功 |
| T2.1.3.3 | 实现 hybrid_search 方法 | `memory/retriever.py` | 混合检索成功 |
| T2.1.3.4 | 实现 rerank 方法 | `memory/retriever.py` | 重排序正确 |
| T2.1.3.5 | 编写 retriever 单元测试 | `tests/unit/memory/test_retriever.py` | 覆盖率 ≥ 80% |

#### T2.1.4: memory/stores/

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.1.4.1 | 创建 MilvusVectorStore | `memory/stores/milvus.py` | Milvus 连接成功 |
| T2.1.4.2 | 创建 PGVectorStore | `memory/stores/pgvector.py` | PGVector 连接成功 |
| T2.1.4.3 | 实现 upsert/search/delete | `memory/stores/milvus.py` | CRUD 操作正常 |
| T2.1.4.4 | 实现 upsert/search/delete | `memory/stores/pgvector.py` | CRUD 操作正常 |
| T2.1.4.5 | 编写 stores 单元测试 | `tests/unit/memory/test_stores.py` | 覆盖率 ≥ 80% |

---

### M2.2: Context 模块完成（第 8 周）

#### T2.2.1: context/models.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.2.1.1 | 创建 BuiltContext 数据类 | `context/models.py` | Pydantic 模型正确 |
| T2.2.1.2 | 创建 ContextConfig 数据类 | `context/models.py` | Pydantic 模型正确 |
| T2.2.1.3 | 创建 CompressionResult 数据类 | `context/models.py` | Pydantic 模型正确 |
| T2.2.1.4 | 编写 models 单元测试 | `tests/unit/context/test_models.py` | 覆盖率 ≥ 80% |

#### T2.2.2: context/builder.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.2.2.1 | 创建 ContextBuilder 类 | `context/builder.py` | 上下文构建正确 |
| T2.2.2.2 | 实现 build 方法 | `context/builder.py` | 构建成功 |
| T2.2.2.3 | 实现 _build_system_prompt 方法 | `context/builder.py` | 系统提示构建正确 |
| T2.2.2.4 | 实现 _gather_history 方法 | `context/builder.py` | 历史获取正确 |
| T2.2.2.5 | 实现 _gather_memory 方法 | `context/builder.py` | 记忆召回正确 |
| T2.2.2.6 | 编写 builder 单元测试 | `tests/unit/context/test_builder.py` | 覆盖率 ≥ 80% |

#### T2.2.3: context/window.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.2.3.1 | 创建 WindowManager 类 | `context/window.py` | 窗口管理正确 |
| T2.2.3.2 | 实现 check_threshold 方法 | `context/window.py` | 阈值检测正确 |
| T2.2.3.3 | 实现 should_compress 方法 | `context/window.py` | 压缩判断正确 |
| T2.2.3.4 | 实现 get_snapshot 方法 | `context/window.py` | 快照获取正确 |
| T2.2.3.5 | 编写 window 单元测试 | `tests/unit/context/test_window.py` | 覆盖率 ≥ 80% |

#### T2.2.4: context/compactor.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.2.4.1 | 创建 Compactor 类 | `context/compactor.py` | LLM 摘要压缩 |
| T2.2.4.2 | 实现 compress 方法 | `context/compactor.py` | 压缩成功 |
| T2.2.4.3 | 实现 create_snapshot 方法 | `context/compactor.py` | 快照创建成功 |
| T2.2.4.4 | 实现 merge_snapshots 方法 | `context/compactor.py` | 快照合并正确 |
| T2.2.4.5 | 编写 compactor 单元测试 | `tests/unit/context/test_compactor.py` | 覆盖率 ≥ 80% |

#### T2.2.5: context/offloader.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.2.5.1 | 创建 Offloader 类 | `context/offloader.py` | 大结果卸载 |
| T2.2.5.2 | 实现 should_offload 方法 | `context/offloader.py` | 卸载判断正确 |
| T2.2.5.3 | 实现 offload 方法 | `context/offloader.py` | 卸载成功 |
| T2.2.5.4 | 实现 reload 方法 | `context/offloader.py` | 重新加载成功 |
| T2.2.5.5 | 编写 offloader 单元测试 | `tests/unit/context/test_offloader.py` | 覆盖率 ≥ 80% |

#### T2.2.6: context/isolator.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.2.6.1 | 创建 Isolator 类 | `context/isolator.py` | Worker 隔离 |
| T2.2.6.2 | 实现 should_isolate 方法 | `context/isolator.py` | 隔离判断正确 |
| T2.2.6.3 | 实现 create_isolated_context 方法 | `context/isolator.py` | 隔离上下文创建 |
| T2.2.6.4 | 实现 merge_results 方法 | `context/isolator.py` | 结果合并正确 |
| T2.2.6.5 | 编写 isolator 单元测试 | `tests/unit/context/test_isolator.py` | 覆盖率 ≥ 80% |

---

### M2.3: Orchestrator 核心完成（第 9 周）

#### T2.3.1: orchestrator/category.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.3.1.1 | 创建 Category 枚举 | `orchestrator/category.py` | QUICK/DEEP/STRATEGIC |
| T2.3.1.2 | 创建 CategoryRouter 类 | `orchestrator/category.py` | 路由逻辑正确 |
| T2.3.1.3 | 实现 route 方法 | `orchestrator/category.py` | 路由正确 |
| T2.3.1.4 | 编写 category 单元测试 | `tests/unit/orchestrator/test_category.py` | 覆盖率 ≥ 80% |

#### T2.3.2: orchestrator/state.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.3.2.1 | 创建 TodoItem 数据类 | `orchestrator/state.py` | Pydantic 模型正确 |
| T2.3.2.2 | 创建 Decision 数据类 | `orchestrator/state.py` | Pydantic 模型正确 |
| T2.3.2.3 | 创建 OrchestratorState 数据类 | `orchestrator/state.py` | Pydantic 模型正确 |
| T2.3.2.4 | 创建 StateStore 类 | `orchestrator/state.py` | 状态管理正确 |
| T2.3.2.5 | 实现 save_state 方法 | `orchestrator/state.py` | 状态保存成功 |
| T2.3.2.6 | 实现 load_state 方法 | `orchestrator/state.py` | 状态加载成功 |
| T2.3.2.7 | 实现 update_todo 方法 | `orchestrator/state.py` | TODO 更新成功 |
| T2.3.2.8 | 实现 complete_todo 方法 | `orchestrator/state.py` | TODO 完成成功 |
| T2.3.2.9 | 编写 state 单元测试 | `tests/unit/orchestrator/test_state.py` | 覆盖率 ≥ 80% |

#### T2.3.3: orchestrator/workers/explorer.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.3.3.1 | 创建 ExplorerWorker 类 | `orchestrator/workers/explorer.py` | 无状态设计 |
| T2.3.3.2 | 实现 execute 方法 | `orchestrator/workers/explorer.py` | 探索执行成功 |
| T2.3.3.3 | 实现 search_codebase 方法 | `orchestrator/workers/explorer.py` | 代码库搜索正确 |
| T2.3.3.4 | 实现 get_file_info 方法 | `orchestrator/workers/explorer.py` | 文件信息获取正确 |
| T2.3.3.5 | 编写 explorer 单元测试 | `tests/unit/orchestrator/workers/test_explorer.py` | 覆盖率 ≥ 80% |

#### T2.3.4: orchestrator/workers/planner.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.3.4.1 | 创建 PlannerWorker 类 | `orchestrator/workers/planner.py` | 无状态设计 |
| T2.3.4.2 | 实现 execute 方法 | `orchestrator/workers/planner.py` | 规划执行成功 |
| T2.3.4.3 | 实现 generate_todo_list 方法 | `orchestrator/workers/planner.py` | TODO 生成正确 |
| T2.3.4.4 | 实现 decompose_task 方法 | `orchestrator/workers/planner.py` | 任务分解正确 |
| T2.3.4.5 | 编写 planner 单元测试 | `tests/unit/orchestrator/workers/test_planner.py` | 覆盖率 ≥ 80% |

#### T2.3.5: orchestrator/workers/coder.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.3.5.1 | 创建 CoderWorker 类 | `orchestrator/workers/coder.py` | 无状态设计 |
| T2.3.5.2 | 实现 execute 方法 | `orchestrator/workers/coder.py` | 编码执行成功 |
| T2.3.5.3 | 实现 apply_diff 方法 | `orchestrator/workers/coder.py` | Diff 应用正确 |
| T2.3.5.4 | 实现 validate_change 方法 | `orchestrator/workers/coder.py` | 变更验证正确 |
| T2.3.5.5 | 编写 coder 单元测试 | `tests/unit/orchestrator/workers/test_coder.py` | 覆盖率 ≥ 80% |

#### T2.3.6: orchestrator/quality.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.3.6.1 | 创建 QualityChecker 类 | `orchestrator/quality.py` | 质量门禁正确 |
| T2.3.6.2 | 实现 run_tests 方法 | `orchestrator/quality.py` | 单元测试执行 |
| T2.3.6.3 | 实现 static_analysis 方法 | `orchestrator/quality.py` | 静态检查执行 |
| T2.3.6.4 | 实现 security_scan 方法 | `orchestrator/quality.py` | 安全扫描执行 |
| T2.3.6.5 | 实现 check 方法 | `orchestrator/quality.py` | 质量检查汇总 |
| T2.3.6.6 | 编写 quality 单元测试 | `tests/unit/orchestrator/test_quality.py` | 覆盖率 ≥ 80% |

#### T2.3.7: orchestrator/reviewer.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.3.7.1 | 创建 Reviewer 类 | `orchestrator/reviewer.py` | 语义验收正确 |
| T2.3.7.2 | 实现 review 方法 | `orchestrator/reviewer.py` | 审查执行正确 |
| T2.3.7.3 | 实现 verify_alignment 方法 | `orchestrator/reviewer.py` | 需求对齐验证 |
| T2.3.7.4 | 编写 reviewer 单元测试 | `tests/unit/orchestrator/test_reviewer.py` | 覆盖率 ≥ 80% |

#### T2.3.8: orchestrator/orchestrator.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T2.3.8.1 | 创建 Orchestrator 主类 | `orchestrator/orchestrator.py` | ReAct 循环正确 |
| T2.3.8.2 | 实现 run 方法 | `orchestrator/orchestrator.py` | 主编排执行 |
| T2.3.8.3 | 实现 _thought 方法 | `orchestrator/orchestrator.py` | 思考阶段正确 |
| T2.3.8.4 | 实现 _decide 方法 | `orchestrator/orchestrator.py` | 决策阶段正确 |
| T2.3.8.5 | 实现 _delegate 方法 | `orchestrator/orchestrator.py` | 委托阶段正确 |
| T2.3.8.6 | 实现 _review 方法 | `orchestrator/orchestrator.py` | 审查阶段正确 |
| T2.3.8.7 | 实现 _update 方法 | `orchestrator/orchestrator.py` | 更新阶段正确 |
| T2.3.8.8 | 实现 _should_continue 方法 | `orchestrator/orchestrator.py` | 循环判断正确 |
| T2.3.8.9 | 编写 orchestrator 单元测试 | `tests/unit/orchestrator/test_orchestrator.py` | 覆盖率 ≥ 80% |

---

### M2.4: Orchestrator 集成（第 10 周）

#### T2.4.1: Orchestrator 与 Session 集成

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T2.4.1.1 | 会话上下文传递 | 消息历史正确传递 |
| T2.4.1.2 | 状态持久化到 Session | 崩溃后可恢复 |
| T2.4.1.3 | 集成测试通过 | Session+Orchestrator |

#### T2.4.2: Orchestrator 与 Context 集成

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T2.4.2.1 | 上下文分配给 Worker | 按需分配正确 |
| T2.4.2.2 | Worker 结果摘要归档 | StateStore 正确更新 |
| T2.4.2.3 | 集成测试通过 | Context+Orchestrator |

#### T2.4.3: Orchestrator 与 Memory 集成

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T2.4.3.1 | 记忆召回触发 | 相关记忆正确召回 |
| T2.4.3.2 | 新记忆存储 | 交互记忆正确保存 |
| T2.4.3.3 | 集成测试通过 | Memory+Orchestrator |

#### T2.4.4: Orchestrator 与 Model 集成

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T2.4.4.1 | LLM 调用正常 | 模型调用成功 |
| T2.4.4.2 | 工具调用结果处理 | ToolResult 正确处理 |
| T2.4.4.3 | 集成测试通过 | Model+Orchestrator |

#### T2.4.5: Orchestrator 与 EventBus 集成

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T2.4.5.1 | 状态变更事件发布 | 事件正确发布 |
| T2.4.5.2 | Worker 执行事件发布 | 事件正确发布 |
| T2.4.5.3 | 集成测试通过 | EventBus+Orchestrator |

#### T2.4.6: 端到端流程测试

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T2.4.6.1 | QUICK 任务流程 | 单 Agent 执行正常 |
| T2.4.6.2 | DEEP 任务流程 | 多 Agent 协作正常 |
| T2.4.6.3 | STRATEGIC 任务流程 | 完整流水线正常 |
| T2.4.6.4 | 崩溃恢复测试 | 状态正确恢复 |

---

## Phase 3: 接入层与集成（第 11-13 周）

### M3.1: Tools 模块完成（第 11 周）

#### T3.1.1: core/tools/framework.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.1.1.1 | 创建 ToolContext 数据类 | `core/tools/framework.py` | Pydantic 模型正确 |
| T3.1.1.2 | 创建 ToolResult 数据类 | `core/tools/framework.py` | Pydantic 模型正确 |
| T3.1.1.3 | 创建 Tool 抽象基类 | `core/tools/framework.py` | 抽象方法定义完整 |
| T3.1.1.4 | 定义 execute 抽象方法 | `core/tools/framework.py` | 方法签名正确 |
| T3.1.1.5 | 编写 framework 单元测试 | `tests/unit/core/tools/test_framework.py` | 覆盖率 ≥ 80% |

#### T3.1.2: core/tools/registry.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.1.2.1 | 创建 ToolRegistry 类 | `core/tools/registry.py` | 注册管理正常 |
| T3.1.2.2 | 实现 register 方法 | `core/tools/registry.py` | 注册成功 |
| T3.1.2.3 | 实现 unregister 方法 | `core/tools/registry.py` | 注销成功 |
| T3.1.2.4 | 实现 get 方法 | `core/tools/registry.py` | 获取成功 |
| T3.1.2.5 | 实现 list_tools 方法 | `core/tools/registry.py` | 列表成功 |
| T3.1.2.6 | 实现 execute 方法 | `core/tools/registry.py` | 执行成功 |
| T3.1.2.7 | 编写 registry 单元测试 | `tests/unit/core/tools/test_registry.py` | 覆盖率 ≥ 80% |

#### T3.1.3: core/tools/security.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.1.3.1 | 创建 PermissionLevel 枚举 | `core/tools/security.py` | 枚举值正确 |
| T3.1.3.2 | 创建 ViolationSeverity 枚举 | `core/tools/security.py` | 枚举值正确 |
| T3.1.3.3 | 创建 SecurityViolation 数据类 | `core/tools/security.py` | Pydantic 模型正确 |
| T3.1.3.4 | 创建 DangerousFunctionDetector | `core/tools/security.py` | AST 检测正确 |
| T3.1.3.5 | 实现 path_whitelist_validation | `core/tools/security.py` | 白名单验证正确 |
| T3.1.3.6 | 编写 security 单元测试 | `tests/unit/core/tools/test_security.py` | 覆盖率 ≥ 80% |

#### T3.1.4: core/tools/builtin/read.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.1.4.1 | 创建 ReadFileTool 类 | `core/tools/builtin/read.py` | 继承 Tool |
| T3.1.4.2 | 实现 execute 方法 | `core/tools/builtin/read.py` | 文件读取成功 |
| T3.1.4.3 | 实现路径验证 | `core/tools/builtin/read.py` | 白名单验证 |
| T3.1.4.4 | 编写 read 单元测试 | `tests/unit/core/tools/builtin/test_read.py` | 覆盖率 ≥ 80% |

#### T3.1.5: core/tools/builtin/write.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.1.5.1 | 创建 WriteFileTool 类 | `core/tools/builtin/write.py` | 继承 Tool |
| T3.1.5.2 | 实现 execute 方法 | `core/tools/builtin/write.py` | 文件写入成功 |
| T3.1.5.3 | 实现原子写入 | `core/tools/builtin/write.py` | 原子性保证 |
| T3.1.5.4 | 编写 write 单元测试 | `tests/unit/core/tools/builtin/test_write.py` | 覆盖率 ≥ 80% |

#### T3.1.6: core/tools/builtin/edit.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.1.6.1 | 创建 EditFileTool 类 | `core/tools/builtin/edit.py` | 继承 Tool |
| T3.1.6.2 | 实现 execute 方法 | `core/tools/builtin/edit.py` | 文件编辑成功 |
| T3.1.6.3 | 实现字符串替换 | `core/tools/builtin/edit.py` | 替换逻辑正确 |
| T3.1.6.4 | 编写 edit 单元测试 | `tests/unit/core/tools/builtin/test_edit.py` | 覆盖率 ≥ 80% |

#### T3.1.7: core/tools/builtin/bash.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.1.7.1 | 创建 BashTool 类 | `core/tools/builtin/bash.py` | 继承 Tool |
| T3.1.7.2 | 实现 execute 方法 | `core/tools/builtin/bash.py` | 命令执行成功 |
| T3.1.7.3 | 实现危险命令检测 | `core/tools/builtin/bash.py` | 命令限制生效 |
| T3.1.7.4 | 实现超时控制 | `core/tools/builtin/bash.py` | 超时正确处理 |
| T3.1.7.5 | 编写 bash 单元测试 | `tests/unit/core/tools/builtin/test_bash.py` | 覆盖率 ≥ 80% |

#### T3.1.8: core/tools/builtin/grep.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.1.8.1 | 创建 GrepTool 类 | `core/tools/builtin/grep.py` | 继承 Tool |
| T3.1.8.2 | 实现 execute 方法 | `core/tools/builtin/grep.py` | 搜索成功 |
| T3.1.8.3 | 编写 grep 单元测试 | `tests/unit/core/tools/builtin/test_grep.py` | 覆盖率 ≥ 80% |

#### T3.1.9: core/tools/builtin/glob.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.1.9.1 | 创建 GlobTool 类 | `core/tools/builtin/glob.py` | 继承 Tool |
| T3.1.9.2 | 实现 execute 方法 | `core/tools/builtin/glob.py` | 匹配成功 |
| T3.1.9.3 | 编写 glob 单元测试 | `tests/unit/core/tools/builtin/test_glob.py` | 覆盖率 ≥ 80% |

#### T3.1.10: 高级工具（可选 P1/P2）

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.1.10.1 | 创建 ASTGrepTool | `core/tools/analysis/ast_grep.py` | AST 搜索正常 |
| T3.1.10.2 | 创建 LSPTool | `core/tools/analysis/lsp.py` | LSP 调用正常 |
| T3.1.10.3 | 创建 WebSearchTool | `core/tools/external/web_search.py` | Web 搜索正常 |
| T3.1.10.4 | 创建 WebFetchTool | `core/tools/external/web_fetch.py` | URL 获取正常 |
| T3.1.10.5 | 创建 TaskCreateTool | `core/tools/task/task_create.py` | 任务创建正常 |
| T3.1.10.6 | 创建 TaskGetTool | `core/tools/task/task_get.py` | 任务获取正常 |
| T3.1.10.7 | 创建 TaskUpdateTool | `core/tools/task/task_update.py` | 任务更新正常 |
| T3.1.10.8 | 创建 TaskListTool | `core/tools/task/task_list.py` | 任务列表正常 |

---

### M3.2: Ingress 模块完成（第 12 周）

#### T3.2.1: ingress/models.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.2.1.1 | 创建 CliMode 枚举 | `ingress/models.py` | REPL/COMMAND |
| T3.2.1.2 | 创建 SessionAction 枚举 | `ingress/models.py` | CREATE/LIST/CONTINUE/DELETE |
| T3.2.1.3 | 创建 UserInput 数据类 | `ingress/models.py` | Pydantic 模型正确 |
| T3.2.1.4 | 创建 CliResult 数据类 | `ingress/models.py` | Pydantic 模型正确 |
| T3.2.1.5 | 编写 models 单元测试 | `tests/unit/ingress/test_models.py` | 覆盖率 ≥ 80% |

#### T3.2.2: ingress/output.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.2.2.1 | 创建 OutputFormatter 类 | `ingress/output.py` | 格式化正确 |
| T3.2.2.2 | 实现 print 方法 | `ingress/output.py` | 输出正确 |
| T3.2.2.3 | 实现 print_error 方法 | `ingress/output.py` | 错误输出正确 |
| T3.2.2.4 | 实现 print_progress 方法 | `ingress/output.py` | 进度条正确 |
| T3.2.2.5 | 编写 output 单元测试 | `tests/unit/ingress/test_output.py` | 覆盖率 ≥ 80% |

#### T3.2.3: ingress/commands.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.2.3.1 | 创建 parse_command 函数 | `ingress/commands.py` | 解析正确 |
| T3.2.3.2 | 实现 do 命令解析 | `ingress/commands.py` | do 解析正确 |
| T3.2.3.3 | 实现 session 命令解析 | `ingress/commands.py` | session 解析正确 |
| T3.2.3.4 | 编写 commands 单元测试 | `tests/unit/ingress/test_commands.py` | 覆盖率 ≥ 80% |

#### T3.2.4: ingress/main.py

| 任务ID | 子任务 | 文件路径 | 验收标准 |
|--------|--------|----------|----------|
| T3.2.4.1 | 创建 BaseCLI 抽象基类 | `ingress/main.py` | 接口定义完整 |
| T3.2.4.2 | 创建 ReplCLI 类 | `ingress/main.py` | REPL 模式正常 |
| T3.2.4.3 | 创建 CommandCLI 类 | `ingress/main.py` | 命令模式正常 |
| T3.2.4.4 | 实现 run 方法 | `ingress/main.py` | 运行正常 |
| T3.2.4.5 | 实现参数解析 | `ingress/main.py` | 参数解析正确 |
| T3.2.4.6 | 实现命令路由 | `ingress/main.py` | 路由正确 |
| T3.2.4.7 | 编写 main 单元测试 | `tests/unit/ingress/test_main.py` | 覆盖率 ≥ 80% |

---

### M3.3: 系统集成完成（第 13 周）

#### T3.3.1: 端到端流程测试

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T3.3.1.1 | 简单任务测试 | "读取 package.json" 正确输出 |
| T3.3.1.2 | 单文件编辑测试 | "添加 import os" 正确修改 |
| T3.3.1.3 | 复杂任务测试 | "重构 auth 模块" 完整执行 |
| T3.3.1.4 | 会话恢复测试 | resume 正确恢复 |
| T3.3.1.5 | 多会话隔离测试 | 数据不混淆 |

#### T3.3.2: EventBus 集成测试

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T3.3.2.1 | user_message 事件 | 事件正确发布 |
| T3.3.2.2 | agent_response 事件 | 事件正确发布 |
| T3.3.2.3 | tool_execution 事件 | 事件正确发布 |
| T3.3.2.4 | session_created 事件 | 事件正确发布 |
| T3.3.2.5 | error 事件 | 事件正确发布 |

#### T3.3.3: 错误处理集成测试

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T3.3.3.1 | 工具不存在错误 | 正确抛出 ToolNotFoundError |
| T3.3.3.2 | 工具执行超时错误 | 正确抛出 ToolExecutionTimeoutError |
| T3.3.3.3 | 路径权限错误 | 正确抛出 PermissionError |
| T3.3.3.4 | 模型调用错误 | 正确处理并传播 |

#### T3.3.4: 配置管理集成测试

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T3.3.4.1 | 配置文件加载 | 所有模块配置加载成功 |
| T3.3.4.2 | 环境变量覆盖 | 环境变量覆盖生效 |
| T3.3.4.3 | 配置验证 | 无效配置正确报错 |

#### T3.3.5: 可观测性集成测试

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T3.3.5.1 | Tracing 集成 | Span 正确创建 |
| T3.3.5.2 | Metrics 集成 | 指标正确上报 |
| T3.3.5.3 | 日志集成 | 日志正确输出 |

---

## Phase 4: 质量与交付（第 14-15 周）

### M4.1: 质量加固完成（第 14 周）

#### T4.1.1: 单元测试补齐

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T4.1.1.1 | infrastructure 模块覆盖率 | ≥ 80% |
| T4.1.1.2 | session 模块覆盖率 | ≥ 80% |
| T4.1.1.3 | core/model 模块覆盖率 | ≥ 80% |
| T4.1.1.4 | context 模块覆盖率 | ≥ 80% |
| T4.1.1.5 | memory 模块覆盖率 | ≥ 80% |
| T4.1.1.6 | orchestrator 模块覆盖率 | ≥ 80% |
| T4.1.1.7 | core/tools 模块覆盖率 | ≥ 80% |
| T4.1.1.8 | ingress 模块覆盖率 | ≥ 80% |

#### T4.1.2: 集成测试补齐

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T4.1.2.1 | Session+Orchestrator 集成 | 核心路径覆盖 |
| T4.1.2.2 | Context+Orchestrator 集成 | 核心路径覆盖 |
| T4.1.2.3 | Memory+Orchestrator 集成 | 核心路径覆盖 |
| T4.1.2.4 | Model+Orchestrator 集成 | 核心路径覆盖 |
| T4.1.2.5 | Tools+Orchestrator 集成 | 核心路径覆盖 |
| T4.1.2.6 | 整体集成测试 | 覆盖率 ≥ 80% |

#### T4.1.3: E2E 测试

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T4.1.3.1 | CLI REPL 模式测试 | E2E 测试通过 |
| T4.1.3.2 | CLI 命令模式测试 | E2E 测试通过 |
| T4.1.3.3 | 会话管理测试 | E2E 测试通过 |
| T4.1.3.4 | 完整任务执行测试 | E2E 测试通过 |

#### T4.1.4: 安全扫描修复

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T4.1.4.1 | bandit 扫描 | 无 HIGH 风险 |
| T4.1.4.2 | pip-audit 扫描 | 无高危漏洞 |
| T4.1.4.3 | npm audit 扫描 | 无高危漏洞 |
| T4.1.4.4 | truffleHog 扫描 | 无硬编码密钥 |

#### T4.1.5: 性能测试

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T4.1.5.1 | 响应时间测试 | < 2s (简单任务) |
| T4.1.5.2 | 并发会话测试 | 10 并发无异常 |
| T4.1.5.3 | 内存使用测试 | 无内存泄漏 |

---

### M4.2: 文档与发布完成（第 15 周）

#### T4.2.1: API 文档

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T4.2.1.1 | session API 文档 | 文档完整 |
| T4.2.1.2 | model API 文档 | 文档完整 |
| T4.2.1.3 | orchestrator API 文档 | 文档完整 |
| T4.2.1.4 | context API 文档 | 文档完整 |
| T4.2.1.5 | memory API 文档 | 文档完整 |
| T4.2.1.6 | tools API 文档 | 文档完整 |
| T4.2.1.7 | ingress API 文档 | 文档完整 |

#### T4.2.2: README 和开发指南

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T4.2.2.1 | README.md | 包含安装使用说明 |
| T4.2.2.2 | CONTRIBUTING.md | 贡献指南完整 |
| T4.2.2.3 | CHANGELOG.md | 变更记录完整 |

#### T4.2.3: 版本发布

| 任务ID | 子任务 | 验收标准 |
|--------|--------|----------|
| T4.2.3.1 | 文档更新 | 所有文档与代码一致 |
| T4.2.3.2 | Git Tag v1.0.0 | Tag 已创建 |
| T4.2.3.3 | Release Notes | 发布说明完整 |
| T4.2.3.4 | 版本对齐检查 | 版本号一致 |

---

## 任务统计

### 按模块统计

| 模块 | 任务数 | 文件数 | 测试文件数 |
|------|--------|--------|-----------|
| infrastructure | 21 | 3 | 3 |
| session | 25 | 4 | 4 |
| core/model | 39 | 8 | 8 |
| memory | 15 | 4 | 4 |
| context | 21 | 6 | 6 |
| orchestrator | 28 | 8 | 8 |
| core/tools | 35+ | 9+ | 9+ |
| ingress | 14 | 4 | 4 |
| 测试和集成 | 30+ | - | - |
| 文档和发布 | 10 | - | - |
| **总计** | **238+** | **46+** | **46+** |

### 按优先级统计

| 优先级 | 任务数 | 说明 |
|--------|--------|------|
| P0 | 120+ | 核心功能，必须完成 |
| P1 | 60+ | 重要功能，应完成 |
| P2 | 40+ | 增强功能，可选 |
| P3 | 20+ | 未来功能，暂不实现 |

---

_版本: v1.0_
_更新日期: 2026-03-31_
