# PROPOSAL: BASE 回流 13 — 第三轮反馈响应（易用性与生态收口）

> 类型: docs-reflow + 产品化
> 提案编号: BASE-REFLOW-20260913-13
> 状态: **人工门禁已批准**（2026-09-13，"批准全部"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 背景

第三轮独立反馈（基准 ecaff30）："内核远超原型，外壳停在原型"——文档滞后 4 版本、
根 README 缺失、平台锁定、硬编码路径、无依赖声明、无接口契约。
逐项核验全部属实（BASE/README 标题 v0.1.0；git ls-tree 无根 README；
USAGE 生成于 1818432 且无 project_*；agent-os.cmd 硬编码 D:/agent-os；无 requirements）。

## 变更（P0/P1/P2）

1. BASE/README.md 重写至 v0.5.0：14 阶段、2 项目族、反馈闭环、快速开始、
   参与方式（提案+门禁+人工）、诚实局限；
2. 新增根 README.md（GitHub 首页引导 + 展示站/Issues 链接）；
3. generate_usage_doc.py 修正（七阶段→14 阶段）并重新生成 AGENT-OS-USAGE.md
   （生成时间 2026-09-13、base=ecaff30、scripts=50、含 project_*）；
4. requirements.txt + Python 版本契约（3.9+ 已实测；pywin32 标注 Windows-only）；
5. BASE/docs/charter.schema.json（charter/评估域/指标的机器可读契约第一版）；
6. agent-os.cmd 去硬编码（`set AGENT_OS_ROOT=%~dp0` 自动定位仓库根）。

## 诚实声明（未做项）

- 跨平台（.sh/cron）全量改造：**列为下一里程碑**——本机无 Linux 环境，
  不验证不宣称（README 已如实标注"Windows 优先"）；
- charter.schema 尚未被新项目引用校验——P-13 挂账项；
- ROADMAP（设计冻结契约）未动，路径参数化进度以 README/本归档为准。

## 台账

P-13#? open(third-party-feedback-round3)：保持 open 至跨平台落地验证、
schema 被真实引用、下一轮核验确认。

## 回滚

git revert a47a313。
