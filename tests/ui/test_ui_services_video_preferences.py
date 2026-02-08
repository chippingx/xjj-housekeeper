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
