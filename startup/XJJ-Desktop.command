#!/bin/bash
# XJJ 桌面应用启动脚本（不依赖Poetry）

echo "🖥️ 启动XJJ桌面应用（免Poetry版）"
echo "==============================="

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

# 后台启动Streamlit
python3 -m streamlit run ui/app.py \
    --server.port=8501 \
    --server.headless=true \
    --browser.gatherUsageStats=false \
    --server.address=127.0.0.1 &

STREAMLIT_PID=$!

# 等待服务器启动
echo "⏳ 等待服务器启动..."
for i in {1..15}; do
    if curl -s http://127.0.0.1:8501 > /dev/null 2>&1; then
        echo "✅ 服务器启动成功!"
        break
    fi
    sleep 1
done

# 创建桌面窗口
echo "🖥️ 创建桌面窗口..."
cat > /tmp/xjj_app.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>XJJ 视频管理系统</title>
    <style>
        body { margin: 0; padding: 0; overflow: hidden; background: #f0f2f6; }
        iframe { width: 100%; height: 100vh; border: none; }
    </style>
</head>
<body>
    <iframe src="http://127.0.0.1:8501"></iframe>
</body>
</html>
EOF

open /tmp/xjj_app.html
sleep 2

echo "✅ 桌面应用已启动!"
echo "💡 关闭此窗口将停止应用"
read -p "按回车键停止应用..."

# 清理
kill $STREAMLIT_PID 2>/dev/null
rm -f /tmp/xjj_app.html
echo "🛑 应用已停止"