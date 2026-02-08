#!/bin/bash
# 启动 Tkinter 桌面客户端

echo "🖥️ 启动 XJJ 桌面客户端 (Tkinter)"
echo "================================"

# 项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$SCRIPT_DIR" || exit 1

# 检查 Python3
if ! command -v python3 &> /dev/null; then
  echo "❌ 需要 Python3 (>=3.10)"
  read -p "按回车关闭..."; exit 1
fi

# 优先使用 Poetry 运行（隔离依赖）
if command -v poetry &> /dev/null; then
  echo "📦 使用 Poetry 环境启动"
  echo "🔒 修复锁文件..." 
  poetry lock --no-interaction || { echo "❌ Poetry lock 失败"; read -p "按回车关闭..."; exit 1; }
  poetry install --no-interaction || { echo "❌ Poetry 依赖安装失败"; read -p "按回车关闭..."; exit 1; }
  poetry run python ui/tkinter/app.py &
else
  echo "🐍 使用系统 Python 启动"
  python3 ui/tkinter/app.py &
fi

APP_PID=$!
sleep 1
echo "✅ 已启动。关闭此窗口不会退出应用。"
read -p "按回车键结束并关闭应用..."
kill $APP_PID 2>/dev/null
echo "🛑 已退出"
