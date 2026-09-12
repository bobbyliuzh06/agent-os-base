#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, sys, glob
from datetime import datetime

PENDING = "D:/agent-os/PENDING"

def log(s):
    print(s, flush=True)

def parse_kv(path, keys):
    out = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                for k in keys:
                    if line.startswith(k + ":") or line.startswith(k + " ="):
                        v = line.split(":", 1)[-1].strip()
                        out[k] = v
                        break
    except Exception as e:
        out["_error"] = str(e)
    return out

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log("POSTPROCESS start " + now)
    if not os.path.isdir(PENDING):
        log("PENDING 不存在，无产物可处理")
        return 0
    gates = sorted(glob.glob(os.path.join(PENDING, "*.gate.txt")))
    alerts = []
    for g in gates:
        kv = parse_kv(g, ["STATUS", "GATE_STATUS", "GATE_RISK", "RISK"])
        # 找对应 pending md
        base = g[:-len(".gate.txt")]
        md = base + ".md"
        status = (kv.get("GATE_STATUS") or kv.get("STATUS") or "unknown").lower()
        risk = (kv.get("GATE_RISK") or kv.get("RISK") or "unknown").lower()
        if status in ("unknown", "", "none"):
            decision = "manual-review (unknown 降级)"
            alerts.append("UNKNOWN: " + g)
        elif status == "accept":
            decision = "waiting-human-merge"
        elif status == "reject":
            decision = "return-to-proposer"
        else:
            decision = "waiting-human-gate"
        if os.path.isfile(md):
            try:
                with open(md, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                marker = "## gate 结论"
                if marker not in content:
                    with open(md, "a", encoding="utf-8") as fh:
                        fh.write("\n%s %s\n- GATE_STATUS: %s\n- GATE_RISK: %s\n- 处置: %s\n" % (marker, now, status, risk, decision))
            except Exception as e:
                alerts.append("MD_WRITE_ERR: " + str(e))
        log("[post] %s -> %s" % (os.path.basename(g), decision))
    if alerts:
        log("ALERTS:")
        for a in alerts:
            log("  " + a)
    log("POSTPROCESS end")
    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("错误: " + str(e))
        sys.exit(1)
