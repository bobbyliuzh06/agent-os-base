#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,sys,argparse
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
ap=argparse.ArgumentParser(); ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
ap.add_argument("--check",action="store_true"); ap.add_argument("--plan",action="store_true")
ap.add_argument("--apply",action="store_true"); ap.add_argument("--yes",action="store_true")
ap.add_argument("--mode",default="")
ns=ap.parse_args()
if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
from sync_manager import run_check, run_apply, _lc, gh_cfg, open_log
C=_lc(); cfg=gh_cfg(C)
if ns.mode: cfg["mode"]=ns.mode
p,fh=open_log(C)
try:
    if ns.apply:
        if not ns.yes:
            print("sync apply 需 --yes 确认")
            sys.exit(1)
        sys.exit(run_apply(C,cfg,fh))
    else:
        sys.exit(run_check(C,cfg,fh))
finally:
    try: fh.close()
    except Exception: pass
