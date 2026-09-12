import os, sys, json, subprocess
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent / "BASE" / "scripts"))
import code_sandbox_run as csr


def test_limits_defaults():
    lim = csr._Limits()
    assert lim.timeout == 30
    assert lim.mem_mb == 256
    assert lim.cpu_sec == 5
    assert lim.cpu_rate == 0
    assert lim.max_procs == 1
    assert lim.pids_limit == 32

def test_job_flags_include_process_time_memory_procs_kill():
    f = csr._job_flags()
    for flag, name in [(0x0100, "PROCESS_MEMORY"), (0x0200, "JOB_MEMORY"),
                       (0x0008, "ACTIVE_PROCESS"), (0x2000, "KILL_ON_JOB_CLOSE"),
                       (0x0002, "PROCESS_TIME")]:
        assert f & flag, "缺少 %s" % name
    assert not (f & 0x800), "不得允许 BREAKAWAY_OK"

def test_job_degraded_when_no_backend(monkeypatch):
    monkeypatch.setattr(csr, "HAVE_PYWIN32", False)
    monkeypatch.setattr(csr, "_try_job_ctypes", lambda proc, limits: (0, None))
    n, tier, note = csr._setup_jobobject(None, csr._Limits())
    assert n == 0
    assert tier == "tier1-degraded"
    assert "timeout" in note

def test_cli_accepts_resource_flags(tmp_path):
    runner = Path(__file__).parent.parent / "BASE" / "scripts" / "code_sandbox_run.py"
    r = subprocess.run([sys.executable, str(runner), "--task", "t-none",
                        "--sandbox-dir", str(tmp_path / "sbx"),
                        "--sandbox-mem", "64", "--sandbox-cpu-sec", "1", "--sandbox-cpu-rate", "5000",
                        "--sandbox-procs", "2", "--sandbox-pids", "48", "--dry"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    assert r.returncode == 0, r.stderr
    assert '"mem_mb": 64' in r.stdout
    assert '"cpu_sec": 1' in r.stdout
    assert '"cpu_rate": 5000' in r.stdout
    assert '"max_procs": 2' in r.stdout
    assert '"pids_limit": 48' in r.stdout

def test_proxy_traps_present():
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY", "FTP_PROXY"):
        assert k in csr.PROXY_TRAPS, "缺少 %s" % k
    assert csr.PROXY_TRAPS["HTTP_PROXY"] == "http://127.0.0.1:9"
    assert csr.PROXY_TRAPS["NO_PROXY"] == ""

def test_probe_script_generation(tmp_path):
    """授权探针脚本（真实 attach 不在 pytest 内自动跑，由 runner 手动执行）。"""
    p = tmp_path / "hog.py"
    p.write_text("import time\nfor _ in range(20): time.sleep(0.1)\n", encoding="utf-8")
    assert "time.sleep" in p.read_text(encoding="utf-8")
