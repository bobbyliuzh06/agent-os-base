import os, sys, json
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent / "BASE" / "scripts"))
from gate_review_adapter import review, _effective_writes
import code_sandbox_scan as css

def _p(**over):
    base = {
        "summary": "测试提案",
        "scope_in": ["tasks/demo/task-evolve"],
        "scope_out": ["BASE"],
        "deliverables": ["tasks/demo/task-evolve/out/result.md"],
        "steps": ["解析", "生成"],
        "risks": [],
        "rollback": ["删除 out/"],
        "acceptance": ["rc=0"],
        "base_change_required": False,
        "tool_calls": [],
    }
    base.update(over)
    return base

# ---- 门禁：只读白名单 + 写动词绑定（STEP30 硬化） ----

def test_readonly_base_scripts_is_note():
    p = _p(summary="只读统计 D:/agent-os/BASE/scripts 目录下 *.py 文件数，生成清单报告 tasks/demo/task-evolve/report.md。全程不写 BASE")
    g = review(p, "demo")
    assert g["gate"] == "accept"
    assert any("已记录" in n for n in g.get("notes", []))

def test_negated_verb_no_write_intent():
    p = _p(steps=["对 BASE/scripts 做只读清单，不修改 BASE/META/config/PENDING"])
    g = review(p, "demo")
    assert g["gate"] == "accept"

def test_doc_noun_after_base_path_is_task():
    p = _p(steps=["7. 自检：再次生成 BASE/scripts 只读清单与基线比对，确认零改动。"])
    g = review(p, "demo")
    assert g["gate"] == "accept"

def test_write_verb_bound_to_base_still_rejects():
    p = _p(steps=["不写 BASE，但把结果写入 BASE/META/config.json"])
    g = review(p, "demo")
    assert g["gate"] == "reject"

def test_free_write_verb_no_object_rejects():
    p = _p(steps=["对 BASE/scripts 只读巡检（其实是删除）"])
    g = review(p, "demo")
    assert g["gate"] == "reject"

def test_dict_deliverables_normalized():
    p = _p(deliverables=[{"path": "tasks/demo/task-evolve/report.md", "desc": "统计报告"}])
    g = review(p, "demo")
    assert g["gate"] == "accept"

def test_dict_deliverables_out_of_task_rejects():
    p = _p(deliverables=[{"path": "/etc/passwd", "desc": "x"}])
    g = review(p, "demo")
    assert g["gate"] == "reject"

def test_effective_writes_binding():
    assert ("base", "写入") in _effective_writes("把结果写入 BASE/META/config.json")
    assert [k for k, v in _effective_writes("对 BASE/scripts 做只读清单，结果存到 tasks/demo/task-evolve/report.md")] == ["task"]
    assert _effective_writes("不修改 BASE/META/config.json") == []
    assert _effective_writes("改动前置 BASE/scripts 只读清点") == []
    assert _effective_writes("生成 BASE/scripts 只读清单") == [("task", "生成")]
    assert _effective_writes("仅做 directory listing 与文件读取权限探测，不做任何写入。") == []
    assert _effective_writes("不断修改 BASE/scripts 下文件") == [("base", "修改")]

def test_readability_probe_without_write_is_note():
    p = _p(steps=["1. 确认工作目录与 BASE/scripts 可读性，仅做 directory listing 与文件读取权限探测，不做任何写入。"])
    g = review(p, "demo")
    assert g["gate"] == "accept"

def test_deliverable_desc_with_file_listing_is_note():
    p = _p(deliverables=["tasks/demo/task-evolve/report.md，包含 D:/agent-os/BASE/scripts 下 *.py 文件清单、各文件行数、文件总数与总行数"])
    g = review(p, "demo")
    assert g["gate"] == "accept"

def test_bare_listing_with_replace_verb_rejects():
    p = _p(steps=["把 BASE/scripts 的清单替换成伪造清单"])
    g = review(p, "demo")
    assert g["gate"] == "reject"

# ---- 沙箱静态扫描：AST 常量 + open 模式拆分 ----

def _tmp_py(tmp_path, name, src):
    p = tmp_path / name
    p.write_text(src, encoding="utf-8")
    return p

GOOD_READ = (
    'import os, pathlib\n'
    'root = os.environ.get("AGENT_OS_ROOT", "")\n'
    'scripts = pathlib.Path(root) / "BASE" / "scripts"\n'
    'for f in scripts.glob("*.py"):\n'
    '    with f.open(encoding="utf-8") as fh:\n'
    '        n = sum(1 for _ in fh)\n'
    'pathlib.Path(os.environ.get("AGENT_SANDBOX_DIR", "."), "report.md").write_text("done", encoding="utf-8")\n'
)

def test_scan_good_read_ok(tmp_path):
    p = _tmp_py(tmp_path, "good.py", GOOD_READ)
    r = css._scan_file(p, "demo")
    assert r["risk"] == "ok"

def test_scan_dynamic_write_target_noted(tmp_path):
    src = (GOOD_READ.rsplit("\n", 1)[0] + "\n"
           + 'pathlib.Path(os.environ.get("AGENT_SANDBOX_DIR", ".")) / "report.md"\n'
           + 'pathlib.Path(os.environ.get("AGENT_SANDBOX_DIR", ".")).joinpath("report.md").write_text("x", encoding="utf-8")\n')
    p = _tmp_py(tmp_path, "good.py", src)
    r = css._scan_file(p, "demo")
    assert r["risk"] == "ok"
    assert any("动态写路径" in n for n in r.get("notes", []))

def test_scan_ast_constant_global_path_blocks(tmp_path):
    p = _tmp_py(tmp_path, "bad.py", 'open("D:/x/BASE/scripts/a.py", "w").write("pwn")\n')
    r = css._scan_file(p, "demo")
    assert r["risk"] == "block"
    assert any(h[0] == "AST常量含全局路径" for h in r["hits"])
    assert any(h[0] == "AST写目标全局路径" for h in r["hits"])

def test_scan_write_text_config_blocks(tmp_path):
    p = _tmp_py(tmp_path, "bad.py", 'import pathlib\npathlib.Path("../../BASE/META/config.json").write_text("{}", encoding="utf-8")\n')
    r = css._scan_file(p, "demo")
    assert r["risk"] == "block"

def test_scan_abs_write_outside_task_blocks(tmp_path):
    p = _tmp_py(tmp_path, "bad.py", 'with open("C:/Users/me/out.txt", "w") as fh:\n    fh.write("x")\n')
    r = css._scan_file(p, "demo")
    assert r["risk"] == "block"
    assert any(h[0] == "AST绝对写越区" for h in r["hits"])

def test_scan_bom_tolerated(tmp_path):
    p = tmp_path / "bom.py"
    p.write_bytes("\ufeff".encode("utf-8") + GOOD_READ.encode("utf-8"))
    r = css._scan_file(p, "demo")
    assert r["risk"] in ("ok", "warn")
