# PROPOSAL — 自举 v0.1 回填提案（复合）

> 变更记录：2026-09-12 人工 Gate 复审，按 4 处意见修订后重新提交（回归公式方案 A / gate-review 步骤 6 落盘规则 / 新增自指处理段 / ARCHIVE 差异更正）。

> 按 `TEMPLATES/PROPOSAL.md` 填写。提案人：本轮设计者 agent（经人工确认后生成）。
> 独立门控由人工担任（冷启动无独立 Gate 执行者，按 `gate-review` 铁律：宁缺毋滥）。

## 提案元信息

- 类型：**architecture**（复合提案，含子项：new-skill ×1、skill-modify ×3、pattern ×5、回归细则 ×1、结构差异 ×7）
- 来源项目：bootstrap-v0.1（冷启动首轮，无真实项目轨迹）
- 提案人：agent（本轮设计者），人工确认：已确认（2026-09-12）
- 目标 BASE 版本：v0.2.0（由人工审核后定版）

## 变更内容（diff 描述）

全部产物在 `WORKSPACE/` 下，合并时映射至 BASE：

| 文件 | 合并去向 | 类型 |
|---|---|---|
| `skills/route-intake/SKILL.md`（改进版） | `BASE/skills/route-intake/SKILL.md` | skill-modify |
| `skills/trace-distill/SKILL.md`（改进版） | `BASE/skills/trace-distill/SKILL.md` | skill-modify |
| `skills/propose-gate/SKILL.md`（改进版） | `BASE/skills/propose-gate/SKILL.md` | skill-modify |
| `skills/gate-review/SKILL.md`（新增） | `BASE/skills/gate-review/SKILL.md` | new-skill |
| `wiki/patterns/` 五条（新增） | `BASE` 经验库首条回填（见 BASE-structure-proposal.md） | pattern |
| `BASE-structure-proposal.md` | 结构差异 7 项，人工逐项取舍 | architecture |
| `route-design.md` | `BASE/META/` 或 README 引用（机制设计文档） | architecture |
| `regression-design.md` | `BASE/META/REGRESSION.md` 的完整细则（补第六维独立验证） | architecture |
| `regression-runs/`（新增目录） | `BASE/regression-runs/` + 项目侧 `WORKSPACE/regression-runs/` | architecture |

## 问题 / 动机

现有 BASE 哪里不适配？证据是什么？

1. **第六维验证缺口**（环境自检发现，人工已确认）：`META/REGRESSION.md` 六维打分只给 0–2 分与 ≥9/12 阈值，第六维"演化规程"无独立、可操作验证方式，"演化回填建议"只是产出清单项。→ `regression-design.md` 以 E1/E2/E3 三项机械可查子检查 + 附加门槛补全。
2. **Gate 角色缺失**：BASE 技能集无独立门控执行者，Gate 职责折叠于 propose-gate 自检 + 人工（自指观察：本轮即由此发现）。→ 新增 `gate-review`，提案人与审核人分离（pattern `gate-rubber-stamp`）。
3. **PURPOSE.md 缺失**：wikiskill 种子要求技能注明演化来源，现 `skills/` 无。→ 结构差异 #3。
4. **"不降回归"条款不可操作**：未定义试跑产物落点。→ `regression-runs/` 落点规范（结构差异 #4）。

## 证据摘要

**第一轮冷启动限制（如实标注，不伪造）**：

- 无真实项目轨迹。本提案证据 = 种子推理（4 个 SEED 摘要的具体结论引用）+ 结构化自指论证（本轮真实过程：环境自检发现缺口 → 设计 → 人工确认迭代）；
- 本会话唯一真实轨迹是元层路由记录 `WORKSPACE/raw/route-bootstrap-v0.1.md`（含技能版本戳、失败记录、人工反馈），它证明流程本身可运行，**不构成领域复用证据**；
- **GATE"≥1 条真实轨迹"门槛在本轮由人工豁免**。回补期限定义：
  > 以"使用本自举候选 BASE v0.1 完成的**第一个真实项目**"为触发点，该项目结束 + 7 天内回补 ≥1 条真实轨迹并在 ≥1 个非原领域探针上复用验证；逾期未回补，本提案状态由 conditional-accept 降级为 **suspended**。
- 冷启动产物定性为"v0.1 自举候选"，不宣称"已通用"。

## 跨领域复用案例

- 原领域：元设计（软件邻接）
- 探针任务（非原领域）：P2 供应链中断响应预演（制造业）、P3 员工报销审批（合规）、P4 内容运营复盘
- 复用结果：**尚未执行**（如实）。设计级替代：探针集本身跨 4 领域 + 反工程师人格污染五措施（regression-design.md §六）；真实复用验证纳入上述回补期限。

## GATE 自检

- [ ] ~~证据链完整~~ → **⚠ 部分豁免**：无真实轨迹，人工豁免 + 回补期限如上；本会话元层轨迹 route-bootstrap-v0.1.md 属实，但仅证流程可运行。
- [ ] ~~跨领域复用成功~~ → **⚠ 未满足**：仅设计级替代；真实复用纳入回补期限。
- [ ] ~~不降回归~~ → **N/A**：首版无历史基线；替代措施 = 回归细则设计 + 人工合并时试跑建立 v0.1 基线（落盘 `BASE/regression-runs/`）。
- [x] 可回滚：全部产物在 `WORKSPACE/`，未触碰 BASE；拒绝合并即完整回滚；合并后可用 git 旧 tag 回滚；wiki patterns 不回滚（经验保留）。
- [x] 不削弱铁律：逐条核对——HITL 保留（gate-review 强化而非削弱门控）；执行与经验隔离保留（trace-distill 仍限定维护/提案角色）；不直连 wiki 抄答案保留；种子仍可替换（无"不可修改项"）；高危权限不开放。

**结论：conditional-accept 候选（冷启动豁免 + 回补期限），最终裁定由人工 Gate 作出。**

## 自指处理

gate-review 作为门控执行者，其自身 SKILL.md 的审核走 GATE 级 C 的简化路径——由人工直接担任 Gate 进行单次审核（无需独立 agent，因元流程角色无法被元流程自身审核），审核记录落盘 regression-runs/gate-review-self-review-2026-09-12.md。后续 ≥2 个真实项目使用后，按其实际审核表现决定是否保留或重构。本例外仅适用于门控角色自身，不扩展到其他技能。

## 回滚方案

1. 拒绝 → 全部产物归档 `ARCHIVE/`，pattern 保留供再评估；
2. 部分接受 → 按 BASE-structure-proposal.md 差异清单逐项合并（各差异独立可取舍）；
3. 合并后劣化 → git 旧 tag 回滚；`wiki/patterns/` 与 `ARCHIVE/` 不回滚；
4. 逾期未回补 → 状态降级 suspended，重新人工审核。

## 状态

proposed（本文件由人工审核；建议裁定：conditional-accept + 回补期限）
