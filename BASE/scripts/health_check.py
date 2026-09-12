#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, glob, subprocess, json, time
from datetime import datetime

BASE="D:/agent-os"
PENDING=os.path.join(BASE,"PENDING")
SCRIPTS=os.path.join(BASE,"BASE","scripts")
LOG=os.path.join(BASE,"BASE","regression-runs","dispatch.log")
DSH_CACHE=os.path.join(os.environ.get("LOCALAPPDATA",""),"npm-cache","_npx")

HARD_FAILS=[]

def log(s):
    print(s, flush=True)

def hard(msg):
    HARD_FAILS.append(msg)
    log("[HEALTH-HARD-FAIL] "+msg)

def soft(msg):
    log("[HEALTH-WARN] "+msg)

def find_bin_js():
    for root, dirs, files in os.walk(DSH_CACHE):
        if os.path.basename(root)=="lib" and "bin.js" in files:
            if root.replace("\\","/").endswith("@deepseek-ai/dsh/lib"):
                return os.path.join(root,"bin.js")
    for name in ["dsh.cmd","dsh.exe","dsh"]:
        p=shutil_which(name)
        if p:
            cand=os.path.join(os.path.dirname(p),"..","lib","bin.js")
            if os.path.isfile(cand): return cand
    return None

def shutil_which(name):
    try:
        import shutil
        return shutil.which(name)
    except Exception:
        return None

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log("HEALTH start "+now)
    mode=sys.argv[1] if len(sys.argv)>1 else "pre"
    # 1) node + bin.js 可达
    node=shutil_which("node")
    if not node:
        hard("node not in PATH")
    else:
        binjs=find_bin_js()
        if not binjs or not os.path.isfile(binjs):
            hard("dsh bin.js not resolvable under "+DSH_CACHE)
        else:
            log("[ok] dsh bin.js = "+binjs)
    # 2) key 可读（winreg 三级；不打印值）
    key=None
    try:
        import winreg
        for hive,sub in [(winreg.HKEY_CURRENT_USER,"Environment"),
                         (winreg.HKEY_LOCAL_MACHINE,r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")]:
            try:
                with winreg.OpenKey(hive,sub) as k:
                    v,_=winreg.QueryValueEx(k,"DEEPSEEK_API_KEY")
                    if v: key="present"
            except Exception:
                pass
    except Exception:
        pass
    if not key:
        key=os.environ.get("DEEPSEEK_API_KEY","")
    if not key:
        hard("DEEPSEEK_API_KEY unavailable (no registry + no env)")
    else:
        log("[ok] DEEPSEEK_API_KEY readable")
    # 3) git 工作区干净（v0.3 起应始终干净；有未提交改动算软警告）
    if os.path.isdir(os.path.join(BASE,".git")):
        try:
            p=subprocess.run('git -C "%s" status --porcelain'%BASE, shell=True, capture_output=True, text=True, encoding="utf-8", timeout=30)
            dirty=[l for l in p.stdout.splitlines() if l.strip() and not l.startswith("??")]
            if dirty:
                soft("git working tree has %d tracked modifications"%len(dirty))
            else:
                log("[ok] git working tree clean")
        except Exception as e:
            soft("git status check error: "+str(e))
    else:
        hard("D:/agent-os is not a git repository")
    # 4) reasoning 文件堆积
    if os.path.isdir(PENDING):
        rs=set()
        for pat in ("*.reasoning.txt","*.gate.reasoning.txt"):
            for f in glob.glob(os.path.join(PENDING, pat)):
                rs.add(f)
        rs=list(rs)
        total=sum(os.path.getsize(f) for f in rs if os.path.isfile(f))
        log("[ok] reasoning files=%d total_mb=%.1f" % (len(rs), total/1024/1024))
        if len(rs)>50 or total>500 * 1024 * 1024:
            soft("reasoning accumulation: files=%d size_mb=%.1f (cleanup should handle)" % (len(rs), total/1024/1024))
    # 5) 上次调度是否按时跑（防任务静默死亡）
    last=None
    try:
        with open(LOG,"r",encoding="utf-8",errors="replace") as f:
            for line in f:
                if "dispatch start" in line:
                    m=__import__("re").search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]",line)
                    if m: last=m.group(1)
    except Exception:
        pass
    if last:
        try:
            lt=datetime.strptime(last,"%Y-%m-%d %H:%M")
            gap=(datetime.now()-lt).total_seconds()/3600
            log("[ok] last dispatch %.1fh ago (%s)"%(gap,last))
            if gap>5 and mode=="pre":
                soft("last dispatch %.1fh ago (>4h window), scheduler may be stale"%gap)
        except Exception:
            pass
    # 6) 必需脚本存在
    for sf in ["evolve_dispatch.py","gate_review_dispatch.py","postprocess_dispatch.py","cleanup_dispatch.py","observe_report.py","merge_advisor.py","dashboard.py"]:
        if not os.path.isfile(os.path.join(SCRIPTS,sf)):
            hard("missing script: "+sf)
    # 判定
    if HARD_FAILS:
        log("HEALTH STATUS: hard-fail count=%d"%len(HARD_FAILS))
        for h in HARD_FAILS: log("  - "+h)
        if mode=="pre":
            log("HEALTH ABORT: skip propose/gate this round")
            return 1
    else:
        log("HEALTH STATUS: healthy")
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log("[HEALTH-HARD-FAIL] exception: "+str(e))
        sys.exit(1)
