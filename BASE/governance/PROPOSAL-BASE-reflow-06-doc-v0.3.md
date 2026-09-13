# PROPOSAL: BASE 回流 06 — PROJECT-LAYER.md v0.3（运行态闭环）

> 类型: docs-reflow（文档类）
> 提案编号: BASE-REFLOW-20260913-06
> 状态: **人工门禁已批准**（2026-09-13，"批准更新 v0.3"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 审批记录

- 草案: tasks/project-layer-p3-20260912/task-evolve/base-reflow/DRAFT-PROJECT-LAYER-v0.3.md
- 规则层: BASE 写入一律 reject → 升级人工（边界正常）
- 人工门禁: 批准更新 v0.3
- 落盘: BASE/docs/PROJECT-LAYER.md，sha256 = eccabb6cd6a22d82…（Copy-Item + 双重校验 IDENTICAL）
- 未 commit/tag（standing 规则）

## 变更内容（v0.2 → v0.3）

1. 0 节裁定新增两条：独立性是机制级要求；台账写入机械化（ledger_append 唯一行身份）；
2. 2.7 节新增"独立制衡"段（验证器+复核人+人工收敛裁决）；
3. 3 节案例表更新为当前真实状态（案例①冻结、②管线接管 12 迭代、③独立复核+回归）；
4. 4 节落地阶段更新 + 新增 4.1"运行态闭环（10 阶段调度）"；
5. 5 节开放问题标注状态（Q4 策略池已试点；Q5 新增 model 级独立与全局汇总候选）。

## 同步任务层

- DESIGN-v0.1.md 新增第 6 节"运行态闭环完成记录"；
- P2 章程 roadmap 更新（P3 完成、管线接管表述）；
- 站点由管线脚本刷新（iteration 12）。

## GATE 通用门槛自检

- [x] 证据链：5 份 governance 提案归档 + 回归台账 + 站点 truth.json
- [x] 跨领域复用：投资/网页/底座三域
- [x] 不降回归：纯文档
- [x] 可回滚：git 恢复 v0.2 内容
- [x] 不削弱铁律：独立性/人工裁决边界均为加强项
