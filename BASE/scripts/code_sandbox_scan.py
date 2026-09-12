#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""code_sandbox_scan：对 tasks/<id>/task-evolve 下代码文件做静态预筛。
HARD 命中 → block_exec=true（不进沙箱，写 blocked.json）；SOFT → warn（进报告，不 block）。
只读扫描，不执行任何代码。

v1.2 硬化：
- AST 字符串常量扫描：常量中带全局路径（BASE/、META/config、PENDING、.git、regression-runs）→ HARD；
- open()/write_text/write_bytes 模式拆分：读模式白名单放行，写模式目标必须在任务区，
  绝对路径写越区或写全局路径 → HARD；动态路径（env/拼接）→ note，由运行时 sitecustomize 守卫兜底。
"""
import os, sys, json, re, ast, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

CODE_EXT = (".py", ".bat", ".sh")

GLOBAL_PATH_RE = re.compile(
    r"(?:^|[\s'\"(])"
    r"(?:(?:[A-Za-z]:[\\/])?(?:[^'\"\s]*[\\/])?)?"
    r"(?:BASE[\\/]|META[\\/]config|PENDING[\\/]|\.git[\\/]|regression-runs[\\/])",
    re.I)
ABS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]|^[\\/]")
WRITE_MODE_RE = re.compile(r"[wax+]")
WRITE_METHODS = ("open", "write_text", "write_bytes")

HARD_PATTERNS = [
    (r"BASE[\\/]", "写BASE路径"),
    (r"META[\\/]config\.json", "写全局config"),
    (r"PENDING[\s\\/]", "写全局PENDING"),
    (r"regression-runs[\\/]", "写回归目录"),
    (r"\.git[\\/]", "写git内部"),
    (r"schtasks|crontab|\bat\s+[^\n]*\n|sc\s+create", "调度/服务注册"),
    (r"os\.system|subprocess|popen|ctypes", "进程/原生调用"),
    (r"\beval\s*\(|\bexec\s*\(|__import__|importlib", "动态执行/导入"),
    (r"\bsocket\b|requests|urllib|ftplib|smtplib", "网络调用"),
    (r"rmdir|rm\s+-rf|format\s+[A-Za-z]:|diskpart", "破坏性命令"),
    (r"sk-[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{8,}|gh[pour]_[A-Za-z0-9]{8,}", "密钥样式"),
    (r"密码\s*=|password\s*=|token\s*=\s*['\"][A-Za-z0-9]{8,}", "明文凭据"),
    (r"dispatch_wrapper|七阶段", "底座调度引用"),
]
SOFT_PATTERNS = [
    (r"pickle|marshal|compile\s*\(|getattr|setattr|monkeypatch|sys\.path", "反射/序列化"),
    (r"https?://|(?:\d{1,3}\.){3}\d{1,3}", "外部URL/IP"),
    (r"pip\s+install", "pip安装（需白名单）"),
]

def _parse(path):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        return ast.parse(text.lstrip("\ufeff"))
    except Exception:
        return None

def _ast_constants(path):
    tree = _parse(path)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append(node.value)
        elif isinstance(node, ast.Str):  # py<=3.7 兼容
            out.append(node.s)
    return out

def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Str):
        return node.s
    return None

def _ast_open_targets(path):
    """返回 [(method, mode, target)]；target 为空串表示动态/不可静态解析。"""
    tree = _parse(path)
    if tree is None:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # 1) 裸函数 open()/file()
        if isinstance(node.func, ast.Name) and node.func.id in ("open", "file"):
            mode = "r"
            if len(node.args) >= 2:
                c = _const_str(node.args[1])
                if c:
                    mode = c
            for kw in node.keywords:
                if kw.arg == "mode":
                    c = _const_str(kw.value)
                    if c:
                        mode = c
            target = _const_str(node.args[0]) if node.args else ""
            out.append((node.func.id, mode, target or ""))
            continue
        # 2) 方法调用 open()/write_text()/write_bytes()
        if not isinstance(node.func, ast.Attribute) or node.func.attr not in WRITE_METHODS:
            continue
        mode = "w" if node.func.attr in ("write_text", "write_bytes") else "r"
        if node.func.attr == "open":
            if len(node.args) >= 2:
                c = _const_str(node.args[1])
                if c:
                    mode = c
            for kw in node.keywords:
                if kw.arg == "mode":
                    c = _const_str(kw.value)
                    if c:
                        mode = c
        # 目标：open 的第一参数 / Path(...) 链的字符串常量片段
        parts = []
        if node.func.attr == "open":
            if node.args:
                c = _const_str(node.args[0])
                if c:
                    parts.append(c)
        val = node.func.value
        while isinstance(val, ast.Call):
            if isinstance(val.func, ast.Attribute) and val.func.attr == "Path":
                for a in val.args:
                    c = _const_str(a)
                    if c:
                        parts.append(c)
            val = val.func.value if isinstance(val.func, ast.Attribute) else None
            if val is None:
                break
        target = "/".join(p for p in parts if p) if parts else ""
        out.append((node.func.attr, mode, target))
    return out

def _scan_file(path, task_id):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    hard_hits, soft_hits, notes = [], [], []
    own = ("tasks/" + task_id + "/task-evolve/").replace("\\", "/")
    flat_own = own.replace("/", "\\")
    if path.suffix.lower() == ".py":
        # 1) AST 字符串常量：全局路径 → HARD
        for c in _ast_constants(path):
            if GLOBAL_PATH_RE.search(c):
                hard_hits.append(("AST常量含全局路径", c[:160]))
        # 2) open/write 模式拆分
        for method, mode, target in _ast_open_targets(path):
            is_write = bool(WRITE_MODE_RE.search(mode))
            if not target:
                if is_write:
                    notes.append("动态写路径（env/拼接），运行时守卫兜底: %s mode=%s" % (method, mode))
                continue
            flat = target.replace("\\", "/")
            if GLOBAL_PATH_RE.search(target):
                hard_hits.append(("AST写目标全局路径", "%s(%s, mode=%s)" % (method, target[:140], mode)))
            elif is_write and ABS_PATH_RE.match(flat) and (own not in flat and flat_own not in target):
                hard_hits.append(("AST绝对写越区", "%s(%s, mode=%s)" % (method, target[:140], mode)))
    # 3) 正则行扫（全部文件）
    for line in text.splitlines():
        l = line.rstrip()
        if not l.strip() or l.strip().startswith("#"):
            continue
        if re.search(r"[A-Za-z]:[\\/]", l):
            if own not in l.replace("\\", "/"):
                hard_hits.append(("绝对盘符路径越区", l[:160]))
        for pat, name in HARD_PATTERNS:
            if re.search(pat, l, re.I):
                hard_hits.append((name, l[:160]))
        for pat, name in SOFT_PATTERNS:
            if re.search(pat, l, re.I):
                soft_hits.append((name, l[:160]))
    if hard_hits:
        return {"file": str(path).replace("\\", "/"), "risk": "block", "hits": hard_hits,
                "warns": soft_hits, "notes": notes}
    if soft_hits:
        return {"file": str(path).replace("\\", "/"), "risk": "warn", "hits": [],
                "warns": soft_hits, "notes": notes}
    return {"file": str(path).replace("\\", "/"), "risk": "ok", "hits": [], "warns": [], "notes": notes}

def main():
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("AGENT_OS_ROOT", ""))
    ap.add_argument("--task", required=True)
    ap.add_argument("--out", default="")
    ns = ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"] = ns.root
    C = _lc()
    td = C.tasks_dir / ns.task
    if not td.exists():
        print("NO_TASK", ns.task); return 1
    ev = td / "task-evolve"
    files = [p for p in sorted(ev.rglob("*")) if p.is_file() and p.suffix.lower() in CODE_EXT and "exec" not in p.parts]
    scanned = []
    for f in files:
        r = _scan_file(f, ns.task)
        if r:
            scanned.append(r)
    block_exec = any(r["risk"] == "block" for r in scanned)
    out = {"task": ns.task, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "scanned": scanned, "block_exec": block_exec,
           "hardening": "v1.2: AST string constants + open-mode split (read-allow / write-task-exec)"}
    execdir = ev / "exec"
    execdir.mkdir(parents=True, exist_ok=True)
    out_path = Path(ns.out) if ns.out else execdir / "scan.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if block_exec:
        blocked = {"task": ns.task, "time": out["time"], "blocked": True,
                   "reason": "HARD 静态规则命中，禁止进入沙箱",
                   "files": [r["file"] for r in scanned if r["risk"] == "block"]}
        (execdir / "blocked.json").write_text(json.dumps(blocked, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SANDBOX_SCAN task=%s files=%d block=%s out=%s" % (ns.task, len(scanned), block_exec, out_path))
    for r in scanned:
        print("  [%s] %s hits=%d warns=%d notes=%d" % (r["risk"], r["file"], len(r["hits"]), len(r["warns"]), len(r.get("notes", []))))
    return 0

if __name__ == "__main__":
    sys.exit(main())
