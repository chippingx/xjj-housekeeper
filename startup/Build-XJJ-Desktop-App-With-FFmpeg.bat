@echo off
REM Build Tkinter desktop app for Windows (PyInstaller)
setlocal enabledelayedexpansion

echo 📦 Building XJJ Desktop App (single-file)
echo =========================================

REM Locate project root (parent of startup)
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.." || goto :error

REM Requirements: Python + Poetry + PyInstaller
where python >nul 2>nul || (
  echo ❌ Missing python
  pause
  exit /b 1
)

where poetry >nul 2>nul || (
  echo ❌ Missing poetry
  pause
  exit /b 1
)

where ffprobe >nul 2>nul || (
  echo ❌ ffprobe not found; bundling is not possible
  echo Suggested: install FFmpeg and add ffprobe to PATH
  pause
  exit /b 1
)
where ffmpeg >nul 2>nul || (
  echo ❌ ffmpeg not found; bundling is not possible
  echo Suggested: install FFmpeg and add ffmpeg to PATH
  pause
  exit /b 1
)

echo 📦 Installing/checking dependencies (Poetry)...
poetry install --no-interaction || goto :error

poetry run pyinstaller --version >nul 2>nul || (
  echo 🧩 Installing PyInstaller...
  poetry add --group dev pyinstaller || goto :error
)

set XJJ_INCLUDE_FFMPEG=1
set NAME=XJJ-Housekeeper
set ICON_PATH=assets\icons\xjj.ico
set ICON_ARG=
if exist "%ICON_PATH%" (
  set ICON_ARG=--icon "%ICON_PATH%"
  echo 🎨 Using icon: %ICON_PATH%
) else (
  echo ℹ️ Icon not found (%ICON_PATH%), using default icon.
)

set ADD_DATA=
if exist "i18n" set ADD_DATA=%ADD_DATA% --add-data "i18n;i18n"
if exist "output" set ADD_DATA=%ADD_DATA% --add-data "output;output"
if exist "config\app_meta.json" set ADD_DATA=%ADD_DATA% --add-data "config\app_meta.json;config"
if exist "tools\video_info_collector\config.yaml" set ADD_DATA=%ADD_DATA% --add-data "tools\video_info_collector\config.yaml;tools\video_info_collector"
if exist "tools\filename_formatter\rename_rules.yaml" set ADD_DATA=%ADD_DATA% --add-data "tools\filename_formatter\rename_rules.yaml;tools\filename_formatter"

echo 🛠️ Building (with bundled ffmpeg/ffprobe)...
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
  echo ✅ Build succeeded: %APP_PATH%
) else (
  echo ❌ Build output not found; please check logs.
)

pause
exit /b 0

:error
echo ❌ Build failed
pause
exit /b 1
