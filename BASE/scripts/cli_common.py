#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v0.4 命令公共依赖：加载配置、任务注册表、ID 生成、去重。只读/建文档，不启 evolve。"""
import os, sys, json, re, datetime
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc
_C = _lc()

def cfg(): return _C
def tasks_dir(): return _C.tasks_dir
def registry_path(): return _C.registry

def ensure_dirs():
    for d in (_C.tasks_dir, _C.profile_dir, _C.profile_dir/"skills"):
        d.mkdir(parents=True, exist_ok=True)

def load_registry():
    p = registry_path()
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8"))
        except Exception: return {"schema":"v0.4","tasks":[]}
    return {"schema":"v0.4","tasks":[]}

def save_registry(reg):
    p = registry_path(); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)

def slugify(s):
    s = re.sub(r"[^\w一-鿿\-]+","-",s.strip()).strip("-")
    return s[:60] or "task"

def gen_task_id(domain, goal):
    date = datetime.date.today().strftime("%Y%m%d")
    return "%s-%s-%s" % (slugify(domain), slugify(goal)[:24], date)

def find_similar(domain, goal, reg):
    # 基于 domain/goal 关键词与已有任务名做简单去重
    kw = set(re.findall(r"[\w一-鿿]{2,}", (domain+" "+goal)))
    hits=[]
    for t in reg.get("tasks",[]):
        name=t.get("id","")+" "+t.get("domain","")+" "+t.get("goal","")
        if any(k in name for k in kw):
            hits.append(t.get("id"))
    return hits

def write_text(path, text):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

if __name__ == "__main__":
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    print("cli ok root=", _C.root, "tasks=", _C.tasks_dir)
