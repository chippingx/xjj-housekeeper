#!/usr/bin/env python3

import sys
import os
import tempfile
import sqlite3

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.metadata import VideoInfo
from tools.video_info_collector.smart_merge_manager import SmartMergeManager
from tools.video_info_collector.file_status_manager import FileStatus

def create_video_info(file_path, video_code, fingerprint, file_status="present"):
    """创建VideoInfo对象"""
    video = VideoInfo(file_path)
    video.filename = os.path.basename(file_path)
    video.video_code = video_code
    video.file_fingerprint = fingerprint
    video.file_status = file_status
    video.file_size = 1000000
    video.duration = 120
    video.width = 1920
    video.height = 1080
    return video

def main():
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # 初始化存储
        storage = SQLiteStorage(db_path)
        manager = SmartMergeManager(storage)
        
        # 创建测试数据 - 新视频有更好的质量
        old_video = create_video_info("/tmp/old_ABC-123.mp4", "ABC-123", "old_fingerprint_123", "present")
        old_video.file_size = 1000000  # 1MB
        old_video.width = 1280
        old_video.height = 720
        old_video.bit_rate = 1000
        
        new_video = create_video_info("/tmp/new_ABC-123.mp4", "ABC-123", "new_fingerprint_123", "present")
        new_video.file_size = 2000000  # 2MB - 更大的文件
        new_video.width = 1920
        new_video.height = 1080
        new_video.bit_rate = 2000  # 更高的码率
        
        # 插入旧视频
        old_video_id = storage.insert_video_info(old_video)
        old_video.id = old_video_id
        print(f"插入旧视频，ID: {old_video_id}")
        
        # 分析合并候选
        merge_results = manager.analyze_merge_candidates([new_video], [old_video])
        print(f"合并分析结果: {merge_results}")
        
        # 执行合并计划
        stats = manager.execute_merge_plan(merge_results, scan_id=1)
        print(f"合并统计: {stats}")
        
        # 直接查询数据库检查状态
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, video_code, file_path, file_status FROM video_info ORDER BY id")
        rows = cursor.fetchall()
        
        print("\n=== 数据库中的所有视频记录 ===")
        for row in rows:
            video_id, video_code, file_path, file_status = row
            print(f"ID: {video_id}, Code: {video_code}, Path: {file_path}, Status: {file_status}")
        
        # 检查REPLACED状态的视频
        cursor.execute("SELECT COUNT(*) FROM video_info WHERE file_status = 'replaced'")
        replaced_count = cursor.fetchone()[0]
        print(f"\n被标记为REPLACED的视频数量: {replaced_count}")
        
        conn.close()
        
    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == "__main__":
    main()