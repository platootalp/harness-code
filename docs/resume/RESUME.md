## 三、项目经历

### Mozi AI Coding Agent

**项目简介**：从 0 到 1 构建的 AI 编程 Agent，支撑需求->编码->测试的自动化闭环。

**核心成果**：需求 AI 渗透率 87.4% | AI 代码采纳率 59.5% | 交付时长下降 30%+

---

### 1. 多智能体编排

- 基于 Orchestrator-Worker 模式构建多智能体编排层：Orchestrator 负责任务分解、决策与调度，Worker 负责无状态执行
- Orchestrator 内部实现 ReAct 循环（Thought → Decide → Delegate → Review），支持复杂任务的动态规划与执行
- Orchestrator 维护全局状态（任务进度、决策历史），支持断点续传；Worker 通过最小上下文隔离避免信息泄露
- Orchestrator 根据任务复杂度自动路由到不同执行模式（QUICK/DEEP/STRATEGIC）

### 2. 任务规划与拆解

- 基于 LLM 实现任务分解，结合规则引擎验证分解质量（完整性、原子性、独立性、可验证性）
- 通过 DAG 管理子任务依赖关系，拓扑排序生成可并行执行计划
- 支持后台任务执行，任务进度实时同步到会话 TODOList 清单

### 3. 高可用工具体系

- 内置 15+ 工具：6 种文件操作工具（Read/Write/Edit/Glob/Grep/Bash）、2 种代码分析工具（AST-Grep/LSP）、3 种外部能力工具（WebSearch/WebFetch/Skills）、4 种任务工具（TaskCreate/TaskGet/TaskUpdate/TaskList）
- 统一工具抽象接口，支持工具动态注册与发现
- 安全执行：路径白名单验证、危险函数静态检测、权限级别控制

### 4. 上下文管理

- 双轨上下文处理：Push（预加载高频信息）+ Pull（JIT 按需探索）
- 基于 token 阈值触发 Compress 策略（LLM 摘要压缩）；Write 策略（引用卸载）保留高价值信息；Isolate 策略（子代理隔离）处理复杂多模块任务
- Agent 自主 JIT 探索机制：按需调用工具探索代码库，而非预设检索规则
- 支持上下文快照分层加载，避免重复压缩

### 5. 知识系统管理

- 混合记忆系统：短期记忆（滑动窗口）+ 长期记忆（语义/情景/程序）
- 向量检索引擎，支持语义相似度匹配 + 元数据过滤
- 多后端存储抽象，支持 Milvus/PGVector 等主流向量数据库
- 记忆冲突解决：相似度去重 + 增量合并 + 版本历史

### 6. 观测与评估

- 基于 OpenTelemetry 构建可观测性体系：结构化日志 + 分布式追踪 + Metrics 指标
- 完整调用链追踪：从请求入口到工具执行的端到端可视化
- Phoenix Evals 评估框架，支持 LLM 输出质量评估与检索评估
- 支持多种 Trace 传播协议（进程内/跨进程/事件驱动）
