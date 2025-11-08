import pytest
import tkinter as tk
from pathlib import Path
from ui.tkinter.app import XJJDesktopApp

class TestPathDisplay:
    def test_path_display_conversion(self):
        """测试路径显示是否转换为视频所在目录"""
        app = XJJDesktopApp()
        
        # 创建模拟表格
        container = tk.Frame(app.content_inner)
        table = tk.ttk.Treeview(container, columns=("filename", "file_path", "file_size", "duration", "resolution"), show="headings")
        
        # 测试数据
        test_data = [
            {
                "filename": "test.mp4",
                "file_path": "/path/to/video/test.mp4",
                "file_size": "100MB",
                "duration": "00:30:00",
                "resolution": "1920x1080"
            }
        ]
        
        # 渲染表格
        app._render_table(table, test_data)
        
        # 获取渲染后的行数据
        items = table.get_children()
        assert len(items) == 1
        
        values = table.item(items[0], "values")
        assert values[0] == "test.mp4"
        assert values[1] == "/path/to/video"  # 应该显示目录路径而非完整文件路径
        assert values[2] == "100MB"
        assert values[3] == "00:30:00"
        assert values[4] == "1920x1080"
        
        app.root.destroy()

    def test_empty_path_display(self):
        """测试空路径的显示"""
        app = XJJDesktopApp()
        
        # 创建模拟表格
        container = tk.Frame(app.content_inner)
        table = tk.ttk.Treeview(container, columns=("filename", "file_path", "file_size", "duration", "resolution"), show="headings")
        
        # 测试数据
        test_data = [
            {
                "filename": "test.mp4",
                "file_path": "",
                "file_size": "100MB",
                "duration": "00:30:00",
                "resolution": "1920x1080"
            }
        ]
        
        # 渲染表格
        app._render_table(table, test_data)
        
        # 获取渲染后的行数据
        items = table.get_children()
        assert len(items) == 1
        
        values = table.item(items[0], "values")
        assert values[1] == ""  # 空路径应该显示为空
        
        app.root.destroy()