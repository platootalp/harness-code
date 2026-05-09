# 方案评审报告（二次评审）

## 元信息

| 字段 | 填写 |
| --- | --- |
| 被评文档 | docs/superpowers/plans/2026-05-08-self-evolution-v4.md |
| 被评版本 / 提交 | 未钉版本（首次评审后修复版，2891 行） |
| 评审日期 | 2026-05-08 |
| 评审者 | 主编排者（合并 C/X/S 三子代理二次评审） |
| 本报告归档路径 | docs/reviews/2026-05-08-self-evolution-v4-dev-plan-review-r2.md |
| 前次评审 | docs/reviews/2026-05-08-self-evolution-v4-dev-plan-review.md |

---

## 被评方案摘要

| 项 | 填写 |
| --- | --- |
| **要解决的核心问题** | 实现 self-evolution 插件 v4：用 AgentHook 在会话 Stop 时自动审查对话、通过 evolve-skill-writer 元技能生成 SKILL.md 文件 |
| **非目标 / 明确不做** | YAML 硬验证、description 优化器、交互式技能开发、事实记忆/情景记忆 |
| **交付形态** | Claude-Code 插件（四通道）+ 测试脚本 + 文档 |
| **关键外部依赖** | Claude-Code v1.x plugin marketplace、jq（必需）、bash >= 4.x |
| **安全风险档位** | 中 — 前次严重/高问题已修复，残余风险为已知 trade-off |

---

## 前次修复验证摘要

| 前次 ID | 级别 | 状态 | 验证结论 |
| --- | --- | --- | --- |
| F1 | 严重 | fixed | security-scan.sh 增加 base64 解码扫描；元技能 Quality Checklist 加"嵌套 PI 检查"。**有残余风险**（base64 正则误匹配长标识符、解码无 token 上限）→ 本轮 S-F1/S-F2 |
| F2 | 高 | fixed | hooks.json + reviewer prompt 增加 SECOND.5 STEP 决策理由强制。**残余**：reviewer 决策事件未写入日志 → 本轮 S-F4 |
| F3 | 高 | documented | README "Known false-positives" 段记录误拦截及 workaround |
| F4 | 高 | documented | 同 F3 |
| F5 | 高 | fixed | 元技能 Quality Checklist 显式列出 8 个 category 白名单 + ABORT 出口。**残余**：security-scan.sh 路径通配符 `*/SKILL.md` 不校验 category → 本轮 S-F3 |
| F6 | 高 | fixed | posix-lock.sh 增加超时日志。**残余**：无重试/恢复机制 → 本轮 S-F5 |
| F7 | 高 | fixed | lib/log.sh + scan_block/lock_timeout/reset_state 事件 + README 监控段。**残余**：reviewer 决策和 hook 执行时长未覆盖 → 本轮 S-F4 |
| F8 | 高 | fixed | Task 0 Step 1 改用 `$REPO_ROOT` |
| F9 | 高 | fixed | Task 1 Step 3 新增 parse_day1_result.sh 标准化 JSON verdict |
| F10 | 高 | fixed | Task 0.5 preflight.sh E1-E7 自动化。**但** preflight 自身依赖 bash 4+ → 本轮 X-F2 |
| F11 | 高 | clarified | 原评审误判，已改写为数组遍历更健壮 |
| F12 | 高 | fixed | verdict 表三态 + fallback 分支明确 |
| F13 | 高 | clarified | 原评审误判，hook input schema 已显式声明 |
| F14-F30 | 中/低 | fixed/documented | 全部已修复或文档化 |

**结论：** 前次 1 严重 + 12 高级别问题中，3 项为评审误判（已澄清），其余全部已修复或文档化。修复引入的残余风险和新增问题见下方发现项。

---

## 发现项

| ID | 级别 | 位置 | 现象 | 触发条件 | 影响 | 建议 | 维度 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F31 | 高 | README Security model + security-scan.sh | README 声称 `DISABLE_SELF_EVOLUTION_PREHOOK=1` 可绕过 PreToolUse hook，但 security-scan.sh 未检查此环境变量 | 用户设置该变量后 | 绕过不生效，文档与代码不一致；用户可能误以为已禁用扫描 | 在 security-scan.sh 开头加 `if [ "${DISABLE_SELF_EVOLUTION_PREHOOK:-0}" = "1" ]; then exit 0; fi`，或删除 README 中的该声明 | 安全性 |
| F32 | 高 | Task 0.5 preflight.sh | preflight.sh 使用 `declare -a` / `+=`（bash 4+ 语法），但 E2 检查的就是 bash 版本，构成自举悖论 | macOS 默认 bash 3.2 | preflight.sh 本身无法在需要检测的环境中运行 | preflight.sh 改用 POSIX 兼容语法（用空格分隔字符串代替数组，用 `while read` 代替 `mapfile`）；或改用 `#!/usr/bin/env bash` 并在脚本开头加 bash 版本检测（纯 POSIX） | 可执行性 |
| F33 | 高 | Task 4 security-scan.sh base64 解码段 | base64 token 提取正则 `[A-Za-z0-9+/]{20,}={0,2}` 会匹配 SHA-1 哈希（40 hex chars）、UUID、长 base64-like 标识符 | 合法 SKILL.md 包含 git commit hash 或 UUID | 垃圾解码内容可能误触发 PI 模式，导致合法内容被拦截 | 在 grep 前加 `--max-count=50` 限制 token 数量；或对解码后的内容做"可打印字符比例 > 80%"预检，丢弃纯二进制解码 | 安全性 |
| F34 | 高 | Task 4 security-scan.sh base64 解码段 | 解码 while 循环无 token 上限，大量长标识符（如 minified JS）可能导致超 10s timeout | SKILL.md 包含大量 base64-like 内容 | security-scan.sh 超时被 hook engine 杀死，Write 请求被默认放行或阻塞 | 在循环外加 `TOKEN_COUNT=0; MAX_TOKENS=50`，每处理一个 token 递增，超限 break；或对整个解码段加 `timeout 5` 包装 | 安全性 |
| F35 | 中 | File Structure vs Tasks | File Structure 列出 `tests/fixtures/redteam/outside-skills.txt` 但无 Task 创建；遗漏 `tests/parse_day1_result.sh` | 实施者按 File Structure 清单核对 | 清单不完整，可能遗漏文件或创建空文件 | 从 File Structure 删除 `outside-skills.txt`，补入 `parse_day1_result.sh` | 一致性 |
| F36 | 中 | Task 4 security-scan.sh 路径白名单 | `~/.claude/skills/*/SKILL.md` 的 `*` 不校验 category 前缀，恶意 agent 可直接 Write 非 白名单 category 的 skill | 恶意 agent 绕过元技能，直接调用 Write | 生成 `~/.claude/skills/evil-backdoor/SKILL.md`，绕过 category 白名单 | 元技能 Quality Checklist 已是首层防御；建议在 security-scan.sh 路径匹配后追加 category 前缀校验（`case "${TARGET##*/skills/}" in debug-*|refactor-*|...`），或列为 v5 纵深防御 | 安全性 |
| F37 | 中 | Task 5 hooks.json + Task 2 lib/log.sh | reviewer 决策（CREATE/UPDATE/SKIP + rationale）和 hook 执行时长未写入 JSONL 日志 | 运行后审计 | 无法从日志中统计 reviewer 决策质量、触发频率、超时趋势 | 在 hooks.json Stop[1] prompt FIFTH STEP 增加"日志记录"指令：reviewer 在 StructuredOutput 前调用 Bash 写一行 JSONL；或在 Stop[2] cleanup 脚本中追加决策记录 | 可验证性 |
| F38 | 中 | Task 4 security-scan.sh + Task 12 | F16-A 并发测试仅检查 "JSON 不破损 + count < threshold"，但未检查 count 精确值 | 并发写入导致部分事件丢失 | 计数丢失但测试通过，隐蔽数据丢失 | 改用"最终 count ≥ 10 且 JSON 合法"的弱断言（承认并发下的 count 可能不完全精确），或用 `flock` 替代 `mkdir` 锁提高原子性 | 可验证性 |
| F39 | 中 | Task 17 verify_quality_checklist.sh | 脚本不包含 base64 解码扫描，与 security-scan.sh 的检测能力不一致 | 生成的 SKILL.md 通过了 Checklist 验证但含编码后的 PI | 独立验证给出 false positive | 在 verify_quality_checklist.sh 中增加"base64 解码扫描"段（与 security-scan.sh 同逻辑），或标注本脚本是"Quick Check"而非"Full Scan" | 可验证性 |
| F40 | 中 | Task 12 F16-A 并发测试 | LLM 红队 R1-R4 未覆盖"恶意 UPDATE"攻击向量（利用已有 skill 的 UPDATE 路径注入恶意内容） | 恶意用户诱导 reviewer UPDATE 已有 skill | 已有 skill 被污染，后续会话自动加载 | 在 Task 16 Step 4 增加 R5：诱导 UPDATE 一个已有 skill，注入 PI 内容，期望 `SKIPPED: hard_gate_blocked: prompt-injection pattern` | 安全性 |
| F41 | 中 | Task 4 / Task 8 / Task 12 性能测试 | `date +%s%N` 是 GNU 扩展，macOS 默认 `date` 不支持 `%N` | macOS 上运行测试 | 性能测试崩溃（非跳过），影响 CI | 改用 `python3 -c 'import time; print(int(time.time()*1e9))'` 或 `gdate`（需 brew），或用 `time` 命令包装 | 可执行性 |
| F42 | 低 | Task 5 hooks.json prompt | prompt 内使用 `$ARGUMENTS` 和 `${session_id}`，但未说明 hook engine 对 prompt 字段的变量替换机制 | hook engine 不做替换 | reviewer 收到字面字符串，无法定位 transcript | 在 Prerequisites 段说明 prompt 变量替换机制，或改 prompt 指令为"Read the trigger flag file to get transcript_path" | 正确性 |
| F43 | 低 | Task 17 verify_quality_checklist.sh | 检查 frontmatter 的 name/description/paths/version 但遗漏 `when_to_use` 和 `allowed-tools` | 生成的 SKILL.md 缺少这两个字段 | 不规范 SKILL.md 通过验证 | 补充 `when_to_use` 和 `allowed-tools` 存在性检查 | 完整性 |
| F44 | 低 | Task 3 stop-gate.sh | 对 `session_id` 做非空校验但 `transcript_path` 无校验 | hook payload 缺少 transcript_path | trigger flag 的 transcript_path 为空，下游 reviewer 读取失败 | 在 `SESSION_ID` 校验后追加 `[ -n "$TRANSCRIPT_PATH" ] || exit 0` | 正确性 |
| F45 | 低 | lib/log.sh | JSONL 日志无轮转策略 | 长期运行 | 日志文件无限膨胀 | v5 加轮转；当前 README 监控段可加 `jq` 过滤最近 7 天的提示 | 可运维性 |
| F46 | 低 | Task 14 run_all.sh | Task 17 Step 4 的"集成到 run_all.sh"指令可能与 Task 14 已有代码重复添加 verify_quality_checklist.sh 自检 | 合并时 | run_all.sh 中出现两段自检代码 | Task 17 Step 4 改为"确认 run_all.sh 已包含"而非"追加" | 一致性 |

### 七维索引

| 维度 | 相关 F 编号 |
| --- | --- |
| 一致性 | F35, F46 |
| 正确性 | F42, F44 |
| 完整性 | F43 |
| 可执行性 | F32, F41 |
| 安全性 | F31, F33, F34, F36, F40 |
| 可验证性 | F37, F38, F39 |
| 可运维性 | F45 |

---

## 开放问题

| ID | 问题 | 是否阻塞结论 | 建议决策方 |
| --- | --- | --- | --- |
| Q1 | Claude-Code hook engine 对 `type:agent` 的 `prompt` 字段是否支持 `$ARGUMENTS` / `${session_id}` 变量替换？ | 否 | 方案作者 + Claude-Code 文档 |
| Q2 | security-scan.sh 是否需要校验 category 前缀白名单（纵深防御）？还是只依赖元技能 Quality Checklist？ | 否（当前可仅依赖元技能，v5 加纵深） | 方案作者 |
| Q3 | base64 解码扫描的 token 上限和误报风险是否可接受？ | 否（需明确 token 上限） | 方案作者 |

---

## 总体结论

### 决策摘要

| 项 | 填写 |
| --- | --- |
| **结论** | 修补后可实现 |
| **发现项最高级别** | 高 |
| **是否阻塞实现或发布** | 是 — 需先修复 F31-F34 的 4 个高级别问题 |
| **下一步必须先做的 1～3 件事** | 1. 修复 F31：在 security-scan.sh 中实现 `DISABLE_SELF_EVOLUTION_PREHOOK` 检查，或删除 README 声明<br>2. 修复 F32：preflight.sh 改用 POSIX 兼容语法<br>3. 修复 F33/F34：base64 解码段加 token 上限 + 可打印字符预检 |

### 理由

**前次严重问题已修复。** F1（prompt injection 编码绕过）已通过 base64 解码扫描 + 元技能嵌套 PI 检查解决，但引入了新的高级别问题：解码正则可能误匹配长标识符（F33）且无 token 上限可能导致超时（F34）。这两个问题有明确的修复方向（加 token 上限 + 可打印字符预检），不涉及架构变更。

**F31（文档与代码不一致）** 和 **F32（bash 自举悖论）** 是实施前必须修复的阻塞项，但修复工作量小（各约 5 行代码变更）。

**F36（路径白名单不校验 category）** 是有效的安全观察，但元技能 Quality Checklist 已是首层防御，security-scan.sh 的路径白名单主要是防"写到 skills 目录外"而非"校验 category 前缀"。建议列为 v5 纵深防御，不阻塞当前实现。

**双视角一致项：**
- X-F1 与 S-F9 独立发现同一问题（DISABLE_SELF_EVOLUTION_PREHOOK 未实现），合并为 F31，置信度高
- C-F1 与 X-F6 独立发现同一问题（outside-skills.txt 遗漏），合并为 F35

**总体评价：** 方案在首次评审后修复质量高，前次 1 严重 + 12 高级别问题中 3 项为评审误判，其余全部修复到位。二次评审发现的 4 个高级别问题均为修复引入的边界情况或文档不一致，修复工作量小且方向明确。方案架构和核心逻辑无误，可在修复上述 4 项后进入实施。

---

## 评审覆盖

### 阅读与假设

- **已读：**
  - 被评文档全文（2891 行），逐 Task 验证修复
  - 前次评审报告全文（30 项发现项）
  - 新增的 Prerequisites & Path Conventions 段、Task 0.5、Task 12.5、Task 17
  - Review feedback 修复对照表（§4）
- **未读或未验证：**
  - 设计规格 spec 全文（仅引用了章节号）
  - Claude-Code hook engine 变量替换机制（Q1）
  - 所有脚本的实际执行
- **假定：**
  - 假设 spec §5.6 与 Task 8 元技能 SKILL.md 保持同步
  - 假设 Claude-Code hook engine 对 `type:agent` prompt 支持某种形式的变量注入
  - 假设 `mapfile`/`declare -a` 在 bash 4+ 下可用（E2 前置条件）

### 证据与验证

| 类别 | 已有 | 缺口 |
| --- | --- | --- |
| 自动化测试 | Task 2-4 单元测试; Task 10-12 集成测试; Task 14 run_all.sh; Task 17 verify_quality_checklist.sh | F33/F34：base64 解码段无 token 上限和误报的测试用例（需补充）<br>是否阻塞结论：否（修复后补充） |
| 手工验收 / 演练 | Task 1 Day 1; Task 15 真实 SkillTool; Task 16 10+4 场景 | Q1 变量替换机制需在 Day 1 验证时确认<br>是否阻塞结论：否 |
| 监控与日志 | lib/log.sh + scan_block/lock_timeout/reset_state 事件 | reviewer 决策事件和 hook 执行时长缺失（F37）<br>是否阻塞结论：否（v5 补充） |
| 回滚或恢复验证 | reset-state.sh; README Rollback 段 | — |
| 红队 / 滥用面 | Task 4: 5 类 fixture; Task 12: S1-S6 + F16; Task 16: R1-R4 | R5 恶意 UPDATE 攻击向量（F40）<br>是否阻塞结论：否（补充 R5 即可） |

---

## 附录

### 修复优先级建议

| 优先级 | F 编号 | 修复工作量 | 说明 |
| --- | --- | --- | --- |
| P0 | F31 | ~5 行 | 加 env var 检查或删 README 声明 |
| P0 | F32 | ~20 行 | preflight.sh 改 POSIX 兼容 |
| P0 | F33 | ~10 行 | base64 解码加 token 上限 + 可打印预检 |
| P0 | F34 | ~5 行 | base64 解码加 MAX_TOKENS break |
| P1 | F35 | ~5 行 | 修正 File Structure |
| P1 | F36 | ~10 行 | security-scan.sh 加 category 前缀校验（可选） |
| P1 | F37 | ~15 行 | reviewer 决策日志（可选，v5 也可） |
| P1 | F41 | ~10 行 | date 命令跨平台兼容 |
| P2 | F38-F40, F42-F46 | 各 ~5 行 | 测试/文档完善 |

### 子代理原始稿

- **C 角色稿：** 5 项发现（C-F1~C-F5），最高级别中
- **X 角色稿：** 6 项发现（X-F1~X-F6），最高级别高
- **S 角色稿：** 9 项发现（S-F1~S-F9），最高级别高

---

**评审完成日期：** 2026-05-08
**评审方法：** 三子代理并行二次评审 + 主编排者合并
**评审轮次：** 第 2 轮（前次 30 项 → 修复 → 本轮 16 项新发现）
