#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-os sync：入站同步。git 模式仅合入 base_subtree；release 模式仅解包 base_subtree。
默认只读；--apply 才写。所有路径走 config_loader，绝不出现根路径字面量。"""
import os, sys, json, shutil, subprocess, datetime, urllib.request, ssl, hashlib, tempfile, re
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

def _stamp(): return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
def _redact(u): return re.sub(r"https://[^@]+@", "https://***@", u) if u else u

def log(msg, fh=None):
    line="[%s] %s"%( _stamp(), msg)
    print(line)
    if fh: 
        try: fh.write(line+"\n"); fh.flush()
        except Exception: pass

def open_log(C):
    d=C.regression; d.mkdir(parents=True, exist_ok=True)
    p=d/("sync-%s.log"%_stamp())
    return p, open(p,"a",encoding="utf-8")

def gh_cfg(C):
    g=C.get("github") or {}
    bd = g.get("backup_dir") or "BASE/regression-runs/sync-backup"
    if not os.path.isabs(bd):
        bd = str(C.root / bd)
    return {
        "enabled": bool(g.get("enabled",False)),
        "mode": g.get("mode","git"),
        "repo_url": (g.get("repo_url") or "").strip(),
        "branch": g.get("branch") or "main",
        "base_subtree": (g.get("base_subtree") or "BASE").strip("/\\"),
        "pattern": g.get("release_asset_pattern") or "agent-os-base-*.zip",
        "token_env": g.get("token_env") or "GH_TOKEN",
        "allow_dirty": bool(g.get("allow_dirty",False)),
        "backup_dir": bd,
        "verify": bool(g.get("verify_checksum",True)),
        "only_base": bool(g.get("only_base_subtree",True)),
    }

def git(*args, cwd, env=None, check=True):
    e=dict(os.environ); 
    if env: e.update(env)
    return subprocess.run(["git"]+list(args), cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", env=e, check=check)

def tree_status(C):
    # 返回 (dirty_bool, changed_files_relative_to_root)
    try:
        r=git("status","--porcelain",cwd=C.root,check=False)
        out=r.stdout or ""
        files=[ln[3:].strip() for ln in out.splitlines() if len(ln)>=3]
        return (len(files)>0, files)
    except Exception as e:
        return (True, ["<git_error:%s>"%e])

def changes_outside_base(C, changed_files, base_subtree):
    inside=[f for f in changed_files if Path(f).parts and Path(f).parts[0].lower()==base_subtree.lower()]
    outside=[f for f in changed_files if f not in inside]
    return outside, inside

def backup_base(C, cfg, fh):
    bd=Path(cfg["backup_dir"]); bd.mkdir(parents=True, exist_ok=True)
    dst=bd/(_stamp())
    src=C.base_dir
    if src.exists():
        # 忽略 backup 目录自身，避免 copytree 递归进入目标
        shutil.copytree(src, dst/"BASE", dirs_exist_ok=True, ignore=shutil.ignore_patterns("sync-backup"))
        log("backup BASE -> %s"%dst, fh)
        return dst
    return None

def ls_remote(git_url, token=None):
    url=git_url
    env={}
    if token and url.startswith("https://"):
        url=url.replace("https://","https://%s@"%token,1)
    try:
        r=subprocess.run(["git","ls-remote",url],capture_output=True,text=True,encoding="utf-8",env={**os.environ,**env},check=False,timeout=30)
        return r.returncode==0, r.stdout
    except Exception as e:
        return False, str(e)

def github_api_latest(repo_url, token=None):
    m=re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$",repo_url)
    if not m: return None
    owner,repo=m.group(1),m.group(2)
    api="https://api.github.com/repos/%s/%s/releases/latest"%(owner,repo)
    req=urllib.request.Request(api, headers={"Accept":"application/vnd.github+json"})
    if token: req.add_header("Authorization","Bearer %s"%token)
    try:
        ctx=ssl.create_default_context()
        with urllib.request.urlopen(req,context=ctx,timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error":str(e)}

def plan_git(C,cfg,fh):
    if not cfg["repo_url"]:
        log("git mode: repo_url 为空，跳过。",fh); return None
    token=os.environ.get(cfg["token_env"],"") 
    ok,remote=ls_remote(cfg["repo_url"],token if token else None)
    if not ok:
        log("git ls-remote 失败: %s"%( _redact(remote) ),fh); return None
    # 取目标分支最新 sha
    target=None
    for line in (remote or "").splitlines():
        if ("refs/heads/"+cfg["branch"]) in line:
            target=line.split()[0]; break
    local="unknown"
    try: local=git("rev-parse","HEAD",cwd=C.root,check=False).stdout.strip()
    except Exception: pass
    log("git plan: local=%s target=%s repo=%s"%(local,target,_redact(cfg["repo_url"])),fh)
    dirty,files=tree_status(C)
    if cfg["only_base"] and files:
        outside,inside=changes_outside_base(C,files,cfg["base_subtree"])
        log("changed_total=%d inside_base=%d outside_base=%d"%(len(files),len(inside),len(outside)),fh)
        if outside and not cfg["allow_dirty"]:
            log("拒绝：远程/本地差量涉及非 base 路径，需先提交或设 allow_dirty。outside=%s"%outside[:20],fh)
            return {"action":"abort","reason":"non-base changes","outside":outside}
    return {"action":"fetch_merge","local":local,"target":target}

def apply_git(C,cfg,fh):
    backup_base(C,cfg,fh)
    token=os.environ.get(cfg["token_env"],"")
    url=cfg["repo_url"]
    env={}
    if token and url.startswith("https://"):
        url=url.replace("https://","https://%s@"%token,1)
    git("fetch",url,cfg["branch"],cwd=C.root,check=False,env=env)
    # 仅合并 base 子树：用 fetch 后 diff 过滤，再 merge -- 简化用 checkout 方式风险大，故采用：
    # 1) 计算 FETCH_HEAD 与 HEAD 差量文件；2) 若仅 base 子树则 merge，否则 abort
    diff=git("diff","--name-only","HEAD","FETCH_HEAD",cwd=C.root,check=False).stdout.splitlines()
    outside,inside=changes_outside_base(C,diff,cfg["base_subtree"])
    if outside and not cfg["allow_dirty"]:
        log("apply 中止：FETCH_HEAD 含非 base 变更：%s"%outside[:20],fh); return 1
    git("merge","--no-ff","-m","agent-os sync(auto,base-only) "+_stamp(),"FETCH_HEAD",cwd=C.root,check=False)
    log("git merge 完成（base-only）。如冲突需人工解决。",fh)
    return 0

def apply_release(C,cfg,fh):
    rel=github_api_latest(cfg["repo_url"])
    if not rel or rel.get("error"):
        log("release 获取失败: %s"%(rel.get("error") if rel else "none"),fh); return 1
    assets=rel.get("assets",[]) or []
    pat=re.compile(cfg["pattern"].replace("*",".*").replace(".zip","\\.zip"))
    pick=[a for a in assets if pat.search(a.get("name",""))]
    if not pick:
        log("未匹配 release 资产: pattern=%s"%cfg["pattern"],fh); return 1
    a=pick[0]; name=a.get("name"); dl=a.get("browser_download_url")
    token=os.environ.get(cfg["token_env"],"")
    req=urllib.request.Request(dl)
    if token: req.add_header("Authorization","Bearer %s"%token)
    td=tempfile.mkdtemp(prefix="agentsync_")
    zp=os.path.join(td,name)
    with urllib.request.urlopen(req,timeout=60) as r, open(zp,"wb") as f:
        f.write(r.read())
    # 校验 size/可选 hash
    if cfg["verify"]:
        digest=a.get("digest") or a.get("sha256") or (a.get("label") or "")
        if digest and ":" in str(digest):
            algo,hexv=digest.split(":",1)
            h=hashlib.new(algo); h.update(open(zp,"rb").read())
            if h.hexdigest().lower()!=hexv.lower():
                log("checksum 不匹配，中止。",fh); return 1
    backup_base(C,cfg,fh)
    # 解压到临时，再只拷贝 base_subtree 内容；防穿越
    ext=os.path.join(td,"ext"); os.makedirs(ext,exist_ok=True)
    shutil.unpack_archive(zp,ext)
    # 找资产内 base 目录
    cand=os.path.join(ext,cfg["base_subtree"])
    if not os.path.isdir(cand):
        # 可能资产根即 base
        cand=ext
    for root,_,fs in os.walk(cand):
        for fn in fs:
            full=os.path.join(root,fn); relp=os.path.relpath(full,cand)
            if ".." in relp.replace("\\","/"): continue
            dst=os.path.join(str(C.base_dir),relp)
            os.makedirs(os.path.dirname(dst),exist_ok=True)
            shutil.copy2(full,dst)
    log("release 解包完成，仅更新 base_subtree=%s 到 %s"%(cfg["base_subtree"],C.base_dir),fh)
    return 0

def run_check(C,cfg,fh):
    log("sync --check enabled=%s mode=%s repo=%s"%(cfg["enabled"],cfg["mode"],_redact(cfg["repo_url"])),fh)
    if not cfg["enabled"]:
        log("github.enabled=false：仅本地校验。建议填 repo_url/mode 后再用 --check 连远程。",fh); return 0
    if cfg["mode"]=="git":
        plan_git(C,cfg,fh)
    elif cfg["mode"]=="release":
        rel=github_api_latest(cfg["repo_url"])
        log("release latest tag=%s assets=%d"%(rel.get("tag_name") if isinstance(rel,dict) else rel, len(rel.get("assets",[])) if isinstance(rel,dict) else 0),fh)
    else:
        log("unknown mode",fh)
    return 0

def run_apply(C,cfg,fh):
    if not cfg["enabled"]:
        log("github.enabled=false，拒绝 --apply。",fh); return 1
    dirty,files=tree_status(C)
    if dirty and not cfg["allow_dirty"]:
        log("工作树脏，拒绝 --apply（先用 git commit 或 --allow-dirty 仅限 base）。changed=%d"%len(files),fh); return 1
    if cfg["mode"]=="git": return apply_git(C,cfg,fh)
    if cfg["mode"]=="release": return apply_release(C,cfg,fh)
    log("unknown mode",fh); return 1

if __name__=="__main__":
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
    ap.add_argument("--check",action="store_true"); ap.add_argument("--plan",action="store_true")
    ap.add_argument("--apply",action="store_true"); ap.add_argument("--yes",action="store_true")
    ap.add_argument("--mode",default=""); ap.add_argument("--tag",default="")
    ns=ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
    C=_lc(); cfg=gh_cfg(C); 
    if ns.mode: cfg["mode"]=ns.mode
    p,fh=open_log(C)
    try:
        if ns.apply:
            if not ns.yes:
                log("apply 需要 --yes 确认。",fh); sys.exit(1)
            rc=run_apply(C,cfg,fh); sys.exit(rc)
        else:
            rc=run_check(C,cfg,fh); sys.exit(rc)
    finally:
        try: fh.close()
        except Exception: pass
