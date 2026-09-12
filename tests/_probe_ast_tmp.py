# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, "BASE/scripts")
import code_sandbox_scan as s

for t in ["D:/x/BASE/scripts/a.py", "../../BASE/META/config.json",
          "tasks/x/task-evolve/exec/out.md", "BASE/scripts/a.py", "report.md",
          "D:\\x\\BASE\\scripts\\a.py"]:
    print(repr(t), "->", bool(s.GLOBAL_PATH_RE.search(t)))

import ast
tree = ast.parse('open("D:/x/BASE/scripts/a.py", "w").write("pwn")')
for n in ast.walk(tree):
    if isinstance(n, ast.Call):
        f = n.func
        print("call func=", type(f).__name__,
              getattr(f, "id", getattr(f, "attr", "?")))
