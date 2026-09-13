# PROPOSAL: BASE 回流 04 — 独立性补强组件挂入 advice 阶段

> 类型: scripts-reflow（管线组件接线）
> 提案编号: BASE-REFLOW-20260913-04
> 状态: **人工门禁已批准**（2026-09-13，"批准接线并验收"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 审批记录

- 草案 DRY 实测: verify（15 行 0 失败）、dual_review（3 轮 LLM 复核，抓出 9 条真实记录卫生问题）
- 人工门禁: 批准接线并验收
- 落盘: BASE/scripts/project_verify_pains.py、BASE/scripts/project_dual_review.py、
  dispatch_wrapper.bat 接入 6a/6b（GBK+CRLF 安全补丁，88 行）

## 端到端验收证据（2026-09-13 12:00 手动完整调度）

- dispatch.log: `[6a/7] project-pain-verify rc=0`、`[6b/7] project-dual-review rc=0`
- summary 行: `... sitegen=0 pverify=0 preview=0 advice=0 ...`
- project-pain-verification.json: entries=22 failed=0（全部证据引用真实）
- project-review.log: events=10 live=True verdict=concern（管线内的独立复核人持续审查新增事件）
- **自观测事件**：selfcheck=1 —— 体检器发现本次接线修改了 dispatch_wrapper.bat（快照漂移），
  如实告警且不中断调度。这正是"系统看见自己演化"的预期行为。

## 复核闭环的收敛（P-5，人工裁决已关闭）

独立复核人对 P-2 弧线共提出 3 轮 9 条意见（版本上下文缺失、证据自引用、重复落库、
行索引不唯一等），全部逐条回应并修正：台账写入机械化（ledger_append.py 唯一 row_id）、
权威索引裁定为文件行序、S-6 证据路径补全、遗留行定位补全。
用户裁决"回应充分"→ P-5#29 resolved(human-verdict)。
教训入库：append-only 历史行不可回写，修正=追加引用行号；复核收敛判定必须人工裁决。

## 回滚

删除两个脚本 + `git checkout -- BASE/scripts/dispatch_wrapper.bat`。

## 未做（standing 规则）

未 commit/tag/push；git 状态含 4 次回流的累积变更，待发布 SOP 授权统一处理。
