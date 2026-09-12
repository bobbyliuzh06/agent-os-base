#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-os publish：手动、强门禁、不自动 push。
默认 --dry：跑全部门禁，门禁全过才生成本地 release asset；
github.enabled=false 时拒绝远程发布，仅允许本地 asset。
真实远程发布需 --yes --repo 显式且 github.enabled=true；不直接 git push / 不直接建 GitHub Release（除非 --gh-upload 且 --yes）。"""
import os, sys, json, subprocess, re, zipfile, argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

def _run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return (r.stdout or "") + (r.stderr or ""), r.returncode
    except Exception as e:
        return str(e), 1

def main():
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("AGENT_OS_ROOT", ""))
    ap.add_argument("--dry", action="store_true", default=True)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--tag", default="v0.4.0-base")
    ap.add_argument("--repo", default="")
    ap.add_argument("--asset", default="")
    ap.add_argument("--gh-upload", action="store_true")
    ap.add_argument("--asset-from-HEAD", action="store_true",
                    help="dry 默认：从 HEAD 现场 git archive 生成干净资产并做门禁")
    ns = ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"] = ns.root
    C = _lc()
    gates = []
    def gate(name, ok, detail):
        gates.append((name, ok, detail))
        print("  [%s] %s %s" % ("PASS" if ok else "FAIL", name, detail))

    # 1) pytest（全量套件）
    out, rc = _run('python -m pytest "%s/tests/" -q' % C.root)
    m = re.search(r"(\d+) passed", out)
    gate("pytest_passed", bool(m) and int(m.group(1)) >= 68, ("%s passed" % m.group(1)) if m else out[-120:])
    # 2) scan hardcoded_d_drive
    out2, _ = _run('python "%s/scan_hardcoded.py"' % C.scripts_dir)
    gate("scan_hardcoded_d_drive_0", "[hardcoded_d_drive]" not in out2, "rows 见报告")
    # 3) doctor
    out3, _ = _run('python "%s/cmd_doctor.py"' % C.scripts_dir)
    bad = re.search(r"(DUPLICATE|ORPHAN|NAME_COLLISION|MISSING_REG)", out3)
    gate("doctor_no_dup_orphan_collision", not bad, "无重复/孤儿/碰撞" if not bad else bad.group(0))
    # 4) watch STATUS healthy
    dash = C.regression / "dashboard.txt"
    dash_txt = dash.read_text(encoding="utf-8", errors="replace") if dash.exists() else ""
    gate("watch_status_healthy", "STATUS: healthy" in dash_txt, dash_txt.splitlines()[1] if dash_txt else "no dashboard")
    # 5) sync 状态
    gh = C.get("github") or {}
    enabled = bool(gh.get("enabled", False))
    gate("sync_local_only", not enabled, "github.enabled=false（仅本地 asset，不远程发布）" if not enabled else "enabled=true 可连远程")
    # 6) 四锁与 task_layer
    locks_absent = not (C.meta_dir/".auto_merge_on").exists() and not (C.regression/"all_probe_green.flag").exists() and not (C.regression/"merge_acks").exists()
    gate("four_locks_off", locks_absent, "未建任何合并锁")
    tl = C.get("task_layer", "enabled")
    gate("task_layer_disabled", tl is False, "task_layer.enabled=%s" % tl)
    # 7) archive scope（tag 或 HEAD 现场生成）
    ref = "HEAD" if ns.asset_from_HEAD else ns.tag
    zip_name = "agent-os-base-HEAD.zip" if ns.asset_from_HEAD else ("agent-os-base-%s.zip" % ns.tag)
    zip_path = C.regression / zip_name
    _out, _rc = _run('git -C "%s" archive --format=zip -o "%s" %s' % (C.root, zip_path, ref))
    bad = 0
    if _rc == 0 and zip_path.exists():
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            bad = sum(1 for n in names if re.search(
                r"(/tasks/|/PENDING/|regression-runs/|\.step.*\.bak$|\.en_bak|__pycache__|\.pyc$|_probe_|PROJECTS/|\.idea/)", n, re.I))
    gate("archive_scope_ok", _rc == 0 and bad == 0, "zip entries bad=%d" % bad)

    passed = all(g[1] for g in gates)
    print("PUBLISH GATES: %s (%d/%d)" % ("ALL-PASS" if passed else "FAILED", sum(1 for g in gates if g[1]), len(gates)))
    if not passed:
        print("未过项：", "; ".join(g[0] for g in gates if not g[1]))
        print("publish 拒绝（门禁未全过），未生成发布。")
        return 1
    print("local asset: %s" % zip_path)
    if not enabled:
        print("github.enabled=false：仅本地 asset，不推送。如需远程发布请显式配置 repo 并 --yes --repo <url>。")
        return 0
    if ns.yes and ns.repo:
        print("建议人工在 GitHub 建 Release 并上传 asset，或使用：")
        print('  gh release create %s "%s" --repo %s' % (ns.tag, zip_path, ns.repo))
        if ns.gh_upload:
            out4, rc4 = _run('gh release create %s "%s" --repo %s' % (ns.tag, zip_path, ns.repo))
            print(out4[-400:])
            return rc4
        return 0
    print("远程发布需要 --yes 且 --repo 显式；本次未执行。")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print("publish error:", e)
        sys.exit(1)
