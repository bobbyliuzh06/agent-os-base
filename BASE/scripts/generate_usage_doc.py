#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 AGENT-OS-USAGE.md；默认中文，--lang en 出英文。重跑即与当前代码/调度/状态同步。"""
import os, sys, subprocess, glob, re, json, argparse
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _load, apply_root_arg
sys.argv = apply_root_arg()
_C = _load()

BASE = str(_C.root)
SCRIPTS = str(_C.scripts_dir)
META = str(_C.meta_dir)
DOCS = str(_C.docs_dir)
PENDING = str(_C.pending)
REG = str(_C.regression)
OUT = os.path.join(DOCS, "AGENT-OS-USAGE.md")

def sh(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        return p.stdout.strip(), p.returncode
    except Exception as e:
        return str(e), 1

def read_text(p):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""

def first_match(text, *pats):
    for pat in pats:
        m = re.search(pat, text, re.S)
        if m:
            return m.group(1).strip()
    return ""

def field(txt, *keys):
    for k in keys:
        for sep in (":", "："):
            m = re.search(re.escape(k) + r"\s*" + re.escape(sep) + r"\s*(.+)", txt)
            if m:
                return m.group(1).strip()
    return "?"

def sched(name):
    out, _ = sh('schtasks /Query /TN %s /V /FO LIST' % name)
    return {
        "run": field(out, "Task To Run", "任务运行", "操作", "运行"),
        "next": field(out, "Next Run Time", "下次运行时间", "下一运行时间"),
        "last": field(out, "Last Result", "上次结果", "最近结果"),
        "status": field(out, "Status", "状态"),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="zh")
    args = ap.parse_args()
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    L = args.lang.lower()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    A = []
    def a(s=""): A.append(s)

    head, _ = sh('git -C "%s" log -1 --format=%%H' % BASE)
    short = head[:7] if head else "na"
    tags_out, _ = sh('git -C "%s" tag -l' % BASE)
    tags = [t for t in tags_out.splitlines() if t.strip()]
    status_out, _ = sh('git -C "%s" status --porcelain' % BASE)
    dirty = "yes" if status_out.strip() else "clean"

    script_files = sorted(glob.glob(os.path.join(SCRIPTS, "*.py")) + glob.glob(os.path.join(SCRIPTS, "*.bat")))
    script_rows = ["- `%s` (%d B)" % (os.path.basename(sf), os.path.getsize(sf)) for sf in script_files]

    ev = sched("AgentOS_EvolveDispatch"); wk = sched("AgentOS_WatchCheck")
    obs = read_text(os.path.join(REG, "observe.csv")).splitlines()
    last_obs = obs[-1] if obs else ""
    dashboard = read_text(os.path.join(REG, "dashboard.txt")).strip()
    readiness = read_text(os.path.join(REG, "readiness.md")).strip()
    gates = sorted(glob.glob(os.path.join(PENDING, "*.gate.txt")))
    gate_rows = []
    for g in gates:
        t = read_text(g)
        st = first_match(t, r"GATE_STATUS\s*[:=]\s*(\S+)", r"STATUS\s*[:=]\s*(\S+)")
        rk = first_match(t, r"GATE_RISK\s*[:=]\s*(\S+)", r"RISK\s*[:=]\s*(\S+)")
        gate_rows.append("- `%s` 状态=%s 风险=%s" % (os.path.basename(g), st or "unknown", rk or "unknown"))
    locks = {
        "自动合并开关(.auto_merge_on)": os.path.isfile(os.path.join(META, ".auto_merge_on")),
        "回归全绿标志(all_probe_green.flag)": os.path.isfile(os.path.join(REG, "all_probe_green.flag")),
        "人工ack(merge_acks/*.ack.json)": bool(glob.glob(os.path.join(REG, "merge_acks", "*.ack.json"))),
    }
    wlp = os.path.join(META, "merge_whitelist.json"); wl = {}
    if os.path.isfile(wlp):
        try: wl = json.loads(read_text(wlp))
        except Exception: pass

    if L != "en":
        a("# Agent-OS 自举底座使用说明（自动生成）")
        a("> 生成时间：**%s**　基础提交：`%s`　Git 状态：**%s**" % (now, short, dirty))
        if tags: a("> 已有标签：" + "、".join("`%s`" % t for t in tags))
        a("")
        a("本文件由 `BASE/scripts/generate_usage_doc.py` 按当前代码/调度/运行状态生成。**请勿手改**；底座演进后重跑生成器即可同步。")
        a("")
        a("## 0. 这是什么")
        a("Agent-OS 是“自提案+自巡检”的 agent 底座，不是自动改生产的机器人。定时调度跑：提案→门禁→后处理→清理→观察→建议→健康/看板。它只产出可审查的改进提案与观察数据；是否落地代码/规则，需要人工同意并满足四道合并锁（观察期全部关闭）。")
        a("")
        a("## 1. 当前部署（自动采集）")
        a("- 根目录：`%s`" % _C.root)
        a("- 规则/常量：`BASE/META/`（含 `merge_whitelist.json`）；硬规则在 `BASE/` 下 GATE/宪法类文件")
        a("- 脚本：`BASE/scripts/`")
        a("  " + "\n  ".join(script_rows))
        a("- 提案/门禁：`PENDING/`")
        a("- 运行数据（通常 gitignore）：`BASE/regression-runs/`（dispatch.log、observe.csv、dashboard.txt、readiness.md、watch.log）")
        a("")
        a("### 1.1 计划任务")
        a("| 任务 | 运行命令 | 下次运行 | 上次结果 | 状态 |")
        a("|---|---|---|---|---|")
        a("| AgentOS_EvolveDispatch | %s | %s | %s | %s |" % (ev["run"], ev["next"], ev["last"], ev["status"]))
        a("| AgentOS_WatchCheck | %s | %s | %s | %s |" % (wk["run"], wk["next"], wk["last"], wk["status"]))
        a("")
        a("### 1.2 最近观察")
        a("```")
        a(dashboard if dashboard else "（暂无 dashboard.txt）")
        a("```")
        a("observe.csv 最新行：`%s`" % last_obs)
        a("")
        a("### 1.3 待处理门禁")
        a("\n".join(gate_rows) if gate_rows else "- （无）")
        a("")
        a("### 1.4 合并锁（只读报告）")
        for k,v in locks.items(): a("- %s：**%s**" % (k, "开启" if v else "关闭"))
        a("- 白名单 `allow_paths`：`%s`" % wl.get("allow_paths", []))
        a("")
        a("## 2. 它会自己常驻自进化吗")
        a("会，但限定范围：调度只做“提案+自检”，不自动改 BASE 硬规则，未开四锁不自动合并。流程：")
        a("```")
        a("propose(PENDING/*.propose.*)")
        a(" -> gate(PENDING/*.gate.txt：STATUS/RISK)")
        a(" -> postprocess/cleanup/observe(observe.csv+git_sha)")
        a(" -> advice(merge_advice.md，仅 dry-run)")
        a(" -> health+dashboard(STATUS: healthy/watch/alert)")
        a("apply = .auto_merge_on 且 白名单 且 all_probe_green.flag 且 merge_acks/*.ack.json")
        a("```")
        a("")
        a("## 3. 有具体需求怎么用（建议独立工作区）")
        a("1. 不要在 `%s/BASE` 内直接写业务代码。" % _C.root)
        a("2. 按第4节取一版底座复制到新项目工作区。")
        a("3. 新工作区放需求卡 `REQ-*.md`（第6节模板）+ 输入 + 输出目录。")
        a("4. 用 dsh 以新工作区为 cwd 启动，先让它读 REQ 与底座 GATE 再提案。")
        a("5. 只看提案/门禁；仅 accept+low 可进入合并，且必须四锁全开。")
        a("6. 原 agent-os 只做底座演化；项目工作区自带 git，不回推 agent-os。")
        a("")
        a("## 4. 获取最新版本（具体路径）")
        a("```powershell")
        a('git -C "%s" tag -l                  # 列标签，如 v0.3.0-base' % _C.root)
        a('git -C "%s" log --oneline -5        # 查提交，如 d33ff63/471999a/31790b7' % _C.root)
        a('git -C "%s" rev-parse v0.3.0-base^0 # 核对锚点提交' % _C.root)
        a('git -C "%s" archive v0.3.0-base | tar -x -C "D:/my-project/agent-base"  # 只读导出' % _C.root)
        a("```")
        a("物理复制：取 `BASE/META/`、`BASE/scripts/`、`PENDING/`（可选），新工作区单独 `git init`。")
        a("发版规则：仅 annotated tag（如 `v0.x.0-base`）对外；用户 checkout 标签到新分支，不移动已发标签。")
        a("")
        a("## 5. 日常只读巡检")
        a("```powershell")
        a('& "%s\\watch_check.bat"   # 四段：调度/看板/readiness/git' % _C.scripts_dir)
        a('python "%s\\readiness_eval.py"  # 写 readiness.md，不碰开关' % _C.scripts_dir)
        a('python "%s\\generate_usage_doc.py"  # 重生成本文件' % _C.scripts_dir)
        a("```")
        a("判读：Last Result=0 且 STATUS healthy 且 readiness 非 BLOCK 即正常；alert/BLOCK 查 dispatch.log 对应运行块；修复后重设 `BASE/regression-runs/.obs_baseline_ts` 再观察。")
        a("")
        a("## 6. 需求卡模板（初始尽量写全）")
        a("```markdown")
        a("# REQ-<项目>-<序号>")
        a("- 版本基线：<如 v0.3.0-base / 提交 471999a>")
        a("- 目标：<一句话业务结果+可量化验收，如把X转Y报告、错误率<Z>")
        a("- 范围：必做 / 不做 / 后续")
        a("- 输入：<路径、格式、表结构、权限>")
        a("- 输出：<路径、格式、命名、量级>")
        a("- 验收：功能 / 质量(rc=0、无unknown、回归全绿、人工抽检) / 性能成本")
        a("- 约束：技术栈环境 / 安全(不写明文密钥) / 合规(审计日志)")
        a("- 风险与回滚：失败点+保留旧版+还原方案")
        a("- 是否允许改底座规则：是/否（是→走提案/门禁/人工ack，不在业务工作区直改BASE）")
        a("- 自动化程度：全人工 / 半自动(仅出草案) / 自动(仅白名单+四锁)")
        a("- 观察周期：如跑3轮，看 dashboard+observe 再决定是否合并")
        a("```")
        a("")
        a("## 7. 就绪度与何时讨论自动合并")
        a("```")
        a(readiness if readiness else "（先跑 readiness_eval.py 生成 readiness.md）")
        a("```")
        a("全部条件（只读评估）：基线后≥6轮、近期 rc/unknown/alerts 全0、出现非 `_` 前缀的 accept+low 门禁、白名单 allow_paths 非空。READy 只是建议；仍须四锁全开并先 dry-run。")
        a("")
        a("## 8. 初学者清单")
        a("1. 确认 dsh 可用、API Key 已配置（从系统/环境变量取，不写死）。")
        a("2. 跑 watch_check.bat，两任务 Ready、Last Result 0。")
        a("3. 新任务进复制出来的工作区，不碰 agent-os/BASE。")
        a("4. 写 REQ 卡，让 harness 先读 REQ+GATE 再写代码。")
        a("5. 看 `PENDING/*.gate.txt`：仅 accept+low 可合并。")
        a("6. 真要开合并：建 `.auto_merge_on`、填白名单路径、出 `all_probe_green.flag`、放 `merge_acks/*.ack.json`，先 `merge_advisor.py` dry-run 再 `merge_apply.py`。")
        a("7. 不手改 dispatch_wrapper.bat 阶段顺序；观察期不删 regression-runs 日志。")
        a("8. 底座任何改动后重跑本生成器，文档与代码同步。")
        a("")
        a("## 9. 排障")
        a("| 现象 | 可能原因 | 处理 |")
        a("|---|---|---|")
        a("| Evolve 上次结果非0 | 某阶段失败/环境异常 | 看 dispatch.log 当次运行块；修复；重设基线 |")
        a("| dashboard STATUS=alert | rc非0/unknown/alerts | 查 observe.csv alerts_total 与运行块；不自动合并 |")
        a("| 前置 health ABORT 跳过提案/门禁 | bin.js或Key不可达/脚本缺失 | health_check.py 报告硬失败；恢复环境；wrapper 故意退出1 |")
        a("| readiness 卡在观察轮数 | 基线后<6轮 | 等约24小时（4小时×6）；勿手动改条件 |")
        a("| 同类故障连出3轮 | 系统性问题 | 停 AgentOS_EvolveDispatch，人工排查；不自动改BASE规则 |")
        a("")
        a("## 10. 版本化与自进化说明")
        a("本文档由活系统生成，随底座一起演进。14 阶段调度（含 5a-6f 的 Project 层阶段）/脚本/调度/合并策略/就绪条件有变动，改生成器字段后重跑；对外变更另打 annotated tag。工具层提交与规则层提交分开，不改写已发布历史。")
        a("")
    else:
        a("# Agent-OS Usage Guide (auto-generated)")
        a("> Generated: %s  base: %s  git: %s" % (now, short, dirty))
        if tags: a("> Tags: " + ", ".join(tags))
        a(""); a("This file is generated by generate_usage_doc.py. Rerun after evolution.")
        a("## Schedule"); a("Evolve: %s next=%s last=%s status=%s" % (ev["run"], ev["next"], ev["last"], ev["status"]))
        a("Watch: %s next=%s last=%s status=%s" % (wk["run"], wk["next"], wk["last"], wk["status"]))
        a("## Scripts"); a("  " + "\n  ".join(script_rows))
        a("## Locks"); 
        for k,v in locks.items(): a("- %s: %s" % (k, "ON" if v else "OFF"))
        a("- whitelist allow_paths: %s" % wl.get("allow_paths", []))
        a("## Dashboard"); a("```"); a(dashboard); a("```")
        a("## Readiness"); a("```"); a(readiness); a("```")

    os.makedirs(DOCS, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(A) + "\n")
    print("GENERATED %s lang=%s base=%s dirty=%s scripts=%d" % (OUT, L, short, dirty, len(script_rows)))
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("generate_usage_doc error: " + str(e)); sys.exit(1)
