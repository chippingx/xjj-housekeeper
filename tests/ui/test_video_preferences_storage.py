from pathlib import Path

import pytest

from tools.video_info_collector.sqlite_storage import SQLiteStorage


def _create_tmp_storage(tmp_path: Path) -> SQLiteStorage:
    db_path = tmp_path / "prefs_test.db"
    storage = SQLiteStorage(str(db_path))
    return storage


def test_video_preferences_table_created_and_unique(tmp_path: Path):
    storage = _create_tmp_storage(tmp_path)
    info = storage.get_table_info()
    assert "video_preferences" in info
    cols = {c["name"] for c in info["video_preferences"]["columns"]}
    assert {"video_code", "status"}.issubset(cols)


def test_upsert_and_get_video_preference(tmp_path: Path):
    storage = _create_tmp_storage(tmp_path)

    # 初次写入 LIKE
    storage.upsert_video_preference("TST-001", "like")
    assert storage.get_video_preference("TST-001") == "like"

    # 再次写入 DISLIKE 应覆盖，而不是新增一行
    storage.upsert_video_preference("TST-001", "dislike")
    assert storage.get_video_preference("TST-001") == "dislike"

    # 清除偏好后应为 None
    storage.clear_video_preference("TST-001")
    assert storage.get_video_preference("TST-001") is None
