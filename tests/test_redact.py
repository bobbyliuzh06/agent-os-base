import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "BASE" / "scripts"))
from redact import redact

def test_redact_api_key():
    out = redact("x api_key=sk-fake1234567890abcdef y")
    assert "sk-fake" not in out
    assert "<REDACTED:api_key>" in out

def test_redact_aws_key():
    assert "<REDACTED:aws_key>" in redact("AKIA1234567890ABCDEF")

def test_redact_github_token():
    out = redact("token=ghp_fakefakefakefakefake12345678")
    assert "ghp_" not in out
    assert "<REDACTED:github_token>" in out

def test_redact_generic_credential():
    assert "<REDACTED:credential>" in redact("password=hunter2 secret:abc123")

def test_redact_leaves_normal_text():
    s = "COUNT 32 files, 3492 lines"
    assert redact(s) == s

def test_redact_non_str_passthrough():
    assert redact(None) is None
    assert redact(123) == 123
