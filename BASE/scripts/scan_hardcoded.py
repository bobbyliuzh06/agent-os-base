#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 BASE/scripts 与 BASE/meta 中的硬编码项，只输出报告、不修改任何文件。"""
import os, re, glob
sys_path_here = os.path.dirname(os.path.abspath(__file__))
if sys_path_here not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path_here)
from config_loader import load_config as _load
_C = _load()

BASE = str(_C.root)
TARGETS = [os.path.join(BASE, "BASE", "scripts"), os.path.join(BASE, "BASE", "META")]
PATTERNS = {
    "hardcoded_d_drive": re.escape(str(_C.root).replace("\\", "/")),
    "hardcoded_env": re.escape(str(_C.root)),
    "absolute_userprofile": "C:/Users/[^\"\\s]+/AppData",
    "schedule_task_name": r"AgentOS_(?:EvolveDispatch|WatchCheck)",
}
SKIP = ("generate_usage_doc.py", "scan_hardcoded.py", ".bak", ".step")

def main():
    rows = []
    for root in TARGETS:
        if not os.path.isdir(root): continue
        for path in sorted(glob.glob(os.path.join(root, "**", "*"), recursive=True)):
            if not os.path.isfile(path): continue
            if any(s in path for s in SKIP): continue
            if not path.endswith((".py", ".bat", ".json", ".md", ".txt")): continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                if "AGENT_OS_ROOT=" in line:
                    continue
                for name, pat in PATTERNS.items():
                    if re.search(pat, line):
                        rows.append((os.path.relpath(path, BASE), i, name, line.strip()[:120]))
    out = ["# 硬编码/本地化扫描报告（自动生成，只读）", ""]
    if rows:
        out.append("共发现 %d 处（v0.4 参数化时需处理，本步不改）：" % len(rows))
        out.append("")
        for r in rows:
            out.append("- `%s:%d` [%s] %s" % r)
    else:
        out.append("未发现硬编码项（已清理）。")
    txt = "\n".join(out) + "\n"
    report = os.path.join(BASE, "BASE", "regression-runs", "hardcoded-scan.md")
    os.makedirs(os.path.dirname(report), exist_ok=True)
    with open(report, "w", encoding="utf-8") as f:
        f.write(txt)
    print("SCAN rows=%d report=%s" % (len(rows), report))
    for r in rows[:50]:
        print("  %s:%d [%s]" % (r[0], r[1], r[2]))
    return 0

if __name__ == "__main__":
    import sys
    try: sys.exit(main())
    except Exception as e: print("scan error:", e); sys.exit(1)
