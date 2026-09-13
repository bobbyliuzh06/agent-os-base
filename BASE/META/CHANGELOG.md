# CHANGELOG

## v0.5.1 2026-09-13
- 宪法修正案 AMEND-20260913-01（用户人工复审批准）：铁律 3 新增新架构对应物（脚本=技能硬化产物；蒸馏路径每轮 reflow 检视；连续 3 轮零蒸馏须如实标注）；以裁定替代修宪不成为先例
- 经验蒸馏第二条：pattern meta-procedure-drift（元程序漂移）
- 回归集 I-10：蒸馏检视连续性强制；站点 demo 升级为输入互动（回显+动画+淡入过渡）
## v0.5.0 2026-09-13
- Project 层（持久责任对象）设计文档入 BASE/docs（v0.3：七要素/三条铁律/评估域抽象/独立制衡）
- 管线接管：调度 10→12 阶段（5a 自体检、5b 站点生成、6a 证据验证、6b 独立复核(pro 模型)、6c 全局痛点汇总、6d 事件驱动策略池、7a 过程回归）
- 机制：痛点台账（append-only+唯一行身份）、评估与回写回路、确定性门禁对 BASE 写入永拒
- 治理：8 份回流提案 + 1 份发布授权归档至 governance/
- 发布：github.enabled 开启，展示站随发布上线 GitHub Pages
- 备注：v0.3.x/v0.4.x 以 git tag 存在（v0.4.6 供应链台账完整），本文件当时未同步维护，故无对应条目

## v0.1.0 (初始版本)
- 建立 BASE 骨架：AGENTS.md、META（CONSTITUTION/GATE/REGRESSION/CHANGELOG）、SEED、TEMPLATES、skills、governance
- 种子技能：constitution / route-intake / trace-distill / propose-gate
- 引入"宪法 + 回填门控 + 回归探针"演化循环
- 来源：mattpocock/skills 抽象 + WikiSkill(raw/wiki/skills/gate) + Scaling(架构假设) + 对话蒸馏

## v0.2.0 2026-09-12
- 新增 gate-review 独立门控技能（提案人/审核人分离，不做自评）
- route-intake/trace-distill/propose-gate 改进版（仅 SKILL.md，未含 PURPOSE.md）
- 新增 gate-review SKILL.md
- META/REGRESSION.md 补全第六维 E1/E2/E3 与附加门槛
- WORKSPACE/wiki/patterns 作为 BASE 种子经验（5 条演化出偏 pattern）
- 新增 ARCHIVE/ 归档规范与回归落点（运行时产物不入库）
- 归档 v0.1 自举提案至 governance/