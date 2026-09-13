# -*- coding: utf-8 -*-
"""project_strategy_pool.py —— 事件驱动策略池（BASE 组件草案，滚动窗口候选方案）。
挂载于 dispatch 第 6d 步，带数据哈希节流：仅当数据文件相对上次运行发生变化时才重赛
（事件驱动节奏：新数据到达→自动竞赛；固定数据→诚实跳过，不做空转演示）。
重赛流程（walk-forward）：6 策略在训练段(前 13 决策周)竞赛→冠军在验证段(后 13 周)样本外
验证→结果写 P1 audit/pool-auto-<ts>.json + decisions.jsonl 决策(eval) →
仅当冠军更换时更新 P-2（幂等，防 4h 调度重复登记）。
输出状态：P1 audit/pool-state.json（数据哈希+上次运行+冠军）。
AGENT_OS_DRY=1：全部输出写到脚本所在目录。"""
import csv, hashlib, json, os, pathlib, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml
from config_loader import get_root
from gate_review_adapter import review as gate_review

ROOT = get_root()
P1 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P1", str(ROOT / "tasks" / "project-layer-p1-20260912" / "task-evolve")))
P0 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P0", str(ROOT / "tasks" / "project-layer-p0-20260912" / "task-evolve")))
REGR = ROOT / "BASE" / "regression-runs"
DRY = os.environ.get("AGENT_OS_DRY") == "1"
OUT_DIR = pathlib.Path(__file__).parent if DRY else P1 / "audit"
STATE = OUT_DIR / "pool-state.json"
DATA = P1 / "data" / "cn300-synth-v2-2020-2026.csv"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
W_CAP, CASH_MIN, TURN_CAP, DD_CAP = 0.20, 0.10, 0.30, -0.15
assets = ["A0%d" % i for i in range(1, 10)] + ["A10"]

def load_weeks():
    rows = list(csv.DictReader(open(DATA, encoding="utf-8")))
    weeks, cur, buf = [], None, []
    for r in rows:
        w = datetime.strptime(r["date"], "%Y-%m-%d").strftime("%Y-%U")
        if w != cur:
            if buf:
                weeks.append(buf[-1])
            cur, buf = w, [r]
        else:
            buf.append(r)
    if buf:
        weeks.append(buf[-1])
    return weeks[-28:]

weeks = load_weeks()

def px(w, a):
    return float(weeks[w][a])

def mom(w, a, lb=4):
    return px(w, a) / px(w - lb, a) - 1 if w >= lb else 0.0

def vol4w(w, a):
    if w < 4:
        return 0.0
    r = [px(t, a) / px(t - 1, a) - 1 for t in range(w - 4, w + 1)]
    m = sum(r) / len(r)
    return (sum((x - m) ** 2 for x in r) / len(r)) ** 0.5

def s1(w):
    t = sorted(assets, key=lambda a: mom(w, a, 4), reverse=True)[:5]
    return {a: 0.16 for a in t}

def s2(w):
    t = sorted(assets, key=lambda a: mom(w, a, 2), reverse=True)[:5]
    return {a: 0.16 for a in t}

def s3(w):
    t = sorted(assets, key=lambda a: mom(w, a, 8), reverse=True)[:5]
    return {a: 0.16 for a in t}

def s4(w):
    t = sorted(assets, key=lambda a: mom(w, a, 4), reverse=True)[:3]
    return {a: 0.28 for a in t}

def s5(w):
    low = sorted(assets, key=lambda a: vol4w(w, a))[:8]
    t = sorted(low, key=lambda a: mom(w, a, 4), reverse=True)[:5]
    return {a: 0.16 for a in t}

def s6(w):
    return {a: 0.09 for a in assets}

STRATS = [("S-1", "top5-mom4w", s1), ("S-2", "top5-mom2w", s2), ("S-3", "top5-mom8w", s3),
          ("S-4", "top3-mom4w", s4), ("S-5", "vol8-mom4w", s5), ("S-6", "equal-weight", s6)]

def enforce(target, prev):
    out = {a: min(target.get(a, 0.0), W_CAP) for a in assets}
    inv = sum(out.values())
    if inv > 1 - CASH_MIN:
        k = (1 - CASH_MIN) / inv
        out = {a: v * k for a, v in out.items()}
    turn = sum(abs(out[a] - prev.get(a, 0.0)) for a in assets) / 2
    if turn > TURN_CAP:
        k = TURN_CAP / turn
        out = {a: prev.get(a, 0.0) + (out[a] - prev.get(a, 0.0)) * k for a in assets}
    return out

def run_window(fn, w0, w1):
    weights = {a: 0.0 for a in assets}
    value, peak, gates = 1.0, 1.0, 0
    max_dd = 0.0
    for w in range(w0, w1):
        new_w = enforce(fn(w), weights)
        prop = {"summary": "策略池(自动) 周期%d" % w,
                "scope_in": ["tasks/project-layer-p1-20260912"],
                "scope_out": ["BASE", "真钱交易"],
                "deliverables": ["tasks/project-layer-p1-20260912/task-evolve/audit/pool-state.json"],
                "steps": ["walk-forward"], "risks": ["合成数据"],
                "rollback": ["恢复上周权重"], "acceptance": ["章程约束"],
                "base_change_required": False, "tool_calls": []}
        g = gate_review(prop, "project-layer-p1-20260912")
        if g["gate"] == "accept":
            gates += 1
        realized = {a: px(w + 1, a) / px(w, a) - 1 for a in assets}
        value *= (1 + sum(weights[a] * realized[a] for a in assets))
        peak = max(peak, value)
        max_dd = min(max_dd, value / peak - 1)
        weights = new_w
    idx_value = 1.0
    for w in range(w0, w1):
        idx_value *= px(w + 1, "IDX") / px(w, "IDX")
    return {"final": round(value, 6), "idx": round(idx_value, 6),
            "excess": round(value - idx_value, 6), "max_dd": round(max_dd, 6),
            "gates": gates, "total": w1 - w0}

def main():
    data_hash = hashlib.sha256(DATA.read_bytes()).hexdigest()[:16]
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    if state.get("data_sha256") == data_hash:
        print("PROJECT_STRATEGY_POOL skip: data unchanged (%s), champion=%s since %s" % (
            data_hash, state.get("champion"), state.get("last_run")))
        return 0
    TRAIN, VALID = (1, 14), (14, 27)
    train_res = {sid: run_window(fn, *TRAIN) for sid, _, fn in STRATS}
    champ_id = max(train_res, key=lambda k: train_res[k]["excess"])
    valid_res = run_window(dict((sid, fn) for sid, _, fn in STRATS)[champ_id], *VALID)
    results = [{"id": sid, "name": name, "train_excess": train_res[sid]["excess"],
                "train_dd": train_res[sid]["max_dd"]} for sid, name, _ in STRATS]
    out = {"run_at": NOW, "data_sha256": data_hash, "champion": champ_id,
           "champion_valid_excess": valid_res["excess"], "champion_valid_dd": valid_res["max_dd"],
           "train_results": results, "note": "合成数据 v2，walk-forward 13/13"}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / ("pool-auto-%s%s.json" % (NOW.replace(":", "").replace("-", ""), ".dry" if DRY else ""))).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    STATE.write_text(json.dumps({"data_sha256": data_hash, "last_run": NOW, "champion": champ_id},
                                ensure_ascii=False, indent=2), encoding="utf-8")
    if not DRY:
        with open(REGR / "strategy-pool.log", "a", encoding="utf-8") as f:
            f.write("[%s] data=%s champion=%s valid_excess=%.4f\n" % (
                NOW, data_hash, champ_id, valid_res["excess"]))
        dec = {"id": "D-POOLAUTO-%s" % NOW, "run_id": "pool-auto", "action": "strategy-pool-event",
               "pain_addressed": "P-2", "data_sha256": data_hash,
               "eval": {"expected": {"champion_valid_excess_gt_0": True},
                        "actual": {"champion": champ_id, "valid_excess": valid_res["excess"],
                                   "gt0": valid_res["excess"] > 0},
                        "delta": {"gt0": valid_res["excess"] > 0}},
               "champion_changed": state.get("champion") not in (None, champ_id)}
        with open(P1 / "memory" / "decisions.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(dec, ensure_ascii=False) + "\n")
        if dec["champion_changed"]:
            with open(P1 / "memory" / "pains.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": "P-2", "t": NOW, "event": "progress",
                                    "source": "strategy-pool-auto", "project": "project-layer-p1",
                                    "symptom": "组合跑输基准（v1 数据）", "frequency": 2, "impact": "high",
                                    "root_cause": "已修生成器；策略池事件驱动重赛",
                                    "action": "冠军=%s（验证段超额 %+.4f）" % (champ_id, valid_res["excess"]),
                                    "expected_metric": "连续 2 周期跑赢基准", "status": "open",
                                    "evidence": "pool-auto-%s.json" % NOW.replace(":", "").replace("-", "")},
                                   ensure_ascii=False) + "\n")
    print("PROJECT_STRATEGY_POOL ran: champion=%s valid_excess=%+.4f dry=%s" % (
        champ_id, valid_res["excess"], DRY))
    return 0

if __name__ == "__main__":
    sys.exit(main())
