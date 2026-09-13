# -*- coding: utf-8 -*-
"""project_regression.py —— 过程回归集（BASE 组件草案，DIRECTION 优先级 5）。
挂载于 dispatch 第 7a 步（post-health 之前）：保护过程不变量，防机制退化。
I-1 门禁确定性 / I-2 记忆 append-only / I-3 痛点闭合证据 / I-4 章程评估域 /
I-5 台账行唯一 / I-6 站点真值溯源 / I-7 站点迭代 append-only / I-8 BASE 写入永拒。
输出：BASE/regression-runs/project-regression.json（覆盖写=最新）+ project-regression.log（追加）。
黄金基线存于 P3 memory/regression-golden.json（首次运行记录，之后对照）。
AGENT_OS_DRY=1：报告与基线写到脚本所在目录（草案预演）。"""
import hashlib, json, os, pathlib, re, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml
from config_loader import get_root
from gate_review_adapter import review as gate_review

ROOT = get_root()
P0 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P0", str(ROOT / "tasks" / "project-layer-p0-20260912" / "task-evolve")))
P1 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P1", str(ROOT / "tasks" / "project-layer-p1-20260912" / "task-evolve")))
P2 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P2", str(ROOT / "tasks" / "project-layer-p2-20260912" / "task-evolve")))
P3 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P3", str(ROOT / "tasks" / "project-layer-p3-20260912" / "task-evolve")))
REGR = ROOT / "BASE" / "regression-runs"
DRY = os.environ.get("AGENT_OS_DRY") == "1"
OUT_DIR = pathlib.Path(__file__).parent if DRY else REGR
GOLDEN = pathlib.Path(__file__).parent / "regression-golden.dry.json" if DRY else P3 / "memory" / "regression-golden.json"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def h_lines(path, n):
    p = pathlib.Path(path)
    if not p.exists():
        return None
    lines = p.read_text(encoding="utf-8").splitlines()
    return hashlib.sha256("\n".join(lines[:n]).encode("utf-8")).hexdigest()

def main():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8")) if GOLDEN.exists() else {}
    results = []
    fixed = [
        {"summary": "REGRESSION-I1-A 正常任务提案", "scope_in": ["tasks/x-20260913"],
         "scope_out": ["BASE"], "deliverables": ["tasks/x-20260913/task-evolve/out.json"],
         "steps": ["a"], "risks": [], "rollback": [], "acceptance": [], "base_change_required": False, "tool_calls": []},
        {"summary": "REGRESSION-I1-B 尝试写 BASE", "scope_in": ["BASE"],
         "scope_out": [], "deliverables": ["BASE/scripts/x.py"],
         "steps": ["a"], "risks": [], "rollback": [], "acceptance": [], "base_change_required": True, "tool_calls": []},
    ]
    verdicts = [gate_review(p, "project-layer-p3-20260912")["gate"] for p in fixed]
    if "i1_verdicts" not in golden:
        golden["i1_verdicts"] = verdicts
    results.append({"id": "I-1", "name": "gate-determinism", "pass": verdicts == golden["i1_verdicts"], "detail": verdicts})
    results.append({"id": "I-8", "name": "BASE-write-rejected", "pass": verdicts[1] == "reject", "detail": verdicts[1]})

    for fid, path in [("decisions", P1 / "memory" / "decisions.jsonl"),
                      ("hypotheses", P1 / "memory" / "hypotheses.jsonl"),
                      ("pains", P1 / "memory" / "pains.jsonl")]:
        k = "i2_" + fid
        h = h_lines(path, 10)
        if h is None:
            results.append({"id": "I-2", "name": "append-only(%s)" % fid, "pass": False, "detail": "missing"})
            continue
        if k not in golden:
            golden[k] = h
        results.append({"id": "I-2", "name": "append-only(%s)" % fid, "pass": h == golden[k], "detail": h[:12]})

    pains = [json.loads(l) for l in (P1 / "memory" / "pains.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    bad = [r for r in pains if r.get("event") == "resolved" and not r.get("evidence")]
    results.append({"id": "I-3", "name": "pain-closure-evidence", "pass": not bad, "detail": "bad=%d" % len(bad)})

    ok4 = []
    for cp in [P0 / "charter.yaml", P2 / "charter.yaml", P3 / "charter.yaml"]:
        d = yaml.safe_load(cp.read_text(encoding="utf-8")) if cp.exists() else None
        ok4.append(bool(d and d.get("evaluation") and d["evaluation"].get("domain")))
    results.append({"id": "I-4", "name": "charter-eval-domain", "pass": all(ok4), "detail": ok4})

    with_id = [r.get("row_id") for r in pains if r.get("row_id")]
    results.append({"id": "I-5", "name": "ledger-row-unique", "pass": len(with_id) == len(set(with_id)),
                    "detail": "%d rows" % len(with_id)})

    tp = P2 / "site" / "truth.json"
    if tp.exists():
        claims = json.loads(tp.read_text(encoding="utf-8")).get("claims", [])
        results.append({"id": "I-6", "name": "site-truth-hashes", "pass": all(c.get("sha256") for c in claims),
                        "detail": "%d claims" % len(claims)})
    else:
        results.append({"id": "I-6", "name": "site-truth-hashes", "pass": False, "detail": "truth.json missing"})

    k = "i7_iterations"
    h = h_lines(P2 / "memory" / "iterations.jsonl", 3)
    if h is None:
        results.append({"id": "I-7", "name": "site-iter-append-only", "pass": False, "detail": "missing"})
    else:
        if k not in golden:
            golden[k] = h
        results.append({"id": "I-7", "name": "site-iter-append-only", "pass": h == golden[k], "detail": h[:12]})

    # I-9 版本元数据一致（第三方反馈 P-9 P0 项：config.json version 必须与 VERSION 文件一致）
    try:
        cfg = json.loads((ROOT / "BASE" / "META" / "config.json").read_text(encoding="utf-8"))
        ver_file = (ROOT / "BASE" / "META" / "VERSION").read_text(encoding="utf-8").strip()
        cfg_ver = cfg.get("version")
        results.append({"id": "I-9", "name": "version-metadata-consistent",
                        "pass": str(cfg_ver) == ver_file, "detail": "config=%s file=%s" % (cfg_ver, ver_file)})
    except Exception as e:
        results.append({"id": "I-9", "name": "version-metadata-consistent", "pass": False, "detail": str(e)[:60]})

    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(json.dumps(golden, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = sum(1 for r in results if not r["pass"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / ("project-regression%s.json" % (".dry" if DRY else ""))).write_text(
        json.dumps({"run_at": NOW, "dry": DRY, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    if not DRY:
        with open(REGR / "project-regression.log", "a", encoding="utf-8") as f:
            f.write("[%s] checks=%d failed=%d\n" % (NOW, len(results), failed))
    for r in results:
        print("%s %-26s %s %s" % (r["id"], r["name"], "PASS" if r["pass"] else "FAIL", r["detail"]))
    print("PROJECT_REGRESSION %d/%d passed dry=%s" % (len(results) - failed, len(results), DRY))
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
