# RELEASE RESULT: v0.5.0

> 时间: 2026-09-13；授权: RELEASE-AUTH-v0.5.0-20260913.md（用户本人授权发布）

## 结果

- 提交: 4d6640e（24 文件，1740+/7-）+ 52b8e16（release-attach 参数与门禁更新）
- 标签: v0.5.0（tag object ba70593a，peel → 4d6640e）
- 推送: main 16bebbe→52b8e16；新 tag v0.5.0 已推送
- Release: https://github.com/bobbyliuzh06/agent-os-base/releases/tag/v0.5.0
  （资产 agent-os-base-v0.5.0.zip, sha256 33df7321...）
- 供应链: release-attach 工作流 success（run 34737470812），四方核验 PASS：
  门禁哈希 == 资产 == subject digest；gh release verify-asset ✓；
  gh attestation verify --signer-workflow ✓（exit 0）；源 main@52b8e16
- 台账: BASE/regression-runs/SUPPLYCHAIN-v0.5.0-provenance.json（schema 1.1, final）
  （如实记录：本 bundle predicate.builder.id 为 null，签名身份以 --signer-workflow 锁定验证为准）
- 站点: GitHub Pages 已启用（build_type=workflow），
  https://bobbyliuzh06.github.io/agent-os-base/ HTTP 200
- 发布后修复: 反馈栏过期文案 + P1 summary 字段重建 + 版本号刷新（随后续提交推送，Pages 自动重部署）

## 复盘要点（写入 lessons）

- Pages 首次运行失败因 Pages 未启用（configure-pages 404）→ 先启用再重跑即成功；
- 发布快照与章程/模板必须同批更新，避免"线上写着未发布"的过期声明；
- 供应链证明沿用 v0.4.6 单工作流模式一次通过，无 retry。
