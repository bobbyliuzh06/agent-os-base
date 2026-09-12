#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""release_split_base.py：把 BASE 子树历史抽取为新裸仓（可重放脚本）。
默认 --dry 只打印命令；真实拆分需人工在克隆副本执行 git-filter-repo，不动原仓、不 force-push。"""
import os, sys, argparse, subprocess
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

def main():
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("AGENT_OS_ROOT", ""))
    ap.add_argument("--source", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--dry", action="store_true", default=True)
    ns = ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"] = ns.root
    C = _lc()
    source = Path(ns.source or str(C.root))
    out = Path(ns.out or str(C.root.parent / "agent-os-base.git"))
    cmds = [
        f'git clone --mirror "{source}" "{out}"',
        f'git -C "{out}" filter-repo --subdirectory-filter BASE --force',
        f'git -C "{out}" update-ref -d refs/tags/v0.4.0-base-rc1  # 若旧 rc1 标签存在则清理（可选）',
        '# 使用方: git remote add base <url>; git fetch base',
    ]
    print("RELEASE_SPLIT_BASE dry=%s source=%s out=%s" % (ns.dry, source, out))
    for c in cmds:
        print("  " + c)
    print("NOTE: 本脚本不执行任何命令。真实拆分：先全量备份原仓，再在克隆副本上跑 filter-repo；不 force-push 原仓。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
