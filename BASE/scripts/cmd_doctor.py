#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-os doctor：只读扫描 tasks/ 重复/孤儿/超大/锁冲突。不改任何文件。"""
import os, sys, json, re
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cli_common import cfg, tasks_dir, load_registry

MB = 1024 * 1024
def main():
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    C=cfg(); td=tasks_dir(); issues=[]
    reg=load_registry(); reg_ids={t["id"] for t in reg.get("tasks",[])}
    if not td.exists():
        print("no tasks dir:", td); return 0
    dirs=[p for p in td.iterdir() if p.is_dir() and not p.name.startswith(".")]
    # 1) 重复：名称相似 / 同 domain+goal
    seen={}
    for d in dirs:
        req=d/"REQ.md"
        txt=req.read_text(encoding="utf-8",errors="replace") if req.exists() else ""
        dom=re.search(r"领域：(.+)", txt); goal=re.search(r"目标：(.+)", txt)
        key=(dom.group(1).strip() if dom else "", goal.group(1).strip() if goal else d.name)
        seen.setdefault(key,[]).append(d.name)
    for k,v in seen.items():
        if len(v)>1: issues.append(("DUPLICATE", "领域/目标相同 %s -> %s"%(k, v)))
    # 2) 孤儿：目录不在 registry
    for d in dirs:
        if d.name not in reg_ids:
            issues.append(("ORPHAN", d.name+" 不在 registry.json"))
    # 3) 未注册但 registry 有路径缺失
    for t in reg.get("tasks",[]):
        if not Path(t.get("path","")).exists():
            issues.append(("MISSING_REG", t.get("id","")+" registry 指向不存在"))
    # 4) 超大文件（>200MB）与无锁
    for d in dirs:
        for f in d.rglob("*"):
            if f.is_file():
                sz=f.stat().st_size
                if sz>200*MB: issues.append(("LARGE", "%s %.1fMB"%(f.relative_to(td), sz/MB)))
        if not (d/".lock").exists():
            issues.append(("NO_LOCK", d.name+" 无 .lock（建议 run/evolve 前创建）"))
    # 5) 同名多实例
    names=[d.name for d in dirs]
    for n in set(names):
        if names.count(n)>1: issues.append(("NAME_COLLISION", n))
    print("DOCTOR tasks_dir=%s tasks=%d issues=%d"%(td, len(dirs), len(issues)))
    for kind,msg in issues:
        print("  [%s] %s"%(kind,msg))
    if not issues: print("  OK: 无重复/孤儿/超大/锁冲突")
    return 0

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as e:
        print("doctor error:", e); sys.exit(1)
