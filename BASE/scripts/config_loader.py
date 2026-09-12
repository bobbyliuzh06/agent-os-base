#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent-OS 统一配置读取。优先级：环境变量 > base/meta/config.json > 代码默认。
所有脚本改从本模块取路径，禁止再写根路径字面量。"""
import os, json, sys
from pathlib import Path

DEFAULT_ROOT_GUESS = str(Path.cwd())  # 仅当无任何配置时回退；正式环境应由 AGENT_OS_ROOT 或 config.json 覆盖

def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_root():
    # 1) 环境变量最高优先
    env = os.environ.get("AGENT_OS_ROOT", "").strip().strip('"')
    if env and Path(env).exists():
        return Path(env)
    # 2) 从调用脚本反推：scripts/.. 应为 BASE；BASE/.. 应为 root（兼容当前 BASE/scripts 与未来 base/scripts）
    here = Path(__file__).resolve()
    for cand in [here.parent, here.parent.parent, here.parent.parent.parent]:
        if (cand / "BASE" / "META" / "config.json").exists() or (cand / "base" / "meta" / "config.json").exists():
            return cand
    # 3) 代码默认（仅本地兼容）
    return Path(DEFAULT_ROOT_GUESS)

def apply_root_arg(argv=None):
    """从 argv 中剥离 --root X 并写入 AGENT_OS_ROOT；返回剩余 argv。供所有脚本统一入口。"""
    argv = list(sys.argv if argv is None else argv)
    if "--root" in argv:
        i = argv.index("--root")
        if i + 1 < len(argv):
            os.environ["AGENT_OS_ROOT"] = argv[i + 1]
            del argv[i:i + 2]
    return argv

class Config:
    def __init__(self):
        self.root = get_root()
        # 兼容新旧两层：旧 BASE/META/config.json；新 base/meta/config.json
        old_cfg = self.root / "BASE" / "META" / "config.json"
        new_cfg = self.root / "base" / "meta" / "config.json"
        self.raw = {}
        if old_cfg.exists():
            self.raw.update(_load_json(old_cfg))
        if new_cfg.exists():
            self.raw.update(_load_json(new_cfg))
        p = self.raw.get("paths", {}) or {}
        self.base_dir = self._resolve(p.get("base_dir")) or (self.root / "BASE")
        # v0.4 布局 base/ 与现行 BASE/ 在 Windows 上大小写不敏感会互相命中：
        # 只要现行大写 BASE/ 存在，就显式采用现行布局（与冒烟预期一致；Linux 真 base/ 布局不受影响）
        if self.base_dir.name.lower() == "base" and (self.root / "BASE").exists():
            self.base_dir = self.root / "BASE"
        if not self.base_dir.exists():
            self.base_dir = self.root / "BASE"
        self.meta_dir = self.base_dir / "META"
        self.scripts_dir = self.base_dir / "scripts"
        self.docs_dir = self.base_dir / "docs"
        self.profile_dir = self._resolve(p.get("profile_dir")) or (self.root / "profile")
        self.tasks_dir = self._resolve(p.get("tasks_dir")) or (self.root / "tasks")
        self.registry = self._resolve(p.get("registry")) or (self.tasks_dir / "registry.json")
        self.regression = self.base_dir / "regression-runs"
        self.pending = self.root / "PENDING"

    def _resolve(self, val):
        if not val:
            return None
        s = str(val)
        s = s.replace("${AGENT_OS_ROOT}", str(self.root))
        return Path(s)

    def get(self, *keys, default=None):
        cur = self.raw
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def env_key(self, name, sources=None):
        # 按 config.env.api_key_source 顺序取；不打印明文
        sources = sources or self.get("env", "api_key_source") or ["env:%s" % self.get("env","key_env_name","DEEPSEEK_API_KEY")]
        for src in sources:
            if src.startswith("env:"):
                v = os.environ.get(src.split(":",1)[1].strip())
                if v: return v
            if src.startswith("winreg:"):
                try:
                    import winreg
                    spec = src.split(":", 1)[1].strip()
                    if "\\" in spec:
                        hive_name, sub = spec.split("\\", 1)
                        hive = getattr(winreg, hive_name, winreg.HKEY_CURRENT_USER)
                        vname = self.get("env", "key_env_name", "DEEPSEEK_API_KEY")
                    else:
                        # 裸值名格式（如 winreg:DEEPSEEK_API_KEY）默认在 HKCU\Environment 下取
                        hive, sub = winreg.HKEY_CURRENT_USER, "Environment"
                        vname = spec
                    with winreg.OpenKey(hive, sub) as k:
                        return winreg.QueryValueEx(k, vname)[0]
                except Exception:
                    continue
        # .env 兜底（不强制依赖 python-dotenv）
        envfile = self.root / ".env"
        if envfile.exists():
            for line in envfile.read_text(encoding="utf-8", errors="replace").splitlines():
                line=line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k,v=line.split("=",1)
                    if k.strip()==self.get("env","key_env_name","DEEPSEEK_API_KEY"):
                        return v.strip().strip('"')
        return None

def load_config():
    return Config()

if __name__ == "__main__":
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    c = load_config()
    print("root=", c.root)
    print("base_dir=", c.base_dir)
    print("scripts_dir=", c.scripts_dir)
    print("regression=", c.regression)
    print("tasks_dir=", c.tasks_dir)
    print("has_api_key=", bool(c.env_key("x")))
