#!/usr/bin/env python3
"""
测试video_master_list功能

测试覆盖：
1. Master list的创建和维护
2. 状态管理（active/deleted/duplicate）
3. 防重复下载逻辑
4. 文件计数统计
5. 时间戳管理
6. 与video_info表的关联
"""

import unittest
import tempfile
import os
import shutil
import sqlite3
from pathlib import Path
import sys
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.video_info_collector.sqlite_storage import SQLiteStorage


class TestMasterList(unittest.TestCase):
    """测试video_master_list功能"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_master_list_creation(self):
        """测试master list的创建"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 验证video_master_list表存在
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='video_master_list'
        ''')
        
        self.assertIsNotNone(cursor.fetchone(), 
                           "video_master_list表应该存在")
        
        # 验证表结构
        cursor.execute("PRAGMA table_info(video_master_list)")
        columns = {column[1]: column[2] for column in cursor.fetchall()}
        
        expected_columns = {
            'video_code': 'TEXT',
            'status': 'TEXT',
            'file_count': 'INTEGER',
            'first_seen': 'TEXT',
            'last_updated': 'TEXT',
            'notes': 'TEXT'
        }
        
        for col_name, col_type in expected_columns.items():
            self.assertIn(col_name, columns,
                         f"列 {col_name} 应该存在")
            self.assertEqual(columns[col_name], col_type,
                           f"列 {col_name} 的类型应该是 {col_type}")
        
        conn.close()
    
    def test_master_list_insert_new_code(self):
        """测试插入新的video code"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入新的video code
        test_code = "ABC-123"
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO video_master_list 
            (video_code, status, file_count, first_seen, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', (test_code, 'active', 1, now, now))
        
        conn.commit()
        
        # 验证插入成功
        cursor.execute('SELECT * FROM video_master_list WHERE video_code = ?', (test_code,))
        result = cursor.fetchone()
        
        self.assertIsNotNone(result, "应该能找到插入的记录")
        self.assertEqual(result[1], test_code, "video_code应该匹配")  # video_code是第1个字段
        self.assertEqual(result[3], 'active', "状态应该是active")  # status是第3个字段
        self.assertEqual(result[4], 1, "文件计数应该是1")  # file_count是第4个字段
        
        conn.close()
    
    def test_master_list_status_transitions(self):
        """测试状态转换"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        test_code = "XYZ-456"
        now = datetime.now().isoformat()
        
        # 插入active状态的记录
        cursor.execute('''
            INSERT INTO video_master_list 
            (video_code, status, file_count, first_seen, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', (test_code, 'active', 1, now, now))
        
        conn.commit()
        
        # 测试转换为deleted状态
        later = (datetime.now() + timedelta(minutes=1)).isoformat()
        cursor.execute('''
            UPDATE video_master_list 
            SET status = ?, last_updated = ?, notes = ?
            WHERE video_code = ?
        ''', ('deleted', later, 'Manually marked as deleted', test_code))
        
        conn.commit()
        
        # 验证状态转换
        cursor.execute('SELECT status, last_updated, notes FROM video_master_list WHERE video_code = ?', 
                      (test_code,))
        result = cursor.fetchone()
        
        self.assertEqual(result[0], 'deleted', "状态应该是deleted")
        self.assertEqual(result[1], later, "last_updated应该更新")
        self.assertEqual(result[2], 'Manually marked as deleted', "notes应该记录原因")
        
        # 测试转换为duplicate状态
        even_later = (datetime.now() + timedelta(minutes=2)).isoformat()
        cursor.execute('''
            UPDATE video_master_list 
            SET status = ?, last_updated = ?, notes = ?
            WHERE video_code = ?
        ''', ('duplicate', even_later, 'Found duplicate', test_code))
        
        conn.commit()
        
        cursor.execute('SELECT status, last_updated, notes FROM video_master_list WHERE video_code = ?', 
                      (test_code,))
        result = cursor.fetchone()
        
        self.assertEqual(result[0], 'duplicate', "状态应该是duplicate")
        
        conn.close()
    
    def test_file_count_management(self):
        """测试文件计数管理"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        test_code = "DEF-789"
        now = datetime.now().isoformat()
        
        # 插入初始记录
        cursor.execute('''
            INSERT INTO video_master_list 
            (video_code, status, file_count, first_seen, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', (test_code, 'active', 1, now, now))
        
        conn.commit()
        
        # 增加文件计数（模拟发现同一video_code的多个文件）
        cursor.execute('''
            UPDATE video_master_list 
            SET file_count = file_count + 1, last_updated = ?
            WHERE video_code = ?
        ''', (now, test_code))
        
        conn.commit()
        
        # 验证计数增加
        cursor.execute('SELECT file_count FROM video_master_list WHERE video_code = ?', (test_code,))
        count = cursor.fetchone()[0]
        
        self.assertEqual(count, 2, "文件计数应该增加到2")
        
        # 减少文件计数（模拟文件删除）
        cursor.execute('''
            UPDATE video_master_list 
            SET file_count = file_count - 1, last_updated = ?
            WHERE video_code = ?
        ''', (now, test_code))
        
        conn.commit()
        
        cursor.execute('SELECT file_count FROM video_master_list WHERE video_code = ?', (test_code,))
        count = cursor.fetchone()[0]
        
        self.assertEqual(count, 1, "文件计数应该减少到1")
        
        conn.close()
    
    def test_duplicate_prevention_logic(self):
        """测试防重复下载逻辑"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入已删除的video code
        deleted_code = "DELETED-001"
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO video_master_list 
            (video_code, status, file_count, first_seen, last_updated, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (deleted_code, 'deleted', 0, now, now, 'User deleted'))
        
        # 插入重复的video code
        duplicate_code = "DUPLICATE-001"
        cursor.execute('''
            INSERT INTO video_master_list 
            (video_code, status, file_count, first_seen, last_updated, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (duplicate_code, 'duplicate', 2, now, now, 'Multiple copies found'))
        
        conn.commit()
        
        # 测试防重复下载查询
        def should_download(video_code):
            cursor.execute('''
                SELECT status FROM video_master_list 
                WHERE video_code = ? AND status IN ('deleted', 'duplicate')
            ''', (video_code,))
            return cursor.fetchone() is None
        
        # 验证防重复逻辑
        self.assertFalse(should_download(deleted_code), 
                        "已删除的video_code不应该重新下载")
        self.assertFalse(should_download(duplicate_code),
                        "重复的video_code不应该重新下载")
        self.assertTrue(should_download("NEW-CODE-001"),
                       "新的video_code应该可以下载")
        
        conn.close()
    
    def test_master_list_query_operations(self):
        """测试master list查询操作"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入测试数据
        test_data = [
            ("ACTIVE-001", "active", 1, "2024-01-01 10:00:00"),
            ("ACTIVE-002", "active", 2, "2024-01-02 10:00:00"),
            ("DELETED-001", "deleted", 0, "2024-01-03 10:00:00"),
            ("DUPLICATE-001", "duplicate", 3, "2024-01-04 10:00:00"),
            ("DUPLICATE-002", "duplicate", 2, "2024-01-05 10:00:00"),
        ]
        
        for video_code, status, file_count, first_seen in test_data:
            cursor.execute('''
                INSERT INTO video_master_list 
                (video_code, status, file_count, first_seen, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (video_code, status, file_count, first_seen, first_seen))
        
        conn.commit()
        
        # 测试按状态查询
        cursor.execute('SELECT COUNT(*) FROM video_master_list WHERE status = ?', ('active',))
        active_count = cursor.fetchone()[0]
        self.assertEqual(active_count, 2, "应该有2个active状态的记录")
        
        cursor.execute('SELECT COUNT(*) FROM video_master_list WHERE status = ?', ('deleted',))
        deleted_count = cursor.fetchone()[0]
        self.assertEqual(deleted_count, 1, "应该有1个deleted状态的记录")
        
        cursor.execute('SELECT COUNT(*) FROM video_master_list WHERE status = ?', ('duplicate',))
        duplicate_count = cursor.fetchone()[0]
        self.assertEqual(duplicate_count, 2, "应该有2个duplicate状态的记录")
        
        # 测试文件计数统计
        cursor.execute('SELECT SUM(file_count) FROM video_master_list WHERE status = ?', ('active',))
        active_files = cursor.fetchone()[0]
        self.assertEqual(active_files, 3, "active状态的总文件数应该是3")
        
        cursor.execute('SELECT SUM(file_count) FROM video_master_list WHERE status = ?', ('duplicate',))
        duplicate_files = cursor.fetchone()[0]
        self.assertEqual(duplicate_files, 5, "duplicate状态的总文件数应该是5")
        
        # 测试时间范围查询
        cursor.execute('''
            SELECT COUNT(*) FROM video_master_list 
            WHERE first_seen >= ? AND first_seen <= ?
        ''', ("2024-01-02 00:00:00", "2024-01-04 23:59:59"))
        date_range_count = cursor.fetchone()[0]
        self.assertEqual(date_range_count, 3, "指定时间范围内应该有3条记录")
        
        conn.close()
    
    def test_master_list_integration_with_video_info(self):
        """测试master list与video_info表的集成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入video_info记录
        video_data = [
            ('/path/to/ABC-123.mp4', 'ABC-123.mp4', 'ABC-123', 1024, 'present'),
            ('/path/to/ABC-123_copy.mp4', 'ABC-123_copy.mp4', 'ABC-123', 1024, 'present'),
            ('/path/to/XYZ-456.mkv', 'XYZ-456.mkv', 'XYZ-456', 2048, 'present'),
        ]
        
        for file_path, filename, video_code, file_size, file_status in video_data:
            cursor.execute('''
                INSERT INTO video_info 
                (file_path, filename, video_code, file_size, file_status, created_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (file_path, filename, video_code, file_size, file_status, 
                  datetime.now().isoformat()))
        
        conn.commit()
        
        # 基于video_info更新master list
        cursor.execute('''
            INSERT OR REPLACE INTO video_master_list (video_code, status, file_count, first_seen, last_updated)
            SELECT 
                video_code,
                CASE 
                    WHEN COUNT(*) > 1 THEN 'duplicate'
                    ELSE 'active'
                END as status,
                COUNT(*) as file_count,
                MIN(created_time) as first_seen,
                MAX(created_time) as last_updated
            FROM video_info 
            WHERE video_code IS NOT NULL AND file_status = 'present'
            GROUP BY video_code
        ''')
        
        conn.commit()
        
        # 验证master list更新
        cursor.execute('SELECT video_code, status, file_count FROM video_master_list ORDER BY video_code')
        results = cursor.fetchall()
        
        expected_results = [
            ('ABC-123', 'duplicate', 2),  # 有2个文件，标记为duplicate
            ('XYZ-456', 'active', 1),     # 只有1个文件，标记为active
        ]
        
        self.assertEqual(len(results), 2, "应该有2条master list记录")
        
        for i, (video_code, status, file_count) in enumerate(expected_results):
            self.assertEqual(results[i][0], video_code, f"第{i+1}条记录的video_code应该是{video_code}")
            self.assertEqual(results[i][1], status, f"第{i+1}条记录的status应该是{status}")
            self.assertEqual(results[i][2], file_count, f"第{i+1}条记录的file_count应该是{file_count}")
        
        conn.close()
    
    def test_master_list_bulk_operations(self):
        """测试master list批量操作"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 批量插入测试数据
        bulk_data = []
        now = datetime.now().isoformat()
        
        for i in range(100):
            video_code = f"BULK-{i:03d}"
            status = 'active' if i % 3 == 0 else ('deleted' if i % 3 == 1 else 'duplicate')
            file_count = (i % 5) + 1
            bulk_data.append((video_code, status, file_count, now, now))
        
        cursor.executemany('''
            INSERT INTO video_master_list 
            (video_code, status, file_count, first_seen, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', bulk_data)
        
        conn.commit()
        
        # 验证批量插入
        cursor.execute('SELECT COUNT(*) FROM video_master_list')
        total_count = cursor.fetchone()[0]
        self.assertEqual(total_count, 100, "应该有100条记录")
        
        # 批量状态更新
        cursor.execute('''
            UPDATE video_master_list 
            SET status = 'archived', last_updated = ?
            WHERE status = 'deleted'
        ''', (now,))
        
        conn.commit()
        
        # 验证批量更新
        cursor.execute('SELECT COUNT(*) FROM video_master_list WHERE status = ?', ('archived',))
        archived_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM video_master_list WHERE status = ?', ('deleted',))
        deleted_count = cursor.fetchone()[0]
        
        self.assertGreater(archived_count, 0, "应该有记录被更新为archived状态")
        self.assertEqual(deleted_count, 0, "不应该再有deleted状态的记录")
        
        conn.close()
    
    def test_master_list_performance(self):
        """测试master list性能"""
        import time
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入大量数据进行性能测试
        large_dataset = []
        now = datetime.now().isoformat()
        
        for i in range(10000):
            video_code = f"PERF-{i:05d}"
            status = ['active', 'deleted', 'duplicate'][i % 3]
            file_count = (i % 10) + 1
            large_dataset.append((video_code, status, file_count, now, now))
        
        # 测试批量插入性能
        start_time = time.time()
        cursor.executemany('''
            INSERT INTO video_master_list 
            (video_code, status, file_count, first_seen, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', large_dataset)
        conn.commit()
        insert_time = time.time() - start_time
        
        # 测试查询性能
        start_time = time.time()
        cursor.execute('SELECT COUNT(*) FROM video_master_list WHERE status = ?', ('active',))
        cursor.fetchone()
        query_time = time.time() - start_time
        
        # 测试复杂查询性能
        start_time = time.time()
        cursor.execute('''
            SELECT status, COUNT(*), SUM(file_count) 
            FROM video_master_list 
            GROUP BY status 
            ORDER BY COUNT(*) DESC
        ''')
        cursor.fetchall()
        complex_query_time = time.time() - start_time
        
        conn.close()
        
        # 性能断言
        self.assertLess(insert_time, 5.0, 
                       f"10000条记录的插入耗时{insert_time:.2f}秒，应该小于5秒")
        self.assertLess(query_time, 0.1,
                       f"简单查询耗时{query_time:.3f}秒，应该小于0.1秒")
        self.assertLess(complex_query_time, 0.5,
                       f"复杂查询耗时{complex_query_time:.3f}秒，应该小于0.5秒")


if __name__ == '__main__':
    unittest.main(verbosity=2)