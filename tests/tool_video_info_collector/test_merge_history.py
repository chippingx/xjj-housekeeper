#!/usr/bin/env python3
"""
测试merge_history功能

测试覆盖：
1. 合并历史记录的创建
2. 不同事件类型的记录（insert_new、update_path、mark_missing等）
3. 历史查询和统计
4. 事件时间线追踪
5. 批量操作的历史记录
"""

import unittest
import tempfile
import os
import shutil
import sqlite3
import json
from pathlib import Path
import sys
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.video_info_collector.sqlite_storage import SQLiteStorage


class TestMergeHistory(unittest.TestCase):
    """测试merge_history功能"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_merge_history_table_creation(self):
        """测试merge_history表的创建"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 验证merge_history表存在
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='merge_history'
        ''')
        
        self.assertIsNotNone(cursor.fetchone(), 
                           "merge_history表应该存在")
        
        # 验证表结构
        cursor.execute("PRAGMA table_info(merge_history)")
        columns = {column[1]: column[2] for column in cursor.fetchall()}
        
        expected_columns = {
            'id': 'INTEGER',
            'merge_time': 'TEXT',
            'event_type': 'TEXT',
            'video_code': 'TEXT',
            'old_path': 'TEXT',
            'new_path': 'TEXT',
            'details': 'TEXT',
            'scan_session_id': 'TEXT'
        }
        
        for col_name, col_type in expected_columns.items():
            self.assertIn(col_name, columns,
                         f"列 {col_name} 应该存在")
            self.assertEqual(columns[col_name], col_type,
                           f"列 {col_name} 的类型应该是 {col_type}")
        
        conn.close()
    
    def test_insert_new_event_recording(self):
        """测试insert_new事件记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 记录insert_new事件
        event_data = {
            'merge_time': datetime.now().isoformat(),
            'event_type': 'insert_new',
            'video_code': 'ABC-123',
            'new_path': '/path/to/ABC-123.mp4',
            'details': json.dumps({
                'file_size': 1073741824,
                'duration': 3600.0,
                'resolution': '1920x1080'
            }),
            'scan_session_id': 'session_001'
        }
        
        cursor.execute('''
            INSERT INTO merge_history 
            (merge_time, event_type, video_code, new_path, details, scan_session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event_data['merge_time'], event_data['event_type'], 
              event_data['video_code'], event_data['new_path'],
              event_data['details'], event_data['scan_session_id']))
        
        conn.commit()
        
        # 验证记录插入
        cursor.execute('SELECT * FROM merge_history WHERE video_code = ?', ('ABC-123',))
        result = cursor.fetchone()
        
        self.assertIsNotNone(result, "应该能找到插入的记录")
        self.assertEqual(result[2], 'insert_new', "事件类型应该是insert_new")
        self.assertEqual(result[3], 'ABC-123', "video_code应该匹配")
        self.assertEqual(result[5], '/path/to/ABC-123.mp4', "new_path应该匹配")
        
        # 验证details JSON格式
        details = json.loads(result[6])
        self.assertEqual(details['file_size'], 1073741824, "details中的file_size应该匹配")
        
        conn.close()
    
    def test_update_path_event_recording(self):
        """测试update_path事件记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 记录update_path事件（文件移动）
        event_data = {
            'merge_time': datetime.now().isoformat(),
            'event_type': 'update_path',
            'video_code': 'XYZ-456',
            'old_path': '/old/path/XYZ-456.mkv',
            'new_path': '/new/path/XYZ-456.mkv',
            'details': json.dumps({
                'reason': 'file_moved',
                'fingerprint_match': True,
                'confidence': 0.95
            }),
            'scan_session_id': 'session_002'
        }
        
        cursor.execute('''
            INSERT INTO merge_history 
            (merge_time, event_type, video_code, old_path, new_path, details, scan_session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (event_data['merge_time'], event_data['event_type'], 
              event_data['video_code'], event_data['old_path'],
              event_data['new_path'], event_data['details'], 
              event_data['scan_session_id']))
        
        conn.commit()
        
        # 验证记录插入
        cursor.execute('SELECT * FROM merge_history WHERE video_code = ?', ('XYZ-456',))
        result = cursor.fetchone()
        
        self.assertIsNotNone(result, "应该能找到插入的记录")
        self.assertEqual(result[2], 'update_path', "事件类型应该是update_path")
        self.assertEqual(result[4], '/old/path/XYZ-456.mkv', "old_path应该匹配")
        self.assertEqual(result[5], '/new/path/XYZ-456.mkv', "new_path应该匹配")
        
        # 验证details
        details = json.loads(result[6])
        self.assertEqual(details['reason'], 'file_moved', "移动原因应该记录")
        self.assertTrue(details['fingerprint_match'], "指纹匹配状态应该记录")
        
        conn.close()
    
    def test_mark_missing_event_recording(self):
        """测试mark_missing事件记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 记录mark_missing事件
        event_data = {
            'merge_time': datetime.now().isoformat(),
            'event_type': 'mark_missing',
            'video_code': 'DEF-789',
            'old_path': '/missing/path/DEF-789.avi',
            'details': json.dumps({
                'last_seen': '2024-01-01 10:00:00',
                'scan_attempts': 3,
                'reason': 'file_not_found'
            }),
            'scan_session_id': 'session_003'
        }
        
        cursor.execute('''
            INSERT INTO merge_history 
            (merge_time, event_type, video_code, old_path, details, scan_session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event_data['merge_time'], event_data['event_type'], 
              event_data['video_code'], event_data['old_path'],
              event_data['details'], event_data['scan_session_id']))
        
        conn.commit()
        
        # 验证记录插入
        cursor.execute('SELECT * FROM merge_history WHERE video_code = ?', ('DEF-789',))
        result = cursor.fetchone()
        
        self.assertIsNotNone(result, "应该能找到插入的记录")
        self.assertEqual(result[2], 'mark_missing', "事件类型应该是mark_missing")
        self.assertEqual(result[4], '/missing/path/DEF-789.avi', "old_path应该匹配")
        self.assertIsNone(result[5], "new_path应该为空")
        
        # 验证details
        details = json.loads(result[6])
        self.assertEqual(details['reason'], 'file_not_found', "缺失原因应该记录")
        self.assertEqual(details['scan_attempts'], 3, "扫描尝试次数应该记录")
        
        conn.close()
    
    def test_duplicate_detection_event_recording(self):
        """测试duplicate_detection事件记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 记录duplicate_detection事件
        event_data = {
            'merge_time': datetime.now().isoformat(),
            'event_type': 'duplicate_detection',
            'video_code': 'DUP-001',
            'new_path': '/path/to/DUP-001_copy.mp4',
            'details': json.dumps({
                'original_path': '/path/to/DUP-001.mp4',
                'duplicate_paths': [
                    '/path/to/DUP-001_copy.mp4',
                    '/backup/DUP-001.mp4'
                ],
                'fingerprint': 'abc123def456',
                'action': 'mark_as_duplicate'
            }),
            'scan_session_id': 'session_004'
        }
        
        cursor.execute('''
            INSERT INTO merge_history 
            (merge_time, event_type, video_code, new_path, details, scan_session_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event_data['merge_time'], event_data['event_type'], 
              event_data['video_code'], event_data['new_path'],
              event_data['details'], event_data['scan_session_id']))
        
        conn.commit()
        
        # 验证记录插入
        cursor.execute('SELECT * FROM merge_history WHERE video_code = ?', ('DUP-001',))
        result = cursor.fetchone()
        
        self.assertIsNotNone(result, "应该能找到插入的记录")
        self.assertEqual(result[2], 'duplicate_detection', "事件类型应该是duplicate_detection")
        
        # 验证details
        details = json.loads(result[6])
        self.assertIn('duplicate_paths', details, "应该记录重复文件路径")
        self.assertEqual(len(details['duplicate_paths']), 2, "应该记录2个重复路径")
        
        conn.close()
    
    def test_merge_session_tracking(self):
        """测试合并会话追踪"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        session_id = 'session_batch_001'
        merge_time = datetime.now().isoformat()
        
        # 模拟一次完整的合并会话，包含多个事件
        events = [
            ('insert_new', 'NEW-001', None, '/path/to/NEW-001.mp4'),
            ('insert_new', 'NEW-002', None, '/path/to/NEW-002.mkv'),
            ('update_path', 'MOVED-001', '/old/MOVED-001.avi', '/new/MOVED-001.avi'),
            ('mark_missing', 'MISSING-001', '/gone/MISSING-001.mp4', None),
            ('duplicate_detection', 'DUP-002', None, '/path/to/DUP-002_copy.mp4'),
        ]
        
        for event_type, video_code, old_path, new_path in events:
            details = json.dumps({'session_event': True, 'batch_operation': True})
            
            cursor.execute('''
                INSERT INTO merge_history 
                (merge_time, event_type, video_code, old_path, new_path, details, scan_session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (merge_time, event_type, video_code, old_path, new_path, details, session_id))
        
        conn.commit()
        
        # 验证会话事件统计
        cursor.execute('SELECT COUNT(*) FROM merge_history WHERE scan_session_id = ?', (session_id,))
        session_event_count = cursor.fetchone()[0]
        self.assertEqual(session_event_count, 5, "会话应该包含5个事件")
        
        # 按事件类型统计
        cursor.execute('''
            SELECT event_type, COUNT(*) 
            FROM merge_history 
            WHERE scan_session_id = ? 
            GROUP BY event_type
        ''', (session_id,))
        
        event_stats = dict(cursor.fetchall())
        expected_stats = {
            'insert_new': 2,
            'update_path': 1,
            'mark_missing': 1,
            'duplicate_detection': 1
        }
        
        self.assertEqual(event_stats, expected_stats, "事件类型统计应该匹配")
        
        conn.close()
    
    def test_history_timeline_query(self):
        """测试历史时间线查询"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入不同时间的历史记录
        base_time = datetime.now()
        
        timeline_events = [
            (base_time - timedelta(hours=3), 'insert_new', 'TIME-001'),
            (base_time - timedelta(hours=2), 'update_path', 'TIME-001'),
            (base_time - timedelta(hours=1), 'mark_missing', 'TIME-001'),
            (base_time, 'insert_new', 'TIME-002'),
        ]
        
        for event_time, event_type, video_code in timeline_events:
            cursor.execute('''
                INSERT INTO merge_history 
                (merge_time, event_type, video_code, scan_session_id)
                VALUES (?, ?, ?, ?)
            ''', (event_time.isoformat(), event_type, video_code, 'timeline_test'))
        
        conn.commit()
        
        # 查询特定video_code的时间线
        cursor.execute('''
            SELECT merge_time, event_type 
            FROM merge_history 
            WHERE video_code = ? 
            ORDER BY merge_time
        ''', ('TIME-001',))
        
        timeline = cursor.fetchall()
        
        self.assertEqual(len(timeline), 3, "TIME-001应该有3个历史事件")
        
        # 验证时间顺序
        event_types = [event[1] for event in timeline]
        expected_sequence = ['insert_new', 'update_path', 'mark_missing']
        self.assertEqual(event_types, expected_sequence, "事件应该按时间顺序排列")
        
        # 查询时间范围内的事件
        start_time = (base_time - timedelta(hours=2, minutes=30)).isoformat()
        end_time = (base_time - timedelta(minutes=30)).isoformat()
        
        cursor.execute('''
            SELECT COUNT(*) FROM merge_history 
            WHERE merge_time >= ? AND merge_time <= ?
        ''', (start_time, end_time))
        
        range_count = cursor.fetchone()[0]
        self.assertEqual(range_count, 2, "指定时间范围内应该有2个事件")
        
        conn.close()
    
    def test_history_statistics_and_reporting(self):
        """测试历史统计和报告"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入大量测试数据
        import random
        
        event_types = ['insert_new', 'update_path', 'mark_missing', 'duplicate_detection']
        base_time = datetime.now()
        
        for i in range(100):
            event_time = base_time - timedelta(days=random.randint(0, 30))
            event_type = random.choice(event_types)
            video_code = f'STAT-{i:03d}'
            session_id = f'session_{i // 10}'  # 每10个事件一个会话
            
            cursor.execute('''
                INSERT INTO merge_history 
                (merge_time, event_type, video_code, scan_session_id)
                VALUES (?, ?, ?, ?)
            ''', (event_time.isoformat(), event_type, video_code, session_id))
        
        conn.commit()
        
        # 统计总事件数
        cursor.execute('SELECT COUNT(*) FROM merge_history')
        total_events = cursor.fetchone()[0]
        self.assertEqual(total_events, 100, "应该有100个历史事件")
        
        # 按事件类型统计
        cursor.execute('''
            SELECT event_type, COUNT(*) 
            FROM merge_history 
            GROUP BY event_type 
            ORDER BY COUNT(*) DESC
        ''')
        
        type_stats = cursor.fetchall()
        self.assertGreater(len(type_stats), 0, "应该有事件类型统计")
        
        # 按会话统计
        cursor.execute('''
            SELECT scan_session_id, COUNT(*) 
            FROM merge_history 
            GROUP BY scan_session_id 
            ORDER BY scan_session_id
        ''')
        
        session_stats = cursor.fetchall()
        self.assertEqual(len(session_stats), 10, "应该有10个不同的会话")
        
        # 每日事件统计
        cursor.execute('''
            SELECT DATE(merge_time) as event_date, COUNT(*) 
            FROM merge_history 
            GROUP BY DATE(merge_time) 
            ORDER BY event_date DESC
        ''')
        
        daily_stats = cursor.fetchall()
        self.assertGreater(len(daily_stats), 0, "应该有每日统计数据")
        
        # 最近活动查询
        recent_time = (base_time - timedelta(days=7)).isoformat()
        cursor.execute('''
            SELECT COUNT(*) FROM merge_history 
            WHERE merge_time >= ?
        ''', (recent_time,))
        
        recent_count = cursor.fetchone()[0]
        self.assertGreaterEqual(recent_count, 0, "最近7天的事件数应该>=0")
        
        conn.close()
    
    def test_history_cleanup_and_maintenance(self):
        """测试历史记录清理和维护"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入不同时期的历史记录
        base_time = datetime.now()
        
        # 插入很旧的记录（超过1年）
        old_time = base_time - timedelta(days=400)
        for i in range(10):
            cursor.execute('''
                INSERT INTO merge_history 
                (merge_time, event_type, video_code, scan_session_id)
                VALUES (?, ?, ?, ?)
            ''', (old_time.isoformat(), 'insert_new', f'OLD-{i}', 'old_session'))
        
        # 插入最近的记录
        recent_time = base_time - timedelta(days=30)
        for i in range(10):
            cursor.execute('''
                INSERT INTO merge_history 
                (merge_time, event_type, video_code, scan_session_id)
                VALUES (?, ?, ?, ?)
            ''', (recent_time.isoformat(), 'insert_new', f'RECENT-{i}', 'recent_session'))
        
        conn.commit()
        
        # 验证插入
        cursor.execute('SELECT COUNT(*) FROM merge_history')
        total_before = cursor.fetchone()[0]
        self.assertEqual(total_before, 20, "应该有20条历史记录")
        
        # 清理超过1年的记录
        cleanup_threshold = (base_time - timedelta(days=365)).isoformat()
        cursor.execute('''
            DELETE FROM merge_history 
            WHERE merge_time < ?
        ''', (cleanup_threshold,))
        
        conn.commit()
        
        # 验证清理结果
        cursor.execute('SELECT COUNT(*) FROM merge_history')
        total_after = cursor.fetchone()[0]
        self.assertEqual(total_after, 10, "清理后应该剩余10条记录")
        
        # 验证保留的都是最近的记录
        cursor.execute('SELECT video_code FROM merge_history ORDER BY video_code')
        remaining_codes = [row[0] for row in cursor.fetchall()]
        
        for code in remaining_codes:
            self.assertTrue(code.startswith('RECENT-'), "保留的应该都是最近的记录")
        
        conn.close()
    
    def test_history_performance(self):
        """测试历史记录性能"""
        import time
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 批量插入大量历史记录
        large_dataset = []
        base_time = datetime.now()
        
        for i in range(5000):
            event_time = base_time - timedelta(minutes=i)
            large_dataset.append((
                event_time.isoformat(),
                ['insert_new', 'update_path', 'mark_missing'][i % 3],
                f'PERF-{i:05d}',
                f'session_{i // 100}'
            ))
        
        # 测试批量插入性能
        start_time = time.time()
        cursor.executemany('''
            INSERT INTO merge_history 
            (merge_time, event_type, video_code, scan_session_id)
            VALUES (?, ?, ?, ?)
        ''', large_dataset)
        conn.commit()
        insert_time = time.time() - start_time
        
        # 测试查询性能
        start_time = time.time()
        cursor.execute('SELECT COUNT(*) FROM merge_history WHERE event_type = ?', ('insert_new',))
        cursor.fetchone()
        query_time = time.time() - start_time
        
        # 测试复杂统计查询性能
        start_time = time.time()
        cursor.execute('''
            SELECT scan_session_id, event_type, COUNT(*) 
            FROM merge_history 
            GROUP BY scan_session_id, event_type 
            ORDER BY scan_session_id, event_type
        ''')
        cursor.fetchall()
        stats_time = time.time() - start_time
        
        conn.close()
        
        # 性能断言
        self.assertLess(insert_time, 3.0,
                       f"5000条记录的插入耗时{insert_time:.2f}秒，应该小于3秒")
        self.assertLess(query_time, 0.1,
                       f"简单查询耗时{query_time:.3f}秒，应该小于0.1秒")
        self.assertLess(stats_time, 1.0,
                       f"统计查询耗时{stats_time:.3f}秒，应该小于1秒")


if __name__ == '__main__':
    unittest.main(verbosity=2)