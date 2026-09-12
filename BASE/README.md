# agent-os / BASE — 通用演化底座 v0.1.0

> **固定路径复制最新版本即可在独立会话随时开始任何需求/任务。**

## 这是什么

一个**自演化 agent 底座**：把"能力生成器"本身作为第一个被设计、被演化的对象。
任何具体需求都从 BASE 复制出独立工作区，跑完按门控回填，下一轮复制即获得累积遗产。

## 目录结构

```
BASE/
├── AGENTS.md              # 会话启动规则（每次注入）
├── README.md
├── META/
│   ├── CONSTITUTION.md    # 元宪法（可演化，需修正案流程）
│   ├── GATE.md            # 回填门控标准
│   ├── REGRESSION.md      # 跨领域回归探针集
│   ├── CHANGELOG.md
│   └── VERSION
├── SEED/                  # 三个资料摘要 + 对话蒸馏（可替换种子）
├── TEMPLATES/             # CONTEXT / PATTERN / SKILL / PROPOSAL 空白件
├── skills/                # 当前生效技能（constitution/route-intake/trace-distill/propose-gate）
├── governance/            # 归档已接受的 PROPOSAL
├── new_task.sh            # 复制 BASE -> ../PROJECTS/<name>
├── .gitignore
└── WORKSPACE/             # （项目侧生成）raw/ wiki/ skills/ + PROPOSAL.md
```

## 三层理念（来自 WikiSkill 种子）

- `raw/` 不可变轨迹 → `wiki/patterns/` 经验 → `skills/` 当前生效技能
- 循环：采集 → 蒸馏 → 提案 → 门控 → 回滚（wiki 不回滚）
- **执行 agent 只加载 skills，不直读 wiki**（避免抄答案导致轨迹退化）

## 日常用法

```bash
cd agent-os/BASE
./new_task.sh 我的新需求
# 在 DeepSeek Harness 选择 ../PROJECTS/我的新需求 作工作区 -> 新会话
# 首条粘贴 BOOT 指令（见下方）
```

### BOOT 指令（粘贴到新会话首条）

```
请按本工作区 AGENTS.md、META/CONSTITUTION.md、META/GATE.md 工作。
先执行 skills/route-intake 对以下需求做任务路由，给出计划等我确认后再动手。
需求：<在此写你的需求>

<若任务是自举 v0.1，用下方任务书覆盖>
```

## 自举 v0.1 任务书（首次运行用）

> 复制到 `PROJECTS/bootstrap-v0.1/` 根，作为本轮需求。

```
当前任务是底座自举 v0.1：基于 SEED 摘要设计"通用演化底座"的最小可用交付物，包括
1) 目录与 raw/wiki/skills/gate 流程（可参考但不可照搬现有 BASE，应独立设计后对比）
2) 通用能力六维定义与验收（任务理解/可验证执行/失败诊断/边界控制/跨领域迁移/演化规程）
3) 新任务 route 机制（何时单/多agent、何时提底座自身修改）
4) 一个非软件探针验收集（制造业供应链中断预演、合规问卷、内容运营复盘各一例）
所有产物放 WORKSPACE/，不直改 BASE；结束输出 PROPOSAL.md，按 GATE.md 自检。
未动文件前先给实施计划等我确认。
```

## 回填流程（项目结束后）

1. 审核项目内 `PROPOSAL.md` 是否通过 GATE
2. `cp PROPOSAL.md BASE/governance/`
3. 合并技能/模板/经验 → 更新 META/VERSION + CHANGELOG
4. `cd BASE && git add -A && git commit && git tag v<new>`
5. 用 `META/REGRESSION.md` 探针做回归，确认不降分

## 铁律（不可绕过）

- 高危操作（删除/外发/付费/凭据/生产写）一律 HITL
- 对 BASE 的修改只能经 PROPOSAL + GATE，禁止会话内"自升级"
- 种子内容（含本文件）均非不可修改；宪法修改需双倍验证 + 保留旧 tag

## 版本

当前 v0.1.0，详见 META/CHANGELOG.md。
