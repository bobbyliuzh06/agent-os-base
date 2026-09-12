import os, sys, subprocess
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent / "BASE" / "scripts"))

BASE_SCRIPTS = str(Path(__file__).parent.parent / "BASE" / "scripts")

NET_PY = (
    "import urllib.request\n"
    "urllib.request.urlopen('http://example.com')\n"
    "print('LEAK')\n"
)

def _run_guarded(script, tmp_path):
    d = tmp_path / "case"
    d.mkdir()
    (d / "net.py").write_text(script, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = BASE_SCRIPTS + os.pathsep + env.get("PYTHONPATH", "")
    env["AGENT_SANDBOX_DIR"] = str(d)
    code = (
        "import sandbox_sitecustomize\n"
        "sandbox_sitecustomize.enable_sandbox_netguard()\n"
        "exec(open(%r, encoding='utf-8').read())\n" % str(d / "net.py")
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=60)
    return r

def test_module_import_does_not_autopatch():
    import socket
    real = socket.socket
    import sandbox_sitecustomize
    assert socket.socket is real, "import 不得自动生效"

def test_enable_blocks_socket(tmp_path):
    r = _run_guarded("import socket\nsocket.create_connection(('1.2.3.4', 80), 1)\nprint('LEAK')\n", tmp_path)
    assert "SandboxNetworkViolation" in r.stderr
    assert "LEAK" not in r.stdout

def test_enable_blocks_urllib(tmp_path):
    r = _run_guarded(NET_PY, tmp_path)
    assert "SandboxNetworkViolation" in r.stderr
    assert "LEAK" not in r.stdout

def test_enable_blocks_requests_lazy(tmp_path):
    try:
        import requests  # noqa
    except ImportError:
        pytest.skip("requests 未安装")
    r = _run_guarded("import requests\nrequests.get('http://example.com')\nprint('LEAK')\n", tmp_path)
    assert "SandboxNetworkViolation" in r.stderr
    assert "LEAK" not in r.stdout

def test_sitecustomize_source_mentions_enable():
    src = Path(BASE_SCRIPTS) / "code_sandbox_run.py"
    text = src.read_text(encoding="utf-8", errors="replace")
    assert "enable_sandbox_netguard" in text
    assert "sandbox_sitecustomize" in text
