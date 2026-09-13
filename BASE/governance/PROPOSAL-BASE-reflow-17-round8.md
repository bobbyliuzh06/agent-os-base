# PROPOSAL: BASE 回流 17 — 第八轮反馈响应（版本真值统一 + 入口自洽 + 实验可见性）

> 类型: consistency-reflow + product-reflow
> 提案编号: BASE-REFLOW-20260913-17
> 状态: **人工门禁已批准**（2026-09-13，"批准全部"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## distillation_check（I-10 固定问句）

**本轮是否有新轨迹可蒸馏？答案：有，已蒸馏。** 本轮真实轨迹 = "最强调真值溯源的
底座连自己版本号都管不住（四处不一致）+ 双入口二义 + 站点入口与定位自相矛盾"——
再次印证既有 pattern《downstream-view-gap》（元真值也是真值，元入口也是下游）与
《meta-procedure-drift》的同源家族。此轮不新增 pattern（避免为蒸馏而蒸馏），
把本轮证据追加到 downstream-view-gap 的证据轨迹字段（见 pattern 文件更新）。

## 背景与核验

第八轮小白视角实测四项缺陷全部属实：版本号四处不一致（root README v0.5.0、
agent-os.cmd/init.bat v0.4）、双入口语义不一致、站点脚本数快照漂移（声称 50 实际 51）、
零配置表述不实（需 PyYAML）。另有定位（A 框架）与站点终端用户入口的自相矛盾。

## 变更清单

1. **版本真值统一**：root README/agent-os.cmd/init.bat → v0.5.1；cmd 增加 demo 子命令
   （与 pip CLI 同一命令集，`agent-os.cmd demo` 实测走通）；cmd_demo 表述修正
   （零 LLM/零网络，依赖 PyYAML）；
2. **I-11 回归检查**：全仓版本串一致性（README/.cmd/.bat/cli 必须含 VERSION 对应串），
   实测 PASS；站点脚本数本为动态计数，快照漂移随下次发布自愈；
3. **站点入口自洽**：新增"给开发者：3 行跑通"真实入口；机制动画明确标注"预置回放
   （输入回显），不是真实运行"；hero 加诚实人话（"不会写代码，这个工具目前不适合你"）；
4. **EXPERIMENTS.md**：发布多 agent 编排实验证据（专家报告要点、交叉验证、基线结论），
   回应"多 agent 缺席"指控中的可见性缺口——实验确已真实 spawn 过，证据此前只在 gitignored 任务区。

## 台账

P-19#? progress：四项缺陷全修 + I-11 机制化；保持 open 至第九轮核验确认。

## 回滚

git revert 本轮提交。
