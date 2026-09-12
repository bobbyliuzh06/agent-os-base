# ARCHIVE/ — 被拒提案归档规范

> GATE 规定：拒绝 ≠ 删除。被拒提案归档至此，pattern 保留供再评估。

## 命名
- 文件：`PROPOSAL-<项目>-v<版本>-<YYYYMMDD>.md`（例：`PROPOSAL-bootstrap-v0.1-20260912.md`）
- 同一提案的多次裁定在同一文件追加“裁定记录”段，不另建文件

## 保留期限
- 永久保留：被拒提案是后续再评估的依据，经验库不回滚
- 清理仅限合并重复条目，且须在 META/CHANGELOG.md 记录

## 复活流程
1. 提案人基于新证据（≥1 条真实轨迹，或新的非原领域探针复用结果）重开原提案
2. 走完整 GATE 流程：propose-gate 自检 → gate-review 独立门控 → 人工终裁
3. 复活成功：旧文件标注 `superseded by <governance 中新提案路径>`，新提案归档至 governance/
4. 复活失败：在旧文件追加新裁定记录，仍保留于 ARCHIVE/