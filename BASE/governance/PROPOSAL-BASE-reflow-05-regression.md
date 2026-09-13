# PROPOSAL: BASE 回流 05 — 过程回归集挂入 7a 阶段

> 类型: scripts-reflow（管线组件接线）
> 提案编号: BASE-REFLOW-20260913-05
> 状态: **人工门禁已批准**（2026-09-13，"批准接线并验收"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 审批记录

- 草案: tasks/project-layer-p3-20260912/task-evolve/base-reflow/DRAFT-project_regression.py
- 任务层原型: p5_regression.py 首跑 10/10 全绿，黄金基线记录于 P3 memory/regression-golden.json
- DRY 实测: 10/10（BASE 组件草稿）
- 人工门禁: 批准接线并验收
- 落盘: BASE/scripts/project_regression.py + dispatch_wrapper.bat 接入 7a（GBK+CRLF，93 行）

## 端到端验收证据（2026-09-13 12:03 手动完整调度）

- dispatch.log: `[7a/7] project-regression rc=0`，管线内 10/10 不变量 PASS：
  I-1 门禁确定性 / I-8 BASE 写入永拒 / I-2 三文件 append-only / I-3 痛点闭合证据 /
  I-4 章程评估域 / I-5 台账行唯一 / I-6 站点真值溯源 / I-7 站点迭代 append-only
- summary 行: `... posthealth=0 regression=0 dashboard=0`
- 自观测事件（预期）：selfcheck=1 —— 体检器再次如实报出 7a 接线对 bat 的漂移，下轮基线更新后自愈

## 意义

DIRECTION-v0.1 五项优先级至此全部落地：
1. 冻结案例层（样本外验证后冻结）
2. 管线接管（5a/5b 体检+站点）
3. 独立性补强（6a/6b 验证器+复核人）
4. 发布通道（未做，等 github.enabled）
5. 过程回归集（7a，本次）

现在每 4 小时调度自动完成：体检自己 → 刷新展示站 → 验证痛点证据 → 独立复核 → 回归防退化。
会话职责收敛为提案与人工门禁——"用系统演化系统"的运行态闭环完成。

## 回滚

删除脚本 + `git checkout -- BASE/scripts/dispatch_wrapper.bat`。

## 未做（standing 规则）

未 commit/tag/push；5 次回流累积变更待发布 SOP 授权统一处理。
