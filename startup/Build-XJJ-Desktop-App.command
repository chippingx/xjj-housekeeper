#!/bin/bash
# 打包 Tkinter 桌面应用为 macOS .app（PyInstaller）

echo "📦 打包 XJJ 桌面应用 (.app)"
echo "============================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$SCRIPT_DIR" || exit 1

# 依赖：Python3 + Poetry + PyInstaller
for cmd in python3 poetry; do
  if ! command -v $cmd &> /dev/null; then
    echo "❌ 需要 $cmd"
    read -p "按回车关闭..."; exit 1
  fi
done

echo "📦 安装/校验依赖（Poetry）..."
poetry install --no-interaction || { echo "❌ 依赖安装失败"; read -p "按回车关闭..."; exit 1; }

# 安装 PyInstaller（开发依赖）
if ! poetry run pyinstaller --version &> /dev/null; then
  echo "🧩 安装 PyInstaller..."
  poetry add --group dev pyinstaller || { echo "❌ PyInstaller 安装失败"; read -p "按回车关闭..."; exit 1; }
fi

ICON_PATH="assets/icons/xjj.icns"
NAME="XJJ-Housekeeper"

EXTRA_ICON_ARG=""
if [ -f "$ICON_PATH" ]; then
  EXTRA_ICON_ARG="--icon $ICON_PATH"
  echo "🎨 使用图标：$ICON_PATH"
else
  echo "ℹ️ 未找到图标文件（$ICON_PATH），将使用默认图标。"
fi

echo "🛠️ 开始打包..."
poetry run pyinstaller \
  --noconfirm \
  --windowed \
  --name "$NAME" \
  $EXTRA_ICON_ARG \
  ui/tkinter/app.py || { echo "❌ 打包失败"; read -p "按回车关闭..."; exit 1; }

APP_PATH="dist/$NAME.app"
if [ -d "$APP_PATH" ]; then
  echo "✅ 打包成功：$APP_PATH"
  open "$APP_PATH"
else
  echo "❌ 未找到打包产物，请检查输出"
fi

read -p "按回车结束..."