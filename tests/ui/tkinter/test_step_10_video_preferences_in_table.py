import tkinter as tk
from types import SimpleNamespace

import pytest


def _find_treeview(widget: tk.Widget):
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


def test_right_click_menu_has_preference_actions_and_updates_row(monkeypatch):
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

        # 填充一条记录
        rows = [
            {
                "video": "TST-001",
                "file_path": "/tmp/tst001.mp4",
                "file_size": "100M",
                "duration": "00:10:00",
                "resolution": "1920x1080",
            }
        ]
        app._render_table(table, rows)
        item_ids = table.get_children()
        assert item_ids
        first_item = item_ids[0]

        # 打补丁服务层 set_video_preference
        calls: list[tuple[str, str | None]] = []

        def fake_set_video_preference(code: str, status: str | None):  # noqa: ANN001
            calls.append((code, status))

        monkeypatch.setattr("ui.tkinter.app.set_video_preference", fake_set_video_preference)

        monkeypatch.setattr(table, "identify_row", lambda _y: first_item)
        monkeypatch.setattr(tk.Menu, "tk_popup", lambda _self, _x, _y: None)
        event = SimpleNamespace(x=5, y=5, x_root=5, y_root=5)

        app._on_table_right_click(table, event)  # type: ignore[arg-type]

        menu = getattr(table, "_context_menu", None)
        assert isinstance(menu, tk.Menu), "右键菜单未挂载到表格 _context_menu"

        # 菜单前几项应为偏好相关动作
        labels = [menu.entrycget(i, "label") for i in range(3)]
        assert labels == ["标记为喜欢", "标记为不喜欢 (Trash)", "清除偏好"]

        # 触发“标记为喜欢”
        menu.invoke(0)

        assert calls and calls[0] == ("TST-001", "like")

        # 行应被打上喜欢的 tag 且“偏好”列显示“喜欢”
        columns = list(table["columns"])
        assert "preference" in columns
        pref_idx = columns.index("preference")
        values = table.item(first_item, "values")
        assert values[pref_idx] == "喜欢"
        assert "pref_like" in table.item(first_item, "tags")
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
