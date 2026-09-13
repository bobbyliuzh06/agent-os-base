# RELEASE AUTHORIZATION: v0.5.0

> 类型: human-verdict（发布授权记录）
> 时间: 2026-09-13
> 状态: 用户本人在会话中授权"发布 v0.5.0（推荐）"

## 授权内容

1. 翻转 BASE/META/config.json `github.enabled` false→true（repo_url 指向 bobbyliuzh06/agent-os-base）；
2. 提交累计 8 次回流的 17 项变更 + 站点发布件（site/ + pages 工作流）+ 版本文件更新；
3. `git tag -a v0.5.0` 并 push main + tag；
4. GitHub Release v0.5.0 + release-attach 供应链验证（v0.4.6 同款四方核验）；
5. 启用 GitHub Pages 发布展示站（site/ 目录，workflow 构建）。

## 依据

- 发布 SOP 阶段清单: tasks/project-layer-p3-20260912/task-evolve/base-reflow/RELEASE-SOP-v0.5.0-staged.md
- standing 规则："no push unless a step authorizes it" —— 本记录即该授权的留痕。
