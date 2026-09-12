# 提案：给 BASE 增加“每日提案计数”规则
## 动机
常驻后每天产生大量提案，需要在 propose-gate 输出里增加统计快照。
## 建议改动
- 修改 D:/agent-os/BASE/TEMPLATES/PROPOSAL.md，增加“统计快照”节，要求运行 proposal_stats.py 并粘贴输出。
- 修改 D:/agent-os/BASE/skills/propose-gate/SKILL.md，步骤中要求生成统计快照。
- 新增 D:/agent-os/BASE/scripts/proposal_stats.py，只读统计 PENDING/governance/ARCHIVE 数量。
## 风险自评
低：仅新增模板字段、技能说明与只读脚本；回滚方案为 git revert 上述三文件。