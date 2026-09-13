# PROPOSAL: BASE 回流 12 — 第二轮独立核验反馈响应

> 类型: scripts-reflow + 修复
> 提案编号: BASE-REFLOW-20260913-12
> 状态: **人工门禁已批准**（2026-09-13，"批准全部"）
> 归档: 依 GATE.md 回填操作归档至 governance/

## 背景

第二轮独立核验（逐行读 reflow 11 的 4 个 commit diff，基准 727b181）：
- 确认 5 项真正生效（版本元数据/I-9、阶段顺序修复、hero、task_layer 明确化、真实世界目标）；
- 指出 2 个缺口：feedback v3 **表达端未接**（clones+delta 只采集不展示——属实）；
  6f 自动发布**缺端到端验证**（与管线自生复核人登记的 P-10/P-11 独立收敛互证）；
- 2 条建议：clones 失败须显式标注（勿静默 None）；版本卡标注快照提交防"元数据漂移"误读。

## 变更

1. project_site_gen.py：truth claim 与页面"真实反馈"节输出 clones_14d(count/uniques)
   与 delta_vs_prev 环比行；版本卡标注"站点快照生成于该提交（仓库 HEAD 可能更新）"；
2. project_feedback_truth.py：clones 纳入 feedback_status 可用性判断；不可得时
   显式 clones_note=unavailable(原因)，不静默；
3. 端到端验证（P-10 关闭证据）：真实差异 → 调度自动重生成 → `eb808f8 [auto-site]`
   自动提交+推送 → Pages 刷新（线上实测：clones=count 55/uniques 25、环比可见、快照标注可见）。

## 台账

- P-10#43 resolved(e2e-evidence)；P-11#44 resolved(e2e-evidence)；
- P-12#45 open(third-party-feedback-round2)——保持 open 至第三轮核验确认或真实世界目标达成；
- lessons 已记录（外部观察抓出 6f 顺序 bug → 可见性规则固化）。

## 回滚

git revert dba3d34 + eb808f8。

## 未做

30 秒交互 demo、LLM 结构化输出、Pages 流量探针——如实挂账（P-9/P-8）。
