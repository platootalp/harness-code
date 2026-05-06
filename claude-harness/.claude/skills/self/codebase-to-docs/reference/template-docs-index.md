# Docs Index Template

目标文件：`docs/index.md`

````markdown
# 文档导航

## 摘要
- 用 1 句话说明系统解决什么问题。
- 用 1 句话说明这套文档如何组织，以及建议从哪里开始读。

## 你将了解
- 哪些页面属于架构解析主轴。
- 哪些页面属于工作流解析主轴。
- 新人、维护者、排障人员分别应从哪里开始阅读。

## 范围
- 范围内：当前仓库已实现的核心系统、关键流程、配置面、风险说明。
- 范围外：历史系统、外部团队维护的系统、未接入或待验证能力。

## 阅读地图
### 建议阅读路径
1. 先读 `overview/architecture-at-a-glance.md`
2. 再读 `overview/workflow-map.md`
3. 按需深入：
   - 架构问题：看 `architecture/`
   - 业务流程问题：看 `workflows/`
   - 查配置/API事实：看 `reference/`
   - 查证据：看 `appendix/evidence-index.md`

## 页面树
```text
docs/
├── index.md
├── overview/
├── architecture/
├── workflows/
├── modules/
├── reference/
└── appendix/
```

## 主轴说明
### 架构解析主轴
- 回答“系统由什么组成、请求如何流动、为什么这样设计”。

### 工作流解析主轴
- 回答“事情如何一步步发生、失败后如何处理、怎么排障和回滚”。

## 读者指引
### 新接手工程师
- 优先看：总览、请求生命周期、核心工作流。

### 长期维护者
- 优先看：失败模型、设计决策、风险与技术债。

### 线上排障人员
- 优先看：异常与恢复、排障手册、配置面。

## 相关页面
- `overview/architecture-at-a-glance.md`
- `overview/workflow-map.md`
- `appendix/evidence-index.md`
````
