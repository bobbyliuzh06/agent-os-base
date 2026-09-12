#!/usr/bin/env bash
# new_task.sh — 从当前 BASE 复制出独立项目工作区
# 用法: ./new_task.sh <project-name>
# 依赖: cp (POSIX, 必带); rsync 可选(有则更优, 无则自动降级为 cp -R)
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
NAME="$1"

if [ -z "$NAME" ]; then
  echo "用法: ./new_task.sh <project-name>"
  exit 1
fi

DEST_PARENT="$(dirname "$BASE_DIR")/PROJECTS"
DEST="$DEST_PARENT/$NAME"

if [ -e "$DEST" ]; then
  echo "错误: 已存在 $DEST"
  exit 1
fi

mkdir -p "$DEST_PARENT"

# 复制(base -> dest), 排除 .git; 优先 rsync, 缺失则 cp -R
if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude='.git' "$BASE_DIR/" "$DEST/"
else
  cp -R "$BASE_DIR" "$DEST.tmp"   # cp -R 不排除 .git, 先拷再清
  rm -rf "$DEST.tmp/.git"
  mv "$DEST.tmp" "$DEST"
fi

# 项目专属工作区(空, 带 .gitkeep 已由 cp 带入; 此处确保目录存在)
mkdir -p "$DEST/WORKSPACE/raw" "$DEST/WORKSPACE/wiki/patterns" "$DEST/WORKSPACE/skills"

# 项目不应携带/篡改 BASE 的版本与变更记录(项目是实例, BASE 才是版本主体)
rm -f "$DEST/META/VERSION" "$DEST/META/CHANGELOG.md" 2>/dev/null || true

# governance/ 属 BASE 侧(归档已接受提案), 不复制到项目
rm -rf "$DEST/governance" 2>/dev/null || true

echo "已创建: $DEST"
echo ""
echo "下一步:"
echo "  1) 在 DeepSeek Harness 中选择工作区: $DEST"
echo "  2) 开新会话，首条粘贴 BOOT 指令(见 BASE/README.md)"
echo "  3) 任务结束产出 PROPOSAL.md -> 人工审核 -> 回填 BASE/governance/ + 打 tag"
