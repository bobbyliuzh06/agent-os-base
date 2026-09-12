#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-os watch：只读汇总 tasks/ 各任务 REQ/最近演化/健康文件；无则提示。不跑调度。"""
import os, sys, json
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cli_common import cfg, tasks_dir, load_registry

def main():
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    C=cfg(); td=tasks_dir(); reg=load_registry()
    print("WATCH root=%s tasks_dir=%s"%(C.root, td))
    if not td.exists() or not any(td.iterdir()):
        print("  无任务。用  agent-os new  创建。基底座健康请跑 BASE/scripts/watch_check.bat")
        return 0
    for t in reg.get("tasks",[]):
        tid=t.get("id","?"); p=Path(t.get("path") or (td/tid))
        req=p/"REQ.md"; ev=p/"task-evolve"
        lines=["  - %s [status=%s]"%(tid, t.get("status","?"))]
        if req.exists(): lines.append("      REQ: 有")
        else: lines.append("      REQ: 缺(需补)")
        if ev.exists():
            logs=sorted(ev.glob("*.log"))+sorted(ev.glob("*.md"))
            lines.append("      task-evolve 文件数=%d"%len(logs))
        else:
            lines.append("      task-evolve: 空(未运行)")
        print("\n".join(lines))
    # 基底座健康摘要（只读调用现有 watch 输出尾部，不改动）
    print("  基底座 STATUS：运行 BASE/scripts/watch_check.bat 查看（本命令不重复触发调度）")
    return 0

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as e:
        print("watch error:", e); sys.exit(1)
