---
name: propose-gate
description: 基于 wiki patterns + raw 轨迹提出技能/架构/宪法修改，按 GATE.md 自检并生成 PROPOSAL.md；自检完成后必须移交独立门控（gate-review 或人工），提案人不得兼任审核人。whenToUse: 任务结束前；或 route-intake 判定"底座不适配"时。
---

# propose-gate — 提案与门控（v0.1 自举候选改进版）

## 目的

把累积经验转化为对 BASE 的可控修改，保证演化**可溯源、可回滚、不退化**。

相对种子版（`skills/propose-gate`）的改进：

1. **提案人与审核人分离**：本技能只做提案与自检；裁定由 `gate-review`（或人工）独立完成（见 pattern `gate-rubber-stamp`）；
2. 门控核验要求**回归试跑产物落盘**至 `WORKSPACE/regression-runs/`；
3. 新增**冷启动诚实条款**。

## 适用角色与领域

维护/提案角色专用。

## 输入

`WORKSPACE/wiki/patterns/` + `WORKSPACE/raw/` + 任务路由记录中的适配判断。

## 步骤

1. **依据来源**：找出 ≥2 条支持同一改动的证据（pattern 或轨迹）。
2. **确定提案类型**：new-skill | skill-modify | architecture | constitution-amendment。
3. **填写 `PROPOSAL.md`**（用 `TEMPLATES/PROPOSAL.md`）：变更内容、动机、证据、跨领域复用验证、回滚方案。
4. **按 `META/GATE.md` 逐条自检（自评）**：
   - 证据链 / 跨领域复用 / 不降回归 / 可回滚 / 不削弱铁律；宪法级另需双倍验证（交叉验证 + 人工复审 + 保留旧 tag）。
   - 自检结果仅供参考，**不替代独立门控**。
5. **移交独立门控**：将 PROPOSAL + 自检表交给 `gate-review`（独立审核者）或人工；记录移交对象（提案人 ≠ 审核人）。
6. **门控结果处理**：
   - accepted → 由人工按 GATE.md"回填操作"合并 + 打 tag（**提案人不自行合并**）
   - rejected → 归档 `ARCHIVE/`，pattern 保留供再评估
   - skill 修改被回滚时，**wiki 不回滚**
7. **冷启动诚实条款**：无真实项目轨迹时，在 PROPOSAL 中如实标注"第一轮冷启动限制"，证据仅用种子推理 + 自指论证；GATE"≥1 条真实轨迹"的豁免与回补期限必须写明；禁止伪造 raw 引用。

## 验证判据

- 每个 PROPOSAL 都有完整 GATE 自检清单
- 无证据支撑的理论提案不被生成（冷启动豁免须显式标注并设回补期限）
- 移交独立门控有记录，提案人与审核人分离可追溯

## 回滚方案

本技能提出的任何改动自带回滚方案；宪法级改动保留旧版本 tag；被拒提案不影响 wiki 经验库。

## 注意事项 / 反模式

- 反模式：自检通过后直接宣布"已升级"；提案人自己跑门控给自己发 accept；省略回归试跑产物；伪造轨迹证据。
- 人工是最终裁决者；独立审核者缺位时由人工（用户）担任 Gate，宁缺毋滥。

## 来源

- 种子：wikiskill（Skill Proposer 角色）、GATE.md
- 演化轨迹：冷启动推理 + 本轮自指观察（现 BASE 无独立 Gate 执行者）；关联 pattern：`gate-rubber-stamp`
