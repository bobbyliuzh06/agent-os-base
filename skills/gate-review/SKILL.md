---
name: gate-review
description: 独立门控执行者：对经 propose-gate 自检的 PROPOSAL 跑回归探针、记录 before/after 至 regression-runs/、输出 accept/reject/archive 裁定。不做提案自评，不修改提案内容，不合并 BASE。whenToUse: 收到待审 PROPOSAL 时；或人工指定复核时。
---

# gate-review — 独立门控执行（v0.1 自举候选，新增）

## 目的

补齐 WikiSkill 四角色循环中缺失的 **Gate 执行者**。当前 BASE 把 Gate 职责折叠进 `propose-gate` 自检 + 人工，存在橡皮图章风险（见 pattern `gate-rubber-stamp`）。

**职责严格限定**：跑探针、记录 before/after、输出 accept/reject/archive。除此之外不做任何事。

## 铁律：提案人与审核人分离

- 审核人不得是提案人本人；同一 agent 会话不得同时担任两者。
- 无独立审核者时，由人工（用户）担任 Gate；宁缺毋滥，不得"自己审核自己"。
- `propose-gate` 的自检表仅供参考，审核人必须独立复核每条条款。
- 审核人**不做提案自评**（自评归 `propose-gate`），**不修改提案内容**，**不产生新提案**，**不合并 BASE**。

## 适用角色与领域

门控角色专用。

## 输入

PROPOSAL.md + 自检表 + 变更对象（技能文件/架构文档/规则改动 diff）。

## 步骤

1. **核验证据链存在性（机械检查）**：raw 链接是否有效；冷启动豁免声明是否存在且注明回补期限。
2. **跑回归探针**：按 `META/REGRESSION.md` 的探针集执行 before/after 试跑；原始记录写入 `WORKSPACE/regression-runs/<提案slug>-<日期>.md`（含各探针六维得分与通过/失败结论）。
3. **核对分级门槛**：按提案类型（A 技能 / B 架构 / C 宪法）逐条核对 GATE.md 条款。
4. **核对自动拒绝项**：放宽高危权限、执行 agent 直读 wiki、无证据纯理论提案、降回归、把种子设为不可修改 —— 命中任一 → 直接 reject。
5. **输出裁定（三选一）**：
   - accept：全部门槛通过，回归不降分
   - conditional-accept：冷启动豁免成立，附回补期限与逾期降级条款（suspended）
   - reject：任一条不满足 → 归档 `ARCHIVE/`，pattern 保留供再评估
6. **记录审核痕迹（永久落盘）**：裁定依据与 before/after 写入 `WORKSPACE/regression-runs/<提案slug>-<日期>.md`（永久落盘，供 E1 查验）；摘要同步至 `WORKSPACE/wiki/skill-impact.md`——本技能作为门控角色，是唯一允许写入 wiki/skill-impact.md 门控结论（accept/reject/回滚原因）的角色；wiki/patterns/ 仍由 trace-distill 维护角色按蒸馏流程写入，二者对象不重叠；执行 agent 不直读 wiki。

## 验证判据

- 每份 PROPOSAL 有独立审核记录与回归产物落盘
- 不存在"提案人自审通过"的 accept 记录
- 裁定均可机械复核（探针得分、门槛条款号可追溯）

## 回滚方案

裁定错误可通过重新审核修正；`ARCHIVE/` 可复活（pattern 保留）；本技能自身修改走 GATE A 级（skill-modify），回滚即恢复上一版 SKILL.md。

## 注意事项 / 反模式

- 反模式：审核时顺手"改进"提案（越权）；以个人偏好替代 GATE 条文；不落盘回归产物直接给结论。
- 审核人发现缺陷 → 记录并退回，由提案人修改后再审。

## 来源

- 种子：wikiskill（Gate 角色）、GATE.md
- 演化轨迹：冷启动推理 + 本轮自指观察（Gate 角色缺失即本技能的存在理由）；关联 pattern：`gate-rubber-stamp`
