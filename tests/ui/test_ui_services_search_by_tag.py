import os
from pathlib import Path

import pytest


def _create_service_with_tmp_db(tmp_path: Path):
    from ui.services import VideoService
    db_path = tmp_path / "video_test.db"
    # 确保目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)
    service = VideoService(db_path=str(db_path))
    service._ensure_storage()
    return service


def test_search_videos_supports_tag_keyword(tmp_path: Path):
    """search_videos 应根据标签进行搜索，而不仅是视频码。"""
    service = _create_service_with_tmp_db(tmp_path)
    storage = service.storage
    conn = storage.connection
    cur = conn.cursor()

    # 插入一条带有特定 video_code 的视频记录
    cur.execute(
        """
        INSERT INTO video_info (file_path, filename, file_size, duration_formatted, resolution, created_time, video_code)
        VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
        """,
        ("/tmp/adn641.mp4", "ADN-641.mp4", 100 * 1024 * 1024, "00:10:00", "1920x1080", "ADN-641"),
    )
    video_id = cur.lastrowid

    # 为该视频插入两个标签
    cur.execute("INSERT INTO video_tags (video_id, tag) VALUES (?, ?)", (video_id, "白峰美羽"))
    cur.execute("INSERT INTO video_tags (video_id, tag) VALUES (?, ?)", (video_id, "办公室"))
    conn.commit()

    # 按标签关键字搜索
    results = service.search_videos("白峰美羽")
    assert results, "按标签搜索应返回结果"
    # 只插入了一条，因此应返回一条记录，且标签文本包含我们的标签
    result = results[0]
    assert result["video"] == "ADN-641"
    assert "白峰美羽" in (result.get("tags") or "")

    # 另一标签同样可命中
    results2 = service.search_videos("办公室")
    assert results2, "按第二个标签搜索也应返回结果"
    assert any("办公室" in (r.get("tags") or "") for r in results2)
