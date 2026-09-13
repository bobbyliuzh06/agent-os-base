# PROPOSAL: BASE 回流 07 — 全局痛点汇总 + 站点渲染 + model 级独立复核

> 类型: scripts-reflow（管线组件接线与升级）
> 提案编号: BASE-REFLOW-20260913-07
> 状态: **人工门禁已批准**（2026-09-13，"批准三项变更"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 审批记录

- 三项变更：①新增 BASE/scripts/project_pain_rollup.py 接入 6c；
  ②project_site_gen.py 新增"全局痛点"节（claims 8→9）；
  ③project_dual_review.py 复核模型 deepseek-v4-flash → deepseek-v4-pro（model 级独立）。
- 草案预验：rollup DRY（7 pains/gaps=0）；站点草案运行（gate=accept, claims=9, iteration 13）；
  pro 模型复核提示词单独验证可用。
- 人工门禁: 批准三项变更。
- 落盘: 3 个 BASE 脚本 + dispatch_wrapper.bat 接入 6c（GBK+CRLF，98 行）。

## 端到端验收证据（2026-09-13 12:09 手动完整调度）

- summary 行: `... preview=0 painrollup=0 advice=0 ...`（6c rc=0）
- pain-rollup.log: `projects=1 pains=7 open=3 resolved=4 gaps=0`
- pain-rollup.json 由管线更新（rolled_at=04:09:01Z）
- 站点"全局痛点（跨项目）"节渲染成功（P-2 居首，score=6）
- 回归集 10/10 绿（I-6 更新为 9 claims）
- 自观测：selfcheck=1 如实报出本提案对 bat+脚本的漂移（下轮基线自愈）

## 意义

1. 跨项目全局痛点视图落地（开放问题 2 registry 方向第一步）：底座在治什么一表可见，
   站点向潜在用户实时展示"系统正在处理什么"——机制自证的一部分；
2. 复核人与提议者模型级隔离：proposer=flash，reviewer=pro；
3. 管线 10→11 阶段（新增 6c）。

## 回滚

删除 project_pain_rollup.py + git 恢复 project_site_gen.py / project_dual_review.py / dispatch_wrapper.bat。

## 未做（standing 规则）

未 commit/tag/push；7 次回流累积变更待发布 SOP 授权统一处理。
