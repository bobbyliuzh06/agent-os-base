# Agent-OS v0.4.0-base (candidate rc1) — 2026-09-12

> Status: **本地候选，未发布、未推送**。本文件是 STEP27 评审归档依据，发布前需逐项打勾。

## 相对 v0.3.0-base 的变更
- [x] BASE 全脚本路径参数化（`config_loader.py`，`AGENT_OS_ROOT` + `config.json`），消除硬编码 D:/agent-os
- [x] v0.4 任务层原型：`agent-os.cmd` + `new / watch / doctor / run / evolve / sync`
  - `new`：交互澄清需求，生成 `tasks/<id>/REQ.md`，registry 去重
  - `watch`：多任务健康只读汇总
  - `doctor`：重复/孤儿/超大/锁冲突扫描（防撞车）
  - `run`：单次执行，仅 dry、只写 `tasks/<id>/task-evolve`
  - `evolve`：任务级轻七阶段常驻，绝不回写 BASE
  - `sync`：入站同步原型（默认只读，--apply 需 --yes），git 仅合 BASE 子树、release 仅解包+校验+防穿越，不推送
- [x] 单实例锁 `task_lock.py`；任务级 observe.csv/dashboard 与全局完全隔离
- [x] 配置骨架 `BASE/META/config.json`：`task_layer.enabled=false`、`github.enabled=false`，四合并锁关闭
- [x] 文档：`AGENT-OS-ROADMAP.md`（架构契约）、`AGENT-OS-USAGE.md`（自生成，中文）

## 发布前置条件（来自 ROADMAP 第六节，本候选满足情况）
- [x] 脚本路径参数化（hardcoded_d_drive=0）
- [x] 运行产物隔离（regression-runs/PENDING/tasks 已 ignore）
- [ ] base 内无明文密钥（Key 仅 winreg/env/.env）—— **待人工审计确认**
- [ ] 一键初始化脚本 init.bat —— **未完成，可放 v0.4.1**
- [ ] REQ 模板与新手快速卡 —— **REQ 模板已有，快速卡可放 v0.4.1**
- [ ] 打 annotated tag v0.4.0-base —— **本步仅打轻量 rc1 候选，正式发布前改 annotated**

## 兼容性
- v0.3 的七阶段调度（dispatch_wrapper）继续运行，未被本版本改写
- 两计划任务 AgentOS_EvolveDispatch / AgentOS_WatchCheck 未重建、未改触发频率
- 四合并锁全关，无任何自动 apply

## 已知缺口（留给 v0.4.1 / v0.5）
- `run/evolve` 为 dry 原型，提案/门禁未接入真实 harness（仅结构化占位）
- `sync` 未接真实远程，`github.enabled` 默认 false
- 未做 BASE 子仓化 / tasks submodule 钉版本（26B 延后）
- 无 `archive` 命令、无 profile/skills 自动提炼
- 备份目录位于 base 内，需 ignore 或外移（已在 regression-runs/sync-backup，被忽略）

## 校验记录（STEP27 归档时填写）
- 七阶段全 rc=0：✅（STEP24 完整 wrapper 回归：pre/propose/gate/post/cleanup/observe/advice/posthealth/dashboard 全 0）
- STATUS/READINESS：healthy / WAIT
- hardcoded_d_drive：0
- sync 沙箱（base-only merge / 脏拒 / 非 base 拒）：pass
- task lock 并发：pass（持锁期 LOCKED exit 1，释放后 RUN_DONE）
- 作用域隔离（base_leak_files=0）：✅（STEP25B 断言）
