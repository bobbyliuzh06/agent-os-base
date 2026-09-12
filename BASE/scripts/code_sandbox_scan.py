#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""code_sandbox_scan：对 tasks/<id>/task-evolve 下代码文件做静态预筛（v1.3）。
HARD 命中 → block_exec=true（不进沙箱，写 blocked.json）；SOFT → warn；potential → note（不 block）。
只读扫描，不执行任何代码。

v1.2：AST 字符串常量 + open() 模式拆分。
v1.3（阶段C）：
- import/from-import 白名单（IMPORT_HARD_MODULES 之外放行）；
- 危险调用（__import__/importlib/eval/exec/compile/ctypes/win32*/subprocess*/os.system|popen|spawn|
  shutil.rmtree/os.remove 越区/os.chmod/os.setuid/os.exec*）→ HARD；
- dunder 访问（__globals__/__subclasses__/__builtins__/__loader__/__import__）→ HARD；
- 动态路径拼接（f-string 含 BASE / os.path.join 含变量 / Path 变量）→ potential（不 block，运行时写守卫硬拦）；
- 只读白名单（READONLY_ALLOW）内的读 → 放行（note）；写模式白名单外 → HARD。
否定语境只做提案文本备注，不作为执行裁决依据。
"""
import os, sys, json, re, ast, fnmatch, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

CODE_EXT = (".py", ".bat", ".sh")

# ---- 模块顶部常量（与 gate_review_adapter 口径一致）----
READONLY_ALLOW = ["BASE/scripts/*.py", "BASE/templates/**", "tasks/<id>/**"]
WRITE_HARD = ["BASE/", "BASE/META/", "PENDING/", "schtasks", "dispatch_wrapper", "*.config.json", "绝对盘符配置"]
IMPORT_HARD_MODULES = frozenset([
    "requests", "urllib", "socket", "ctypes", "win32api", "win32com", "win32job", "pywin32",
    "subprocess", "paramiko", "ftplib", "smtplib", "httpx", "websocket", "pickle", "marshal",
    "importlib", "builtins",
])
DANGEROUS_ATTRS = frozenset([
    "system", "popen", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve",
    "spawnvp", "spawnvpe", "execv", "execve", "execvp", "execvpe", "execl", "execle",
    "execlp", "execlpe", "remove", "unlink", "rmtree", "chmod", "setuid", "setgid",
])
DUNDER = frozenset(["__globals__", "__subclasses__", "__builtins__", "__loader__", "__import__"])

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

def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Str):
        return node.s
    return None

def _top_name(name):
    return name.split(".")[0]

def _matches_readonly(s, task_id):
    pats = [p.replace("<id>", task_id) for p in READONLY_ALLOW]
    flat = s.replace("\\", "/")
    return any(fnmatch.fnmatchcase(flat, p) for p in pats)

def _in_exec_allow(s, task_id):
    return ("tasks/%s/task-evolve/exec/" % task_id) in s.replace("\\", "/")

def _scan_ast(path, task_id, hard_hits, notes):
    tree = _parse(path)
    if tree is None:
        return
    own_prefix = "tasks/%s/task-evolve/exec/" % task_id
    for node in ast.walk(tree):
        # 1) import 白名单
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = _top_name(alias.name)
                if top in IMPORT_HARD_MODULES or top.startswith("win32") or top == "pywin32":
                    hard_hits.append(("import 非白名单", alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = _top_name(node.module)
                if top in IMPORT_HARD_MODULES or top.startswith("win32") or top == "pywin32":
                    hard_hits.append(("import 非白名单", "from %s import ..." % node.module))
        # 2) dunder 访问
        if isinstance(node, ast.Attribute) and node.attr in DUNDER:
            hard_hits.append(("dunder 访问被禁止", node.attr))
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        # 3) 危险裸调用
        if isinstance(fn, ast.Name):
            if fn.id == "__import__":
                hard_hits.append(("动态执行/导入", "__import__"))
            elif fn.id in ("eval", "exec", "compile"):
                hard_hits.append(("动态执行", fn.id))
            elif fn.id == "getattr":
                if len(node.args) >= 2:
                    a0 = node.args[0]
                    a1 = _const_str(node.args[1])
                    src = a0.id if isinstance(a0, ast.Name) else ""
                    if src in ("os", "subprocess", "sys", "builtins", "ctypes", "importlib") and a1:
                        hard_hits.append(("getattr 链式取危险对象", "getattr(%s,%r)" % (src, a1)))
                    elif a1 in DANGEROUS_ATTRS:
                        hard_hits.append(("getattr 危险属性", "getattr(?,%r)" % a1))
                    else:
                        notes.append("getattr 动态访问（potential）: %s" % (a1 or "?")[:60])
        # 4) 危险属性调用
        if isinstance(fn, ast.Attribute):
            owner = fn.value
            owner_name = owner.id if isinstance(owner, ast.Name) else ""
            if owner_name == "ctypes":
                hard_hits.append(("ctypes.* 调用", fn.attr))
            elif owner_name in ("win32api", "win32com", "win32job"):
                hard_hits.append(("win32* 调用", "%s.%s" % (owner_name, fn.attr)))
            elif owner_name == "os" and fn.attr in ("system", "popen") or \
                    owner_name == "os" and fn.attr.startswith("spawn") or \
                    owner_name == "os" and fn.attr.startswith("exec"):
                hard_hits.append(("os 进程调用", "os.%s" % fn.attr))
            elif owner_name == "os" and fn.attr in ("chmod", "setuid", "setgid"):
                hard_hits.append(("os 权限调用", "os.%s" % fn.attr))
            elif owner_name == "os" and fn.attr in ("remove", "unlink"):
                tgt = _const_str(node.args[0]) if node.args else ""
                if tgt and (tgt.replace("\\", "/").startswith(own_prefix) or ("/" not in tgt and "\\" not in tgt)):
                    notes.append("os.remove 任务区/相对路径（已记录）: %s" % tgt[:100])
                else:
                    hard_hits.append(("os.remove 目标越白名单", (tgt or "动态")[:120]))
            elif owner_name == "subprocess" and fn.attr in ("run", "Popen", "system", "call", "check_output", "check_call"):
                hard_hits.append(("subprocess 调用", "subprocess.%s" % fn.attr))
            elif owner_name == "shutil" and fn.attr == "rmtree":
                hard_hits.append(("shutil.rmtree", "shutil.rmtree"))
            elif owner_name == "importlib" and fn.attr == "import_module":
                hard_hits.append(("动态导入", "importlib.import_module"))
        # 5) 动态路径拼接 → potential（不 block）
        if isinstance(fn, ast.Attribute) and fn.attr == "join" and isinstance(fn.value, ast.Attribute) \
                and fn.value.attr == "path" and isinstance(fn.value.value, ast.Name) \
                and fn.value.value.id == "os" and any(not _const_str(a) for a in node.args):
            notes.append("动态路径拼接（potential，运行时守卫硬拦）: os.path.join")
        if isinstance(fn, ast.Attribute) and fn.attr == "Path" and any(not _const_str(a) for a in node.args):
            notes.append("动态路径拼接（potential，运行时守卫硬拦）: Path(...)")
        if any(isinstance(a, ast.JoinedStr) for a in node.args):
            notes.append("f-string 路径拼接（potential，运行时守卫硬拦）")
        # 6) open/write 模式拆分（Name open + Attribute open/write_text/write_bytes）
        method = mode = target = None
        if isinstance(fn, ast.Attribute) and fn.attr in WRITE_METHODS:
            method = fn.attr
            mode = "w" if method in ("write_text", "write_bytes") else "r"
            if method == "open" and len(node.args) >= 2:
                c = _const_str(node.args[1])
                if c:
                    mode = c
            for kw in node.keywords:
                if kw.arg == "mode":
                    c = _const_str(kw.value)
                    if c:
                        mode = c
            parts = []
            if method == "open" and node.args:
                c = _const_str(node.args[0])
                if c:
                    parts.append(c)
            val = fn.value
            while isinstance(val, ast.Call):
                if isinstance(val.func, ast.Attribute) and val.func.attr == "Path":
                    for a in val.args:
                        c = _const_str(a)
                        if c:
                            parts.append(c)
                val = val.func.value if isinstance(val.func, ast.Attribute) else None
                if val is None:
                    break
            target = "/".join(p for p in parts if p)
        elif isinstance(fn, ast.Name) and fn.id in ("open", "file"):
            method = "open"
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
        if method:
            is_write = bool(WRITE_MODE_RE.search(mode))
            if not target:
                if is_write:
                    notes.append("动态写路径（env/拼接），运行时守卫兜底: %s mode=%s" % (method, mode))
            else:
                flat = target.replace("\\", "/")
                if is_write:
                    if GLOBAL_PATH_RE.search(target) and not _in_exec_allow(target, task_id):
                        hard_hits.append(("AST写目标全局路径", "%s(%s, mode=%s)" % (method, target[:140], mode)))
                    elif ABS_PATH_RE.match(flat) and not (own_prefix in flat or _in_exec_allow(target, task_id)):
                        hard_hits.append(("AST绝对写越区", "%s(%s, mode=%s)" % (method, target[:140], mode)))
                else:
                    if _matches_readonly(target, task_id):
                        notes.append("只读白名单放行: %s" % target[:100])
                    elif GLOBAL_PATH_RE.search(target):
                        hard_hits.append(("读全局路径越白名单", "%s(%s)" % (method, target[:140])))
    # 7) 字符串常量：全局路径 → HARD；只读白名单 → note；f-string 段 → potential
    js_const_ids = set()
    for js in (n for n in ast.walk(tree) if isinstance(n, ast.JoinedStr)):
        for c in ast.walk(js):
            if isinstance(c, ast.Constant):
                js_const_ids.add(id(c))
    for node in ast.walk(tree):
        c = _const_str(node)
        if not c:
            continue
        if GLOBAL_PATH_RE.search(c):
            if id(node) in js_const_ids:
                notes.append("f-string 路径段（potential，运行时守卫硬拦）: %s" % c[:100])
            elif _matches_readonly(c, task_id):
                notes.append("常量只读白名单路径（已记录）: %s" % c[:100])
            else:
                hard_hits.append(("AST常量含全局路径", c[:160]))

def _scan_file(path, task_id):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    hard_hits, soft_hits, notes = [], [], []
    own = ("tasks/" + task_id + "/task-evolve/").replace("\\", "/")
    if path.suffix.lower() == ".py":
        _scan_ast(path, task_id, hard_hits, notes)
    # 正则行扫（全部文件）
    for line in text.splitlines():
        l = line.rstrip()
        if not l.strip() or l.strip().startswith("#"):
            continue
        dyn_line = bool(re.search(r'f["\']|os\.path\.join|\bPath\s*\(\s*[A-Za-z_]', l))
        if re.search(r"[A-Za-z]:[\\/]", l):
            if own not in l.replace("\\", "/"):
                hard_hits.append(("绝对盘符路径越区", l[:160]))
        for pat, name in HARD_PATTERNS:
            if re.search(pat, l, re.I):
                if name == "写BASE路径" and dyn_line:
                    notes.append("动态路径行（potential，运行时守卫硬拦）: %s" % l[:120])
                else:
                    hard_hits.append((name, l[:160]))
        for pat, name in SOFT_PATTERNS:
            if re.search(pat, l, re.I):
                soft_hits.append((name, l[:160]))
    # 去重（保持顺序）
    seen = set()
    hard_hits = [h for h in hard_hits if not (tuple(h) in seen or seen.add(tuple(h)))]
    soft_hits = [h for h in soft_hits if not (tuple(h) in seen or seen.add(tuple(h)))]
    notes = [n for n in notes if not (("note", n) in seen or seen.add(("note", n)))]
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
           "hardening": "v1.3: imports/dunder/dangerous-calls/dynamic-path + readonly allowlist"}
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
