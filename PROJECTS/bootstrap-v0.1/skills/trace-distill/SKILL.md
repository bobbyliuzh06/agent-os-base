---
name: trace-distill
description: 从原始执行轨迹（WORKSPACE/raw）中蒸馏出可复用模式写入 wiki/patterns，不直接修改执行技能。whenToUse: 任务完成后、产出 PROPOSAL 前；或周期性复盘时。
---

# trace-distill — 轨迹蒸馏为模式

## 目的
把原始轨迹转化为结构化、可跨项目复用的 pattern（经验库），是演化循环的"知识沉淀"环节。

## 步骤

### 1. 采集轨迹到 `WORKSPACE/raw/`
每条轨迹文件记录：prompt、技能版本、工具调用、中间结果、失败、最终输出、人工反馈。
格式：`<时间戳>-<任务slug>.md`

### 2. 阅读 raw + 现有 `wiki/patterns/`
找出：反复出现的失败、意外成功、可复用的决策规则。

### 3. 抽取 pattern → `WORKSPACE/wiki/patterns/<slug>.md`
使用 `TEMPLATES/PATTERN.md` 结构：现象 / 触发条件 / 根因 / 应对措施 / 适用条件 / 证据链 / 跨领域适用性。

### 4. 更新 `wiki/logs.md`
按迭代记录本次发现。

### 5. **不直接修改执行技能**
技能修改由 `propose-gate` 基于 wiki + raw 提出，经门控后生效。

## 关键原则
- **执行 agent 不直读 wiki**：本技能仅给维护/提案角色使用
- **wiki 持久、不随 skill 回滚**：失败经验永远保留
- 优先抽象到领域无关层级，提升跨域复用性

## 验证判据
- 每条 pattern 都有 ≥ 1 条轨迹证据链
- pattern 有"跨领域适用性评估"字段

## 回滚
删除/合并 pattern 无需门控（经验库非执行面），但需在 logs.md 记录。
