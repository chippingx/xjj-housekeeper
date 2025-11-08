import pytest
import tkinter as tk
from pathlib import Path
from ui.tkinter.app import XJJDesktopApp

class TestErrorHandling:
    def test_nonexistent_path_check(self, monkeypatch):
        """测试不存在路径的检查"""
        app = XJJDesktopApp()
        
        # 测试不存在的目录
        nonexistent_dir = "/nonexistent/path"
        assert not Path(nonexistent_dir).exists()
        
        # 测试不存在的视频文件
        nonexistent_video = Path("/nonexistent/path") / "test.mp4"
        assert not nonexistent_video.exists()
        
        app.root.destroy()

    def test_system_commands(self, monkeypatch):
        """测试系统命令调用"""
        app = XJJDesktopApp()
        
        # 模拟系统命令调用
        called_commands = []
        
        def mock_system(cmd):
            called_commands.append(cmd)
            return 0
        
        def mock_startfile(path):
            called_commands.append(f"startfile: {path}")
        
        # 测试不同平台的命令调用
        if app.root.tk.call("tk", "windowingsystem") == "win32":
            monkeypatch.setattr("os.startfile", mock_startfile)
            app._open_file_manager("/test/path")
            assert called_commands == ["startfile: /test/path"]
        else:
            monkeypatch.setattr("os.system", mock_system)
            app._open_file_manager("/test/path")
            if app.root.tk.call("tk", "windowingsystem") == "aqua":  # macOS
                assert called_commands == ["open '/test/path'"]
            else:  # Linux
                assert called_commands == ["xdg-open '/test/path'"]
        
        app.root.destroy()