# -*- coding: utf-8 -*-
"""project_dual_review.py —— 独立复核人（BASE 组件草案，独立性补强·LLM+确定性回退）。
挂载于 dispatch 第 6b 步（advice 之前），带节流：仅当 P1 痛点台账存在晚于上次复核的
新事件时才执行（4h 调度不空转不刷屏）；对新增事件做独立审计：
角色分离（独立审计员语义）、只允许基于事实记录判断、短输出（P-1 教训）。
记录：P3 memory/reviews.jsonl + BASE/regression-runs/project-review.log。
verdict=disagree/concern → 幂等登记新痛点待人工裁决。
AGENT_OS_DRY=1 时记录写到脚本所在目录。"""
import json, os, pathlib, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import get_root
from proposer import deepseek_propose

ROOT = get_root()
P1 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P1", str(ROOT / "tasks" / "project-layer-p1-20260912" / "task-evolve")))
P3 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P3", str(ROOT / "tasks" / "project-layer-p3-20260912" / "task-evolve")))
PAINS = P1 / "memory" / "pains.jsonl"
DEC = P1 / "memory" / "decisions.jsonl"
REVIEWS = P3 / "memory" / "reviews.jsonl"
REGR = ROOT / "BASE" / "regression-runs"
DRY = os.environ.get("AGENT_OS_DRY") == "1"
OUT_DIR = pathlib.Path(__file__).parent if DRY else P3 / "memory"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def read_jsonl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []

def main():
    pains = read_jsonl(PAINS)
    reviews = read_jsonl(REVIEWS)
    last_t = max((r.get("reviewed_at", "") for r in reviews), default="")
    new_events = [e for e in pains if (e.get("t") or "") > last_t]
    if not new_events:
        print("PROJECT_DUAL_REVIEW skip: no new pain events since %s" % (last_t or "beginning"))
        return 0
    dec_ids = [d.get("id") for d in read_jsonl(DEC)]
    facts = [{"id": e.get("id"), "t": e.get("t"), "event": e.get("event"),
              "evidence": (e.get("evidence") or "")[:150],
              "action": (e.get("action") or "")[:100],
              "root_cause": (e.get("root_cause") or "")[:100]} for e in new_events]
    facts_txt = json.dumps({"new_events": facts, "decision_ids": dec_ids[-20:]}, ensure_ascii=False)
    prompt = ("你是独立审计员，与提议/执行角色无关。只允许基于下面的事实记录判断，"
              "不得补充未经记录的事实。审查新增痛点事件的证据链自洽性。\n事实记录：\n" + facts_txt +
              "\n只输出极短 JSON（<300字）：{\"verdict\":\"agree|concern|disagree\","
              "\"issues\":[\"一句话，最多3条\"],\"alternative_framings\":[\"一句话，最多2条\"]}")
    try:
        # model 级独立：复核人用 deepseek-v4-pro（提议者用 flash，不同模型）
        r = deepseek_propose(prompt, "project-independent-review", model="deepseek-v4-pro", thinking=False)
        live = True
    except Exception as e:
        live = False
        issues = []
        for ev in new_events:
            if not ev.get("evidence"):
                issues.append("事件 %s 缺 evidence" % ev.get("id"))
        r = {"verdict": "concern" if issues else "agree",
             "issues": issues or ["(fallback) 无结构问题"],
             "alternative_framings": ["(fallback) LLM 复核失败: %s" % str(e)[:60]]}
    verdict = str(r.get("verdict", "agree")).lower()
    rec = {"review_id": "REV-%s" % NOW, "reviewed_at": NOW, "subject": "new pain events",
           "reviewer": "independent-auditor-llm" if live else "deterministic-fallback",
           "live": live, "verdict": verdict, "issues": r.get("issues") or [],
           "alternative_framings": r.get("alternative_framings") or [],
           "new_event_count": len(new_events)}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "reviews.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if not DRY:
        with open(REGR / "project-review.log", "a", encoding="utf-8") as f:
            f.write("[%s] events=%d live=%s verdict=%s issues=%d\n" % (
                NOW, len(new_events), live, verdict, len(rec["issues"])))
    if verdict in ("disagree", "concern") and not DRY:
        existing = read_jsonl(PAINS)
        symptom = "独立复核 concern/disagree: %s" % "; ".join(rec["issues"])[:100]
        if not any(x.get("status") == "open" and x.get("source") == "independent-reviewer"
                   and x.get("symptom", "").startswith(symptom[:50]) for x in existing):
            rec_pain = {"id": "P-%d" % (len({x["id"] for x in existing}) + 1), "t": NOW, "event": "open",
                        "source": "independent-reviewer", "project": "project-layer-p1",
                        "symptom": symptom, "frequency": 1, "impact": "medium",
                        "root_cause": "独立复核提出保留意见", "action": "逐条回应并记录（人工裁决）",
                        "expected_metric": "复核意见逐条回应", "status": "open"}
            with open(PAINS, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec_pain, ensure_ascii=False) + "\n")
    print("PROJECT_DUAL_REVIEW events=%d live=%s verdict=%s issues=%s" % (
        len(new_events), live, verdict, rec["issues"] or "无"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
