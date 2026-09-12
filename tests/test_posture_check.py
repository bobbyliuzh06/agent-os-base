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
        if args[0] == "ls-remote" and args[1] == "refs/heads/main":
            return subprocess.CompletedProcess(args, 0,
                ("%s\trefs/heads/main\n" % remote_main) if remote_main else "", "")
        if args[0] == "ls-remote" and args[1] == "--tags":
            return subprocess.CompletedProcess(args, 0, tags_text or _tags_output(), "")
        if args[0] == "rev-list":
            return subprocess.CompletedProcess(args, 0, ("%d\n" % (ahead if "..HEAD" in args[1] else behind)), "")
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
    assert any("remote-only tags" in i for i in rec["issues"])

def test_posture_check_local_only_tag(tmp_path, monkeypatch, base_snap):
    snap = dict(base_snap)
    snap["v0.2.0"] = {"type": "commit", "obj": "894644566ca2", "peel": "894644566ca2"}
    monkeypatch.setattr(pc, "_run", _make_fake())
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: snap)
    rec = pc.run_posture("repo", str(tmp_path / "out"))
    assert rec["local_only_tags"] == ["v0.2.0"]
    assert any("local-only tags" in i for i in rec["issues"])

def test_posture_check_diverged_tag(tmp_path, monkeypatch):
    snap = {"v0.4.3-cleanbase": {"type": "tag", "obj": "cccccccccccccccccccccccccccccccccccccccc", "peel": PEEL_SHA}}
    monkeypatch.setattr(pc, "_run", _make_fake())
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: snap)
    rec = pc.run_posture("repo", str(tmp_path / "out"))
    assert rec["diverged_tags"] == ["v0.4.3-cleanbase"]
    assert rec["healthy"] is False
    assert any("diverged tags" in i for i in rec["issues"])

def test_posture_check_no_fetch(tmp_path, monkeypatch, base_snap):
    calls = []
    monkeypatch.setattr(pc, "_run", _make_fake(calls=calls))
    monkeypatch.setattr(pc, "_snapshot_local", lambda repo: dict(base_snap))
    pc.run_posture("repo", str(tmp_path / "out"))
    assert not any(c[0] == "fetch" for c in calls)
    assert not any("fetch" in c for c in calls)
