import tkinter as tk

import pytest


def _find_treeview(widget: tk.Widget):
    """递归查找第一个 Treeview 组件。"""
    try:
        children = widget.winfo_children()
    except Exception:
        return None

    for child in children:
        # 与现有测试保持风格，使用 tk.ttk.Treeview 判断
        if isinstance(child, tk.ttk.Treeview):
            return child
        nested = _find_treeview(child)
        if nested is not None:
            return nested
    return None


def _get_table_order(table: "tk.ttk.Treeview"):
    """返回当前表格中首列（视频）值的顺序列表。"""
    order = []
    for item_id in table.get_children():
        values = table.item(item_id, "values")
        if values:
            order.append(values[0])
    return order


def test_sort_by_file_size_stable_and_toggle_direction():
    """按大小列排序：默认升序，再次点击降序，并且相同值保持当前顺序。"""
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

        # 进入查询页并获取表格
        app.show_query_page()
        table = _find_treeview(app.content_inner)
        assert table is not None, "未找到结果表格"

        # 构造测试数据：B、C 的大小相同，用于验证稳定性
        rows = [
            {
                "video": "AAA-001",
                "file_path": "/a",
                "file_size": "100M",
                "duration": "00:10:00",
                "resolution": "1280x720",
            },
            {
                "video": "BBB-001",
                "file_path": "/b",
                "file_size": "200M",
                "duration": "00:05:00",
                "resolution": "1920x1080",
            },
            {
                "video": "CCC-001",
                "file_path": "/c",
                "file_size": "200M",
                "duration": "00:05:00",
                "resolution": "1920x1080",
            },
        ]

        # 使用应用自身的渲染逻辑填充表格
        app._render_table(table, rows)
        assert _get_table_order(table) == ["AAA-001", "BBB-001", "CCC-001"]

        # 第一次排序：按大小升序
        app._sort_table(table, "file_size")
        order_after_first_sort = _get_table_order(table)
        # 100M, 200M, 200M；且 BBB 仍在 CCC 之前
        assert order_after_first_sort == ["AAA-001", "BBB-001", "CCC-001"]

        # 第二次排序：再次点击同一列，切换为降序
        app._sort_table(table, "file_size")
        order_after_second_sort = _get_table_order(table)
        # 200M, 200M, 100M；且两条 200M 的顺序仍是 BBB, CCC
        assert order_after_second_sort == ["BBB-001", "CCC-001", "AAA-001"]

    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass


def test_sort_by_duration_and_resolution():
    """验证按时长和分辨率列排序时，数值解析正确且排序稳定。"""
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

        rows = [
            {
                "video": "VID-001",
                "file_path": "/a",
                "file_size": "150M",
                "duration": "00:10:00",
                "resolution": "1280x720",
            },
            {
                "video": "VID-002",
                "file_path": "/b",
                "file_size": "150M",
                "duration": "01:00:00",
                "resolution": "1920x1080",
            },
            {
                "video": "VID-003",
                "file_path": "/c",
                "file_size": "150M",
                "duration": "00:05:00",
                "resolution": "640x480",
            },
        ]

        app._render_table(table, rows)

        # 按时长升序：5 分钟, 10 分钟, 60 分钟
        app._sort_table(table, "duration")
        assert _get_table_order(table) == ["VID-003", "VID-001", "VID-002"]

        # 按分辨率升序：以 (width, height) 排序 -> 640x480, 1280x720, 1920x1080
        app._sort_table(table, "resolution")
        assert _get_table_order(table) == ["VID-003", "VID-001", "VID-002"]

        # 再次按分辨率排序应变为降序
        app._sort_table(table, "resolution")
        assert _get_table_order(table) == ["VID-002", "VID-001", "VID-003"]

    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass


def test_sort_header_indicator_updates():
    """验证表头排序箭头指示：同一列在 ↑/↓ 间切换，切换列时旧列箭头清除。"""
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

        # 初始表头文本不应包含箭头
        assert table.heading("file_size", "text") == "大小"
        assert table.heading("duration", "text") == "时长"

        # 按大小升序
        app._sort_table(table, "file_size")
        assert table.heading("file_size", "text") == "大小 ↑"
        # 其他列应保持原文字，不带箭头
        assert table.heading("duration", "text") == "时长"

        # 按大小再排序一次，应切换为降序箭头
        app._sort_table(table, "file_size")
        assert table.heading("file_size", "text") == "大小 ↓"

        # 切换到按时长排序，大小列箭头应被移除，时长列出现箭头
        app._sort_table(table, "duration")
        assert table.heading("duration", "text") == "时长 ↑"
        assert table.heading("file_size", "text") == "大小"

    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
