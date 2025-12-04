import os
import tkinter as tk
from pathlib import Path

import pytest


def _find_button_by_text(widget: tk.Widget, text: str):
    """递归查找指定文本的按钮"""
    try:
        children = widget.winfo_children()
    except Exception:
        return None
    for child in children:
        if isinstance(child, tk.Button) and child.cget("text") == text:
            return child
        found = _find_button_by_text(child, text)
        if found:
            return found
    return None


def test_filename_adjustment_button_exists():
    """验证维护页面存在“文件名调整”按钮"""
    try:
        from ui.tkinter.app import XJJDesktopApp
        app = XJJDesktopApp()
    except Exception as e:
        pytest.skip(f"Tkinter 初始化失败，跳过UI按钮测试：{e}")

    try:
        app.show_maintain_page()
        btn = _find_button_by_text(app.content_inner, "文件名调整")
        assert btn is not None, "未找到‘文件名调整’按钮"
    finally:
        # 关闭窗口以避免阻塞或资源泄漏
        try:
            app.root.destroy()
        except Exception:
            pass


def test_run_filename_adjustment_preview(tmp_path: Path, monkeypatch):
    """验证辅助函数封装 filename_formatter 的预览行为"""
    # 使用较小的最小文件大小，以便测试小文件
    monkeypatch.setenv("MIN_VIDEO_SIZE_BYTES", "1")

    # 创建示例文件（将被格式化为 ABC-123.mp4）
    sample = tmp_path / "abc123.mp4"
    sample.write_bytes(b"a")

    from ui.tkinter.app import run_filename_adjustment

    result = run_filename_adjustment(
        base_path=str(tmp_path),
        include_subdirs=False,
        flatten_output=False,
        dry_run=True,  # 预览模式，不实际重命名
        log_operations=False,
    )

    summary = result["summary"]
    logs = result["log_lines"]

    # 应至少有一条预览记录
    assert summary["preview"] >= 1
    assert any("preview" in line for line in logs)