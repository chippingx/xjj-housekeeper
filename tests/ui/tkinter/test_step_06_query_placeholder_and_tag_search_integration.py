import tkinter as tk

import pytest


def _find_first_entry(widget: tk.Widget):
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


def test_query_input_has_placeholder_and_no_label_video_code():
    """查询页输入框默认展示 placeholder，且不再有“视频码”标签。"""
    try:
        from ui.tkinter.app import XJJDesktopApp
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Tkinter 应用初始化失败，跳过测试：{exc}")

    app = None
    try:
        app = XJJDesktopApp()
        app.show_query_page()

        # 页面上应该能找到输入框
        entry = _find_first_entry(app.content_inner)
        assert entry is not None, "未在查询页找到输入框"

        # 默认值应为 placeholder 文本
        assert app.query_var.get() == "视频号/标签"

        # 检查没有文字为“视频码”的标签控件
        def _has_label_with_text(root, text: str) -> bool:
            try:
                children = root.winfo_children()
            except Exception:
                return False
            for child in children:
                if isinstance(child, tk.Label) and child.cget("text") == text:
                    return True
                if _has_label_with_text(child, text):
                    return True
            return False

        assert not _has_label_with_text(app.content_inner, "视频码"), "应移除旧的“视频码”标签"
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass


def test_query_placeholder_does_not_trigger_search(monkeypatch):
    """占位符文本不应触发实际搜索（视为空输入）。"""
    try:
        from ui.tkinter.app import XJJDesktopApp
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Tkinter 应用初始化失败，跳过测试：{exc}")

    app = None
    try:
        app = XJJDesktopApp()

        seen_keywords = []

        def fake_search_videos(keyword: str):
            seen_keywords.append(keyword)
            return []

        monkeypatch.setattr("ui.tkinter.app.search_videos", fake_search_videos)

        app.show_query_page()
        # 初始时 query_var 是占位符文本
        assert app.query_var.get() == "视频号/标签"

        # 触发一次实时搜索逻辑
        app.query_var.set("视频号/标签")

        # 不应调用 search_videos
        assert not seen_keywords, "占位符文本不应触发搜索"
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
