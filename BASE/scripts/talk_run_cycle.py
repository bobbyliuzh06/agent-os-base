# -*- coding: utf-8 -*-
"""talk_run_cycle.py —— talk --run 的第一周期执行器（底座健康真值）。
真实真值：仓库同步 / 站点 HTTP 200 / 最近调度 24h 内。
写入目标项目的 truth/check-*.json + decisions.jsonl（append-only）。
诚实标注：这是走通链路的默认第一周期；目标专属真值由 charter.truth_sources 声明后接入。"""
import io, json, pathlib, re, subprocess, sys, urllib.request
from datetime import datetime, timezone

# 注意：本模块被 cmd_talk.py import 复用，不得在此包装 sys.stdout（避免二次包装导致缓冲区关闭）

def run_first_cycle(task, goal):
    task = pathlib.Path(task)
    for d in ("truth", "memory"):
        (task / d).mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    NOW = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1) 仓库同步（ls-remote 只读）
    try:
        r = subprocess.run(["git", "ls-remote", "origin", "main"], capture_output=True, text=True, timeout=30)
        remote = r.stdout.split()[0] if r.returncode == 0 else None
        local = subprocess.run(["git", "-C", r"D:/agent-os", "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout.strip()
        repo = {"local": local, "remote": remote, "synced": remote == local}
    except Exception as e:
        repo = {"synced": None, "error": str(e)[:80]}
    # 2) 站点
    try:
        site = {"status": urllib.request.urlopen(
            "https://bobbyliuzh06.github.io/agent-os-base/", timeout=30).status, "alive": True}
    except Exception as e:
        site = {"status": None, "alive": False, "error": str(e)[:80]}
    # 3) 调度新鲜度
    log = pathlib.Path(r"D:/agent-os/BASE/regression-runs/dispatch.log")
    if log.exists():
        m = re.findall(r"\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2})\] dispatch end",
                       log.read_text(encoding="utf-8", errors="replace")[-2000:])
        if m:
            last = datetime.strptime(m[-1], "%Y-%m-%d %H:%M")
            dispatch = {"age_hours": round((now - last).total_seconds() / 3600, 1),
                        "recent": (now - last).total_seconds() <= 86400}
        else:
            dispatch = {"recent": None, "error": "no end marker"}
    else:
        dispatch = {"recent": None, "error": "no log"}

    checks = [("repo-synced", repo.get("synced")), ("site-alive", site.get("alive")),
              ("dispatch-recent", dispatch.get("recent"))]
    healthy = all(v is True for _, v in checks)
    truth = {"checked_at": NOW, "goal": goal, "source": "real-git+http+log",
             "note": "第一周期默认走底座健康真值（链路验证）；目标专属真值由 charter.truth_sources 声明后接入",
             "status": "healthy" if healthy else "degraded",
             "repo": repo, "site": site, "dispatch": dispatch}
    fn = "check-%s.json" % NOW.replace(":", "").replace("-", "")
    (task / "truth" / fn).write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(task / "memory" / "decisions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"id": "D-FIRST-%s" % NOW, "action": "first-cycle",
                            "checked_at": NOW, "healthy": healthy,
                            "eval": {"expected": {"all_healthy": True}, "actual": dict(checks),
                                     "delta": {"all_healthy": healthy}},
                            "truth_file": "truth/%s" % fn}, ensure_ascii=False) + "\n")
    for name, v in checks:
        print("  %-18s %s" % (name, "PASS" if v is True else ("FAIL" if v is False else "UNKNOWN")))
    print("TALK --run 第一周期：healthy=%s | 真值=%s（可核验路径）" % (healthy, task / "truth" / fn))
    return healthy
