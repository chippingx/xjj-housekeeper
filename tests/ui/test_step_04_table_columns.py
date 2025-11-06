import importlib


def test_table_renderer_headers_and_styles():
    tr = importlib.import_module("ui.table_renderer")
    sample = [
        {"视频": "ABC-123.mp4", "大小": "10MB", "路径": "/a/b/c/ABC-123.mp4"},
        {"视频": "DEF-456.mp4", "大小": "20MB", "路径": "/x/y/z/DEF-456.mp4"},
    ]
    html = tr.render_search_results_table(sample)

    # 中文表头
    assert "视频" in html and "大小" in html and "路径" in html

    # 列换行策略class
    assert "class=\"nowrap\"" in html  # 应用于 视频/大小
    assert "class=\"breakall\"" in html  # 应用于 路径

    # 斑马线与悬停样式（:nth-child 与 :hover）
    assert ":nth-child(odd)" in html or ":nth-child(even)" in html
    assert ".sr-table tbody tr:hover" in html


def test_table_renderer_no_data_returns_hint():
    tr = importlib.import_module("ui.table_renderer")
    html = tr.render_search_results_table([])
    assert "暂无数据" in html
