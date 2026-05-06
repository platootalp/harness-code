# OpenHarness 3人 + CC 开发分工

## 系统规模

| 指标 | 数据 |
|------|------|
| 总代码量 | ~38,800 LOC (Python + TypeScript) |
| Python 文件 | 205 个 .py 文件 |
| 工具实现 | 45 个 |
| 聊天平台 | 9+ 个 |
| 预估工期 | 12-18 个月（全职） |

---

## 人员分配

| 角色 | 负责人 | 负责模块 |
|------|--------|----------|
| **P0 - 核心引擎** | 开发者 A | config, api, auth, permissions, tools, engine, mcp, sandbox |
| **P1 - 功能集成** | 开发者 B | tasks, subagent, memory, context, skills, swarm, plugins, channels |
| **P2 - 前端 & 编排** | 开发者 C | ui, commands, state, prompts, hooks, services, bridge |

---

## 详细模块归属

### P0 - 核心引擎 (开发者 A)

```
config/           # 配置系统（所有模块依赖）
platforms/        # 平台检测
utils/            # 工具函数
engine/messages/  # 消息类型定义
engine/stream_events/  # 流事件类型
api/              # API 客户端（Anthropic, OpenAI, Codex）
auth/             # 认证管理
permissions/      # 权限系统
tools/            # 工具注册表 + 基础工具实现
engine/           # 查询引擎（核心 Agent Loop）
mcp/              # MCP 协议支持（依赖 tools）
sandbox/          # 沙箱执行（依赖 tools）
```

**关键路径**: `config → api/auth → engine → tools`

### P1 - 功能集成 (开发者 B)

```
tasks/            # 后台任务管理
subagent/         # 子智能体支持
memory/           # 记忆管理
context/          # 上下文管理
skills/           # 技能加载
swarm/            # 多智能体协调
plugins/          # 插件系统
channels/         # 9个聊天平台适配器（最后做）
```

### P2 - 前端 & 编排 (开发者 C)

```
ui/               # React/Ink TUI 界面
commands/         # CLI 命令注册
state/            # 应用状态
prompts/          # Prompt 构建
hooks/            # Hook 执行器
services/         # 服务层（压缩、会话存储）
bridge/           # 桥接会话管理
```

**最后集成**，依赖 P0 和 P1 的模块。

---

## 模块依赖关系

```
Tier 0 - 基础层（无内部依赖）:
config, platforms, utils, engine/messages, engine/stream_events

Tier 1 - 核心基础设施:
api, auth, permissions

Tier 2 - 执行核心:
tools, coordinator, engine, mcp, sandbox

Tier 3 - 服务与扩展:
hooks, services, prompts, memory, swarm, tasks, skills, plugins, channels, bridge

Tier 4 - 应用层:
ui, commands, state
```

---

## 开发阶段

### Phase 1: 基础设施 (Week 1-4)

| 开发者 | 任务 |
|--------|------|
| P0 | config, api, auth, permissions, tools, engine, mcp, sandbox |
| P1 | 准备 channels 接口定义，先不动实现 |
| P2 | 准备 ui 和 commands 骨架 |

### Phase 2: 功能开发 (Week 5-12)

| 开发者 | 任务 |
|--------|------|
| P0 | 完善 tools/mcp/sandbox 实现，响应 P1/P2 的接口需求 |
| P1 | **tasks → subagent → context+memory** |
| P2 | ui 骨架开发，commands 完善 |

### Phase 3: 功能开发续 & 集成 (Week 13-20)

| 开发者 | 任务 |
|--------|------|
| P0 | mcp/sandbox 完善，性能优化，Bug 修复 |
| P1 | **skills → swarm** |
| P2 | ui 开发，commands 完善 |

### Phase 4: 扩展功能 & 收尾 (Week 21-26)

| 开发者 | 任务 |
|--------|------|
| P0 | Bug 修复，性能优化 |
| P1 | **plugins → channels** |
| P2 | 收尾 |

---

## 关键依赖提醒

### P0 最关键
所有其他人都依赖他的接口（tools、mcp、sandbox 尤为关键）。如果 P0 延迟，整个项目延迟。

### 每日对齐
- 每天 P0 和 P1/P2 对齐接口，确保需求清晰
- 使用 CC 帮忙写测试、文档、简单工具实现

### 提前准备
- P2 可以先做 ui 骨架，不依赖 engine 实现
- P1 可以先定义 channels 接口，具体实现等 engine 就绪

---

## P1 模块优先级

1. **tasks** — 后台任务管理
2. **subagent** — 子智能体支持
3. **context + memory** — 上下文管理与记忆
4. **skills** — 技能加载
5. **swarm** — 多智能体协调
6. **plugins** — 插件系统
7. **channels** — 9个聊天平台（最后做，依赖 engine 稳定）

---

## P1 任务简介（简历级别）

### 1. 任务层

```
- DAG 任务分解与调度引擎
  技术：拓扑排序 / 并行执行计划 / 任务状态机
  解决：任务依赖混乱、串行阻塞、执行效率低下
  成果：支持任务并行调度，利用率提升 N 倍

- 后台任务管理与优先级队列
  技术：优先级队列 / 任务持久化 / 后台 Worker
  解决：长时间运行任务的后台化、任务丢失
  成果：支持后台执行、任务可恢复

- TODOList 任务管理
  技术：任务看板 / 优先级排序 / 状态流转
  解决：任务散落、状态不清、难追踪
  成果：可视化任务管理、状态一目了然
```

### 2. 上下文

```
- 检索（Retrieval）
  技术：向量数据库 / 语义搜索 / 混合检索
  解决：记忆量大、难以快速找到相关内容
  成果：毫秒级语义检索、精准召回

- 选择（Selection）
  技术：重要性评分 / 上下文相关性 / 过滤策略
  解决：无关信息淹没关键上下文
  成果：智能筛选、只保留高价值上下文

- 构建（Construction）
  技术：Prompt 模板 / 动态组装 / 角色适配
  解决：上下文拼接混乱、Prompt 质量不稳
  成果：高质量 Prompt 自动构建、稳定可靠

- 压缩（Compression）
  技术：LLM 摘要 / 滑动窗口 / 重要性评分
  解决：上下文长度超出模型限制
  成果：自动压缩、关键信息不丢失

- 提取（Extraction）→ 长期记忆
  技术：实体抽取 / 知识图谱 / 持久化存储
  解决：重要信息未能转化为长期记忆
  成果：跨会话知识积累、持续学习
```

### 3. 编排

```
- 编排器（Orchestrator）+ Subagent 模式
  技术：任务分发 / 资源调度 / 结果聚合
  解决：主 Agent 负载过重、无法并行处理
  成果：主从 Agent 协作、效率倍增

- Agent Team 模式（Swarm）
  技术：注册中心 / 心跳检测 / 故障转移
  解决：多 Agent 协作难、状态同步复杂
  成果：多 Agent 动态组队、自动容错

- Agent 消息路由
  技术：消息队列 / 协议适配器 / 路由表
  解决：不同 Agent 间消息格式不通
  成果：统一消息协议、跨 Agent 通信
```

### 4. 集成

```
- 技能（Skills）按需加载与执行
  技术：动态加载 / 技能沙箱 / 版本管理
  解决：技能膨胀、加载慢、版本冲突
  成果：按需加载技能、秒级响应

- 插件系统（Plugin）生态
  技术：插件发现 / 热加载 / 接口契约
  解决：功能扩展繁琐、耦合主代码库
  成果：第三方插件即插即用、生态开放

- 多平台消息通道（Channels）适配
  技术：统一消息模型 / 平台 SDK 适配器
  解决：各平台 API 差异大、维护成本高
  成果：一套代码支持 9+ 平台、快速接入新平台
```

---

## 最小可行核心

系统启动所需的最少模块：

```
config          # 配置系统
platforms       # 平台检测
engine/messages # 消息类型
api             # API 客户端
auth            # 认证管理
permissions     # 权限系统
tools           # 工具注册表
engine          # 查询引擎
mcp             # MCP 协议支持
sandbox         # 沙箱执行
prompts         # Prompt 构建
hooks           # Hook 系统
services        # 服务层
ui              # 应用界面
