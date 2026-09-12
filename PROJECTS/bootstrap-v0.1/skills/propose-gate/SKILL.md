---
name: propose-gate
description: 基于 wiki patterns + raw 轨迹提出技能/架构/宪法修改，按 GATE.md 自检并生成 PROPOSAL.md。whenToUse: 任务结束前；或 route-intake 判定"底座不适配"时。
---

# propose-gate — 提案与门控

## 目的
把累积的经验转化为对 BASE 的可控修改，保证演化**可溯源、可回滚、不退化**。

## 步骤

### 1. 依据来源
阅读 `WORKSPACE/wiki/patterns/` + `WORKSPACE/raw/`，找出 ≥ 2 条支持同一改动的证据。

### 2. 确定提案类型
new-skill | skill-modify | architecture | constitution-amendment

### 3. 填写 `PROPOSAL.md`（用 TEMPLATES/PROPOSAL.md）
包含：变更内容、动机、证据、跨领域复用验证、回滚方案。

### 4. 按 `META/GATE.md` 逐条自检
- 证据链 / 跨领域复用 / 不降回归 / 可回滚 / 不削弱铁律
- 宪法修正案需**双倍验证**（交叉验证 + 人工复审 + 保留旧 tag）

### 5. 交付人工审核
输出 `PROPOSAL.md` 交给用户，**不自行合并进 BASE**。

### 6. 门控结果处理
- accepted：用户按 GATE.md "回填操作"合并 + 打 tag
- rejected：归档至 `ARCHIVE/`，保留 pattern 供再评估
- skill 修改被回滚时，**wiki 不回滚**

## 验证判据
- 每个 PROPOSAL 都有完整的 GATE 自检清单
- 无证据支撑的理论提案不被生成

## 回滚
本技能提出的任何改动自带回滚方案；宪法级改动保留旧版本 tag。
