# -*- coding: utf-8 -*-
"""agent_os_cli — agent-os 命令入口（最小可分发形态，pip install -e . 后可用）。

定位：A 开发者框架的最小 CLI 壳。本模块只做两件事：
1) 定位仓库 BASE/scripts（环境变量 AGENT_OS_ROOT 或包所在仓库根向上查找）；
2) 把子命令分发给 BASE/scripts/cmd_*.py（现成实现，不重写）。
诚实声明：这是 v0.5.1 的最小分发壳，Windows 优先；pip 安装包本身不含管线脚本，
需与仓库并存（研究原型阶段）。"""
import os, subprocess, sys
from pathlib import Path


def find_root():
    env = os.environ.get("AGENT_OS_ROOT", "").strip().strip('"')
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for cand in [here] + list(here.parents):
        if (cand / "BASE" / "scripts" / "cmd_demo.py").exists():
            return cand
    raise SystemExit("找不到 agent-os 仓库根（BASE/scripts/cmd_demo.py 不存在）。"
                     "请设置 AGENT_OS_ROOT 或把包安装在仓库内（pip install -e .）。")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("agent-os v0.5.1 —— 自托管、自审查、自演化的智能体底座（研究原型）\n"
              "用法：agent-os <子命令> [参数]\n"
              "  子命令：demo    十分钟黄金路径（模板 charter + 一次最小演化，零配置）\n"
              "          init    初始化任务目录\n"
              "          run     在任务工作区执行一次任务\n"
              "          watch   查看任务健康度\n"
              "          doctor  扫描任务区冗余\n"
              "          quickcard 新手快速卡\n"
              "完整机制与参与方式见 BASE/README.md 与 https://bobbyliuzh06.github.io/agent-os-base/")
        return 0
    root = find_root()
    cmd = sys.argv[1]
    py = sys.executable
    script = root / "BASE" / "scripts" / ("cmd_%s.py" % cmd)
    if not script.exists():
        print("未知子命令：%s（agent-os help 查看列表）" % cmd)
        return 1
    env = dict(os.environ)
    env["AGENT_OS_ROOT"] = str(root)
    return subprocess.call([py, str(script)] + sys.argv[2:], env=env)


if __name__ == "__main__":
    sys.exit(main())
