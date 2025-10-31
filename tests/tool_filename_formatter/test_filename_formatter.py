import os
import yaml
from pathlib import Path

import pytest

from tools.filename_formatter import FilenameFormatter, RenameResult


def write_rules_yaml(tmp_path: Path, rules: list) -> Path:
    """在临时目录写入重命名规则 YAML 文件，并返回路径"""
    rules_path = tmp_path / "rename_rules.yaml"
    with open(rules_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"rename_rules": rules}, f, allow_unicode=True)
    return rules_path


# -----------------------------
# 基础格式化行为
# -----------------------------
def test_format_filename_basic_uppercase_and_dash():
    fmt = FilenameFormatter(min_file_size=1)
    assert fmt.format_filename("ABC123.mp4") == "ABC-123.mp4"
    assert fmt.format_filename("ABC-123.mp4") == "ABC-123.mp4"


def test_format_filename_lowercase_to_upper():
    fmt = FilenameFormatter(min_file_size=1)
    assert fmt.format_filename("abc123.mp4") == "ABC-123.mp4"
    assert fmt.format_filename("abc-123.mp4") == "ABC-123.mp4"


def test_format_filename_unmatched_returns_original():
    fmt = FilenameFormatter(min_file_size=1)
    # 不符合字母+数字模式，保持原样
    assert fmt.format_filename("random_name.mp4") == "random_name.mp4"
    assert fmt.format_filename("noext") == "noext"


# -----------------------------
# 规则应用与加载
# -----------------------------
def test_apply_rename_rules_then_format(tmp_path, monkeypatch):
    """测试先应用规则再格式化的组合操作"""
    rules = [
        {"pattern": "site1234.com@", "replace": ""},
    ]
    rules_path = write_rules_yaml(tmp_path, rules)
    fmt = FilenameFormatter(default_rules_path=str(rules_path))

    # 测试组合操作：先移除前缀，再格式化
    assert fmt.apply_rename_rules("site1234.com@ABC123ch.mp4") == "ABC-123.mp4"





def test_is_standard_true_false():
    fmt = FilenameFormatter(min_file_size=1)
    assert fmt.is_standard("ABC-123.mp4") is True
    assert fmt.is_standard("abc-123.mp4") is False  # 需要大写
    assert fmt.is_standard("ABC123.mp4") is True    # 允许无连字符
    assert fmt.is_standard("ABC-123.mkv") is False  # 仅 .mp4


# -----------------------------
# 批量重命名（目录内）
# -----------------------------
def test_rename_in_directory_non_recursive(tmp_path):
    # 创建测试文件
    f1 = tmp_path / "abc123.mp4"          # 需格式化
    f2 = tmp_path / "random.txt"          # 非视频扩展，忽略
    f3 = tmp_path / ".hidden.mp4"         # 隐藏文件，忽略
    f4 = tmp_path / "ABC-123.mp4"         # 已标准，同名跳过

    f1.write_bytes(b"a")
    f2.write_text("x")
    f3.write_bytes(b"a")
    f4.write_bytes(b"a")

    fmt = FilenameFormatter(min_file_size=1)
    results = fmt.rename_in_directory(str(tmp_path), include_subdirs=False)

    # 将结果映射为字典便于断言
    status_map = {Path(r.original).name: r.status for r in results}
    # 非视频不会出现在结果中；隐藏文件在当前实现中被跳过且不记录
    assert "random.txt" not in status_map
    # 重新构建 status_map 只针对我们明确知道会产生结果的文件
    status_map = {Path(r.original).name: r.status for r in results if Path(r.original).name in {"abc123.mp4", "ABC-123.mp4"}}

    # 目标文件已存在时应安全跳过；允许 success 或 skipped: target exists
    assert status_map["abc123.mp4"].startswith("success") or status_map["abc123.mp4"] == "skipped: target exists"
    assert status_map["ABC-123.mp4"] == "skipped: same name"

    # 验证重命名后文件存在
    assert (tmp_path / "ABC-123.mp4").exists()


def test_rename_in_directory_recursive(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()

    f1 = sub / "site1234.com@DEF456.mp4"  # 需规则清理 + 格式化
    f1.write_bytes(b"a")

    # 写入规则文件并使用 default_rules_path 传入
    rules_path = write_rules_yaml(tmp_path, [{"pattern": "site1234.com@", "replace": ""}])
    fmt = FilenameFormatter(default_rules_path=str(rules_path), min_file_size=1)

    results = fmt.rename_in_directory(str(tmp_path), include_subdirs=True)

    # 应该将文件重命名为 DEF-456.mp4
    target = sub / "DEF-456.mp4"
    assert target.exists()

    # 校验结果记录
    by_name = {Path(r.original).name: r for r in results}
    assert "site1234.com@DEF456.mp4" in by_name
    assert by_name["site1234.com@DEF456.mp4"].status == "success"


def test_rename_in_directory_target_exists_skip(tmp_path):
    # 源文件与预期目标文件都存在，应跳过
    src = tmp_path / "ABC123.mp4"
    target = tmp_path / "ABC-123.mp4"
    src.write_bytes(b"a")
    target.write_bytes(b"a")

    fmt = FilenameFormatter(min_file_size=1)
    results = fmt.rename_in_directory(str(tmp_path), include_subdirs=False)

    # 找到对应记录
    entry = next((r for r in results if Path(r.original).name == "ABC123.mp4"), None)
    assert entry is not None
    assert entry.status == "skipped: target exists"
    # 原文件仍存在
    assert src.exists()
    assert target.exists()


def test_rename_in_directory_same_name_skip(tmp_path):
    # 已标准命名，规则和格式化后不变，跳过
    src = tmp_path / "DEF-456.mp4"
    src.write_bytes(b"a")

    fmt = FilenameFormatter(min_file_size=1)
    results = fmt.rename_in_directory(str(tmp_path), include_subdirs=False)

    entry = next((r for r in results if Path(r.original).name == "DEF-456.mp4"), None)
    assert entry is not None
    assert entry.status == "skipped: same name"
    assert src.exists()


def test_rename_in_directory_min_file_size_skip(tmp_path):
    # 设置 min_file_size 大于文件大小，应跳过处理
    small = tmp_path / "ABC123.mp4"
    small.write_bytes(b"a")  # 1 字节

    fmt = FilenameFormatter(min_file_size=2)  # 门槛为 2 字节
    results = fmt.rename_in_directory(str(tmp_path), include_subdirs=False)

    # 不应有任何结果记录（文件被大小门槛跳过）
    assert all(Path(r.original).name != "ABC123.mp4" for r in results)


# -----------------------------
# 异常路径与参数校验
# -----------------------------
def test_rename_in_directory_invalid_path():
    fmt = FilenameFormatter(min_file_size=1)
    with pytest.raises(FileNotFoundError):
        fmt.rename_in_directory("/path/not/exist", include_subdirs=False)

    file_path = Path(__file__)  # 当前测试文件为普通文件
    with pytest.raises(NotADirectoryError):
        fmt.rename_in_directory(str(file_path), include_subdirs=False)


def test_btnets_net_rule_removal(tmp_path):
    """专门测试 example1.net_ 规则的清理功能"""
    # 构造包含 example1.net_ 规则的测试规则
    rules = [
        {"pattern": "example1.net_", "replace": ""},
    ]
    rules_path = write_rules_yaml(tmp_path, rules)
    fmt = FilenameFormatter(default_rules_path=str(rules_path))

    # 测试各种 example1.net_ 前缀的情况
    test_cases = [
        ("example1.net_TST-002.mp4", "TST-002.mp4"),
        ("example1.net_ABC-123.mp4", "ABC-123.mp4"),
        ("example1.net_DEF456.mp4", "DEF-456.mp4"),
        ("example1.net_abc123.mp4", "ABC-123.mp4"),
        ("example1.net_def456.mp4", "DEF-456.mp4"),
        ("normal_file.mp4", "normal_file.mp4"),  # 不包含前缀的文件应保持不变
    ]

    for input_name, expected_output in test_cases:
        result = fmt.apply_rename_rules(input_name)
        assert result == expected_output, f"输入: {input_name}, 期望: {expected_output}, 实际: {result}"


def test_btnets_net_rule_in_directory_rename(tmp_path):
    """测试 example1.net_ 规则在目录重命名中的实际应用"""
    # 创建包含 example1.net_ 前缀的测试文件
    test_file = tmp_path / "example1.net_TST-002.mp4"
    test_file.write_bytes(b"test content")

    # 构造规则
    rules = [
        {"pattern": "example1.net_", "replace": ""},
    ]
    rules_path = write_rules_yaml(tmp_path, rules)
    fmt = FilenameFormatter(default_rules_path=str(rules_path), min_file_size=1)

    # 执行目录重命名
    results = fmt.rename_in_directory(str(tmp_path), include_subdirs=False)

    # 验证重命名结果
    assert len(results) == 1
    result = results[0]
    assert result.status == "success"
    assert Path(result.original).name == "example1.net_TST-002.mp4"
    assert Path(result.new).name == "TST-002.mp4"

    # 验证文件确实被重命名
    assert not test_file.exists()
    assert (tmp_path / "TST-002.mp4").exists()