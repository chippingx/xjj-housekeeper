#!/bin/bash
# 打包 Tkinter 桌面应用为 macOS 单文件（PyInstaller）

echo "📦 打包 XJJ 桌面应用（单文件）"
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

echo "🛠️ 开始打包..."
# 使用 .spec 文件进行打包，确保配置（如图标）生效
poetry run pyinstaller XJJ-Housekeeper.spec --noconfirm || { echo "❌ 打包失败"; read -p "按回车关闭..."; exit 1; }

APP_PATH="dist/千姫の居所.app"
if [ -d "$APP_PATH" ]; then
  echo "✅ 打包成功：$APP_PATH"
  
  # 清理中间产物目录（用户只想要 .app）
  if [ -d "dist/千姫の居所" ]; then
    echo "🧹 清理临时构建目录..."
    rm -rf "dist/千姫の居所"
  fi
else
  echo "❌ 未找到打包产物，请检查输出"
fi

read -p "按回车结束..."
