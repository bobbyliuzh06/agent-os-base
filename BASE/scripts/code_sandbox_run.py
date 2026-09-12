#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""code_sandbox_run：L1 proc 沙箱执行器（v1.3）。
- --dry：只打印执行计划，不启动子进程；--exec 才真实执行。
- limits 默认：timeout=30s, mem_mb=256, cpu_sec=5, cpu_rate=0(用时间限兜底), max_procs=1, pids_limit=32。
- JobObject（阶段A）：优先 pywin32，缺则 ctypes 兜底；均失败 → job_tier=tier1-degraded（仅 timeout 兜底，如实标记）。
  内存上限（PROCESS+JOB_MEMORY）、CpuRateHardCap（Win10+，失败回退 PerProcessUserTimeLimit=cpu_sec*10ms）、
  ActiveProcessLimit=max_procs、不设 BREAKAWAY_OK（禁 breakaway）、KILL_ON_JOB_CLOSE。
- 网络（阶段B）：env 代理陷阱（HTTP(S)_PROXY=http://127.0.0.1:9，其余置空）+ sandbox_sitecustomize 懒补丁
  （socket/urllib/requests/httpx/ftplib/smtplib/websocket → SandboxNetworkViolation）。
- 写守卫：sitecustomize 内 builtins.open/io.open/pathlib 写模式仅允许 sandbox 内。
- 日志（阶段E）：result.json/run.log/violation.json 的 stdout/stderr 写盘前经 redact 脱敏；控制台不改。
"""
import os, sys, json, subprocess, datetime, shutil, ctypes
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc
from redact import redact

try:
    import win32job, win32con, win32api  # noqa
    HAVE_PYWIN32 = True
except ImportError:
    HAVE_PYWIN32 = False

PROXY_TRAPS = {"HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9",
               "NO_PROXY": "", "ALL_PROXY": "", "FTP_PROXY": ""}
CLEAR_ENV_MARK = ("KEY", "TOKEN", "SECRET", "PASS")

SITE_CUSTOMIZE = '''# -*- coding: utf-8 -*-
import builtins, os, sys, io
_SANDBOX = os.environ.get("AGENT_SANDBOX_DIR", "")
if _SANDBOX:
    _S = os.path.abspath(_SANDBOX).replace("\\\\", "/").rstrip("/") + "/"
    _real_open = builtins.open
    def _guarded_open(file, *a, **k):
        mode = a[0] if a else k.get("mode", "r")
        if any(ch in mode for ch in "wax+"):
            p = os.path.abspath(str(file)).replace("\\\\", "/")
            if not p.startswith(_S):
                raise PermissionError("SANDBOX_WRITE_OUTSIDE: " + p)
        return _real_open(file, *a, **k)
    builtins.open = _guarded_open
    io.open = _guarded_open
    import pathlib
    _orig_write_text = pathlib.Path.write_text
    def _guarded_write_text(self, data, *a, **k):
        p = os.path.abspath(str(self)).replace("\\\\", "/")
        if not p.startswith(_S):
            raise PermissionError("SANDBOX_WRITE_OUTSIDE: " + p)
        return _orig_write_text(self, data, *a, **k)
    pathlib.Path.write_text = _guarded_write_text
    _orig_write_bytes = pathlib.Path.write_bytes
    def _guarded_write_bytes(self, data, *a, **k):
        p = os.path.abspath(str(self)).replace("\\\\", "/")
        if not p.startswith(_S):
            raise PermissionError("SANDBOX_WRITE_OUTSIDE: " + p)
        return _orig_write_bytes(self, data, *a, **k)
    pathlib.Path.write_bytes = _guarded_write_bytes
import sandbox_sitecustomize
sandbox_sitecustomize.enable_sandbox_netguard()
'''


class _Limits:
    def __init__(self, timeout=30, mem_mb=256, cpu_sec=5, cpu_rate=0, max_procs=1, pids_limit=32):
        self.timeout = timeout
        self.mem_mb = mem_mb
        self.cpu_sec = cpu_sec
        self.cpu_rate = cpu_rate
        self.max_procs = max_procs
        self.pids_limit = pids_limit

    def as_dict(self):
        return {"timeout": self.timeout, "mem_mb": self.mem_mb, "cpu_sec": self.cpu_sec,
                "cpu_rate": self.cpu_rate, "max_procs": self.max_procs, "pids_limit": self.pids_limit}


def _job_flags():
    f = 0x0100 | 0x0200 | 0x0008 | 0x2000  # PROCESS_MEMORY | JOB_MEMORY | ACTIVE_PROCESS | KILL_ON_CLOSE
    return f | 0x0002  # PROCESS_TIME（PerProcessUserTimeLimit 生效前提）


def _try_job_pywin32(proc, limits):
    """pywin32 路径：JobObject 扩展限制 + CpuRateHardCap（Win10+，失败回退时间限）。"""
    try:
        h = win32job.CreateJobObject(None, "")
        info = {"LimitFlags": _job_flags(),
                "ProcessMemoryLimit": limits.mem_mb * 1024 * 1024,
                "JobMemoryLimit": limits.mem_mb * 1024 * 1024,
                "ActiveProcessLimit": limits.max_procs}
        if limits.cpu_rate <= 0:
            info["PerProcessUserTimeLimit"] = limits.cpu_sec * 10_000_000
        else:
            info["PerProcessUserTimeLimit"] = 0
        win32job.SetInformationJobObject(h, win32job.JobObjectExtendedLimitInformation, info)
        cpu_rate_ok = False
        if limits.cpu_rate > 0:
            try:
                ci = {"ControlFlags": 0x1 | 0x4,  # ENABLE | HARD_CAP
                      "CpuRate": limits.cpu_rate, "Weight": 0, "MinRate": 0, "MaxRate": 0}
                win32job.SetInformationJobObject(h, win32job.JobObjectCpuRateControlInformation, ci)
                cpu_rate_ok = True
            except Exception:
                cpu_rate_ok = False
        if limits.cpu_rate > 0 and not cpu_rate_ok:
            info["PerProcessUserTimeLimit"] = limits.cpu_sec * 10_000_000
            win32job.SetInformationJobObject(h, win32job.JobObjectExtendedLimitInformation, info)
        hp = win32api.OpenProcess(win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE, False, proc.pid)
        try:
            win32job.AssignProcessToJobObject(h, hp)
        finally:
            win32api.CloseHandle(hp)
        return 1, "pywin32 JobObject 已附加（mem=%sMB procs=%s cpu_rate=%s%s + KILL_ON_CLOSE）" % (
            limits.mem_mb, limits.max_procs, limits.cpu_rate,
            "" if (limits.cpu_rate <= 0 or cpu_rate_ok) else "(rate不可用→时间限兜底)")
    except Exception:
        return 0, None


def _try_job_ctypes(proc, limits):
    """ctypes 兜底路径：与 pywin32 等价能力（无 CpuRateHardCap，仅时间限）。"""
    try:
        k32 = ctypes.windll.kernel32

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [("ReadOperationCount", ctypes.c_ulonglong),
                        ("WriteOperationCount", ctypes.c_ulonglong),
                        ("OtherOperationCount", ctypes.c_ulonglong),
                        ("ReadTransferCount", ctypes.c_ulonglong),
                        ("WriteTransferCount", ctypes.c_ulonglong),
                        ("OtherTransferCount", ctypes.c_ulonglong)]

        class BASIC(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                        ("PerJobUserTimeLimit", ctypes.c_longlong),
                        ("LimitFlags", ctypes.c_ulong),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", ctypes.c_ulong),
                        ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", ctypes.c_ulong),
                        ("SchedulingClass", ctypes.c_ulong)]

        class EXT(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO_COUNTERS),
                        ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        h = k32.CreateJobObjectW(None, None)
        if not h:
            return 0, None
        info = EXT()
        info.BasicLimitInformation.LimitFlags = _job_flags()
        info.BasicLimitInformation.PerProcessUserTimeLimit = limits.cpu_sec * 10_000_000
        info.BasicLimitInformation.ActiveProcessLimit = limits.max_procs
        info.ProcessMemoryLimit = limits.mem_mb * 1024 * 1024
        info.JobMemoryLimit = limits.mem_mb * 1024 * 1024
        if not k32.SetInformationJobObject(h, 9, ctypes.byref(info), ctypes.sizeof(info)):
            k32.CloseHandle(h)
            return 0, None
        if not k32.AssignProcessToJobObject(h, proc._handle):
            k32.CloseHandle(h)
            return 0, None
        return 1, "ctypes JobObject 已附加（mem=%sMB procs=%s cpu_sec=%ss + KILL_ON_CLOSE）" % (
            limits.mem_mb, limits.max_procs, limits.cpu_sec)
    except Exception:
        return 0, None


def _setup_jobobject(proc, limits):
    """返回 (job_attached, job_tier, job_note)。失败如实 tier1-degraded，不伪硬限。"""
    if HAVE_PYWIN32:
        n, note = _try_job_pywin32(proc, limits)
        if n:
            return n, "job-object-attached", note
    n, note = _try_job_ctypes(proc, limits)
    if n:
        return n, "job-object-attached", note
    return 0, "tier1-degraded", "JobObject 附加失败（pywin32/ctypes 均不可用或宿主作业限制），仅 timeout 兜底"


def _stage_entry(entry, sd, td):
    if entry.exists():
        return entry
    for src in (td / "task-evolve" / entry.name, td / entry.name):
        if src.exists():
            dst = sd / entry.name
            shutil.copy2(src, dst)
            print("  ENTRY_STAGED %s -> %s" % (src, dst))
            return dst
    return entry


def main():
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("AGENT_OS_ROOT", ""))
    ap.add_argument("--task", required=True)
    ap.add_argument("--sandbox-dir", default="")
    ap.add_argument("--entry", default="")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--sandbox-mem", type=int, default=256)
    ap.add_argument("--max-mem-mb", type=int, default=None, help="别名(兼容)")
    ap.add_argument("--sandbox-cpu-sec", type=int, default=5)
    ap.add_argument("--max-cpu-sec", type=int, default=None, help="别名(兼容)")
    ap.add_argument("--sandbox-cpu-rate", type=int, default=0)
    ap.add_argument("--sandbox-procs", type=int, default=1)
    ap.add_argument("--sandbox-pids", type=int, default=32)
    ap.add_argument("--runtime", default="proc", choices=["proc", "docker"])
    ap.add_argument("--dry", action="store_true")
    ns = ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"] = ns.root
    mem_mb = ns.max_mem_mb if ns.max_mem_mb is not None else ns.sandbox_mem
    cpu_sec = ns.max_cpu_sec if ns.max_cpu_sec is not None else ns.sandbox_cpu_sec
    limits = _Limits(timeout=ns.timeout, mem_mb=mem_mb, cpu_sec=cpu_sec,
                     cpu_rate=ns.sandbox_cpu_rate, max_procs=ns.sandbox_procs, pids_limit=ns.sandbox_pids)
    C = _lc()
    td = C.tasks_dir / ns.task
    sd = Path(ns.sandbox_dir) if ns.sandbox_dir else td / "task-evolve" / "exec" / ("run-" + datetime.date.today().isoformat()) / "sandbox-copy"
    if not sd.exists():
        sd.mkdir(parents=True, exist_ok=True)
        print("SANDBOX_CREATED", sd)
    entries = [p for p in sorted(sd.rglob("*.py")) if ".guard" not in p.parts]
    if ns.entry:
        cand = Path(ns.entry)
        entry = cand if cand.is_absolute() else sd / cand
        entry = _stage_entry(entry, sd, td)
    else:
        entry = entries[0] if entries else None
    tmpdir = sd / "tmp"
    keep_env = {"PATH": os.environ.get("PATH", ""), "SystemRoot": os.environ.get("SystemRoot", ""),
                "PYTHONPATH": str(sd), "AGENT_SANDBOX_DIR": str(sd),
                "AGENT_OS_ROOT": os.environ.get("AGENT_OS_ROOT", str(C.root)),
                "TASK_DIR": str(td / "task-evolve"),
                "TMPDIR": str(tmpdir), "TEMP": str(tmpdir), "TMP": str(tmpdir),
                "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    keep_env.update(PROXY_TRAPS)
    cleared = sorted(k for k in os.environ if k not in keep_env and any(m in k.upper() for m in CLEAR_ENV_MARK))
    print("SANDBOX_RUN dry=%s runtime=%s task=%s" % (ns.dry, ns.runtime, ns.task))
    print("  sandbox=%s" % sd)
    print("  entry=%s" % entry)
    print("  limits: %s" % json.dumps(limits.as_dict(), ensure_ascii=False))
    print("  job_backend=pywin32" if HAVE_PYWIN32 else "  job_backend=ctypes-fallback(无pywin32)")
    print("  env_cleared=%s" % (",".join(cleared) if cleared else "(无敏感项)"))
    print("  proxy_traps=HTTP_PROXY/HTTPS_PROXY=127.0.0.1:9, NO_PROXY/ALL_PROXY/FTP_PROXY=空")
    print("  netguard=sandbox_sitecustomize(懒补丁 socket/urllib/requests/httpx/ftplib/smtplib/websocket)")
    print("  injected=TASK_DIR,TMPDIR(%s),AGENT_SANDBOX_DIR" % tmpdir)
    print("  write_whitelist=%s" % sd)
    if ns.dry:
        print("  DRY: 未启动任何子进程")
        return 0
    if not entry or not entry.exists():
        print("NO_ENTRY"); return 1
    guard_dir = sd / ".guard"
    guard_dir.mkdir(exist_ok=True)
    (guard_dir / "sitecustomize.py").write_text(SITE_CUSTOMIZE, encoding="utf-8")
    shutil.copy2(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox_sitecustomize.py"),
                 guard_dir / "sandbox_sitecustomize.py")
    keep_env["PYTHONPATH"] = str(guard_dir) + os.pathsep + str(sd)
    tmpdir.mkdir(exist_ok=True)
    if ns.runtime == "docker":
        cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "%sm" % limits.mem_mb,
               "--cpus", "0.5", "--pids-limit", str(limits.pids_limit), "--read-only", "--tmpfs", "/tmp",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "-v", "%s:/work:ro" % sd, "-w", "/work", "python:3.9-slim", "python", str(entry.relative_to(sd))]
        print("DOCKER_RUNTIME 需要本机 docker；未检测则失败并标 L1 降级。")
    else:
        cmd = [sys.executable, str(entry)]
    netguard_status = "full" if entry.suffix.lower() == ".py" else "partial (env-only，非Python入口)"
    t0 = datetime.datetime.now()
    job_attached, job_tier, job_note = 0, "tier1-degraded", "未尝试 JobObject"
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, cwd=str(sd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=keep_env, creationflags=creationflags)
        if os.name == "nt":
            job_attached, job_tier, job_note = _setup_jobobject(proc, limits)
        try:
            out, err = proc.communicate(timeout=limits.timeout)
            rc = proc.returncode
            stdout_s = (out.decode("utf-8", "replace") or "")[:4000]
            stderr_s = (err.decode("utf-8", "replace") or "")[:4000]
            if "SandboxNetworkViolation" in stderr_s or "SANDBOX_NETWORK_BLOCKED" in stderr_s:
                violation = "network"
            elif "SANDBOX_WRITE_OUTSIDE" in stderr_s:
                violation = "write-outside"
            elif rc in (0xC0000044, 0xC000013A, 0xC000013B):
                # STATUS_QUOTA_EXCEEDED / END_OF_JOB_TIME：CPU时间/内存 JobObject 限制触发
                violation = "resource-limit"
            else:
                violation = ""
            result = {"task": ns.task, "runtime": ns.runtime,
                      "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      "exit_code": rc, "stdout": redact(stdout_s), "stderr": redact(stderr_s),
                      "elapsed_s": round((datetime.datetime.now() - t0).total_seconds(), 2),
                      "violated": bool(violation), "reason": violation or None,
                      "job_attached": job_attached, "job_tier": job_tier, "job_note": job_note,
                      "job_limits": limits.as_dict(),
                      "netguard_status": netguard_status,
                      "notes": ("netguard 命中: %s" % violation) if violation else "L1 proc 沙箱"}
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            result = {"task": ns.task, "runtime": ns.runtime,
                      "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      "exit_code": None, "stdout": "", "stderr": redact("TIMEOUT after %ss" % limits.timeout),
                      "elapsed_s": limits.timeout, "violated": True, "reason": "timeout",
                      "job_attached": job_attached, "job_tier": job_tier, "job_note": job_note,
                      "job_limits": limits.as_dict(),
                      "netguard_status": netguard_status, "notes": "timeout 越界"}
    except Exception as e:
        result = {"task": ns.task, "runtime": ns.runtime,
                  "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  "exit_code": None, "stdout": "", "stderr": redact("LAUNCH_ERROR: %s" % e),
                  "elapsed_s": round((datetime.datetime.now() - t0).total_seconds(), 2),
                  "violated": True, "reason": "launch-error",
                  "job_attached": job_attached, "job_tier": job_tier, "job_note": job_note,
                  "job_limits": limits.as_dict(),
                  "netguard_status": netguard_status, "notes": "启动异常"}
    outdir = td / "task-evolve" / "exec"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "run.log").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    if result["violated"]:
        (outdir / "violation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SANDBOX_RESULT violated=%s exit=%s job=%s/%s netguard=%s" % (
        result["violated"], result["exit_code"], job_tier, job_attached, netguard_status))
    return 0


if __name__ == "__main__":
    sys.exit(main())
