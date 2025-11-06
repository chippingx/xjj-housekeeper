import importlib
import types


def test_streamlit_app_entry_exists():
    mod = importlib.import_module("ui.app")
    assert isinstance(mod, types.ModuleType)
    assert hasattr(mod, "render_query_page")
    assert hasattr(mod, "render_maintain_page")
    assert hasattr(mod, "ROUTE_QUERY")
    assert hasattr(mod, "ROUTE_MAINTAIN")


def test_route_constants_and_pill_labels():
    mod = importlib.import_module("ui.app")
    assert mod.ROUTE_QUERY == "query"
    assert mod.ROUTE_MAINTAIN == "maintain"
    assert mod.PILL_LABEL_QUERY == "维护视频数据"
    assert mod.PILL_LABEL_MAINTAIN == "返回查询"
