from types import SimpleNamespace
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


def _make_double_click_event(monkeypatch, table: ttk.Treeview, item_id: str, col_id: str):
    monkeypatch.setattr(ttk.Treeview, "identify_row", lambda _self, _y: item_id)
    monkeypatch.setattr(ttk.Treeview, "identify_column", lambda _self, _x: col_id)
    return SimpleNamespace(x=1, y=1, x_root=1, y_root=1)


def test_double_click_tags_column_does_not_open_dir(monkeypatch, tmp_path: Path):
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

        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"0")

        rows = [
            {
                "video": "VID-CLICK-001",
                "tags": "标签A",
                "file_path": str(video_file),
                "file_size": "1M",
                "duration": "00:00:01",
                "resolution": "1x1",
            }
        ]
        app._render_table(table, rows)
        app.root.update()
        item_ids = table.get_children()
        assert item_ids
        columns = list(table["columns"])
        tags_col_id = f"#{columns.index('tags') + 1}" if "tags" in columns else "#1"

        play_calls: list[str] = []

        monkeypatch.setattr(app, "_open_file_manager", lambda _path: pytest.fail("不应打开目录"))
        monkeypatch.setattr(app, "_play_video", lambda path: play_calls.append(path))

        event = _make_double_click_event(monkeypatch, table, item_ids[0], tags_col_id)

        app._on_table_double_click(table, event)  # type: ignore[arg-type]

        assert play_calls == [str(video_file)]
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass


def test_double_click_path_column_opens_dir(monkeypatch, tmp_path: Path):
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

        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"0")

        rows = [
            {
                "video": "VID-CLICK-002",
                "tags": "标签B",
                "file_path": str(video_file),
                "file_size": "1M",
                "duration": "00:00:01",
                "resolution": "1x1",
            }
        ]
        app._render_table(table, rows)
        app.root.update()
        item_ids = table.get_children()
        assert item_ids
        columns = list(table["columns"])
        path_col_id = f"#{columns.index('file_path') + 1}"

        open_calls: list[str] = []
        play_calls: list[str] = []

        monkeypatch.setattr(app, "_open_file_manager", lambda path: open_calls.append(path))
        monkeypatch.setattr(app, "_play_video", lambda path: play_calls.append(path))
        event = _make_double_click_event(monkeypatch, table, item_ids[0], path_col_id)

        app._on_table_double_click(table, event)  # type: ignore[arg-type]

        assert open_calls == [str(video_file)]
        assert play_calls == []
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
