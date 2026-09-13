# PROPOSAL: BASE 回流 — Project 层设计文档

> 类型: docs-reflow（文档类，非技能/架构/宪法）
> 提案编号: BASE-REFLOW-20260913-01
> 状态: **人工门禁已批准**（2026-09-13，用户本人在会话中批准）
> 归档: 依 GATE.md 回填操作，人工审核通过后归档至 governance/

## 审批记录（人工门禁）

- 提案文件: tasks/project-layer-p3-20260912/task-evolve/base-reflow/PROPOSAL.md
- 草案文件: tasks/project-layer-p3-20260912/task-evolve/base-reflow/DRAFT-PROJECT-LAYER.md
- 确定性规则层预审: **reject**（"写BASE被禁止"，risk=high，auto_merge=False）→ 正确升级人工
- 人工门禁: **批准写入**（用户选择"批准写入（推荐）"）
- 落盘文件: BASE/docs/PROJECT-LAYER.md
- 字节一致性: DRAFT 与落盘文件 sha256 相同 = e3e7d19ada0d1ca693da7161f31fc1d2a8372952a024b101c52bcbfb73ff0d56
- 版本操作（commit/tag/CHANGELOG）: **未执行**——遵守项目standing规则"无步骤授权不自动 commit/tag"，留待后续发布 SOP 授权。

## 变更内容

- 新增 BASE/docs/PROJECT-LAYER.md（Project 层设计 v0.1 草案：七要素、三条铁律、三类案例与真实实现状态）。
- 纯文档；不修改任何现有 BASE 文件；不参与运行路径。

## GATE 通用门槛自检

- [x] 证据链：案例 P0/P1/P2/P3 真实产物（audit/*.json、memory/*.jsonl、site/truth.json、selfchecks.jsonl）
- [x] 跨领域复用：投资 → 网站 → 底座自身三域
- [x] 不降回归：纯文档，不影响 META/REGRESSION
- [x] 可回滚：删除 BASE/docs/PROJECT-LAYER.md
- [x] 不削弱铁律：文档明确 HITL 边界（真钱/发布/自修订必须人工）

## 留痕

- 预审脚本: tasks/project-layer-p3-20260912/task-evolve/base-reflow/rehearse_gate.py
- 提案原文: tasks/project-layer-p3-20260912/task-evolve/base-reflow/PROPOSAL.md
