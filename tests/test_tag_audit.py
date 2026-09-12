import os, sys, json, subprocess
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent / "BASE" / "scripts"))
import tag_audit as ta

# ---- 辅助 ----

def _init_tmp_repo(path):
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    (path / "a.txt").write_text("1", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "a.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "c1"], check=True)
    c1 = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                        capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "-C", str(path), "tag", "-a", "v1", "-m", "annotated"], check=True)
    subprocess.run(["git", "-C", str(path), "tag", "lw1"], check=True)
    return str(path), c1

FIXED_LOCAL = {
    "v0.4.3-cleanbase": {"type": "tag", "obj": "a67d52d5", "peel": "06702c31"},
    "v0.4.0-base": {"type": "tag", "obj": "103f76c0", "peel": "7fa6f36f"},
    "v0.4.1-sandbox-live": {"type": "tag", "obj": "5a06488b", "peel": "de241cd0"},
    "v0.4.2-sandbox-hard": {"type": "tag", "obj": "8455cb30", "peel": "bc6891d6"},
    "v0.3.0-base": {"type": "tag", "obj": "30422f17", "peel": "d33ff637"},
    "v0.2.0": {"type": "commit", "obj": "89464456", "peel": "89464456"},
}

# ---- 测试 ----

def test_diff_local_only_five(monkeypatch):
    def fake_run(args, repo=None):
        if args[0] == "for-each-ref":
            lines = []
            for n, v in FIXED_LOCAL.items():
                lines.append("%s\t%s\t%s\t%s" % (n, v["type"], v["obj"], v["peel"]))
            return subprocess.CompletedProcess(args, 0, "\n".join(lines) + "\n", "")
        if args[0] == "ls-remote":
            return subprocess.CompletedProcess(args, 0,
                "a67d52d5\trefs/tags/v0.4.3-cleanbase\n06702c31\trefs/tags/v0.4.3-cleanbase^{}\n", "")
        if args[0] == "rev-parse":
            return subprocess.CompletedProcess(args, 0, "89464456\n", "")
        if args[0] == "cat-file":
            return subprocess.CompletedProcess(args, 0, "commit\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(ta, "_run", fake_run)
    lo, ro, local = ta.diff("repo")
    assert lo == ["v0.2.0", "v0.3.0-base", "v0.4.0-base", "v0.4.1-sandbox-live", "v0.4.2-sandbox-hard"]
    assert ro == []

def test_check_tag_types(tmp_path):
    repo, _ = _init_tmp_repo(tmp_path / "r")
    a = ta.check_tag("v1", repo)
    assert a["type"] == "tag" and a["reachable"] is True and a["peel"]
    lw = ta.check_tag("lw1", repo)
    assert lw["type"] == "commit" and lw["reachable"] is True
    missing = ta.check_tag("nope", repo)
    assert missing["type"] == "MISSING" and missing["reachable"] is False

def test_plan_recovery_never_calls_update_ref(tmp_path, monkeypatch):
    calls = []
    def fake_run(args, repo=None):
        calls.append(args[0])
        if args[0] == "rev-parse":
            return subprocess.CompletedProcess(args, 0, "aaaaaaaa\n", "")
        if args[0] == "cat-file":
            return subprocess.CompletedProcess(args, 0, "tag\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(ta, "_run", fake_run)
    bak = tmp_path / "backup"
    doc = ta.plan_recovery(["v0.4.0-base"], str(bak), "repo")
    assert doc["applied"] is False
    assert "update-ref" not in calls
    assert doc["plan"][0]["type"] == "tag"
    assert "update-ref" in doc["plan"][0]["command"]  # 只出现在计划文本里
    assert (bak / "recovery-plan.json").exists()

def test_apply_recovery_requires_confirm(tmp_path, monkeypatch):
    plan_path = tmp_path / "recovery-plan.json"
    plan_path.write_text(json.dumps({"applied": False, "plan": [
        {"tag": "v0.4.0-base", "type": "tag", "object": "aaaaaaaa",
         "command": "git update-ref refs/tags/v0.4.0-base aaaaaaaa", "status": "pending"}]}),
        encoding="utf-8")
    calls = []
    monkeypatch.setattr(ta, "_run", lambda args, repo=None: (calls.append(args[0]),
        subprocess.CompletedProcess(args, 0, "", ""))[1])
    r1 = ta.apply_recovery(plan_path, "repo", confirm=False)
    assert r1["status"] == "skipped-no-confirm"
    assert calls == []
    r2 = ta.apply_recovery(plan_path, "repo", confirm=True)
    assert r2["status"] == "applied"
    assert calls == ["update-ref"]
    assert json.loads(plan_path.read_text(encoding="utf-8"))["applied"] is True

def test_cli_dry_run_no_ref_change(tmp_path, capsys):
    repo, _ = _init_tmp_repo(tmp_path / "r2")
    bak = tmp_path / "backup"
    before = ta.snapshot_local(repo)
    rc = ta.main(["--repo", repo, "--backup-dir", str(bak)])
    after = ta.snapshot_local(repo)
    out = capsys.readouterr().out
    assert rc == 0
    assert before == after, "dry-run 不得修改任何 ref"
    assert "LOCAL_TOTAL=2" in out
    assert "RECOVERY_PLAN" in out and "applied=False" in out

def _fake_fetch_interceptor(recorded):
    real_run = ta.subprocess.run
    def fake_run(cmd, **k):
        if "fetch" in cmd:
            recorded.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return real_run(cmd, **k)
    return fake_run

# ---- STEP37 sync-remote-only ----

def _add_v043_tag(repo):
    subprocess.run(["git", "-C", repo, "tag", "v0.4.3-cleanbase"], check=True)

def test_sync_remote_only_dry_run_plans_only(tmp_path, monkeypatch):
    repo, _ = _init_tmp_repo(tmp_path / "r3")
    _add_v043_tag(repo)
    bak = tmp_path / "backup"
    recorded = []
    monkeypatch.setattr(ta, "_list_remote", lambda r: {"v0.4.3-cleanbase", "v0.5.0"})
    monkeypatch.setattr(ta.subprocess, "run", _fake_fetch_interceptor(recorded))
    before = ta.snapshot_local(repo)
    meta = ta.sync_remote_only(repo, str(bak), dry_run=True)
    assert meta["only_remote"] == ["v0.5.0"]
    assert len(meta["plan"]) == 1
    assert meta["plan"][0] == ["git", "-C", repo, "fetch", "origin",
                               "refs/tags/v0.5.0:refs/tags/v0.5.0"]
    assert recorded == []
    assert ta.snapshot_local(repo) == before
    assert (bak / "sync-remote-plan.json").exists()

def test_sync_remote_only_no_prune_or_overwrite(tmp_path, monkeypatch):
    repo, _ = _init_tmp_repo(tmp_path / "r4")
    _add_v043_tag(repo)
    bak = tmp_path / "backup"
    recorded = []
    monkeypatch.setattr(ta, "_list_remote", lambda r: {"v0.4.3-cleanbase", "v0.5.0", "v0.6.0"})
    monkeypatch.setattr(ta.sys, "argv", ["tag_audit.py", "--confirm"])
    monkeypatch.setenv("TAG_AUDIT_CONFIRM", "yes")
    monkeypatch.setattr(ta.subprocess, "run", _fake_fetch_interceptor(recorded))
    before = ta.snapshot_local(repo)
    meta = ta.sync_remote_only(repo, str(bak), dry_run=False)
    tokens = [tok for c in recorded for tok in c]  # 只检查命令 token，排除含 "no_prune" 的 tmp 路径
    assert all(tok != "--prune" and tok != "--prune-tags" for tok in tokens)
    assert all("+refs/tags" not in tok for tok in tokens)
    assert all("push" not in tok for tok in tokens)
    assert len(recorded) == 2  # 两个精确 fetch（被 mock 拦截，未真联网）
    assert all(c[-1].startswith("refs/tags/") and ":refs/tags/" in c[-1]
               and "*" not in c[-1] for c in recorded)
    assert len(meta["failed"]) == 0
    assert ta.snapshot_local(repo) == before  # 本地 tag 对象未被 overwrite

def test_sync_remote_no_confirm_is_dry(tmp_path, monkeypatch):
    repo, _ = _init_tmp_repo(tmp_path / "r5")
    _add_v043_tag(repo)
    bak = tmp_path / "backup"
    recorded = []
    monkeypatch.setattr(ta, "_list_remote", lambda r: {"v0.4.3-cleanbase", "v0.5.0"})
    monkeypatch.setattr(ta.subprocess, "run", _fake_fetch_interceptor(recorded))
    monkeypatch.delenv("TAG_AUDIT_CONFIRM", raising=False)
    monkeypatch.setattr(ta.sys, "argv", ["tag_audit.py"])
    meta1 = ta.sync_remote_only(repo, str(bak), dry_run=False)
    assert recorded == [], "缺 env 确认时不得 fetch"
    assert meta1["dry_run"] is False and meta1["plan"]
    monkeypatch.setenv("TAG_AUDIT_CONFIRM", "yes")
    monkeypatch.setattr(ta.sys, "argv", ["tag_audit.py", "--confirm"])
    ta.sync_remote_only(repo, str(bak), dry_run=False)
    assert len(recorded) == 1, "env+--confirm 后才执行精确 fetch"
    assert recorded[0][-1] == "refs/tags/v0.5.0:refs/tags/v0.5.0"
