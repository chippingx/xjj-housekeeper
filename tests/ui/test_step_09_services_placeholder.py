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
    svc = importlib.import_module("ui.services")
    with pytest.raises(ValueError) as ei:
        svc.search_videos("")
    assert "keyword must be non-empty and exact" in str(ei.value)

    with pytest.raises(RuntimeError) as ei2:
        svc.start_maintain(path="/tmp", labels=None, logical_path=None)
    assert "not implemented" in str(ei2.value)
