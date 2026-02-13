#!/bin/bash
# 打开已打包的 .app（默认路径 dist/倩影の居.app）

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
APP_PATH="$SCRIPT_DIR/dist/倩影の居.app"

if [ -d "$APP_PATH" ]; then
  echo "🖱️ 打开：$APP_PATH"
  open "$APP_PATH"
else
  echo "❌ 未找到 $APP_PATH，请先运行 startup/Build-XJJ-Desktop-App.command"
fi

read -p "按回车结束..."
