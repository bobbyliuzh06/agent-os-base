import os, sys, json, re
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent/"BASE"/"scripts"))
from gate_review_adapter import review, DENY_PATTERNS, ALLOW_PATH_PREFIX

def test_accept_clean_proposal(sample_proposal):
    g = review(sample_proposal, "demo")
    assert g["gate"] == "accept"
    assert g["auto_merge"] is False
    assert g["risk"] == "low"

@pytest.mark.parametrize("bad", [
    "deliverables", "steps", "scope_in", "rollback"
])
def test_deny_writes_base_in_any_field(sample_proposal, bad):
    p = json.loads(json.dumps(sample_proposal))
    p[bad] = ["把结果写入 BASE/META/config.json"]
    g = review(p, "demo")
    assert g["gate"] == "reject"
    assert any("BASE" in r or "写BASE" in r for r in g["reasons"])

def test_deny_scheduled_task_change(sample_proposal):
    p = json.loads(json.dumps(sample_proposal))
    p["steps"] = ["用 schtasks 把 AgentOS_EvolveDispatch 改成每小时"]
    g = review(p, "demo")
    assert g["gate"] in ("reject","escalate")

def test_deny_pending_writes(sample_proposal):
    p = json.loads(json.dumps(sample_proposal))
    p["steps"] = ["清理 PENDING/ 下旧文件"]
    g = review(p, "demo")
    assert g["gate"] == "reject"

def test_deny_destructive_commands(sample_proposal):
    p = json.loads(json.dumps(sample_proposal))
    p["steps"] = ["rmdir /s /q D:/agent-os/BASE"]
    g = review(p, "demo")
    assert g["gate"] == "reject"

def test_deny_secret_in_output(sample_proposal):
    p = json.loads(json.dumps(sample_proposal))
    p["deliverables"] = ["tasks/demo/task-evolve/out/key.txt 内容 sk-demoXXXX1234567890"]
    g = review(p, "demo")
    assert g["gate"] == "reject"
    assert any("密钥" in r for r in g["reasons"])

def test_escalate_base_change_required(sample_proposal):
    p = json.loads(json.dumps(sample_proposal))
    p["base_change_required"] = True
    g = review(p, "demo")
    assert g["gate"] == "escalate"

def test_reject_tool_calls(sample_proposal):
    p = json.loads(json.dumps(sample_proposal))
    p["tool_calls"] = [{"name":"write_file","args":{}}]
    g = review(p, "demo")
    assert g["gate"] == "reject"

def test_deliverable_must_be_task_local(sample_proposal):
    p = json.loads(json.dumps(sample_proposal))
    p["deliverables"] = ["/etc/passwd", "tasks/demo/task-evolve/ok.md"]
    g = review(p, "demo")
    assert g["gate"] == "reject"

def test_mock_propose_no_tool_calls():
    sys.path.insert(0, str(Path(__file__).parent.parent/"BASE"/"scripts"))
    from proposer import mock_propose
    p = mock_propose("领域:demo 目标:测试", "demo")
    assert p["tool_calls"] == []
    assert p["base_change_required"] is False
    assert all(d.startswith("tasks/demo/task-evolve/") for d in p["deliverables"])

def test_proposer_schema_fields():
    from proposer import mock_propose, SCHEMA_REQUIRED
    p = mock_propose("领域:seo 目标:关键词分析", "seo")
    for k in SCHEMA_REQUIRED:
        assert k in p, "缺少字段 %s" % k
