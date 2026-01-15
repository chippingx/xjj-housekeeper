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


def test_maintain_broken_videos_button_opens_window_and_sorts(monkeypatch, tmp_path: Path):
    try:
        from ui.tkinter.app import XJJDesktopApp
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Tkinter 应用初始化失败，跳过测试：{exc}")

    app = None
    try:
        app = XJJDesktopApp()
        app.show_page("maintain")

        button = _find_button_by_text(app.pages["maintain"], "损坏视频")
        assert button is not None, "未找到“损坏视频”按钮"

        f1 = tmp_path / "a.mp4"
        f2 = tmp_path / "b.mp4"
        f3 = tmp_path / "c.mp4"
        for f in (f1, f2, f3):
            f.write_bytes(b"0")

        rows = [
            {"video": "BROKEN-001", "tags": "", "file_path": str(f1), "file_size": "100M", "duration": None, "resolution": ""},
            {"video": "BROKEN-002", "tags": "", "file_path": str(f2), "file_size": "2G", "duration": None, "resolution": ""},
            {"video": "BROKEN-003", "tags": "", "file_path": str(f3), "file_size": "900M", "duration": None, "resolution": ""},
        ]

        # 修改：由于 app.py 现在在线程中创建 VideoService 实例，
        # 我们需要 mock ui.services.VideoService.broken_videos 方法
        monkeypatch.setattr("ui.services.VideoService.broken_videos", lambda self, **_kwargs: rows)

        button.invoke()
        
        # 等待表格更新（原设计为弹窗，现改为在当前页显示）
        import time
        start_time = time.time()
        table = _find_treeview(app.pages["maintain"])
        assert table is not None, "未找到结果表格"
        
        found = False
        while time.time() - start_time < 2.0:
            app.root.update()
            if len(table.get_children()) == 3:
                found = True
                break
            time.sleep(0.1)
            
        assert found, "表格未更新或数据不匹配"

        item_ids = table.get_children()
        assert len(item_ids) == 3
        values0 = table.item(item_ids[0], "values")
        values1 = table.item(item_ids[1], "values")
        values2 = table.item(item_ids[2], "values")

        assert values0[0] == "BROKEN-001"
        assert values1[0] == "BROKEN-002"
        assert values2[0] == "BROKEN-003"
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass

