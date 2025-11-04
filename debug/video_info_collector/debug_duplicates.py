#!/usr/bin/env python3
"""
调试重复检测问题 - 检查数据库中的实际数据
"""

import sqlite3
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.metadata import VideoInfo

def debug_database_data():
    """调试数据库中的实际数据"""
    print("=== 调试数据库中的实际数据 ===")
    
    # 创建内存数据库
    storage = SQLiteStorage(":memory:")
    
    # 创建测试数据
    test_videos = [
        VideoInfo("/path/to/movie.mp4", tags=["test"], logical_path="test/path"),
        VideoInfo("/path/to/movie.mkv", tags=["test"], logical_path="test/path"),
        VideoInfo("/path/to/other.mp4", tags=["test"], logical_path="test/path")
    ]
    
    # 设置基本属性
    for i, video in enumerate(test_videos):
        video.width = 1920
        video.height = 1080
        video.duration = 120.5 + i * 10
        video.video_codec = "h264"
        video.audio_codec = "aac"
        video.file_size = 75000000 + i * 1000000
        video.bit_rate = 5000000
        video.frame_rate = 30.0
    
    print("\n1. 插入测试数据...")
    for video in test_videos:
        print(f"   插入: {video.filename}")
        print(f"   video_code: {video.video_code}")
        storage.insert_video_info(video)
    
    # 直接查询数据库
    cursor = storage.connection.cursor()
    
    print("\n2. 查看数据库中的实际数据:")
    cursor.execute("SELECT id, filename, video_code FROM video_info ORDER BY id")
    rows = cursor.fetchall()
    for row in rows:
        print(f"   ID: {row[0]}, filename: {row[1]}, video_code: {row[2]}")
    
    print("\n3. 检查video_code字段是否正确存储:")
    cursor.execute("SELECT filename, video_code FROM video_info")
    rows = cursor.fetchall()
    for row in rows:
        filename = row[0]
        stored_video_code = row[1]
        # 手动计算expected video_code
        expected_code = filename.rsplit('.', 1)[0] if '.' in filename else filename
        print(f"   {filename}: 存储={stored_video_code}, 期望={expected_code}, 匹配={stored_video_code == expected_code}")
    
    print("\n4. 测试GROUP BY查询:")
    cursor.execute("""
        SELECT video_code, COUNT(*) as count, GROUP_CONCAT(filename) as files
        FROM video_info 
        GROUP BY video_code
        ORDER BY video_code
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"   video_code: '{row[0]}', count: {row[1]}, files: {row[2]}")
    
    print("\n5. 测试重复检测查询:")
    cursor.execute("""
        SELECT video_code, COUNT(*) as count, GROUP_CONCAT(filename) as files
        FROM video_info 
        GROUP BY video_code
        HAVING COUNT(*) > 1
        ORDER BY video_code
    """)
    rows = cursor.fetchall()
    print(f"   找到 {len(rows)} 个重复组:")
    for row in rows:
        print(f"   video_code: '{row[0]}', count: {row[1]}, files: {row[2]}")
    
    print("\n6. 检查get_enhanced_statistics结果:")
    stats = storage.get_enhanced_statistics()
    print(f"   duplicate_video_groups: {stats.get('duplicate_video_groups', 'N/A')}")
    print(f"   total_duplicate_videos: {stats.get('total_duplicate_videos', 'N/A')}")
    print(f"   unique_videos: {stats.get('unique_videos', 'N/A')}")
    
    storage.close()

if __name__ == "__main__":
    debug_database_data()