import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_maintain_form_fields():
    """测试维护表单字段是否正确"""
    from ui.app import get_maintain_form_fields
    
    fields = get_maintain_form_fields()
    expected_fields = ["扫描目录", "标签", "逻辑路径"]
    
    assert fields == expected_fields
    assert len(fields) == 3