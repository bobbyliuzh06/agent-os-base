# Seed: WikiSkill — 经验编译管线

> 来源：https://arxiv.org/abs/2608.27454 （Google Research + Virginia Tech）
> 定位：**让 agent 越干越聪明**的经验→知识→技能演化机制。这是 BASE 演化循环的**主引擎参考**。

## 三层结构（永不混用）

- `raw/`：**不可变**执行轨迹（prompt、推理、工具调用、结果、失败、人工反馈）
- `wiki/`：持续累积的 Markdown 知识
  - `patterns/`：失败模式 / 成功策略（现象、根因、适用条件、应对、证据链）
  - `logs.md`：按迭代记录发现
  - `skill-impact.md`：技能提案 diff / 验证分 / accept-reject / 回滚原因
- `skills/`：**当前生效**技能（SKILL.md + PURPOSE.md，注明由哪些 wiki pattern 演化而来）

## 四角色循环

1. **Inference Agent**：用当前 `skills/` 执行（**只加载 skill，不加载 wiki**）
2. **Wiki Maintainer**：读 raw + 现有 wiki → 蒸馏 pattern → 更新 `wiki/patterns/`
3. **Skill Proposer**：读 wiki + 近期 raw → 提 skill 增删改 → 写 PURPOSE 说明演化依据
4. **Gate**：留出验证集 / 历史回归集，跑 before/after，未达标则**回滚 skill**（wiki 不回滚，保留经验）

## 关键原则（BASE 已采纳）

- **执行期隔离**：推理 agent 不直连 wiki，避免"抄答案 → 轨迹退化 → 后续演化变差"
- **wiki 持久、不随 skill 回滚**：失败经验永远保留
- **留出验证 / 回滚**：所有修改可证伪、可撤销
- ablation 参考：持久 wiki 是主引擎（论文实验约 63.7% → 48.7% 当移除）

## 作为种子的姿态

- ✅ 提供**演化循环骨架**（raw→wiki→skill→gate→rollback）
- ✅ 提供"执行与经验隔离"这一关键设计
- ❌ 不预设具体 pattern 内容、验证集构成 —— 由项目经验填充
