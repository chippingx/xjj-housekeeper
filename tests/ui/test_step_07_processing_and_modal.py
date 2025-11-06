from importlib import import_module


def test_processing_overlay_accessibility_and_scroll_lock():
    mf = import_module("ui.maintain_form")
    html = mf.render_processing_overlay()
    assert "position: fixed" in html or "position:fixed" in html
    assert "overflow: hidden" in html or "overflow:hidden" in html
    assert "aria-busy=\"true\"" in html


def test_complete_modal_accessibility_attributes():
    mf = import_module("ui.maintain_form")
    html = mf.render_complete_modal("维护完成")
    assert "role=\"dialog\"" in html
    assert "aria-modal=\"true\"" in html
    assert "tabindex=\"-1\"" in html
    assert "维护完成" in html


def test_route_after_escape_returns_query_when_modal_open():
    app = import_module("ui.app")
    assert app.route_after_escape(app.ROUTE_MAINTAIN, modal_open=True) == app.ROUTE_QUERY
    assert app.route_after_escape(app.ROUTE_QUERY, modal_open=True) == app.ROUTE_QUERY
    assert app.route_after_escape(app.ROUTE_MAINTAIN, modal_open=False) == app.ROUTE_MAINTAIN
