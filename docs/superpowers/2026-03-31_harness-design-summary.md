# Harness Design for Long-Running Apps — 技术总结

> **来源：** https://www.anthropic.com/engineering/harness-design-long-running-apps
> **作者：** Prithvi Rajasekaran, Anthropic Labs team
> **日期：** 2026-03-24

---

## 背景与核心问题

Anthropic 团队在尝试让 Claude 生成高质量前端设计、以及构建无需人工干预的完整应用时，遇到了瓶颈：基本的 prompt engineering 无法突破性能天花板。

**两个核心挑战：**
1. 让 Claude 生成高质量前端设计
2. 构建完全无需人工干预的完整应用

---

## 核心洞察：Generator-Evaluator 模式

灵感来自 GAN（生成对抗网络）。

### 问题：Self-Evaluation Bias

> "Agents tend to respond by confidently praising the work—even when, to a human observer, the quality is obviously mediocre."

Agent 对自己的输出存在过度自信的偏见，无法客观评价自己的工作质量。

### 解决方案：Generator-Evaluator 分离

```
┌──────────────┐                      ┌──────────────┐
│  Generator   │                      │  Evaluator   │
│   (生成)      │────── 产出 ─────────→│   (评判)     │
│              │                      │              │
│              │←───── 反馈 ──────────│              │
└──────────────┘                      └──────────────┘
```

**关键发现：**
- 分离"干活"和"评判"比让 generator 自我批判更有效
- "Tuning a standalone evaluator to be skeptical turns out to be far more tractable than making a generator critical of its own work."

---

## Context 管理

### Context Anxiety

部分模型表现出"context anxiety"：接近 context limit 时会过早收尾。

### 两种处理方式对比

| 方式 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **Context Reset** | 完全清空 context window，用结构化 artifact 交接 | 提供干净的 slate | 需要良好的状态传递 |
| **Compaction** | 在原位总结早期对话 | 保留上下文 | 没有干净 slate，context anxiety 仍可能存在 |

**经验：**
- Claude Sonnet 4.5 的 context anxiety 严重到 compaction 不够用，必须用 context reset
- Opus 4.6 大幅改善，几乎消除了这个问题

---

## 前端设计实验

### 四维度评分标准

| 标准 | 问题 | 权重 |
|------|------|------|
| **Design Quality** | 设计是否像一个整体而非零件堆砌？ | 高 |
| **Originality** | 是否有自定义决策，还是模板/库默认/AI生成图案？ | 高 |
| **Craft** | 技术执行——排版层级、间距一致性、色彩和谐度、对比度 | 低（默认表现就好） |
| **Functionality** | 用户能否理解界面、完成操作而不需要猜测？ | 低（默认表现就好） |

**设计原则：** 明确惩罚"AI slop"模式，并主动引导设计师向"museum quality"收敛。

### 实现细节

- 使用 Claude Agent SDK 构建
- Evaluator 配备 Playwright MCP，直接与运行中的页面交互
- 每次生成 5-15 轮迭代
- 完整运行可达 4 小时

### 关键发现

> "Even on the first iteration, outputs were noticeably better than a baseline with no prompting at all, suggesting the criteria and associated language themselves steered the model away from generic defaults."

**创意飞跃案例（荷兰艺术博物馆）：**
- 第 9 轮：生成干净暗色主题的落地页
- 第 10 轮：完全推翻重来，重新构想为空间体验——CSS perspective 渲染的 3D 房间、棋盘格地板、自由布局的画作、门式导航切换房间

---

## 全栈开发：三 Agent 架构

### Agent 角色定义

```
┌─────────────────────────────────────────────────────────────────┐
│                         Planner Agent                           │
│  - 将 1-4 句 prompt 扩展为完整产品 spec                          │
│  - 保持产品上下文和高层技术设计                                   │
│  - 避免陷入细节以防止错误级联                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Generator Agent                           │
│  - 按 sprint 工作，一次一个功能                                   │
│  - 技术栈：React, Vite, FastAPI, PostgreSQL                     │
│  - 每个 sprint 结束时自我评估                                    │
│  - 配备 git 版本控制                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Evaluator Agent                           │
│  - 使用 Playwright MCP 测试运行中的应用                          │
│  - 按产品深度、功能性、视觉设计、代码质量评分                     │
│  - 每个标准有硬阈值，任意一项低于阈值则 sprint 失败               │
└─────────────────────────────────────────────────────────────────┘
```

### Sprint Contract

> "Before each sprint, the generator and evaluator negotiated a sprint contract: agreeing on what 'done' looked like for that chunk of work before any code was written."

每个 sprint 开始前，generator 和 evaluator 协商完成标准。

### 通信方式

通过文件交互：一个 agent 写文件，另一个读文件响应。

---

## 实验对比：Retro Game Maker

**Prompt：** "Create a 2D retro game maker with features including a level editor, sprite editor, entity behaviors, and a playable test mode."

| 方式 | 时长 | 成本 |
|------|------|------|
| Solo | 20 min | $9 |
| Full Harness | 6 hr | $200 |

### Solo 运行问题

- 固定高度面板导致视口大部分空白
- 刚性工作流，无 UI 引导
- 游戏损坏——实体出现但无响应
- "实体定义和游戏运行时之间的连接断开"

### Harness 运行优势

- Canvas 使用完整视口
- 一致的视觉识别，追踪设计方向
- 内置 Claude 集成用于 AI 辅助生成
- 播放模式实际可用

---

## Evaluator 发现案例（具体 bug）

| Contract 标准 | Evaluator 发现 |
|---------------|----------------|
| Rectangle fill tool allows click-drag to fill rectangular area | FAIL — 工具只在拖动起点/终点放置 tiles |
| User can select and delete placed entity spawn points | FAIL — Delete key handler 要求同时设置 `selection` 和 `selectedEntityId` |
| User can reorder animation frames via API | FAIL — 路由定义在 `/{frame_id}` 路由之后，FastAPI 把 'reorder' 匹配为 frame_id 整数 |

---

## DAW 实验

**Prompt：** "Build a fully featured DAW in the browser using the Web Audio API."

| Agent & Phase | Duration | Cost |
|---------------|----------|------|
| Planner | 4.7 min | $0.46 |
| Build (Round 1) | 2 hr 7 min | $71.08 |
| QA (Round 1) | 8.8 min | $3.24 |
| Build (Round 2) | 1 hr 2 min | $36.89 |
| QA (Round 2) | 6.8 min | $3.09 |
| Build (Round 3) | 10.9 min | $5.88 |
| QA (Round 3) | 9.6 min | $4.06 |
| **Total V2 Harness** | **3 hr 50 min** | **$124.70** |

### QA 反馈示例

**Round 1：** "Several core DAW features are display-only without interactive depth: clips can't be dragged/moved on the timeline, there are no instrument UI panels (synth knobs, drum pads), and no visual effect editors."

**Round 2：** "Audio recording is still stub-only (button toggles but no mic capture). Clip resize by edge drag and clip split not implemented. Effect visualizations are numeric sliders, not graphical."

---

## Harness 简化历程

### 移除 Context Reset（Opus 4.6 后）

> "It plans more carefully, sustains agentic tasks for longer, can operate more reliably in larger codebases, and has better code review and debugging skills."

### 移除 Sprint 构造

从完全移除 sprint 开始，但保留了 planner 和 evaluator：
- 没有 planner，generator 会低估工作量
- evaluator 仍然能 catch 有意义的问题

### Evaluator 角色演进

> "The evaluator is not a fixed yes-or-no decision. It is worth the cost when the task sits beyond what the current model does reliably solo."

---

## 核心原则

### 1. 保持简单

> "Find the simplest solution possible, and only increase complexity when needed."

每个 component 都编码了对模型能力的假设，需要不断重新评估。

### 2. 模型进步不减少 harness 组合空间

> "The space of interesting harness combinations doesn't shrink as models improve. Instead, it moves."

模型变强后，旧组件可能不再需要，但新的更强大组件会出现。

### 3. 模型更新后重新审视 Harness

> "When a new model lands, it is generally good practice to re-examine a harness, stripping away pieces that are no longer load-bearing to performance and adding new pieces to achieve greater capability."

### 4. 任务分解

对于复杂任务，分解任务并应用专门 agent 到每个方面是有帮助的。

### 5. 评分标准塑造输出

> "Including phrases like 'the best designs are museum quality' pushed designs toward a particular visual convergence."

---

## 核心引用

> "Agents tend to respond by confidently praising the work—even when, to a human observer, the quality is obviously mediocre."

> "Separating the agent doing the work from the agent judging it proves to be a strong lever."

> "Tuning a standalone evaluator to be skeptical turns out to be far more tractable than making a generator critical of its own work."

> "The evaluator is worth the cost when the task sits beyond what the current model does reliably solo."

> "The space of interesting harness combinations doesn't shrink as models improve. Instead, it moves."

> "Every component in a harness encodes an assumption about what the model can't do on its own—and those assumptions are worth stress testing."

---

## 对 Mozi 的启示

### 1. Generator-Evaluator 架构

可考虑为 Orchestrator 层引入独立的 evaluator 进行结果校验，特别是在代码生成和测试场景中。

### 2. 三层 Agent 结构

- **Planner** → 扩展需求为详细 spec
- **Generator** → 一次实现一个功能
- **Evaluator** → 评分 + 可执行反馈

### 3. Sprint Contract 机制

在 task 模块引入"完成标准"协商，弥合需求和可测试标准之间的鸿沟。

### 4. Context 管理策略

根据使用的模型版本选择合适的 context 管理方式。Opus 4.6+ 可简化处理。

### 5. 评分标准设计

设计具体的、可操作的评分维度，明确惩罚不希望出现的行为（如"AI slop"）。

### 6. 复杂度匹配

结合 Mozi 的 complexity-based routing (SIMPLE ≤40, MEDIUM 40-70, COMPLEX >70)：
- SIMPLE 任务：可走简化流程
- COMPLEX 任务：走完整 harness

### 7. 迭代优化

完整的 generator-evaluator 循环可达多轮，每轮基于上一轮反馈进行改进。

---

## 附录：成本-质量权衡

| 任务类型 | Solo | Harness | 质量提升 |
|----------|------|---------|---------|
| Simple | 快且便宜 | 不值得 | 一般 |
| Complex | 20min/$9 | 6hr/$200 | 显著 |
| Very Complex (DAW) | 不可行 | 3hr50min/$125 | 达到可用 |

**结论：** Harness 的额外成本在大复杂任务上是值得的。
