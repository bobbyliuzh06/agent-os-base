#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, glob, sys, json, subprocess
from datetime import datetime

BASE="D:/agent-os"
PENDING=os.path.join(BASE,"PENDING")
SCRIPTS=os.path.join(BASE,"BASE","scripts")
OBS_CSV=os.path.join(BASE,"BASE","regression-runs","observe.csv")
ADVICE=os.path.join(PENDING,"merge_advice.md")
SWITCH=os.path.join(BASE,"BASE","META",".auto_merge_on")
WL=os.path.join(BASE,"BASE","META","merge_whitelist.json")
ACK_DIR=os.path.join(BASE,"BASE","regression-runs","merge_acks")

def log(s):
    print(s, flush=True)

def run(cmd):
    log("RUN: "+cmd)
    p=subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
    if p.stdout: log(p.stdout.strip())
    if p.stderr: log("[err] "+p.stderr.strip())
    return p.returncode

def load_json(path, default):
    if os.path.isfile(path):
        try:
            with open(path,"r",encoding="utf-8-sig") as f: return json.load(f)
        except Exception: return default
    return default

def latest_obs_ok():
    if not os.path.isfile(OBS_CSV):
        return False, "no-observe-csv"
    rows=[]
    try:
        with open(OBS_CSV,"r",encoding="utf-8",errors="replace") as f:
            lines=f.readlines()
        for ln in lines[1:]:
            parts=[x.strip() for x in ln.split(",")]
            if len(parts)<10: continue
            rows.append(parts)
    except Exception as e:
        return False, "obs-read-error:"+str(e)
    if not rows: return False, "no-obs-rows"
    last=rows[-1]
    # 列序同 observe_report: time,reviews,gates,propose_rc,gate_rc,post_rc,cleanup_rc,unknown,alerts_total,decision,candidates
    def eq(v,ok): return v in ok
    if last[3] not in("0","na") or last[4] not in("0","na") or last[5] not in("0","na") or last[6] not in("0","na"):
        return False, "recent-rc-nonzero"
    if int(last[7] or 0)>0: return False, "recent-unknown-gate"
    if int(last[8] or 0)>0: return False, "recent-alerts>0"
    return True, "ok"

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not os.path.isfile(SWITCH):
        log("AUTO_MERGE_OFF: 未创建 .auto_merge_on，merge_apply 直接退出（仅dry-run有效）")
        return 0
    wl=load_json(WL,{})
    ok,why=latest_obs_ok()
    if not ok:
        log("AUTO_MERGE_BLOCK: observe条件不满足: "+why); return 0
    if wl.get("require_regression_all_green",True):
        # 回归全绿以独立探针结果文件为准；这里只检查是否存在 regression-runs 下全绿标记文件
        green=os.path.join(BASE,"BASE","regression-runs","all_probe_green.flag")
        if not os.path.isfile(green):
            log("AUTO_MERGE_BLOCK: 无 all_probe_green.flag，回归未确认全绿"); return 0
    if wl.get("require_human_ack_file",True):
        os.makedirs(ACK_DIR,exist_ok=True)
        acks=glob.glob(os.path.join(ACK_DIR,"*.ack.json"))
        if not acks:
            log("AUTO_MERGE_BLOCK: 无人工ack文件，apply不执行"); return 0
    # 从 advice 抽取 ready-dryrun 方案并执行（极保守：每个candidate单独分支、打tag、不push）
    if not os.path.isfile(ADVICE):
        log("AUTO_MERGE_BLOCK: 无 merge_advice.md"); return 0
    txt=open(ADVICE,"r",encoding="utf-8",errors="replace").read()
    blocks=re.findall(r"## (.+?\.gate\.txt)\n.*?verdict=ready-dryrun.*?plan:\n```\n(.*?)```", txt, re.S)
    if not blocks:
        log("AUTO_MERGE_BLOCK: advice 无 ready-dryrun 方案"); return 0
    for name,plan in blocks:
        ack_path=os.path.join(ACK_DIR, name.replace(".gate.txt","")+".ack.json")
        if not os.path.isfile(ack_path):
            log("SKIP %s: 无对应人工ack"%name); continue
        pretag="pre-auto/"+now.replace(":","-").replace(" ","T")+"/"+name
        run('git -C "%s" tag -a %s -m "pre-auto-merge backup"'%(BASE,pretag))
        for line in plan.splitlines():
            line=line.strip()
            if not line or line.startswith("#"): continue
            if "push" in line.lower():
                log("BLOCK push command in plan: "+line); continue
            rc=run(line)
            if rc!=0:
                log("APPLY_FAIL %s rc=%d, 已打备份tag=%s，人工回滚"%(name,rc,pretag)); return 1
        log("APPLIED %s backup_tag=%s"%(name,pretag))
    log("merge_apply done")
    return 0

if __name__=="__main__":
    try:
        main()
    except Exception as e:
        log("merge_apply error: "+str(e)); sys.exit(1)
