# agent-os / BASE — 自托管、自审查、自演化的智能体底座

> **版本 v0.5.0**（git tag v0.5.0；供应链台账 SUPPLYCHAIN-v0.5.0-provenance.json）。
> 公开展示站（真值驱动，管线每 4 小时自动刷新）：https://bobbyliuzh06.github.io/agent-os-base/
> 反馈通道：https://github.com/bobbyliuzh06/agent-os-base/issues

## 这是什么

agent-os 不追求"一次性交付"，而是把每个长期目标当作**持续责任**来管理——
把它注册为一个 Project（charter + 记忆 + 真值 + 节奏 + 策略 + 审计），
由底座按周期自动观察、提议、门禁、执行、记录、复盘，并把失败聚合成痛点、把
反馈固化为记忆。三条铁律是硬约束：

1. **记忆先于智能** —— 假设台账/决策日志/教训库 append-only，不可篡改；
2. **真值先于自动化** —— 每个页面声称都有来源文件 + sha256 溯源；接不上真值
   的场景显式降级声明，不编造；
3. **人机分界按风险** —— 规则层对 BASE 写入一律拒绝，只有人工门禁能放行。

## 当前状态（活系统，数字由管线生成）

- **14 阶段调度**（每 4 小时）：pre-health → propose → gate → post → cleanup →
  observe → 5a 自体检 → 5b 站点生成 → 6a 证据验证 → 6b 独立复核(pro 模型) →
  6c 全局痛点汇总 → 6d 事件驱动策略池 → 6e 反馈真值轮询 → 6f 站点自动发布 →
  advice → post-health → 7a 过程回归 → dashboard
- **50 个管线脚本**（BASE/scripts）、**19 份回归台账**、**12 份治理归档**
- **2 个项目族**：纸面投资组合（合成数据演练，已冻结为机制样本）、链接保鲜
  知识库（真实 HTTP 探针真值）——验证机制跨域迁移
- **痛点台账**：失败聚合、关闭必附证据、未治愈持续挂账
- **真实世界反馈**：Issues/下载/stars/clones 轮询入真值，反馈回执写入可见通道

## 快速开始（Windows 优先；跨平台为下一里程碑）

```bat
:: 1. 依赖：Python 3.9+（本机 3.9.13 验证） + PyYAML
pip install -r requirements.txt
:: 2. 克隆后无需改路径：入口自动定位仓库根（不再硬编码 D:/agent-os）
agent-os.cmd help
:: 3. 单次体检+站点刷新+发布（完整 14 阶段）
BASE\scripts\dispatch_wrapper.bat
:: 4. 查看公开站点（或本地生成件）
start https://bobbyliuzh06.github.io/agent-os-base/
```

> 平台说明（诚实）：调度依赖 Windows 计划任务（AgentOS_EvolveDispatch），
> 跨平台（cron/.sh）为已声明的下一里程碑，未经验证不宣称支持。

## 目录

```
BASE/
  scripts/      # 14 阶段管线（dispatch_wrapper.bat 为调度入口）
  docs/         # PROJECT-LAYER.md(Project 层设计) / AGENT-OS-USAGE.md(生成) / charter.schema.json
  META/         # CONSTITUTION/GATE/REGRESSION/config.json/VERSION
  governance/   # 全部回流提案与发布档案（人工门禁留痕）
  regression-runs/  # 台账（供应链证明、回归、体检、反馈轮询日志）
site/           # 展示站发布快照（管线 6f 自动提交推送）
tasks/          # 项目族（gitignored：chart/记忆/真值/审计，append-only）
```

## 参与方式（唯一路径：提案 + 门禁 + 人工）

1. 任何修改先写 PROPOSAL（改动、动机、风险、回滚、验收）；
2. 过确定性规则层（对 BASE 写入一律 reject → 升级人工）；
3. 人工门禁批准后落盘；归档至 BASE/governance/；
4. 外部反馈同样走痛点台账：登记 → 行动 → 证据回写 → 可见回执（Issue）。

## 诚实局限（与展示站同步声明）

- 投资案例为合成数据演练，无真实市场含义；价值在决策链纪律而非收益；
- task_layer.enabled=false（明确为下一里程碑候选）；
- 访问量（Pages 流量）无公开 API，未展示即未编造；
- 文档正在追平代码（v0.5.0 本轮更新）；跨平台与接口契约逐项推进中。
