import os
import shutil
import sqlite3
import subprocess

import pytest


def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def check_ffmpeg_available() -> dict:
    ffmpeg_ok = _which("ffmpeg")
    ffprobe_ok = _which("ffprobe")
    details = {}
    if ffmpeg_ok:
        try:
            out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
            details["ffmpeg_version"] = out.stdout.splitlines()[0] if out.stdout else ""
        except Exception as e:
            details["ffmpeg_error"] = str(e)
    if ffprobe_ok:
        try:
            out = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True, timeout=5)
            details["ffprobe_version"] = out.stdout.splitlines()[0] if out.stdout else ""
        except Exception as e:
            details["ffprobe_error"] = str(e)
    return {"ffmpeg": ffmpeg_ok, "ffprobe": ffprobe_ok, "details": details}


def check_sqlite_available() -> bool:
    try:
        # simple in-memory connection
        conn = sqlite3.connect(":memory:")
        conn.execute("select 1")
        conn.close()
        return True
    except Exception:
        return False


def test_dependencies_declared_in_poetry():
    # 确认 pyproject.toml 中声明了最低限度依赖
    pyproject = open("pyproject.toml", "r", encoding="utf-8").read()
    assert "streamlit" in pyproject, "必须在Poetry依赖中声明 streamlit"
    assert "pytest" in pyproject, "必须在Poetry dev/test 依赖中声明 pytest"
    assert "selenium" in pyproject, "必须加入 selenium 以支持UI自动化"


@pytest.mark.slow
@pytest.mark.parametrize("binary", ["ffmpeg", "ffprobe"])  # 允许在无安装时失败但给出提示
def test_ffmpeg_and_ffprobe_presence(binary):
    available = _which(binary)
    if not available:
        pytest.skip(f"{binary} 未安装，跳过（参考 design.md 安装指南）")
    assert available


def test_sqlite_available():
    assert check_sqlite_available() is True
