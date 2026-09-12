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

_CONF_DEFAULTS = {
    "default_model": "deepseek-v4-flash",
    "code_model": "deepseek-v4-pro",
    "base_url": "https://api.deepseek.com",
    "thinking": {"enabled": False, "reasoning_effort": "low"},
    "code_thinking": {"enabled": True, "reasoning_effort": "high"},
    "temperature": {"structured": 0.2, "analysis": 1.0},
    "max_tokens": {"structured": 2048, "code": 4096},
    "json_mode": True,
    "fail_fallback_mock": True,
    "key_sources": ["env:DEEPSEEK_API_KEY", "winreg:HKCU\\Environment/DEEPSEEK_API_KEY"],
}

def _merge_conf(base, over):
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge_conf(base[k], v)
        else:
            base[k] = v

def load_proposer_config():
    """读取 BASE/META/proposer.config.json；缺失/损坏用内嵌默认，不报错。"""
    conf = json.loads(json.dumps(_CONF_DEFAULTS))
    try:
        C = _lc()
        p = Path(C.meta_dir) / "proposer.config.json"
        if p.exists():
            _merge_conf(conf, json.loads(p.read_text(encoding="utf-8")))
    except Exception:
        pass
    return conf

def _read_key_from_registry():
    try:
        import winreg
        for hive, sub in [(winreg.HKEY_CURRENT_USER, "Environment"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")]:
            try:
                with winreg.OpenKey(hive, sub) as key:
                    val, _ = winreg.QueryValueEx(key, "DEEPSEEK_API_KEY")
                    if val:
                        return str(val)
            except Exception:
                pass
    except Exception:
        pass
    return ""

def _resolve_api_key(api_key):
    """env → winreg；仅进程内存使用，不打印、不写文件。"""
    if api_key:
        return api_key
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    return key or _read_key_from_registry()

def _pick_proposer(conf, req_text, model, thinking, reasoning, no_think, temperature):
    low = (req_text or "").lower()
    if any(k in low for k in ["代码", "修复", "单测", "实现", "bug", "code", "fix", "test"]):
        kind = "code"
    elif any(k in low for k in ["分析", "统计", "数据处理", "数据分析", "analysis", "data"]):
        kind = "analysis"
    else:
        kind = "structured"
    use_model = model or (conf["code_model"] if kind == "code" else conf["default_model"])
    if temperature is not None:
        use_temp = temperature
    elif kind == "code":
        # V4：thinking profile 不写 temperature；code 无思考时才用确定性温度
        use_temp = conf["temperature"].get("code") if "code" in conf.get("temperature", {}) else 0.0
    else:
        use_temp = conf["temperature"].get(kind, 0.2)
    use_tokens = conf["max_tokens"].get("code" if kind == "code" else "structured", 2048)
    th = conf["code_thinking"] if kind == "code" else conf["thinking"]
    th_enabled = bool(th.get("enabled", False)) and "pro" in use_model and not no_think and thinking
    th_effort = reasoning or th.get("reasoning_effort", "low")
    if th_effort not in ("low", "high", "max"):
        th_effort = th.get("reasoning_effort", "low")
    return {"kind": kind, "model": use_model, "temperature": use_temp, "max_tokens": use_tokens,
            "thinking": th_enabled, "reasoning_effort": th_effort, "json_mode": bool(conf.get("json_mode", True)),
            "base_url": conf.get("base_url") or "https://api.deepseek.com"}

def _build_request_kwargs(pick, system, user):
    """V4 请求体：thinking 开启 → 不写 temperature/top_p，只发 reasoning_effort + thinking。"""
    kwargs = {"model": pick["model"],
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
              "max_tokens": pick["max_tokens"], "stream": False,
              "response_format": {"type": "json_object"}}
    if pick["thinking"]:
        kwargs["reasoning_effort"] = pick["reasoning_effort"]
        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
    else:
        kwargs["temperature"] = pick["temperature"]
    return kwargs

def deepseek_propose(req_text, task_id, model="", thinking=True, reasoning=None, no_think=False,
                     temperature=None, api_key=None, base_url=None, timeout=60):
    conf = load_proposer_config()
    pick = _pick_proposer(conf, req_text, model, thinking, reasoning, no_think, temperature)
    print("PROPOSER_CFG kind=%s model=%s temperature=%s thinking=%s reasoning=%s max_tokens=%s json_mode=%s (脱敏，无密钥)" % (
        pick["kind"], pick["model"], pick["temperature"], pick["thinking"], pick["reasoning_effort"],
        pick["max_tokens"], pick["json_mode"]))
    api_key = _resolve_api_key(api_key)
    if not api_key:
        raise RuntimeError("no DEEPSEEK_API_KEY; 回退 mock 或显式 --mock")
    base_url = base_url or pick["base_url"]
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("未安装 openai SDK；pip install openai 或用 --mock")
    client = OpenAI(api_key=api_key, base_url=base_url)
    system = (
        "你是 agent-os 任务提案器。仅输出 JSON，绝不直接执行。字段必须含：" + ",".join(SCHEMA_REQUIRED) +
        " 和 tool_calls（恒为空数组）。" +
        "若方案需要改 BASE/META/config/PENDING/schtasks/全局调度/删除文件/写密钥，"
        "必须把 base_change_required 置 true 并在 scope_out 说明，由规则层人工裁决，不得自行给出写路径或命令。"
        "禁止输出任何密钥；所有产物路径必须以 tasks/<task_id>/task-evolve/ 开头。"
    )
    user = "TASK_ID=%s\nREQ:\n%s\n请按上述 schema 输出纯 JSON。" % (task_id, req_text)
    # V4：thinking 开启的 profile 不写 temperature/top_p（见 _build_request_kwargs）
    kwargs = _build_request_kwargs(pick, system, user)
    r = client.chat.completions.create(**kwargs)
    content = r.choices[0].message.content or "{}"
    data = json.loads(content)
    data["proposal_id"] = "prop-%s-%s" % (task_id, _now())
    data["model"] = pick["model"]
    for k in SCHEMA_REQUIRED:
        if k not in data: data[k] = (False if k=="base_change_required" else [])
    data.setdefault("tool_calls", [])
    # 规范化 deliverables：dict 形式（{path,desc}）→ 纯路径字符串数组；desc 并入 deliverable_descs
    raw_del = data.get("deliverables") or []
    norm_del, descs = [], []
    for d in raw_del:
        if isinstance(d, dict):
            p = d.get("path") or d.get("file")
            if isinstance(p, str) and p.strip():
                norm_del.append(p.strip())
                if d.get("desc"):
                    descs.append("%s: %s" % (p.strip(), str(d["desc"])[:80]))
        elif isinstance(d, str) and d.strip():
            norm_del.append(d.strip())
    data["deliverables"] = norm_del
    if descs:
        data["deliverable_descs"] = descs
    return data

def propose(req_text, task_id, live=False, model="", thinking=True, reasoning=None, no_think=False, temperature=None):
    if live:
        try:
            return deepseek_propose(req_text, task_id, model=model, thinking=thinking,
                                    reasoning=reasoning, no_think=no_think, temperature=temperature)
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
