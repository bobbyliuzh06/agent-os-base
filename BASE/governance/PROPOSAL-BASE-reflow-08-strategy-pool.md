# PROPOSAL: BASE 回流 08 — 事件驱动策略池接入 6d + P-6/P-7 裁决关闭

> 类型: scripts-reflow（管线组件接线）
> 提案编号: BASE-REFLOW-20260913-08
> 状态: **人工门禁已批准**（2026-09-13，"批准接线" + "接受追加修正，关闭"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 审批记录

- 草案 DRY 实测：首跑重赛（champion=S-2 valid_excess=+0.1763）→ 二跑诚实跳过（数据哈希未变）
- 人工门禁: 批准接线；P-6/P-7 采纳"追加修正为终局"关闭
- 落盘: BASE/scripts/project_strategy_pool.py + dispatch_wrapper.bat 接入 6d（GBK+CRLF，103 行）

## 端到端验收证据（2026-09-13 12:11 手动完整调度）

- summary 行: `... painrollup=0 pool=0 advice=0 ...`（6d rc=0）
- strategy-pool.log: `champion=S-2 valid_excess=0.1763`（生产首跑；此后数据未变将诚实跳过）
- pool-state.json: 数据哈希+上次运行+冠军（事件驱动节流状态）
- P-6#31/P-7#32 resolved(human-verdict)：append-only 账本下"追加修正为终局"裁定落账
- 回归集 10/10 绿（I-5 ledger-row-unique=9；I-2 三台账前 10 行哈希未变——历史未被触碰的机器证明）
- 自观测：selfcheck=1 报出 6d 接线漂移（下轮自愈）

## 意义

1. 策略池成为事件驱动管线任务：**新数据到达→自动重赛**；固定数据→诚实跳过，零空转。
   这同时回答了一个诚实问题：合成数据固定后，周期性重赛没有信息量——机制以"跳过"表达这一点；
2. 管线 11→12 阶段；append-only 的"历史不可改"由回归集 I-2 持续机器证明。

## 回滚

删除 project_strategy_pool.py + git 恢复 dispatch_wrapper.bat。

## 未做（standing 规则）

未 commit/tag/push；8 次回流累积变更待发布 SOP 授权统一处理。
