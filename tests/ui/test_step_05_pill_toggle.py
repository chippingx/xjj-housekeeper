import importlib


def test_pill_label_switching_by_route():
    app = importlib.import_module("ui.app")

    assert app.get_top_pill_label(app.ROUTE_QUERY) == app.PILL_LABEL_QUERY
    assert app.get_top_pill_label(app.ROUTE_MAINTAIN) == app.PILL_LABEL_MAINTAIN


def test_route_state_switch_helper():
    app = importlib.import_module("ui.app")
    # 纯函数校验
    assert app.route_after_toggle(app.ROUTE_QUERY) == app.ROUTE_MAINTAIN
    assert app.route_after_toggle(app.ROUTE_MAINTAIN) == app.ROUTE_QUERY
