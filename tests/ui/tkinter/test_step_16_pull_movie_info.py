
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock
import threading

def _find_button_by_text(widget: tk.Widget, text: str):
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

def _find_notebook(widget: tk.Widget):
    try:
        children = widget.winfo_children()
    except Exception:
        return None
    for child in children:
        if isinstance(child, ttk.Notebook):
            return child
        nested = _find_notebook(child)
        if nested is not None:
            return nested
    return None

def _select_tab_by_text(widget: tk.Widget, text: str):
    notebook = _find_notebook(widget)
    if notebook is None:
        return False
    for tab_id in notebook.tabs():
        if notebook.tab(tab_id, "text") == text:
            notebook.select(tab_id)
            return True
    return False

def test_movie_info_buttons_include_import_export(monkeypatch):
    from ui.tkinter.app import XJJDesktopApp
    
    # Mock MovieDataCaptureService to ensure page is rendered
    MockServiceClass = MagicMock()
    monkeypatch.setattr("ui.tkinter.app.MovieDataCaptureService", MockServiceClass)
    
    app = XJJDesktopApp()
    app.show_page("maintain")
    
    # Switch to movie_info tab
    assert _select_tab_by_text(app.pages["maintain"], "影视资讯")
    app.root.update()
    
    btn_pull = _find_button_by_text(app.pages["maintain"], "拉取讯息")
    assert btn_pull is None, "应移除'拉取讯息'按钮"
    
    btn_import = _find_button_by_text(app.pages["maintain"], "导入")
    btn_export = _find_button_by_text(app.pages["maintain"], "导出")
    assert btn_import is not None, "未找到'导入'按钮"
    assert btn_export is not None, "未找到'导出'按钮"
    
    app.root.destroy()

def test_import_button_triggers_service(monkeypatch):
    from ui.tkinter.app import XJJDesktopApp
    
    # Mock Service Class
    MockServiceClass = MagicMock()
    mock_instance = MockServiceClass.return_value
    mock_instance.import_movie_info_file.return_value = {
        "total": 2,
        "imported": 2,
        "skipped": 0,
        "invalid_date": 0,
    }
    
    monkeypatch.setattr("ui.tkinter.app.MovieDataCaptureService", MockServiceClass)
    
    # Mock Toplevel
    mock_toplevel = MagicMock()
    monkeypatch.setattr("tkinter.Toplevel", mock_toplevel)
    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda **kwargs: "/tmp/data.csv")
    monkeypatch.setattr("tkinter.messagebox.showinfo", MagicMock())
    
    # Mock Threading to run synchronously
    def mock_start(self):
        self._target()
    monkeypatch.setattr(threading.Thread, "start", mock_start)
    
    app = XJJDesktopApp()
    app.show_page("maintain")
    assert _select_tab_by_text(app.pages["maintain"], "影视资讯")
    app.root.update()
    
    btn_import = _find_button_by_text(app.pages["maintain"], "导入")
    assert btn_import is not None
    btn_import.invoke()
    
    mock_instance.import_movie_info_file.assert_called_once_with("/tmp/data.csv")
    
    app.root.destroy()

def test_export_button_triggers_service(monkeypatch):
    from ui.tkinter.app import XJJDesktopApp
    
    # Mock Service Class
    MockServiceClass = MagicMock()
    mock_instance = MockServiceClass.return_value
    mock_instance.export_movie_info_file.return_value = {"total": 3}
    
    monkeypatch.setattr("ui.tkinter.app.MovieDataCaptureService", MockServiceClass)
    
    # Mock Toplevel
    mock_toplevel = MagicMock()
    monkeypatch.setattr("tkinter.Toplevel", mock_toplevel)
    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **kwargs: "/tmp/export.csv")
    monkeypatch.setattr("tkinter.messagebox.showinfo", MagicMock())
    
    # Mock Threading to run synchronously
    def mock_start(self):
        self._target()
    monkeypatch.setattr(threading.Thread, "start", mock_start)
    
    app = XJJDesktopApp()
    app.show_page("maintain")
    assert _select_tab_by_text(app.pages["maintain"], "影视资讯")
    app.root.update()
    
    btn_export = _find_button_by_text(app.pages["maintain"], "导出")
    assert btn_export is not None
    btn_export.invoke()
    
    mock_instance.export_movie_info_file.assert_called_once_with("/tmp/export.csv")
    
    app.root.destroy()
