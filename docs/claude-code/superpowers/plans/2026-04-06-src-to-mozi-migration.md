# TypeScript to Python Migration Plan (src/ → src_py/)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate TypeScript implementation from `src/` to Python implementation in `src_py/`, with functional equivalence verification.

**Architecture:** Modular migration with per-module mapping between TypeScript source and Python destination. Each batch file maps to specific TypeScript source files and Python destination modules.

**Tech Stack:** Python 3.11+, TypeScript, pytest, ruff, mypy

---

## Migration Mapping Reference

### TypeScript 源文件 (src/)

| 文件 | 说明 |
|------|------|
| `src/QueryEngine.ts` | QueryEngine 主入口，submit_message 方法 |
| `src/query.ts` | 查询循环、上下文管理、工具编排（1800+ 行） |
| `src/context.ts` | 系统/用户上下文获取 |
| `src/tools.ts` | 工具定义和注册表 |
| `src/Task.ts` | Task 模型、TaskStatus、TaskType |
| `src/Tool.ts` | Tool 接口、buildTool 工厂函数 |
| `src/commands.ts` | 命令系统 |
| `src/state/AppStateStore.ts` | 状态存储 |
| `src/types/message.ts` | 消息类型 |
| `src/services/api/claude.ts` | Claude API 客户端 |

---

## 验证策略

### Cross-Language Functional Equivalence

对于每个迁移的模块，验证：

1. **接口一致性**: Python API 签名与 TypeScript 接口匹配
2. **行为一致性**: 相同输入产生相同输出
3. **类型一致性**: 数据模型序列化/反序列化一致

### 验证命令模式

```bash
# 1. Python lint + type check
ruff check src_py/src/claude_code/<module>/
mypy src_py/src/claude_code/<module>/

# 2. Python tests
pytest src_py/tests/<module> -v --tb=short

# 3. TypeScript compilation check
cd src && npx tsc --noEmit

# 4. Cross-language snapshot tests (if available)
# Compare JSON serialized outputs between TS and Python implementations
```

---

## Task Templates

### Task Template: Module Migration

```markdown
### Task {ID}: {Module Name}

**迁移自 (Migration Source):**
- TypeScript: `src/{Module}.ts`
- Python 原始: `src_py/src/claude_code/{module}/{file}.py`

**目标 (Destination):**
- Python: `src_py/src/claude_code/{module}/{file}.py`

**验证 (Verification):**
- [ ] Python: `ruff check src_py/src/claude_code/{module}/`
- [ ] Python: `mypy src_py/src/claude_code/{module}/`
- [ ] Python: `pytest src_py/tests/{module}/ -v`
- [ ] TypeScript: `cd src && npx tsc --noEmit`
- [ ] 功能一致性: 对比 TypeScript 和 Python 输出的 JSON 序列化结果

**迁移检查清单:**
- [ ] 数据模型字段映射完整
- [ ] 方法签名一致
- [ ] 错误处理行为一致
- [ ] 类型对应关系正确
```

---

## Verification Strategy

### Cross-Language Functional Equivalence

For each migrated module, verify:

1. **Interface Consistency**: Python API signatures match TypeScript interfaces
2. **Behavior Consistency**: Same inputs produce same outputs
3. **Type Consistency**: Data models serialize/deserialize identically

### Verification Commands Pattern

```bash
# 1. Python lint + type check
ruff check mozi/<module>/
mypy mozi/<module>/

# 2. Python tests
pytest mozi/tests/<module> -v --tb=short

# 3. TypeScript compilation check
cd src && npx tsc --noEmit

# 4. Cross-language snapshot tests (if available)
# Compare JSON serialized outputs between TS and Python implementations
```

---

## Task Templates

### Task Template: Module Migration

```markdown
### Task {ID}: {Module Name}

**迁移自 (Migration Source):**
- TypeScript: `src/{Module}.ts`
- Python 原始: `src_py/src/claude_code/{module}/{file}.py`

**目标 (Destination):**
- Python: `mozi/{module}/{file}.py`

**验证 (Verification):**
- [ ] Python: `ruff check mozi/{module}/`
- [ ] Python: `mypy mozi/{module}/`
- [ ] Python: `pytest mozi/tests/{module}/ -v`
- [ ] TypeScript: `cd src && npx tsc --noEmit`
- [ ] 功能一致性: 对比 TypeScript 和 Python 输出的 JSON 序列化结果

**迁移检查清单:**
- [ ] 数据模型字段映射完整
- [ ] 方法签名一致
- [ ] 错误处理行为一致
- [ ] 类型对应关系正确
```

---

## Implementation Steps

### Step 1: Update Batch Task Files

For each batch file (batch-01 through batch-12), update the structure to include:

1. **sourceFiles**: TypeScript source files from `src/`
2. **originalPythonFiles**: Original Python implementation from `src_py/` (reference)
3. **destinationFiles**: Python destination in `mozi/`
4. **verification**: Cross-language verification commands

### Step 2: Create Verification Scripts

Create shared verification utilities:

1. `verify_model_consistency.py` - Compare data model serialization
2. `verify_api_signature.py` - Check Python API matches TypeScript interface
3. `cross_language_test.py` - Run both TS and Python tests against same inputs

### Step 3: Execute Per-Batch Migration

Follow the batch order:
- Batch 01: Infrastructure (models, state, api client, security)
- Batch 02: Query Engine
- Batch 03: Tool System
- Batch 04: Command System
- Batch 05: CLI/REPL
- Batch 06: Bridge System
- Batch 07: Services Layer
- Batch 08: UI Components
- Batch 09: Hooks/State
- Batch 10: Utils Library
- Batch 11: Skills System
- Batch 12: Plugins System

---

## Sample Task: P1-1 - QueryEngine Migration

### Task P1-1: 实现 orchestrator/orchestrator.py - QueryEngine

**迁移自 (Migration Source):**
- TypeScript: `src/QueryEngine.ts`
- Python 原始: `src_py/src/claude_code/engine/engine.py`

**目标 (Destination):**
- Python: `mozi/orchestrator/orchestrator.py`

**Files:**
- Source: `src/QueryEngine.ts` (lines 1-200+)
- Original: `src_py/src/claude_code/engine/engine.py` (deleted, reference only)
- Destination: `mozi/orchestrator/orchestrator.py`

**Verification:**
- [ ] `ruff check mozi/orchestrator/`
- [ ] `mypy mozi/orchestrator/`
- [ ] `pytest mozi/tests/orchestrator/ -v --tb=short`
- [ ] TypeScript: `cd src && npx tsc --noEmit`
- [ ] 功能一致性: `python -c "from mozi.orchestrator import QueryEngine; print(QueryEngine.__doc__)"`
