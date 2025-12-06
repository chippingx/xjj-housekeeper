import tkinter as tk

import pytest


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


def test_choose_dir_uses_current_scan_path_as_initialdir(tmp_path, monkeypatch):
    """当扫描路径输入框已有有效目录时，选择目录对话框应以此作为初始目录。"""
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

        app.show_maintain_page()

        # 在扫描路径输入框中预填一个存在的目录
        current_dir = str(tmp_path)
        app.scan_dir_var.set(current_dir)

        # 记录 askdirectory 调用的参数
        called_kwargs = {}

        def fake_askdirectory(**kwargs):
            called_kwargs.update(kwargs)
            # 模拟用户选择了子目录
            return str(tmp_path / "chosen")

        # 确保 isdir 对我们预设的路径返回 True
        monkeypatch.setattr("ui.tkinter.app.os.path.isdir", lambda p: True)
        monkeypatch.setattr("ui.tkinter.app.filedialog.askdirectory", fake_askdirectory)

        # 触发“选择目录”按钮
        btn = _find_button_by_text(app.content_inner, "选择目录")
        assert btn is not None, "未找到‘选择目录’按钮"
        btn.invoke()

        # 验证 initialdir 使用当前输入框内的路径
        assert called_kwargs.get("initialdir") == current_dir
        # 验证输入框与 last_scan_dir 被更新为返回值
        expected_selected = str(tmp_path / "chosen")
        assert app.scan_dir_var.get() == expected_selected
        assert app._last_scan_dir == expected_selected
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass


def test_choose_dir_falls_back_to_last_scan_dir(tmp_path, monkeypatch):
    """当输入框为空时，选择目录对话框应回退到上一次停留目录。"""
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

        app.show_maintain_page()

        # 清空输入框，但预设 last_scan_dir
        app.scan_dir_var.set("")
        last_dir = str(tmp_path)
        app._last_scan_dir = last_dir

        called_kwargs = {}

        def fake_askdirectory(**kwargs):
            called_kwargs.update(kwargs)
            return last_dir

        monkeypatch.setattr("ui.tkinter.app.os.path.isdir", lambda p: True)
        monkeypatch.setattr("ui.tkinter.app.filedialog.askdirectory", fake_askdirectory)

        btn = _find_button_by_text(app.content_inner, "选择目录")
        assert btn is not None, "未找到‘选择目录’按钮"
        btn.invoke()

        assert called_kwargs.get("initialdir") == last_dir
        assert app.scan_dir_var.get() == last_dir
        assert app._last_scan_dir == last_dir
    finally:
        if app is not None:
            try:
                app.root.destroy()
            except Exception:
                pass
