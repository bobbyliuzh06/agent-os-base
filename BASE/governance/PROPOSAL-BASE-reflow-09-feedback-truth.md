# PROPOSAL: BASE 回流 09 — 真实世界反馈真值接入（6e）

> 类型: scripts-reflow（管线组件接线）
> 提案编号: BASE-REFLOW-20260913-09
> 状态: **人工门禁已批准**（2026-09-13，"批准三项"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 审批记录

- 草案 DRY 实测：feedback truth（issues=0 status=available）；站点（claims=10, iteration 18）
- 人工门禁: 批准三项
- 落盘: BASE/scripts/project_feedback_truth.py + project_site_gen.py（真实反馈节）+
  dispatch_wrapper.bat 接入 6e（GBK+CRLF，108 行）

## 端到端验收证据（2026-09-13 13:29 手动完整调度）

- summary 行: `... pool=0 feedback=0 advice=0 ...`（6e rc=0）
- 回归集 10/10（I-6=10 claims）
- P-8#35 progress(feedback-truth-wired)：真实数据入账 open_issues=0、v0.5.0 下载=2
- 站点"真实反馈（世界在怎么回应）"节上线（发布快照已随 45e2f1a 推送，Pages 自动重部署）
- 自观测：selfcheck=1 报出 6e 接线漂移（下轮自愈）

## 意义

- 案例② 评估域 showcase-feedback 的"反馈接收数"指标有了**真实数据源**（GitHub API 只读轮询，
  1h 节流，失败如实 degraded）——真值先于自动化第一次由外部世界数据驱动；
- 管线 12→13 阶段；访问量（Pages 流量）仍无公开 API，如实降级标注（P-8 保持 open 至该部分解决）。

## 回滚

删除 project_feedback_truth.py + git 恢复 project_site_gen.py / dispatch_wrapper.bat。

## 未做

站点发布快照刷新机制（每 4h 站点在 tasks/ 内更新，但 site/ 发布快照需人工提交）——
已记入 P-8 action 候选：由 6e 轮询检测到数据变化时触发 site/ 自动提交。
