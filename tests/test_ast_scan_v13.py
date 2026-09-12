import os, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent / "BASE" / "scripts"))
import code_sandbox_scan as css

# 与 tasks/demo-real-20260912/task-evolve/count_scripts.py 同源的只读统计脚本
COUNT_SCRIPTS = '''# -*- coding: utf-8 -*-
# 只读统计入口：统计 BASE/scripts 下 *.py 文件名与行数（只读，不写 BASE，不联网）
import os
import pathlib

root = os.environ.get("AGENT_OS_ROOT", "")
scripts = pathlib.Path(root) / "BASE" / "scripts"
rows = []
total = 0
for f in sorted(scripts.glob("*.py")):
    n = 0
    with f.open(encoding="utf-8", errors="replace") as fh:
        n = sum(1 for _ in fh)
    total += n
    rows.append("- `%s` %d lines" % (f.name, n))
report = pathlib.Path(os.environ.get("AGENT_SANDBOX_DIR", ".")) / "report.md"
report.write_text("# 统计结果（只读）\\n\\n共 %d 个 .py，%d 行\\n\\n%s\\n" % (len(rows), total, "\\n".join(rows)), encoding="utf-8")
print("COUNT %d files, %d lines" % (len(rows), total))
'''

EVIL_V13 = '''import requests, subprocess, ctypes, pickle
from win32api import RegOpenKey

eval("print(1)")
__import__("os").system("dir")
importlib.import_module("socket")
getattr(os, "system")("calc")

class X:
    pass
X.__globals__

f = open("D:/x/BASE/META/config.json", "w")
os.remove("C:/Windows/system32/x.dll")
os.chmod("x", 0o777)
shutil.rmtree("D:/data")
subprocess.run(["cmd", "/c", "whoami"])
'''

DYN_PATH = '''import os, pathlib
root = os.environ.get("AGENT_OS_ROOT", "")
p = os.path.join(root, "BASE", "scripts")
q = f"{root}/BASE/scripts/x.py"
pathlib.Path(root) / "BASE" / "scripts"
print(p, q)
'''


def _w(tmp_path, name, src):
    p = tmp_path / name
    p.write_text(src, encoding="utf-8")
    return p

def test_count_scripts_read_allow(tmp_path):
    p = _w(tmp_path, "count_scripts.py", COUNT_SCRIPTS)
    r = css._scan_file(p, "demo-real")
    assert r["risk"] == "ok", r
    assert len(r["hits"]) == 0
    assert not any("写BASE" in h[0] for h in r["hits"])

def test_readonly_constant_in_whitelist_is_note(tmp_path):
    p = _w(tmp_path, "r.py", 'pathlib.Path("BASE/scripts/a.py").read_text(encoding="utf-8")\n')
    hard, notes = [], []
    css._scan_ast(p, "demo", hard, notes)
    assert not any("全局路径" in h[0] or "越白名单" in h[0] for h in hard)
    assert any("只读白名单" in n for n in notes)

def test_evil_v13_all_hard(tmp_path):
    p = _w(tmp_path, "evil.py", EVIL_V13)
    r = css._scan_file(p, "demo")
    assert r["risk"] == "block"
    kinds = {h[0] for h in r["hits"]}
    for expect in ("import 非白名单", "动态执行", "动态导入", "dunder 访问被禁止",
                   "os.remove 目标越白名单", "os 权限调用", "shutil.rmtree",
                   "subprocess 调用", "getattr 链式取危险对象", "AST常量含全局路径"):
        assert expect in kinds, "缺 HARD: %s (hits=%s)" % (expect, kinds)

def test_dynamic_path_potential_not_block(tmp_path):
    p = _w(tmp_path, "dyn.py", DYN_PATH)
    r = css._scan_file(p, "demo")
    assert r["risk"] == "ok", r
    assert any("potential" in n for n in r.get("notes", []))

def test_import_whitelist_defaults():
    for m in ("requests", "urllib", "socket", "ctypes", "win32api", "subprocess",
              "paramiko", "ftplib", "smtplib", "httpx", "websocket", "pickle",
              "marshal", "importlib", "builtins"):
        assert m in css.IMPORT_HARD_MODULES
    for m in ("pathlib", "json", "csv", "io", "re", "ast", "math", "datetime",
              "collections", "itertools", "dataclasses", "typing", "enum",
              "statistics", "unittest", "pytest", "os"):
        assert m not in css.IMPORT_HARD_MODULES

def test_module_constants_defined():
    assert "BASE/scripts/*.py" in css.READONLY_ALLOW
    assert "BASE/META/" in css.WRITE_HARD
    assert "schtasks" in css.WRITE_HARD
