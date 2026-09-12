#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, sys, json, shutil, subprocess, hashlib
from datetime import datetime

BASE_DIR = "D:/agent-os/BASE"
PENDING_DIR = "D:/agent-os/PENDING"
GATE_STATE_FILE = os.path.join(BASE_DIR, "scripts", "gate_state.json")

DSH_PROFILE = "headless"
DSH_PROVIDER = "deepseek-official"
DSH_MODEL = "deepseek-flash"
GATE_REASONING_KEEP = 20

def log(s):
    try:
        print(s, flush=True)
    except Exception:
        pass

def md5_of_text(t):
    return hashlib.md5(t.encode("utf-8", "replace")).hexdigest()

def _candidate_bin_paths():
    out = []
    env_js = os.environ.get("DSH_BIN_JS", "").strip()
    if env_js:
        for p in re.split(r"[;:]", env_js):
            if p.strip():
                out.append(p.strip())
    try:
        proc = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, encoding="utf-8", timeout=60)
        if proc.returncode == 0 and proc.stdout.strip():
            out.append(os.path.join(proc.stdout.strip(), "@deepseek-ai", "dsh", "lib", "bin.js"))
    except Exception:
        pass
    for name in ["dsh.cmd", "dsh.exe", "dsh"]:
        p = shutil.which(name)
        if p:
            d = os.path.dirname(p)
            out.append(os.path.join(d, "..", "lib", "bin.js"))
            out.append(os.path.join(d, "lib", "bin.js"))
            out.append(p)
    for base in [os.environ.get("APPDATA", ""), os.environ.get("LOCALAPPDATA", "")]:
        if base:
            out.append(os.path.join(base, "npm", "node_modules", "@deepseek-ai", "dsh", "lib", "bin.js"))
            out.append(os.path.join(base, "npm-cache", "_npx"))
    home = os.path.expanduser("~")
    for base in [home, os.path.join(home, ".npm"), os.path.join(home, "AppData", "Roaming", "npm"),
                os.path.join(home, "AppData", "Local", "npm-cache")]:
        if base:
            out.append(os.path.join(base, "node_modules", "@deepseek-ai", "dsh", "lib", "bin.js"))
    return out

def resolve_dsh():
    for cand in _candidate_bin_paths():
        if cand.endswith(".js") and os.path.isfile(cand):
            node = shutil.which("node")
            if node:
                return [node, cand]
        elif cand.endswith("_npx") or os.path.isdir(cand):
            if os.path.isdir(cand):
                for root, dirs, files in os.walk(cand):
                    if os.path.basename(root) == "lib" and "bin.js" in files:
                        if root.replace("\\", "/").endswith("@deepseek-ai/dsh/lib"):
                            js = os.path.join(root, "bin.js")
                            node = shutil.which("node")
                            if node and os.path.isfile(js):
                                return [node, js]
    node = shutil.which("node")
    dshcmd = shutil.which("dsh.cmd") or shutil.which("dsh")
    if node and dshcmd:
        return [node, dshcmd]
    if dshcmd:
        return [dshcmd]
    return ["dsh"]

def read_key_from_registry():
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

def load_gate_state():
    if os.path.isfile(GATE_STATE_FILE):
        try:
            with open(GATE_STATE_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return {"gated": {}}
    return {"gated": {}}

def save_gate_state(st):
    with open(GATE_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

def build_gate_prompt(review_path, review_text):
    rules = []
    for r in [os.path.join(BASE_DIR, "AGENTS.md"), os.path.join(BASE_DIR, "META", "GATE.md"),
             os.path.join(BASE_DIR, "META", "REGRESSION.md"), os.path.join(BASE_DIR, "META", "ROUTE.md"),
             os.path.join(BASE_DIR, "skills", "propose-gate", "SKILL.md"),
             os.path.join(BASE_DIR, "skills", "gate-review", "SKILL.md")]:
        if os.path.isfile(r):
            with open(r, "r", encoding="utf-8", errors="replace") as fh:
                rules.append("# 规则文件 " + os.path.relpath(r, BASE_DIR) + "\n" + fh.read())
    sys_prompt = (
        "你是 agent-os 独立 gate-review 审核员，与 propose 评审不是同一上下文。只接收 propose 产出的评审草案与规则文件，"
        "不读取 propose 的 reasoning/stderr，不继承提案作者推理。按 META/GATE.md 与 skills/gate-review/SKILL.md 做独立裁决。\n"
        "输出要求：1) 复核 propose 评审是否漏判 GATE 自动拒绝项/通用门槛/分级门槛；2) 核对评审 diff 与提案是否一致；"
        "3) 若需回归探针，列出必跑探针与 before/after 判据；4) 给出最终门控结论。\n"
        "正文最后必须输出独立块：\n## GATE_VERDICT\nGATE_STATUS: accept|reject|needs-revision\nGATE_RISK: low|medium|high\n"
        "不要把推理过程写进最终正文。\n\n" + "\n\n".join(rules)
    )
    user_prompt = "待审评审草案文件：" + review_path + "\n\n# 评审草案正文\n" + review_text
    return sys_prompt, user_prompt

def run_headless(sys_prompt, user_prompt):
    full_task = "SYSTEM_RULES_START\n" + sys_prompt + "\nSYSTEM_RULES_END\n\nUSER_TASK_START\n" + user_prompt + "\nUSER_TASK_END"
    env = dict(os.environ)
    key = env.get("DEEPSEEK_API_KEY") or read_key_from_registry()
    if key:
        env["DEEPSEEK_API_KEY"] = key
    env["DEEPSEEK_PROVIDER"] = DSH_PROVIDER
    env["DEEPSEEK_MODEL"] = DSH_MODEL
    args = resolve_dsh() + ["--profile", DSH_PROFILE, full_task]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=env, timeout=1800)
        return proc.stdout or "", proc.stderr or "", proc.returncode
    except Exception as e:
        return "", "gate headless 调用失败：" + str(e), 1

def parse_gate_verdict(text):
    status, risk = "unknown", "unknown"
    m = re.search(r"##\s*GATE_VERDICT\s*(.*)", text, re.S)
    block = m.group(1) if m else ""
    sm = re.search(r"GATE_STATUS:\s*(accept|reject|needs-revision)", block or text, re.I)
    if sm:
        status = sm.group(1).lower()
    rm = re.search(r"GATE_RISK:\s*(low|medium|high)", block or text, re.I)
    if rm:
        risk = rm.group(1).lower()
    return status, risk

def trim_gate_reasoning():
    if not os.path.isdir(PENDING_DIR):
        return
    files = [os.path.join(PENDING_DIR, p) for p in os.listdir(PENDING_DIR) if p.endswith(".gate.reasoning.txt")]
    files.sort(key=lambda x: os.path.getmtime(x))
    while len(files) > GATE_REASONING_KEEP:
        old = files.pop(0)
        try:
            os.remove(old)
        except Exception:
            pass

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    log("GATE_DSH_RESOLVE: " + " ".join(resolve_dsh()))
    os.makedirs(PENDING_DIR, exist_ok=True)
    state = load_gate_state()
    state.setdefault("gated", {})
    reviews = []
    if os.path.isdir(PENDING_DIR):
        for p in sorted(os.listdir(PENDING_DIR)):
            if p.endswith(".review.txt") and not p.endswith(".gate.review.txt"):
                reviews.append(os.path.join(PENDING_DIR, p))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    processed = 0
    for review_path in reviews:
        with open(review_path, "r", encoding="utf-8", errors="replace") as fh:
            review_text = fh.read()
        h = md5_of_text(review_text)
        if state["gated"].get(review_path) == h:
            continue  # 已门控且内容未变，跳过
        gate_out = review_path[:-len(".review.txt")] + ".gate.txt"
        gate_reason = review_path[:-len(".review.txt")] + ".gate.reasoning.txt"
        stdout_text, stderr_text, rc = "", "", 0
        sys_p, user_p = build_gate_prompt(review_path, review_text)
        stdout_text, stderr_text, rc = run_headless(sys_p, user_p)
        gstatus, grisk = parse_gate_verdict(stdout_text)
        with open(gate_reason, "w", encoding="utf-8") as f:
            f.write("# gate-review stderr/reasoning\n# review=%s rc=%s time=%s\n\n" % (review_path, rc, now))
            f.write(stderr_text if stderr_text.strip() else "(empty)")
        body = stdout_text.strip() or "(无 gate 正文)"
        with open(gate_out, "w", encoding="utf-8") as f:
            f.write("# 独立 gate-review 裁决\n# review=%s rc=%s time=%s\n" % (review_path, rc, now))
            f.write("GATE_STATUS: %s    GATE_RISK: %s\n" % (gstatus, grisk))
            f.write("---- 门控正文 ----\n\n")
            f.write(body + "\n")
        # 待办标记：不自动合并
        if gstatus == "accept":
            decision = "waiting-human-merge"
        elif gstatus == "reject":
            decision = "return-to-proposer"
        else:
            decision = "waiting-human-gate"
        pending_md = review_path[:-len(".review.txt")] + ".md"
        if os.path.isfile(pending_md):
            with open(pending_md, "a", encoding="utf-8") as f:
                f.write("\n# gate 结论 %s\n- GATE_STATUS: %s\n- GATE_RISK: %s\n- 处置: %s\n" % (now, gstatus, grisk, decision))
        state["gated"][review_path] = h
        processed += 1
        log("[门控] %s -> 裁决 %s | 推理 %s | GATE_STATUS=%s | rc=%s" % (review_path, gate_out, gate_reason, gstatus, rc))
    save_gate_state(state)
    trim_gate_reasoning()
    log("=" * 50)
    log("运行时间：%s\n扫描review数：%d\n本次门控：%d\ngate状态：%s" % (now, len(reviews), processed, GATE_STATE_FILE))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("错误：" + str(e))
        sys.exit(1)
