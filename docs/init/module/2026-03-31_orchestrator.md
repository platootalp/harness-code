# Orchestrator 编排层设计文档 v5.0

> **模板版本**: 3.0
> **创建日期**: 2026-03-31
> **更新日期**: 2026-04-01
> **版本**: 5.0
> **状态**: 已批准

---

## 1. 概述

### 1.1 模块名称

Orchestrator（编排器）

### 1.2 解决的问题

编排层是 Mozi AI Coding Agent 应对复杂任务处理的**核心决策中心**。它解决了以下问题：

| 问题 | 描述 | 解决方案 |
| ---- | ---- | -------- |
| **信息不完整** | 用户请求往往模糊、缺少关键信息（如目标文件、约束条件） | 澄清检查：通过 LLM 自我反思判断是否需要追问用户 |
| **复杂度差异大** | 简单读取文件与重构整个模块，执行路径应完全不同 | 复杂度评分：0-100 分量化，映射到 QUICK/DEEP/STRATEGIC |
| **资源滥用** | 用复杂推理处理简单任务浪费成本，用简单流程处理复杂任务易出错 | 路由决策：根据复杂度选择合适的执行策略和 Sub-Agent 组合 |
| **单点失控** | LLM 直接执行任务，缺乏审核和纠错机制 | 审核控制：Orchestrator 审核 Sub-Agent 结果，决定重试或继续 |
| **状态丢失** | 多轮对话中上下文丢失，执行结果无法连贯 | 状态管理：维护全局状态、TODO 列表、决策历史 |

**编排层的位置**：

```
用户输入
    │
    ▼
┌─────────────────┐
│   Ingress 层    │  ← 接收用户请求，解析原始输入
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Orchestrator   │  ← 核心决策：澄清检查 → 复杂度评分 → 路由
└────────┬────────┘
         │ 委托任务
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Planner        │     │  Coder          │     │  Explorer       │
│  (规划)         │ ←→  │  (编码)         │ ←→  │  (探索)         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  QualityChecker │  ← 质量审核
│  Reviewer      │  ← 语义验收
└─────────────────┘
         │
         ▼
   执行结果返回用户
```

### 1.3 职责

Orchestrator 是 Mozi AI Coding Agent 的核心**编排层**，作为系统的大脑负责：

| 职责 | 说明 |
|------|------|
| **澄清检查** | 判断任务是否需要用户澄清（如信息不足、歧义等） |
| **复杂度评估** | 量化任务复杂程度，输出 0-100 分数，映射到 SIMPLE/MEDIUM/COMPLEX |
| **路由决策** | 根据复杂度选择执行策略（QUICK/DEEP/STRATEGIC） |
| **Sub-Agent 调度** | 委托合适的 Sub-Agent 执行任务（Planner/Coder/Explorer/QualityChecker/Reviewer） |
| **审核控制** | 审核 Sub-Agent 返回的结果，决定是否继续或重试 |

### 1.4 核心能力

| 能力 | 说明 |
| ---- | ---- |
| 三步预处理 | 澄清检查 → 复杂度评分 → 路由 |
| 三级策略 | SIMPLE→QUICK / MEDIUM→DEEP / COMPLEX→STRATEGIC |
| Sub-Agent 调度 | Orchestrator 编排决策，Sub-Agent 无状态执行 |
| 状态管理 | 维护 TODO 列表、进度、决策历史等全局状态 |
| 生命周期控制 | 管理完整任务的生命周期 |

### 1.5 Orchestrator 架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Orchestrator 架构                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  User Input                                                              │
│      │                                                                   │
│      ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    Orchestrator (编排器)                              │  │
│  │                                                                      │  │
│  │  ┌─────────────────────────────────────────────────────────────┐   │  │
│  │  │                   两步预处理 (Pre-processing)                    │   │  │
│  │  │                                                              │   │  │
│  │  │   ┌──────────────────┐                                       │   │  │
│  │  │   │ 1. Clarification │  判断是否需要用户澄清                  │   │  │
│  │  │   │    Check        │  ──────► 需要澄清 → 暂停 → 等待输入  │   │  │
│  │  │   └────────┬─────────┘                                       │   │  │
│  │  │            │                                                 │   │  │
│  │  │            ▼                                                 │   │  │
│  │  │   ┌──────────────────┐                                       │   │  │
│  │  │   │ 2. Complexity    │  量化复杂程度 (0-100)                  │   │  │
│  │  │   │   Assessment     │  SIMPLE/MEDIUM/COMPLEX               │   │  │
│  │  │   │                  │  + 同步确定策略 QUICK/DEEP/STRATEGIC  │   │  │
│  │  │   └────────┬─────────┘                                       │   │  │
│  │  └────────────┼─────────────────────────────────────────────────┘   │  │
│  │               │                                                      │  │
│  │               ▼                                                      │  │
│  │  ┌─────────────────────────────────────────────────────────────┐   │  │
│  │  │               Sub-Agent 调度                                  │   │  │
│  │  │                                                              │   │  │
│  │  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───┐ │   │  │
│  │  │   │ Planner │  │ Coder   │  │ Explorer│  │Quality  │  │   │ │   │  │
│  │  │   │         │  │         │  │         │  │Checker  │  │ R │ │   │  │
│  │  │   │ 任务分解 │  │ 代码执行 │  │ 代码探索 │  │ 质量检查 │  │ e │ │   │  │
│  │  │   │ TODO   │  │ 文件修改 │  │ 信息检索 │  │ 测试运行 │  │ v │ │   │  │
│  │  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘  │ i │ │   │  │
│  │  │                                                    │ e │ │   │  │
│  │  │                                                    │ w │ │   │  │
│  │  │                                                    │ e │ │   │  │
│  │  │                                                    │ r │ │   │  │
│  │  │                                                    │ r │ │   │  │
│  │  │                                                    │ e │ │   │  │
│  │  │                                                    │ r │ │   │  │
│  │  │                                                    └───┘ │   │  │
│  │  └─────────────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│      │                                                                     │
│      ▼                                                                     │
│  OrchestratorResult                                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.6 Orchestrator vs Sub-Agent 职责划分

| 角色 | 定位 | 职责 |
|------|------|------|
| **Orchestrator** | 编排者（大脑） | 决策、路由、委托、审核、状态管理、生命周期控制 |
| **Planner** | 规划者 | 任务分解、TODO 生成、计划验证 |
| **Coder** | 编码者 | 代码执行、文件修改、diff 生成 |
| **Explorer** | 探索者 | 代码搜索、信息检索、路径发现 |
| **QualityChecker** | 质量检查者 | 运行时测试、静态分析、安全扫描 |
| **Reviewer** | 审查者 | 语义验收、需求对齐、交付评估 |

**设计原则**：
- Orchestrator 有状态，Sub-Agent 无状态
- Orchestrator 决定"做什么"，Sub-Agent 负责"怎么做"
- Sub-Agent 用完即焚，不保留上下文

---

## 2. 三步预处理

### 2.1 Step 1: Clarification Check（澄清检查）

#### 2.1.1 核心定位

> **"当前信息是否足以安全、正确地执行任务？"**

澄清检查的核心目的不是"确认意图标签"，而是判断**任务可执行性**。意图识别只是判断"信息是否足够"的一种手段——去掉意图识别后，澄清检查承担起"理解任务"的责任。

**三重角色**：

| 角色 | 说明 | 示例 |
| ---- | ---- | ---- |
| **安全网 (Safety Net)** | 防止"灵活"变成"乱来" | "删掉没用的代码" → 高风险，澄清范围 |
| **效率优化器 (Efficiency Optimizer)** | 用一次澄清换多次高效执行 | "修复登录报错" → 追问日志，大幅缩短排查 |
| **软意图发现 (Soft Intent Discovery)** | 澄清过程即意图收敛过程 | 用户回答澄清问题后，隐式获得任务类型/范围/目标 |

#### 2.1.2 触发条件（基于可执行性）

| 原触发条件 (基于意图) | 新触发条件 (基于可执行性) | 示例 |
| --------------------- | ------------------------- | ---- |
| 意图置信度 < 0.5 | 目标描述模糊 | "优化一下" → 优化什么？ |
| 缺少必要参数 | 关键实体缺失 | "修改那个文件" → 哪个文件？ |
| 歧义性输入 | 多解空间过大 | "清理项目" → 删缓存？删依赖？删日志？ |
| 复杂度异常 | 风险/收益比不清晰 | "改个小地方"但涉及核心模块 |

#### 2.1.3 实现方式：LLM 自我反思

不采用规则判断，而是让模型自己评估任务的可执行性。

**评估 Prompt**：

```
你是一个任务执行专家。请分析用户请求：

"{user_input}"

请回答以下问题：
1. 【目标清晰度】用户想要达成的具体结果是什么？(1-10分)
2. 【约束充分性】是否有足够的上下文/参数来执行？(1-10分)
3. 【歧义风险】是否存在多种合理的理解方式？(是/否)
4. 【风险感知】执行此任务是否有潜在破坏性？(低/中/高)

如果 1<7 或 2<7 或 3=是，请生成澄清问题。
否则，直接输出"无需澄清"。

输出格式 (JSON):
{
  "needs_clarification": true/false,
  "reason": "目标过于宽泛，未指定优化指标",
  "questions": ["您希望优化启动速度、内存占用还是代码可维护性？"],
  "suggestions": ["性能优化", "代码重构", "依赖清理"],
  "risk_level": "MEDIUM"
}
```

#### 2.1.4 输出数据结构

```python
@dataclass
class ClarificationResult:
    needs_clarification: bool           # 是否需要澄清
    reason: str | None                # 判断理由
    questions: list[str]              # 需要用户回答的问题
    suggestions: list[str]            # 可能的澄清选项（隐式意图，供 Planner 参考）
    risk_level: RiskLevel            # LOW / MEDIUM / HIGH

@dataclass
class TaskAssessment:
    """澄清检查的完整评估结果，同时服务于路由决策"""
    clarification: ClarificationResult  # 澄清结果
    complexity_score: int              # 预计算的复杂度分数（供路由用）
    suggested_actions: list[str]        # 隐式"意图"：建议的行动方向
```

#### 2.1.5 处理流程

```
┌─────────────────────────────────────────────────────────────────┐
│                  Clarification Check 流程                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  输入: user_input                                              │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ LLM 自我反思评估                                            │    │
│  │ - 目标清晰度 (1-10)                                        │    │
│  │ - 约束充分性 (1-10)                                        │    │
│  │ - 歧义风险 (是/否)                                         │    │
│  │ - 风险感知 (低/中/高)                                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 判断结果                                                    │    │
│  │                                                         │    │
│  │  needs_clarification = True:                              │    │
│  │    → 生成澄清问题列表                                      │    │
│  │    → 暂停任务，等待用户输入                                │    │
│  │    → 澄清历史进入 Session Context                         │    │
│  │                                                         │    │
│  │  needs_clarification = False:                             │    │
│  │    → suggested_actions 作为隐式意图                        │    │
│  │    → 继续下一步（复杂度评分）                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.1.6 澄清历史作为上下文

```
用户多轮对话:
1. "优化项目" → 澄清: "优化哪方面？"
2. "启动速度" → 澄清: "有性能分析数据吗？"
3. "有，CPU 占用高" → 无需澄清，执行

↓
每次澄清的问答都进入 Session Context
Planner 可以看到完整的"意图收敛轨迹"
```

---

### 2.2 Step 2: Complexity Scoring（复杂度评分）

#### 2.2.1 职责

量化任务复杂程度，输出 0-100 的分数，映射到 SIMPLE/MEDIUM/COMPLEX 等级。

#### 2.2.2 分数计算

| 因素 | 计算方式 | 分数范围 |
| ---- | -------- | -------- |
| **文件数量** | 分段阈值 | 0-40 |
| **操作类型** | 权重累加 | 0-100+ |
| **描述长度** | 阈值判断 | 0 或 10 |

##### 文件数量分数

| 文件数量 | 分数 |
| -------- | ---- |
| 1 | 0 |
| 2-5 | 5 |
| 6-10 | 10 |
| 11-25 | 20 |
| 26-50 | 30 |
| 51+ | 40 |

##### 操作类型权重

| 操作类型 | 权重分数 |
| -------- | -------- |
| read | 5 |
| glob | 5 |
| grep | 8 |
| edit | 15 |
| write | 20 |
| delete | 25 |
| create | 25 |
| bash | 30 |
| execute | 35 |

##### 总分计算

```
total_score = min(100, file_score + operation_score + description_score)
```

#### 2.2.3 复杂度等级

| 分数范围 | 等级 | 路由策略 |
| -------- | ---- | -------- |
| ≤ 40 | SIMPLE | QUICK |
| 41-70 | MEDIUM | DEEP |
| > 70 | COMPLEX | STRATEGIC |

> **说明**：复杂度等级与执行策略是同一概念，SIMPLE 即 QUICK，MEDIUM 即 DEEP，COMPLEX 即 STRATEGIC。风险等级用于在同一复杂度内调整策略细节（高风险倾向于更审慎的执行路径）。

#### 2.2.4 复杂度评估数据结构

```python
@dataclass
class TaskComplexity:
    score: int                           # 0-100
    level: ComplexityLevel               # SIMPLE / MEDIUM / COMPLEX
    factors: dict[str, int]              # 因素分解
    risk_level: RiskLevel              # LOW / MEDIUM / HIGH
    reasoning: str                       # 决策理由
    suggested_actions: list[str]        # 隐式意图，供 Planner 参考
```

**风险等级对策略的影响**：

| 复杂度 \ 风险 | LOW | MEDIUM/HIGH |
| -------------- | --- | ------------ |
| SIMPLE | QUICK | DEEP（带确认） |
| MEDIUM | DEEP | STRATEGIC（多轮确认） |
| COMPLEX | STRATEGIC | STRATEGIC + 人工确认 |

---

## 3. Sub-Agent 调度

### 3.1 Sub-Agent 概述

Sub-Agent 是由 Orchestrator 调度的无状态执行单元，负责执行特定类型的任务。

| Sub-Agent | 职责 | 输入 | 输出 |
|-----------|------|------|------|
| **Planner** | 任务分解 | 目标描述 | TODO 列表 |
| **Coder** | 代码执行 | 具体任务 | 代码变更/diff |
| **Explorer** | 代码探索 | 搜索查询 | 搜索结果 |
| **QualityChecker** | 质量检查 | 检查范围 | 质量报告 |
| **Reviewer** | 语义验收 | 交付物 | 验收结果 |

### 3.2 委托流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Sub-Agent 委托流程                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Orchestrator: "需要实现支付模块"                                 │
│       │                                                           │
│       ▼                                                           │
│  Decide: 选择 Planner Sub-Agent                                   │
│       │                                                           │
│       ▼                                                           │
│  Delegate:                                                        │
│   {                                                              │
│     "agent": "planner",                                          │
│     "task": "规划支付模块实现",                                    │
│     "context": {                                                 │
│       "goal": "实现支付功能",                                    │
│       "constraints": ["支持支付宝", "支持微信支付"]              │
│     }                                                            │
│   }                                                              │
│       │                                                           │
│       ▼                                                           │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │ Planner Sub-Agent (无状态执行)                              │   │
│  │ - 接收最小上下文                                            │   │
│  │ - 执行任务分解                                              │   │
│  │ - 返回 TODO 列表                                            │   │
│  └───────────────────────────────────────────────────────────┘   │
│       │                                                           │
│       ▼                                                           │
│  Review: "计划是否合理？"                                         │
│       │                                                           │
│       ├─ Yes: 继续下一步                                          │
│       │                                                           │
│       └─ No: 重新委托或更换 Sub-Agent                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 各策略任务处理流程

### 4.1 QUICK 任务处理流程

**典型场景**：读取单个文件、简单代码修改

```
┌─────────────────────────────────────────────────────────────────┐
│  QUICK 任务处理流程                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User: "Read the config.py file"                                │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 预处理 (三步)                                              │    │
│  │ 1. Clarification: 无需澄清                              │    │
│  │ 2. Complexity: score=5, SIMPLE → QUICK                 │    │
│  │ 3. Routing: QUICK 策略                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Sub-Agent 调度: Coder                                   │    │
│  │   Delegate: {task: "read config.py"}                   │    │
│  │   Execute: Coder (ReadFile)                           │    │
│  │   Review: 返回文件内容                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                        │
│         ▼                                                        │
│  结果: 返回文件内容给用户                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 DEEP 任务处理流程

**典型场景**：多步骤代码修改、需要规划的任务

```
┌─────────────────────────────────────────────────────────────────┐
│  DEEP 任务处理流程                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User: "Refactor UserService to use dependency injection"       │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 预处理 (三步)                                              │    │
│  │ 1. Clarification: 无需澄清                              │    │
│  │ 2. Complexity: score=45, MEDIUM → DEEP                │    │
│  │ 3. Routing: DEEP 策略                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Sub-Agent 调度                                           │    │
│  │                                                         │    │
│  │  1. Planner: 生成 TODO 列表                            │    │
│  │     Delegate: {goal: "refactor DI"}                    │    │
│  │     Review: TODO 列表 ✓                                 │    │
│  │                                                         │    │
│  │  2. Coder (每个 TODO 项):                              │    │
│  │     - Modify constructor                                │    │
│  │     - Update dependency injection                       │    │
│  │     Review: 每步 ✓                                     │    │
│  │                                                         │    │
│  │  3. QualityChecker: 运行测试                           │    │
│  │     Delegate: {task: "run tests"}                    │    │
│  │     Review: 测试通过 ✓                                │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                        │
│         ▼                                                        │
│  结果: 修改摘要 + 质量报告                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 STRATEGIC 任务处理流程

**典型场景**：完整模块重构、需要用户确认

```
┌─────────────────────────────────────────────────────────────────┐
│  STRATEGIC 任务处理流程                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User: "Implement payment system with Alipay and WeChat"       │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 预处理 (三步)                                              │    │
│  │ 1. Clarification: 无需澄清                              │    │
│  │ 2. Complexity: score=85, COMPLEX → STRATEGIC           │    │
│  │ 3. Routing: STRATEGIC 策略                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Sub-Agent 调度                                           │    │
│  │                                                         │    │
│  │  阶段 1: Planner (全局规划)                             │    │
│  │     Delegate: {task: "create payment design"}          │    │
│  │     Review: 设计文档 ✓                                 │    │
│  │                                                         │    │
│  │  [用户确认设计]                                          │    │
│  │                                                         │    │
│  │  阶段 2: Explorer (探索)                                │    │
│  │     Delegate: {task: "explore existing code"}         │    │
│  │     Review: 探索结果 ✓                                 │    │
│  │                                                         │    │
│  │  阶段 3: Planner (任务规划)                            │    │
│  │     Delegate: {context: 探索结果, goal: "implement"} │    │
│  │     Review: TODO 列表 ✓                                │    │
│  │                                                         │    │
│  │  阶段 4: Coder (每个 TODO 项)                          │    │
│  │     - Create payment base class                        │    │
│  │     - Implement Alipay adapter                         │    │
│  │     - Implement WeChat adapter                         │    │
│  │     Review: 每步 ✓                                     │    │
│  │                                                         │    │
│  │  阶段 5: QualityChecker (质量检查)                      │    │
│  │     Delegate: {task: "run tests + security scan"}     │    │
│  │     Review: 质量报告 ✓                                 │    │
│  │                                                         │    │
│  │  阶段 6: Reviewer (语义验收)                           │    │
│  │     Delegate: {task: "validate against original intent"} │
│  │     Review: 交付评估 ✓                                │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                        │
│         ▼                                                        │
│  结果: 实现摘要 + 质量报告 + 交付评估                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. 模块结构

### 5.1 目录结构

```
mozi/orchestrator/
    __init__.py                      # 模块导出
    orchestrator.py                  # Orchestrator 主类
    │
    ├── core/                        # 核心组件
    │   ├── __init__.py
    │   ├── clarification.py         # ClarificationCheck
    │   ├── complexity.py            # ComplexityScoring
    │   └── router.py                # Router
    │
    ├── agent/                       # Sub-Agent
    │   ├── __init__.py
    │   ├── base.py                   # SubAgentBase
    │   ├── planner.py               # Planner Sub-Agent
    │   ├── coder.py                 # Coder Sub-Agent
    │   ├── explorer.py              # Explorer Sub-Agent
    │   ├── quality_checker.py       # QualityChecker Sub-Agent
    │   └── reviewer.py              # Reviewer Sub-Agent
    │
    └── session/                     # 会话管理
        ├── __init__.py
        ├── context.py               # SessionContext
        └── manager.py               # SessionManager
```

### 5.2 核心类说明

| 类 | 文件 | 职责 |
|----|------|------|
| `Orchestrator` | orchestrator.py | 主编排器，执行三步预处理 + Sub-Agent 调度 |
| `OrchestratorConfig` | orchestrator.py | 编排器配置 |
| `OrchestratorResult` | orchestrator.py | 执行结果 |
| `ClarificationCheck` | clarification.py | 澄清检查 |
| `ClarificationResult` | clarification.py | 澄清检查结果 |
| `ComplexityScoring` | complexity.py | 复杂度评分 |
| `TaskComplexity` | complexity.py | 复杂度评估结果 |
| `Router` | router.py | 路由决策 |
| `RouteResult` | router.py | 路由结果 |
| `SubAgentBase` | base.py | Sub-Agent 基类 |
| `PlannerAgent` | planner.py | 规划 Sub-Agent |
| `CoderAgent` | coder.py | 编码 Sub-Agent |
| `ExplorerAgent` | explorer.py | 探索 Sub-Agent |
| `QualityCheckerAgent` | quality_checker.py | 质量检查 Sub-Agent |
| `ReviewerAgent` | reviewer.py | 审查 Sub-Agent |

---

## 6. 错误处理

### 6.1 异常体系

| 异常类 | 基类 | 说明 |
|--------|------|------|
| `OrchestratorError` | `MoziError` | 编排器内部错误 |
| `ClarificationError` | `MoziError` | 澄清检查失败 |
| `ComplexityError` | `MoziError` | 复杂度评估失败 |
| `RoutingError` | `MoziError` | 路由决策失败 |
| `SubAgentError` | `MoziError` | Sub-Agent 执行错误 |

### 6.2 错误处理策略

| 阶段 | 错误类型 | 处理策略 |
|------|----------|----------|
| Clarification Check | 无法澄清 | 暂停，请求用户介入 |
| Complexity Scoring | 负数文件数 | 抛出 ComplexityError |
| Routing | 路由失败 | 抛出 RoutingError |
| Sub-Agent Execution | 执行失败 | 记录错误，决定重试或更换 Sub-Agent |
| 任意阶段 | 异常 | 捕获并包装为 OrchestratorError |

---

## 7. 约束与限制

### 7.1 迭代控制

| 策略 | 最大迭代次数 | 说明 |
|------|-------------|------|
| QUICK | 5 | 防止简单任务无限循环 |
| DEEP | 15 | 中等任务留有足够探索空间 |
| STRATEGIC | 30 | 复杂任务允许多轮规划执行 |

### 7.2 输入限制

| 参数 | 限制 | 说明 |
|------|------|------|
| task_description | 非空字符串 | 必填 |
| intent.confidence | 0.0-1.0 | 自动截断 |
| complexity.score | 0-100 | 超出范围抛出异常 |

---

## 8. 度量指标

| 指标名称 | 类型 | 说明 |
| -------- | ---- | ---- |
| `orchestrator_run_total` | Counter | Orchestrator 运行总次数 |
| `orchestrator_run_duration_seconds` | Histogram | 运行耗时分布 |
| `subagent_execute_total` | Counter | Sub-Agent 执行总次数（按类型） |
| `subagent_execute_duration_seconds` | Histogram | Sub-Agent 执行耗时分布 |
| `complexity_score_distribution` | Histogram | 复杂度分数分布 |
| `clarification_rate` | Gauge | 需要澄清的比例 |
| `task_completion_rate` | Gauge | 任务完成率 |

---

## 9. 参考

- **架构参考**：oh-my-openagent (Sisyphus architecture)
- **错误处理**：遵循统一异常体系，见 [error_handling.md](./2026-03-29_error_handling.md)
- **测试策略**：见 [testing.md](./2026-03-29_testing.md)
- **相关模块**：[Context](./2026-03-29_context.md)、[Model](./2026-03-29_model.md)、[Task](./2026-03-29_task.md)

---

## 附录 A：类型别名速查

```python
# Complexity
ComplexityLevel = Enum("ComplexityLevel", ["SIMPLE", "MEDIUM", "COMPLEX"])

# Routing
RoutingStrategy = Enum("RoutingStrategy", ["QUICK", "DEEP", "STRATEGIC"])

# Risk Assessment
RiskLevel = Enum("RiskLevel", ["LOW", "MEDIUM", "HIGH"])

# Session
SessionState = Enum("SessionState", ["ACTIVE", "PAUSED", "COMPLETED", "ABANDONED", "ERROR"])
```

---

## 变更记录

| 版本 | 日期 | 变更内容 |
| ---- | ---- | -------- |
| 5.0 | 2026-04-01 | 全面重构：三步预处理（澄清检查→复杂度评分→路由）、澄清检查机制、Sub-Agent 调度架构；移除意图识别 |
| 4.0 | 2026-04-01 | 上一版本（Multi-Agent 架构初稿） |
| 3.0 | 2026-03-31 | 模板 v3.0 结构 |
| 4.0 | 2026-04-01 | 上一版本（Multi-Agent 架构初稿） |
| 3.0 | 2026-03-31 | 模板 v3.0 结构 |

_版本: 5.0_
_更新日期: 2026-04-01_
