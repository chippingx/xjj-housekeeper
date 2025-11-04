import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_app_import():
    """测试UI主入口是否可以正常导入"""
    try:
        from ui import app
        assert app is not None
    except ImportError:
        pytest.fail("UI主入口导入失败")

def test_main_function_exists():
    """测试main函数是否存在"""
    from ui.app import main
    assert main is not None
    assert callable(main)

def test_page_functions_exist():
    """测试页面函数是否存在"""
    from ui.app import show_query_page, show_maintain_page
    assert show_query_page is not None
    assert callable(show_query_page)
    assert show_maintain_page is not None
    assert callable(show_maintain_page)