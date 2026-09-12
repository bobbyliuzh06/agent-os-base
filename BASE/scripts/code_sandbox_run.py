#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""code_sandbox_run：L1 proc 沙箱执行器。
- --dry：只打印执行计划（entry/资源上限/清空env/写白名单），不启动子进程。
- 真实执行：清空敏感 env（含代理变量）、cwd=sandbox、sitecustomize 禁网+写前缀守卫、
  注入 TASK_DIR/TMPDIR（沙箱内临时目录）、timeout 兜底。
- Windows 尝试 ctypes JobObject 附加内存上限（JOB_OBJECT_LIMIT_PROCESS_MEMORY +
  KILL_ON_JOB_CLOSE）；附加失败（宿主作业限制等）→ 报告 tier1-degraded，仅 timeout 兜底。
- 任何 violation（超时/越界写/网络）→ violated=true + violation.json，不继续。"""
import os, sys, json, subprocess, datetime, shutil, ctypes
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

SITE_CUSTOMIZE = '''
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
    # pathlib.Path.write_text/write_bytes 直写路径也必须守卫
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
    import socket
    def _block(*a, **k):
        raise OSError("SANDBOX_NETWORK_BLOCKED")
    socket.socket = _block
    socket.create_connection = _block
'''

PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
              "http_proxy", "https_proxy", "all_proxy", "no_proxy")

def _try_job_attach(proc, max_mem_mb):
    """Windows JobObject：内存上限 + job 关闭即杀子进程。返回 (attached, msg)。"""
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
            return False, "CreateJobObjectW 失败"
        JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x0100
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        info = EXT()
        info.BasicLimitInformation.LimitFlags = (JOB_OBJECT_LIMIT_PROCESS_MEMORY |
                                                 JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
        info.ProcessMemoryLimit = max_mem_mb * 1024 * 1024
        if not k32.SetInformationJobObject(h, 9, ctypes.byref(info), ctypes.sizeof(info)):
            k32.CloseHandle(h)
            return False, "SetInformationJobObject 失败"
        if not k32.AssignProcessToJobObject(h, proc._handle):
            k32.CloseHandle(h)
            return False, "AssignProcessToJobObject 失败（宿主作业限制或权限）"
        # 句柄由本进程持有；job 关闭即杀子进程
        return True, "JobObject 已附加（内存上限 %sMB + KILL_ON_CLOSE）" % max_mem_mb
    except Exception as e:
        return False, "JobObject 尝试异常: %s" % e

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
    ap.add_argument("--max-mem-mb", type=int, default=256)
    ap.add_argument("--max-cpu-sec", type=int, default=5)
    ap.add_argument("--runtime", default="proc", choices=["proc", "docker"])
    ap.add_argument("--dry", action="store_true")
    ns = ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"] = ns.root
    C = _lc()
    td = C.tasks_dir / ns.task
    sd = Path(ns.sandbox_dir) if ns.sandbox_dir else td / "task-evolve" / "exec" / ("run-" + datetime.date.today().isoformat()) / "sandbox-copy"
    if not sd.exists():
        print("NO_SANDBOX", sd); return 1
    entries = [p for p in sorted(sd.rglob("*.py")) if ".guard" not in p.parts]
    if ns.entry:
        cand = Path(ns.entry)
        entry = cand if cand.is_absolute() else sd / cand
    else:
        entry = entries[0] if entries else None
    tmpdir = sd / "tmp"
    keep_env = {"PATH": os.environ.get("PATH", ""), "SystemRoot": os.environ.get("SystemRoot", ""),
                "PYTHONPATH": str(sd), "AGENT_SANDBOX_DIR": str(sd),
                "AGENT_OS_ROOT": os.environ.get("AGENT_OS_ROOT", str(C.root)),
                "TASK_DIR": str(td / "task-evolve"),
                "TMPDIR": str(tmpdir), "TEMP": str(tmpdir), "TMP": str(tmpdir),
                "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    cleared = sorted(k for k in os.environ if k not in keep_env and (
        "KEY" in k.upper() or "TOKEN" in k.upper() or "SECRET" in k.upper() or "PASS" in k.upper()))
    proxy_cleared = [k for k in PROXY_KEYS if k in os.environ and k not in keep_env]
    print("SANDBOX_RUN dry=%s runtime=%s task=%s" % (ns.dry, ns.runtime, ns.task))
    print("  sandbox=%s" % sd)
    print("  entry=%s" % entry)
    print("  limits: timeout=%ss mem=%sMB cpu=%ss job_object=%s" % (
        ns.timeout, ns.max_mem_mb, ns.max_cpu_sec, "attempt" if os.name == "nt" else "n/a"))
    print("  env_cleared=%s" % (",".join(cleared) if cleared else "(无敏感项)"))
    print("  proxy_cleared=%s" % (",".join(proxy_cleared) if proxy_cleared else "(无代理变量)"))
    print("  injected=TASK_DIR,TMPDIR(%s),AGENT_SANDBOX_DIR" % tmpdir)
    print("  write_whitelist=%s  network=blocked" % sd)
    if ns.dry:
        print("  DRY: 未启动任何子进程")
        return 0
    if not entry or not entry.exists():
        print("NO_ENTRY"); return 1
    # 注入 sitecustomize 守卫
    guard_dir = sd / ".guard"
    guard_dir.mkdir(exist_ok=True)
    (guard_dir / "sitecustomize.py").write_text(SITE_CUSTOMIZE, encoding="utf-8")
    keep_env["PYTHONPATH"] = str(guard_dir) + os.pathsep + str(sd)
    tmpdir.mkdir(exist_ok=True)
    if ns.runtime == "docker":
        cmd = ["docker", "run", "--rm", "--network", "none", "--memory", "%sm" % ns.max_mem_mb,
               "--cpus", "0.5", "--pids-limit", "64", "--read-only", "--tmpfs", "/tmp",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "-v", "%s:/work:ro" % sd, "-w", "/work", "python:3.9-slim", "python", str(entry.relative_to(sd))]
        print("DOCKER_RUNTIME 需要本机 docker；未检测则失败并标 L1 降级。")
    else:
        cmd = [sys.executable, str(entry)]
    t0 = datetime.datetime.now()
    job_note = "tier1-degraded：未尝试 JobObject" if os.name != "nt" else ""
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(cmd, cwd=str(sd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=keep_env, creationflags=creationflags)
        if os.name == "nt":
            ok, job_note = _try_job_attach(proc, ns.max_mem_mb)
            if not ok:
                job_note = "tier1-degraded：%s（仅 timeout 兜底）" % job_note
        try:
            out, err = proc.communicate(timeout=ns.timeout)
            rc = proc.returncode
            stdout_s = (out.decode("utf-8", "replace") or "")[:4000]
            stderr_s = (err.decode("utf-8", "replace") or "")[:4000]
            guard_hit = ("SANDBOX_WRITE_OUTSIDE" in stderr_s) or ("SANDBOX_NETWORK_BLOCKED" in stderr_s)
            result = {"task": ns.task, "runtime": ns.runtime, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      "exit_code": rc, "stdout": stdout_s, "stderr": stderr_s,
                      "elapsed_s": round((datetime.datetime.now() - t0).total_seconds(), 2),
                      "violated": guard_hit, "job_object": job_note,
                      "notes": "sitecustomize 守卫命中（越界写/联网）" if guard_hit else "L1 proc 沙箱"}
        except subprocess.TimeoutExpired:
            proc.kill()
            out, err = proc.communicate()
            result = {"task": ns.task, "runtime": ns.runtime, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      "exit_code": None, "stdout": "", "stderr": "TIMEOUT after %ss" % ns.timeout,
                      "elapsed_s": ns.timeout, "violated": True, "job_object": job_note,
                      "notes": "timeout 越界"}
    except Exception as e:
        result = {"task": ns.task, "runtime": ns.runtime, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  "exit_code": None, "stdout": "", "stderr": "LAUNCH_ERROR: %s" % e,
                  "elapsed_s": round((datetime.datetime.now() - t0).total_seconds(), 2),
                  "violated": True, "job_object": job_note, "notes": "启动异常"}
    outdir = td / "task-evolve" / "exec"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "run.log").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    if result["violated"]:
        (outdir / "violation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SANDBOX_RESULT violated=%s exit=%s job=%s" % (result["violated"], result["exit_code"], job_note))
    return 0

if __name__ == "__main__":
    sys.exit(main())
