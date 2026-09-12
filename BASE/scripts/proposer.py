#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务提案适配器：mock 默认；--live 调 DeepSeek。只产出结构化草案 JSON，不写任何文件、不执行。"""
import os, sys, json, argparse, datetime, re
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

SCHEMA_REQUIRED = ["summary","scope_in","scope_out","deliverables","steps","risks","rollback","acceptance","base_change_required"]

def _now(): return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def mock_propose(req_text, task_id):
    # 确定性草案：基于 REQ 文本做关键词抽取，不联网。用于回归/离线。
    low = (req_text or "").lower()
    base_change = any(k in low for k in ["改base规则：是","改底座规则：是","改meta","改config","修改全局调度","改dispatch","dispatch_wrapper","schtasks"])
    scope_out = ["任何 BASE/META 规则修改","任何全局 schtasks/dispatch 修改","删除生产数据","明文写入密钥"]
    # 摘要只取领域/目标字段（模板元数据如 BASE/docs 引用不进入待检文本）
    m_dom = re.search(r"领域：(.+)", req_text or "")
    m_goal = re.search(r"目标：(.+)", req_text or "")
    summary = "领域:%s 目标:%s" % (
        (m_dom.group(1).strip() if m_dom else "?"),
        (m_goal.group(1).strip() if m_goal else (req_text or "").strip()[:80]))
    if "report" in low or "报告" in low:
        deliverables=["tasks/%s/task-evolve/out/report.md" % task_id]
        steps=["读取输入","清洗","生成报告","人工抽检"]
    elif "seo" in low:
        deliverables=["tasks/%s/task-evolve/out/seo-suggestions.json" % task_id]
        steps=["抓取页面","关键词分析","出建议","人工审核"]
    else:
        deliverables=["tasks/%s/task-evolve/out/result.md" % task_id]
        steps=["解析REQ","制定方案","生成草案","等待gate"]
    return {
        "proposal_id":"prop-%s-%s" % (task_id, _now()),
        "model":"mock-v1",
        "summary":summary,
        "scope_in":["tasks/%s 内全部产物" % task_id],
        "scope_out":scope_out,
        "deliverables":deliverables,
        "steps":steps,
        "risks":["mock未接真实业务系统；产出仅草案"],
        "rollback":["删除 task-evolve/out 下本次产物","REQ 保持不变"],
        "acceptance":["rc=0","无unknown","人工抽检通过","不修改BASE"],
        "base_change_required": bool(base_change),
        "tool_calls":[]  # mock 不允许任何工具调用
    }

def deepseek_propose(req_text, task_id, model="deepseek-v4-flash", thinking=True, api_key=None, base_url=None, timeout=60):
    if not api_key:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("no DEEPSEEK_API_KEY; 回退 mock 或显式 --mock")
    base_url = base_url or "https://api.deepseek.com"
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("未安装 openai SDK；pip install openai 或用 --mock")
    client = OpenAI(api_key=api_key, base_url=base_url)
    system = (
        "你是 agent-os 任务提案器。仅输出 JSON，绝不直接执行。字段必须含：" + ",".join(SCHEMA_REQUIRED) +
        "。额外字段 tool_calls 只能是空数组；若方案需要改 BASE/META/全局调度/删除文件/写密钥，"
        "必须把 base_change_required 置 true 并在 scope_out 说明，由规则层人工裁决，不得自行给出写路径或命令。"
        "所有产物路径必须以 tasks/<task_id>/task-evolve/ 开头。"
    )
    user = "TASK_ID=%s\nREQ:\n%s\n请按上述 schema 输出纯 JSON。" % (task_id, req_text)
    kwargs = dict(model=model, messages=[{"role":"system","content":system},{"role":"user","content":user}],
                  temperature=0.2, max_tokens=2048, stream=False,
                  response_format={"type":"json_object"})
    if thinking and "pro" in model:
        kwargs["reasoning_effort"]="high"; kwargs["extra_body"]={"thinking":{"type":"enabled"}}
    r = client.chat.completions.create(**kwargs)
    content = r.choices[0].message.content or "{}"
    data = json.loads(content)
    data["proposal_id"] = "prop-%s-%s" % (task_id, _now())
    data["model"] = model
    for k in SCHEMA_REQUIRED:
        if k not in data: data[k] = (False if k=="base_change_required" else [])
    data.setdefault("tool_calls", [])
    return data

def propose(req_text, task_id, live=False, model="deepseek-v4-flash", thinking=True):
    if live:
        try:
            return deepseek_propose(req_text, task_id, model=model, thinking=thinking)
        except Exception as e:
            return {"proposal_id":"prop-%s-%s"%(task_id,_now()),"model":"error-fallback-mock",
                    "summary":"live失败回退mock: %s"%e, "scope_in":["tasks/%s"%task_id],
                    "scope_out":["BASE"],"deliverables":[],"steps":[],"risks":[str(e)],
                    "rollback":[],"acceptance":[],"base_change_required":False,"tool_calls":[]}
    return mock_propose(req_text, task_id)

if __name__ == "__main__":
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
    ap.add_argument("--task",required=True); ap.add_argument("--req",default="")
    ap.add_argument("--live",action="store_true"); ap.add_argument("--mock",action="store_true")
    ap.add_argument("--model",default="deepseek-v4-flash"); ap.add_argument("--no-think",action="store_true")
    ns=ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
    C=_lc(); req=ns.req or (Path(C.tasks_dir)/ns.task/"REQ.md").read_text(encoding="utf-8",errors="replace") if (Path(C.tasks_dir)/ns.task/"REQ.md").exists() else ""
    live = ns.live and not ns.mock
    out=propose(req, ns.task, live=live, model=ns.model, thinking=not ns.no_think)
    print(json.dumps(out, ensure_ascii=False, indent=2))
