import importlib


def test_maintain_form_structure_and_classes():
    mf = importlib.import_module("ui.maintain_form")
    html = mf.render_maintain_form()

    # 四行表单元素占位
    assert "扫描目录路径" in html
    assert "选择目录" in html
    assert "标签（可选）" in html
    assert "逻辑路径（可选）" in html
    assert "开始维护" in html

    # 布局与密度（类名存在）
    assert ".form-row" in html
    assert "display:flex" in html
    assert "gap:8px" in html or "gap: 8px" in html
    assert "align-items:center" in html
    assert "margin:10px 0" in html
