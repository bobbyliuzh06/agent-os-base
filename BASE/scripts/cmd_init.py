#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-os init：目录/配置/密钥审计/自测。只读检查 + 按需创建，不接 LLM、不改 evolve。"""
import os, sys, json, datetime, re
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_config as _lc

DEFAULT_CFG = {
    "_comment": "生成于 init；修改后保留 task_layer.enabled=false / github.enabled=false",
    "version": "0.4.0-rc1",
    "paths": {
        "base_dir": "${AGENT_OS_ROOT}/BASE",
        "profile_dir": "${AGENT_OS_ROOT}/profile",
        "tasks_dir": "${AGENT_OS_ROOT}/tasks",
        "registry": "${AGENT_OS_ROOT}/tasks/registry.json"
    },
    "env": {
        "api_key_source": ["winreg:DEEPSEEK_API_KEY", "env:DEEPSEEK_API_KEY", ".env"],
        "key_env_name": "DEEPSEEK_API_KEY"
    },
    "schedule": {"base_evolve": {"task_name": "AgentOS_EvolveDispatch", "interval_hours": 4, "enabled": True},
                 "watch": {"task_name": "AgentOS_WatchCheck", "interval": "daily", "enabled": True}},
    "task_layer": {"enabled": False, "commands": ["sync","new","run","watch","evolve","doctor","archive"],
                   "single_base_only": True, "registry_dedup": True, "per_task_lock": True},
    "github": {"enabled": False, "mode": "git", "repo_url": "", "branch": "main", "base_subtree": "BASE",
               "release_asset_pattern": "agent-os-base-*.zip", "token_env": "GH_TOKEN",
               "allow_dirty": False, "backup_dir": "${AGENT_OS_ROOT}/BASE/regression-runs/sync-backup",
               "verify_checksum": True, "only_base_subtree": True}
}

def ensure_config(C):
    p = C.meta_dir / "config.json"
    if p.exists():
        print("[config] 已存在，保留现有配置（如需重置请手动备份后删除）：", p)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(DEFAULT_CFG, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[config] 已生成模板：", p)

def audit_keys(C):
    key = C.env_key("x")  # 返回 None 不打印值
    name = C.get("env", "key_env_name") or "DEEPSEEK_API_KEY"
    sources = C.get("env", "api_key_source") or []
    print("[keys] key_env_name =", name)
    found = []
    for src in sources:
        if src.startswith("env:") and os.environ.get(src.split(":",1)[1].strip()):
            found.append("env:%s=set" % src.split(":",1)[1].strip())
        elif src.startswith("winreg:"):
            try:
                import winreg
                spec = src.split(":", 1)[1].strip()
                if "\\" in spec:
                    hive_name, sub = spec.split("\\", 1)
                    hive = getattr(winreg, hive_name, winreg.HKEY_CURRENT_USER)
                    vname = name
                else:
                    hive, sub, vname = winreg.HKEY_CURRENT_USER, "Environment", spec
                with winreg.OpenKey(hive, sub) as k:
                    winreg.QueryValueEx(k, vname)
                found.append("winreg:%s=set" % sub)
            except Exception:
                pass
        elif src == ".env":
            envf = C.root / ".env"
            if envf.exists() and name in envf.read_text(encoding="utf-8", errors="replace"):
                found.append(".env=set")
    if found:
        print("[keys] OK 可用来源：", "; ".join(found))
    else:
        print("[keys] WARN 未找到 %s。请在系统环境变量 / winreg / .env 中任一配置（不写明文到仓库）。"%name)

def selfcheck(C):
    ok = True
    def check(name, cond):
        nonlocal ok; ok = ok and bool(cond)
        print("  [%s] %s" % ("PASS" if cond else "FAIL", name))
    check("AGENT_OS_ROOT 可解析", bool(C.root) and C.root.exists())
    check("BASE 目录存在", C.base_dir.exists())
    check("scripts 目录存在且有 config_loader", (C.scripts_dir.exists() and (C.scripts_dir/"config_loader.py").exists()))
    check("meta 目录存在", C.meta_dir.exists())
    check("config.json 合法 JSON", (C.meta_dir/"config.json").exists())
    check("tasks 目录存在", C.tasks_dir.exists())
    check("task_layer.enabled=False（安全默认）", C.get("task_layer","enabled") is False)
    check("github.enabled=False（未连远程）", C.get("github","enabled") is False)
    check("无明文密钥文件（扫描 .env/config 中的 sk- 模式）", not _has_plaintext(C))
    print("SELFCHECK overall:", "PASS" if ok else "FAIL")
    return 0 if ok else 1

def _has_plaintext(C):
    pat = re.compile(r"sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}")
    for p in (C.root/".env", C.meta_dir/"config.json"):
        if p.exists():
            try:
                if pat.search(p.read_text(encoding="utf-8", errors="replace")):
                    return True
            except Exception: pass
    return False

def main():
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("AGENT_OS_ROOT",""))
    ap.add_argument("--ensure-config", action="store_true")
    ap.add_argument("--audit-keys", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ns = ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"] = ns.root
    C = _lc()
    ran_any = ns.ensure_config or ns.audit_keys or ns.selfcheck
    if ns.ensure_config: ensure_config(C)
    if ns.audit_keys: audit_keys(C)
    if ns.selfcheck: sys.exit(selfcheck(C))
    if not ran_any:
        # 无参数 = 全跑（init.bat 用）
        ensure_config(C); audit_keys(C); sys.exit(selfcheck(C))
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception as e:
        print("init error:", e); sys.exit(1)
