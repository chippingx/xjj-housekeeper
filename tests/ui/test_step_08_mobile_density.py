from importlib import import_module


def test_mobile_density_styles_exist():
    mf = import_module("ui.maintain_form")
    html = mf.render_mobile_density_styles()
    assert "@media (max-width: 480px)" in html
    assert ".form-row" in html
    assert "gap:4px" in html or "gap: 4px" in html


def test_table_mobile_word_break_rules():
    tr = import_module("ui.table_renderer")
    html = tr.render_table([
        {"视频": "A.mp4", "大小": "10MB", "路径": "a/b/c/very/long/path/that/should/wrap"}
    ])
    # 路径允许断行；视频/大小不换行
    assert "word-break: break-all" in html
    assert "white-space: nowrap" in html
