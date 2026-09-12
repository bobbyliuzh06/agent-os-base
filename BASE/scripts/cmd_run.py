#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-os run：默认 mock+dry（=propose-only）；--live 联网；--apply-code 仅任务区出代码草案。
绝不接受 --write-base；改 BASE 需走 BASE 提案/门禁。"""
import os,sys,argparse,datetime
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
if "--write-base" in sys.argv:
    print("拒绝：run/evolve 不支持 --write-base。改 BASE 请走 BASE 提案/门禁流程。")
    sys.exit(1)
ap=argparse.ArgumentParser(description="任务级单次执行（草案+门禁，不回 BASE）")
ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
ap.add_argument("--task",default=""); ap.add_argument("task_pos",nargs="?",default="")
ap.add_argument("--live",action="store_true"); ap.add_argument("--mock",action="store_true")
ap.add_argument("--model",default=""); ap.add_argument("--no-think",action="store_true"); ap.add_argument("--reasoning",default=None)
ap.add_argument("--temperature",type=float,default=None)
ap.add_argument("--propose-only",action="store_true"); ap.add_argument("--apply-code",action="store_true")
ap.add_argument("--dry",action="store_true")
ap.add_argument("--exec",action="store_true"); ap.add_argument("--exec-dry",action="store_true")
ap.add_argument("--sandbox-timeout",type=int,default=30); ap.add_argument("--sandbox-mem",type=int,default=256)
ap.add_argument("--sandbox-runtime",default="proc"); ap.add_argument("--sandbox-entry",default="")
ns=ap.parse_args()
if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
tid = ns.task or ns.task_pos
if not tid:
    print("usage: cmd_run.py --task <id> [--live|--mock] [--dry] [--apply-code] [--exec|--exec-dry]")
    sys.exit(2)
# 1.4 注册表自动登记：任务目录存在但未注册 → 补登记（不覆盖已有条目）
try:
    from cli_common import load_registry, save_registry
    from config_loader import load_config as _lc3
    from pathlib import Path as _P3
    _C3 = _lc3()
    _td3 = _C3.tasks_dir / tid
    if _td3.exists():
        reg = load_registry()
        ids = {t.get("id") for t in reg.get("tasks", [])}
        if tid not in ids:
            reg["tasks"].append({"id": tid, "domain": "", "goal": "", "path": str(_td3),
                                 "status": "auto-registered", "created": datetime.date.today().isoformat()})
            save_registry(reg)
            print("REGISTRY_AUTO_ADD task=%s" % tid)
except Exception as _e:
    print("registry auto-register skipped: %s" % _e)
from task_engine import run_once
rc = run_once(tid, dry=True, live=ns.live and not ns.mock, mock=ns.mock or not ns.live,
              model=ns.model, no_think=ns.no_think, reasoning=ns.reasoning, apply_code=ns.apply_code or ns.exec or ns.exec_dry,
              temperature=ns.temperature)
if rc != 0:
    sys.exit(rc)
if ns.exec or ns.exec_dry:
    SCR = os.path.dirname(os.path.abspath(__file__))
    import subprocess, datetime
    from pathlib import Path
    from config_loader import load_config as _lc2
    _C2 = _lc2()
    scan = subprocess.run([sys.executable, os.path.join(SCR, "code_sandbox_scan.py"), "--task", tid],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(scan.stdout, end="")
    if "block=True" in scan.stdout:
        print("EXEC_BLOCKED：静态扫描命中 HARD 规则，不进沙箱（详见 exec/blocked.json）。")
        sys.exit(0)
    sandbox_dir = os.path.join(str(_C2.root), "tasks", tid,
                               "task-evolve", "exec", "run-" + datetime.date.today().isoformat(), "sandbox-copy")
    args = [sys.executable, os.path.join(SCR, "code_sandbox_run.py"), "--task", tid,
            "--sandbox-dir", sandbox_dir, "--timeout", str(ns.sandbox_timeout),
            "--max-mem-mb", str(ns.sandbox_mem), "--runtime", ns.sandbox_runtime]
    if ns.sandbox_entry: args += ["--entry", ns.sandbox_entry]
    if ns.exec_dry: args += ["--dry"]
    sys.exit(subprocess.call(args))
sys.exit(rc)
