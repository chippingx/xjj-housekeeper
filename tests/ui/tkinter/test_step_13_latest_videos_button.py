from pathlib import Path
import tkinter as tk
from tkinter import ttk

import pytest


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


def test_latest_videos_button_renders_sorted_by_file_size_desc(monkeypatch, tmp_path: Path):
    try:
        from ui.tkinter.app import XJJDesktopApp
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Tkinter 应用初始化失败，跳过测试：{exc}")

    app = None
    try:
        app = XJJDesktopApp()
        app.show_page("query")
        table = _find_treeview(app.pages["query"])
        assert table is not None, "未找到结果表格"

        button = _find_button_by_text(app.pages["query"], "最新视频")
        assert button is not None, "未找到“最新视频”按钮"

        f1 = tmp_path / "a.mp4"
        f2 = tmp_path / "b.mp4"
        f3 = tmp_path / "c.mp4"
        for f in (f1, f2, f3):
            f.write_bytes(b"0")

        rows = [
            {"video": "VID-L-001", "tags": "T1", "file_path": str(f1), "file_size": "100M"},
            {"video": "VID-L-002", "tags": "T2", "file_path": str(f2), "file_size": "2G"},
            {"video": "VID-L-003", "tags": "T3", "file_path": str(f3), "file_size": "900M"},
        ]

        calls = {}

        def fake_latest_videos(*, days: int = 14, limit: int = 20, ensure_accessible: bool = True):
            calls["days"] = days
            calls["limit"] = limit
            calls["ensure_accessible"] = ensure_accessible
            return rows

        monkeypatch.setattr("ui.tkinter.app.latest_videos", fake_latest_videos)

        button.invoke()
        app.root.update_idletasks()

        assert calls == {"days": 14, "limit": 20, "ensure_accessible": True}

        item_ids = table.get_children()
        assert len(item_ids) == 3
        values0 = table.item(item_ids[0], "values")
        values1 = table.item(item_ids[1], "values")
        values2 = table.item(item_ids[2], "values")

        assert values0[0] == "VID-L-002"
        assert values1[0] == "VID-L-003"
        assert values2[0] == "VID-L-001"
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass

