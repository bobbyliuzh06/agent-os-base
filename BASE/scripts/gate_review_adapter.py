#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务门禁适配器：对 proposer 输出做规则裁决。accept / reject / escalate。
规则优先于 LLM；裁决规则：
- 只读白名单（BASE/scripts、BASE/templates、BASE/docs、本任务区）：只读/否定语境 = 放行（记 note，不豁免裁决依据）。
- 写意图（写|写入|修改|删除|创建|更改|生成|落盘|清理|覆盖）指向全局路径（BASE/META/PENDING/.git/schtasks/dispatch）或
  破坏性命令/密钥样式/tool_calls/越区 deliverables → reject。
- 无写意图但提及调度/底座 → escalate；base_change_required → escalate。
"""
import os, sys, json, re
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

READONLY_ALLOW = [
    r"BASE[\\/]scripts",
    r"BASE[\\/]templates",
    r"BASE[\\/]docs",
    r"tasks[\\/]",
]
WRITE_VERBS = re.compile(r"写入|写到|存到|输出到|导出到|保存|写|修改|删除|创建|更改|改|生成|落盘|清理|覆盖|替换|重写|mkdir|rmdir|rm\s+-rf|del\s+/[fq]")
READ_VERBS = re.compile(r"只读|读取|可读|统计|枚举|分析|清点|盘点|列举|遍历|检查|校验|验证|确认|只读清单|文件清单|清单报告|目录清单|基线清单|parse|read|ls\b")
NEG_CTX = re.compile(r"不|禁止|无|不得|未|勿|不做|若需.{0,20}人工|人工裁决")
_PATH_TOKEN = re.compile(r"(?:[A-Za-z]:[\\/][A-Za-z0-9_.-]+[\\/])?(?:BASE[\\/][A-Za-z0-9_.-]*|tasks[\\/][A-Za-z0-9_.-]*|META[\\/][A-Za-z0-9_.-]*|PENDING|\.git)", re.I)
_BASE_TOKEN = re.compile(r"BASE[\\/]|META[\\/]|PENDING|\.git", re.I)
_CJK = re.compile(r"[\u4e00-\u9fff]")
_DOC_NOUN = re.compile(r"清单|快照|列表|报告|统计|摘要|索引|巡检")
_NEG_PAIR = ("禁止", "不得", "不会", "不能", "没有", "无需")
_NEG_PREFIX = re.compile(r"(?:不做|不进行|不会|不再|不要|不得|禁止|未|无|勿|非)(?:任何|一切|全部|丝毫)?$")

def _effective_writes(ctx):
    """绑定写动词与宾语：返回 [(kind, verb)]，kind in {base, task, unclear}。
    - 动词被直接否定（不修改/未改动/禁止写入）→ 忽略；
    - 动词与路径之间夹 CJK 词（改动前置/存到）→ 复合词非写指令，忽略；
    - BASE 路径后紧跟文档名词（生成 BASE/scripts 只读清单）→ 路径是读取源，视为 task。"""
    eff = []
    for w in WRITE_VERBS.finditer(ctx):
        p1 = ctx[w.start()-1] if w.start() > 0 else ""
        p2 = ctx[w.start()-2:w.start()] if w.start() >= 2 else ""
        if (p1 and p1 in "不未无勿非") or (p2 and p2 in _NEG_PAIR) or _NEG_PREFIX.search(ctx[:w.start()]):
            continue
        tail = ctx[w.end():w.end()+45]
        mp = _PATH_TOKEN.search(tail)
        if mp:
            if _CJK.search(tail[:mp.start()]) or mp.start() > 4:
                continue
            after = tail[mp.end():mp.end()+10]
            if _BASE_TOKEN.search(mp.group()) and _DOC_NOUN.search(after[:8]):
                kind = "task"
            else:
                kind = "base" if _BASE_TOKEN.search(mp.group()) else "task"
            eff.append((kind, w.group()))
        else:
            head = tail[:2]
            if head and not _CJK.search(head):
                eff.append(("unclear", w.group()))
    return eff
SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{8,}|gh[pour]_[A-Za-z0-9]{8,}", "输出含密钥样式被禁止"),
    (r"密码\s*=|password\s*=|token\s*=\s*['\"][A-Za-z0-9]{8,}", "明文凭据"),
]
WRITE_PATH_PATTERNS = [
    (r"BASE[\\/]META", "写BASE/META被禁止"),
    (r"BASE[\\/]", "写BASE被禁止"),
    (r"META[\\/]config\.json", "改全局config被禁止"),
    (r"PENDING[\s\\/]", "写全局PENDING被禁止"),
    (r"\.git[\\/]", "写git内部被禁止"),
    (r"rmdir|rm\s+-rf|del\s+/[fq]|format\s+[A-Za-z]:|diskpart", "破坏性命令被禁止"),
]
SOFT_PATTERNS = [
    (r"dispatch_wrapper", "提及七阶段wrapper，需走BASE提案"),
    (r"schtasks", "提及计划任务，需走BASE提案"),
]
ALLOW_PATH_PREFIX = re.compile(r"^tasks/[^/]+/task-evolve/")

# 兼容测试套件导入的合并别名
DENY_PATTERNS = WRITE_PATH_PATTERNS + SOFT_PATTERNS + SECRET_PATTERNS

def _readonly_hit(s):
    return any(re.search(p, s, re.I) for p in READONLY_ALLOW)

def _classify_item(s):
    """返回 (reject_hits, escalate_hits, notes)"""
    rejects, escalates, notes = [], [], []
    for pat, name in SECRET_PATTERNS:
        m = re.search(pat, s, re.I)
        if m:
            rejects.append(name)
    for pat, name in WRITE_PATH_PATTERNS:
        m = re.search(pat, s, re.I)
        if not m:
            continue
        ctx = s[max(0, m.start()-80):m.end()+80]
        if name == "破坏性命令被禁止":
            rejects.append("%s :: %s" % (name, s[:160]))
            continue
        eff = _effective_writes(ctx)
        base_w = [k for k, v in eff if k == "base"]
        task_w = [k for k, v in eff if k == "task"]
        decl = bool(READ_VERBS.search(ctx) or NEG_CTX.search(ctx))
        if base_w:
            rejects.append("%s :: %s" % (name, s[:160]))
        elif task_w:
            notes.append("写入目标为任务区、BASE 仅读取对象（已记录）: %s :: %s" % (name, s[:120]))
        elif eff:  # 写动词无明确宾语 → 保守拒绝
            rejects.append("%s :: %s" % (name, s[:160]))
        elif decl:
            notes.append("只读/声明（已记录）: %s :: %s" % (name, s[:120]))
        else:
            rejects.append("%s :: %s" % (name, s[:160]))
    for pat, name in SOFT_PATTERNS:
        m = re.search(pat, s, re.I)
        if not m:
            continue
        ctx = s[max(0, m.start()-80):m.end()+80]
        if WRITE_VERBS.search(ctx):
            escalates.append("%s :: %s" % (name, s[:160]))
        elif READ_VERBS.search(ctx) or NEG_CTX.search(ctx):
            notes.append("调度/底座提及（只读或否定，已记录）: %s :: %s" % (name, s[:120]))
        else:
            escalates.append("%s :: %s" % (name, s[:160]))
    return rejects, escalates, notes

def review(proposal, task_id):
    rejects, escalates, notes = [], [], []
    if proposal.get("base_change_required"):
        escalates.append("proposal.base_change_required=true，需走BASE提案/人工门禁")
    for fld in ("summary", "scope_in", "deliverables", "steps", "rollback"):
        items = [proposal.get(fld)] if fld == "summary" else (proposal.get(fld) or [])
        for item in items:
            r, e, n = _classify_item(str(item))
            rejects += r; escalates += e; notes += n
    if proposal.get("tool_calls"):
        rejects.append("proposal 含tool_calls，任务层不执行工具")
    for d in (proposal.get("deliverables") or []):
        if isinstance(d, dict):
            dp = str(d.get("path") or d.get("file") or "").replace("\\", "/")
            if not ALLOW_PATH_PREFIX.match(dp):
                rejects.append("deliverable 路径不在任务区task-evolve: %s" % str(d)[:160])
            else:
                notes.append("deliverable desc: %s" % str(d.get("desc", ""))[:100])
        else:
            if not ALLOW_PATH_PREFIX.match(str(d).replace("\\", "/")):
                rejects.append("deliverable 路径不在任务区task-evolve: %s" % str(d)[:160])
    if proposal.get("model", "") == "error-fallback-mock" and proposal.get("risks"):
        escalates.append("live回退mock，需人工确认: %s" % str(proposal.get("risks"))[:120])
    if not rejects and not escalates:
        return {"gate": "accept", "risk": "low", "auto_merge": False,
                "note": "task-local only; 不回BASE；需人工抽检后合并",
                "reasons": [], "notes": notes}
    if rejects:
        return {"gate": "reject", "risk": "high", "auto_merge": False,
                "note": "规则层拒绝，不写任何BASE/全局文件",
                "reasons": rejects, "notes": notes}
    return {"gate": "escalate", "risk": "medium", "auto_merge": False,
            "note": "转人工；可能涉及底座变更或live异常",
            "reasons": escalates, "notes": notes}

if __name__ == "__main__":
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=os.environ.get("AGENT_OS_ROOT", ""))
    ap.add_argument("--task", required=True); ap.add_argument("--proposal-json", required=True)
    ns = ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"] = ns.root
    data = json.loads(Path(ns.proposal_json).read_text(encoding="utf-8"))
    print(json.dumps(review(data, ns.task), ensure_ascii=False, indent=2))
