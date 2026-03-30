# {Module} 模块设计文档

> **模板版本**: 2.0
> **创建日期**: {date}
> **最后更新**: {date}

---

## 1. 概述

### 1.1 模块名称

{ModuleName}

### 1.2 职责

> 简洁描述模块的核心职责（3-5 条 bullet points）
>
> **注意**：如果模块与其他模块有边界交互，在此说明

### 1.3 核心能力

| 能力 | 说明 |
| ---- | ---- |
| {能力1} | {说明} |
| {能力2} | {说明} |

---

## 2. 核心问题与解决方案

### 2.1 {问题标题}

**问题描述**：{准确描述要解决的核心问题}

**挑战**：{解决过程中遇到的主要技术挑战或复杂性}

**解决方案**：{详细描述如何解决这个问题，包括设计思路、关键决策、权衡取舍}

### 2.2 {问题标题}

**问题描述**：

**挑战**：

**解决方案**：

---

## 3. 数据模型

### 3.1 核心类型定义

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class {Entity}Type(Enum):
    """实体类型枚举"""
    TYPE_A = "type_a"
    TYPE_B = "type_b"


@dataclass
class {Entity}:
    """实体结构"""
    id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
```

### 3.2 状态机（可选）

> 如模块有状态流转，描述状态机

```
┌─────────┐     event1      ┌─────────┐
│  StateA │ ──────────────► │ StateB  │
└─────────┘                 └─────────┘
```

---

## 4. 模块结构

### 4.1 目录结构

```
{module_path}/
    __init__.py              # 模块导出
    {file1}.py               # {职责}
    {file2}.py               # {职责}
```

### 4.2 关键文件

| 文件 | 职责 |
| ---- | ---- |
| `{file1}.py` | {职责描述} |
| `{file2}.py` | {职责描述} |

### 4.3 依赖项

| 依赖 | 版本 | 用途 |
| ---- | ---- | ---- |
| `{package}` | {version} | {purpose} |

---

## 5. 接口与交互

### 5.1 核心接口定义

```python
from abc import ABC, abstractmethod


class {Module}Interface(ABC):
    """模块抽象接口"""

    @abstractmethod
    async def operation(self, param: str) -> None:
        """操作描述"""
        raise NotImplementedError
```

### 5.2 模块交互图

```
{ExternalModule1}        {Module}              {ExternalModule2}
      │                     │                       │
      │                     │                       │
      │<────────────────────>│                       │
      │                     │                       │
      │                     │<──────────────────────>│
```

### 5.3 模块上下文交互

| 层级 | 与 {Module} 的交互 |
| ---- | ----------------- |
| {ModuleA} | {交互描述} |
| {ModuleB} | {交互描述} |

### 5.4 EventBus 事件

| 事件 | 方向 | Payload | 说明 |
| ---- | ---- | ------- | ---- |
| `{event_name}` | → EventBus | `{payload}` | {说明} |

---

## 6. 核心业务流程

### 6.1 主要流程

```
{actor}              {module}              {dependency}
   │                    │                      │
   │──► {action_1} ────►│                      │
   │                    │──► {call_dep} ──────►│
   │                    │◄── {response} ◄─────│
   │◄── {result} ◄──────│                      │
   │                    │                      │
```

**步骤说明**：

| 步骤 | 操作 | 说明 |
| ---- | ---- | ---- |
| 1 | {action_1} | {描述} |
| 2 | {call_dep} | {描述} |
| 3 | {response} | {描述} |
| 4 | {result} | {描述} |

### 6.2 异常流程

| 异常场景 | 处理方式 |
| -------- | -------- |
| {scenario_1} | {handling} |
| {scenario_2} | {handling} |

### 6.3 关键决策点

> 解释重要的设计决策或分支选择

---

## 7. 实现细节（可选）

### 7.1 {子模块A}设计

> 如模块有多个子组件/子模块，在此描述

### 7.2 持久化方案（可选）

> 如涉及存储，在此描述

### 7.3 特殊机制（可选）

> 如有队列、缓存、批量处理等特殊机制，在此描述

---

## 8. 配置

> 如模块有独立配置项（非全局配置），在此描述；否则引用 Config 模块

| 配置项 | 类型 | 默认值 | 说明 |
| ------ | ---- | ------ | ---- |
| `{config_key}` | {type} | {default} | {description} |

---

## 9. 参考

- **错误处理**：遵循统一异常体系，见 [error_handling.md](./2026-03-29_error_handling.md)
- **测试策略**：见 [testing.md](./2026-03-29_testing.md)
- **相关模块**：{模块名}、[链接]()

---

## 变更记录

| 版本 | 日期 | 变更内容 |
| ---- | ---- | -------- |
| 2.1 | {date} | 新增核心业务流程章节 |
| 2.0 | {date} | 优化章节结构，核心问题改为段落描述，移除适配器模式假设 |
| 1.0 | {date} | 初始版本 |

_版本: 2.1_
_更新日期: {date}_
