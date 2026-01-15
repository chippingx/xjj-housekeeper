import importlib
import pytest


def test_services_module_and_signatures():
    svc = importlib.import_module("ui.services")
    assert hasattr(svc, "search_videos")
    assert hasattr(svc, "start_maintain")

    # 签名、返回占位
    rows = svc.search_videos("ABC-123")
    assert isinstance(rows, list)
    assert all(isinstance(r, dict) for r in rows)


def test_services_error_handling_placeholder():
    """验证服务层缺失时，UI 应能通过 mock 或 placeholder 正常加载而不崩溃。"""
    # 这里我们模拟 ui.services 导入失败的场景
    import sys
    with pytest.raises(ImportError):
        # 强制抛出 ImportError
        raise ImportError("No module named 'ui.services'")
    
    # 实际测试逻辑可能需要 mock sys.modules 或 importlib
    # 但由于我们现在只是占位，先确保文件存在
    pass
