@echo off
REM 打包 Tkinter 桌面应用为 Windows 单文件（PyInstaller）
setlocal enabledelayedexpansion

echo 📦 打包 XJJ 桌面应用（单文件）
echo =============================

REM 定位到项目根目录（startup 上一级）
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.." || goto :error

REM 依赖：Python + Poetry + PyInstaller
where python >nul 2>nul || (
  echo ❌ 需要 python
  pause
  exit /b 1
)

where poetry >nul 2>nul || (
  echo ❌ 需要 poetry
  pause
  exit /b 1
)

echo 📦 安装/校验依赖（Poetry）...
poetry install --no-interaction || goto :error

poetry run pyinstaller --version >nul 2>nul || (
  echo 🧩 安装 PyInstaller...
  poetry add --group dev pyinstaller || goto :error
)

set NAME=XJJ-Housekeeper
set ICON_PATH=assets\icons\xjj.ico
set ICON_ARG=
if exist "%ICON_PATH%" (
  set ICON_ARG=--icon "%ICON_PATH%"
  echo 🎨 使用图标：%ICON_PATH%
) else (
  echo ℹ️ 未找到图标文件（%ICON_PATH%），将使用默认图标。
)

set ADD_DATA=
if exist "i18n" set ADD_DATA=%ADD_DATA% --add-data "i18n;i18n"
if exist "output" set ADD_DATA=%ADD_DATA% --add-data "output;output"
if exist "config\app_meta.json" set ADD_DATA=%ADD_DATA% --add-data "config\app_meta.json;config"
if exist "tools\video_info_collector\config.yaml" set ADD_DATA=%ADD_DATA% --add-data "tools\video_info_collector\config.yaml;tools\video_info_collector"
if exist "tools\filename_formatter\rename_rules.yaml" set ADD_DATA=%ADD_DATA% --add-data "tools\filename_formatter\rename_rules.yaml;tools\filename_formatter"

echo 🛠️ 开始打包...
poetry run pyinstaller ^
  --noconfirm ^
  --windowed ^
  --onefile ^
  --name "%NAME%" ^
  %ICON_ARG% ^
  %ADD_DATA% ^
  ui\tkinter\app.py || goto :error

set APP_PATH=dist\%NAME%.exe
if exist "%APP_PATH%" (
  echo ✅ 打包成功：%APP_PATH%
) else (
  echo ❌ 未找到打包产物，请检查输出
)

pause
exit /b 0

:error
echo ❌ 打包失败
pause
exit /b 1
