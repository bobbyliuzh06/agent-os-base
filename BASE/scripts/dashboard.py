#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, csv, glob
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _load, apply_root_arg
sys.argv = apply_root_arg()
_C = _load()

BASE=str(_C.root)
OBS=os.path.join(BASE,"BASE","regression-runs","observe.csv")
PENDING=os.path.join(BASE,"PENDING")

def log(s):
    print(s, flush=True)

def _after_baseline(rows, header):
    import os, datetime
    bpath = os.path.join(str(_C.regression), ".obs_baseline_ts")
    if not os.path.isfile(bpath):
        return rows
    try:
        bt = open(bpath, "r", encoding="utf-8").read().strip()
        base = datetime.datetime.strptime(bt, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return rows
    out=[]
    for r in rows:
        t=r[0].strip()
        try:
            rt=datetime.datetime.strptime(t,"%Y-%m-%d %H:%M:%S")
        except Exception:
            out.append(r); continue
        if rt>=base: out.append(r)
    return out

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    n=24
    rows=[]
    header=[]
    if os.path.isfile(OBS):
        with open(OBS,"r",encoding="utf-8",errors="replace") as f:
            lines=f.readlines()
        header=[x.strip() for x in lines[0].split(",")] if lines else []
        idx={name:i for i,name in enumerate(header)}
        for ln in lines[1:]:
            parts=[x.strip() for x in ln.split(",")]
            if len(parts)<len(header): continue
            rows.append(parts)
    rows=_after_baseline(rows, header)
    recent=rows[-n:]
    def col(r,k,default="0"):
        i=idx.get(k)
        return r[i] if (i is not None and i<len(r) and r[i]!="") else default
    total=len(rows)
    rounds=len(recent)
    all_zero=lambda k: all(col(r,k) in("0","na") for r in recent)
    alerts=sum(int(col(r,"alerts_total","0")) for r in recent)
    unknown=sum(int(col(r,"unknown","0")) for r in recent)
    gate_dist={}
    for r in rows:
        kv=col(r,"decision","manual")
        gate_dist[kv]=gate_dist.get(kv,0)+1
    accept_low=sum(1 for r in rows if col(r,"accept_low_candidates","")!="")
    sha=col(rows[-1],"git_sha","na") if rows else "na"
    rc_ok=all(
        all(col(r,k) in("0","na") for k in ["propose_rc","gate_rc","post_rc","cleanup_rc","observe_rc","advice_rc"])
        for r in recent)
    disk=0
    if os.path.isdir(PENDING):
        for p in glob.glob(os.path.join(PENDING,"*.reasoning.txt")):
            try: disk+=os.path.getsize(p)
            except Exception: pass
    if alerts>0 or unknown>0 or not rc_ok:
        status="alert"
    elif rounds==0:
        status="watch"
    else:
        status="healthy"
    out=[]
    out.append("=" * 50)
    out.append("agent-os evolve dashboard  %s"%datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    out.append("STATUS: %s"%status)
    out.append("- observe rows (total / last %d): %d / %d"%(n,total,rounds))
    out.append("- all-rc-zero in window: %s"%rc_ok)
    out.append("- unknown gates (window): %d"%unknown)
    out.append("- alerts_total (window sum): %d"%alerts)
    out.append("- decision distribution (all): %s"%gate_dist)
    out.append("- accept+low candidates (all): %d"%accept_low)
    out.append("- reasoning disk MB: %.1f"%(disk/1024/1024))
    out.append("- current git_sha: %s"%sha)
    out.append("=" * 50)
    txt="\n".join(out)
    log(txt)
    with open(os.path.join(BASE,"BASE","regression-runs","dashboard.txt"),"w",encoding="utf-8") as f:
        f.write(txt+"\n")
    return 0

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        log("dashboard error: "+str(e)); sys.exit(1)
