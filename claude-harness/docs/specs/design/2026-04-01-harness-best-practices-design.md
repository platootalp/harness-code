# Harness 工程最佳实践设计

> **Design ID:** DESIGN-BE-001
> **Date:** 2026-04-01
> **Feature:** Claude Harness 工程最佳实践应用
> **Status:** Proposed

---

## 1. 概述

本文档应用 Anthropic 文章 [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps) 中的最佳实践，改进现有的 spec-driven 开发系统。

## 2. 核心问题分析

### 2.1 当前系统局限性

| 当前系统 | 最佳实践要求 | 差距 |
|---------|-------------|------|
| Review Agent 兼职评估 | 独立的 Evaluator Agent | 需要解耦生成与评估 |
| 顺序工作流 | Sprint Contracts | 需要在每个迭代前定义"完成标准" |
| 主观评审标准 | 具体可量化的评分标准 | 需要校准评估器 |
| 单次评审 | 迭代优化循环 | 需要多轮反馈 |
| 固定流程 | Simplify as Models Improve | 需要定期审视组件必要性 |

## 3. 最佳实践应用设计

### 3.1 多代理分离原则 (Multi-Agent Separation)

**核心洞察：** 将执行工作的代理与评判工作的代理分离，比自我评估效果更好。代理天生倾向于赞美自己的输出。

**应用设计：**

```
当前系统:
  Requirements Agent → PRD Agent → Design Agent → ... (生成者兼任评估)

改进后:
  [Generator Agents] ←→ [Evaluator Agent]
     ↓                      ↓
  执行文档生成           独立评估校准
```

**文件变更：**

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `.claude/agents/evaluator-agent.md` | 新增 | 独立的 Evaluator Agent |
| `.claude/agents/generator-agent.md` | 新增 | Generator Agent 抽象基类 |
| `.claude/rules/multi-agent-separation.md` | 新增 | 多代理分离规则 |

### 3.2 三代理系统 (Three-Agent System)

**最佳实践：**
- **Planner**: 将简单提示扩展为完整产品规格，保持高层设计而非实现细节
- **Generator**: 在 sprint 中工作，根据约定的 contract 实现功能
- **Evaluator**: 通过 Playwright MCP 等工具测试，根据具体标准评分，提供可操作的反馈

**当前系统映射：**

| 最佳实践角色 | 当前系统对应 | 改进说明 |
|------------|-------------|---------|
| Planner | Requirements Agent + PRD Agent | 合并为 Planner，统一做高层规划 |
| Generator | Design + Dev-Plan + Testing-Plan Agents | 按 sprint 工作 |
| Evaluator | Review Agent | 独立出来，专注评估校准 |

### 3.3 具体化评分标准 (Grading Criteria Must Be Concrete)

**最佳实践：** 主观质量通过具体标准变得可评分。设计工作：设计质量、原创性、工艺、功能性。权重应该偏向模型默认表现不佳的领域。

**应用设计：**

更新评审模板，增加具体评分维度：

```markdown
## 评审评分维度

| 维度 | 权重 | 评分标准 (1-5) | 默认表现 |
|------|------|---------------|----------|
| 完整性 | 25% | 所有章节填写，无遗漏 | 较好 |
| 清晰度 | 25% | 语言无歧义，可直接实现 | 较差 |
| 可行性 | 20% | 技术上可实现 | 一般 |
| 可测试性 | 15% | 可被验证 | 一般 |
| 一致性 | 15% | 与其他文档对齐 | 较好 |
```

### 3.4 基于结构化 artifacts 的通信 (Communication via Structured Artifacts)

**最佳实践：** 基于文件的交接保留状态在代理之间。一个代理写文件，另一个代理读取并响应。这保持工作忠实于规格，而不会过早指定实现。

**应用设计：**

```markdown
## 文件交接规范

### 必需包含的 Handoff Artifacts

1. **State Summary** (每个文档末尾)
   ```markdown
   ## State Summary

   - 本文档版本: {version}
   - 依赖的前置文档: {dependencies}
   - 为后续代理留下的决策: {pending_decisions}
   - 关键假设: {assumptions}
   ```

2. **Contract Block** (Generator 工作前)
   ```markdown
   ## Sprint Contract

   - **目标**: {sprint_goal}
   - **完成标准**: {done_criteria}
   - **验证方法**: {verification_methods}
   - **风险**: {risks}
   ```
```

### 3.5 Sprint Contracts

**最佳实践：** 在每个工作块之前，generator 和 evaluator 协商"完成"的样子。Generator 提出范围和验证方法；evaluator 审查以确保一致。这桥接高层规格到可测试的实现。

**应用设计：**

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `docs/specs/templates/sprint-contract.md` | 新增 | Sprint Contract 模板 |
| `.claude/agents/generator-agent.md` | 更新 | 增加 contract 协商流程 |
| `.claude/agents/evaluator-agent.md` | 新增 | Evaluator Agent 定义 |

### 3.6 Evaluator 校准 (Evaluator Calibration)

**最佳实践：**
- 使用 few-shot examples 和详细的分数分解
- 通过阅读 evaluator 日志调优，找到判断分歧，更新提示
- Evaluator 必须持怀疑态度——必须主动对抗它的宽容

**应用设计：**

```markdown
## Evaluator 校准流程

1. **Few-Shot Examples**
   - 为每个评审类型准备 3-5 个校准示例
   - 包含详细的分数分解说明

2. **校准日志**
   - 记录每次评审的判断依据
   - 追踪判断分歧案例

3. **迭代优化**
   - 每 10 次评审后分析分歧
   - 更新 Evaluator prompt
```

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `docs/review/calibration/` | 新增目录 | 校准示例存放 |
| `.claude/agents/evaluator-agent.md` | 新增 | 增加校准流程 |

### 3.7 迭代优化循环 (Iterative Refinement Loops)

**最佳实践：** 多个迭代周期，feedback 从 evaluator 流回 generator。每次评估后的战略决策：如果趋势良好则完善当前方向；如果方法不工作则完全转向。

**应用设计：**

```markdown
## 迭代流程

```
Generator → Evaluator → [决策节点]
    ↑           ↓
    └── 反馈 ←──┘

决策:
- 趋势良好 → 完善当前实现
- 方法失败 → 调整策略或放弃
```

**Review 评审决策扩展：**

| 决策 | 含义 | 下一步 |
|------|------|--------|
| Approved | 达标 | 进入下一阶段 |
| Approved with conditions | 条件通过 | 完善后重新评审 |
| Rejected | 拒绝 | 重大修改后重新评审 |
| **Needs Iteration** | 需要迭代 | 返回 Generator 重做 |
```

### 3.8 随着模型改进简化 (Simplify as Models Improve)

**最佳实践：** 每个组件都编码了关于模型不能做什么的假设。定期压力测试这些假设。当新模型到来时，移除不再承重的组件。有趣的 harness 组合空间不会缩小——会移动。

**应用设计：**

```markdown
## 简化原则

### 需要定期审视的组件

1. **Context Management**
   - 当前: 手动管理 context reset
   - 未来: Opus 4.6 可能消除 context reset 需求

2. **Review Agent**
   - 当前: 复杂的多步骤评审
   - 未来: 模型改进后可能简化为单一 prompt

3. **Sprint Contracts**
   - 当前: 详细的前置条件
   - 未来: 可能简化为高层目标
```

## 4. 系统架构改进

### 4.1 改进后的工作流

```
用户输入
    ↓
Planner Agent (扩展提示为规格)
    ↓
Sprint Contract 协商
    ↓
┌─────────────────────────────────────────┐
│           ITERATION LOOP               │
│  Generator → Evaluator → 决策节点      │
│      ↑           ↓                      │
│      └── 反馈 ←──┘                      │
└─────────────────────────────────────────┘
    ↓ (通过后)
Doc Agent (更新项目文档)
    ↓
Release
```

### 4.2 代理职责重新划分

| 代理 | 职责 | 工具 |
|------|------|------|
| Planner | 理解需求，扩展为详细规格 | Read, Glob, Write |
| Generator | 按 sprint 实现功能 | Read, Glob, Write, Bash |
| Evaluator | 测试和评估，提供可操作反馈 | Read, Glob, Bash, Edit |
| Doc Agent | 维护项目文档 | Read, Glob, Bash, Edit |

### 4.3 新增文件清单

| 文件路径 | 类型 | 说明 |
|---------|------|------|
| `.claude/agents/evaluator-agent.md` | 新增 | Evaluator Agent |
| `.claude/agents/planner-agent.md` | 新增 | Planner Agent (合并 Requirements + PRD) |
| `.claude/rules/multi-agent-separation.md` | 新增 | 多代理分离规则 |
| `.claude/rules/evaluator-calibration.md` | 新增 | Evaluator 校准规则 |
| `.claude/rules/sprint-contract.md` | 新增 | Sprint Contract 规则 |
| `.claude/rules/iterative-refinement.md` | 新增 | 迭代优化规则 |
| `docs/specs/templates/sprint-contract.md` | 新增 | Sprint Contract 模板 |
| `docs/review/calibration/*.md` | 新增 | 校准示例 |

## 5. 实施计划

### Phase 1: 核心改进 (第 1 阶段)

1. 创建 `evaluator-agent.md`
2. 创建 `planner-agent.md` (合并 requirements + prd)
3. 更新 `sprint-contract.md` 模板

### Phase 2: 规则增强 (第 2 阶段)

1. 创建 `multi-agent-separation.md`
2. 创建 `evaluator-calibration.md`
3. 创建 `sprint-contract.md` 规则

### Phase 3: 迭代支持 (第 3 阶段)

1. 更新评审模板增加评分维度
2. 创建校准示例
3. 更新 generator agent 增加迭代支持

### Phase 4: 简化审视 (第 4 阶段)

1. 审视当前组件的必要性
2. 更新文档架构
3. 清理冗余规则

## 6. 成本效益分析

**Evaluator 的价值：** 只有当任务超出当前模型可靠独立完成的范围时，Evaluator 才是值得的。对于简单任务，overhead 可能超过收益。

**决策矩阵：**

| 任务类型 | 建议工作流 |
|---------|-----------|
| 简单文档生成 | Generator alone |
| 标准 PRD/Design | Generator + Light Review |
| 复杂架构设计 | Generator + Calibrated Evaluator |
| 高风险决策 | Full Three-Agent + Iteration |

---

## 7. 参考

- [Harness Design for Long-Running Apps - Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps)
- [Spec-Driven Workflow](./workflows.md)
- [Review Process](../.claude/rules/review-process.md)
