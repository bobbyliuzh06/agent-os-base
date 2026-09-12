# BASE 目录结构提案（v0.1 自举候选）

> 定性：v0.1 自举候选，不宣称"已通用"。本提案独立设计后与现 BASE（按 README 描述）逐条对照，
> 差异清单见文末。所有差异只写入本文件与 PROPOSAL，由人工合并；本设计轮不直接改 BASE。

## 一、四子系统总览

| 子系统 | 职责 | 主要载体 | 访问者 |
|---|---|---|---|
| raw（采集层） | 不可变执行轨迹 | `WORKSPACE/raw/` | 维护/提案角色 |
| wiki（经验层） | 蒸馏后的模式与演化记录 | `WORKSPACE/wiki/` | 维护/提案角色 |
| skills（执行层） | 当前生效技能 | `BASE/skills/`（生效）+ `WORKSPACE/skills/`（候选） | 执行 agent 只读生效层 |
| gate（门控层） | 回填审查与回归验证 | `META/GATE.md`+`REGRESSION.md`+`gate-review`+`governance/`+`ARCHIVE/`+`regression-runs/` | 门控角色 + 人工 |

四者关系：raw →（trace-distill）→ wiki →（propose-gate）→ PROPOSAL →（gate-review + 回归）→ BASE/skills 与规则面更新 →（回填打 tag）→ 下一轮。wiki 不回滚；skills 可回滚；gate 规则本身走宪法修正案流程。

## 二、完整目录结构与文件清单

```
BASE/
├── AGENTS.md                  # 会话启动规则（每次注入；铁律所在，修改走提案）
├── README.md                  # 底座说明 + BOOT 指令 + 自举任务书
├── new_task.sh                # 复制 BASE → PROJECTS/<name>
├── .gitignore
├── META/                      # 规则面（gate 子系统的条文部分）
│   ├── CONSTITUTION.md        # 元宪法（修改走宪法修正案，保留旧 tag）
│   ├── GATE.md                # 回填门控标准（通用门槛 + A/B/C 分级 + 自动拒绝项）
│   ├── REGRESSION.md          # 跨领域回归探针集（六维打分 + 第六维独立验证，见回归设计）
│   ├── CHANGELOG.md           # 每次回填的变更记录
│   └── VERSION                # 当前版本号（回填时更新）
├── SEED/                      # 可替换种子（mattpocock/wikiskill/scaling/dialogue 摘要）
├── TEMPLATES/                 # 空白模板：CONTEXT / PATTERN / SKILL / PROPOSAL
├── skills/                    # 当前生效技能（skills 子系统的执行面）
│   ├── constitution/
│   │   ├── SKILL.md           # 元原则守护（不可绕过）
│   │   └── PURPOSE.md         # 演化依据：由哪些 pattern/项目经验演化而来（本轮补的缺失项）
│   ├── route-intake/
│   │   ├── SKILL.md           # 任务路由 + 适配判断
│   │   └── PURPOSE.md
│   ├── trace-distill/
│   │   ├── SKILL.md           # 轨迹蒸馏（维护/提案角色专用）
│   │   └── PURPOSE.md
│   ├── propose-gate/
│   │   ├── SKILL.md           # 提案 + 自检（不自审）
│   │   └── PURPOSE.md
│   └── gate-review/           # 本轮新增：独立门控执行者
│       ├── SKILL.md           # 跑探针、记 before/after、出 accept/reject/archive
│       └── PURPOSE.md
├── governance/                # 已接受 PROPOSAL 归档（回填时 cp 入内）
├── ARCHIVE/                   # 被拒提案归档（v0.1.1 已有；本轮补充归档规范，见差异 #1）
├── regression-runs/           # 本轮新增：BASE 各版本的回归基线记录（每版一份，供"不降回归"比对）
└── （项目侧，由 new_task.sh 从 BASE 复制生成）
    WORKSPACE/
    ├── CONTEXT.md             # 项目统一语言（目标/边界/成功标准/不做什么/术语表）
    ├── raw/                   # 不可变轨迹：<时间戳>-<任务slug>.md
    │                          #   字段：prompt/技能版本戳/工具调用/中间结果/失败记录/最终输出/人工反馈
    ├── wiki/                  # 经验库（维护/提案角色专用，执行 agent 不直读）
    │   ├── patterns/          # 失败模式/成功策略（按 TEMPLATES/PATTERN.md）
    │   ├── logs.md            # 按迭代记录发现
    │   └── skill-impact.md    # 技能提案 diff / 验证分 / accept-reject / 回滚原因
    ├── skills/                # 项目侧技能提案候选（经门控后才并入 BASE/skills/）
    ├── regression-runs/       # 本轮新增：每轮回归试跑原始记录固定落点（第六维 E1 查验对象）
    └── PROPOSAL.md            # 任务结束汇总提案（人工审核后归档至 BASE/governance/）
```

## 三、各目录职责细则

1. **META/**：规则面。GATE 定义"能不能进"，REGRESSION 定义"进来后如何证明不退化"。两者都是可演化对象，但修改分别走 GATE 级 B/级 C，且必须保留旧 tag。
2. **SEED/**：首批假设，非教义。禁止任何提案把种子设为不可修改项（自动拒绝项）。
3. **TEMPLATES/**：空白件只提供结构，不提供答案；发现模板文案带领域偏见时按 `seed-persona-lock` pattern 改写。
4. **BASE/skills/**：执行 agent 唯一允许加载的技能面。每个技能必须有 PURPOSE.md（wikiskill 种子要求：注明由哪些 wiki pattern 演化而来）——现 BASE 缺失，为本轮发现缺陷之一。
5. **WORKSPACE/raw/**：不可变。缺技能版本戳的轨迹允许入 raw 但蒸馏降权（字段规范见 trace-distill）。
6. **WORKSPACE/wiki/**：经验面。不随 skill 回滚；删除/合并 pattern 无需门控但须记 logs.md。
7. **WORKSPACE/regression-runs/** 与 **BASE/regression-runs/**：前者是每轮门控试跑的工作落点，后者是 BASE 每版发布时的基线归档。gate-review 的裁定必须引用前者产物。
8. **governance/** 与 **ARCHIVE/**：接受的提案与拒绝的提案都永久留存——拒绝 ≠ 删除，pattern 保留供再评估（GATE 原文）。

## 四、与现 BASE（按 README 描述）的差异清单

| # | 差异 | 理由 |
|---|---|---|
| 1 | ARCHIVE/ 归档规则明确化 | GATE 规定拒绝≠删除，v0.1.1 已有 ARCHIVE/ 目录，本轮补充归档规范（命名/保留期限/复活流程）至 ARCHIVE/README.md |
| 2 | 新增 `gate-review` 技能 | 补齐 WikiSkill 四角色中缺失的 Gate 执行者（pattern `gate-rubber-stamp`） |
| 3 | 新增 `skills/<name>/PURPOSE.md` | wikiskill 种子明确要求"注明由哪些 wiki pattern 演化而来"，现 skills/ 缺失 |
| 4 | 新增 `BASE/regression-runs/` 与 `WORKSPACE/regression-runs/` | "不降回归"条款的操作化落点；第六维 E1 机械查验对象 |
| 5 | 明确 raw 轨迹字段规范（技能版本戳/失败记录/人工反馈） | 第六维 E1"留痕完整性"的可查依据 |
| 6 | `skills/` 下现有 3 技能升级为改进版（route-intake/trace-distill/propose-gate） | 见各 SKILL.md"目的"节所列改进点 |
| 7 | `constitution` 技能本轮不改动 | 改它本身要走宪法修正案流程；本轮只经提案呈现机制，体现机制自指约束 |

> 注：差异对照基于本工作区 README.md 对 BASE 的描述；真实 BASE 目录如有出入，以真实 BASE 为准，合并时由人工复核。

## 五、回滚方案

- 本提案被拒 → 全部产物留在 `WORKSPACE/`，不合并即完整回滚；
- 部分接受 → 按差异清单逐项合并（各差异互相独立，可单独取舍）；
- 合并后发现问题 → git 旧 tag 回滚；`wiki/patterns/` 与 `ARCHIVE/` 不回滚（经验保留）。

## 六、冷启动声明

本结构未经真实跨领域项目验证，定性为 v0.1 自举候选；"通用"须由后续真实项目回填证明（回补期限见 PROPOSAL.md）。
