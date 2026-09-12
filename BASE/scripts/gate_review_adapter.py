#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务门禁适配器：对 proposer 输出做规则裁决。accept / reject / escalate。
规则优先于 LLM；任何涉及 BASE/META/全局/PENDING/密钥/破坏性/非任务区写路径均不放行 auto。
分层：HARD（reject）> 软性底座变更意图（escalate）。scope_in/scope_out 属声明不扫描；
summary/deliverables/steps/rollback 为待检内容。"""
import os, sys, json, re
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

HARD_PATTERNS = [
    (r"BASE[\\/]", "写BASE被禁止"),
    (r"META[\\/]config\.json", "改全局config被禁止"),
    (r"PENDING[\s\\/]", "写全局PENDING被禁止"),
    (r"\.git[\\/]", "写git内部被禁止"),
    (r"rmdir|del\s+/[fq]|rm\s+-rf|format\s+", "破坏性命令被禁止"),
    (r"sk-[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{8,}", "输出含密钥样式被禁止"),
    (r"auto_merge|all_probe_green|merge_acks", "合并锁/自动合并被禁止"),
]
SOFT_PATTERNS = [
    (r"dispatch_wrapper", "提及七阶段wrapper，需走BASE提案"),
    (r"schtasks", "提及计划任务，需走BASE提案"),
]
ALLOW_PATH_PREFIX = re.compile(r"^tasks/[^/]+/task-evolve/")

# 兼容测试套件导入的合并别名（硬拒 + 软升级）
DENY_PATTERNS = HARD_PATTERNS + SOFT_PATTERNS

def _scan_hits(proposal, patterns):
    hits=[]
    for fld in ("summary","scope_in","deliverables","steps","rollback"):
        for item in ([proposal.get(fld)] if fld=="summary" else (proposal.get(fld) or [])):
            s=str(item)
            for pat,reason in patterns:
                if re.search(pat, s, re.I):
                    hits.append((reason, s[:160]))
    return hits

def review(proposal, task_id):
    reasons=[]
    if proposal.get("base_change_required"):
        reasons.append(("escalate","proposal.base_change_required=true，需走BASE提案/人工门禁"))
    for reason, snippet in _scan_hits(proposal, SOFT_PATTERNS):
        reasons.append(("escalate", "%s :: %s" % (reason, snippet)))
    for reason, snippet in _scan_hits(proposal, HARD_PATTERNS):
        reasons.append(("reject", "%s :: %s" % (reason, snippet)))
    # tool_calls 任何非空都拒（任务层不允许直接工具执行）
    if proposal.get("tool_calls"):
        reasons.append(("reject","proposal 含tool_calls，任务层不执行工具 :: %s" % str(proposal.get("tool_calls"))[:160]))
    # deliverables 写路径必须 tasks/<id>/task-evolve/
    for d in (proposal.get("deliverables") or []):
        if not ALLOW_PATH_PREFIX.match(str(d).replace("\\","/")):
            reasons.append(("reject","deliverable 路径不在任务区task-evolve: %s"%str(d)[:160]))
    if proposal.get("model","") == "error-fallback-mock" and proposal.get("risks"):
        reasons.append(("escalate","live回退mock，需人工确认: %s"%str(proposal.get("risks"))[:120]))
    if not reasons:
        return {"gate":"accept","risk":"low","auto_merge":False,
                "note":"task-local only; 不回BASE；需人工抽检后合并","reasons":[]}
    rejects=[r for r in reasons if r[0]=="reject"]
    if rejects:
        all_rs = [r[1] for r in rejects] + ["[escalate-class] " + r[1] for r in reasons if r[0]=="escalate"]
        return {"gate":"reject","risk":"high","auto_merge":False,
                "note":"规则层拒绝，不写任何BASE/全局文件","reasons":all_rs}
    return {"gate":"escalate","risk":"medium","auto_merge":False,
            "note":"转人工；可能涉及底座变更或live异常","reasons":[r[1] for r in reasons]}

if __name__=="__main__":
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
    ap.add_argument("--task",required=True); ap.add_argument("--proposal-json",required=True)
    ns=ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
    data=json.loads(Path(ns.proposal_json).read_text(encoding="utf-8"))
    print(json.dumps(review(data, ns.task), ensure_ascii=False, indent=2))
