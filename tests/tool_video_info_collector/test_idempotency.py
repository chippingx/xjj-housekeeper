"""
幂等性测试用例

专门测试video_info_collector工具的幂等性，确保：
1. 重复扫描不会产生重复记录
2. 重复操作结果一致
3. 数据库状态稳定
"""

import os
import tempfile
import shutil
import sqlite3
import pytest
from pathlib import Path

from tools.video_info_collector.scanner import VideoFileScanner
from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.metadata import VideoMetadataExtractor, VideoInfo
from tools.video_info_collector.csv_writer import CSVWriter


class TestScannerIdempotency:
    """测试扫描器的幂等性"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.test_video1 = os.path.join(self.test_dir, "video1.mp4")
        self.test_video2 = os.path.join(self.test_dir, "video2.avi")
        
        # 创建测试视频文件
        with open(self.test_video1, 'wb') as f:
            fake_content = b"fake video content 1" * 600  # 约12KB
            f.write(fake_content)
        with open(self.test_video2, 'wb') as f:
            fake_content = b"fake video content 2" * 600  # 约12KB
            f.write(fake_content)
    
    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_repeated_scanning_returns_same_results(self):
        """测试重复扫描返回相同结果"""
        scanner = VideoFileScanner()
        
        # 第一次扫描
        files1 = scanner.scan_directory(self.test_dir)
        files1_sorted = sorted(files1)
        
        # 第二次扫描
        files2 = scanner.scan_directory(self.test_dir)
        files2_sorted = sorted(files2)
        
        # 第三次扫描
        files3 = scanner.scan_directory(self.test_dir)
        files3_sorted = sorted(files3)
        
        # 验证结果一致
        assert files1_sorted == files2_sorted == files3_sorted
        assert len(files1_sorted) == 2
        assert self.test_video1 in files1_sorted
        assert self.test_video2 in files1_sorted
    
    def test_scanning_with_file_changes(self):
        """测试文件变化后扫描的一致性"""
        scanner = VideoFileScanner()
        
        # 初始扫描
        files_before = scanner.scan_directory(self.test_dir)
        
        # 修改文件内容（但不改变文件名）
        with open(self.test_video1, 'wb') as f:
            fake_content = b"modified fake video content 1" * 600  # 约12KB
            f.write(fake_content)
        
        # 再次扫描
        files_after = scanner.scan_directory(self.test_dir)
        
        # 验证扫描结果一致（扫描器只关心文件名，不关心内容）
        assert sorted(files_before) == sorted(files_after)


class TestSQLiteStorageIdempotency:
    """测试SQLite存储的幂等性"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test.db")
        self.test_video = os.path.join(self.test_dir, "test.mp4")
        
        # 创建测试视频文件
        with open(self.test_video, 'wb') as f:
            f.write(b"fake video content")
    
    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_upsert_video_info_idempotency(self):
        """测试upsert操作的幂等性"""
        storage = SQLiteStorage(self.test_db)
        
        # 准备测试数据
        video_info = VideoInfo(
            file_path=self.test_video,
            tags=['test', 'idempotency'],
            logical_path='test'
        )
        video_info.filename = 'test.mp4'
        video_info.file_size = 100
        video_info.duration = 120
        video_info.frame_rate = 30.0
        
        # 第一次插入
        video_id1 = storage.upsert_video_info(video_info)
        
        # 检查数据库状态
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM video_info")
        count1 = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video_tags")
        tag_count1 = cursor.fetchone()[0]
        
        conn.close()
        
        # 第二次插入（相同数据）
        video_id2 = storage.upsert_video_info(video_info)
        
        # 检查数据库状态
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM video_info")
        count2 = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video_tags")
        tag_count2 = cursor.fetchone()[0]
        
        conn.close()
        
        # 验证幂等性
        assert video_id1 == video_id2
        assert count1 == count2 == 1
        assert tag_count1 == tag_count2 == 2
        
        storage.close()
    
    def test_upsert_with_updated_info(self):
        """测试更新信息的upsert操作"""
        storage = SQLiteStorage(self.test_db)
        
        # 初始数据
        video_info1 = VideoInfo(
            file_path=self.test_video,
            tags=['original'],
            logical_path='test'
        )
        video_info1.filename = 'test.mp4'
        video_info1.file_size = 100
        video_info1.duration = 120
        video_info1.frame_rate = 30.0
        
        video_id1 = storage.upsert_video_info(video_info1)
        
        # 更新数据
        video_info2 = VideoInfo(
            file_path=self.test_video,
            tags=['updated'],
            logical_path='test'
        )
        video_info2.filename = 'test.mp4'
        video_info2.file_size = 150
        video_info2.duration = 150
        video_info2.frame_rate = 25.0
        
        video_id2 = storage.upsert_video_info(video_info2)
        
        # 验证是同一条记录
        assert video_id1 == video_id2
        
        # 验证数据被更新
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT file_size, duration, frame_rate FROM video_info WHERE id = ?", (video_id1,))
        result = cursor.fetchone()
        
        assert result[0] == 150
        assert result[1] == 150
        assert result[2] == 25.0
        
        # 验证只有一条记录
        cursor.execute("SELECT COUNT(*) FROM video_info")
        count = cursor.fetchone()[0]
        assert count == 1
        
        conn.close()
        storage.close()


class TestCSVWriterIdempotency:
    """测试CSV写入器的幂等性"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.test_csv = os.path.join(self.test_dir, "test.csv")
    
    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_write_video_infos_idempotency(self):
        """测试写入视频信息的幂等性"""
        writer = CSVWriter()
        
        # 准备测试数据
        video_info1 = VideoInfo(
            file_path='/test/video1.mp4',
            tags=['test'],
            logical_path='test'
        )
        video_info1.filename = 'video1.mp4'
        video_info1.file_size = 100
        video_info1.duration = 120
        video_info1.frame_rate = 30.0
        
        video_info2 = VideoInfo(
            file_path='/test/video2.mp4',
            tags=['test'],
            logical_path='test'
        )
        video_info2.filename = 'video2.mp4'
        video_info2.file_size = 200
        video_info2.duration = 180
        video_info2.frame_rate = 25.0
        
        video_infos = [video_info1, video_info2]
        
        # 第一次写入
        writer.write_video_infos(video_infos, self.test_csv)
        
        with open(self.test_csv, 'r', encoding='utf-8') as f:
            content1 = f.read()
        
        # 第二次写入（相同数据）
        writer.write_video_infos(video_infos, self.test_csv)
        
        with open(self.test_csv, 'r', encoding='utf-8') as f:
            content2 = f.read()
        
        # 验证内容一致
        assert content1 == content2
        
        # 验证包含预期数据
        assert 'video1.mp4' in content1
        assert 'video2.mp4' in content1


class TestIntegrationIdempotency:
    """测试集成场景的幂等性"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "integration.db")
        self.test_video = os.path.join(self.test_dir, "test.mp4")
        
        # 创建测试视频文件
        with open(self.test_video, 'wb') as f:
            fake_content = b"fake video content for integration test" * 300  # 约12KB
            f.write(fake_content)
    
    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_full_workflow_idempotency(self):
        """测试完整工作流的幂等性"""
        scanner = VideoFileScanner()
        storage = SQLiteStorage(self.test_db)
        
        # 第一次完整工作流
        files1 = scanner.scan_directory(self.test_dir)
        
        for file_path in files1:
            video_info = VideoInfo(
                file_path=file_path,
                tags=['integration', 'test'],
                logical_path='test'
            )
            video_info.filename = os.path.basename(file_path)
            video_info.file_size = os.path.getsize(file_path)
            video_info.duration = None
            video_info.frame_rate = None
            
            storage.upsert_video_info(video_info)
        
        # 检查第一次结果
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM video_info")
        count1 = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video_tags")
        tag_count1 = cursor.fetchone()[0]
        
        conn.close()
        
        # 第二次完整工作流（相同操作）
        files2 = scanner.scan_directory(self.test_dir)
        
        for file_path in files2:
            video_info = VideoInfo(
                file_path=file_path,
                tags=['integration', 'test'],
                logical_path='test'
            )
            video_info.filename = os.path.basename(file_path)
            video_info.file_size = os.path.getsize(file_path)
            video_info.duration = None
            video_info.frame_rate = None
            
            storage.upsert_video_info(video_info)
        
        # 检查第二次结果
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM video_info")
        count2 = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video_tags")
        tag_count2 = cursor.fetchone()[0]
        
        conn.close()
        
        # 验证幂等性
        assert sorted(files1) == sorted(files2)
        assert count1 == count2 == 1
        assert tag_count1 == tag_count2 == 2
        
        storage.close()
    
    def test_concurrent_access_safety(self):
        """测试并发访问的安全性"""
        storage1 = SQLiteStorage(self.test_db)
        storage2 = SQLiteStorage(self.test_db)
        
        # 准备测试数据
        video_info = VideoInfo(
            file_path=self.test_video,
            tags=['concurrent'],
            logical_path='test'
        )
        video_info.filename = 'test.mp4'
        video_info.file_size = 100
        video_info.duration = None
        video_info.frame_rate = None
        
        # 两个连接同时插入相同数据
        video_id1 = storage1.upsert_video_info(video_info)
        video_id2 = storage2.upsert_video_info(video_info)
        
        # 验证结果一致
        assert video_id1 == video_id2
        
        # 验证数据库中只有一条记录
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM video_info")
        count = cursor.fetchone()[0]
        assert count == 1
        
        conn.close()
        storage1.close()
        storage2.close()