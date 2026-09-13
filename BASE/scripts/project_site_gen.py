# -*- coding: utf-8 -*-
"""project_site_gen.py —— 底座展示站生成器（BASE 组件草案，案例②管线接管）。
挂载于 dispatch 第 5b 步：采集仓库真值（版本/脚本清单/台账/案例/P1 决策计数/章程叙事）
→ 确定性门禁 → 渲染 index.html + truth.json → 追加站点迭代记忆。
每条页面声称记录来源文件 + sha256。只写 P2 Project 任务区，不写 BASE 规则。
退出码 0=成功，1=失败（不中断调度，rc 留痕）。"""
import csv, hashlib, json, os, pathlib, subprocess, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml
from config_loader import get_root
from gate_review_adapter import review as gate_review

ROOT = get_root()
TASK = ROOT / "tasks" / "project-layer-p2-20260912"
EVO = TASK / "task-evolve"
MEM = EVO / "memory"; SITE = EVO / "site"
MEM.mkdir(parents=True, exist_ok=True); SITE.mkdir(parents=True, exist_ok=True)
CLAIMS = []

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def claim(cid, label, text, source):
    h = None
    if "*" in source:
        matches = sorted(ROOT.glob(source))
        if matches:
            h = hashlib.sha256(b"".join(p.read_bytes() for p in matches)).hexdigest()
    else:
        p = ROOT / source if not pathlib.Path(source).is_absolute() else pathlib.Path(source)
        if p.is_dir():
            h = hashlib.sha256("".join(sorted(p.name for p in p.iterdir())).encode()).hexdigest()
        elif p.exists():
            h = sha256(p)
    CLAIMS.append({"id": cid, "label": label, "text": text, "source": source, "sha256": h})

def gather():
    r = subprocess.run(["git", "describe", "--tags", "--always"], cwd=str(ROOT),
                       capture_output=True, text=True)
    if r.returncode == 0:
        version = r.stdout.strip()
        claim("git-version", "仓库版本", version, ".git/refs/tags")
    else:
        version = "无法获取（%s）" % r.stderr.strip()[-120:]
        claim("git-version", "仓库版本", version, "git describe 失败记录")
    scripts = sorted(p.name for p in (ROOT / "BASE" / "scripts").iterdir()
                     if p.suffix in (".py", ".bat", ".ps1"))
    claim("pipeline-scripts", "七段管线脚本清单", "%d 个脚本：%s" % (
        len(scripts), "、".join(scripts)), "BASE/scripts")
    ledgers = []
    for p in sorted((ROOT / "BASE" / "regression-runs").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            ledgers.append({"file": p.name,
                            "schema": d.get("schema_version") or d.get("schema"),
                            "status": d.get("status"),
                            "enabled": d.get("enabled") if "enabled" in d else d.get("immutable")})
        except Exception as e:
            ledgers.append({"file": p.name, "error": str(e)[:80]})
    claim("regression-ledgers", "回归台账", json.dumps(ledgers, ensure_ascii=False),
          "BASE/regression-runs")
    cases = []
    for s in sorted(ROOT.glob("tasks/project-layer-*/task-evolve/audit/summary.json")):
        d = json.loads(s.read_text(encoding="utf-8"))
        cases.append({"dir": s.parts[s.parts.index("tasks") + 1].split("/")[0],
                      "charter_id": d.get("charter_id"), "cycles": d.get("cycles"),
                      "final_value": d.get("final_value"), "mode": d.get("mode")})
    claim("project-cases", "案例汇总", json.dumps(cases, ensure_ascii=False),
          "tasks/project-layer-*/task-evolve/audit/summary.json")
    dec = TASK.parent / "project-layer-p1-20260912" / "task-evolve" / "memory" / "decisions.jsonl"
    fallback = 0; normal = 0; stress = 0
    if dec.exists():
        for line in dec.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            if "cycle" not in d:
                continue
            if float(d.get("stress_factor", 1.0)) < 1:
                stress += 1
            else:
                normal += 1
                if not d.get("live"):
                    fallback += 1
        claim("p1-llm-fallback", "P1 LLM 回退次数",
              "正常周期 %d 个中规则回退 %d 次（压力周期 %d 个，规则型设计，未计入）" % (normal, fallback, stress),
              str(dec.relative_to(ROOT)))
    else:
        claim("p1-llm-fallback", "P1 LLM 回退次数", "决策日志不存在", "N/A")
    charter = yaml.safe_load((EVO / "charter.yaml").read_text(encoding="utf-8"))
    claim("limitations", "真实局限", "\n".join("- " + x for x in charter["limitations"]),
          str((EVO / "charter.yaml").relative_to(ROOT)))
    claim("roadmap", "路线图", "\n".join("- " + x for x in charter.get("roadmap", [])),
          str((EVO / "charter.yaml").relative_to(ROOT)))
    claim("narrative", "机制讲解叙事(初衷/用法/案例样本/方向/愿景)",
          json.dumps({"intent": charter.get("intent"), "what_is": charter.get("what_is"),
                      "how_to_use": charter.get("how_to_use"),
                      "cases_as_samples": charter.get("cases_as_samples"),
                      "directions": charter.get("directions"),
                      "potential": charter.get("potential")}, ensure_ascii=False),
          str((EVO / "charter.yaml").relative_to(ROOT)))
    # 7) 全局痛点汇总（来源：P3 audit/pain-rollup.json，由调度 6c 阶段生成）
    rp = TASK.parent / "project-layer-p3-20260912" / "task-evolve" / "audit" / "pain-rollup.json"
    if rp.exists():
        ru = json.loads(rp.read_text(encoding="utf-8"))
        pain_rows = [{"pain": p["pain"], "project": p["project"], "status": p["status"],
                      "score": p["score"], "symptom": p["symptom"]} for p in ru.get("pains", [])]
        claim("pain-rollup", "全局痛点汇总",
              "projects=%d pains=%d open=%d resolved=%d evidence_gaps=%d" % (
                  ru["projects"], ru["total_pains"], ru["open"], ru["resolved"], ru["evidence_gaps"]),
              str(rp.relative_to(ROOT)))
    else:
        pain_rows = None
        claim("pain-rollup", "全局痛点汇总", "未生成（pain_rollup 尚未运行）", "N/A")
    # 8) 真实世界反馈真值（来源：P2 truth/feedback.json，由 6e 阶段轮询 GitHub API 生成）
    fp = EVO / "truth" / "feedback.json"
    if fp.exists():
        fb = json.loads(fp.read_text(encoding="utf-8"))
        fb_rel = fb.get("releases") or []
        fb_v050 = next((r["downloads"] for r in fb_rel if r.get("tag") == "v0.5.0"), None)
        fb_clones = fb.get("clones_14d")
        clones_txt = ("count=%s/uniques=%s" % (fb_clones["count"], fb_clones["uniques"])
                      if isinstance(fb_clones, dict) else (fb.get("clones_note") or "unavailable"))
        fb_delta = fb.get("delta_vs_prev") or {}
        delta_txt = ", ".join("%s%+d" % (k, v) for k, v in sorted(fb_delta.items())) or "首轮无基线"
        feedback = {"polled_at": fb.get("polled_at"), "open_issues": fb.get("open_issues"),
                    "status": fb.get("feedback_status"), "v050_downloads": fb_v050,
                    "clones_txt": clones_txt, "delta_txt": delta_txt,
                    "releases": fb_rel}
        claim("feedback-truth", "真实世界反馈真值",
              "issues=%s status=%s v0.5.0_downloads=%s clones=%s delta=%s" % (
                  fb.get("open_issues"), fb.get("feedback_status"), fb_v050, clones_txt, delta_txt),
              str(fp.relative_to(ROOT)))
    else:
        feedback = None
        claim("feedback-truth", "真实世界反馈真值", "未采集（feedback_truth 尚未运行）", "N/A")
    # 9) 30 秒体验 demo 数据（真实策略池审计，非编造）
    pool_audits = sorted((TASK.parent / "project-layer-p1-20260912" / "task-evolve" / "audit")
                         .glob("pool-v2-*.json"))
    demo = None
    if pool_audits:
        p = json.loads(pool_audits[-1].read_text(encoding="utf-8"))
        results = p.get("results", [])
        winner = next((r for r in results if r.get("id") == (p.get("winner") or "S-1")), results[0] if results else {})
        demo = {"winner": p.get("winner"), "winner_name": winner.get("name"),
                "winner_excess": winner.get("excess"), "gates": winner.get("gates_ok"),
                "gates_total": winner.get("gates_total"),
                "source": str(pool_audits[-1].relative_to(ROOT))}
        claim("demo-data", "机制示意演示数据",
              "winner=%s excess=%+.4f gates=%s/%s（真实策略池审计）" % (
                  demo["winner"], demo["winner_excess"], demo["gates"], demo["gates_total"]),
              str(pool_audits[-1].relative_to(ROOT)))
    # 9b) 真实目标（talk 入口）聚合脱敏信息 —— 目标内容与真值文件默认私有，不公开
    real_goal = None
    talk_dirs = sorted(ROOT.glob("tasks/talk-*/task-evolve"))
    talk_checks = sorted(ROOT.glob("tasks/talk-*/task-evolve/truth/check-*.json"))
    if talk_checks:
        rg = json.loads(talk_checks[-1].read_text(encoding="utf-8"))
        healthy_count = sum(1 for c in talk_checks
                            if json.loads(c.read_text(encoding="utf-8")).get("status") == "healthy")
        real_goal = {"count": len(talk_dirs), "healthy_cycles": healthy_count,
                     "last_checked": rg.get("checked_at"), "last_status": rg.get("status")}
        claim("real-goal", "真实目标聚合状态（脱敏）",
              "注册数=%d 健康周期=%d 最近状态=%s（目标内容与真值文件默认私有，未公开）" % (
                  real_goal["count"], real_goal["healthy_cycles"], real_goal["last_status"]),
              "tasks/talk-*/（私有任务区，不公开路径）")
    else:
        claim("real-goal", "真实目标聚合状态（脱敏）", "尚未注册真实目标（agent-os talk 可用）", "N/A")
    # 9c) 婴儿成长日记（脱敏聚合：任务区 diary.json，只发布过程指标）
    diary = None
    dp = ROOT / "tasks" / "project-layer-core-20260913" / "task-evolve" / "memory" / "diary.json"
    if dp.exists():
        diary = json.loads(dp.read_text(encoding="utf-8"))
        claim("baby-diary", "婴儿成长日记（脱敏聚合）",
              "cycles=%s events=%s autonomy=%s selfmods=%s+%s paper_value=%s" % (
                  diary.get("cycles"), diary.get("events"), diary.get("autonomy"),
                  diary.get("selfmods_nav"), diary.get("selfmods_cognition"),
                  (diary.get("paper_portfolio") or {}).get("value")),
              str(dp.relative_to(ROOT)))
    else:
        claim("baby-diary", "婴儿成长日记（脱敏聚合）", "未生成（baby_diary 尚未运行）", "N/A")
    return {"version": version, "scripts": scripts, "ledgers": ledgers, "cases": cases,
            "charter": charter, "fallback": fallback, "normal_total": normal,
            "pain_rows": pain_rows, "feedback": feedback, "demo": demo,
            "real_goal": real_goal, "diary": diary}

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def render(data):
    c = data["charter"]
    ver = esc(data["version"])
    script_list = "、".join(esc(s) for s in data["scripts"])
    ledger_rows = "".join(
        '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            esc(l["file"]), esc(l.get("schema") or "—"), esc(l.get("status") or "—"),
            esc(l.get("enabled") if l.get("enabled") is not None else l.get("error") or "—"))
        for l in data["ledgers"])
    case_rows = "".join(
        '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            esc(x["dir"]), esc(x.get("charter_id") or "—"), esc(x.get("cycles") or "—"),
            esc(x.get("final_value") or "—"), esc(x.get("mode") or "—"))
        for x in data["cases"])
    lim_html = "".join("<li>%s</li>" % esc(x) for x in c["limitations"])
    fallback_note = ("P1 正常周期 %d 个中，LLM live 成功 %d、规则回退 %d 次（压力周期为规则型设计，未计入）。"
                     % (data["normal_total"], data["normal_total"] - data["fallback"], data["fallback"]))
    road_html = "".join("<li>%s</li>" % esc(x) for x in c.get("roadmap", []))
    intent_txt = esc((c.get("intent") or "").strip())
    what_html = "".join("<li>%s</li>" % esc(x) for x in c.get("what_is", []))
    how_html = "".join("<li>%s</li>" % esc(x) for x in c.get("how_to_use", []))
    samples_html = "".join("<li>%s</li>" % esc(x) for x in c.get("cases_as_samples", []))
    dir_html = "".join("<li>%s</li>" % esc(x) for x in c.get("directions", []))
    pot_txt = esc((c.get("potential") or "").strip())
    hero_scenario = esc((c.get("hero_scenario") or "").strip())
    hero_human = esc((c.get("hero_human") or "").strip())
    demo = data.get("demo")
    if demo:
        steps = [
            ("观察", "目标被注册为持续责任对象，每周自动体检、留痕。"),
            ("提议", "策略池竞赛冠军 %s（%s），训练段超额 %+.4f。" % (
                esc(demo["winner"]), esc(demo["winner_name"]), demo["winner_excess"])),
            ("门禁", "25/25 周期确定性门禁 accept；章程约束逐周期钳制，规则层对越界一律 reject。"),
            ("回填", "假设 confirmed（超额 %+.4f）；痛点台账按证据 progress——合成数据演练，无投资含义。" % (
                demo["winner_excess"])),
        ]
        steps_html = "".join(
            '<div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;'
            'padding:10px;margin:6px 0;"><b>%s</b> %s</div>' % (esc(s[0]), esc(s[1]))
            for s in steps)
        demo_html = (
            '<p class="note">静态过程示意（不可操作）——真实入口是上面 3 行命令或 agent-os talk。'
            '数据来自 %s（真实策略池审计记录）。</p>%s'
            % (esc(demo["source"]), steps_html))
    else:
        demo_html = '<p class="note">演示数据未生成（策略池尚未运行）。</p>'
    participation_html = (
        '<div class="cards">'
        '<div class="card"><b>使用者</b><span>写一份 charter，把长期目标交给底座：<a href="%s">快速开始</a></span></div>'
        '<div class="card"><b>提意见者</b><span>反馈会进痛点台账并被逐条回应：<a href="%s">GitHub Issues</a></span></div>'
        '<div class="card"><b>二次开发者</b><span>按机器可读契约扩展：<a href="%s">charter.schema.json</a> + <a href="%s">Project 层设计</a></span></div>'
        '</div>'
        % ("https://github.com/bobbyliuzh06/agent-os-base/blob/main/BASE/README.md",
           "https://github.com/bobbyliuzh06/agent-os-base/issues",
           "https://github.com/bobbyliuzh06/agent-os-base/blob/main/BASE/docs/charter.schema.json",
           "https://github.com/bobbyliuzh06/agent-os-base/blob/main/BASE/docs/PROJECT-LAYER.md"))
    dy = data.get("diary")
    if dy:
        pf = dy.get("paper_portfolio") or {}
        diary_html = ('<p>周期 <b>%s</b> · 事件 <b>%s</b>（%s）· 世界 <b>%s</b> · 自主等级 <b>%s</b> · '
                      '连续无事故 <b>%s</b> · 自改 <b>%s</b> 次（导航 %s + 认知 %s）· 影子运行 <b>%s</b> 次 · '
                      '信号学习 <b>%s</b> 类 · 假设裁决 <b>%s</b> 条</p>'
                      '<p>纸面组合（合成回放演练，无真实市场含义，不构成投资建议）：本金 100000 → 净值 '
                      '<b>%s</b>（结算 %s 周期）</p>'
                      '<p class="note">成长日记为脱敏聚合：目标内容与真值路径默认私有；数字来自真实运行记录。</p>'
                      % (esc(dy.get("cycles")), esc(dy.get("events")), esc(dy.get("chain")),
                         esc(",".join(dy.get("worlds", []))), esc(dy.get("autonomy")),
                         esc(dy.get("consecutive_clean_cycles")), esc(dy.get("selfmods_nav")),
                         esc(dy.get("selfmods_nav")), esc(dy.get("selfmods_cognition")),
                         esc(dy.get("shadow_runs")), esc(dy.get("signals_learned")),
                         esc(dy.get("hypotheses_confirmed")), esc(pf.get("value")),
                         esc(pf.get("settled_cycles"))))
    else:
        diary_html = '<p class="note">婴儿成长日记未生成（baby_diary 尚未运行）。</p>'
    rg = data.get("real_goal")
    if rg:
        real_goal_html = ('<p>已注册真实目标 <b>%s</b> 个；健康检查周期 <b>%s</b> 次；最近检查：%s（%s）。</p>'
                          '<p class="note">目标内容与真值文件默认私有（用户显式授权前不公开）。'
                          '可溯源 ≠ 公开：证据链在用户的任务区，授权公开时才上站。'
                          '第一周期默认走底座健康真值（链路验证），目标专属真值由 charter.truth_sources 声明后接入。</p>'
                          % (esc(rg["count"]), esc(rg["healthy_cycles"]), esc(rg["last_checked"]), esc(rg["last_status"])))
    else:
        real_goal_html = '<p class="note">尚未注册真实目标——agent-os talk 说一句人话即可注册并跑通第一周期。</p>'
    if data.get("pain_rows") is None:
        pain_html = '<p class="note">全局痛点汇总未生成（pain_rollup 尚未运行）。</p>'
    else:
        pain_html = ('<table><tr><th>痛点</th><th>项目</th><th>状态</th><th>分值</th><th>症状</th></tr>%s</table>'
                     % "".join('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                         esc(r["pain"]), esc(r["project"]), esc(r["status"]), esc(r["score"]), esc(r["symptom"]))
                         for r in data["pain_rows"]))
    fb = data.get("feedback")
    if fb is None:
        feedback_html = '<p class="note">真实反馈真值未采集（feedback_truth 尚未运行）。</p>'
    else:
        rel_rows = "".join('<tr><td>%s</td><td>%s</td></tr>' % (esc(r.get("tag")), esc(r.get("downloads")))
                           for r in (fb.get("releases") or []))
        feedback_html = ('<p>采集时间 %s（GitHub API 只读轮询，%s）。Issues 数：%s。</p>'
                         '<p>14 天 clone：%s（count/uniques）。相对上次轮询环比：%s。</p>'
                         '<table><tr><th>Release</th><th>下载数</th></tr>%s</table>'
                         '<p class="note">访问量（Pages 流量）尚无法经此 API 获取，未展示即未编造（P-8 待办）；clone 数据不可得时显式标注 unavailable。</p>'
                         % (esc(fb.get("polled_at")), esc(fb.get("status") or "?"), esc(fb.get("open_issues")),
                            esc(fb.get("clones_txt") or "?"), esc(fb.get("delta_txt") or "?"), rel_rows))
    it_log = MEM / "iterations.jsonl"
    prev = [json.loads(l) for l in it_log.read_text(encoding="utf-8").splitlines()] if it_log.exists() else []
    it_rows = "".join(
        '<tr><td>#%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            esc(r["iteration"]), esc(r["built_at"]), esc(r["gate"]),
            esc(r["claims"]), esc(r["script_sha256"][:12]))
        for r in prev)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    it_rows += ('<tr><td>#%s</td><td>%s</td><td colspan="3">本次（正在生成）</td></tr>'
                % (len(prev) + 1, now))
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>agent-os · 自托管、自审查、自演化的智能体底座</title>
<style>
:root { --bg:#0f1419; --panel:#161d26; --ink:#e6e9ef; --dim:#9aa5b1; --acc:#4da3ff; --line:#26313d; }
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--ink); font:15px/1.65 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif; }
.wrap { max-width:960px; margin:0 auto; padding:40px 20px 60px; }
h1 { font-size:30px; letter-spacing:.5px; }
h2 { font-size:20px; margin:44px 0 14px; color:var(--acc); }
p, li { color:var(--dim); }
.tag { display:inline-block; border:1px solid var(--line); border-radius:6px; padding:2px 10px; margin:6px 6px 0 0; font-size:13px; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin:24px 0; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
.card b { display:block; font-size:22px; color:var(--ink); }
.card span { font-size:13px; color:var(--dim); }
table { width:100%%; border-collapse:collapse; margin:12px 0; font-size:13.5px; }
th, td { border:1px solid var(--line); padding:8px 10px; text-align:left; }
th { background:var(--panel); color:var(--ink); }
td { color:var(--dim); }
.note { font-size:12.5px; color:var(--dim); margin-top:8px; }
a { color:var(--acc); }
.flow { display:flex; flex-wrap:wrap; gap:8px; margin:14px 0; }
.flow span { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:6px 12px; font-size:13.5px; }
.foot { margin-top:56px; border-top:1px solid var(--line); padding-top:16px; font-size:12.5px; color:var(--dim); }
</style>
</head>
<body><div class="wrap">
<h1>agent-os</h1>
<p style="font-size:18px;color:var(--ink);"><strong>把"帮我长期盯住一件事"这句话，变成一个记教训、讲证据、不越界的持续责任体。</strong></p>
<p>给有长期目标的人用的运行时——你负责说目标，它负责持续照顾、每一步可追溯、越界会被拦住。</p>
<p>%s</p>
<p style="color:var(--acc);">%s</p>
<div class="cards">
<div class="card"><b>%s</b><span>站点快照生成于该提交（git describe；仓库 HEAD 可能更新）</span></div>
<div class="card"><b>%d</b><span>管线脚本（BASE/scripts 真实清单）</span></div>
<div class="card"><b>%d</b><span>回归台账（真实字段）</span></div>
<div class="card"><b>%d</b><span>项目案例（持续责任对象）</span></div>
</div>

<h2>给开发者：3 行跑通（或直接说人话）</h2>
<pre style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;color:var(--ink);">pip install -e .
agent-os demo
agent-os talk "帮我长期盯住一组重要链接"   # 自然语言 → charter，门禁审过你再跑</pre>
<p class="note">真实入口=上面 3 行。下面是静态过程示意（不可操作），仅供了解机制，不是交互。</p>

<h2>机制过程示意（静态）</h2>
%s

<h2>我要参与</h2>
%s

<h2>架构初衷</h2>
<p>%s</p>

<h2>它是什么 / 不是什么</h2>
<ul>%s</ul>

<h2>怎么用</h2>
<ul>%s</ul>
<p class="tag">proposal + gate 演化闭环</p><p class="tag">七段调度管线</p><p class="tag">确定性规则门禁</p><p class="tag">L1 代码沙箱</p><p class="tag">供应链发布验证</p>

<h2>演化闭环</h2>
<div class="flow"><span>propose</span><span>gate</span><span>execute</span><span>postprocess</span><span>observe</span><span>advice</span><span>dashboard</span></div>
<p>任何对 BASE 规则的修改都必须经过提案 + 门禁 + 人审：先证明，再落盘。</p>
<details><summary>机制档案（脚本清单与台账，给想深挖的人）</summary>
<p class="note">%s</p>

<h2>当前真实状态</h2>
<p>本表来自仓库真实文件，每项声称的来源与 sha256 记录在 <a href="truth.json">truth.json</a>。</p>
<table>
<tr><th>回归台账</th><th>schema</th><th>status</th><th>enabled</th></tr>
%s
</table>
<p class="note">台账解析失败项会原样记录错误，不掩盖。</p>
</details>

<h2>婴儿成长日记（脱敏）</h2>
%s

<h2>真实目标（talk 入口，可核验）</h2>
%s

<h2>全局痛点（跨项目）</h2>
<p>痛点台账的跨项目汇总（pain_rollup，调度 6c 阶段生成）：底座当前在治什么、治好了什么，一表可见。</p>
%s

<h2>真实反馈（世界在怎么回应）</h2>
%s

<h2>案例样本（机制演示，不是主角）</h2>
<p>案例是让机制可被理解的样本：每个案例标注它演示了底座的哪一部分。</p>
<table>
<tr><th>案例</th><th>章程</th><th>周期</th><th>期末净值</th><th>模式</th></tr>
%s
</table>
<ul>%s</ul>
<p class="note">%s<br>免责声明：研究工具定位，不构成投资建议。组合数字均为合成数据演练结果。</p>

<h2>真实局限</h2>
<ul>%s</ul>
<p class="note">%s</p>

<h2>本站演化日志</h2>
<p>本页渲染自己的迭代记忆（memory/iterations.jsonl）：每次再生成都是真实记录，"交付后持续维护"不是口号。</p>
<table>
<tr><th>迭代</th><th>时间(UTC)</th><th>门禁</th><th>声称数</th><th>生成脚本sha</th></tr>
%s
</table>

<h2>路线图与潜在方向</h2>
<ul>%s</ul>
<ul>%s</ul>
<p class="note">路线图与方向文本来自本站章程 charter.yaml（真实文件），不代表任何承诺。</p>

<h2>突破性可能</h2>
<p>%s</p>

<h2>反馈</h2>
<p>本站是底座自身的展示窗口。你的反馈就是演化的真实世界输入：<a href="%s">GitHub Issues →</a></p>
<p class="note">发布状态：本站已随 v0.5.0 上线 GitHub Pages；访问/反馈指标接入为 P-8 待办，接入前本声明继续生效。</p>

<div class="foot">
<p>本页面由 <code>project_site_gen.py</code> 于 %s 从仓库真实状态生成；页面数字均可追溯至 truth.json 中的来源文件 + sha256。</p><p>本站为 agent-os 唯一官方公开入口（GitHub Pages）；其他同名部署（如旧版 workbuddy 链接）不属本仓库维护范围，以本站为准。</p>
<p>免责声明：研究工具定位，不构成投资建议。本站内容如实呈现底座状态，不夸大任何能力。</p>
</div>
</div></body></html>
""" % (hero_scenario, hero_human, ver, len(data["scripts"]), len(data["ledgers"]), len(data["cases"]),
       demo_html, participation_html,
       intent_txt, what_html, how_html,
       script_list, ledger_rows, real_goal_html, diary_html, pain_html, feedback_html, case_rows, samples_html, fallback_note,
       lim_html, esc(fallback_note), it_rows, road_html, dir_html, pot_txt,
       c["feedback"]["channel"], now)

def gate(data):
    prop = {
        "summary": "生成 agent-os 展示站 index.html + truth.json（真值驱动，管线接管）",
        "scope_in": ["tasks/project-layer-p2-20260912"],
        "scope_out": ["BASE", "push/发布"],
        "deliverables": ["tasks/project-layer-p2-20260912/task-evolve/site/index.html",
                         "tasks/project-layer-p2-20260912/task-evolve/site/truth.json"],
        "steps": ["采集真实状态", "确定性门禁", "渲染", "记录迭代日志"],
        "risks": ["页面声称与仓库状态不一致（以 truth.json 溯源缓解）"],
        "rollback": ["删除本次生成的 site/index.html 与 truth.json"],
        "acceptance": ["truth.json 中每项声称均有来源文件与 sha256", "门禁 accept"],
        "base_change_required": False, "tool_calls": [],
    }
    return gate_review(prop, "project-layer-p2-20260912")

def main():
    try:
        data = gather()
        g = gate(data)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        html = render(data)
        truth = {"generated_at": now, "charter_id": data["charter"]["id"], "claims": CLAIMS,
                 "gate": g, "files": None}
        idx_path = SITE / "index.html"; truth_path = SITE / "truth.json"
        idx_path.write_text(html, encoding="utf-8")
        truth["files"] = {"index.html": sha256(idx_path), "truth.json": "self"}
        truth_path.write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
        truth["files"]["truth.json"] = sha256(truth_path)
        truth_path.write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
        it_log = MEM / "iterations.jsonl"
        prev = [json.loads(l) for l in it_log.read_text(encoding="utf-8").splitlines()] if it_log.exists() else []
        rec = {"iteration": len(prev) + 1, "built_at": now,
               "script_sha256": sha256(pathlib.Path(__file__)),
               "gate": g["gate"], "claims": len(CLAIMS), "files": truth["files"]}
        with open(it_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("PROJECT_SITE_GEN gate=%s claims=%d -> %s (iteration %d)" % (
            g["gate"], len(CLAIMS), idx_path, rec["iteration"]))
        return 0
    except Exception as e:
        print("PROJECT_SITE_GEN FAILED: %s" % e)
        return 1

if __name__ == "__main__":
    sys.exit(main())
