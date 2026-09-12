#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""posture_check：只读发布态势巡检（STEP39）。
- 全部远端读取走 git ls-remote 直连，绝不 fetch/push/prune/update-ref/tag -f/reset/clean/rm，
  不更新 remote-tracking 引用、不写任何 ref。
- 输出 POSTURE-daily-<YYYYMMDD-HHMMSS>.json 与 POSTURE-daily-latest.json 到 regression-runs/posture-daily/（ignore 内）。
- healthy = 无任何 issue；issue 仅为报告，不自动修复。
"""
import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc
from tag_audit import _snapshot_local

_C = _lc()
_DEFAULT_REPO = str(_C.root)
_DEFAULT_OUT = str(pathlib.Path(_C.root) / "BASE" / "regression-runs" / "posture-daily")


def _run(args, repo):
    return subprocess.run(["git", "-C", repo] + args, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def _parse_ls_remote_tags(text):
    """ls-remote --tags 文本 -> (tags: {name: tagobj_sha}, peels: {name: commit_sha})。"""
    tags, peels = {}, {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2 or not parts[1].startswith("refs/tags/"):
            continue
        sha, ref = parts[0], parts[1]
        name = ref[len("refs/tags/"):]
        if name.endswith("^{}"):
            peels[name[:-3]] = sha
        else:
            tags[name] = sha
    return tags, peels


def run_posture(repo, out_dir):
    r = _run(["rev-parse", "HEAD"], repo)
    local_head = r.stdout.strip() if r.returncode == 0 else None
    r = _run(["rev-parse", "origin/main"], repo)
    local_origin_main = r.stdout.strip() if r.returncode == 0 else None
    r = _run(["ls-remote", "origin", "refs/heads/main"], repo)
    remote_main = r.stdout.split()[0] if r.stdout.strip() else None
    r = _run(["ls-remote", "--tags", "origin"], repo)
    remote_tags, remote_peels = _parse_ls_remote_tags(r.stdout)
    local_snap = _snapshot_local(repo)  # {name: {type,obj,peel}}
    local_names = set(local_snap)
    remote_names = set(remote_tags)

    remote_only = sorted(remote_names - local_names)
    local_only = sorted(local_names - remote_names)
    diverged = sorted(
        name for name in (remote_names & local_names)
        if remote_tags[name] != local_snap[name]["obj"])

    ahead, behind = 0, 0
    issues = []
    if local_origin_main is None:
        issues.append("local origin/main missing")
    else:
        r = _run(["rev-list", "--count", "%s..HEAD" % local_origin_main], repo)
        ahead = int(r.stdout.strip() or 0) if r.returncode == 0 else 0
        r = _run(["rev-list", "--count", "HEAD..%s" % local_origin_main], repo)
        behind = int(r.stdout.strip() or 0) if r.returncode == 0 else 0
    if remote_main and local_origin_main and remote_main != local_origin_main:
        issues.append("remote main moved since last fetch (need fetch to update local remote-tracking ref)")
    if remote_main and remote_main != local_head:
        issues.append("local HEAD diverges from remote main: ahead=%d behind=%d" % (ahead, behind))
    if remote_only:
        issues.append("remote-only tags: %s" % remote_only)
    if local_only:
        issues.append("local-only tags: %s" % local_only)
    if diverged:
        issues.append("diverged tags: %s" % diverged)
    if ahead > 0:
        issues.append("local ahead by %d commits" % ahead)

    healthy = len(issues) == 0
    rec = {
        "generated_at": datetime.datetime.now().isoformat(),
        "repo": str(repo),
        "local_head": local_head,
        "local_origin_main": local_origin_main,
        "remote_main": remote_main,
        "ahead": ahead,
        "behind": behind,
        "local_only_tags": local_only,
        "remote_only_tags": remote_only,
        "diverged_tags": diverged,
        "issues": issues,
        "healthy": healthy,
        "command": "posture_check.py --repo %s --out-dir %s" % (repo, out_dir),
        "read_only": True,
    }
    od = pathlib.Path(out_dir)
    od.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    (od / ("POSTURE-daily-%s.json" % stamp)).write_text(
        json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    (od / "POSTURE-daily-latest.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    print("LOCAL_HEAD=%s REMOTE_MAIN=%s AHEAD=%d BEHIND=%d" % (
        (local_head or "")[:12], (remote_main or "")[:12], ahead, behind))
    print("LOCAL_ONLY=%s REMOTE_ONLY=%s DIVERGED=%s ISSUES=%d HEALTHY=%s" % (
        local_only, remote_only, diverged, len(issues), healthy))
    return rec


def main(argv=None):
    if sys.stdout.encoding.lower().startswith("utf"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=_DEFAULT_REPO)
    ap.add_argument("--out-dir", default=_DEFAULT_OUT)
    ns = ap.parse_args(argv)
    run_posture(ns.repo, ns.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
