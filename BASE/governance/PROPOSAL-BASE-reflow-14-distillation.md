# PROPOSAL: BASE 回流 14 — 第四轮反馈响应（第一轮真实经验蒸馏 + 表达窗口改造）

> 类型: **distillation-reflow**（13 轮以来第一类新演化类型：经验蒸馏）
> 提案编号: BASE-REFLOW-20260913-14
> 状态: **人工门禁已批准**（2026-09-13，"批准全部"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 背景与核验

第四轮反馈两条挑刺均逐项核验属实：
① **忘本**：CONSTITUTION 元流程 = 轨迹采集→模式提取→技能提案→门控验证→回填；
13 轮 reflow 全部为 scripts-reflow/docs-reflow，模式提取与技能提案一次未发生
（wiki/patterns 5 条种子、skills 5 个技能自 v0.1 冻结）；
② 展示站是"内部审计报告"而非"表达窗口"。

## 变更一：第一轮真实经验蒸馏

- **轨迹**：本会话 4 条真实实例（6f 顺序 bug 由用户观察暴露；版本元数据漂移由外部核验指出；
  feedback 半落地由逐行核验指出；快照滞后误读）；
- **模式提取**：`WORKSPACE/wiki/patterns/downstream-view-gap.md`（status=distilled，
  完整六段结构 + 4 条证据轨迹 + 跨领域适用性评估）；
- **技能提案**：`BASE/skills/downstream-verify/SKILL.md`（whenToUse + 四步 + 硬性判据 + 回滚）；
- **门控验证**：规则层照例对 BASE 写入 reject → 人工门禁批准；
- **回填**：pattern 入 wiki、技能入 skills、本归档留痕——元流程五步首次完整走通。

## 变更二：展示站表达改造

- hero 加人话场景句（charter hero_scenario，真值溯源）；
- 新增"30 秒零成本体验"交互 demo（真实策略池审计数据驱动，claims=11）；
- 新增"我要参与"三入口（使用者/提意见者/二次开发者）。

## 对"铁律 3 是否还活着"的诚实回答

- 现状：14 阶段管线直接执行硬化后的脚本，运行时不加载 skills——skills 层在运行时是
  遗留物；但 skills 作为"经验蒸馏的落点"仍有效（本轮即其证明）。
- 裁定（本轮，不修宪）：**铁律 3 在新架构中的对应物 = "脚本是硬化后的技能；
  蒸馏路径（trace→pattern→skill→script）每轮 reflow 检视一次"**。本归档即检视产物。
  若连续 N 轮检视仍为零蒸馏，将在展示站如实标注"经验蒸馏停转中"（P-14 挂账条件）。

## 台账

- P-14#? open(third-party-feedback-round4)：蒸馏常态化、引流指标达标、第五轮核验前不关闭；
- 演化类型从本轮起分两类：**脚本/文档硬化** 与 **经验蒸馏**（本归档为首例蒸馏）。

## 回滚

git revert 52b0d32（pattern/skill/site 一处回退）。
