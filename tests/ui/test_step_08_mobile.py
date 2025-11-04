import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_mobile_config():
    """测试移动端配置功能"""
    from ui.app import get_mobile_config
    
    config = get_mobile_config()
    
    # 检查配置是否包含必要的移动端适配参数
    assert "compact" in config
    assert "min_width" in config
    assert "max_width" in config
    
    # 检查配置值是否合理
    assert config["compact"] is True
    assert config["min_width"] <= config["max_width"]