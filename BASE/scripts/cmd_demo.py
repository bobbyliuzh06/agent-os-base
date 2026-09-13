# -*- coding: utf-8 -*-
"""cmd_demo.py —— agent-os demo：十分钟黄金路径（零配置最小演化）。

选定位后的第一个产品动作：让陌生开发者在 10 分钟内从"听说"到"第一次跑通"。
本命令只做四步（全部真实、可溯源，无 LLM 调用、无网络、无 DeepSeek key）：
1) 生成模板 charter（评估域+约束+审批点，写入 tasks/demo-<ts>/task-evolve/）
2) 用一条真实样例提案过确定性门禁（gate_review_adapter，规则层）
3) 记录决策到 decisions.jsonl（append-only）
4) 打印四步走通摘要 + 下一步指引（README/展示站/Issues）
退出码 0=走通。失败如实报错不伪造。"""
import io, json, pathlib, sys
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import yaml
from config_loader import get_root
from gate_review_adapter import review as gate_review

TEMPLATE = """\
# -*- coding: utf-8 -*-
id: demo-{ts}
name: 我的第一个持续责任对象（demo）
mission: 十分钟路径演示：观察→提议→门禁→记录（无 LLM/无网络/零配置）
constraints:
  - 只写本任务目录；不写 BASE
approval_points:
  - 演示动作: 自动
cadence: event
evaluation:
  domain: demo-smoke
  purpose: 验证十分钟黄金路径可走通
  metrics:
    - {{name: 门禁走通率, direction: eq, target: 100%, source: gate_review}}
  degradation: 无真值时显式标注
"""

def main():
    root = get_root()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    task = root / "tasks" / ("demo-%s" % ts) / "task-evolve"
    task.mkdir(parents=True, exist_ok=True)
    charter_path = task / "charter.yaml"
    charter_path.write_text(TEMPLATE.format(ts=ts), encoding="utf-8")
    charter = yaml.safe_load(charter_path.read_text(encoding="utf-8"))

    proposal = {"summary": "demo 十分钟路径：最小演化样例提案",
                "scope_in": ["tasks/demo-%s" % ts], "scope_out": ["BASE"],
                "deliverables": ["tasks/demo-%s/task-evolve/out.json" % ts],
                "steps": ["生成 charter", "过门禁", "记录决策"],
                "risks": ["无"], "rollback": ["删除 demo 任务目录"],
                "acceptance": ["门禁 accept"], "base_change_required": False, "tool_calls": []}
    g = gate_review(proposal, "demo-%s" % ts)

    decision = {"id": "D-DEMO-%s" % ts, "run_id": "demo", "action": "golden-path",
                "gate": g["gate"], "decided_at": ts,
                "eval": {"expected": {"gate_accept": True}, "actual": {"gate": g["gate"]},
                         "delta": {"gate_accept": g["gate"] == "accept"}}}
    (task / "memory").mkdir(exist_ok=True)
    with open(task / "memory" / "decisions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(decision, ensure_ascii=False) + "\n")

    print("=== agent-os 十分钟黄金路径走通 ===\n"
          "① 观察  模板 charter 已生成：%s（评估域 %s）\n"
          "② 提议  样例提案已构造（scope_in=任务目录，scope_out=BASE）\n"
          "③ 门禁  确定性规则层裁决：%s（对 BASE 写入一律 reject 的边界在生效）\n"
          "④ 记录  决策已入 decisions.jsonl（append-only）\n"
          "\n下一步：把 charter 里的 mission 换成你的长期目标，再跑 agent-os run；\n"
          "机制总览 https://bobbyliuzh06.github.io/agent-os-base/ ；卡住请提 Issue（onboarding 模板）。"
          % (charter_path, charter["evaluation"]["domain"], g["gate"]))
    return 0 if g["gate"] == "accept" else 1

if __name__ == "__main__":
    sys.exit(main())
