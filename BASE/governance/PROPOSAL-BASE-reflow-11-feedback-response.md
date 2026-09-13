# PROPOSAL: BASE 回流 11 — 第三方反馈响应（P-9 行动）

> 类型: scripts-reflow + 修复
> 提案编号: BASE-REFLOW-20260913-11
> 状态: **人工门禁已批准**（2026-09-13，"批准全部"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 背景：第一份真实世界反馈

2026-09-13 收到独立使用者逐项核对仓库后的反馈（P-9 种子，source=third-party-feedback）。
逐项核验结果：全部事实主张属实（config version 冲突、19 台账、1 项目、10 痛点等）。

## 本提案变更（其 P0/P1/P2 建议的落地）

1. BASE/META/config.json `version` 0.4.0-roadmap → 0.5.0（修复元数据不一致）；
2. project_regression.py 新增 **I-9 version-metadata-consistent**（config version == VERSION 文件，
   防止再次漂移）——草案实测在修复前精确 FAIL、修复后 PASS；
3. project_feedback_truth.py v3：新增 clones_14d（traffic/clones API）+ delta_vs_prev 环比——
   反馈从单点快照升级为带时间语义的趋势（其 P1 建议 3/4）；
4. project_site_gen.py：站点 hero 叙事强化（"把长期目标变成被持续照顾、可审计、会自我演化的
   责任体"+"谁需要它"一句话）——其 P2 建议 6；
5. P2 charter：task_layer 明确列为下一里程碑候选（不留在模糊态）；evaluation 增加真实世界
   验证目标（≥1 条非作者有效反馈 或 ≥5 次 v0.5.0 下载 或 ≥1 star）；
6. 站点快照重发布并 push（ad350a2）。

## 验收证据

- I-9：修复前 FAIL（config=0.4.0-roadmap vs file=0.5.0）→ 修复后 PASS（0.5.0==0.5.0）
- 站点 iteration 23，claims=10，hero 新叙事已上线
- 回归集 10→11 项检查

## 尚未落地（P-9 挂账，如实记录）

- P1 建议 5 的"吸引 N 个非作者用户"已设目标，未达标前 P-9 不关闭；
- P2 建议 7（30 秒交互 demo）与 P3 建议 9（提法器结构化输出/分块）、10（第二个异构项目）
  列为后续候选——不演示通胀，逐项评估后再动。

## 回滚

git revert ad350a2（单提交含全部变更）。
