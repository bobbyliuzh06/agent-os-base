#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-os new：交互澄清并生成任务工作区。只读提问+写 tasks/<id>，不跑 evolve。"""
import os, sys, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cli_common import (cfg, ensure_dirs, load_registry, save_registry,
                        gen_task_id, find_similar, write_text, tasks_dir)

def ask(prompt, default=""):
    try:
        v = input(prompt + ((" [%s] " % default) if default else " ")).strip()
    except Exception:
        v = ""
    return v or default

def main():
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=os.environ.get("AGENT_OS_ROOT",""))
    ap.add_argument("--domain", default=""); ap.add_argument("--goal", default=""); ap.add_argument("--noninteractive", action="store_true")
    ns, _ = ap.parse_known_args()
    if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
    ensure_dirs()
    C = cfg()
    domain = ns.domain or (not ns.noninteractive and ask("1/领域(如 sales/website/seo):")) or "general"
    goal = ns.goal or (not ns.noninteractive and ask("2/目标(一句话,如 q3分析/改版方案):")) or "task"
    reg = load_registry()
    sim = find_similar(domain, goal, reg)
    if sim and not ns.noninteractive:
        print("[去重] 已有相似任务: %s；可复用而非新建。" % ", ".join(sim))
        if ask("仍新建?(y/N):","n").lower()!="y":
            print("已取消，使用已有任务即可。"); return 0
    tid = gen_task_id(domain, goal)
    base = tasks_dir()/tid
    (base/"workspace").mkdir(parents=True, exist_ok=True)
    (base/"task-evolve").mkdir(parents=True, exist_ok=True)
    req = f"""# REQ-{tid}

- 版本基线：{ (C.get('version') or 'v0.4-proto') }（base commit 见 BASE/docs/AGENT-OS-USAGE.md）
- 领域：{domain}
- 目标：{goal}
- 范围：必做 / 不做 / 后续（交互未填请补）
- 输入：<路径/格式/权限>
- 输出：<路径/格式/命名>
- 验收：功能 / 质量(rc=0、无unknown、回归全绿、人工抽检) / 性能成本
- 约束：技术栈环境 / 安全(不写明文密钥) / 合规(审计日志)
- 风险与回滚：失败点+保留旧版+还原方案
- 是否允许改底座规则：否（如需改→走 BASE 提案/门禁，不在本任务区直改）
- 自动化程度：全人工 / 半自动(仅草案) / 自动(仅白名单+四锁)
- 观察周期：如跑3轮再评估合并
"""
    write_text(base/"REQ.md", req)
    write_text(base/"config.json", json.dumps({
        "task_id": tid, "base_version": C.get("version","proto"),
        "use_base_evolve": False, "per_task_evolve": False,
        "lock": True, "schedule": "manual"
    }, ensure_ascii=False, indent=2))
    reg["tasks"].append({"id":tid,"domain":domain,"goal":goal,"path":str(base),
                         "status":"created","created":__import__("datetime").date.today().isoformat()})
    save_registry(reg)
    print("CREATED task=%s" % tid)
    print("REQ=%s" % (base/"REQ.md"))
    print("下一步：补充 REQ.md 后执行  agent-os watch  查看；run/evolve 待后续 STEP。")
    return 0

if __name__=="__main__":
    try: sys.exit(main())
    except Exception as e:
        print("new error:", e); sys.exit(1)
