@echo off
REM XJJ Housekeeper - Windows 启动脚本（原生 Tkinter 客户端）
setlocal enabledelayedexpansion

REM 定位到项目根目录（startup 上一级）
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%.." || goto :error

REM 优先使用 python，其次使用 py -3
where python >nul 2>nul && (
  python ui\tkinter\app.py
) || (
  py -3 ui\tkinter\app.py
)

goto :eof

:error
echo [ERROR] 无法定位项目根目录。
pause
exit /b 1