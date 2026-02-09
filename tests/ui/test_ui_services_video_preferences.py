from pathlib import Path

from ui.services import VideoService


def _create_service_with_tmp_db(tmp_path: Path) -> VideoService:
    db_path = tmp_path / "video_pref.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    service = VideoService(db_path=str(db_path))
    service._ensure_storage()
    return service


def test_search_results_include_preference_status(tmp_path: Path):
    service = _create_service_with_tmp_db(tmp_path)
    storage = service.storage
    conn = storage.connection
    cur = conn.cursor()

    # 准备一条带 video_code 的记录
    cur.execute(
        """
        INSERT INTO video_info (file_path, filename, file_size, duration_formatted, resolution, created_time, video_code)
        VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
        """,
        ("/tmp/tst001.mp4", "TST-001.mp4", 50 * 1024 * 1024, "00:05:00", "1920x1080", "TST-001"),
    )
    conn.commit()

    # 标记喜欢
    service.set_video_preference("TST-001", "like")

    results = service.search_videos("TST-001")
    assert results, "应能搜索到插入的视频"
    pref = results[0].get("preference")
    assert pref == "like"

    service.set_video_preference("TST-001", "deleted")
    results_deleted = service.search_videos("TST-001")
    assert results_deleted
    pref_deleted = results_deleted[0].get("preference")
    assert pref_deleted == "deleted"

    # 清除偏好后，再次搜索应不再返回状态
    service.set_video_preference("TST-001", None)
    results2 = service.search_videos("TST-001")
    assert results2
    pref2 = results2[0].get("preference")
    assert pref2 in (None, "")


def test_preference_deleted_updates_master_and_file_status(tmp_path: Path):
    service = _create_service_with_tmp_db(tmp_path)
    storage = service.storage
    conn = storage.connection
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO video_info (file_path, filename, file_size, duration_formatted, resolution, created_time, video_code, file_status)
        VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?)
        """,
        ("/tmp/tst002.mp4", "TST-002.mp4", 40 * 1024 * 1024, "00:04:00", "1920x1080", "TST-002", "present"),
    )
    cur.execute(
        """
        INSERT INTO video_master_list (video_code, status, file_count)
        VALUES (?, 'active', 1)
        """,
        ("TST-002",),
    )
    conn.commit()

    service.set_video_preference("TST-002", "deleted")

    cur.execute("SELECT status FROM video_master_list WHERE video_code = ?", ("TST-002",))
    status = cur.fetchone()[0]
    assert status == "deleted"

    cur.execute("SELECT file_status FROM video_info WHERE video_code = ?", ("TST-002",))
    file_status = cur.fetchone()[0]
    assert file_status == "deleted"


def test_sync_deleted_preferences_updates_master_and_file_status(tmp_path: Path):
    service = _create_service_with_tmp_db(tmp_path)
    storage = service.storage
    conn = storage.connection
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO video_info (file_path, filename, file_size, duration_formatted, resolution, created_time, video_code, file_status)
        VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?)
        """,
        ("/tmp/tst003.mp4", "TST-003.mp4", 30 * 1024 * 1024, "00:03:00", "1920x1080", "TST-003", "present"),
    )
    cur.execute(
        """
        INSERT INTO video_master_list (video_code, status, file_count)
        VALUES (?, 'active', 1)
        """,
        ("TST-003",),
    )
    cur.execute(
        """
        INSERT INTO video_preferences (video_code, status)
        VALUES (?, 'deleted')
        """,
        ("TST-003",),
    )
    conn.commit()

    service._deleted_pref_synced = False
    service.sync_deleted_preferences()

    cur.execute("SELECT status FROM video_master_list WHERE video_code = ?", ("TST-003",))
    status = cur.fetchone()[0]
    assert status == "deleted"

    cur.execute("SELECT file_status FROM video_info WHERE video_code = ?", ("TST-003",))
    file_status = cur.fetchone()[0]
    assert file_status == "deleted"


def test_delete_video_updates_master_list_after_remove(tmp_path: Path):
    service = _create_service_with_tmp_db(tmp_path)
    storage = service.storage
    conn = storage.connection
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO video_info (file_path, filename, file_size, duration_formatted, resolution, created_time, video_code, file_status)
        VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?)
        """,
        ("/tmp/tst004.mp4", "TST-004.mp4", 20 * 1024 * 1024, "00:02:00", "1920x1080", "TST-004", "present"),
    )
    cur.execute(
        """
        INSERT INTO video_master_list (video_code, status, file_count)
        VALUES (?, 'active', 1)
        """,
        ("TST-004",),
    )
    conn.commit()

    cur.execute("SELECT id FROM video_info WHERE video_code = ?", ("TST-004",))
    video_id = cur.fetchone()[0]
    assert service.delete_video(video_id) is True

    cur.execute("SELECT file_count, status, last_updated FROM video_master_list WHERE video_code = ?", ("TST-004",))
    row = cur.fetchone()
    assert row[0] == 0
    assert row[1] == "deleted"
    assert row[2] is not None
