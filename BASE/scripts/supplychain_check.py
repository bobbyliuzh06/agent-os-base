#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""supplychain_check：供应链配置只读校验（STEP42B）。
- 打印仓库基本属性与指定 Release 的 draft/prerelease/资产列表（gh api，只读）。
- immutability：REST 无对应字段 → 仅提示人工确认 Settings→Releases。
- attestation 可用性：只打印验证命令，不执行任何写操作（不 create/upload/delete release）。
"""
import argparse
import os
import subprocess
import sys

_GH = "gh"
if not os.path.isdir("C:\\Program Files\\GitHub CLI"):
    _GH = "gh"
elif os.path.exists("C:\\Program Files\\GitHub CLI\\gh.exe"):
    _GH = "C:\\Program Files\\GitHub CLI\\gh.exe"


def _gh(*args, repo):
    cmd = [_GH, "api"] + list(args)
    if repo:
        cmd += ["-R", repo]
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main(argv=None):
    if sys.stdout.encoding.lower().startswith("utf"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="bobbyliuzh06/agent-os-base")
    ap.add_argument("--tag", default="v0.4.5")
    ns = ap.parse_args(argv)
    r = _gh("repos/%s" % ns.repo, "--jq",
            "{default_branch, visibility, allow_update_branch}", repo=None)
    print("REPO", r.stdout.strip() or r.stderr.strip()[:120])
    r = _gh("repos/%s/releases/tags/%s" % (ns.repo, ns.tag), "--jq",
            "{tag:.tag_name,draft:.draft,prerelease:.prerelease,assets:[.assets[].name]}",
            repo=None)
    print("RELEASE", r.stdout.strip() or r.stderr.strip()[:120])
    print("IMMUTABILITY: REST 无字段；需人工确认 Settings→Releases→Enable release immutability（仅影响未来 Release）")
    print("ATTESTATION_VERIFY_COMMANDS(只读，不执行写):")
    print("  gh release verify %s -R %s" % (ns.tag, ns.repo))
    print("  gh release verify-asset %s <local-zip> -R %s" % (ns.tag, ns.repo))
    print("  gh attestation verify <local-zip> -R %s" % ns.repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
