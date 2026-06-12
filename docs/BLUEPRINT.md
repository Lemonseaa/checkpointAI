# Loop Harness Blueprint

**External Workflow Evidence Harness**

## One Line

Loop Harness 是外部工作流的证据与可视化诊断 Harness。

它不负责替代外部工作流，不做通用 Agent 平台，不做拖拽工作流引擎。它接入外部 Agent / 自动化 / 业务流程，把每次运行和改动变成可观察、可视化、可比较、可验证、可审批、可回滚的证据。

---

## Current Position

```text
Dify / Nexent / Archon / LangGraph / TradingAgents = 执行工作流
Loop Harness = 看清工作流 + 判断工作流改动有没有变好
```

Loop Harness 的核心不是“让 AI 干活”，而是：

```text
证明一次改动是否值得保留。
```

---

## Core Question

每次外部工作流发生改动时，Loop Harness 必须回答：

```text
1. 改了什么？
2. 为什么改？
3. 改之前的 baseline 是什么？
4. 改之后的 candidate 表现如何？
5. 指标有没有变好？
6. 风险有没有变大？
7. 证据是否足够？
8. 是否符合人的方法论和边界？
9. 该 approve、reject、继续 shadow，还是 rollback？
```

如果回答不了，就不能进入自动优化。

---

## New Architecture

```mermaid
flowchart LR
    A["External Workflow"] --> B["Evidence Adapter"]
    B --> C["Workflow Contract"]
    C --> D["Workflow Visualization"]
    C --> E["Trace + Metrics"]
    E --> F["Baseline Compare"]
    F --> G["Evidence Review"]
    G --> H["Report"]
    H --> I["Human Decision / Rollback"]
```

---

## What We Stop Building

以下方向冻结，不再作为主线继续补完：

```text
Generic Agent Runtime
Workflow Engine
Message Bus / Registry / Scheduler platform
Drag-and-drop Workflow Builder
Plugin Marketplace
Full LLM Provider Platform
HA / Kubernetes enterprise platform
TradingAgents clone
Dify / Nexent clone
Auto live trading / auto publishing
```

这些不是立即全部删除，而是标记为 legacy / frozen。等新的 Evidence Adapter 跑通真实数据后，再按引用关系清理。

---

## What We Keep

保留这些核心能力：

| Module | Purpose |
|---|---|
| Evidence Adapter | 接入外部 workflow run JSON |
| Workflow Contract | 标准化 nodes / edges / trace / metrics / config / artifacts |
| Workflow Visualization | 诊断图：节点、路径、黑盒、覆盖率、成本、延迟、错误 |
| Experiment Ledger | 记录假设、baseline、改动、结果、结论 |
| Metric Schema | 指标方向、类别、权重、阈值 |
| Baseline Compare | 判断 candidate 是否真的更好 |
| Shadow / Replay | 候选改动不直接污染线上 |
| Decision Log | 记录 approve / reject / rollback 原因 |
| Policy / Risk Gate | 控制自动、审批、阻断 |
| Approval Inbox | 人类集中处理关键决策 |
| Backup / Rollback | 支持恢复 |
| Reports | 把证据变成人能读懂的报告 |
| Methodology Profile | 人的方法论、审美、风险偏好参与判断 |

---

## Immediate Plan

当前唯一主线：

```text
External Workflow Evidence Adapter + Workflow Visualization
```

第一版只做：

```text
ingest external run JSON
normalize workflow contract
build workflow visualization data
mark black-box nodes
calculate trace / metric coverage
store trace and metrics
compare baseline vs candidate
generate evidence report
produce approve / reject recommendation
```

不做：

```text
更多平台功能
更多 UI 页面
更多 agent 协作模式
更多 provider 支持
```

详细计划见：

```text
docs/STRATEGIC_RESET_PLAN.md
```

---

## Current Implemented Evidence Chain

当前代码已经跑通：

```text
external run ingest
single run detail API
workflow visualization UI
node evidence inspector
evidence quality gate
pinned workflow baseline
baseline vs candidate comparison
metric delta visualization
evidence comparison -> approval proposal
repeatable quant-shaped evidence drill
```

仍然不能宣称：

```text
真实交易 alpha
自动实盘部署
真实账号增长
长期自主学习已被证明
```

---

## First Real Drill

优先接量化回测数据。

原因：

```text
1. 有历史数据
2. 有 baseline
3. 有明确指标
4. 可以 replay
5. 反馈比内容场景快
```

第一轮验收：

```text
1. 至少 30 次 historical / semi-real backtest run
2. 至少 5 个 candidate vs baseline comparison
3. 至少 3 份 evidence report
4. 至少 1 次 approve / reject decision
5. 能在图上看见 workflow 节点、运行路径、黑盒节点和指标覆盖
6. 发现并记录至少 3 个系统问题或指标盲区
```

---

## Document Map

| Document | Role |
|---|---|
| `docs/README.md` | 文档结构入口 |
| `docs/BLUEPRINT.md` | 当前方向总纲 |
| `docs/STRATEGIC_RESET_PLAN.md` | 新执行计划 |
| `docs/core_innovation/` | Loop Harness 自己必须掌握的核心创新 |
| `docs/core_innovation/metrics_reference.md` | 指标参考 |
| `docs/core_innovation/user_preference.md` | 人类偏好 / Hermes 草稿机制 |
| `docs/borrowed_wheels/` | 外部参考项目、替代轮子、接入检查 |
| `docs/borrowed_wheels/legacy_replacement_matrix.md` | 旧模块替换/重写/保留/隔离矩阵 |
| `docs/borrowed_wheels/reference_projects.md` | 外部参考项目：哪些借鉴、哪些替代、哪些不做 |
| `docs/borrowed_wheels/adapter_checklist.md` | Adapter 接入评估清单 |
| `docs/business_lines/` | 量化、自媒体、demo 等业务落地层 |
| `docs/deployment/` | 部署与运维资料 |
| `docs/archive/` | 历史架构和研究材料，只作审计背景 |

历史报告和验收文档只作为审计记录，不作为下一阶段路线图。
