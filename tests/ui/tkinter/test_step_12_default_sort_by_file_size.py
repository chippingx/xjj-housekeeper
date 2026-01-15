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


def test_search_results_default_sorted_by_file_size_desc(monkeypatch, tmp_path: Path):
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

        f1 = tmp_path / "a.mp4"
        f2 = tmp_path / "b.mp4"
        f3 = tmp_path / "c.mp4"
        for f in (f1, f2, f3):
            f.write_bytes(b"0")

        rows = [
            {"video": "VID-001", "tags": "T1", "file_path": str(f1), "file_size": "100M"},
            {"video": "VID-002", "tags": "T2", "file_path": str(f2), "file_size": "1G"},
            {"video": "VID-003", "tags": "T3", "file_path": str(f3), "file_size": "900M"},
        ]

        monkeypatch.setattr("ui.tkinter.app.search_videos", lambda _k: rows)

        app.query_var.set("VID")
        app.root.update_idletasks()

        item_ids = table.get_children()
        assert len(item_ids) == 3
        values0 = table.item(item_ids[0], "values")
        values1 = table.item(item_ids[1], "values")
        values2 = table.item(item_ids[2], "values")

        assert values0[0] == "VID-002"
        assert values1[0] == "VID-003"
        assert values2[0] == "VID-001"
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass


def test_random_pick_default_sorted_by_file_size_desc(monkeypatch, tmp_path: Path):
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

        button = _find_button_by_text(app.pages["query"], "随机挑选")
        assert button is not None, "未找到“随机挑选”按钮"

        f1 = tmp_path / "a.mp4"
        f2 = tmp_path / "b.mp4"
        f3 = tmp_path / "c.mp4"
        for f in (f1, f2, f3):
            f.write_bytes(b"0")

        rows = [
            {"video": "VID-R-001", "tags": "T1", "file_path": str(f1), "file_size": "2G"},
            {"video": "VID-R-002", "tags": "T2", "file_path": str(f2), "file_size": "1500M"},
            {"video": "VID-R-003", "tags": "T3", "file_path": str(f3), "file_size": "800M"},
        ]

        monkeypatch.setattr("ui.tkinter.app.random_videos", lambda **_kwargs: rows)

        button.invoke()
        app.root.update_idletasks()

        item_ids = table.get_children()
        assert len(item_ids) == 3
        values0 = table.item(item_ids[0], "values")
        values1 = table.item(item_ids[1], "values")
        values2 = table.item(item_ids[2], "values")

        assert values0[0] == "VID-R-001"
        assert values1[0] == "VID-R-002"
        assert values2[0] == "VID-R-003"
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
