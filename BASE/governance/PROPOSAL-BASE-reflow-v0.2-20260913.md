# PROPOSAL: BASE 回流 v0.2 — PROJECT-LAYER.md 评估域抽象更新

> 类型: docs-reflow（文档类）
> 提案编号: BASE-REFLOW-20260913-02
> 状态: **人工门禁已批准**（2026-09-13，用户本人在会话中批准"批准更新 v0.2"）
> 归档: 依 GATE.md 回填操作，人工审核通过后归档至 governance/

## 审批记录（人工门禁）

- 草案文件: tasks/project-layer-p3-20260912/task-evolve/base-reflow/DRAFT-PROJECT-LAYER-v0.2.md
- 确定性规则层: BASE 写入一律 reject → 升级人工（规则层边界，同 v0.1 预审结论）
- 人工门禁: **批准更新 v0.2**
- 落盘文件: BASE/docs/PROJECT-LAYER.md
- 字节一致性: sha256 = 59f50ea57ed09101…（Copy-Item + 双重 sha256 校验 IDENTICAL）
- 版本操作（commit/tag/CHANGELOG）: **未执行**——遵守 standing 规则"无步骤授权不自动 commit/tag"。

## 变更内容（v0.1 → v0.2）

1. 0 节新增裁定：评估与回写是机制级原语（2026-09-13 平等讨论裁定）；
2. 1.1 七要素：章程增加"评估域声明"、记忆增加"痛点台账"；
3. 2.1 charter 草案增加 evaluation 块；
4. 2.2 memory/ 增加 pains.jsonl；2.4 六步的第 1/2/5/6 步并入通用回路；
5. 新增 2.7 节"评估与回写机制（评估域抽象）"含五场景示例表；
6. 3 案例表增加评估域列（paper-performance / showcase-feedback / process-health）。

## GATE 通用门槛自检

- [x] 证据链：P1 run-20260913T031934Z（P-1 live 3/3 关闭、P-2 open、P-4 关闭）+ P2 站点 iteration 5 + P3 自检 2 轮
- [x] 跨领域复用：投资 / 网页 / 底座自身三域同机制不同评估域
- [x] 不降回归：纯文档
- [x] 可回滚：git 恢复 BASE/docs/PROJECT-LAYER.md v0.1 内容
- [x] 不削弱铁律：显式降级声明、人工复核边界均加强 HITL

## 留痕

- 设计文档: tasks/project-layer-design-20260912/workspace/DESIGN-v0.1.md（2.7 节 + 0 节裁定）
- 三个 charter 的 evaluation 块: P0/P2/P3 task-evolve/charter.yaml
