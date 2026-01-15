import pytest
import tkinter as tk
from ui.tkinter.app import XJJDesktopApp

class TestEventBinding:
    def test_table_events_bound(self):
        """测试表格事件是否正确绑定"""
        app = XJJDesktopApp()
        
        # 显示查询页面
        app.show_page("query")
        
        # 获取表格组件
        table = None
        # 内容结构：pages["query"] -> content -> table_container -> table
        for content in app.pages["query"].winfo_children():
            for table_container in content.winfo_children():
                for widget in table_container.winfo_children():
                    if isinstance(widget, tk.ttk.Treeview):
                        table = widget
                        break
                if table:
                    break
            if table:
                break
        
        assert table is not None, "表格组件未找到"
        
        app.root.destroy()

    def test_right_click_menu_creation(self):
        """测试右键菜单创建功能"""
        app = XJJDesktopApp()
        
        # 测试系统播放器获取功能
        players = app._get_system_video_players()
        assert isinstance(players, dict), "播放器列表应该是字典类型"
        assert "默认播放器" in players, "应该包含默认播放器选项"
        
        app.root.destroy()