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
_DEFAULT_ALLOW = str(pathlib.Path(_C.root) / "BASE" / "scripts" / "posture_allow.yaml")

_EMPTY_ALLOW = {
    "known_local_only_tags": [],
    "max_acceptable_ahead": 0,
    "ignore_issue_types": [],
    "never_ignore": [
        "remote_main_moved", "head_diverges", "remote_only_unknown_tag",
        "diverged_tag", "local_only_unknown_tag", "uncommitted_changes"],
}


def load_allow(path):
    """读取白名单（.yaml 优先，缺 PyYAML 时回退 .json）。缺失/损坏返回空规则。"""
    p = pathlib.Path(path) if path else None
    try:
        if p is not None and p.exists():
            text = p.read_text(encoding="utf-8")
            if p.suffix.lower() in (".yaml", ".yml"):
                import yaml
                data = yaml.safe_load(text) or {}
            else:
                data = json.loads(text) if text.strip() else {}
            if not isinstance(data, dict):
                return dict(_EMPTY_ALLOW)
            out = dict(_EMPTY_ALLOW)
            out["known_local_only_tags"] = list(data.get("known_local_only_tags") or [])
            out["max_acceptable_ahead"] = int(data.get("max_acceptable_ahead", 0) or 0)
            out["ignore_issue_types"] = list(data.get("ignore_issue_types") or [])
            out["never_ignore"] = list(data.get("never_ignore") or _EMPTY_ALLOW["never_ignore"])
            return out
    except Exception:
        pass
    return dict(_EMPTY_ALLOW)


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


def run_posture(repo, out_dir, allow_file=None):
    allow = load_allow(allow_file)
    known = set(allow.get("known_local_only_tags") or [])
    ignore_types = set(allow.get("ignore_issue_types") or [])
    limit = allow.get("max_acceptable_ahead", 0)
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
    if local_origin_main is not None:
        r = _run(["rev-list", "--count", "%s..HEAD" % local_origin_main], repo)
        ahead = int(r.stdout.strip() or 0) if r.returncode == 0 else 0
        r = _run(["rev-list", "--count", "HEAD..%s" % local_origin_main], repo)
        behind = int(r.stdout.strip() or 0) if r.returncode == 0 else 0

    # ---- 白名单分级：issues（真异常）与 infos（已知/可接受，降噪）----
    issues, infos = [], []
    known_local = [t for t in local_only if t in known]
    unknown_local = [t for t in local_only if t not in known]
    if known_local:
        if "local_only_known" in ignore_types:
            infos.append({"type": "local_only_known", "tags": known_local,
                          "msg": "known local-only tags (whitelisted), not published"})
        else:
            issues += [{"type": "local_only_tag", "tag": t} for t in known_local]
    issues += [{"type": "local_only_unknown_tag", "tag": t} for t in unknown_local]  # 永不抑制
    if ahead > 0:
        if ahead <= limit and "ahead_within_limit" in ignore_types:
            infos.append({"type": "ahead_within_limit", "ahead": ahead, "limit": limit})
        else:
            issues.append({"type": "local_ahead", "ahead": ahead, "limit": limit})
    # ---- 永不抑制项 ----
    if local_origin_main is None:
        issues.append({"type": "origin_main_missing"})
    if remote_main and local_origin_main and remote_main != local_origin_main:
        issues.append({"type": "remote_main_moved",
                       "remote_main": remote_main, "local_origin_main": local_origin_main})
    if remote_main and remote_main != local_head:
        issues.append({"type": "head_diverges", "ahead": ahead, "behind": behind})
    issues += [{"type": "remote_only_unknown_tag", "tag": t} for t in remote_only]
    issues += [{"type": "diverged_tag", "tag": t} for t in diverged]

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
        "infos": infos,
        "healthy": healthy,
        "allow": {
            "known_local_only_tags_count": len(known),
            "max_acceptable_ahead": limit,
            "ignore_issue_types": sorted(ignore_types),
            "never_ignore": sorted(allow.get("never_ignore") or []),
        },
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
    print("LOCAL_ONLY=%s REMOTE_ONLY=%s DIVERGED=%s" % (local_only, remote_only, diverged))
    print("ISSUES=%d INFOS=%d HEALTHY=%s" % (len(issues), len(infos), healthy))
    for i in infos:
        print("  INFO %s" % json.dumps(i, ensure_ascii=False))
    for i in issues:
        print("  ISSUE %s" % json.dumps(i, ensure_ascii=False))
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
    ap.add_argument("--allow-file", default=_DEFAULT_ALLOW)
    ns = ap.parse_args(argv)
    run_posture(ns.repo, ns.out_dir, allow_file=ns.allow_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
