#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务级轻七阶段：propose(proposer)->gate(规则层)->postprocess->observe->health；只写 tasks/<id>/task-evolve。
不调用 BASE 全局 evolve，不写 PENDING/，不写 BASE/regression-runs，不碰 BASE/META 规则。
默认 mock+dry；--live 才联网；--apply-code 才在任务区出代码草案（仍不执行、不写BASE）。"""
import os, sys, json, datetime, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc
from task_lock import TaskLock
from proposer import propose as _propose
from gate_review_adapter import review as _gate_review

STAGES=["propose","gate","postprocess","observe","health"]

def _stamp(): return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def _read_req(task_dir):
    p=task_dir/"REQ.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""

def run_once(task_id, dry=True, live=False, mock=True, model="",
             no_think=False, apply_code=False, reasoning=None, temperature=None, max_iter=1):
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
        ts=_stamp()
        log=ev/("run-%s.log"%ts)
        lines=[]
        def a(s): lines.append(s)
        use_live = live and not mock
        a("TASK=%s dry=%s live=%s model=%s time=%s"%(task_id, dry, use_live, model or "config", ts))
        # 1 propose：proposer 适配器（mock 或 deepseek），只产出结构化草案 JSON
        prop=_propose(req, task_id, live=use_live, model=model, thinking=not no_think,
                      reasoning=reasoning, no_think=no_think, temperature=temperature)
        prop_path=ev/("propose-%s.json"%ts)
        prop_path.write_text(json.dumps(prop,ensure_ascii=False,indent=2),encoding="utf-8")
        a("PROPOSE=%s model=%s"%(prop.get("proposal_id"), prop.get("model")))
        # 2 gate：确定性规则层裁决（LLM 结论仅参考，不自动执行）
        g=_gate_review(prop, task_id)
        gate_path=ev/("gate-%s.json"%ts)
        gate_path.write_text(json.dumps(g,ensure_ascii=False,indent=2),encoding="utf-8")
        a("GATE=%s risk=%s auto_merge=%s"%(g["gate"], g["risk"], g["auto_merge"]))
        verdict=g["gate"]
        status = "accept-plan" if (verdict=="accept" and apply_code) else ("accept-dry" if verdict=="accept" else "blocked")
        # 3 产物：blocked 不产任何代码草案；accept+apply_code 才写 plan（仍不执行）
        out_dir=td/"workspace"
        out_dir.mkdir(parents=True, exist_ok=True)
        if verdict=="accept":
            if apply_code:
                plan=out_dir/("plan-%s.md"%ts)
                plan.write_text("# 代码草案(plan only, 未执行)\n\n任务=%s\n提案=%s\n\n- 仅任务区草案，需人工审查后手动实现\n- 不写BASE、不执行shell\n"%(task_id, prop.get("proposal_id")),encoding="utf-8")
                a("PLAN=%s (apply-code draft only)"%plan)
            else:
                rd=out_dir/"README.dry"
                rd.write_text("dry 模式：仅出提案+门禁，未生成代码草案。使用 --apply-code 可出任务区草案。\n",encoding="utf-8")
                a("DRY=README.dry (no code emitted)")
        else:
            a("BLOCKED=%s reasons=%d (no code, no BASE write)"%(verdict, len(g.get("reasons",[]))))
        # 4 observe：任务级 csv（rc 恒 0；gate 结论记录在 dashboard 与 gate json）
        obs=ev/"observe.csv"
        header="round,rc,unknown,alerts,timestamp\n"
        cur=header if not obs.exists() else obs.read_text(encoding="utf-8",errors="replace")
        if cur.strip()=="" : cur=header
        round_no=len([l for l in cur.strip().splitlines() if l and not l.startswith("round")])+1
        cur+="%d,0,0,0,%s\n"%(round_no,ts)
        obs.write_text(cur,encoding="utf-8")
        a("OBSERVE round=%d rc=0 unknown=0 alerts=0"%round_no)
        # 5 dashboard：任务级摘要（含 gate 结论）
        dash="STATUS: %s\nTASK: %s\nlast_run: %s\npropose: %s\ngate: %s/%s\nauto_merge: %s\nobserve_rounds: %d\n"%(
            status, task_id, ts, prop.get("model"), verdict, g["risk"], g["auto_merge"], round_no)
        (ev/"dashboard.txt").write_text(dash,encoding="utf-8")
        a("HEALTH="+dash.replace("\n"," | "))
        log.write_text("\n".join(lines)+"\n",encoding="utf-8")
        print("RUN_%s task=%s log=%s gate=%s risk=%s model=%s"%(
            "DONE" if verdict=="accept" else "BLOCKED", task_id, log, verdict, g["risk"], prop.get("model")))
        return 0
    finally:
        lock.release()

def evolve(task_id, iterations=3, dry=True, live=False, mock=True, model="",
           no_think=False, apply_code=False, reasoning=None, temperature=None):
    # 常驻轻量：多次 run_once，写 task-evolve；不回 BASE
    for i in range(iterations):
        rc=run_once(task_id, dry=dry, live=live, mock=mock, model=model,
                    no_think=no_think, apply_code=apply_code, reasoning=reasoning,
                    temperature=temperature)
        if rc!=0: return rc
    print("EVOLVE_DONE task=%s iterations=%d (task-local only)"%(task_id,iterations))
    return 0

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
    ap.add_argument("cmd",nargs="?",default="run"); ap.add_argument("task",nargs="?",default="")
    ap.add_argument("--iterations",type=int,default=3); ap.add_argument("--dry",action="store_true")
    ap.add_argument("--live",action="store_true"); ap.add_argument("--mock",action="store_true")
    ap.add_argument("--model",default="deepseek-v4-flash"); ap.add_argument("--no-think",action="store_true")
    ap.add_argument("--apply-code",action="store_true")
    ns=ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
    if not ns.task:
        print("usage: task_engine.py [run|evolve] <task_id> [--dry] [--live] [--apply-code] [--iterations N]"); sys.exit(2)
    if ns.cmd=="evolve":
        sys.exit(evolve(ns.task, ns.iterations, dry=ns.dry or True, live=ns.live and not ns.mock,
                        mock=ns.mock or not ns.live, model=ns.model, no_think=ns.no_think, apply_code=ns.apply_code))
    else:
        sys.exit(run_once(ns.task, dry=ns.dry or True, live=ns.live and not ns.mock,
                          mock=ns.mock or not ns.live, model=ns.model, no_think=ns.no_think, apply_code=ns.apply_code))
