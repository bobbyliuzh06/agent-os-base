# -*- coding: utf-8 -*-
"""project_feedback_truth.py —— 真实世界反馈真值采集（BASE 组件草案，P-8 行动）。
挂载于 dispatch 第 6e 步，带节流（上次轮询 <1 小时则跳过）：
gh CLI 只读轮询 Issues 计数 + Release 下载计数 → 写入 P2 truth/feedback.json（快照）
+ truth/feedback-log.jsonl（append 真值历史）+ regression-runs/feedback-truth.log。
gh 不可用/失败如实记录 degraded，不伪造。AGENT_OS_DRY=1：输出写到脚本所在目录。"""
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
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=60)
    return r

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
    rec["feedback_status"] = ("available" if (rec.get("open_issues") is not None and rec.get("releases") is not None)
                              else "degraded")
    return rec

def main():
    snap = TRUTH / "feedback.json"
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
    TRUTH.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(TRUTH / "feedback-log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if not DRY:
        with open(REGR / "feedback-truth.log", "a", encoding="utf-8") as f:
            f.write("[%s] issues=%s status=%s downloads_v050=%s\n" % (
                rec["polled_at"], rec.get("open_issues"), rec["feedback_status"],
                next((r["downloads"] for r in rec.get("releases") or [] if r["tag"] == "v0.5.0"), "?")))
    print("PROJECT_FEEDBACK_TRUTH issues=%s status=%s dry=%s" % (
        rec.get("open_issues"), rec["feedback_status"], DRY))
    return 0

if __name__ == "__main__":
    sys.exit(main())
