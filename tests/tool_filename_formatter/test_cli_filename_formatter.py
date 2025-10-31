import os
from pathlib import Path

import pytest

from tools.filename_formatter.cli import main as cli_main

# 工具函数：写临时规则文件并通过环境变量覆盖默认路径
def write_rules(tmp_path: Path, rules: list, monkeypatch) -> Path:
    import yaml
    path = tmp_path / "rules.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"rename_rules": rules}, f, allow_unicode=True)
    monkeypatch.setenv("RENAME_RULES_PATH", str(path))
    return path


def test_cli_basic_rename_non_recursive(tmp_path, capsys, monkeypatch):
    # 设置小尺寸以便测试
    monkeypatch.setenv("MIN_VIDEO_SIZE_BYTES", "1")
    # 创建文件：需要重命名的 mp4、隐藏文件、非视频扩展
    f1 = tmp_path / "abc123.mp4"
    f2 = tmp_path / ".hidden.mp4"
    f3 = tmp_path / "random.txt"
    f1.write_bytes(b"a")
    f2.write_bytes(b"a")
    f3.write_text("x")

    code = cli_main([str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "处理目录:" in out
    assert (tmp_path / "ABC-123.mp4").exists()
    # 隐藏文件不应影响结果
    assert ".hidden.mp4" not in out
    # 非视频不在输出中
    assert "random.txt" not in out



# 移除 dry-run 相关测试（CLI 已简化为单一命令）


def test_cli_rename_success(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("MIN_VIDEO_SIZE_BYTES", "1")
    f1 = tmp_path / "abc123.mp4"
    f1.write_bytes(b"a")
    code = cli_main([str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert (tmp_path / "ABC-123.mp4").exists()
    assert not (tmp_path / "abc123.mp4").exists()


def test_cli_recursive_with_rules(tmp_path, capsys, monkeypatch):
    sub = tmp_path / "subdir"
    sub.mkdir()
    f1 = sub / "site1234.com@DEF456.mp4"
    f1.write_bytes(b"a")

    monkeypatch.setenv("MIN_VIDEO_SIZE_BYTES", "1")
    write_rules(tmp_path, [{"pattern": "site1234.com@", "replace": ""}], monkeypatch)
    code = cli_main([str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    # 由于默认扁平化，文件会被移动到根目录
    assert (tmp_path / "DEF-456.mp4").exists()


def test_cli_invalid_directory(capsys):
    code = cli_main(["/path/not/exist"])
    out = capsys.readouterr().out
    assert code == 2
    assert "目录不存在" in out


# 移除多扩展名测试（CLI 默认仅 .mp4）