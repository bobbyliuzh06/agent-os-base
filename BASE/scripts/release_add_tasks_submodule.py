#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""release_add_tasks_submodule.py：对 tasks/<id> 输出 submodule/subtree 钉版本命令（可重放）。
默认不执行，仅打印；单 base 多任务独立发版才用 submodule，否则保持单仓 ignore tasks 更简单。"""
import os, sys, argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

def main():
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("AGENT_OS_ROOT", ""))
    ap.add_argument("--task", required=True)
    ap.add_argument("--url", default="")
    ap.add_argument("--mode", default="submodule", choices=["submodule", "subtree"])
    ns = ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"] = ns.root
    C = _lc()
    task = ns.task
    url = ns.url or "<git-url-of-task-repo>"
    if ns.mode == "submodule":
        cmds = [f'git -C "{C.root}" submodule add {url} tasks/{task}',
                f'git -C "{C.root}" -c protocol.file.allow=always submodule update --init --recursive  # 首次拉取']
    else:
        cmds = [f'git -C "{C.root}" subtree add --prefix=tasks/{task} {url} main --squash']
    print("RELEASE_ADD_TASK mode=%s task=%s (dry, 不执行)" % (ns.mode, task))
    for c in cmds:
        print("  " + c)
    print("NOTE: submodule 适合任务独立发版；通用场景建议保持单仓 + ignore tasks。回滚：git submodule deinit -f tasks/<id>; git rm tasks/<id>")
    return 0

if __name__ == "__main__":
    sys.exit(main())
