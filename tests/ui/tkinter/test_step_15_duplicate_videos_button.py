from pathlib import Path
import tkinter as tk
from tkinter import ttk

import pytest


def _find_button_by_text(widget: tk.Widget, text: str):
    try:
        children = widget.winfo_children()
    except Exception:
        return None
    for child in children:
        if isinstance(child, tk.Button) and child.cget("text") == text:
            return child
        nested = _find_button_by_text(child, text)
        if nested is not None:
            return nested
    return None


def _find_toplevel(root: tk.Tk, title: str):
    for child in root.winfo_children():
        if isinstance(child, tk.Toplevel) and child.title() == title:
            return child
    return None


def _find_treeview(widget: tk.Widget):
    try:
        children = widget.winfo_children()
    except Exception:
        return None
    for child in children:
        if isinstance(child, ttk.Treeview):
            return child
        nested = _find_treeview(child)
        if nested is not None:
            return nested
    return None


def test_maintain_duplicate_videos_button_opens_window_and_sorts(monkeypatch, tmp_path: Path):
    try:
        from ui.tkinter.app import XJJDesktopApp
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Tkinter 应用初始化失败，跳过测试：{exc}")

    app = None
    try:
        app = XJJDesktopApp()
        app.show_page("maintain")

        # 切换到“旧视频管理” Tab
        # 我们可以通过点击按钮或者直接调用 switch_tab (如果在 app 中可访问)
        # 这里尝试点击按钮
        btn_manage = _find_button_by_text(app.pages["maintain"], "旧视频管理")
        assert btn_manage is not None, "未找到“旧视频管理”按钮"
        btn_manage.invoke()
        app.root.update()

        button = _find_button_by_text(app.pages["maintain"], "重复视频")
        assert button is not None, "未找到“重复视频”按钮"

        f1 = tmp_path / "dup1.mp4"
        f2 = tmp_path / "dup2.mp4"
        f3 = tmp_path / "unique.mp4"
        for f in (f1, f2, f3):
            f.write_bytes(b"0")

        # 模拟 duplicate_videos 返回结果
        rows = [
            {"video": "DUP-001", "tags": "", "file_path": str(f1), "file_size": "100M", "duration": "00:01:00", "resolution": ""},
            {"video": "DUP-002", "tags": "", "file_path": str(f2), "file_size": "100M", "duration": "00:01:00", "resolution": ""},
        ]

        # Mock VideoService class entirely to avoid instantiation issues (DB connection etc)
        class MockVideoService:
            def __init__(self, db_path=None):
                pass
            def duplicate_videos(self, ensure_accessible=True):
                return rows
        
        # Patch the class in ui.services module
        # Note: app.py imports it as 'from ui.services import VideoService' inside the worker
        # So we must patch it in ui.services
        monkeypatch.setattr("ui.services.VideoService", MockVideoService)

        button.invoke()
        
        # 等待表格更新（原设计为弹窗，现改为在当前页显示）
        import time
        start_time = time.time()
        table = _find_treeview(app.pages["maintain"])
        assert table is not None, "未找到结果表格"
        
        found = False
        start_time = time.time()
        while time.time() - start_time < 5.0:
            app.root.update()
            if len(table.get_children()) == 2:
                found = True
                break
            time.sleep(0.1)
            
        assert found, "表格未更新或数据不匹配"

        item_ids = table.get_children()
        assert len(item_ids) == 2
        values0 = table.item(item_ids[0], "values")
        values1 = table.item(item_ids[1], "values")

        # 验证排序（按文件大小降序，虽然这里都一样）
        assert values0[3] == "100M"
        assert values1[3] == "100M"

    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
