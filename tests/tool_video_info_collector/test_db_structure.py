#!/usr/bin/env python3
"""测试数据库结构"""

import sys
import os
# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tools.video_info_collector.sqlite_storage import SQLiteStorage

def test_database_structure():
    """测试数据库结构"""
    print("=== 测试数据库结构 ===")
    
    # 创建内存数据库
    storage = SQLiteStorage(":memory:")
    
    # 检查video_info表结构
    cursor = storage.connection.cursor()
    cursor.execute("PRAGMA table_info(video_info)")
    columns = cursor.fetchall()
    
    print("video_info表结构:")
    for column in columns:
        print(f"  {column[1]} ({column[2]})")
    
    # 检查是否有新列
    column_names = [column[1] for column in columns]
    required_columns = ['video_code', 'file_fingerprint', 'file_status', 'last_scan_time', 'last_merge_time']
    
    print("\n检查新列:")
    for col in required_columns:
        status = "✓" if col in column_names else "✗"
        print(f"  {status} {col}")
    
    # 测试插入数据
    print("\n测试插入数据...")
    try:
        cursor.execute("""
            INSERT INTO video_info (file_path, filename, created_time, video_code, file_fingerprint, file_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("/test/path.mp4", "test.mp4", "2024-01-01", "TEST001", "fingerprint123", "present"))
        
        # 查询数据
        cursor.execute("SELECT file_path, video_code, file_fingerprint, file_status FROM video_info")
        result = cursor.fetchone()
        print(f"插入成功: {result}")
        
    except Exception as e:
        print(f"插入失败: {e}")
    
    storage.close()

if __name__ == "__main__":
    test_database_structure()