# PROPOSAL: BASE 回流 03 — 管线接管（Project 层挂入七段调度）

> 类型: scripts-reflow（管线组件接线）
> 提案编号: BASE-REFLOW-20260913-03
> 状态: **人工门禁已批准**（2026-09-13，用户选择"批准接线并验收"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 审批记录

- 草案: tasks/project-layer-p3-20260912/task-evolve/base-reflow/DRAFT-project_{selfcheck,site_gen}.py
- 规则层预审: reject（写 BASE 被禁止，risk=high）→ 升级人工（边界正常生效）
- 人工门禁: 批准接线并验收
- 落盘: BASE/scripts/project_selfcheck.py、BASE/scripts/project_site_gen.py、
  BASE/scripts/dispatch_wrapper.bat（GBK+CRLF 字节安全补丁，78 行）

## 端到端验收证据（2026-09-13 11:53 手动完整调度）

- dispatch.log: `[5a/7] project-selfcheck rc=0`、`[5b/7] project-site-gen rc=0`
- summary 行: `... observe=0 selfcheck=0 sitegen=0 advice=0 ...`（新字段生效）
- post-health: HEALTHY（WARN 仅"1 tracked modifications"= 本提案修改的 bat，体检如实报出）
- project-selfcheck.log 首行: scripts=43（41+2 新组件）基线，healthy=True
- P3 memory/selfchecks.jsonl 新增管线记录（drift: added=43 基线）
- P2 站点由 BASE 组件刷新至 iteration 9，truth.json 8 项声称全溯源
- 已修: 自检日志行"无"→"none"（避免 GBK 显示工具乱码）

## 意义

这是"用系统演化系统"的完整句：调度管线（每 4 小时）现在自动执行
Project 层体检与展示站刷新——体检器上线后第一次运行就把两个新组件记入快照，
下一次起任何脚本漂移都会被自动发现。会话从此只做提案与人工门禁。

## 回滚

删除两个新脚本 + `git checkout -- BASE/scripts/dispatch_wrapper.bat`。

## 未做（standing 规则）

未 commit / 未 tag / 未 push；git 状态含本提案的 1 tracked 修改 + 2 新文件，
待发布 SOP 授权后统一处理。
