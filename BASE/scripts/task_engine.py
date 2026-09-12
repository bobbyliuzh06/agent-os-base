#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务级轻七阶段：propose->gate->postprocess->observe->health；只写 tasks/<id>/task-evolve。
不调用 BASE 全局 evolve，不写 PENDING/，不写 BASE/regression-runs，不碰 BASE/META 规则。"""
import os, sys, json, datetime, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc
from task_lock import TaskLock

STAGES=["propose","gate","postprocess","observe","health"]

def _stamp(): return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def _read_req(task_dir):
    p=task_dir/"REQ.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""

def run_once(task_id, dry=False, max_iter=1):
    C=_lc(); td=C.tasks_dir/task_id
    if not td.exists():
        print("NO_TASK", task_id); return 1
    lock = TaskLock(os.path.join(str(td), ".lock"), timeout=0)
    if not lock.acquire():
        print("LOCKED", "TASK_LOCKED:" + os.path.join(str(td), ".lock"))
        return 1
    try:
        ev=td/"task-evolve"; ev.mkdir(parents=True, exist_ok=True)
        req=_read_req(td)
        log=ev/("run-%s.log"%_stamp())
        lines=[]
        def a(s): lines.append(s)
        a("TASK=%s dry=%s time=%s"%(task_id, dry, _stamp()))
        # 1 propose：基于 REQ 生成提案文本（不调用外部模型；用规则摘要，后续可接 dsh）
        propose={"goal": (re.search(r"目标：(.+)",req) or [None,""])[1].strip(),
                 "domain": (re.search(r"领域：(.+)",req) or [None,""])[1].strip(),
                 "draft_steps":["parse_req","design_plan","implement_draft","self_check"],
                 "notes":"原型提案；未调用LLM，待 run 接入 harness"}
        a("PROPOSE="+json.dumps(propose,ensure_ascii=False))
        prop_path=ev/("propose-%s.json"%_stamp()); prop_path.write_text(json.dumps(propose,ensure_ascii=False,indent=2),encoding="utf-8")
        # 2 gate：轻量规则门禁（只判 dry/risk，不合并）
        risk="low" if dry else "review"
        status="accept" if dry else "needs_human"
        gate={"GATE_STATUS":status,"GATE_RISK":risk,"auto_merge":False,
              "reason":"task-layer prototype; base rules untouched; requires human review before any apply"}
        a("GATE="+json.dumps(gate,ensure_ascii=False))
        (ev/("gate-%s.txt"%_stamp())).write_text("GATE_STATUS=%s\nGATE_RISK=%s\nauto_merge=false\nreason=%s\n"%(status,risk,gate["reason"]),encoding="utf-8")
        # 3 postprocess：仅记录产物路径，不写代码到 BASE
        a("POSTPROCESS=record_only; artifacts_dir=%s"%(td/"workspace"))
        # 4 observe：写 observe.csv（任务级，独立文件）
        obs=ev/"observe.csv"
        header="round,rc,unknown,alerts,timestamp\n"
        cur=header if not obs.exists() else obs.read_text(encoding="utf-8",errors="replace")
        if cur.strip()=="" : cur=header
        round_no=len([l for l in cur.strip().splitlines() if l and not l.startswith("round")])+1
        cur+="%d,0,0,0,%s\n"%(round_no,_stamp())
        obs.write_text(cur,encoding="utf-8")
        a("OBSERVE round=%d rc=0 unknown=0 alerts=0"%round_no)
        # 5 health/dashboard：任务级摘要
        dash="STATUS: %s\nTASK: %s\nlast_run: %s\npropose: yes\ngate: %s/%s\nobserve_rounds: %d\n"%("healthy" if dry else "watch",task_id,_stamp(),status,risk,round_no)
        (ev/"dashboard.txt").write_text(dash,encoding="utf-8")
        a("HEALTH="+dash.replace("\n"," | "))
        log.write_text("\n".join(lines)+"\n",encoding="utf-8")
        print("RUN_DONE task=%s log=%s status=%s risk=%s"%(task_id,log,status,risk))
        return 0
    finally:
        lock.release()

def evolve(task_id, iterations=3, dry=True):
    # 常驻轻量：多次 run_once，写 task-evolve；不回 BASE
    for i in range(iterations):
        rc=run_once(task_id, dry=dry)
        if rc!=0: return rc
    print("EVOLVE_DONE task=%s iterations=%d (task-local only)"%(task_id,iterations))
    return 0

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
    ap.add_argument("cmd",nargs="?",default="run"); ap.add_argument("task",nargs="?",default="")
    ap.add_argument("--iterations",type=int,default=3); ap.add_argument("--dry",action="store_true")
    ns=ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
    if not ns.task:
        print("usage: task_engine.py [run|evolve] <task_id> [--dry] [--iterations N]"); sys.exit(2)
    if ns.cmd=="evolve":
        sys.exit(evolve(ns.task, ns.iterations, dry=ns.dry or True))
    else:
        sys.exit(run_once(ns.task, dry=ns.dry or True))
