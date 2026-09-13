# PROPOSAL: BASE 回流 18 — 第九轮反馈响应（目标门槛 + 自然语言入口 + 地面第一块砖）

> 类型: product-reflow
> 提案编号: BASE-REFLOW-20260913-18
> 状态: **人工门禁已批准**（2026-09-13，"批准全部"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## distillation_check（I-10 固定问句）

**本轮是否有新轨迹可蒸馏？答案：有轨迹，暂不蒸馏（记录）。** 轨迹 = "门槛用错
（agent 系统以'会不会写代码'划分用户）+ 伪交互中间态 + 机制过剩价值未兑现"。
前两项属下游表达问题（已由 downstream-view-gap 家族覆盖），第三项属产品节奏问题，
需等真实采用数据再蒸馏。连续 3 轮蒸馏后保持"有轨迹不蒸馏"的纪律本身即记录。

## 变更清单

1. **cmd_talk.py**（agent-os talk）：自然语言 → charter 入口——LLM 起草 + 规则层
   门禁 + 规则模板兜底（LLM 失败时）；实测走通（本轮 LLM 走兜底路径，charter 生成 +
   门禁 accept + 决策留痕）；agent-os.cmd 增加 talk 子命令（双入口同命令集）；
2. **站点**：删伪交互（输入框/按钮全移除，改静态过程示意，明标"不可操作"）；
   hero 门槛句改为目标导向（"门槛是'有没有目标'，不是'会不会写代码'"）；
   新增第九轮诚实声明（机制过剩、价值未兑现、真实用户=1/star=0/downloads=2）；
3. **地面第一块砖**：真实目标经 talk 注册——"帮我长期盯住这个仓库别断更，站点别挂"
   （tasks/talk-goal-20260913T114221Z），第一周期真实真值全 PASS
   （repo-synced ✓ site-alive ✓ dispatch-recent 0.6h ✓），truth/decisions 留痕。

## 台账

P-20#? progress：门槛/伪交互/自然语言入口/诚实声明四项落地；保持 open 至
真实采用数据出现（talk 被真实使用或 star/下载变化）。

## 回滚

git revert 本轮提交。
