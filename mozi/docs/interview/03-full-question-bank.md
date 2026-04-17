# 全方位简历拷打问题库

> 针对简历各模块的深层追问，按领域分类。包含基础版 + 深入追问版。

---

## 一、AI Coding Agent 项目

> **说明**: 本节基于项目实际架构设计文档编写，参考：
> - [2026-03-31_orchestrator.md](./docs/init/module/2026-03-31_orchestrator.md)
> - [2026-04-01-complexity-scoring-design.md](./docs/superpowers/specs/2026-04-01-complexity-scoring-design.md)
> - [2026-03-31_architecture_design.md](./docs/init/2026-03-31_architecture_design.md)

### 1.1 架构决策（基础版）

**Q1:** 你提到"Orchestrator-Worker 状态中枢"，但 AutoGPT、CrewAI 都用类似架构。你的核心差异化是什么？Orchestrator 是"智能大脑"（有状态、做决策），Sub-Agent 是"无状态执行器"（用完即焚），对比过竞品吗？

**Q2:** ReAct 循环的退出条件，"最大轮次耗尽"设置了多少？QUICK=5次、DEEP=15次、STRATEGIC=30次。如果 LLM 在第 8 轮突然开始幻觉但还没触发退出，怎么应对？

**Q3:** "复杂度-风险双维路由"中，复杂度 0-100 分数是怎么量化的？"重构 user service"涉及 4 步、4 个文件、需搜索代码库和生成测试，为什么是 45 分而不是 40 或 50？

**Q4:** SIMPLE/MEDIUM/COMPLEX 三级复杂度怎么映射到 QUICK/DEEP/STRATEGIC 执行策略？边界是 ≤40/41-70/>70。切换触发条件是什么？有没有出现过模式选错导致的问题？

**Q5:** "5 类领域专家 Sub-Agent"协同（Planner/Coder/Explorer/QualityChecker/Reviewer），Reviewer 和 Coder 同时改一个文件，谁优先级高？有没有出现过 reviewer 否决但 coder 继续基于旧代码开发的情况？

### 1.1 架构决策（深入追问版）

#### Orchestrator 形态追问

**Q1.1:** Orchestrator 是一个进程还是一个服务？如果是进程，和 Worker 之间怎么通信？同进程内调用？

**Q1.2:** Orchestrator 的状态存在哪？内存？SQLite？进程重启后状态怎么恢复？

**Q1.3:** Orchestrator 是单实例还是多实例？多实例会不会脑裂？状态同步怎么做？

**Q1.4:** 你的架构和 AutoGPT/CrewAI/LangGraph 到底有什么区别？Orchestrator 参与决策还是只做调度？

**Q1.5:** Orchestrator 调用 LLM 的频率是多少？每个子任务都调？还是只在关键节点调（澄清检查、复杂度评分、路由决策）？

**Q1.6:** Orchestrator 三步预处理是什么？Clarification Check → Complexity Assessment → Routing 每个状态的进入/退出条件是什么？

#### ReAct 循环追问

**Q2.1:** ReAct 循环的四个阶段：Thought → Decide → Delegate → Review。具体在代码里怎么实现？

**Q2.2:** "任务完成"怎么定义？LLM 自己说完成了就完成了？还是有 QualityChecker 的质量报告或 Reviewer 的语义验收？

**Q2.3:** 最大轮次是多少？QUICK=5次、DEEP=15次、STRATEGIC=30次。为什么设这些值？

**Q2.4:** "明确放弃"的触发条件是什么？LLM 说"做不到"？连续 N 次返回相同结果？达到最大迭代次数？

**Q2.5:** Clarification Check 用的是 LLM 自我反思还是规则判断？评估 Prompt 具体是什么？

**Q2.6:** Sub-Agent 返回的结果由谁审核？Orchestrator 自己还是独立的 Reviewer？

**Q2.7:** Agent 的 Thought 是存状态里还是每次重新生成？如果存状态，占多少 Token？

**Q2.8:** 你遇到过最离谱的 ReAct 幻觉是什么？LLM 编造文件路径？记错前 N 轮观察结果？

**Q2.9:** 迭代控制具体怎么实现？到达上限后怎么办？

#### 复杂度-风险路由追问

**Q3.1:** 复杂度计算公式：
- 任务维度得分 = (任务指标总和 / 9) × 50
- 技术维度得分 = (技术指标总和 / 12) × 30
- 不确定性维度 = (不确定指标总和 / 9) × 20
权重 50%/30%/20% 是人工设定还是 ML 学出来的？

**Q3.2:** 0-100 分数怎么归一化的？Category 边界：≤40 → SIMPLE(QUICK)、41-70 → MEDIUM(DEEP)、>70 → COMPLEX(STRATEGIC)。为什么是 40 和 70 这两个阈值？

**Q3.3:** 谁来计算复杂度？Orchestrator 在收到任务时计算？还是边执行边调整？复杂度变了模式会切换吗？

**Q3.4:** 风险维度中，"操作可逆性"、"影响范围"、"数据敏感性"怎么打分？删除文件/修改文件/修改配置分别打多少分？

**Q3.5:** 复杂度等级与执行策略是同一概念，SIMPLE 即 QUICK，MEDIUM 即 DEEP，COMPLEX 即 STRATEGIC。风险等级用于在同一复杂度内调整策略细节（高风险倾向于更审慎的执行路径）。具体怎么调整？

**Q3.6:** 复杂度评估的时机？任务开始前评估一次？每个子任务执行前都评估？动态评估会引入额外延迟吗？

**Q3.7:** QUICK/DEEP/STRATEGIC 的边界：≤40 → QUICK？41-70 → DEEP？>70 → STRATEGIC？那风险维度呢？复杂度 35 但风险 HIGH 算什么模式？

**Q3.8:** 响应延迟降低是怎么算的？基线是什么？吞吐量提升是相对串行执行吗？

**Q3.9:** 有没有出现过模式选错？简单任务走 DEEP（浪费）、复杂任务走 QUICK（结果不对）？能自动纠正吗？

#### 5类 Sub-Agent 协作追问

**Q4.1:** 每个 Sub-Agent 的 Prompt 具体是什么？Planner 分解完任务后会自己执行吗？Coder 写完代码会自己做 basic review 吗？QualityChecker 发现 bug 会直接告诉 Coder 怎么改吗？

**Q4.2:** Sub-Agent 之间的通信机制是什么？共享状态？消息传递？还是通过 Orchestrator 中转？

**Q4.3:** 每个 Sub-Agent 是独立进程还是同一进程的不同实例？进程间通信开销有多大？状态隔离怎么做？

**Q4.4:** Sub-Agent 的设计原则：最小暴露（只接收完成当前任务所需的上下文）、摘要返回（返回压缩摘要而非完整输出）、用完即焚（完成后不保留上下文）。实际怎么实现？

**Q4.5:** Agent A 申请锁被批准，Agent B 申请锁被拒绝进入等待队列。B 等多久？等期间干什么？A 拿了锁后宕了锁怎么释放？超时多久？

**Q4.6:** 场景：Coder 写完 v1，Reviewer 说"第 20 行有 bug"，Coder 开始改但状态里还是 v1，基于 v1 做了其他修改，最后提交的是 v1 的修改而非 reviewer 要求的。怎么处理？

**Q4.7:** 任务分配策略是什么？Orchestrator 决定"这个子任务给哪个 Sub-Agent"？规则引擎还是 LLM 决定？怎么避免 LLM 偏见？

**Q4.8:** Coder Sub-Agent 正在忙，来了新编码任务。排队等？分配给其他 Sub-Agent？还是创建新实例？最大并发数多少？

#### Planner 任务分解追问

**Q5.1:** LLM 分解出的任务是串行（分析需求 → 写代码 → 测试），但真的必须串行吗？分析需求和写代码能不能并行？如果 LLM 说"分析需求"需要"写代码"的结果（反向依赖）怎么办？

**Q5.2:** 任务分解的输出是什么？TODO 列表？有依赖关系吗？DAG 怎么生成？

**Q5.3:** 四维度校验（完整性/原子性/独立性/可验证性）不通过率是多少？不通过后回传 LLM 重分解还是自动修复？

**Q5.4:** 检测到环形依赖（A → B → C → A）后怎么办？重分解 prompt 是什么？重分解 3 次失败后人工介入？

**Q5.5:** 100 个子任务，最多能并行多少个？受什么限制？CPU 核心数？LLM API 限流？Sub-Agent 实例数？

**Q5.6:** Task A 需要 8GB 内存，Task B 需要 8GB 内存，系统只有 10GB。调度器会同时调度 A 和 B 吗？OOM 了怎么办？

**Q5.7:** Planner 的任务分解是直接输出 TODO 列表还是带依赖关系的任务图？拓扑排序用 Kahn 还是 DFS？

**Q5.8:** Planner 分解任务时，Orchestrator 提供什么上下文？最小暴露原则下，Planner 能看到多少历史对话？

#### 分层上下文追问

**Q6.1:** Context 模块的 Snapshot 分层：
- Snapshot-0：原始消息（最近 10 条）
- Snapshot-1：压缩快照 #1（50 轮摘要）
- Snapshot-2：压缩快照 #2（200 轮摘要）
- Offload：外部存储（按需 Reload）
这个分层机制具体怎么实现？触发条件是什么？

**Q6.2:** Token 阈值是多少？超过阈值怎么触发压缩？Compress 策略是 LLM 摘要还是规则截断？

**Q6.3:** Subagent 隔离边界是什么？进程隔离还是只 context window 隔离？如果是内存隔离，Docker 容器还是进程？创建/销毁开销多大？

**Q6.4:** Subagent 产生长输出，摘要后回传多少？摘要内容是什么？结论？执行步骤？摘要质量怎么保证？

**Q6.5:** "避免交叉污染"——Subagent A 修改了全局配置，Subagent B 会感知到吗？隔离基于 namespace 还是虚拟内存？

**Q6.6:** JIT 探索机制：Agent 自主按需探索（grep/ls/read_file），而非预设检索规则。具体怎么实现？Orchestrator 怎么知道 Agent 需要什么上下文？

**Q6.7:** Context 模块的 Compress 策略：当 token >= 阈值（默认 80%）时自动触发，通过 LLM 摘要压缩上下文。这个阈值固定还是动态？

**Q6.8:** Push 预加载：自动预加载高频通用上下文（项目规范、开发偏好等）~30% tokens。这个比例怎么定的？

**Q6.9:** 工具结果过长时，会 Offload 到本地文件。文件存哪？本地磁盘还是分布式文件系统？TTL 多久？

**Q6.10:** 做过压缩后信息丢失率测试吗？原始上下文和压缩后上下文的语义相似度是多少？任务完成率下降多少？

### 1.2 指标与数据

**Q6:** "任务完成率提升"——基线是什么？对照组怎么设计？统计显著性检验做了吗？

**Q7:** "AI 渗透率、代码采纳率"——谁统计的？会不会只是点了一下对话框就算"渗透"？

**Q8:** "需求平均交付时长下降"——相对什么基准？有没有排除其他变量（人员变化、需求复杂度变化）？

**Q9:** "PB 级存储"、"200+ 业务调用"——实际数字是多少？峰值 QPS？

### 1.3 技术细节

**Q10:** 复杂度评分用的是什么算法？规则+启发式方法？具体怎么识别步骤数量、文件数量、关键词？

**Q11:** 分层上下文架构，Token 阈值是固定还是动态？1000 轮对话压缩率多少？做过信息丢失率评估吗？

**Q12:** 哈希锚定并发冲突检测，LINE#ID + 内容哈希双重校验的具体实现？哈希碰撞怎么处理？

**Q13:** "15+ 内置工具"——工具接口契约是什么？升级兼容性怎么保证？

**Q14:** 四级容错机制（L1 超时重试 → L2 降级 → L3 熔断 → L4 人工），能画一个错误从发生到处理的完整流程图吗？

**Q15:** "需求 AI 渗透率 | AI 代码采纳率"——这个数据采集的埋点在哪里？有没有可能被刷单？

### 1.4 实战问题

**Q16:** 最离谱的 LLM 幻觉是什么？系统怎么兜底？

**Q17:** "删掉所有测试文件然后重写"——安全评估机制在哪一层拦截？Clarification Check 的风险感知？

**Q18:** "代码编辑冲突率降低"——基线是什么？有没有哈希锚定失效的 case？

**Q19:** "万行代码库检索延迟相比传统 grep 提升"——测试基线和测试方法？百万行级别呢？

---

## 二、文件服务平台项目

### 2.1 多云架构（基础版）

**Q20:** 腾讯 COS 和华为 OBS 的 API 差异大吗？策略模式+适配器模式，有遇到过语义不一致无法抽象的情况吗？

**Q21:** "双云数据同步与故障自动切换"——同步元数据还是文件内容？上传大文件时主云故障，状态怎么恢复？

**Q22:** "RTO < 30s、RPO ≈ 0、SLA >= 99.95%"——怎么测出来的？真做过故障演练还是估算的？

**Q23:** "灰度切流（AppID 级别 + 流量比例）"——实现细节？切流过程中数据一致性怎么保证？

**Q24:** "存储成本优化 20%+"——怎么算的？具体优化了什么（冷热分层、压缩、生命周期管理）？

### 2.1 多云架构（深入追问版）

#### COS/OBS API 差异追问

**Q20.1:** 存储概念差异——COS 用 AppId+Bucket+Object，华为 OBS 用 Bucket+Object。你的适配层怎么抽象？upload(bucket, key, data) 怎么兼容 COS 的 {name}-{appid} 命名格式？

**Q20.2:** 认证机制差异——COS 用 STS 临时密钥，华为用 AK/SK。你的 Auth 适配层怎么设计？统一成一个 Auth 对象还是分开两种？

**Q20.3:** 分片上传 API 差异——虽然都叫 initMultipartUpload/uploadPart/completeMultipartUpload，但签名前的 stringToSign 格式完全不同。你怎么统一这个差异？还是分别实现三套？

#### 灰度切流追问

**Q23.1:** 切流的映射数据（AppID → 云厂商、权重）存在哪？内存？Redis？MySQL？为什么？

**Q23.2:** 切流一致性——AppID=123 从腾讯切到华为过程中，用户 A 上传文件路由到腾讯，用户 B 读文件路由到华为，但文件可能还在同步中。怎么处理"文件在老云但请求在新云"的情况？

**Q23.3:** 切流后老云数据处理——切流完成后老云文件删不删？立即删？保留多久？存储成本怎么算？

#### 双云同步追问

**Q21.1:** 同步粒度——同步元数据还是文件内容？还是两者都同步？先写老云还是新云？还是并行写？双写延迟是多少？

**Q21.2:** 大文件上传中断——用户上传 5GB 文件到 80%，腾讯云故障，切换华为云。华为云从哪开始接？从头传？还是从 80% 继续？进度状态存哪？

**Q21.3:** 故障判断——什么条件判定"主云故障"？网络不通？超时率超阈值？返回特定错误码？如果判断错了误切换怎么办？

#### RTO/RPO 追问

**Q22.1:** RTO 30s 怎么测的？真的杀掉云节点？还是模拟故障（配置切换流量）？演练频率多少？测试环境还是生产环境？

**Q22.2:** RPO ≈ 0 怎么保证？主云写入成功还没同步到从云时主云挂了，这部分数据丢了怎么办？RPO ≈ 0 只适用于某些场景？

**Q22.3:** 99.95% SLA 是云厂商给的还是自己统计的？统计口径是什么？包含计划内维护吗？

### 2.2 性能优化（基础版）

**Q25:** "核心接口 P99 延迟从 800ms 降至 300ms"——profiling 数据在哪？怎么定位到瓶颈的？具体优化了哪几个点？

**Q26:** "流式中转基于流式 IO 实现背压控制"——背压实现细节？上游 > 下游速度时缓冲区满了怎么办？

**Q27:** "5GB+ 大文件上传成功率从 85% 提升至 99.5%+"——怎么做到的？分片大小怎么定？并行度多少？

**Q28:** "分片元数据管理（MySQL + Redis 二级缓存）"——缓存不一致怎么解决？Redis 挂了怎么办？

### 2.2 性能优化（深入追问版）

#### 800ms → 300ms 追问

**Q25.1:** 800ms 分配——网络延迟 50ms + 数据库 300ms + 缓存 10ms + 业务逻辑 200ms + 序列化 100ms + 其他 140ms。你怎么知道各部分耗时？用 Arthas/SkyWalking/APM？能给我看火焰图吗？

**Q25.2:** 数据库慢的原因——慢 SQL 是什么？用了索引吗？数据量多大？优化手段是加索引/读写分离/SQL 重写/分库分表？哪个手段收益最大？

**Q25.3:** 300ms 置信度——P50/P95/P99 最大值分别是多少？如果 P50=100ms、P95=250ms、P99=300ms 但最大值=8000ms，300ms 在美化体验吗？最大值 8000ms 的慢请求是什么场景？

**Q25.4:** 50% 内存降低——原来占用多少？现在占用多少？是峰值/平均/单请求/整个服务内存？统计方法是什么？

#### 背压控制追问

**Q26.1:** 背压实现——push 模式（上游直接推送，缓冲区满则拒绝）vs pull 模式（下游主动拉取）。你用哪种？缓冲区满了怎么办？

**Q26.2:** 流式 IO vs 传统 IO——传统 IO 为什么内存占用高？流式 IO 怎么实现背压控制？具体代码怎么写？

### 2.3 一致性保障（基础版）

**Q29:** "Kafka + 本地消息表保障日均千万级文件处理"——为什么两个都要？只用 Kafka 不行？本地消息表的作用？

**Q30:** "同步/异步双模式"——什么时候用同步什么时候用异步？怎么选？

**Q31:** "任务状态机与回调监听机制"——状态机有哪些状态？状态流转怎么定义的？

**Q32:** "失败重试 + 死信队列 + 人工干预三级容错"——死信进入人工干预的触发条件？自动转人工的流程？

### 2.3 一致性保障（深入追问版）

#### Kafka + 本地消息表追问

**Q29.1:** Kafka 可靠性——acks=all + retries=3 + enable.idempotence=true 能保证消息不丢失。本地消息表的作用是什么？Kafka 的 backup？还是解决"Kafka 挂了"的问题？

**Q29.2:** 本地消息表设计——表结构是什么（消息ID/内容/状态/重试次数/创建时间）？为什么不用 RabbitMQ/RocketMQ 等专业 MQ？

**Q29.3:** 一致性——消息写入本地消息表成功但推送到 Kafka 失败怎么办？定时轮询推送？本地消息表所在机器宕了消息会丢吗？

#### 千万级文件处理 Kafka 设计追问

**Q61（新编号):** Topic 分区设计——单 Topic 还是多 Topic？分区数多少？Topic 命名按业务/时间/租户拆分？日均千万 = 平均 115 QPS，峰值 1000 QPS+，有几个消费者？

**Q62（新编号):** 消费者组规模——消费者数量和分区数关系？分区数和吞吐量关系？Rebalance 什么时候触发？STOP THE WORLD 怎么优化？

#### 死信队列追问

**Q32.1:** 死信触发条件——重试 N 次后仍失败（N=多少？）？特定异常类型？消息格式错误？业务限流？

**Q32.2:** 人工干预流程——谁处理？客服/运营/开发？人工处理后怎么同步回系统？人工干预比例多少？

### 2.4 SDK 开发

**Q33:** "兼容 S3 规范"——S3 哪个版本？所有 API 都兼容了？multipart upload 支持到什么程度？

**Q34:** "秒传"原理？服务端判断文件已存在的机制？MD5 碰撞？

**Q35:** "网络自适应重试策略"——丢包率和延迟怎么采集？动态调整重试的算法？

### 2.5 网关

**Q36:** SpringCloud Gateway 鉴权过滤实现？鉴权服务挂了怎么 fail？

**Q37:** "业务接入时长从 3 天降至 0.5 天"——怎么衡量的？哪些环节省了时间？

---

## 三、后端工程化能力

### 3.1 Java/Spring Cloud（基础版）

**Q38:** 能手写一个 Spring Boot Starter 吗？自动配置怎么实现的？

**Q39:** SpringCloud Gateway 鉴权过滤实现？鉴权服务挂了 fail-open 还是 fail-close？

**Q40:** SpringCloud 改造中最大的技术债务是什么？怎么逐步偿还的？

**Q41:** @Transactional 的 propagation 属性有哪些？REQUIRED 和 REQUIRES_NEW 的区别？什么时候会失效？

**Q42:** Spring Boot 启动流程？Bean 生命周期？循环依赖怎么解决？

### 3.1 Java/Spring Cloud（深入追问版）

#### Spring Boot Starter 追问

**Q38.1:** Starter 结构——xxx-spring-boot-starter/ 下有哪些组件？XxxAutoConfiguration.java + XxxProperties.java + META-INF/spring.factories 或 AutoConfiguration.imports。能写出代码吗？

**Q38.2:** 条件注解执行顺序——@ConditionalOnClass/@ConditionalOnMissingBean/@ConditionalOnProperty/@ConditionalOnWebApplication 的执行顺序是什么？如果两个 @Bean 都有 @ConditionalOnMissingBean 谁先生效？

**Q38.3:** Gateway Filter 加载——Gateway 的 Filter 怎么加载的？你写的鉴权 Filter 怎么被 Spring 扫描到的？为什么有些 Filter 用 @Component 有些用 @Bean？

#### @Transactional 追问

**Q41.1:** 失效场景——非 public 方法失效（为什么）？类内部调用失效（this.methodB() 不走代理）？异常被 catch 吞掉？多数据源没指定？你遇到过哪个？

**Q41.2:** REQUIRED vs REQUIRES_NEW——methodA() 调用 methodB()，methodA() 有 @Transactional，methodB() 有 @Transactional(propagation=REQUIRES_NEW)。methodB() 抛异常，methodA() 会回滚吗？methodA() 抛异常，methodB() 会回滚吗？

**Q41.3:** 隔离级别——READ_UNCOMMITTED/READ_COMMITTED/REPEATABLE_READ/SERIALIZABLE 区别？你在项目里用过哪个？有遇到过脏读/不可重复读/幻读吗？

#### Spring Bean 生命周期追问

**Q42.1:** 生命周期完整流程——实例化 → 属性填充 → 初始化（BeanNameAware → BeanFactoryAware → ApplicationContextAware → BeanPostProcessor.postProcessBeforeInitialization → @PostConstruct → InitializingBean.afterPropertiesSet → init-method → BeanPostProcessor.postProcessAfterInitialization）→ 销毁（@PreDestroy → DisposableBean.destroy → destroy-method）。@PostConstruct 和 InitializingBean 哪个先执行？BeanPostProcessor 作用？

**Q42.2:** 循环依赖解决——Spring 能解决哪些循环依赖（setter + singleton）？不能解决哪些（构造器注入）？三级缓存（singletonObjects/earlySingletonObjects/singletonFactories）各存什么？为什么需要三级？

**Q42.3:** prototype 作用域——prototype Bean 和 singleton Bean 混合使用时，prototype Bean 的依赖怎么注入？prototype Bean 能解决循环依赖吗？

#### SpringCloud Gateway 追问

**Q39.1:** 请求处理流程——RoutePredicateHandlerMapping 匹配 Route → FilteringWebHandler 构建 Filter 链执行 Pre Filter → 代理后端 → 执行 Post Filter。你写的鉴权 Filter 在 Pre 还是 Post？

**Q39.2:** Filter 执行顺序——多个 Filter 的顺序怎么定？@Order(1) vs 配置文件？两个 Filter 都想排第一谁说了算？

**Q39.3:** 熔断降级——Gateway 熔断用 Resilience4j？Hystrix？熔断配置（错误率阈值/熔断时长/降级返回）？你配置过吗？

### 3.2 Python/异步编程（基础版）

**Q43:** asyncio 和多线程的区别？什么场景用 asyncio 反而更慢？

**Q44:** FastAPI 和 Flask 的区别？为什么选 FastAPI？有没有权衡过 Django？

**Q45:** Pydantic BaseModel 怎么用？Field 怎么定义验证？有没有手写过自定义 validator？

**Q46:** "uv 现代包管理"——uv 和 pip 的区别？pyproject.toml 在项目里怎么用？

### 3.2 Python/异步编程（深入追问版）

#### asyncio 本质追问

**Q43.1:** asyncio 陷阱——time.sleep 是阻塞调用会卡事件循环，应该用 asyncio.sleep。忘记 await（result 是协程对象不是数据）。在同步函数里用 await（语法错误）。你遇到过哪个？

**Q43.2:** CPU 密集型问题——JSON 序列化是 CPU 密集型，asyncio 处理会怎样？怎么用 run_in_executor 解决？

**Q43.3:** 事件循环原理——事件循环维护任务队列，不断取出执行，遇到 await 让出控制权，await 完成后 callback 入队。如果一个任务执行时间很长（没有 await）会怎样？怎么用 asyncio.sleep(0) 解决？

**Q43.4:** 多线程 vs asyncio——多线程是 OS 调度（抢占式/共享内存/上下文切换开销/GIL）；asyncio 是协程协作（用户态调度/单线程/切换开销小/必须异步代码）。什么场景用 asyncio 更慢？

#### FastAPI 深入追问

**Q44.1:** FastAPI 架构——FastAPI 实际上是 Starlette 的子类。直接用 Starlette 写 API 怎么写？

**Q44.2:** 依赖注入系统——Depends(get_db) 每次请求都执行 get_db？db 是单例怎么改成 per-request？Depends 执行顺序？

**Q44.3:** 异步 vs 同步路由——async def 和 def 的区别？同步路由会阻塞事件循环吗？在同步路由里调用异步函数会怎样？

#### Pydantic 深入追问

**Q45.1:** BaseModel 验证流程——类型检查 → 默认值 → validator → beforevalidator，验证失败抛 ValidationError。validator（类级别验证多字段）和 field_validator（字段级别验证单字段）区别？

**Q45.2:** ConfigDict 用法——str_strip_whitespace=True（自动去除首尾空格）/ populate_by_name=True（别名和字段名都能用）/ arbitrary_types_allowed=True（允许任意类型）。populate_by_name = True 什么意思？

**Q45.3:** 自定义验证器——跨字段验证怎么写？异步验证怎么写？

#### uv 包管理追问

**Q46.1:** uv vs pip——uv 安装速度 10-100x（Rust 实现）/ 确定性 lock 文件 / 内置 Python 版本管理。uv lock 文件有什么用？

**Q46.2:** uv vs pipenv/poetry——uv 和 pipenv/poetry 的区别？uv sync 和 uv pip install 的区别？

**Q46.3:** pyproject.toml——PEP 621 标准项目配置。[project]（name/version/dependencies）+ [project.optional-dependencies]（dev = ["pytest"]）+ [build-system]。你项目里用过 uv 管理依赖吗？

### 3.3 性能优化（基础版）

**Q47:** SQL 优化举例——你看的是执行计划吗？重点关注哪些字段？

**Q48:** 缓存穿透、缓存雪崩、缓存击穿是什么？怎么处理？

**Q49:** "异步化处理"——具体在哪个项目用过？异步带来的一致性问题怎么解决？

### 3.3 性能优化（深入追问版）

#### SQL 优化追问

**Q47.1:** 执行计划解读——type 列（ref 和 eq_ref 区别）/ key 列（实际用哪个索引）/ rows 列（扫描行数）/ Extra 列（Using index condition 什么意思）。能解读一个实际的执行计划吗？

**Q47.2:** 索引失效场景——LIKE '%xxx%' / OR 条件 / 函数包裹（YEAR()）/ 类型转换（phone varchar 但查 phone = 数字）。你遇到过哪个？分别怎么优化？

**Q47.3:** 慢查询优化例子——优化前 SQL 和执行时间？优化手段（加索引/SQL 重写/读写分离/分库分表）？优化后提升多少倍？

#### 缓存三兄弟追问

**Q48.1:** 穿透——布隆过滤器（存所有存在 key）/ 缓存空值（null 也缓存，短 TTL）。你用哪种？为什么？布隆过滤器的实现原理？误判率怎么算？

**Q48.2:** 雪崩——随机 TTL（每个 key 加随机值）/ 多级缓存（L1+L2+DB）/ Redis 高可用（哨兵/集群）。你用哪种？

**Q48.3:** 击穿——互斥锁（只允许一个查 DB）/ 永不过期（定时更新）/ 逻辑过期（设置"逻辑过期时间"，后台异步更新）。你用哪种？互斥锁的代码怎么写？

**Q48.4:** 一致性——Cache Aside（先读缓存，没有就读 DB 再写缓存；先写 DB 再删除缓存）/ Read-Through（缓存负责查 DB）/ Write-Through（同时写 DB 和缓存）。为什么 Cache Aside 是"删除缓存"而不是"更新缓存"？

#### 异步化追问

**Q49.1:** 异步一致性——MQ 异步解耦场景。异步后怎么通知用户结果？异步任务失败怎么办？

**Q49.2:** 幂等性——MQ 消费失败重试会不会重复处理？怎么保证幂等？唯一键？状态机？

---

## 四、存储与中间件

### 4.1 MySQL（基础版）

**Q50:** 能手写一个事务隔离级别的问题排查吗？脏读、不可重复读、幻读的场景？

**Q51:** InnoDB 和 MyISAM 的区别？为什么选 InnoDB？

**Q52:** explain 执行计划怎么看？哪些字段最重要？

**Q53:** 慢查询优化举例？索引失效的场景？

**Q54:** 分库分表做过吗？分片键怎么选？跨分页查询怎么解决？

### 4.1 MySQL（深入追问版）

#### 事务隔离级别追问

**Q50.1:** 脏读——事务 A 读取了事务 B 未提交的数据，事务 B 回滚。哪个隔离级别会发生？

**Q50.2:** 不可重复读——事务 A 两次读取同一行数据，结果不同（因为事务 B 在中间修改并提交了）。哪个隔离级别会发生？

**Q50.3:** 幻读——事务 A 两次查询结果集不同（因为事务 B 在中间插入/删除了记录）。哪个隔离级别会发生？

**Q50.4:** MVCC 原理——REPEATABLE READ 下 MVCC 怎么实现？Read View 结构？trx_id 的作用？快照读和当前读区别？

**Q50.5:** 你的项目用过哪个隔离级别？为什么选这个？遇到过脏读/不可重复读/幻读吗？

#### InnoDB vs MyISAM 追问

**Q51.1:** 核心区别——聚簇索引（数据和索引在一起）vs 非聚簇索引（分开）/ ACID 支持 vs 不支持 / 行级锁 vs 表级锁。

**Q51.2:** 为什么选 InnoDB？MySQL 5.5+ 默认 InnoDB 但之前默认 MyISAM。InnoDB 的自适应哈希索引了解吗？

#### 执行计划解读追问

**Q52.1:** 关键字段——id（执行顺序）/ type（ALL/INDEX/RANGE/REF/EQ_REF/CONST）/ possible_keys（可能索引）/ key（实际索引）/ rows（扫描行数）/ Extra（Using filesort/Using temporary）。

**Q52.2:** Using filesort 是什么？什么情况出现？怎么优化？

**Q52.3:** Using temporary 是什么？什么情况出现？怎么优化？

**Q52.4:** type 列从好到坏排序：system > const > eq_ref > ref > range > index > ALL。哪些需要优化？

#### 分库分表追问

**Q54.1:** 分片键选择——按用户 ID 分片？按时间分片？按地域分片？分片键不均匀怎么办（热点用户）？

**Q54.2:** 跨分页查询——假设按 user_id 分片，查"第 100 页用户列表"，怎么查？每个分片查一页再合并？这样复杂度是 O(n)？

**Q54.3:** 分片后排序/聚合——GROUP BY、ORDER BY 怎么跨分片执行？

**Q54.4:** 扩容方案——按 ID 取模分片，扩容时怎么迁移数据？一致性 hash 方案？

### 4.2 Redis（基础版）

**Q55:** RDB 和 AOF 的区别？你们用的哪种？为什么？

**Q56:** Redis 集群模式下 key 怎么分布？slot 迁移时请求怎么处理？

**Q57:** 缓存和数据库一致性怎么保证？Cache Aside 和 Read-Through 区别？

**Q58:** Redis 分布式锁怎么实现？Redisson 用的多吗？有没有遇到过锁失效的 case？

**Q59:** Redis 的 ZSet 底层实现？跳表和压缩列表的区别？什么情况切换？

### 4.2 Redis（深入追问版）

#### 持久化追问

**Q55.1:** RDB 原理——定时快照，fork 子进程生成 dump.rdb。优点（文件小/恢复快）缺点（可能丢数据）。

**Q55.2:** AOF 原理——记录每个写命令到 .aof 文件。fsync 策略（everysec/always/no）。优点（数据安全）缺点（文件大/恢复慢）。

**Q55.3:** 你们用哪种？如果两种都用，配置是什么？AOF 的 fsync 策略是 everysec？为什么？

#### 集群与槽迁移追问

**Q56.1:** 槽迁移过程——目标节点 Importing / 源节点 Migrating / 客户端收到 MOVED 重定向 / 客户端更新 slot 缓存。迁移过程中客户端请求会失败吗？原子性怎么保证？

**Q56.2:** 集群一致性——Redis Cluster 是弱最终一致。主节点写入成功后主节点宕机，从节点还没同步完成，哨兵切换从为主。这个过程会不会丢数据？

**Q56.3:** 槽重新分配——集群扩缩容时，槽怎么重新分配？rebalance 过程对线上影响？

#### 分布式锁追问

**Q58.1:** 简单实现——SET key value NX PX timeout。问题：进程拿锁后执行超时怎么办？进程拿锁后宕机怎么办？Redis 挂了锁怎么恢复？

**Q58.2:** Redisson 实现——WatchDog 机制（锁自动续期）。RLock 和 Redis 原生 SET 的区别？

**Q58.3:** 锁失效 case——时钟跳变导致锁提前释放？主从切换导致锁丢失？Redisson 怎么解决？

#### ZSet 底层实现追问

**Q59.1:** 跳表 vs 压缩列表——ZSet 在什么情况下降级为压缩列表？压缩列表转跳表的阈值（zset-max-ziplist-entries / zset-max-ziplist-value）？

**Q59.2:** 跳表原理——为什么是 O(log n) 查找？多层链表的结构？插入时随机决定层数？

### 4.3 Kafka（基础版）

**Q60:** Consumer Group 机制？Rebalance 什么时候触发？Consumer 处理慢怎么办？

**Q61:** "日均千万级文件处理"——单 Topic 还是多 Topic？分区数怎么设计？

**Q62:** 消息积压怎么解决？有没有遇到过？怎么排查的？

**Q63:** Kafka 怎么保证消息不丢失？生产者、Broker、消费者三端分别怎么配置？

**Q64:** Kafka 的 Exactly-Once 语义怎么实现？

### 4.3 Kafka（深入追问版）

#### Consumer Group 追问

**Q60.1:** Rebalance 触发时机——新消费者加入 / 消费者主动离开 / 消费者被踢出（超时）/ 分区数变化。Rebalance 期间会发生什么？"Stop The World"是什么？

**Q60.2:** Rebalance 优化——session.timeout.ms（心跳超时）/ heartbeat.interval.ms（心跳间隔）/ max.poll.interval.ms（最大处理间隔）。怎么避免频繁 Rebalance？

**Q60.3:** Consumer 处理慢——max.poll.records 太大？处理逻辑太重？外部依赖超时？Kafka 有背压机制吗？

#### 消息不丢失追问

**Q63.1:** 生产者配置——acks=0（发送即成功，可能丢）/ acks=1（Leader 确认，可能丢）/ acks=all（ISR 全部确认，最安全）。

**Q63.2:** Broker 配置——replication.factor >= 3 / min.insync.replicas >= 2。

**Q63.3:** 消费者配置——手动提交 offset / 先处理再提交。

**Q63.4:** 你们的项目各端分别怎么配置的？

#### Exactly-Once 追问

**Q64.1:** Producer 幂等性——enable.idempotence=true。幂等 Producer 怎么实现？每条消息有唯一 PID，Broker 只接受 PID 首次出现的消息。

**Q64.2:** 事务性 Producer——transactional.id。事务性 Producer 怎么实现？开启事务 → 发送消息 → commit 或 abort。

**Q64.3:** 适用场景——什么场景需要 Exactly-Once？性能损耗有多大？你们用过吗？

### 4.4 Elasticsearch（基础版）

**Q65:** 倒排索引原理？分片和副本怎么协调？

**Q66:** ES 写数据时副本和主分片一致性怎么保证？

**Q67:** 你们用 ES 做什么场景？为什么不用 MySQL 全文索引？

**Q68:** ES 的 Query 和 Filter 区别？哪些操作用 filter 会更快？

**Q69:** ES 集群扩容怎么操作？rebalance 过程对线上影响？

### 4.4 Elasticsearch（深入追问版）

#### 倒排索引追问

**Q65.1:** 索引结构——词典（Dictionary）+ 倒排列表（Posting List）。TF（词频）/ IDF（逆文档频率）/ BM25（对 TF/IDF 的改进）。

**Q65.2:** 分片分配策略——平衡算法 / 热点权重 / 强制平衡规则。节点宕机时分片怎么重新分配？副本怎么提升为主分片？

#### 写入一致性追问

**Q66.1:** 写入流程——写入主分片成功后，异步复制到副本。wait_for_active_shards 参数的作用？

**Q66.2:** 副本写入失败——主分片写入成功，副本写入失败。怎么处理？如果副本长期不可用会阻塞写入吗？

**Q66.3:** 段合并——Segment 是什么？为什么 ES 定期合并段？合并过程中对查询有什么影响？

#### Query vs Filter 追问

**Q68.1:** 区别——Query（相关性计算，会评分，结果缓存）/ Filter（二元判断，不评分，bitset 缓存）。Filter 会用 bitset 缓存匹配结果。

**Q68.2:** 性能差异——Filter 不评分所以更快？哪些场景用 Filter 会明显更快？需要排序或相关性计算的用 Query？

---

## 五、真实性核查

**Q70:** "独立完成需求分析、接口设计、编码实现与单元测试"——真的是独立？团队成员？你角色是 Senior 还是 Junior？

**Q71:** "参与企业 AI Agent 平台技术探索"——参与和主导的区别？你具体贡献什么？

**Q72:** 所有技术栈敢不敢当场手写 Hello World 或回答最基础问题？

---

*问题版本：v1.2 | 生成日期：2026-04-07*
