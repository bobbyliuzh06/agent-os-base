#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, glob, csv, sys, subprocess, shutil
from datetime import datetime

BASE="D:/agent-os"
PENDING=os.path.join(BASE,"PENDING")
LOG=os.path.join(BASE,"BASE","regression-runs","dispatch.log")
CSV=os.path.join(BASE,"BASE","regression-runs","observe.csv")
AUTO_READY=os.path.join(PENDING,"auto_ready.md")

CSV_HEADER=["time","reviews","gates","propose_rc","gate_rc","post_rc","cleanup_rc",
            "unknown","alerts_total","decision","accept_low_candidates","git_sha"]

def current_git_sha():
    try:
        p=subprocess.run(["git","-C",BASE,"rev-parse","--short","HEAD"],
                         capture_output=True,text=True,timeout=30)
        out=(p.stdout or "").strip()
        return out.splitlines()[0].strip() if out else "na"
    except Exception:
        return "na"

def migrate_csv_if_needed():
    """observe.csv 无 git_sha 列时迁移：备份原文件，旧行补 ,na，字段数不足的行丢弃并返回。"""
    dropped=[]
    if not os.path.isfile(CSV):
        return dropped
    try:
        with open(CSV,"r",encoding="utf-8",errors="replace") as f:
            lines=f.read().splitlines()
    except Exception:
        return dropped
    if not lines:
        return dropped
    first=lines[0]
    if "git_sha" in first.split(","):
        return dropped
    try:
        shutil.copy(CSV, CSV+".step16.bak")
    except Exception:
        pass
    ncols=len(first.split(","))
    out=[first+",git_sha"]
    for ln in lines[1:]:
        if not ln.strip():
            continue
        parts=[x.strip() for x in ln.split(",")]
        if len(parts)<ncols:
            dropped.append(ln)
            continue
        out.append(ln+",na")
    with open(CSV,"w",encoding="utf-8",newline="") as f:
        f.write("\n".join(out)+"\n")
    return dropped

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

def count_alerts_last_run(log_path):
    import re
    if not os.path.isfile(log_path):
        return 0
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return 0
    # 按 “========== [YYYY-MM-DD HH:MM] dispatch start ==========” 切分
    parts = re.split(r"={3,}\s*\[[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}\]\s*dispatch start\s*={3,}", text)
    if len(parts) < 2:
        # 找不到起始块时用全文 fallback，但只数最近 200 行，避免历史污染
        tail = text.splitlines()[-200:]
        return sum(1 for l in tail if "[ALERT]" in l)
    last = parts[-1]
    m_end = re.search(r"={3,}\s*\[[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}\]\s*dispatch end", last)
    block = last[:m_end.start()] if m_end else last
    return sum(1 for l in block.splitlines() if "[ALERT]" in l)

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reviews=sorted(glob.glob(os.path.join(PENDING,"*.review.txt")))
    gates=sorted(glob.glob(os.path.join(PENDING,"*.gate.txt")))
    prop_rc=gate_rc=post_rc=clean_rc="na"
    # 从本次运行块抓各阶段 rc（与 count_alerts_last_run 同一分块口径）
    try:
        with open(LOG,"r",encoding="utf-8",errors="replace") as f:
            text=f.read()
        parts=re.split(r"={3,}\s*\[[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}\]\s*dispatch start\s*={3,}", text)
        block=parts[-1] if len(parts)>1 else "\n".join(text.splitlines()[-200:])
        def last_num(pat):
            ms=re.findall(pat, block)
            return ms[-1] if ms else "na"
        prop_rc=last_num(r"propose rc=(\d+)")
        gate_rc=last_num(r"gate rc=(\d+)")
        post_rc=last_num(r"postprocess rc=(\d+)")
        clean_rc=last_num(r"cleanup rc=(\d+)")
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
    alerts=count_alerts_last_run(LOG)
    reasons=[]
    if prop_rc not in("0","na"): reasons.append("propose_rc="+str(prop_rc))
    if gate_rc not in("0","na"): reasons.append("gate_rc="+str(gate_rc))
    if post_rc not in("0","na"): reasons.append("post_rc="+str(post_rc))
    if alerts>0: reasons.append("history_alerts="+str(alerts))
    if unknown_list: reasons.append("unknown_gates="+str(len(unknown_list)))
    auto_on=os.path.exists(os.path.join(BASE,"BASE","META",".auto_merge_on"))
    ready = bool(accept_low) and not reasons and auto_on
    git_sha=current_git_sha()
    dropped=migrate_csv_if_needed()
    if dropped:
        log("CSV_MIGRATE dropped_rows=%d"%(len(dropped)))
        for d in dropped:
            log("  DROPPED: "+d[:200])
    row=[now,n_prop,n_gate,prop_rc,gate_rc,post_rc,clean_rc,len(unknown_list),alerts,
         "ready" if ready else "manual", ";".join(r[0] for r in accept_low), git_sha]
    write_header=not os.path.isfile(CSV)
    with open(CSV,"a",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        if write_header:
            w.writerow(CSV_HEADER)
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
    log("OBSERVE now=%s reviews=%d gates=%d unknown=%d alerts=%d decision=%s auto_on=%s git_sha=%s"%
        (now,n_prop,n_gate,len(unknown_list),alerts,"ready" if ready else "manual",auto_on,git_sha))
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
