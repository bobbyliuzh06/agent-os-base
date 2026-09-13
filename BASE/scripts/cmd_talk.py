# -*- coding: utf-8 -*-
"""cmd_talk.py —— agent-os talk：自然语言 → charter 入口（第九轮 P1 行动）。

门槛从"会不会写代码"换成"有没有目标"：用户说一句人话，
1) LLM（deepseek-v4-flash）把目标翻译成 charter 骨架（id/name/mission/constraints/
   approval_points/cadence/evaluation，硬约束模板兜底）；LLM 失败回退规则模板；
2) 确定性规则层对提案做门禁（scope_in=新任务目录，scope_out=BASE）；
3) 写 charter.yaml + 决策留痕；门禁 reject 则不写，如实报告。
用法：agent-os talk "帮我长期盯住一组重要链接"
诚实：charter 由 LLM 起草、规则层门禁、需人工审阅后运行——不声称全自动。"""
import hashlib, io, json, pathlib, re, sys
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import yaml
from config_loader import get_root
from gate_review_adapter import review as gate_review
from proposer import deepseek_propose

def slugify(text):
    # 保留中文（\u4e00-\u9fff）与字母数字，其余转连字符；空结果用原文 sha256 前 8 位兜底
    s = re.sub(r"[^\u4e00-\u9fff\w]+", "-", text)[:24].strip("-")
    if not s:
        s = "goal-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return s

def rule_template(goal):
    return {
        "id": "goal-%s" % slugify(goal),
        "name": goal[:40],
        "mission": goal,
        "constraints": ["只写本任务目录；不写 BASE", "高风险动作（真钱/发布/删除）必须人工"],
        "approval_points": {"自动": "观察/提议/门禁/记录", "人工": "charter 自修订与高风险动作"},
        "cadence": "weekly",
        "evaluation": {"domain": "goal-maintenance",
                       "purpose": goal,
                       "metrics": [{"name": "周期闭环率", "direction": "eq", "target": "100%", "source": "decisions.jsonl"}],
                       "degradation": "真值不可得时显式标注，不编造"},
    }

def main():
    argv = [a for a in sys.argv[1:] if a != "--run"]
    goal = " ".join(argv).strip() if argv else ""
    if not goal:
        print("用法：agent-os talk \"帮我长期盯住一组重要链接\" [--run]")
        return 1
    root = get_root()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    task_id = "talk-%s-%s" % (slugify(goal), ts)
    task = root / "tasks" / task_id / "task-evolve"
    prompt = ("把用户的一句话目标翻译成 agent-os 项目章程（charter）骨架。只输出 JSON（<400字），键固定："
              "id(小写连字符)、name、mission、constraints(字符串列表，必须含'只写本任务目录'与'高风险动作必须人工')、"
              "approval_points(自动/人工)、cadence(weekly|daily|event)、evaluation(domain/purpose/metrics 数组/"
              "degradation)。用户目标：" + goal)
    live = True
    try:
        r = deepseek_propose(prompt, "talk-%s" % ts, model="deepseek-v4-flash", thinking=False)
        charter = {k: r.get(k) for k in ("id", "name", "mission", "constraints",
                                         "approval_points", "cadence", "evaluation")}
        if not charter.get("id"):
            charter = rule_template(goal)
            live = False
    except Exception:
        charter = rule_template(goal)
        live = False
    if not isinstance(charter.get("constraints"), list) or not charter["constraints"]:
        charter["constraints"] = ["只写本任务目录；不写 BASE", "高风险动作必须人工"]
    if not charter.get("evaluation") or not isinstance(charter.get("evaluation"), dict):
        charter["evaluation"] = rule_template(goal)["evaluation"]
    charter["id"] = re.sub(r"[^a-z0-9-]", "", str(charter.get("id") or "goal"))[:40] or "goal-%s" % slugify(goal)

    task.mkdir(parents=True, exist_ok=True)
    charter_text = yaml.safe_dump(charter, allow_unicode=True, sort_keys=False)
    proposal = {"summary": "talk 入口生成的章程提案：%s" % goal[:60],
                "scope_in": ["tasks/%s" % task_id], "scope_out": ["BASE"],
                "deliverables": ["tasks/%s/task-evolve/charter.yaml" % task_id],
                "steps": ["LLM 起草" if live else "规则模板起草", "规则门禁", "人工审阅后运行"],
                "risks": ["LLM 起草的 charter 需人工审阅；门禁只保证范围合规"],
                "rollback": ["删除 tasks/%s" % task_id],
                "acceptance": ["门禁 accept", "charter 含 evaluation 段"],
                "base_change_required": False, "tool_calls": []}
    g = gate_review(proposal, task_id)
    if g["gate"] != "accept":
        print("TALK 门禁 %s：%s —— 未写入（如实报告）" % (g["gate"], g.get("reasons")))
        return 1
    (task / "charter.yaml").write_text("# -*- coding: utf-8 -*-\n" + charter_text, encoding="utf-8")
    (task / "memory").mkdir(exist_ok=True)
    with open(task / "memory" / "decisions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"id": "D-TALK-%s" % ts, "run_id": "talk", "action": "nl-to-charter",
                            "goal": goal, "live_llm": live, "gate": g["gate"], "decided_at": ts},
                           ensure_ascii=False) + "\n")
    run_cycle = "--run" in sys.argv
    print("=== agent-os talk：自然语言 → charter 走通 ===\n"
          "你的目标：%s\n起草方式：%s\n门禁：%s\n产物：%s"
          % (goal, "LLM 起草" if live else "规则模板兜底", g["gate"], task / "charter.yaml"))
    if run_cycle:
        from talk_run_cycle import run_first_cycle
        ok = run_first_cycle(task, goal)
        return 0 if ok else 1
    print("下一步：人工审阅 charter 后运行（agent-os run）；或 agent-os talk --run \"你的目标\" 立即跑第一周期。"
          "门禁保证范围合规，不替代你审内容。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
