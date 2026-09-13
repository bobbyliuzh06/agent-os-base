# EXPERIMENTS — 底座实验与真实目标记录（可见档案）

> 目的：把 gitignored 任务区的实验/真实目标证据发布到可见位置。
> 下游核验"做了什么、结论如何、证据在哪"以此文件为准。

## 真实目标（talk 入口，可核验）

- **repo-freshness（仓库别断更，第九轮注册）**：真实真值第一周期全 PASS
  （repo-synced / site-alive / dispatch-recent）。证据：
  `tasks/talk-goal-20260913T114221Z/task-evolve/truth/check-*.json`（任务区）。
  诚实备注（第十轮修正）：该目标是底座自我维护，不是外部真实用户诉求——已如实承认，
  外部真实目标正通过 agent-os talk 向真实的人征集（见站点"真实目标"节与 P-21 台账）。
- **talk --run 链路（第十轮实测）**：`agent-os talk --run "帮我长期盯住一组重要链接"`
  → 中文目标完整保留（目录名含全文）→ charter 生成 → 规则门禁 accept →
  第一周期底座健康真值全 PASS，EXIT=0。证据：`tasks/talk-帮我长期盯住一组重要链接-*/`
  （任务区）；站点 truth.json 有 real-goal claim（链接指向仓库文件，可核验）。

## ma-20260913 · 多 agent 编排最小实验（回应第六轮"多 agent 缺席"）

- route-intake 裁决：并行度高 ✓ / 可独立验收 ✓ / 错误代价低 ✓ → orchestrator + 2 experts。
- 专家 A（管线审计）5 findings（含 dashboard 先于 7a 的顺序漂移——单 agent 15 轮未发现）；
  专家 B（台账+真值审计）3 findings；orchestrator 交叉验证：5 属实、1 误报剔除、2 信息性。
- 结论：并行独立审计显著优于单 agent 基线；边界：审计型任务天然利于并行，不可外推。
- 蒸馏：第三条 pattern《independent-parallel-audit》。

## demo 十分钟黄金路径自测

- agent-os demo 多次实测走通（模板 charter → 门禁 accept → decisions.jsonl append-only）。
- 依赖实况：Python + PyYAML（表述已修正，不自称零配置）。
