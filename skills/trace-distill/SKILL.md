---
name: trace-distill
description: 从原始执行轨迹（WORKSPACE/raw）蒸馏可复用模式写入 wiki/patterns；强制轨迹版本留痕、新颖性检查与 pattern 抽象层级测试；不直接修改执行技能。whenToUse: 任务完成后、产出 PROPOSAL 前；或周期性复盘时。
---

# trace-distill — 轨迹蒸馏为模式（v0.1 自举候选改进版）

## 目的

把原始轨迹转化为结构化、可跨项目复用的 pattern（经验库），是演化循环的"知识沉淀"环节。

相对种子版（`skills/trace-distill`）的改进：

1. 轨迹格式强制**技能版本戳**与**失败记录**字段（供第六维 E1 查验）；
2. 新增**新颖性检查**（防经验库同义重复、信息量退化，见 pattern `wiki-answer-copy`）；
3. 新增**抽象层级测试**（防跨域迁移静默失败，见 pattern `cross-domain-transfer-failure`）。

## 适用角色与领域

**维护/提案角色专用**。执行 agent 不得使用本技能（执行与经验隔离铁律）。

## 输入

`WORKSPACE/raw/` 轨迹 + 现有 `WORKSPACE/wiki/patterns/`。

## 步骤

1. **采集/校验轨迹**：每条轨迹须含 prompt、技能版本戳、工具调用、中间结果、失败记录、最终输出、人工反馈字段；缺版本戳的轨迹标注"字段不全"后仍可入 raw，但蒸馏时降权。格式：`<时间戳>-<任务slug>.md`。
2. **阅读 raw + 现有 patterns**：找出反复出现的失败、意外成功、可复用的决策规则。
3. **新颖性检查**：候选 pattern 与现有 pattern 逐条对照；完全同义 → 不新建，合并进现有条目并在 `logs.md` 记录。避免"抄答案式"重复蒸馏（轨迹信息量退化）。
4. **抽象层级测试**：候选 pattern 的"现象/触发条件/应对措施"能否**全文无领域名词重述**且仍可执行？
   - 能 → 领域无关层，可进通用目录
   - 不能 → 标注领域限定，写清依赖的领域前提（防 cross-domain-transfer-failure）
5. **抽取 pattern** → `WORKSPACE/wiki/patterns/<slug>.md`（按 `TEMPLATES/PATTERN.md`：类型/现象/触发条件/根因/应对措施/适用条件与例外/证据轨迹/跨领域适用性评估/状态）。
6. **更新 `WORKSPACE/wiki/logs.md`**，按迭代记录本次发现。
7. **不直接修改执行技能**：技能修改由 `propose-gate` 基于 wiki + raw 提出，经门控生效。
8. **底座缺陷上报**：若发现底座自身缺陷（gate 漏洞、回归盲区等）→ 产出 meta-* pattern 候选，交 `propose-gate` 处理，不在本技能内直接改规则。

## 验证判据

- 每条 pattern 有 ≥1 条轨迹证据链（冷启动无轨迹时如实标注"冷启动推理"，禁止虚构）
- pattern 含"跨领域适用性评估"与"抽象层级"结论
- `logs.md` 有新发现记录；无重复 pattern 入库

## 回滚方案

删除/合并 pattern 无需门控（经验库非执行面），但须在 `logs.md` 记录；wiki 不随 skill 回滚（失败经验永久保留）。

## 注意事项 / 反模式

- 反模式：执行 agent 使用本技能；虚构 raw 轨迹引用；跳过新颖性检查导致 pattern 堆积。
- 冷启动诚实条款：无真实轨迹时，证据轨迹字段写"冷启动推理：依据 = 种子推理 + 自指论证"，并注明回补期限。

## 来源

- 种子：wikiskill（raw/wiki/skills 三层 + 执行隔离）、mattpocock（诊断骨架）
- 演化轨迹：冷启动推理；关联 pattern：`wiki-answer-copy`、`cross-domain-transfer-failure`
