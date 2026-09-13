# -*- coding: utf-8 -*-
"""project_pain_rollup.py —— 跨项目全局痛点汇总（BASE 组件草案，开放问题 2 registry 方向）。
挂载于 dispatch 第 6c 步（独立复核之后）：扫描全部 tasks/project-layer-*/…/pains.jsonl，
取每痛点最新状态行，按频率×影响打分排序，附带证据引用可验证性检查。
输出：P3 audit/pain-rollup.json（覆盖写=最新全局视图，供站点渲染与人工总览）+
BASE/regression-runs/pain-rollup.log（追加）。只读扫描，不改任何台账。
AGENT_OS_DRY=1：输出写到脚本所在目录。"""
import hashlib, json, os, pathlib, re, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import get_root

ROOT = get_root()
P3 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P3", str(ROOT / "tasks" / "project-layer-p3-20260912" / "task-evolve")))
REGR = ROOT / "BASE" / "regression-runs"
DRY = os.environ.get("AGENT_OS_DRY") == "1"
OUT_DIR = pathlib.Path(__file__).parent if DRY else P3 / "audit"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

PATH_RE = re.compile(r"(?:tasks|BASE)/[A-Za-z0-9_\-./]+")
RUN_RE = re.compile(r"(?:run|pool|pool-v2|evo|so)-\d{8}T\d{6}Z")
SCORE = {"high": 3, "medium": 2, "low": 1}

def read_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []

def main():
    pains = []
    for pdir in sorted(ROOT.glob("tasks/project-layer-*/task-evolve")):
        pfile = pdir / "memory" / "pains.jsonl"
        if not pfile.exists():
            continue
        project = pdir.parent.name
        rows = read_jsonl(pfile)
        latest = {}
        for r in rows:
            latest[r.get("id")] = r
        dec_text = (pdir / "memory" / "decisions.jsonl").read_text(encoding="utf-8") if (pdir / "memory" / "decisions.jsonl").exists() else ""
        audit_names = {p.name for p in (pdir / "audit").glob("*.json")} if (pdir / "audit").exists() else set()
        for pid, e in latest.items():
            text = (e.get("evidence") or "") + " " + (e.get("action") or "")
            gaps = []
            for cp in set(PATH_RE.findall(text)):
                if cp.startswith(("tasks/", "BASE/")) and not (ROOT / cp).exists():
                    gaps.append("missing:%s" % cp)
            for rid in set(RUN_RE.findall(text)):
                if rid not in dec_text and not any(rid in n for n in audit_names):
                    gaps.append("runid:%s" % rid)
            pains.append({"pain": pid, "project": project, "status": e.get("status"),
                          "event": e.get("event"), "symptom": (e.get("symptom") or "")[:80],
                          "action": (e.get("action") or "")[:80], "impact": e.get("impact"),
                          "frequency": e.get("frequency", 1),
                          "score": (e.get("frequency", 1) or 1) * SCORE.get(e.get("impact"), 1),
                          "evidence_ok": not gaps, "gaps": gaps, "last_t": e.get("t"),
                          "source_file": str(pfile.relative_to(ROOT))})
    pains.sort(key=lambda p: (-p["score"], p["project"], p["pain"]))
    open_count = sum(1 for p in pains if p["status"] == "open")
    rollup = {"rolled_at": NOW, "dry": DRY, "projects": len({p["project"] for p in pains}),
              "total_pains": len(pains), "open": open_count,
              "resolved": sum(1 for p in pains if p["status"] == "resolved"),
              "evidence_gaps": sum(1 for p in pains if not p["evidence_ok"]), "pains": pains}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / ("pain-rollup%s.json" % (".dry" if DRY else ""))
    out.write_text(json.dumps(rollup, ensure_ascii=False, indent=2), encoding="utf-8")
    if not DRY:
        with open(REGR / "pain-rollup.log", "a", encoding="utf-8") as f:
            f.write("[%s] projects=%d pains=%d open=%d resolved=%d gaps=%d\n" % (
                NOW, rollup["projects"], rollup["total_pains"], open_count, rollup["resolved"], rollup["evidence_gaps"]))
    print("PROJECT_PAIN_ROLLUP projects=%d pains=%d open=%d resolved=%d gaps=%d dry=%s -> %s" % (
        rollup["projects"], rollup["total_pains"], open_count, rollup["resolved"], rollup["evidence_gaps"], DRY, out))
    for p in pains:
        print("  %-4s %-24s %-9s score=%-2d %s" % (p["pain"], p["project"], p["status"], p["score"], p["symptom"][:46]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
