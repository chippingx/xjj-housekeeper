#!/bin/bash
# XJJ 浏览器应用启动脚本（Poetry 版）

echo "🌐 启动 XJJ 应用（浏览器版 - Poetry）"
echo "===================================="

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要 Python3 (>=3.8)"
    read -p "按回车关闭..."
    exit 1
fi

# 检查 Poetry
if ! command -v poetry &> /dev/null; then
    echo "❌ 需要 Poetry。请安装：https://python-poetry.org/docs/#installation"
    read -p "按回车关闭..."
    exit 1
fi

echo "📦 安装/校验依赖（Poetry）..."
poetry install --no-interaction || {
  echo "❌ 依赖安装失败，请检查网络或 Poetry 配置"
  read -p "按回车关闭..."
  exit 1
}

echo "🚀 启动应用..."
poetry run python -m streamlit run ui/app.py \
  --server.port=8501 \
  --browser.gatherUsageStats=false

read -p "应用已关闭，按回车退出..."