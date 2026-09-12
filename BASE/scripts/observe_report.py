#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, glob, csv, sys
from datetime import datetime

BASE="D:/agent-os"
PENDING=os.path.join(BASE,"PENDING")
LOG=os.path.join(BASE,"BASE","regression-runs","dispatch.log")
CSV=os.path.join(BASE,"BASE","regression-runs","observe.csv")
AUTO_READY=os.path.join(PENDING,"auto_ready.md")

def log(s):
    print(s, flush=True)

def parse_head(path, keys):
    out={}
    try:
        with open(path,"r",encoding="utf-8",errors="replace") as f:
            for line in f:
                line=line.strip()
                for k in keys:
                    m=re.match(re.escape(k)+r"\s*[:=]\s*(.+)",line)
                    if m:
                        out[k]=m.group(1).strip()
                        break
                if len(out)>=len(keys):
                    break
    except Exception:
        pass
    return out

def last_alert_count(n_lines=200000):
    c=0
    try:
        with open(LOG,"r",encoding="utf-8",errors="replace") as f:
            for line in f:
                if "[ALERT]" in line:
                    c+=1
    except Exception:
        pass
    return c

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reviews=sorted(glob.glob(os.path.join(PENDING,"*.review.txt")))
    gates=sorted(glob.glob(os.path.join(PENDING,"*.gate.txt")))
    prop_rc=gate_rc=post_rc=clean_rc="na"
    # 从最新log尾尝试抓本轮rc（简单粗解析）
    try:
        with open(LOG,"r",encoding="utf-8",errors="replace") as f:
            tail=f.read()[-8000:]
        for tag,var in [("propose_rc=","p"),("gate_rc=","g"),("post_rc=","o"),("cleanup_rc=","c")]:
            ms=re.findall(tag+r"(\d+)",tail)
            if ms:
                m=ms[-1]
                if var=="p": prop_rc=m
                if var=="g": gate_rc=m
                if var=="o": post_rc=m
                if var=="c": clean_rc=m
    except Exception:
        pass
    n_prop=len(reviews); n_gate=len(gates)
    accept_low=[]
    unknown_list=[]
    for g in gates:
        kv=parse_head(g,["GATE_STATUS","GATE_RISK","STATUS","RISK"])
        st=(kv.get("GATE_STATUS") or kv.get("STATUS") or "unknown").lower()
        rk=(kv.get("GATE_RISK") or kv.get("RISK") or "unknown").lower()
        if st=="unknown" or rk=="unknown":
            unknown_list.append(os.path.basename(g))
        if st=="accept" and rk=="low":
            accept_low.append((os.path.basename(g),os.path.basename(g).replace(".gate.txt","")))
    alerts=last_alert_count()
    reasons=[]
    if prop_rc not in("0","na"): reasons.append("propose_rc="+str(prop_rc))
    if gate_rc not in("0","na"): reasons.append("gate_rc="+str(gate_rc))
    if post_rc not in("0","na"): reasons.append("post_rc="+str(post_rc))
    if alerts>0: reasons.append("history_alerts="+str(alerts))
    if unknown_list: reasons.append("unknown_gates="+str(len(unknown_list)))
    auto_on=os.path.exists(os.path.join(BASE,"BASE","META",".auto_merge_on"))
    ready = bool(accept_low) and not reasons and auto_on
    row=[now,n_prop,n_gate,prop_rc,gate_rc,post_rc,clean_rc,len(unknown_list),alerts,
         "ready" if ready else "manual", ";".join(r[0] for r in accept_low)]
    write_header=not os.path.isfile(CSV)
    with open(CSV,"a",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        if write_header:
            w.writerow(["time","reviews","gates","propose_rc","gate_rc","post_rc","cleanup_rc",
                        "unknown","alerts_total","decision","accept_low_candidates"])
        w.writerow(row)
    if accept_low:
        with open(AUTO_READY,"w",encoding="utf-8") as f:
            f.write("# 自动合并候选 %s\n"%now)
            f.write("- auto_merge_switch: %s\n"%("ON" if auto_on else "OFF(仅建议)"))
            f.write("- 判定原因排除项: %s\n"%(";".join(reasons) if reasons else "无"))
            for g,base in accept_low:
                f.write("\n## %s\n- gate: %s\n- 建议: %s\n"%(" ".join(base.split('_')[:2]) if base else base, g,
                      "可人工合并" if (auto_on and not reasons) else "仅列候选，不自动合并"))
    else:
        if os.path.isfile(AUTO_READY):
            try: os.remove(AUTO_READY)
            except Exception: pass
    log("OBSERVE now=%s reviews=%d gates=%d unknown=%d alerts=%d decision=%s auto_on=%s"%
        (now,n_prop,n_gate,len(unknown_list),alerts,"ready" if ready else "manual",auto_on))
    if accept_low:
        log("accept_low_candidates="+";".join(r[0] for r in accept_low))
    if unknown_list:
        log("unknown_gates="+";".join(unknown_list))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("observe error: " + str(e))
        sys.exit(1)
