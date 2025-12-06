import os
from pathlib import Path

from ui.services import VideoService


def _create_service_with_tmp_db(tmp_path: Path) -> VideoService:
    db_path = tmp_path / "video_test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    service = VideoService(db_path=str(db_path))
    service._ensure_storage()
    return service


def test_folder_based_tags_use_first_level_subdir_as_tag(tmp_path: Path):
    """start_maintain 完成后，应按首层子目录名为视频自动打标签。"""
    service = _create_service_with_tmp_db(tmp_path)
    storage = service.storage
    conn = storage.connection
    cur = conn.cursor()

    # 构造一个类似于：root/标签A/a1.mp4, root/标签B/b1.mp4 的路径结构
    root_dir = tmp_path / "root"
    sub_a = root_dir / "标签A"
    sub_b = root_dir / "标签B"
    sub_a.mkdir(parents=True)
    sub_b.mkdir(parents=True)

    file_a = sub_a / "a1.mp4"
    file_b = sub_b / "b1.mp4"
    # 实际文件是否存在对 _apply_folder_based_tags 没有影响，这里创建以贴近真实场景
    file_a.touch()
    file_b.touch()

    # 直接往 video_info 表插入两条记录，模拟已扫描结果
    for fp in (file_a, file_b):
        cur.execute(
            """
            INSERT INTO video_info (file_path, filename, created_time)
            VALUES (?, ?, datetime('now'))
            """,
            (str(fp), fp.name),
        )
    conn.commit()

    # 调用私有方法应用目录标签
    service._apply_folder_based_tags(str(root_dir))

    # 校验：每条记录都应获得以首层子目录命名的标签
    cur.execute(
        """
        SELECT vi.file_path, vt.tag
        FROM video_info vi
        JOIN video_tags vt ON vi.id = vt.video_id
        ORDER BY vi.file_path
        """
    )
    rows = cur.fetchall()
    mapping = {row["file_path"]: row["tag"] for row in rows}

    assert mapping[str(file_a)] == "标签A"
    assert mapping[str(file_b)] == "标签B"
