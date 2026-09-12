# Agent-OS 架构路线图（v0.3 → v0.4）

> 状态：设计冻结（2026-09）。本文件是后续 STEP 的共同契约，任何与本文冲突的代码改动需先更新本文并走提案/门禁。

## 一、设计原则
1. **底座与任务分离**：`base/`（通用规则+工具）只读挂载到每个任务；任务只在其自身目录演化，不回写 base。
2. **分身与专项分层**：
   - 元底座 `base/` + 个人画像 `profile/` = 使用者的“电子分身”（沉淀“你怎么做事”）；
   - `tasks/<task-id>/` = 专项工作区（针对一件事，独立 REQ、数据、产物、任务级演化）。
3. **单一权威底座**：本机只有一份 base，禁止“一个任务复制一份 base”导致分叉冗余。
4. **可发布性**：base 不含密钥、不含运行产物、路径参数化，可从 GitHub 克隆后一行命令部署。
5. **向后兼容**：v0.3 的七阶段调度（dispatch_wrapper）继续运行；v0.4 在其上叠加任务层，不重写。

## 二、目标目录结构（v0.4）
D:/agent-os/
  base/                  # 原 BASE/，通用、可发布
    meta/                # 规则 + config.json + merge_whitelist.json
    scripts/             # 所有 .py/.bat，路径全部参数化
    docs/                # AGENT-OS-USAGE.md / ROADMAP.md / 模板
  profile/               # 个人长期记忆（私有，不发布）：偏好、决策、skills/
    preferences.json
    skills/              # 跨任务提炼的通用技能
  tasks/                 # 专项任务工作区（各自独立）
    registry.json        # 任务注册表
    <task-id>/           # 一个任务一个目录
      REQ.md
      workspace/         # 输入输出数据
      task-evolve/       # 任务级演化记录（提案/门禁/产物）
      config.json        # 任务级配置（挂接哪个 base 版本、调度策略）
  agent-os.cmd           # 统一命令入口（v0.4 新增）
  .env                   # 本地环境（API Key 等，gitignore，不入库）

## 三、配置层级（优先级从低到高）
1. base/meta/config.json        —— 底座默认值
2. profile/preferences.json     —— 个人偏好覆盖
3. tasks/<id>/config.json       —— 任务级覆盖
读取规则：上层覆盖下层；脚本只通过统一函数 `get_config()` 取值，禁止硬编码 D:/agent-os。

## 四、命令入口（v0.4，后续 STEP 逐步实现，本步不实现）
- `agent-os sync`     ：从 GitHub 拉取最新 base（git pull / release 下载）
- `agent-os new`      ：交互式澄清需求 → 生成 tasks/<id>/REQ.md
- `agent-os run <id>` ：在任务工作区执行一次任务（内部复用七阶段思想，但作用于 task-evolve）
- `agent-os watch`    ：查看所有任务健康度（复用现有 watch_check 逻辑）
- `agent-os evolve <id>`：仅对指定任务做专项常驻演化
- `agent-os doctor`   ：扫描重复/孤儿/超大任务，防撞车冗余
- `agent-os archive <id>`：归档已完成任务（提炼通用技能到 profile/skills/）

## 五、防撞车/冗余机制（契约）
1. 单一权威 base：所有任务 Junction/软链指向同一 base，禁止复制。
2. registry.json 去重：new 时检索同名/同标签任务，提示复用。
3. 差异存储：task 只存与 base 的差异（REQ + 自定义脚本 + 产物），不存 base 副本。
4. 单实例锁：task 目录 `.lock`，run/evolve 启动时校验。
5. 命名规范：`<领域>-<目标>-<YYYYMMDD>`，如 sales-q3-analysis-20260912。
6. 任务级 evolve 与 base evolve 完全隔离：前者只写 tasks/<id>/，后者只写 base/（且需人工审核）。

## 六、GitHub 发布前置条件（v0.4 发版前必须完成）
- [ ] 所有脚本路径参数化（无硬编码 D:/agent-os）
- [ ] 移除/隔离所有运行产物（regression-runs、PENDING、watch.log → 全部 .gitignore）
- [ ] base 内无明文密钥；Key 统一从 .env / winreg 读取
- [ ] 提供 agent-os.cmd + 一键初始化脚本（init.bat）
- [ ] 提供 REQ 模板与新手快速卡
- [ ] 打 annotated tag v0.4.0-base 并写 CHANGELOG

## 七、版本节奏
- v0.3.x：仅观察期修复（per-run alert、baseline、readiness、watch），不动结构
- v0.4.0-base：参数化 + 命令入口 + 任务层（本路线图的目标版本）
- v0.5+：远程同步、多机协同、profile 迁移（暂不设计）

## 八、本步边界（STEP23）
- 只写本文档 + 盘点脚本 + config.json 骨架；
- 不实现 sync/new/run/watch/evolve/doctor；
- 不修改 dispatch_wrapper.bat、不改动计划任务；
- 不建 GitHub 仓库、不做 git push。
