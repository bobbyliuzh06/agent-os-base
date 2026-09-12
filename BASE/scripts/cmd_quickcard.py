#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-os quickcard：打印 REQ 快速卡模板；--task <id> 则把填空结果写入 tasks/<id>/REQ.md。"""
import os, sys, argparse, datetime
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cli_common import (cfg, ensure_dirs, load_registry, gen_task_id, find_similar,
                        write_text, tasks_dir)

TPL = """# REQ-{tid}

> 快速卡：每项填一句，越具体越好。填完即可 `agent-os run {tid}`。

- 版本基线：{version}
- 领域：{domain}（如 sales/website/data/seo）
- 目标：{goal}（一句话 + 可量化验收，如"把 X 转成 Y 报告，错误率<1%"）
- 范围：
  - 必做：
  - 不做：
  - 后续：
- 输入：<文件路径/格式/表结构/权限>
- 输出：<文件路径/格式/命名>
- 验收：
  - 功能：
  - 质量：rc=0、无 unknown、回归全绿、人工抽检通过
  - 性能/成本：<如单次<10分钟、token 预算>
- 约束：技术栈/环境 / 安全(不写明文密钥) / 合规(审计日志)
- 风险与回滚：失败点 + 保留旧版 + 还原方案
- 是否允许改底座规则：否（改→走 BASE 提案/门禁，不在本任务区直改）
- 自动化程度：全人工 / 半自动(仅草案) / 自动(仅白名单+四锁)
- 观察周期：如跑 3 轮再评估合并
"""

def main():
    if sys.stdout.encoding.lower().startswith("utf"):
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=os.environ.get("AGENT_OS_ROOT",""))
    ap.add_argument("--task", default=""); ap.add_argument("--domain", default=""); ap.add_argument("--goal", default="")
    ap.add_argument("--print", action="store_true", help="仅打印模板到 stdout")
    ns = ap.parse_args()
    if ns.root: os.environ["AGENT_OS_ROOT"] = ns.root
    ensure_dirs(); C = cfg(); reg = load_registry()
    tid = ns.task or (gen_task_id(ns.domain or "general", ns.goal or "task"))
    filled = TPL.format(tid=tid, version=C.get("version") or "proto",
                        domain=ns.domain or "<领域>", goal=ns.goal or "<目标>")
    if ns.print or not ns.task:
        print(filled)
    if ns.task:
        p = tasks_dir()/tid/"REQ.md"
        if p.exists():
            print("[skip] 已存在，不覆盖：", p)
        else:
            write_text(p, filled)
            print("QUICKCARD written:", p)
    return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception as e: print("quickcard error:", e); sys.exit(1)
