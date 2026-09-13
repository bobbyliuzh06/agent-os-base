# -*- coding: utf-8 -*-
"""project_verify_pains.py —— 痛点台账独立验证器（BASE 组件草案，独立性补强·确定性）。
挂载于 dispatch 第 6a 步（advice 之前）：
审计 pains.jsonl 中所有 resolved/progress/escalate 行的证据引用：
1) 引用文件路径存在性（tasks/...、BASE/...、*.jsonl 等）；
2) 引用 run_id 在 decisions.jsonl / audit 中存在；
3) 引用哈希片段与文件内容匹配。
输出：BASE/regression-runs/project-pain-verification.json（覆盖写=最新报告）。
失败项 → 幂等登记新痛点（同症状+同来源的 open 痛点存在则跳过，防 4h 调度重复登记）。
AGENT_OS_DRY=1 时报告写到脚本所在目录（草案预演，不写 BASE）。"""
import hashlib, json, os, pathlib, re, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import get_root

ROOT = get_root()
P1 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P1", str(ROOT / "tasks" / "project-layer-p1-20260912" / "task-evolve")))
PAINS = P1 / "memory" / "pains.jsonl"
DEC = P1 / "memory" / "decisions.jsonl"
AUD = P1 / "audit"
REGR = ROOT / "BASE" / "regression-runs"
DRY = os.environ.get("AGENT_OS_DRY") == "1"
OUT = pathlib.Path(__file__).parent if DRY else REGR
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

PATH_RE = re.compile(r"(?:tasks|BASE)/[A-Za-z0-9_\-./]+|[\w\-]+\.(?:jsonl|json|md|py|csv)")
RUN_RE = re.compile(r"(?:run|pool|pool-v2|evo|so)-\d{8}T\d{6}Z")
HASH_RE = re.compile(r"[0-9a-f]{16,}")

def read_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []

def sha256_of_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def main():
    entries = read_jsonl(PAINS)
    dec_text = DEC.read_text(encoding="utf-8") if DEC.exists() else ""
    audit_names = {p.name for p in AUD.glob("*.json")} if AUD.exists() else set()
    report = []
    for e in entries:
        if e.get("event") not in ("resolved", "progress", "escalate"):
            continue
        ev = (e.get("evidence") or "") + " " + (e.get("action") or "")
        gaps = []
        cited_paths = set(PATH_RE.findall(ev))
        for cp in cited_paths:
            if cp.startswith(("tasks/", "BASE/")) and not (ROOT / cp).exists():
                gaps.append("引用文件不存在: %s" % cp)
        for rid in set(RUN_RE.findall(ev)):
            if rid not in dec_text and not any(rid in n for n in audit_names):
                gaps.append("引用 run_id 无记录: %s" % rid)
        for h in set(HASH_RE.findall(ev)):
            if not any(cp.startswith(("tasks/", "BASE/")) and sha256_of_file(ROOT / cp) and h in sha256_of_file(ROOT / cp)
                       for cp in cited_paths):
                gaps.append("哈希片段未匹配: %s" % h[:16])
        verdict = "verified" if not gaps else "failed"
        report.append({"id": e["id"], "event": e.get("event"), "t": e.get("t"), "verdict": verdict,
                       "gaps": gaps, "evidence_excerpt": (e.get("evidence") or "")[:120]})
    out = {"verified_at": NOW, "dry": DRY, "subject": "pains.jsonl 非 open 事件行", "entries": report}
    (OUT / ("project-pain-verification%s.json" % (".dry" if DRY else ""))).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [r for r in report if r["verdict"] == "failed"]
    if failed and not DRY:
        existing = read_jsonl(PAINS)
        for r in failed:
            symptom = "证据引用未通过独立验证: %s(%s) %s" % (r["id"], r["event"], "; ".join(r["gaps"]))
            if any(x.get("status") == "open" and x.get("source") == "independent-verifier"
                   and x.get("symptom", "").startswith(symptom[:60]) for x in existing):
                continue
            rec = {"id": "P-%d" % (len({x["id"] for x in existing}) + 1), "t": NOW, "event": "open",
                   "source": "independent-verifier", "project": "project-layer-p1",
                   "symptom": symptom, "frequency": 1, "impact": "high",
                   "root_cause": "证据引用不完整或过期", "action": "补全引用或修正证据文本（人工裁决）",
                   "expected_metric": "重新验证 verdict=verified", "status": "open"}
            with open(PAINS, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("PROJECT_VERIFY_PAINS rows=%d failed=%d dry=%s -> %s" % (
        len(report), len(failed), DRY, OUT / ("project-pain-verification%s.json" % (".dry" if DRY else ""))))
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
