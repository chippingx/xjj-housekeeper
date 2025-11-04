import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_navigation_text():
    """测试导航文案是否正确"""
    from ui.app import get_navigation_text
    
    # 查询页面的导航文案应该是"维护视频数据"
    assert get_navigation_text("查询") == "维护视频数据"
    
    # 维护页面的导航文案应该是"返回查询"
    assert get_navigation_text("维护") == "返回查询"