# -*- coding: utf-8 -*-
import sys, io, ast
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
src = '\ufeffopen("D:/x/BASE/scripts/a.py", "w").write("pwn")'
try:
    ast.parse(src)
    print("parse BOM: ok")
except SyntaxError as e:
    print("parse BOM: SyntaxError ->", e.msg)
print("parse BOM stripped: ok" if ast.parse(src.lstrip("\ufeff")) else "")
