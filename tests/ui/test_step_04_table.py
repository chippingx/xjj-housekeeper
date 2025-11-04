import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_table_columns():
    """测试表格列是否正确"""
    from ui.app import get_table_columns
    
    columns = get_table_columns()
    expected_columns = ["视频", "大小", "路径", "标签", "逻辑路径"]
    
    assert columns == expected_columns
    assert len(columns) == 5