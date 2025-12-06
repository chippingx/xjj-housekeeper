import tkinter as tk

import pytest


def _find_treeview(widget: tk.Widget):
    """递归查找第一个 Treeview 组件。"""
    try:
        children = widget.winfo_children()
    except Exception:
        return None

    for child in children:
        if isinstance(child, tk.ttk.Treeview):
            return child
        nested = _find_treeview(child)
        if nested is not None:
            return nested
    return None


def test_query_table_includes_tags_column_and_renders_tags():
    """查询结果表格应包含“标签”列，并正确渲染标签文本。"""
    try:
        from ui.tkinter.app import XJJDesktopApp
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Tkinter 应用初始化失败，跳过测试：{exc}")

    app = None
    try:
        try:
            app = XJJDesktopApp()
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Tkinter 应用构造失败，跳过测试：{exc}")

        app.show_query_page()
        table = _find_treeview(app.content_inner)
        assert table is not None, "未找到结果表格"

        # 验证列顺序包含 video -> tags -> file_path ...
        columns = list(table["columns"])
        assert columns[:2] == ["video", "tags"], f"前两列应为 video、tags，当前为: {columns[:2]}"

        # 构造一行带标签的数据，并通过 _render_table 渲染
        rows = [
            {
                "video": "VID-TAGS-001",
                "tags": "标签A, 标签B",
                "file_path": "/path/to/video/file.mp4",
                "file_size": "100M",
                "duration": "00:10:00",
                "resolution": "1920x1080",
            }
        ]

        app._render_table(table, rows)

        items = table.get_children()
        assert len(items) == 1
        values = table.item(items[0], "values")

        # 校验列值顺序：视频码、标签、目录路径、大小、时长、分辨率
        assert values[0] == "VID-TAGS-001"
        assert values[1] == "标签A, 标签B"
        assert values[2] == "/path/to/video"
        assert values[3] == "100M"
        assert values[4] == "00:10:00"
        assert values[5] == "1920x1080"
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
