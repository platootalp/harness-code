# Evidence Index Template

目标文件：`docs/appendix/evidence-index.md`

````markdown
# 证据索引

## 摘要
- 这一页集中收纳关键结论的源码回溯点。
- 这不是正文主体，而是正文结论的核验入口。

## 你将了解
- 每个关键结论对应哪些文件、符号、配置键和测试。
- 哪些结论置信度高，哪些仍然是待验证假设。

## 范围
- 范围内：正文已经提出的关键结论及其证据。
- 范围外：正文没有出现的零散路径清单。

## 使用方式
- 先读正文，再回到这一页核验结论。
- 不要把这一页当成系统说明书。

## 证据总表（必填）
| 结论 | 证据路径 | 符号 / 配置键 | 类型 | 置信度(H/M/L) | 说明 |
|------|----------|---------------|------|---------------|------|
| 请求入口位于 API 层 | `src/api/order.py` | `create_order` | 代码 | H | 主请求入口 |
| 重试上限来自默认配置 | `config/default.yaml` | `retry.max_attempts` | 配置 | H | 重试上限来源 |

## 测试映射
| 结论 | 测试资产 | 说明 |
|------|----------|------|
| 异常流会映射到业务错误码 | `tests/api/test_errors.py` | 覆盖异常映射 |

## 待验证假设
- 将没有直接证据、但在正文中必须使用的推断显式列出。
- 每条假设写明为什么尚未确认，以及如何后续验证。

## 相关页面
- `index.md`
- `architecture/request-lifecycle.md`
- `architecture/failure-model.md`
- `workflows/workflow-<name>-deep-dive.md`
````
