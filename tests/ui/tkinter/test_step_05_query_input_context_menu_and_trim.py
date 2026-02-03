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


def test_query_input_trims_spaces_before_search(monkeypatch):
    """验证搜索时会自动去掉关键字前后的空格。"""
    try:
        from ui.tkinter.app import XJJDesktopApp
    except Exception as exc:  # pragma: no cover - Tk 初始化环境问题
        pytest.skip(f"Tkinter 应用初始化失败，跳过测试：{exc}")

    app = None
    try:
        try:
            app = XJJDesktopApp()
        except Exception as exc:  # pragma: no cover - Tk 后端不可用等情况
            pytest.skip(f"Tkinter 应用构造失败，跳过测试：{exc}")

        seen_keywords = []

        def fake_search_videos_paged(keyword: str, preference: str = "all", page: int = 1, page_size: int = 100):
            seen_keywords.append(keyword)
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        # 打补丁到 app 模块级别的 search_videos，使查询走到我们的桩函数
        monkeypatch.setattr("ui.tkinter.app.search_videos_paged", fake_search_videos_paged)

        # 切到查询页面并找到输入框
        app.show_page("query")
        entry = _find_first_entry(app.pages["query"])
        assert entry is not None, "未能在查询页找到输入框"

        # 方式 1：通过回车事件触发 do_search -> do_search_live
        # 注意：先清空占位符，否则 insert 会拼接在占位符前
        if app.query_var.get() == app.query_placeholder:
            entry.delete(0, tk.END)
            
        entry.insert(0, "  ABC123  ")
        # 手动同步 StringVar，确保 trace 或 get 能获取到最新值
        app.query_var.set(entry.get())
        entry.event_generate("<Return>")

        # 方式 2：直接修改 StringVar 触发 trace_add('write') 路径
        app.query_var.set("  DEF456  ")

        # 至少应有两次调用，且关键字都已去掉前后空格
        assert seen_keywords, "search_videos_paged 未被调用"
        for kw in seen_keywords:
            assert kw == kw.strip(), f"关键字前后空格未被去除: {kw!r}"

        # 同时确保具体值按预期被去空格
        assert "ABC123" in seen_keywords
        assert "DEF456" in seen_keywords
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass


def test_query_and_maintain_inputs_have_context_menu():
    """验证查询页和维护页的输入框均挂载了右键菜单并包含剪切/复制/粘贴。"""
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

        # 查询页输入框
        app.show_page("query")
        query_entry = _find_first_entry(app.pages["query"])
        assert query_entry is not None, "查询页未找到输入框"

        # _attach_entry_context_menu 会在 entry 上挂 _context_menu 属性
        assert hasattr(query_entry, "_context_menu"), "查询输入框未挂载上下文菜单属性"
        query_menu = getattr(query_entry, "_context_menu")
        assert isinstance(query_menu, tk.Menu), "查询输入框的上下文菜单类型不正确"

        # 菜单中应包含“剪切/复制/粘贴”三个选项
        labels = [
            query_menu.entrycget(i, "label")
            for i in range(query_menu.index("end") + 1)
        ]
        for expected in ("剪切", "复制", "粘贴"):
            assert expected in labels, f"查询输入框菜单缺少选项：{expected}"

        # 检查右键绑定存在（不同平台可能对应 Button-3 / Button-2 / Control-Button-1）
        assert query_entry.bind("<Button-3>") or query_entry.bind("<Button-2>") or query_entry.bind("<Control-Button-1>"), (
            "查询输入框未绑定任一右键菜单事件"
        )

        # 维护页输入框
        app.show_page("maintain")
        maintain_entry = _find_first_entry(app.pages["maintain"])
        assert maintain_entry is not None, "维护页未找到输入框"
        assert hasattr(maintain_entry, "_context_menu"), "维护输入框未挂载上下文菜单属性"
        maintain_menu = getattr(maintain_entry, "_context_menu")
        assert isinstance(maintain_menu, tk.Menu), "维护输入框的上下文菜单类型不正确"

        labels = [
            maintain_menu.entrycget(i, "label")
            for i in range(maintain_menu.index("end") + 1)
        ]
        for expected in ("剪切", "复制", "粘贴"):
            assert expected in labels, f"维护输入框菜单缺少选项：{expected}"

    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
