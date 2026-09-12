#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, glob, sys, json
from datetime import datetime

BASE="D:/agent-os"
PENDING=os.path.join(BASE,"PENDING")
SCRIPTS=os.path.join(BASE,"BASE","scripts")
ADVICE=os.path.join(PENDING,"merge_advice.md")
WHITELIST=os.path.join(BASE,"BASE","META","merge_whitelist.json")

def log(s):
    print(s, flush=True)

def parse_head(path, keys):
    out={}
    try:
        with open(path,"r",encoding="utf-8",errors="replace") as f:
            for line in f:
                line=line.strip()
                for k in keys:
                    m=re.match(re.escape(k)+r"\s*[:=]\s*(.+)",line)
                    if m:
                        out[k]=m.group(1).strip(); break
                if len(out)>=len(keys): break
    except Exception:
        pass
    return out

def load_whitelist():
    if os.path.isfile(WHITELIST):
        try:
            with open(WHITELIST,"r",encoding="utf-8-sig") as f:
                d=json.load(f)
            if isinstance(d,dict):
                return d
        except Exception:
            pass
    return {"allow_paths":[], "allow_risk":["low"], "max_auto_files":5}

def propose_files_from_review(review_path):
    # 从 review.txt 粗略抽取“拟修改/新增文件”相对BASE的路径；仅用于建议，不自动判定合法性
    files=[]
    try:
        with open(review_path,"r",encoding="utf-8",errors="replace") as f:
            txt=f.read()
    except Exception:
        return files
    for m in re.finditer(r"(?:修改|新增|文件)[^\n]*?([A-Za-z]:[\\/][^\s\"']+|D:/agent-os/[^\s\"']+)", txt):
        p=m.group(1).replace("/","\\")
        if os.path.isfile(p):
            files.append(p)
    # 也匹配 review 里常见的相对 BASE 路径
    for m in re.finditer(r"BASE[\\/]([^\s\"']+\.(py|md|bat|json|js))", txt):
        p=os.path.join(BASE,"BASE",m.group(1)).replace("/","\\")
        if os.path.isfile(p):
            files.append(p)
    uniq=[]
    for p in files:
        if p not in uniq: uniq.append(p)
    return uniq

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    now=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wl=load_whitelist()
    allow_paths=[p.replace("/","\\") for p in wl.get("allow_paths",[])]
    allow_risk=set(x.lower() for x in wl.get("allow_risk",["low"]))
    max_files=int(wl.get("max_auto_files",5))

    gates=sorted(glob.glob(os.path.join(PENDING,"*.gate.txt")))
    rows=[]
    for g in gates:
        kv=parse_head(g,["GATE_STATUS","GATE_RISK","STATUS","RISK"])
        st=(kv.get("GATE_STATUS") or kv.get("STATUS") or "unknown").lower()
        rk=(kv.get("GATE_RISK") or kv.get("RISK") or "unknown").lower()
        base=g[:-len(".gate.txt")]
        review=base+".review.txt"
        pending_md=base+".md"
        if st!="accept":
            rows.append((os.path.basename(g),st,rk,"skip:not-accept","",""))
            continue
        if rk not in allow_risk:
            rows.append((os.path.basename(g),st,rk,"skip:risk-not-in-whitelist","",""))
            continue
        files=propose_files_from_review(review) if os.path.isfile(review) else []
        # 白名单路径前缀校验
        ok_files=[]
        bad_files=[]
        for fpath in files:
            fp=fpath.replace("/","\\")
            if any(fp.startswith(ap) for ap in allow_paths) or not allow_paths:
                ok_files.append(fp)
            else:
                bad_files.append(fp)
        if bad_files:
            rows.append((os.path.basename(g),st,rk,"skip:files-out-of-whitelist:"+";".join(bad_files),"",""))
            continue
        if len(ok_files)>max_files:
            rows.append((os.path.basename(g),st,rk,"skip:too-many-files(%d>%d)"%(len(ok_files),max_files),"",""))
            continue
        branch="auto/"+os.path.basename(base).replace(".","-")+"-"+now.replace(":","").replace(" ","T")
        cmds=[]
        cmds.append('git -C "%s" checkout -b %s'%(BASE,branch))
        for fp in ok_files:
            rel=os.path.relpath(fp,BASE).replace("\\","/")
            cmds.append('git -C "%s" add "%s"'%(BASE,rel))
        msg="chore(agent-os): auto-merge candidate %s (gate=accept risk=%s)"%(os.path.basename(base),rk)
        cmds.append('git -C "%s" commit -m "%s"'%(BASE,msg))
        tag="agent-os/auto/"+now.replace(":","-").replace(" ","T")+"/"+os.path.basename(base)
        cmds.append('git -C "%s" tag -a %s -m "auto-merge dry-run candidate"'%(BASE,tag))
        cmds.append('# dry-run only; apply requires .auto_merge_on + regression all-green + human ack file')
        rows.append((os.path.basename(g),st,rk,"ready-dryrun",branch,"\n".join(cmds)))
    with open(ADVICE,"w",encoding="utf-8") as f:
        f.write("# merge advice (dry-run) %s\n"%now)
        f.write("- mode: dry-run-only (no commit/tag/push performed)\n")
        f.write("- whitelist: %s\n"%WHITELIST+"\n")
        for name,st,rk,verdict,branch,cmds in rows:
            f.write("\n## %s\n- GATE_STATUS=%s GATE_RISK=%s\n- verdict=%s\n"%(name,st,rk,verdict))
            if branch: f.write("- branch=%s\n"%branch)
            if cmds: f.write("- plan:\n```\n%s\n```\n"%cmds)
    for r in rows:
        log("ADVICE %s status=%s risk=%s verdict=%s"%(r[0],r[1],r[2],r[3]))
    log("merge_advice written: %s"%ADVICE)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("merge_advisor error: " + str(e))
        sys.exit(1)
