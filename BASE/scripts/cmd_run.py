#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-os run：默认 mock+dry（=propose-only）；--live 联网；--apply-code 仅任务区出代码草案。
绝不接受 --write-base；改 BASE 需走 BASE 提案/门禁。"""
import os,sys,argparse
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
if "--write-base" in sys.argv:
    print("拒绝：run/evolve 不支持 --write-base。改 BASE 请走 BASE 提案/门禁流程。")
    sys.exit(1)
ap=argparse.ArgumentParser(description="任务级单次执行（草案+门禁，不回 BASE）")
ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
ap.add_argument("--task",default=""); ap.add_argument("task_pos",nargs="?",default="")
ap.add_argument("--live",action="store_true"); ap.add_argument("--mock",action="store_true")
ap.add_argument("--model",default="deepseek-v4-flash"); ap.add_argument("--no-think",action="store_true")
ap.add_argument("--propose-only",action="store_true"); ap.add_argument("--apply-code",action="store_true")
ap.add_argument("--dry",action="store_true")
ns=ap.parse_args()
if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
tid = ns.task or ns.task_pos
if not tid:
    print("usage: cmd_run.py --task <id> [--live|--mock] [--dry] [--apply-code]")
    sys.exit(2)
from task_engine import run_once
sys.exit(run_once(tid, dry=True, live=ns.live and not ns.mock, mock=ns.mock or not ns.live,
                  model=ns.model, no_think=ns.no_think, apply_code=ns.apply_code))
