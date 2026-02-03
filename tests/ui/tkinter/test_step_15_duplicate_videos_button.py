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

def _find_notebook(widget: tk.Widget):
    try:
        children = widget.winfo_children()
    except Exception:
        return None
    for child in children:
        if isinstance(child, ttk.Notebook):
            return child
        nested = _find_notebook(child)
        if nested is not None:
            return nested
    return None

def _select_tab_by_text(widget: tk.Widget, text: str):
    notebook = _find_notebook(widget)
    if notebook is None:
        return False
    for tab_id in notebook.tabs():
        if notebook.tab(tab_id, "text") == text:
            notebook.select(tab_id)
            return True
    return False


def _find_toplevel(root: tk.Tk, title: str):
    for child in root.winfo_children():
        if isinstance(child, tk.Toplevel) and child.title() == title:
            return child
    return None


def _find_treeview(widget: tk.Widget):
    matches: list[ttk.Treeview] = []

    def walk(w: tk.Widget):
        try:
            children = w.winfo_children()
        except Exception:
            return
        for child in children:
            if isinstance(child, ttk.Treeview):
                matches.append(child)
            walk(child)

    walk(widget)
    for tv in matches:
        try:
            cols = list(tv["columns"])
        except Exception:
            cols = []
        if "file_path" in cols:
            return tv
    return matches[0] if matches else None


def test_maintain_duplicate_videos_button_opens_window_and_sorts(monkeypatch, tmp_path: Path):
    try:
        from ui.tkinter.app import XJJDesktopApp
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Tkinter 应用初始化失败，跳过测试：{exc}")

    app = None
    try:
        app = XJJDesktopApp()
        app.show_page("maintain")
        assert _select_tab_by_text(app.pages["maintain"], "问题视频")
        # app.root.update()

        button = _find_button_by_text(app.pages["maintain"], "重复视频")
        assert button is not None, "未找到“重复视频”按钮"

        f1 = tmp_path / "dup1.mp4"
        f2 = tmp_path / "dup2.mp4"
        for f in (f1, f2):
            f.write_bytes(b"0")

        # 模拟 duplicate_videos 返回结果
        rows = [
            {"video": "DUP-001", "tags": "", "file_path": str(f1), "file_size": "100M", "duration": "00:01:00", "resolution": ""},
            {"video": "DUP-002", "tags": "", "file_path": str(f2), "file_size": "100M", "duration": "00:01:00", "resolution": ""},
        ]

        class MockVideoService:
            def __init__(self, db_path=None):
                pass
            def duplicate_videos(self, ensure_accessible=True):
                return rows
        
        monkeypatch.setattr("ui.services.VideoService", MockVideoService)

        button.invoke()
        
        import time
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

        columns = list(table["columns"])
        assert "file_size" in columns
        idx = columns.index("file_size")
        assert values0[idx] == "100M"
        assert values1[idx] == "100M"

    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
