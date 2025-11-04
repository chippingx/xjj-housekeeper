import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_progress_states():
    """测试进度状态功能"""
    from ui.app import get_progress_states
    
    states = get_progress_states()
    expected_states = ["等待中", "处理中", "已完成", "失败"]
    
    assert states == expected_states
    assert len(states) == 4