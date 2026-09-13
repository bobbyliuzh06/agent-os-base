# -*- coding: utf-8 -*-
"""project_selfcheck.py —— 七段管线自体检（BASE 组件草案，案例③管线接管）。
挂载于 dispatch 第 5a 步（observe 之后）：
1) BASE/scripts 哈希快照 + 与上次快照漂移对比（changed/removed 视为不健康，added 为正常演化）；
2) 健康信号：dispatch.log 尾部 rc、observe.csv 最近行、dashboard.txt、nightly 台账、计划任务查询；
3) 记录到 P3 Project 的 memory/selfchecks.jsonl + BASE/regression-runs/project-selfcheck.log。
只读于 BASE 机制（快照与记录除外）；退出码 0=健康，1=告警（不中断调度）。"""
import hashlib, json, os, pathlib, subprocess, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import get_root

ROOT = get_root()
SCRIPTS = ROOT / "BASE" / "scripts"
REGR = ROOT / "BASE" / "regression-runs"
PROJECT = pathlib.Path(os.environ.get(
    "AGENT_OS_PROJECT_P3", str(ROOT / "tasks" / "project-layer-p3-20260912")))
MEM = PROJECT / "task-evolve" / "memory"
MEM.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def snapshot():
    return {p.name: sha256(p) for p in sorted(SCRIPTS.iterdir())
            if p.suffix in (".py", ".bat", ".ps1")}

def health_signals():
    sig = {}
    log = REGR / "dispatch.log"
    if log.exists():
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-14:]
        rc_lines = [l for l in tail if "rc=" in l]
        sig["dispatch_log"] = {"rc_all_zero": all("rc=0" in l for l in rc_lines),
                               "git_sha": None, "last_lines": tail[-2:]}
    else:
        sig["dispatch_log"] = None
    csv = REGR / "observe.csv"
    if csv.exists():
        lines = [l for l in csv.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
        sig["observe_last"] = lines[-1] if lines else None
    else:
        sig["observe_last"] = None
    dash = REGR / "dashboard.txt"
    sig["dashboard"] = {"exists": dash.exists(), "size": dash.stat().st_size if dash.exists() else 0}
    nights = sorted(REGR.glob("nightly-*.json"))
    sig["nightly_latest"] = nights[-1].name if nights else None
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-ScheduledTask | Where-Object {$_.TaskName -match 'agent|dispatch|dsh'} | Select-Object -ExpandProperty TaskName"],
                           capture_output=True, text=True, timeout=30)
        names = [x.strip() for x in r.stdout.splitlines() if x.strip()]
        sig["scheduled_task"] = {"found": names, "rc": r.returncode,
                                 "err": r.stderr.strip()[:120] or None}
    except Exception as e:
        sig["scheduled_task"] = {"found": None, "error": str(e)[:120]}
    return sig

def main():
    cur = snapshot()
    prev_path = MEM / "snapshot-current.json"
    prev = json.loads(prev_path.read_text(encoding="utf-8")) if prev_path.exists() else {}
    drift = {"changed": sorted([k for k in cur if k in prev and cur[k] != prev[k]]),
             "added": sorted([k for k in cur if k not in prev]),
             "removed": sorted([k for k in prev if k not in cur])}
    sig = health_signals()
    healthy = True
    issues = []
    if sig.get("dispatch_log") and sig["dispatch_log"].get("rc_all_zero") is False:
        healthy = False
        issues.append("dispatch 有阶段非 rc=0")
    if drift["changed"] or drift["removed"]:
        healthy = False
        issues.append("漂移: changed=%s removed=%s" % (drift["changed"], drift["removed"]))
    prev_path.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
    rec = {"check_id": NOW, "scripts_count": len(cur), "drift": drift, "healthy": healthy,
           "issues": issues, "signals": sig}
    with open(MEM / "selfchecks.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open(REGR / "project-selfcheck.log", "a", encoding="utf-8") as f:
        f.write("[%s] scripts=%d changed=%d added=%d removed=%d healthy=%s issues=%s\n" % (
            NOW, len(cur), len(drift["changed"]), len(drift["added"]), len(drift["removed"]),
            healthy, "; ".join(issues) or "none"))
    print("PROJECT_SELFCHECK scripts=%d changed=%s added=%s removed=%s healthy=%s issues=%s" % (
        len(cur), drift["changed"], drift["added"], drift["removed"], healthy, issues or "无"))
    return 0 if healthy else 1

if __name__ == "__main__":
    sys.exit(main())
