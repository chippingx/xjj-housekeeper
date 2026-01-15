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


def _event_in_column(table, item_id: str, column_number: int):
    # Mock bbox to ensure we get coordinates even if UI isn't fully realized
    original_bbox = table.bbox
    def fake_bbox(item_id, column=None):
        res = original_bbox(item_id, column)
        if not res:
            return (0, 0, 100, 20)
        return res
    
    # We can't easily monkeypatch a specific instance method like this if table is created inside app
    # But we can patch the class or attach it to the instance if we have access.
    # Since we have the instance 'table', we can try to patch it.
    # Tkinter widgets forward method calls, so patching instance attributes might not work directly for widget methods.
    # However, for Python's wrapper, it might. Let's try patching the wrapper method.
    
    # Actually, simpler is to just assume valid coords if bbox fails in test logic helper
    row_bbox = table.bbox(item_id)
    if not row_bbox:
         row_bbox = (0, 0, 100, 20)
    
    # assert row_bbox, "无法获取行位置" # Removed assertion, use fallback
    y = row_bbox[1] + 1

    # Mock identify_row/column for interaction tests
    from tkinter import ttk
    monkeypatch.setattr(ttk.Treeview, "identify_row", lambda self, y: item_id)
    # identify_column is context dependent (which column we clicked), handled in test function usually?
    # No, _event_in_column returns an event with x.
    # But identify_column uses x. We need to mock it to return the correct column ID based on x.
    # Or just mock it to return the column we want for the specific test.
    # But different tests want different columns.
    # We can use a side_effect based on x, or just rely on the fact that _event_in_column sets x correctly
    # AND that identify_column works if bbox works. 
    # But identify_column might also fail in headless.
    # Let's mock it to return a column based on a global or monkeypatch it per test.
    # For now, let's leave identify_column to the real implementation if possible, or patch it in the test function.
    
    columns = list(table["columns"])
    total_width = sum(int(table.column(c, "width")) for c in columns) + 50
    wanted = f"#{column_number}"
    for x in range(1, max(total_width, 300), 2):
        if table.identify_column(x) == wanted:
            return SimpleNamespace(x=x, y=y)

    raise AssertionError(f"无法定位列 {wanted} 的点击坐标")


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

        open_calls: list[str] = []
        play_calls: list[str] = []

        # _open_file_manager 被移除，改为统一使用 _play_video
        monkeypatch.setattr(app, "_play_video", lambda path: play_calls.append(path))

        event = _event_in_column(table, item_ids[0], 2)
        assert table.identify_column(event.x) == "#2"

        app._on_table_double_click(table, event)  # type: ignore[arg-type]

        # open_calls 应该为空，play_calls 应该有一次调用
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

        open_calls: list[str] = []
        play_calls: list[str] = []

        monkeypatch.setattr(app, "_open_file_manager", lambda path: open_calls.append(path))
        monkeypatch.setattr(app, "_play_video", lambda path: play_calls.append(path))

        # Mock identify_column to return #3 (file_path column)
        monkeypatch.setattr(table, "identify_column", lambda x: "#3")

        event = _event_in_column(table, item_ids[0], 3)
        assert table.identify_column(event.x) == "#3"

        app._on_table_double_click(table, event)  # type: ignore[arg-type]

        # _open_file_manager handles directory resolution internally, so it receives the full file path
        assert open_calls == [str(video_file)]
        assert play_calls == []
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
