# EXPERIMENTS — 底座实验记录（可见档案）

> 目的：把 gitignored 任务区的实验证据发布到可见位置。下游核验"做了什么实验、
> 结论如何"以此文件为准。

## ma-20260913 · 多 agent 编排最小实验（回应第六轮"多 agent 缺席"）

- **问题**：route-intake 的"保守默认单 agent"叠加"基线未测前不拆"成为永久状态。
- **route-intake 裁决**：并行度高 ✓ / 可独立验收 ✓ / 错误代价低 ✓ → orchestrator + 2 experts。
- **执行**：真实 spawn 两个独立审计专家（并行）：
  - 专家 A（管线漂移与回归审计）：5 findings，含 dashboard 先于 7a 回归执行的顺序漂移
    （单 agent 15 轮演化未发现）；
  - 专家 B（痛点台账与第二项目族真值审计）：3 findings，含 rollup 落后台账、3/3 HTTP 探针一致。
- **orchestrator 交叉验证**：8 findings → 5 属实、1 误报剔除（专家 B 的"悬空对象"判断
  被 git 历史推翻）、2 信息性。
- **基线对比结论**：并行独立审计显著优于单 agent 基线（覆盖更广 + 发现真缺陷 + 误报可剔除）。
  边界声明：审计型任务天然利于并行，不可外推"多 agent 处处更优"；编排能力来自宿主
  harness 的 subagent 机制，BASE 脚本层自身尚无 spawn 实现（P-16 挂账项）。
- **蒸馏**：第三条 pattern《independent-parallel-audit》。
- **证据**：tasks/project-layer-ma-20260913/task-evolve/audit/ma-20260913.json（任务区）+ 本文件。

## demo-20260913T102016Z / demo-20260913T110421Z · 十分钟黄金路径自测

- agent-os demo 两次实测走通：模板 charter → 规则门禁 accept → decisions.jsonl append-only。
- 依赖实况：Python + PyYAML（表述已于 v0.5.1 修正，不再自称"零配置"）。
