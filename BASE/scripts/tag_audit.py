#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tag_audit：只读 tag 审计 + 恢复计划生成（STEP36B 防呆固化）。
- 默认 --dry-run：只盘点本地/远端 tag、计算差集、生成 recovery-plan.json（applied=false），不修改任何 ref。
- apply 恢复需 --apply --confirm 且环境变量 TAG_AUDIT_CONFIRM=yes，缺一即跳过。
- 明确不调用：fetch --prune-tags、fetch +refs/tags/*:refs/tags/* --prune、tag -f、push。
审计规则（同 POSTURE-v0.4.3-rev1.json audit_rules）：
  1. 禁止 git fetch --prune-tags
  2. 禁止 git fetch +refs/tags/*:refs/tags/* --prune
  3. 禁止 git fetch --tags 配合 --prune
  4. 只读盘点用 ls-remote --tags + for-each-ref + 脚本 diff
  5. 拉取新远端 tag 用 git fetch origin --tags --no-overwrite-tags（Git>=2.23）或对差集逐条 fetch
  6. 恢复前必做：备份快照 + cat-file -t 验对象可达 + recovery-plan(applied=false) + 人工确认
  7. annotated 恢复用 update-ref 保真；轻量 tag 用 tag <name> <commit>
  8. 禁止 tag -f 移动已发布/已上云 tag；禁止批量推送（不 --tags、不 --mirror）
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path


def _run(args, repo=None):
    cmd = ["git"]
    if repo:
        cmd += ["-C", repo]
    cmd += args
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def snapshot_local(repo=None):
    """for-each-ref 全量快照 -> {name: {type,obj,peel}}。"""
    r = _run(["for-each-ref",
              "--format=%(refname:short)%09%(objecttype)%09%(objectname)%09%(*objectname)",
              "refs/tags"], repo)
    out = {}
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or not parts[0]:
            continue
        out[parts[0]] = {"type": parts[1], "obj": parts[2],
                         "peel": parts[3] if len(parts) > 3 else ""}
    return out


def list_remote(remote="origin", repo=None):
    """ls-remote --tags 只读清单 -> set(name)，不含 ^{}。"""
    r = _run(["ls-remote", "--tags", remote], repo)
    tags = set()
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("refs/tags/"):
            name = parts[1][len("refs/tags/"):]
            if not name.endswith("^{}"):
                tags.add(name)
    return tags


def diff(repo=None):
    """返回 (local_only, remote_only, local_snapshot)。"""
    local = snapshot_local(repo)
    remote = list_remote(repo=repo)
    return sorted(set(local) - remote), sorted(remote - set(local)), local


def check_tag(tagname, repo=None):
    """返回 {type,obj,peel,reachable}；type in tag/commit/MISSING。"""
    obj_r = _run(["rev-parse", "--verify", "refs/tags/" + tagname], repo)
    if obj_r.returncode != 0:
        return {"type": "MISSING", "obj": "", "peel": "", "reachable": False}
    obj = obj_r.stdout.strip()
    type_r = _run(["cat-file", "-t", obj], repo)
    t = type_r.stdout.strip()
    peel_r = _run(["rev-parse", "refs/tags/%s^{}" % tagname], repo)
    peel = peel_r.stdout.strip() if peel_r.returncode == 0 else ""
    return {"type": t, "obj": obj, "peel": peel,
            "reachable": type_r.returncode == 0 and t in ("tag", "commit")}


def plan_recovery(tags, backup_dir, repo=None):
    """生成 recovery-plan.json（applied=false）。不执行 update-ref。"""
    plan = []
    for name in sorted(tags):
        info = check_tag(name, repo)
        if not info["reachable"]:
            raise SystemExit("UNREACHABLE_TAG_OBJECT: " + name)
        prefix = ("-C " + repo + " ") if repo else ""
        if info["type"] == "tag":
            cmd = "git %supdate-ref refs/tags/%s %s" % (prefix, name, info["obj"])
        else:
            cmd = "git %stag %s %s" % (prefix, name, info["obj"])
        plan.append({"tag": name, "type": info["type"], "object": info["obj"],
                     "command": cmd.strip(), "status": "pending"})
    doc = {"generated_at": datetime.datetime.now().isoformat(),
           "applied": False, "plan": plan}
    path = Path(backup_dir) / "recovery-plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc


def apply_recovery(plan_path, repo=None, confirm=False):
    """仅 confirm=True 才逐条执行；返回 {status, results}。"""
    p = Path(plan_path)
    if not p.exists():
        return {"status": "no-plan", "results": []}
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("applied"):
        return {"status": "already-applied", "results": []}
    if not confirm:
        return {"status": "skipped-no-confirm", "results": []}
    results = []
    for item in doc.get("plan", []):
        if item["type"] == "tag":
            r = _run(["update-ref", "refs/tags/" + item["tag"], item["object"]], repo)
        else:
            r = _run(["tag", item["tag"], item["object"]], repo)
        results.append({"tag": item["tag"], "rc": r.returncode,
                        "stderr": r.stderr.strip()[:200]})
        if r.returncode != 0:
            doc["applied"] = False
            doc["applied_at"] = datetime.datetime.now().isoformat()
            p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"status": "failed", "results": results}
    doc["applied"] = True
    doc["applied_at"] = datetime.datetime.now().isoformat()
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "applied", "results": results}


def main(argv=None):
    if sys.stdout.encoding.lower().startswith("utf"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="")
    ap.add_argument("--backup-dir", default="BASE/regression-runs/tag-backup")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true",
                    help="应用 recovery-plan（需 --confirm 且 TAG_AUDIT_CONFIRM=yes）")
    ap.add_argument("--confirm", action="store_true")
    ns = ap.parse_args(argv)
    repo = ns.repo or None
    backup = ns.backup_dir
    local = snapshot_local(repo)
    remote = list_remote(repo=repo)
    lo = sorted(set(local) - remote)
    ro = sorted(remote - set(local))
    print("LOCAL_TOTAL=%d REMOTE_TOTAL=%d" % (len(local), len(remote)))
    print("LOCAL_ONLY=%s" % (",".join(lo) if lo else "(none)"))
    print("REMOTE_ONLY=%s" % (",".join(ro) if ro else "(none)"))
    for name in sorted(local):
        info = check_tag(name, repo)
        print("MAP %s %s %s %s" % (name, info["type"], info["obj"][:7],
                                   info["peel"][:7] or "(lightweight)"))
    if lo:
        doc = plan_recovery(lo, backup, repo)
        plan_path = str(Path(backup) / "recovery-plan.json")
        print("RECOVERY_PLAN %s applied=%s items=%d" % (
            plan_path, doc["applied"], len(doc["plan"])))
        if ns.apply:
            if ns.confirm and os.environ.get("TAG_AUDIT_CONFIRM") == "yes":
                res = apply_recovery(plan_path, repo, confirm=True)
                print("APPLY_RESULT", res["status"], json.dumps(res["results"], ensure_ascii=False))
            else:
                print("APPLY_SKIPPED: 需要 --confirm 且 TAG_AUDIT_CONFIRM=yes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
