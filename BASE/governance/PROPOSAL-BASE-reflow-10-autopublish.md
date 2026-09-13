# PROPOSAL: BASE 回流 10 — 站点发布快照自动化（6f）+ 反馈参与信号 v2

> 类型: scripts-reflow（管线组件接线与升级；治理边界变更：自动 push 开启）
> 提案编号: BASE-REFLOW-20260913-10
> 状态: **人工门禁已批准**（2026-09-13，"批准自动发布"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 审批记录

- 草案 DRY 实测：publish（快照已最新→正确跳过）；feedback v2（issues=0 stars=0 watchers=0 forks=0 available）
- 人工门禁: 批准自动发布（用户明确选择"批准自动发布（推荐）"）
- 落盘: BASE/scripts/project_site_publish.py + project_feedback_truth.py v2 +
  dispatch_wrapper.bat 接入 6f（GBK+CRLF，113 行）

## 端到端验收证据（2026-09-13 13:50 手动完整调度）

- summary 行: `... feedback=0 sitepub=0 advice=0 ...`（6f rc=0，快照已最新→skip）
- 回归集 10/10（I-5=11 rows）
- git 身份确认：AgentOS Harness <agent-os@localhost>（自动提交可用）
- 自观测：selfcheck=1 报出 6f 接线漂移（下轮自愈）

## 治理边界（自动 push 的严格约束，已写入组件）

1. 只允许提交 `site/index.html` 与 `site/truth.json` 两个路径（git add 显式路径）；
2. 工作区存在其他 staged/unstaged 变更 → 拒绝并 rc=1（绝不混入未授权内容）；
3. 仅 main 分支；commit 前缀 [auto-site]；push 失败如实 rc=1，不中断调度；
4. 首次差异触发前，管线不会产生任何自动提交（快照当前已同步）。

## 意义

- "交付后持续维护"的最后一环机械化：站点内容由管线生成，发布快照由管线推送——
  展示站从此在无人工干预下保持与底座真值同步；
- 反馈真值从 2 维（Issues/下载）扩到 5 维（+stars/watchers/forks）；
- 管线 13→14 阶段。剩余诚实缺口：Pages 流量无公开 API（P-8 保持 open）。

## 回滚

删除 project_site_publish.py + git 恢复 project_feedback_truth.py / dispatch_wrapper.bat；
已产生的 [auto-site] 提交可 git revert。
