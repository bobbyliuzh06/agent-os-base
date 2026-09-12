import os, sys, json, subprocess
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent / "BASE" / "scripts"))
import posture_check as pc

FORBIDDEN = ("fetch", "push", "prune", "update-ref", "tag -f", "reset", "clean", "rm")

MAIN_SHA = "cf421cf9c2ef252b20728ec74ebb4f38ca35de7a"
TAG_SHA = "a67d52d5a2cf5cd908bb2ad6363ec789821bf89b"
PEEL_SHA = "06702c3145e64b25bd1dc071e0b9420d3ea4b7a0"

def _tags_output(extra=None):
    """远端 ls-remote --tags 文本；extra: {name: (tagsha, peelsha)}。"""
    lines = ["%s\trefs/tags/v0.4.3-cleanbase" % TAG_SHA,
             "%s\trefs/tags/v0.4.3-cleanbase^{}" % PEEL_SHA]
    for name, (t, p) in (extra or {}).items():
        lines.append("%s\trefs/tags/%s" % (t, name))
        lines.append("%s\trefs/tags/%s^{}" % (p, name))
    return "\n".join(lines) + "\n"

def _make_fake(local_head=MAIN_SHA, local_origin_main=MAIN_SHA, remote_main=MAIN_SHA,
               tags_text=None, calls=None, local_snap=None, ahead=0, behind=0):
    def fake(args, repo):
        if calls is not None:
            calls.append(list(args))
        if args[0] == "rev-parse" and "HEAD" in args:
            return subprocess.CompletedProcess(args, 0, local_head + "\n", "")
        if args[0] == "rev-parse" and "origin/main" in args:
            return subprocess.CompletedProcess(args, 0, local_origin_main + "\n", "")
        if args[0] == "ls-remote" and "refs/heads/main" in args:
            return subprocess.CompletedProcess(args, 0,
                ("%s\trefs/heads/main\n" % remote_main) if remote_main else "", "")
        if args[0] == "ls-remote" and "--tags" in args:
            return subprocess.CompletedProcess(args, 0, tags_text or _tags_output(), "")
        if args[0] == "rev-list":
            return subprocess.CompletedProcess(args, 0,
                ("%d\n" % (ahead if "..HEAD" in args[-1] else behind)), "")
        return subprocess.CompletedProcess(args, 0, "", "")
    return fake

@pytest.fixture
def base_snap():
    return {"v0.4.3-cleanbase": {"type": "tag", "obj": TAG_SHA, "peel": PEEL_SHA}}

def test_posture_check_readonly_no_write_commands(tmp_path, monkeypatch, base_snap):
    calls = []
    monkeypatch.setattr(pc, "_run", _make_fake(calls=calls))
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: dict(base_snap))
    rec = pc.run_posture("repo", str(tmp_path / "out"))
    assert rec["read_only"] is True
    for cmd in calls:
        joined = " ".join(cmd)
        for tok in FORBIDDEN:
            assert tok not in cmd, "出现被禁写命令: %s (%s)" % (tok, cmd)
    assert any(c[0] == "ls-remote" for c in calls), "应使用 ls-remote 直读"

def test_posture_check_in_sync(tmp_path, monkeypatch, base_snap):
    monkeypatch.setattr(pc, "_run", _make_fake())
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: dict(base_snap))
    rec = pc.run_posture("repo", str(tmp_path / "out"))
    assert rec["healthy"] is True
    assert rec["local_only_tags"] == [] and rec["remote_only_tags"] == []
    assert rec["diverged_tags"] == []
    assert rec["ahead"] == 0 and rec["behind"] == 0

def test_posture_check_remote_only_tag(tmp_path, monkeypatch, base_snap):
    extra = {"v0.5.0": ("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", PEEL_SHA)}
    monkeypatch.setattr(pc, "_run", _make_fake(tags_text=_tags_output(extra)))
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: dict(base_snap))
    rec = pc.run_posture("repo", str(tmp_path / "out"))
    assert rec["remote_only_tags"] == ["v0.5.0"]
    assert rec["healthy"] is False
    assert any(i.get("type") == "remote_only_unknown_tag" and i.get("tag") == "v0.5.0"
               for i in rec["issues"])

def test_posture_check_local_only_tag(tmp_path, monkeypatch, base_snap):
    snap = dict(base_snap)
    snap["v0.2.0"] = {"type": "commit", "obj": "894644566ca2", "peel": "894644566ca2"}
    monkeypatch.setattr(pc, "_run", _make_fake())
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: snap)
    rec = pc.run_posture("repo", str(tmp_path / "out"))
    assert rec["local_only_tags"] == ["v0.2.0"]
    assert any(i.get("type") == "local_only_unknown_tag" and i.get("tag") == "v0.2.0"
               for i in rec["issues"])

def test_posture_check_diverged_tag(tmp_path, monkeypatch):
    snap = {"v0.4.3-cleanbase": {"type": "tag", "obj": "cccccccccccccccccccccccccccccccccccccccc", "peel": PEEL_SHA}}
    monkeypatch.setattr(pc, "_run", _make_fake())
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: snap)
    rec = pc.run_posture("repo", str(tmp_path / "out"))
    assert rec["diverged_tags"] == ["v0.4.3-cleanbase"]
    assert rec["healthy"] is False
    assert any(i.get("type") == "diverged_tag" and i.get("tag") == "v0.4.3-cleanbase"
               for i in rec["issues"])

def test_posture_check_no_fetch(tmp_path, monkeypatch, base_snap):
    calls = []
    monkeypatch.setattr(pc, "_run", _make_fake(calls=calls))
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: dict(base_snap))
    pc.run_posture("repo", str(tmp_path / "out"))
    assert not any(c[0] == "fetch" for c in calls)
    assert not any("fetch" in c for c in calls)

# ---- STEP42A whitelist ----

KNOWN5 = ["v0.2.0", "v0.3.0-base", "v0.4.0-base", "v0.4.1-sandbox-live", "v0.4.2-sandbox-hard"]

def _allow_yaml(tmp_path, known=None, max_ahead=0, ignore=None):
    p = tmp_path / "allow.yaml"
    lines = ["known_local_only_tags:"]
    for t in (known or []):
        lines.append("  - %s" % t)
    lines.append("max_acceptable_ahead: %d" % max_ahead)
    lines.append("ignore_issue_types:")
    for t in (ignore or []):
        lines.append("  - %s" % t)
    lines.append("never_ignore: [remote_main_moved, head_diverges, remote_only_unknown_tag, diverged_tag, local_only_unknown_tag, uncommitted_changes]")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)

def _snap_with_known(base_snap, extra=None):
    snap = dict(base_snap)
    for t in KNOWN5:
        snap[t] = {"type": "commit", "obj": "1111" + t[-4:].ljust(36, "1")[:36], "peel": t}
    if extra:
        snap[extra] = {"type": "commit", "obj": "9999999999999999999999999999999999999999", "peel": extra}
    return snap

def test_whitelist_known_local_only_is_info(tmp_path, monkeypatch, base_snap):
    allow = _allow_yaml(tmp_path, known=KNOWN5, max_ahead=0,
                        ignore=["local_only_known", "ahead_within_limit"])
    monkeypatch.setattr(pc, "_run", _make_fake())
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: _snap_with_known(base_snap))
    rec = pc.run_posture("repo", str(tmp_path / "out"), allow_file=allow)
    assert rec["healthy"] is True
    assert not any(i["type"].startswith("local_only") for i in rec["issues"])
    assert any(i.get("type") == "local_only_known" and i.get("tags") == KNOWN5
               for i in rec["infos"])

def test_whitelist_unknown_local_tag_still_issues(tmp_path, monkeypatch, base_snap):
    allow = _allow_yaml(tmp_path, known=KNOWN5, max_ahead=0,
                        ignore=["local_only_known", "ahead_within_limit"])
    monkeypatch.setattr(pc, "_run", _make_fake())
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: _snap_with_known(base_snap, extra="v9.9.9"))
    rec = pc.run_posture("repo", str(tmp_path / "out"), allow_file=allow)
    assert rec["healthy"] is False
    assert any(i.get("type") == "local_only_unknown_tag" and i.get("tag") == "v9.9.9"
               for i in rec["issues"])

def test_whitelist_ahead_within_limit_is_info(tmp_path, monkeypatch, base_snap):
    calls = []
    allow3 = _allow_yaml(tmp_path, known=[], max_ahead=3,
                         ignore=["local_only_known", "ahead_within_limit"])
    parent = "cf421cf9c2ef252b20728ec74ebb4f38ca35de7a"
    monkeypatch.setattr(pc, "_run",
                        _make_fake(local_origin_main=parent, ahead=3, calls=calls))
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: dict(base_snap))
    rec = pc.run_posture("repo", str(tmp_path / "out"), allow_file=allow3)
    assert any(i.get("type") == "ahead_within_limit" and i.get("ahead") == 3
               for i in rec["infos"])
    assert not any(i.get("type") == "local_ahead" for i in rec["issues"])
    assert not any("fetch" in c or "push" in c or "prune" in c for c in calls)
    # 阈值外：max=0 → 不降级
    allow0 = _allow_yaml(tmp_path, known=[], max_ahead=0,
                         ignore=["local_only_known", "ahead_within_limit"])
    rec2 = pc.run_posture("repo", str(tmp_path / "out"), allow_file=allow0)
    assert any(i.get("type") == "local_ahead" and i.get("ahead") == 3
               for i in rec2["issues"])
