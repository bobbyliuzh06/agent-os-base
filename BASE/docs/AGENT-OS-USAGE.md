# Agent-OS 自举底座使用说明（自动生成）
> 生成时间：**2026-09-13 15:58:51**　基础提交：`ecaff30`　Git 状态：**yes**
> 已有标签：`v0.2.0`、`v0.3.0-base`、`v0.4.0-base`、`v0.4.1-sandbox-live`、`v0.4.2-sandbox-hard`、`v0.4.3-cleanbase`、`v0.4.4-audit`、`v0.4.5`、`v0.4.6`、`v0.5.0`

本文件由 `BASE/scripts/generate_usage_doc.py` 按当前代码/调度/运行状态生成。**请勿手改**；底座演进后重跑生成器即可同步。

## 0. 这是什么
Agent-OS 是“自提案+自巡检”的 agent 底座，不是自动改生产的机器人。定时调度跑：提案→门禁→后处理→清理→观察→建议→健康/看板。它只产出可审查的改进提案与观察数据；是否落地代码/规则，需要人工同意并满足四道合并锁（观察期全部关闭）。

## 1. 当前部署（自动采集）
- 根目录：`D:\agent-os`
- 规则/常量：`BASE/META/`（含 `merge_whitelist.json`）；硬规则在 `BASE/` 下 GATE/宪法类文件
- 脚本：`BASE/scripts/`
  - `cleanup_dispatch.py` (1564 B)
  - `cli_common.py` (2051 B)
  - `cmd_doctor.py` (2535 B)
  - `cmd_evolve.py` (1672 B)
  - `cmd_init.py` (5819 B)
  - `cmd_new.py` (3382 B)
  - `cmd_publish.py` (5396 B)
  - `cmd_quickcard.py` (2605 B)
  - `cmd_run.py` (3983 B)
  - `cmd_sync.py` (923 B)
  - `cmd_watch.py` (1669 B)
  - `code_sandbox_run.py` (17753 B)
  - `code_sandbox_scan.py` (16786 B)
  - `config_loader.py` (5759 B)
  - `dashboard.py` (3711 B)
  - `dispatch_wrapper.bat` (5284 B)
  - `evolve_dispatch.py` (11907 B)
  - `gate_review_adapter.py` (8766 B)
  - `gate_review_dispatch.py` (10666 B)
  - `generate_usage_doc.py` (13541 B)
  - `health_check.py` (5433 B)
  - `merge_advisor.py` (5685 B)
  - `merge_apply.py` (4697 B)
  - `nightly_check.bat` (1678 B)
  - `observe_report.py` (7379 B)
  - `postprocess_dispatch.py` (2778 B)
  - `posture_check.py` (8295 B)
  - `project_dual_review.py` (5599 B)
  - `project_feedback_truth.py` (5566 B)
  - `project_pain_rollup.py` (4601 B)
  - `project_regression.py` (7149 B)
  - `project_selfcheck.py` (4744 B)
  - `project_site_gen.py` (20223 B)
  - `project_site_publish.py` (3514 B)
  - `project_strategy_pool.py` (8725 B)
  - `project_verify_pains.py` (4849 B)
  - `proposer.py` (11329 B)
  - `readiness_eval.py` (8121 B)
  - `redact.py` (741 B)
  - `release_add_tasks_submodule.py` (1710 B)
  - `release_split_base.py` (1716 B)
  - `sandbox_sitecustomize.py` (3097 B)
  - `scan_hardcoded.py` (3860 B)
  - `supplychain_check.py` (2165 B)
  - `sync_manager.py` (10561 B)
  - `tag_audit.bat` (65 B)
  - `tag_audit.py` (10046 B)
  - `task_engine.py` (6750 B)
  - `task_lock.py` (1444 B)
  - `watch_check.bat` (931 B)
- 提案/门禁：`PENDING/`
- 运行数据（通常 gitignore）：`BASE/regression-runs/`（dispatch.log、observe.csv、dashboard.txt、readiness.md、watch.log）

### 1.1 计划任务
| 任务 | 运行命令 | 下次运行 | 上次结果 | 状态 |
|---|---|---|---|---|
| AgentOS_EvolveDispatch | ? | ? | ? | ? |
| AgentOS_WatchCheck | ? | ? | ? | ? |

### 1.2 最近观察
```
==================================================
agent-os evolve dashboard  2026-09-13 15:33:05
STATUS: healthy
- observe rows (total / last 24): 20 / 20
- all-rc-zero in window: True
- unknown gates (window): 0
- alerts_total (window sum): 0
- decision distribution (all): {'manual': 20}
- accept+low candidates (all): 0
- reasoning disk MB: 0.1
- current git_sha: dba3d34
==================================================
```
observe.csv 最新行：`2026-09-13 15:32:55,1,1,0,0,0,0,0,0,manual,,dba3d34`

### 1.3 待处理门禁
- `_smoke-propose-2026-09-12.gate.txt` 状态=reject 风险=medium

### 1.4 合并锁（只读报告）
- 自动合并开关(.auto_merge_on)：**关闭**
- 回归全绿标志(all_probe_green.flag)：**关闭**
- 人工ack(merge_acks/*.ack.json)：**关闭**
- 白名单 `allow_paths`：`[]`

## 2. 它会自己常驻自进化吗
会，但限定范围：调度只做“提案+自检”，不自动改 BASE 硬规则，未开四锁不自动合并。流程：
```
propose(PENDING/*.propose.*)
 -> gate(PENDING/*.gate.txt：STATUS/RISK)
 -> postprocess/cleanup/observe(observe.csv+git_sha)
 -> advice(merge_advice.md，仅 dry-run)
 -> health+dashboard(STATUS: healthy/watch/alert)
apply = .auto_merge_on 且 白名单 且 all_probe_green.flag 且 merge_acks/*.ack.json
```

## 3. 有具体需求怎么用（建议独立工作区）
1. 不要在 `D:\agent-os/BASE` 内直接写业务代码。
2. 按第4节取一版底座复制到新项目工作区。
3. 新工作区放需求卡 `REQ-*.md`（第6节模板）+ 输入 + 输出目录。
4. 用 dsh 以新工作区为 cwd 启动，先让它读 REQ 与底座 GATE 再提案。
5. 只看提案/门禁；仅 accept+low 可进入合并，且必须四锁全开。
6. 原 agent-os 只做底座演化；项目工作区自带 git，不回推 agent-os。

## 4. 获取最新版本（具体路径）
```powershell
git -C "D:\agent-os" tag -l                  # 列标签，如 v0.3.0-base
git -C "D:\agent-os" log --oneline -5        # 查提交，如 d33ff63/471999a/31790b7
git -C "D:\agent-os" rev-parse v0.3.0-base^0 # 核对锚点提交
git -C "D:\agent-os" archive v0.3.0-base | tar -x -C "D:/my-project/agent-base"  # 只读导出
```
物理复制：取 `BASE/META/`、`BASE/scripts/`、`PENDING/`（可选），新工作区单独 `git init`。
发版规则：仅 annotated tag（如 `v0.x.0-base`）对外；用户 checkout 标签到新分支，不移动已发标签。

## 5. 日常只读巡检
```powershell
& "D:\agent-os\BASE\scripts\watch_check.bat"   # 四段：调度/看板/readiness/git
python "D:\agent-os\BASE\scripts\readiness_eval.py"  # 写 readiness.md，不碰开关
python "D:\agent-os\BASE\scripts\generate_usage_doc.py"  # 重生成本文件
```
判读：Last Result=0 且 STATUS healthy 且 readiness 非 BLOCK 即正常；alert/BLOCK 查 dispatch.log 对应运行块；修复后重设 `BASE/regression-runs/.obs_baseline_ts` 再观察。

## 6. 需求卡模板（初始尽量写全）
```markdown
# REQ-<项目>-<序号>
- 版本基线：<如 v0.3.0-base / 提交 471999a>
- 目标：<一句话业务结果+可量化验收，如把X转Y报告、错误率<Z>
- 范围：必做 / 不做 / 后续
- 输入：<路径、格式、表结构、权限>
- 输出：<路径、格式、命名、量级>
- 验收：功能 / 质量(rc=0、无unknown、回归全绿、人工抽检) / 性能成本
- 约束：技术栈环境 / 安全(不写明文密钥) / 合规(审计日志)
- 风险与回滚：失败点+保留旧版+还原方案
- 是否允许改底座规则：是/否（是→走提案/门禁/人工ack，不在业务工作区直改BASE）
- 自动化程度：全人工 / 半自动(仅出草案) / 自动(仅白名单+四锁)
- 观察周期：如跑3轮，看 dashboard+observe 再决定是否合并
```

## 7. 就绪度与何时讨论自动合并
```
# readiness evaluation 2026-09-13 08:00:01
- verdict: **WAIT**
- advice: 存在未满足条件；BLOCK 表示需先修复故障并重置基线，WAIT 表示需继续观察或由人工补充配置。

## checks
- [PASS] observe_rounds: got=7 expect=6
- [PASS] recent_rc_zero: got=True expect=True
- [PASS] recent_unknown_zero: got=True expect=True
- [PASS] recent_alerts_zero: got=True expect=True
- [FAIL] real_accept_low_candidate: got=0 expect=1
- [FAIL] whitelist_nonempty: got=0 expect=1
- [PASS] auto_merge_switch: got=0 expect=0
- [PASS] all_probe_green_exists: got=0 expect=0
- [PASS] human_ack_present: got=0 expect=0
- [PASS] dashboard_healthy: got=healthy expect=healthy

## gate scan
- _smoke-propose-2026-09-12.gate.txt status=reject risk=medium real=False

## observe summary
- total_after_baseline=7 recent_window=6
- current_git_sha=16bebbe
```
全部条件（只读评估）：基线后≥6轮、近期 rc/unknown/alerts 全0、出现非 `_` 前缀的 accept+low 门禁、白名单 allow_paths 非空。READy 只是建议；仍须四锁全开并先 dry-run。

## 8. 初学者清单
1. 确认 dsh 可用、API Key 已配置（从系统/环境变量取，不写死）。
2. 跑 watch_check.bat，两任务 Ready、Last Result 0。
3. 新任务进复制出来的工作区，不碰 agent-os/BASE。
4. 写 REQ 卡，让 harness 先读 REQ+GATE 再写代码。
5. 看 `PENDING/*.gate.txt`：仅 accept+low 可合并。
6. 真要开合并：建 `.auto_merge_on`、填白名单路径、出 `all_probe_green.flag`、放 `merge_acks/*.ack.json`，先 `merge_advisor.py` dry-run 再 `merge_apply.py`。
7. 不手改 dispatch_wrapper.bat 阶段顺序；观察期不删 regression-runs 日志。
8. 底座任何改动后重跑本生成器，文档与代码同步。

## 9. 排障
| 现象 | 可能原因 | 处理 |
|---|---|---|
| Evolve 上次结果非0 | 某阶段失败/环境异常 | 看 dispatch.log 当次运行块；修复；重设基线 |
| dashboard STATUS=alert | rc非0/unknown/alerts | 查 observe.csv alerts_total 与运行块；不自动合并 |
| 前置 health ABORT 跳过提案/门禁 | bin.js或Key不可达/脚本缺失 | health_check.py 报告硬失败；恢复环境；wrapper 故意退出1 |
| readiness 卡在观察轮数 | 基线后<6轮 | 等约24小时（4小时×6）；勿手动改条件 |
| 同类故障连出3轮 | 系统性问题 | 停 AgentOS_EvolveDispatch，人工排查；不自动改BASE规则 |

## 10. 版本化与自进化说明
本文档由活系统生成，随底座一起演进。14 阶段调度（含 5a-6f 的 Project 层阶段）/脚本/调度/合并策略/就绪条件有变动，改生成器字段后重跑；对外变更另打 annotated tag。工具层提交与规则层提交分开，不改写已发布历史。

