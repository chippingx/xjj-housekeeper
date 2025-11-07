import pytest
import tkinter as tk
from ui.tkinter.app import XJJDesktopApp

class TestSelectedColor:
    def test_selected_color_config(self):
        """测试选中行颜色配置是否正确"""
        app = XJJDesktopApp()
        
        # 检查颜色配置
        assert app.colors["brand"] == "#2563EB"
        assert app.colors["white"] == "#FFFFFF"
        
        app.root.destroy()

    def test_treeview_style_config(self):
        """测试Treeview样式配置是否正确"""
        app = XJJDesktopApp()
        
        # 获取Treeview样式
        style = tk.ttk.Style()
        
        # 检查背景色和前景色配置
        background_config = style.map("Treeview", "background")
        foreground_config = style.map("Treeview", "foreground")
        
        # 检查选中状态的颜色配置
        assert any("selected" in state and "#2563EB" in value for state, value in background_config)
        assert any("selected" in state and "#FFFFFF" in value for state, value in foreground_config)
        
        app.root.destroy()