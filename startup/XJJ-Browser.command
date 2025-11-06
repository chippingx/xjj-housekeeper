#!/bin/bash
# XJJ 浏览器应用启动脚本（不依赖Poetry）

echo "🌐 启动XJJ应用（浏览器版-免Poetry）"
echo "================================="

# 获取项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要Python3"
    read -p "按回车关闭..."
    exit 1
fi

# 检查Streamlit
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "📦 安装Streamlit..."
    python3 -m pip install streamlit --user
fi

# 检查其他必要依赖
echo "📦 检查依赖..."
python3 -m pip install --user pandas requests 2>/dev/null || true

echo "🚀 启动应用..."
python3 -m streamlit run ui/app.py --server.port=8501 --browser.gatherUsageStats=false

read -p "应用已关闭，按回车退出..."