
import tkinter as tk
from tkinter import ttk
import pytest
from unittest.mock import MagicMock, patch
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

def test_pull_info_button_exists_and_handles_empty_input(monkeypatch):
    from ui.tkinter.app import XJJDesktopApp
    
    # Mock MovieDataCaptureService to ensure page is rendered
    MockServiceClass = MagicMock()
    monkeypatch.setattr("ui.tkinter.app.MovieDataCaptureService", MockServiceClass)
    
    # Mock Toplevel
    mock_toplevel = MagicMock()
    monkeypatch.setattr("tkinter.Toplevel", mock_toplevel)
    
    app = XJJDesktopApp()
    app.show_page("maintain")
    
    # Switch to movie_info tab
    assert _select_tab_by_text(app.pages["maintain"], "影视资讯")
    app.root.update()
    
    # Find Pull Info button
    btn_pull = _find_button_by_text(app.pages["maintain"], "拉取讯息")
    assert btn_pull is not None, "未找到'拉取讯息'按钮"
    
    # Mock messagebox
    mock_msg = MagicMock()
    monkeypatch.setattr("tkinter.messagebox.showwarning", mock_msg)
    
    # Clear input
    app.movie_info_keyword.set("")
    
    btn_pull.invoke()
    
    mock_msg.assert_called_once()
    args, _ = mock_msg.call_args
    assert "请输入查询关键字" in args[1]
    
    app.root.destroy()

def test_pull_info_logic_video_code(monkeypatch):
    from ui.tkinter.app import XJJDesktopApp
    
    # Mock Service Class
    MockServiceClass = MagicMock()
    mock_instance = MockServiceClass.return_value
    mock_instance.search_movie_info.return_value = []
    
    monkeypatch.setattr("ui.tkinter.app.MovieDataCaptureService", MockServiceClass)
    
    # Mock Toplevel
    mock_toplevel = MagicMock()
    monkeypatch.setattr("tkinter.Toplevel", mock_toplevel)
    
    # Mock Threading to run synchronously
    def mock_start(self):
        self._target()
    monkeypatch.setattr(threading.Thread, "start", mock_start)
    
    app = XJJDesktopApp()
    app.show_page("maintain")
    assert _select_tab_by_text(app.pages["maintain"], "影视资讯")
    app.root.update()
    
    btn_pull = _find_button_by_text(app.pages["maintain"], "拉取讯息")
    assert btn_pull is not None
    
    # Test Video Code
    app.movie_info_keyword.set("ABC-123")
    btn_pull.invoke()
    
    # Verify search_movie_info called with video
    mock_instance.search_movie_info.assert_called()
    args, kwargs = mock_instance.search_movie_info.call_args
    assert args[0] == "ABC-123"
    assert args[1] == "video"
    assert "check_cancellation" in kwargs
    
    app.root.destroy()

def test_pull_info_logic_actress(monkeypatch):
    from ui.tkinter.app import XJJDesktopApp
    
    # Mock Service Class
    MockServiceClass = MagicMock()
    mock_instance = MockServiceClass.return_value
    mock_instance.search_movie_info.return_value = []
    
    monkeypatch.setattr("ui.tkinter.app.MovieDataCaptureService", MockServiceClass)
    
    # Mock Toplevel
    mock_toplevel = MagicMock()
    monkeypatch.setattr("tkinter.Toplevel", mock_toplevel)
    
    # Mock Threading to run synchronously
    def mock_start(self):
        self._target()
    monkeypatch.setattr(threading.Thread, "start", mock_start)
    
    app = XJJDesktopApp()
    app.show_page("maintain")
    assert _select_tab_by_text(app.pages["maintain"], "影视资讯")
    app.root.update()
    
    btn_pull = _find_button_by_text(app.pages["maintain"], "拉取讯息")
    assert btn_pull is not None
    
    # Test Actress
    app.movie_info_keyword.set("ABC")
    btn_pull.invoke()
    
    # Verify search_movie_info called with actress
    mock_instance.search_movie_info.assert_called()
    args, kwargs = mock_instance.search_movie_info.call_args
    assert args[0] == "ABC"
    assert args[1] == "actress"
    
    app.root.destroy()
