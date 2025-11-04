import pytest
import importlib

def test_streamlit_import():
    """测试Streamlit是否可以正常导入"""
    try:
        import streamlit
        assert streamlit is not None
    except ImportError:
        pytest.fail("Streamlit导入失败")

def test_selenium_import():
    """测试selenium是否可以正常导入"""
    try:
        import selenium
        assert selenium is not None
    except ImportError:
        pytest.fail("selenium导入失败")