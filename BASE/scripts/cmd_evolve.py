#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-os evolve：任务级轻七阶段常驻原型；默认 mock+dry；--live 联网；--apply-code 仅任务区草案。
绝不接受 --write-base。"""
import os,sys,argparse
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
if "--write-base" in sys.argv:
    print("拒绝：run/evolve 不支持 --write-base。改 BASE 请走 BASE 提案/门禁流程。")
    sys.exit(1)
ap=argparse.ArgumentParser(description="任务级常驻演化（dry，不回 BASE）")
ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
ap.add_argument("--task",default=""); ap.add_argument("task_pos",nargs="?",default="")
ap.add_argument("--iterations",type=int,default=3)
ap.add_argument("--live",action="store_true"); ap.add_argument("--mock",action="store_true")
ap.add_argument("--model",default="deepseek-v4-flash"); ap.add_argument("--no-think",action="store_true"); ap.add_argument("--reasoning",default=None)
ap.add_argument("--propose-only",action="store_true"); ap.add_argument("--apply-code",action="store_true")
ap.add_argument("--dry",action="store_true")
ns=ap.parse_args()
if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
tid = ns.task or ns.task_pos
if not tid:
    print("usage: cmd_evolve.py --task <id> [--iterations N] [--live|--mock] [--apply-code]")
    sys.exit(2)
from task_engine import evolve
sys.exit(evolve(tid, ns.iterations, dry=True, live=ns.live and not ns.mock,
                mock=ns.mock or not ns.live, model=ns.model, no_think=ns.no_think,
                reasoning=ns.reasoning, apply_code=ns.apply_code))
