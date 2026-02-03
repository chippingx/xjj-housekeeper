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

        app.show_page("query")
        table = _find_treeview(app.pages["query"])
        assert table is not None, "未找到结果表格"

        columns = list(table["columns"])
        assert "tags" in columns, f"列中应包含 tags，当前为: {columns}"

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
        assert values[columns.index("video")] == "VID-TAGS-001"
        assert values[columns.index("tags")] == "标签A, 标签B"
        assert values[columns.index("file_path")] == "/path/to/video"
        if "file_size" in columns:
            assert values[columns.index("file_size")] == "100M"
        if "duration" in columns:
            assert values[columns.index("duration")] == "00:10:00"
        if "resolution" in columns:
            assert values[columns.index("resolution")] == "1920x1080"
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
