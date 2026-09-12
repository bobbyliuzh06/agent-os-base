import os, sys, json
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent / "BASE" / "scripts"))
import proposer as P


class _FakeC:
    def __init__(self, meta_dir):
        self.meta_dir = Path(meta_dir)

def test_config_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "_lc", lambda: _FakeC(tmp_path))
    c = P.load_proposer_config()
    assert c["default_model"] == "deepseek-v4-flash"
    assert c["code_model"] == "deepseek-v4-pro"
    assert c["temperature"]["structured"] == 0.2
    assert c["json_mode"] is True
    assert c["fail_fallback_mock"] is True
    assert len(c["key_sources"]) == 2

def test_config_file_override(tmp_path, monkeypatch):
    (tmp_path / "proposer.config.json").write_text(json.dumps({
        "default_model": "custom-flash",
        "temperature": {"structured": 0.7},
        "json_mode": False,
    }), encoding="utf-8")
    monkeypatch.setattr(P, "_lc", lambda: _FakeC(tmp_path))
    c = P.load_proposer_config()
    assert c["default_model"] == "custom-flash"
    assert c["temperature"]["structured"] == 0.7
    assert c["temperature"]["analysis"] == 1.0  # 未覆盖项保留默认
    assert c["json_mode"] is False
    assert c["base_url"] == "https://api.deepseek.com"

def test_v4_no_deepseek_chat_reasoner_refs():
    c = P.load_proposer_config()
    blob = json.dumps(c)
    assert "deepseek-chat" not in blob and "deepseek-reasoner" not in blob
    assert c["default_model"] == "deepseek-v4-flash"
    assert c["code_model"] == "deepseek-v4-pro"
    assert c["thinking"]["reasoning_effort"] in ("low", "high", "max")
    assert c["code_thinking"]["reasoning_effort"] in ("low", "high", "max")
    assert "code" not in c["temperature"], "thinking profile 不得配置 temperature"

def test_pick_code_kind():
    c = P.load_proposer_config()
    p = P._pick_proposer(c, "实现一个代码修复并补单测", "", True, None, False, None)
    assert p["kind"] == "code"
    assert p["model"] == "deepseek-v4-pro"
    assert p["temperature"] == 0.0
    assert p["max_tokens"] == 4096
    assert p["thinking"] is True  # pro + config enabled + 未禁用
    assert p["reasoning_effort"] == "high"

def test_pick_analysis_kind():
    c = P.load_proposer_config()
    p = P._pick_proposer(c, "数据分析与统计报表", "", True, None, False, None)
    assert p["kind"] == "analysis"
    assert p["temperature"] == 1.0
    assert p["thinking"] is False  # flash 不发 thinking

def test_pick_default_kind():
    c = P.load_proposer_config()
    p = P._pick_proposer(c, "一般任务描述", "", True, None, False, None)
    assert p["kind"] == "structured"
    assert p["model"] == "deepseek-v4-flash"
    assert p["temperature"] == 0.2
    assert p["max_tokens"] == 2048

def test_cli_overrides_config():
    c = P.load_proposer_config()
    p = P._pick_proposer(c, "一般任务描述", "deepseek-v4-pro", True, "high", False, 0.5)
    assert p["model"] == "deepseek-v4-pro"
    assert p["temperature"] == 0.5
    assert p["reasoning_effort"] == "high"

def test_no_think_disables_thinking():
    c = P.load_proposer_config()
    p = P._pick_proposer(c, "实现一个代码修复", "", True, None, True, None)
    assert p["thinking"] is False

def test_missing_key_fallback_mock_no_crash(monkeypatch):
    monkeypatch.setattr(P, "_resolve_api_key", lambda api_key: "")
    prop = P.propose("任意需求", "demo-task", live=True)
    assert prop["model"] == "error-fallback-mock"
    assert prop["base_change_required"] is False
    assert prop["tool_calls"] == []
    for k in P.SCHEMA_REQUIRED:
        assert k in prop

def test_resolved_key_sources_are_references_only(monkeypatch):
    c = P.load_proposer_config()
    assert "DEEPSEEK_API_KEY" in c["key_sources"][0]
    assert "winreg" in c["key_sources"][1]
    assert not any(k.startswith("sk-") for k in c["key_sources"])

def test_build_kwargs_thinking_omits_temperature():
    pick = {"model": "deepseek-v4-pro", "temperature": 0.0, "max_tokens": 4096,
            "thinking": True, "reasoning_effort": "high", "json_mode": True}
    kw = P._build_request_kwargs(pick, "SYS", "USR")
    assert "temperature" not in kw
    assert "top_p" not in kw
    assert kw["reasoning_effort"] == "high"
    assert kw["extra_body"] == {"thinking": {"type": "enabled"}}

def test_build_kwargs_no_thinking_has_temperature():
    pick = {"model": "deepseek-v4-flash", "temperature": 0.2, "max_tokens": 2048,
            "thinking": False, "reasoning_effort": "low", "json_mode": True}
    kw = P._build_request_kwargs(pick, "SYS", "USR")
    assert kw["temperature"] == 0.2
    assert "reasoning_effort" not in kw and "extra_body" not in kw

def test_reasoning_effort_coerced_to_v4_values():
    c = P.load_proposer_config()
    p = P._pick_proposer(c, "实现一个代码修复", "deepseek-v4-pro", True, "extreme", False, None)
    assert p["thinking"] is True
    assert p["reasoning_effort"] == "high"  # 非法值回退配置值
    p2 = P._pick_proposer(c, "一般任务", "deepseek-v4-pro", True, "max", False, None)
    assert p2["reasoning_effort"] == "max"

def test_pick_has_base_url():
    c = P.load_proposer_config()
    p = P._pick_proposer(c, "一般任务", "", True, None, False, None)
    assert p["base_url"] == "https://api.deepseek.com"
