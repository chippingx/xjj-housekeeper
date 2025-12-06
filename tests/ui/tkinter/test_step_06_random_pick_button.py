import tkinter as tk

import pytest


def _find_first_entry(widget: tk.Widget):
    """在给定容器下递归查找第一个 tk.Entry。"""
    try:
        children = widget.winfo_children()
    except Exception:
        return None

    for child in children:
        if isinstance(child, tk.Entry):
            return child
        nested = _find_first_entry(child)
        if nested is not None:
            return nested
    return None


def _find_button_by_text(widget: tk.Widget, text: str):
    """递归查找指定文本的按钮。"""
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


def _find_treeview(widget: tk.Widget):
    """递归查找第一个 Treeview 组件。"""
    try:
        children = widget.winfo_children()
    except Exception:
        return None

    for child in children:
        # 通过 tk.ttk.Treeview 类型判断（与现有测试保持一致风格）
        if isinstance(child, tk.ttk.Treeview):
            return child
        nested = _find_treeview(child)
        if nested is not None:
            return nested
    return None


def test_random_pick_button_exists():
    """验证查询页面存在“随机挑选”按钮。"""
    try:
        from ui.tkinter.app import XJJDesktopApp
    except Exception as exc:  # pragma: no cover - Tk 初始化失败等
        pytest.skip(f"Tkinter 应用初始化失败，跳过测试：{exc}")

    app = None
    try:
        try:
            app = XJJDesktopApp()
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Tkinter 应用构造失败，跳过测试：{exc}")

        app.show_query_page()
        btn = _find_button_by_text(app.content_inner, "随机挑选")
        assert btn is not None, "未找到‘随机挑选’按钮"
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass


def test_random_pick_uses_service_and_renders_rows(monkeypatch):
    """验证点击“随机挑选”会调用服务并渲染结果。"""
    try:
        from ui.tkinter.app import XJJDesktopApp, random_videos
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Tkinter 应用初始化失败，跳过测试：{exc}")

    app = None
    try:
        try:
            app = XJJDesktopApp()
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Tkinter 应用构造失败，跳过测试：{exc}")

        # 先切到查询页面，确保按钮和表格都已创建
        app.show_query_page()

        # 查找表格和按钮
        table = _find_treeview(app.content_inner)
        assert table is not None, "未找到结果表格"
        btn = _find_button_by_text(app.content_inner, "随机挑选")
        assert btn is not None, "未找到‘随机挑选’按钮"

        calls = []

        def fake_random_videos(limit: int = 20, ensure_accessible: bool = True):
            calls.append({"limit": limit, "ensure_accessible": ensure_accessible})
            return [
                {
                    "video": "RANDOM-001",
                    "file_path": "/tmp/random1.mp4",
                    "file_size": "100M",
                    "duration": "00:10:00",
                    "resolution": "1920x1080",
                },
                {
                    "video": "RANDOM-002",
                    "file_path": "/tmp/random2.mp4",
                    "file_size": "200M",
                    "duration": "00:20:00",
                    "resolution": "1280x720",
                },
            ]

        # 打补丁到 tkinter app 模块级别的 random_videos
        monkeypatch.setattr("ui.tkinter.app.random_videos", fake_random_videos)

        # 点击“随机挑选”按钮
        btn.invoke()

        # 至少应调用一次，并使用我们预期的参数
        assert calls, "random_videos 未被调用"
        assert calls[0]["limit"] == 20
        assert calls[0]["ensure_accessible"] is True

        # 表格中应渲染出我们的两条随机数据
        items = table.get_children()
        assert len(items) == 2
        first_values = table.item(items[0], "values")
        assert first_values[0] == "RANDOM-001"
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
