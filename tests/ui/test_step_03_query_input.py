import importlib


def test_validation_api_and_constants_present():
    app = importlib.import_module("ui.app")
    v = importlib.import_module("ui.validation")

    # app 常量与占位文案
    assert hasattr(app, "QUERY_PLACEHOLDER")
    assert app.QUERY_PLACEHOLDER == "按视频编号精确查询（示例：ABC-123）"
    assert hasattr(app, "QUERY_EMPTY_HINT")
    assert app.QUERY_EMPTY_HINT == "请输入关键词进行查询"
    assert hasattr(app, "QUERY_INVALID_HINT")
    assert app.QUERY_INVALID_HINT == "仅精确匹配；禁空/禁模糊"

    # validation API
    assert hasattr(v, "is_valid_video_code")
    assert hasattr(v, "validate_query_input")


def test_is_valid_video_code_exact_pattern():
    v = importlib.import_module("ui.validation")
    # 合法示例（大小写不敏感）
    assert v.is_valid_video_code("ABC-123") is True
    assert v.is_valid_video_code("abc-123") is True
    assert v.is_valid_video_code("DEMO-002") is True

    # 非法示例
    for s in ["", " ", "ABC123", "AB-123", "ABCDEFG-123", "ABC-12", "ABC-12345", "ABC_123", "ABC-1a3", "*ABC-123", "ABC-123*"]:
        assert v.is_valid_video_code(s) is False


def test_validate_query_input_messages():
    v = importlib.import_module("ui.validation")
    app = importlib.import_module("ui.app")

    ok, msg = v.validate_query_input("")
    assert ok is False and msg == app.QUERY_EMPTY_HINT

    ok, msg = v.validate_query_input("   ")
    assert ok is False and msg == app.QUERY_EMPTY_HINT

    ok, msg = v.validate_query_input("ABC123")
    assert ok is False and msg == app.QUERY_INVALID_HINT

    ok, msg = v.validate_query_input("ABC-123")
    assert ok is True and msg == ""
