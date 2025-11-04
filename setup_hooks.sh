#!/bin/bash

# 设置Git hooks以强制执行无迁移无兼容政策

echo "🔧 设置Git hooks..."

# 创建.git/hooks目录（如果不存在）
mkdir -p .git/hooks

# 复制pre-commit hook
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo "✅ Git hooks设置完成！"
echo ""
echo "📋 已安装的hooks:"
echo "  - pre-commit: 检查无迁移无兼容政策违规"
echo ""
echo "🚨 重要提醒:"
echo "  - 每次提交前会自动检查迁移代码"
echo "  - 发现违规代码将阻止提交"
echo "  - 详见 NO_MIGRATION_POLICY.md"
echo ""