#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, sys, json, shutil, hashlib, subprocess
from datetime import datetime

BASE_DIR = "D:/agent-os/BASE"
PROJECTS_DIR = "D:/agent-os/PROJECTS"
PENDING_DIR = "D:/agent-os/PENDING"
STATE_FILE = os.path.join(BASE_DIR, "scripts", "state.json")

DSH_PROFILE = "headless"
DSH_PROVIDER = "deepseek-official"
DSH_MODEL = "deepseek-flash"
REVIEW_ENABLED = True
REASONING_KEEP = 20

def md5_of_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def _candidate_bin_paths():
    out = []
    env_js = os.environ.get("DSH_BIN_JS", "").strip()
    if env_js:
        for p in re.split(r"[;:]", env_js):
            if p.strip():
                out.append(p.strip())
    # npm global root
    try:
        proc = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, encoding="utf-8", timeout=60)
        if proc.returncode == 0 and proc.stdout.strip():
            out.append(os.path.join(proc.stdout.strip(), "@deepseek-ai", "dsh", "lib", "bin.js"))
    except Exception:
        pass
    # which dsh -> dsh.cmd 同级 ../lib/bin.js
    for name in ["dsh.cmd", "dsh.exe", "dsh"]:
        p = shutil.which(name)
        if p:
            d = os.path.dirname(p)
            out.append(os.path.join(d, "..", "lib", "bin.js"))
            out.append(os.path.join(d, "lib", "bin.js"))
            out.append(p)
    # 常见 npm 全局与 npx 缓存
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    for base in [appdata, localappdata]:
        if not base:
            continue
        out.append(os.path.join(base, "npm", "node_modules", "@deepseek-ai", "dsh", "lib", "bin.js"))
        out.append(os.path.join(base, "npm-cache", "_npx"))
    home = os.path.expanduser("~")
    for base in [home, os.path.join(home, ".npm"), os.path.join(home, "AppData", "Roaming", "npm"),
                os.path.join(home, "AppData", "Local", "npm-cache")]:
        if base:
            out.append(os.path.join(base, "node_modules", "@deepseek-ai", "dsh", "lib", "bin.js"))
    return out

def resolve_dsh():
    # 1) 显式 DSH_BIN_JS 或自动候选 js
    for cand in _candidate_bin_paths():
        if cand.endswith(".js"):
            if os.path.isfile(cand):
                node = shutil.which("node")
                if node:
                    return [node, cand]
        elif cand.endswith("_npx") or os.path.isdir(cand):
            # npx 缓存：递归找 @deepseek-ai/dsh/lib/bin.js
            if os.path.isdir(cand):
                for root, dirs, files in os.walk(cand):
                    if os.path.basename(root) == "lib" and "bin.js" in files:
                        if root.replace("\\", "/").endswith("@deepseek-ai/dsh/lib"):
                            js = os.path.join(root, "bin.js")
                            node = shutil.which("node")
                            if node and os.path.isfile(js):
                                return [node, js]
    # 2) 回退：node dsh 命令
    node = shutil.which("node")
    dshcmd = shutil.which("dsh.cmd") or shutil.which("dsh")
    if node and dshcmd:
        return [node, dshcmd]
    if dshcmd:
        return [dshcmd]
    return ["dsh"]

def find_proposals():
    found = []
    if not os.path.isdir(PROJECTS_DIR):
        return found
    for name in sorted(os.listdir(PROJECTS_DIR)):
        proj = os.path.join(PROJECTS_DIR, name)
        if not os.path.isdir(proj):
            continue
        for cand in [os.path.join(proj, "WORKSPACE", "PROPOSAL.md"), os.path.join(proj, "PROPOSAL.md")]:
            if os.path.isfile(cand):
                found.append((name, cand, md5_of_file(cand)))
                break
    return found

def load_state():
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return {"known": {}}
    return {"known": {}}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def prune_ghost_state(state):
    known = state.get("known", {})
    removed = []
    for k in list(known.keys()):
        if not os.path.isfile(k):
            removed.append(k)
            del known[k]
    if removed:
        state["known"] = known
        save_state(state)
    return removed

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
                continue
    except Exception:
        pass
    return ""

def build_prompt(proj_name, prop_path):
    rules = []
    for r in [os.path.join(BASE_DIR, "AGENTS.md"), os.path.join(BASE_DIR, "META", "GATE.md"),
             os.path.join(BASE_DIR, "META", "REGRESSION.md"), os.path.join(BASE_DIR, "META", "ROUTE.md"),
             os.path.join(BASE_DIR, "skills", "propose-gate", "SKILL.md"),
             os.path.join(BASE_DIR, "skills", "gate-review", "SKILL.md")]:
        if os.path.isfile(r):
            with open(r, "r", encoding="utf-8", errors="replace") as fh:
                rules.append("# 规则文件 " + os.path.relpath(r, BASE_DIR) + "\n" + fh.read())
    with open(prop_path, "r", encoding="utf-8", errors="replace") as fh:
        prop_text = fh.read()
    sys_prompt = ("你是 agent-os propose-gate 评审员。只基于下面规则与提案产出对 BASE 的修改建议，不执行合并、不执行 git 写操作。\n"
                  "输出要求：1) 摘要；2) 拟修改/新增文件清单（相对 D:/agent-os/BASE）；3) 每个文件给 unified diff 或完整新内容；"
                  "4) 自评估风险等级低/中/高与触发回归探针；5) 若不满足 META/GATE.md 门槛，说明驳回理由。\n"
                  "正文最后必须输出独立块：\n## VERDICT\nSTATUS: accept|reject|needs-revision\nRISK: low|medium|high\n"
                  "不要把推理过程写进最终正文。\n\n" + "\n\n".join(rules))
    user_prompt = "项目：" + proj_name + "\n提案文件：" + prop_path + "\n\n# 提案内容\n" + prop_text
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
        return "", "headless 调用失败：" + str(e), 1

def parse_verdict(stdout_text):
    status, risk = "unknown", "unknown"
    m = re.search(r"##\s*VERDICT\s*(.*)", stdout_text, re.S)
    block = m.group(1) if m else ""
    sm = re.search(r"STATUS:\s*(accept|reject|needs-revision)", block or stdout_text, re.I)
    if sm:
        status = sm.group(1).lower()
    rm = re.search(r"RISK:\s*(low|medium|high)", block or stdout_text, re.I)
    if rm:
        risk = rm.group(1).lower()
    return status, risk

def trim_reasoning_files():
    files = [os.path.join(PENDING_DIR, p) for p in os.listdir(PENDING_DIR)] if os.path.isdir(PENDING_DIR) else []
    files = [p for p in files if p.endswith(".reasoning.txt")]
    files.sort(key=lambda x: os.path.getmtime(x))
    while len(files) > REASONING_KEEP:
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
    os.makedirs(PENDING_DIR, exist_ok=True)
    print("DSH_RESOLVE:", " ".join(resolve_dsh()))
    state = load_state()
    ghosts = prune_ghost_state(state)
    if ghosts:
        print("清理幽灵 state 条目：" + str(ghosts))
    first_run = (len(state.get("known", {})) == 0)
    proposals = find_proposals()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_items, historical = [], 0
    for name, path, h in proposals:
        if state.get("known", {}).get(path) == h:
            continue
        if first_run:
            state.setdefault("known", {})[path] = h
            historical += 1
        else:
            new_items.append((name, path, h))
            state.setdefault("known", {})[path] = h
    save_state(state)
    for name, path, h in new_items:
        date_str = now[:10]
        slug = re.sub(r"[^0-9A-Za-z_-]", "-", name)
        pending_md = os.path.join(PENDING_DIR, f"{slug}-{date_str}.md")
        review_txt = os.path.join(PENDING_DIR, f"{slug}-{date_str}.review.txt")
        reasoning_txt = os.path.join(PENDING_DIR, f"{slug}-{date_str}.reasoning.txt")
        with open(pending_md, "w", encoding="utf-8") as f:
            f.write(f"# 待人工复核提案\n\n- 项目：{name}\n- 提案：{path}\n- 哈希：{h}\n- 时间：{now}\n- 状态：waiting-gate\n")
        stdout_text, stderr_text, rc = "", "", 0
        if REVIEW_ENABLED:
            sys_p, user_p = build_prompt(name, path)
            stdout_text, stderr_text, rc = run_headless(sys_p, user_p)
            status, risk = parse_verdict(stdout_text)
            with open(reasoning_txt, "w", encoding="utf-8") as f:
                f.write(f"# dsh headless stderr/reasoning\n# project={name} rc={rc} time={now}\n\n")
                f.write(stderr_text if stderr_text.strip() else "(empty)")
            body = stdout_text.strip() or "(无 stdout 评审正文)"
            with open(review_txt, "w", encoding="utf-8") as f:
                f.write(f"# dsh headless 评审草案\n# project={name} proposal={path} rc={rc} time={now}\n")
                f.write(f"STATUS: {status}    RISK: {risk}\n")
                f.write("---- 评审正文 ----\n\n")
                f.write(body + "\n")
        else:
            with open(review_txt, "w", encoding="utf-8") as f:
                f.write(f"# 未启用自动评审 {name} {now}\n")
        print(f"[新提案] {name} -> 待办 {pending_md}")
        print(f"[评审]   {name} -> 正文 {review_txt} | 推理 {reasoning_txt} | rc={rc}")
    trim_reasoning_files()
    print("=" * 50)
    print(f"运行时间：{now}\n扫描项目数：{len(proposals)}\n首次登记历史：{historical}\n新提案：{len(new_items)}")
    print(f"状态文件：{STATE_FILE}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("错误：" + str(e))
        sys.exit(1)
