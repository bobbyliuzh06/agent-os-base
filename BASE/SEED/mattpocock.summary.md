# Seed: mattpocock/skills — 工程师工作流抽象

> 来源：https://github.com/mattpocock/skills （SKILL.md 可组合技能目录）
> 定位：**优秀工程师的影子**。此处仅取其**通用认知骨架**，剥离"写代码"语境，作为首批可替换假设。

## 原始形态（软件语境）

- `grill-me` / `grill-with-docs`：通过盘问建立需求共识 → 产出 `CONTEXT.md`
- `tdd`：红绿重构，先写失败测试再实现
- `diagnose`：复现 → 最小化 → 假设 → 插桩 → 修复
- `triage`：失败分类
- `to-prd` / `to-issues`：拆垂直切片，打 HITL/AFK 标签
- `improve-codebase-architecture`：架构重构
- `ADR`：记录难逆转架构决策
- `.out-of-scope`：记录"不做什么"
- git guardrails / pre-commit

## 抽象为通用能力（底座实际使用层）

| 通用骨架 | 抽象含义 | 适用角色 |
|---|---|---|
| grill（需求质询） | 任务开始前澄清目标、边界、成功标准、假设 | 任何角色 |
| 可验证拆解（红绿/issue） | 先定义可验证成功标准，再执行，再据反馈修正 | 任何角色 |
| 根因诊断（diagnose） | 现象 → 复现 → 最小化 → 假设 → 验证 | 运维/分析/客服 |
| 决策记录（ADR） | 记录不可逆决定及备选与被否决理由 | 管理/架构 |
| 范围外清单 | 明确"不做什么"，限制自作主张 | 任何角色 |
| 护栏（guardrails） | 敏感操作前置检查 | 任何角色 |

## 作为种子的姿态

- ✅ 提供**初始技能集**与**工作流程模板**
- ❌ 不设为不可修改
- ❌ 不强加"工程师人格"——非软件项目应重写为领域等价物（如 TDD → "先定义验收判据"）
- 自举后由 WikiSkill 式演化循环（raw/wiki/skills/gate）逐步被项目经验覆盖、改写
