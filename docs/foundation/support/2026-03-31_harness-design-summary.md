# Harness Design for Long-Running Apps — 总结

> 来源：https://www.anthropic.com/engineering/harness-design-long-running-apps
> 日期：2026-03-31

## 概述

Anthropic 关于如何构建可靠 AI Agent（尤其是长时间运行应用）的架构设计经验。核心洞察：**Generator-Evaluator 分离**是解决 self-evaluation bias 的关键。

---

## 核心架构：Generator-Evaluator

将"干活 agent"和"评判 agent"分离，避免 agent 对自己的输出过度宽容。

```
┌─────────────┐     产出      ┌─────────────┐
│  Generator  │ ────────────→│  Evaluator  │
│   (干活)     │              │   (评判)    │
└─────────────┘              └─────────────┘
     ↑                             │
     └─────────── 反馈 ────────────┘
```

---

## 三 Agent 系统

| Agent | 职责 | 特点 |
|-------|------|------|
| **Planner** | 将简单 prompt 扩展为详细 spec | 保持高层视角，不陷入细节 |
| **Generator** | 一次实现一个功能 | 小步快跑，管控 scope |
| **Evaluator** | 评分 + 提供可执行反馈 | 需要迭代调优 prompt |

---

## 关键设计模式

### 1. 任务分解
复杂任务拆成小块，一次做一件。"one-feature-at-a-time" 防止 agent 跑偏。

### 2. 结构化交接（Structured Handoffs）
- **Context Reset**：提供干净的 slate
- **Artifact**：携带状态跨 session 传递

### 3. Sprint Contracts
实现前 generator 和 evaluator 协商"完成标准"，弥合 user story 和可测试标准。

---

## 实践原则

| 原则 | 说明 |
|------|------|
| **主观质量可评分** | 问"是否符合设计原则"比问"这好吗"更可操作 |
| **Evaluator 需调优** | prompt 需要迭代优化才能可靠catch问题 |
| **复杂度匹配能力** | 每个 component 都假设了模型能力，需压力测试 |
| **成本-质量权衡** | 完整 harness 比 solo 贵 20x，复杂任务质量提升显著 |

---

## 对 Mozi 的启示

- **Evaluator 设计**：可考虑为 Orchestrator 层引入独立的 evaluator agent 进行结果校验
- **任务分解**：结合 Mozi 的 complexity-based routing (SIMPLE/MEDIUM/COMPLEX)，小任务简单处理，大任务走完整 harness
- **Sprint Contract**：在 task 模块引入"完成标准"协商机制
- **Generator-Evaluator 分离**：避免 self-evaluation bias，特别在代码生成和测试场景

---

## 核心引用

> "Separating the agent doing the work from the agent judging it proves to be a strong lever."

> "Getting the evaluator to perform at this level took work."

> "Every component in a harness encodes an assumption about what the model can't do on its own—and those assumptions are worth stress testing."
