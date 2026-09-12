#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, csv, glob, json, re
from datetime import datetime

BASE = "D:/agent-os"
PENDING = os.path.join(BASE, "PENDING")
OBS_CSV = os.path.join(BASE, "BASE", "regression-runs", "observe.csv")
BASELINE_TS = os.path.join(BASE, "BASE", "regression-runs", ".obs_baseline_ts")
DASHBOARD_TXT = os.path.join(BASE, "BASE", "regression-runs", "dashboard.txt")
READINESS_MD = os.path.join(BASE, "BASE", "regression-runs", "readiness.md")
WHITELIST = os.path.join(BASE, "BASE", "META", "merge_whitelist.json")
SWITCH = os.path.join(BASE, "BASE", "META", ".auto_merge_on")
GREEN_FLAG = os.path.join(BASE, "BASE", "regression-runs", "all_probe_green.flag")
ACK_DIR = os.path.join(BASE, "BASE", "regression-runs", "merge_acks")

MIN_OBSERVE_ROUNDS = 6

def log(s):
    print(s, flush=True)

def parse_head(path, keys):
    out = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                s = line.strip()
                for k in keys:
                    m = re.match(re.escape(k) + r"\s*[:=]\s*(.+)", s)
                    if m:
                        out[k] = m.group(1).strip()
                        break
                if len(out) >= len(keys):
                    break
    except Exception:
        pass
    return out

def load_json(path, default):
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def read_obs_rows():
    if not os.path.isfile(OBS_CSV):
        return [], []
    with open(OBS_CSV, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    if not lines:
        return [], []
    header = [x.strip() for x in lines[0].split(",")]
    rows = []
    for ln in lines[1:]:
        parts = [x.strip() for x in ln.split(",")]
        if len(parts) < len(header):
            continue
        rows.append(parts)
    return header, rows

def after_baseline(rows):
    if not os.path.isfile(BASELINE_TS):
        return rows
    try:
        bt = open(BASELINE_TS, "r", encoding="utf-8").read().strip()
        base = datetime.strptime(bt, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return rows
    out = []
    for r in rows:
        try:
            rt = datetime.strptime(r[0].strip(), "%Y-%m-%d %H:%M:%S")
        except Exception:
            out.append(r)
            continue
        if rt >= base:
            out.append(r)
    return out

def col(row, header, key, default=""):
    i = header.index(key) if key in header else -1
    if i >= 0 and i < len(row) and row[i] != "":
        return row[i]
    return default

def scan_gates():
    out = []
    for g in sorted(glob.glob(os.path.join(PENDING, "*.gate.txt"))):
        name = os.path.basename(g)
        kv = parse_head(g, ["GATE_STATUS", "STATUS", "GATE_RISK", "RISK"])
        status = (kv.get("GATE_STATUS") or kv.get("STATUS") or "unknown").lower()
        risk = (kv.get("GATE_RISK") or kv.get("RISK") or "unknown").lower()
        is_real = not name.startswith("_")
        out.append({"name": name, "status": status, "risk": risk, "is_real": is_real})
    return out

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    checks = []

    header, rows_all = read_obs_rows()
    rows = after_baseline(rows_all)
    recent = rows[-MIN_OBSERVE_ROUNDS:]

    total_after = len(rows)
    enough_rounds = total_after >= MIN_OBSERVE_ROUNDS
    checks.append(("observe_rounds", total_after, MIN_OBSERVE_ROUNDS, enough_rounds))

    all_rc_ok = False
    unknown_ok = False
    alerts_ok = False
    if recent:
        all_rc_ok = all(
            col(r, header, k, "na") == "0"
            for k in ("propose_rc", "gate_rc", "post_rc", "cleanup_rc")
            for r in recent
        )
        unknown_ok = all(int(col(r, header, "unknown", "0") or 0) == 0 for r in recent)
        alerts_ok = all(int(col(r, header, "alerts_total", "0") or 0) == 0 for r in recent)
    checks.append(("recent_rc_zero", all_rc_ok, True, all_rc_ok))
    checks.append(("recent_unknown_zero", unknown_ok, True, unknown_ok))
    checks.append(("recent_alerts_zero", alerts_ok, True, alerts_ok))

    gates = scan_gates()
    real_candidates = [g for g in gates if g["is_real"] and g["status"] == "accept" and g["risk"] == "low"]
    has_candidate = len(real_candidates) > 0
    checks.append(("real_accept_low_candidate", len(real_candidates), 1, has_candidate))

    wl = load_json(WHITELIST, {})
    allow_paths = [p.replace("/", "\\") for p in wl.get("allow_paths", [])]
    allow_paths_ok = len(allow_paths) > 0
    checks.append(("whitelist_nonempty", len(allow_paths), 1, allow_paths_ok))

    switch_on = os.path.isfile(SWITCH)
    green_on = os.path.isfile(GREEN_FLAG)
    acks = []
    if os.path.isdir(ACK_DIR):
        acks = glob.glob(os.path.join(ACK_DIR, "*.ack.json"))
    ack_on = len(acks) > 0
    checks.append(("auto_merge_switch", 1 if switch_on else 0, 0, not switch_on))
    checks.append(("all_probe_green_exists", 1 if green_on else 0, 0, not green_on))
    checks.append(("human_ack_present", len(acks), 0, not ack_on))

    dashboard_status = None
    if os.path.isfile(DASHBOARD_TXT):
        try:
            with open(DASHBOARD_TXT, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("STATUS:"):
                        dashboard_status = line.split(":", 1)[1].strip().lower()
                        break
        except Exception:
            pass
    checks.append(("dashboard_healthy", dashboard_status, "healthy", dashboard_status == "healthy"))

    fails = [c for c in checks if not c[3]]
    if not enough_rounds:
        verdict = "WAIT"
        advice = "观察轮数不足，继续观察，至少达到 %d 轮（约24小时）后再评估。" % MIN_OBSERVE_ROUNDS
    elif fails:
        hard_block = any(c[0] in ("recent_rc_zero", "recent_unknown_zero", "recent_alerts_zero") and not c[3] for c in checks)
        verdict = "BLOCK" if hard_block else "WAIT"
        advice = "存在未满足条件；BLOCK 表示需先修复故障并重置基线，WAIT 表示需继续观察或由人工补充配置。"
    else:
        verdict = "READY"
        advice = "所有只读条件满足。仍应由人工确认后手动创建 .auto_merge_on、all_probe_green.flag 和 merge_acks/*.ack.json，再单独运行 merge_apply.py 验证。"

    lines = []
    lines.append("# readiness evaluation %s" % now)
    lines.append("- verdict: **%s**" % verdict)
    lines.append("- advice: %s" % advice)
    lines.append("")
    lines.append("## checks")
    for key, val, expect, ok in checks:
        lines.append("- [%s] %s: got=%s expect=%s" % ("PASS" if ok else "FAIL", key, val, expect))
    lines.append("")
    lines.append("## gate scan")
    if gates:
        for g in gates:
            lines.append("- %s status=%s risk=%s real=%s" % (g["name"], g["status"], g["risk"], g["is_real"]))
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## observe summary")
    lines.append("- total_after_baseline=%d recent_window=%d" % (total_after, len(recent)))
    lines.append("- current_git_sha=%s" % (col(rows[-1], header, "git_sha", "na") if rows else "na"))
    md = "\n".join(lines) + "\n"
    with open(READINESS_MD, "w", encoding="utf-8") as f:
        f.write(md)
    log("READINESS: " + verdict)
    for key, val, expect, ok in checks:
        log("  [%s] %s got=%s expect=%s" % ("PASS" if ok else "FAIL", key, val, expect))
    log("readiness.md written: " + READINESS_MD)
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("readiness_eval error: " + str(e))
        sys.exit(1)
