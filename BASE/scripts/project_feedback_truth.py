# -*- coding: utf-8 -*-
"""project_feedback_truth.py v2 —— 真实反馈真值采集（加 stars/watchers/forks 真实参与信号）。
挂载于 dispatch 第 6e 步，1h 节流；gh 只读轮询：
Issues 数 / Release 下载数 / stars / watchers / forks → P2 truth/feedback.json + append log。
失败如实 degraded。AGENT_OS_DRY=1：输出写到脚本所在目录。"""
import io, json, os, pathlib, subprocess, sys
from datetime import datetime, timezone, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import get_root

ROOT = get_root()
P2 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P2", str(ROOT / "tasks" / "project-layer-p2-20260912" / "task-evolve")))
REGR = ROOT / "BASE" / "regression-runs"
DRY = os.environ.get("AGENT_OS_DRY") == "1"
TRUTH = pathlib.Path(__file__).parent / "truth-dry" if DRY else P2 / "truth"
NOW = datetime.now(timezone.utc)

def gh(args):
    return subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=60)

def jq_int(jq_expr):
    r = gh(["api", "repos/bobbyliuzh06/agent-os-base", "--jq", jq_expr])
    if r.returncode == 0:
        try:
            return int(r.stdout.strip())
        except ValueError:
            return None
    return None

def poll():
    rec = {"polled_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "source": "github-api (gh cli, read-only)"}
    r1 = gh(["api", "repos/bobbyliuzh06/agent-os-base/issues", "--jq", "length"])
    if r1.returncode == 0:
        try:
            rec["open_issues"] = int(r1.stdout.strip())
        except ValueError:
            rec["open_issues"] = None
            rec["issues_error"] = "parse: %s" % r1.stdout[:60]
    else:
        rec["open_issues"] = None
        rec["issues_error"] = "gh exit %s: %s" % (r1.returncode, (r1.stderr or "")[:120])
    r2 = gh(["api", "repos/bobbyliuzh06/agent-os-base/releases",
             "--jq", "[.[] | {tag: .tag_name, downloads: (.assets[0].download_count // 0)}]"])
    if r2.returncode == 0:
        try:
            rec["releases"] = json.loads(r2.stdout)
        except json.JSONDecodeError:
            rec["releases"] = None
            rec["releases_error"] = "parse: %s" % r2.stdout[:60]
    else:
        rec["releases"] = None
        rec["releases_error"] = "gh exit %s: %s" % (r2.returncode, (r2.stderr or "")[:120])
    rec["stars"] = jq_int(".stargazers_count")
    rec["watchers"] = jq_int(".subscribers_count")
    rec["forks"] = jq_int(".forks_count")
    r3 = gh(["api", "repos/bobbyliuzh06/agent-os-base/traffic/clones",
             "--jq", "{count: .count, uniques: .uniques}"])
    if r3.returncode == 0:
        try:
            rec["clones_14d"] = json.loads(r3.stdout)
        except json.JSONDecodeError:
            rec["clones_14d"] = None
            rec["clones_error"] = "parse"
    else:
        rec["clones_14d"] = None
        rec["clones_error"] = "gh exit %s" % r3.returncode
    ok = rec.get("open_issues") is not None and rec.get("releases") is not None and rec.get("stars") is not None
    rec["feedback_status"] = "available" if ok else "degraded"
    return rec

def delta(prev, cur):
    """环比：关键指标相对上次轮询的变化（反馈本身的时间语义）。"""
    d = {}
    for k in ("open_issues", "stars", "watchers", "forks"):
        if isinstance(prev.get(k), int) and isinstance(cur.get(k), int):
            d[k] = cur[k] - prev[k]
    pv = next((r["downloads"] for r in prev.get("releases") or [] if r["tag"] == "v0.5.0"), None)
    cv = next((r["downloads"] for r in cur.get("releases") or [] if r["tag"] == "v0.5.0"), None)
    if pv is not None and cv is not None:
        d["v050_downloads"] = cv - pv
    return d

def main():
    snap = TRUTH / "feedback.json"
    prev = None
    if not DRY and snap.exists():
        prev = json.loads(snap.read_text(encoding="utf-8"))
        try:
            last = datetime.fromisoformat(prev.get("polled_at", "").replace("Z", "+00:00"))
            if (NOW - last) < timedelta(hours=1):
                print("PROJECT_FEEDBACK_TRUTH skip: last poll %s (<1h)" % prev.get("polled_at"))
                return 0
        except ValueError:
            pass
    rec = poll()
    if prev:
        rec["delta_vs_prev"] = delta(prev, rec)
    TRUTH.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(TRUTH / "feedback-log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if not DRY:
        with open(REGR / "feedback-truth.log", "a", encoding="utf-8") as f:
            f.write("[%s] issues=%s stars=%s watchers=%s forks=%s downloads_v050=%s status=%s\n" % (
                rec["polled_at"], rec.get("open_issues"), rec.get("stars"), rec.get("watchers"),
                rec.get("forks"),
                next((r["downloads"] for r in rec.get("releases") or [] if r["tag"] == "v0.5.0"), "?"),
                rec["feedback_status"]))
    print("PROJECT_FEEDBACK_TRUTH issues=%s stars=%s watchers=%s forks=%s status=%s dry=%s" % (
        rec.get("open_issues"), rec.get("stars"), rec.get("watchers"), rec.get("forks"),
        rec["feedback_status"], DRY))
    return 0

if __name__ == "__main__":
    sys.exit(main())
