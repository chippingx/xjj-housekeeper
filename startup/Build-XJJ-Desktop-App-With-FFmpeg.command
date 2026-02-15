#!/bin/bash
# Build Tkinter desktop app for macOS (PyInstaller)

echo "📦 Building XJJ Desktop App (single-file)"
echo "========================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
cd "$SCRIPT_DIR" || exit 1

# Requirements: Python3 + Poetry + PyInstaller
for cmd in python3 poetry; do
  if ! command -v $cmd &> /dev/null; then
    echo "❌ Missing $cmd"
    read -p "Press Enter to exit..."; exit 1
  fi
done

if ! command -v ffprobe &> /dev/null; then
  echo "❌ ffprobe not found; bundling is not possible"
  echo "   Suggested: brew install ffmpeg"
  read -p "Press Enter to exit..."; exit 1
fi
if ! command -v ffmpeg &> /dev/null; then
  echo "❌ ffmpeg not found; bundling is not possible"
  echo "   Suggested: brew install ffmpeg"
  read -p "Press Enter to exit..."; exit 1
fi

echo "📦 Installing/checking dependencies (Poetry)..."
poetry install --no-interaction || { echo "❌ Dependency install failed"; read -p "Press Enter to exit..."; exit 1; }

# Install PyInstaller (dev dependency)
if ! poetry run pyinstaller --version &> /dev/null; then
  echo "🧩 Installing PyInstaller..."
  poetry add --group dev pyinstaller || { echo "❌ PyInstaller install failed"; read -p "Press Enter to exit..."; exit 1; }
fi

export XJJ_INCLUDE_FFMPEG=1

echo "🛠️ Building (with bundled ffmpeg/ffprobe)..."
# Build with spec to ensure config (e.g., icon) is applied
poetry run pyinstaller XJJ-Housekeeper.spec --noconfirm || { echo "❌ Build failed"; read -p "Press Enter to exit..."; exit 1; }

APP_PATH="dist/倩影の居.app"
if [ -d "$APP_PATH" ]; then
  echo "✅ Build succeeded: $APP_PATH"
  
  # Clean intermediate output (keep .app only)
  if [ -d "dist/倩影の居" ]; then
    echo "🧹 Cleaning intermediate build directory..."
    rm -rf "dist/倩影の居"
  fi
else
  echo "❌ Build output not found; please check logs."
fi

read -p "Press Enter to close..."
