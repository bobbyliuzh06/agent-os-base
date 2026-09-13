# PROPOSAL: BASE 回流 15 — 第五轮反馈响应（修宪补程序 + 蒸馏常态化 + 互动 demo）

> 类型: constitution-amendment + distillation-reflow + scripts-reflow
> 提案编号: BASE-REFLOW-20260913-15
> 状态: **人工门禁已批准**（2026-09-13，两项均批准）
> 归档: 依 GATE.md 回填操作归档至 governance/

## distillation_check（每轮 reflow 固定问句，I-10 强制）

**问句：本轮是否有新轨迹可蒸馏？**
**答案：有。** 本轮真实轨迹 = "reflow 14 以裁定替代修宪、被外部核验指为程序违规、
随后正式补办修正案"——已蒸馏为第二条 pattern《meta-procedure-drift》（元程序漂移，
完整六段结构，状态 distilled）。与 reflow 14 的《downstream-view-gap》构成连续两轮蒸馏。

## 变更清单

1. **宪法修正案 AMEND-20260913-01**（用户人工复审批准）：铁律 3 新增新架构对应物段
   （脚本=技能硬化产物；蒸馏路径每轮检视；连续 3 轮零蒸馏须如实标注；
   "以裁定替代修宪不成为先例"写入宪法正文）；交叉验证 3 条跨项目证据；
   保留旧 tag v0.5.0，新 tag v0.5.1；CHANGELOG v0.5.1；
2. **蒸馏第二条**：WORKSPACE/wiki/patterns/meta-procedure-drift.md（status=distilled）；
3. **回归 I-10**（蒸馏检视连续性）：最新 governance 归档必须含 distillation_check
   字段——实测修复前 FAIL、本轮归档后 PASS，把"每轮都问一遍"从口号变成机器强制；
4. **站点 demo 升级**：回放→输入互动（纯前端输入回显 + 四步动画 + 淡入过渡，
   诚实标注"预置流程+输入回显"）；hero 改读者痛点视角。

## 端到端验收

- I-10：本归档含 distillation_check → PASS（回归集 12 项）；
- 站点 iteration 31+，互动 demo 上线（随 6f 自动发布）；
- VERSION/config=0.5.1 一致（I-9 PASS）；v0.5.1 tag 已打并推送。

## 台账

- P-15 保持 open：等第六轮核验确认三项（蒸馏常态化机制、修宪程序合规、demo 互动效果）。

## 回滚

git revert 本轮提交 + 删除 v0.5.1 tag（宪法文本回旧版；旧 tag v0.5.0 不受影响）。
