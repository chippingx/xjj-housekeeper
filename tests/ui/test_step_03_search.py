import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_search_input_validation():
    """测试查询输入验证逻辑"""
    from ui.app import validate_search_input
    
    # 空输入应该返回False
    assert validate_search_input("") is False
    assert validate_search_input("   ") is False
    
    # 非空输入应该返回True
    assert validate_search_input("test") is True
    assert validate_search_input("123") is True
    assert validate_search_input("a b c") is True