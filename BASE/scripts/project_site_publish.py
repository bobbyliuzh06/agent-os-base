# -*- coding: utf-8 -*-
"""project_site_publish.py —— 展示站发布快照自动提交（BASE 组件草案，P-8 action）。
挂载于 dispatch 第 6f 步（feedback 之后）：
1) 比较 tasks 站点（site gen 产物）与仓库 site/ 发布快照，无差异则跳过（0 成本）；
2) 有差异：仅 copy site/index.html + site/truth.json → site/；
3) 安全边界：只 git add 这两个文件；工作区存在其他 staged/unstaged 变更时拒绝并如实记录
   （绝不把未授权内容混入发布提交）；非 main 分支拒绝；
4) commit 消息固定前缀 [auto-site]；push origin main；失败如实 rc=1 不中断调度。
AGENT_OS_DRY=1：只比较+报告，不写不提交。"""
import io, os, pathlib, subprocess, sys
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import get_root

ROOT = get_root()
P2 = pathlib.Path(os.environ.get("AGENT_OS_PROJECT_P2", str(ROOT / "tasks" / "project-layer-p2-20260912" / "task-evolve")))
REGR = ROOT / "BASE" / "regression-runs"
DRY = os.environ.get("AGENT_OS_DRY") == "1"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
FILES = ["index.html", "truth.json"]

def git(args, cwd=None):
    r = subprocess.run(["git", "-C", str(cwd or ROOT)] + args, capture_output=True, text=True)
    return r

def same_bytes():
    for f in FILES:
        a = P2 / "site" / f
        b = ROOT / "site" / f
        if not b.exists():
            return False
        if a.read_bytes() != b.read_bytes():
            return False
    return True

def main():
    if same_bytes():
        print("PROJECT_SITE_PUBLISH skip: snapshot up to date")
        return 0
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if branch != "main":
        print("PROJECT_SITE_PUBLISH refuse: branch=%s (only main)" % branch)
        return 1
    status = git(["status", "--short"]).stdout.strip()
    allowed = {"site/index.html", "site/truth.json"}
    dirty = [l for l in status.splitlines() if l.strip() and l[3:].strip() not in allowed]
    if dirty and not DRY:
        print("PROJECT_SITE_PUBLISH refuse: worktree has other changes: %s" % dirty[:3])
        return 1
    if DRY:
        print("PROJECT_SITE_PUBLISH dry: would copy %s and commit [auto-site]" % FILES)
        return 0
    for f in FILES:
        (ROOT / "site" / f).write_bytes((P2 / "site" / f).read_bytes())
    r = git(["add", "site/index.html", "site/truth.json"])
    if r.returncode != 0:
        print("PROJECT_SITE_PUBLISH add failed: %s" % r.stderr[:120])
        return 1
    diff = git(["diff", "--cached", "--stat"]).stdout.strip()
    if not diff:
        print("PROJECT_SITE_PUBLISH skip: no staged change after add")
        return 0
    r = git(["commit", "-m", "[auto-site] publish showcase snapshot %s" % NOW])
    if r.returncode != 0:
        print("PROJECT_SITE_PUBLISH commit failed: %s" % (r.stderr or r.stdout)[:200])
        return 1
    r = git(["push", "origin", "main"])
    if r.returncode != 0:
        print("PROJECT_SITE_PUBLISH push failed: %s" % (r.stderr or r.stdout)[:200])
        return 1
    with open(REGR / "site-publish.log", "a", encoding="utf-8") as f:
        f.write("[%s] published %s\n" % (NOW, "; ".join(FILES)))
    print("PROJECT_SITE_PUBLISH published: %s" % diff.replace("\n", " "))
    return 0

if __name__ == "__main__":
    sys.exit(main())
