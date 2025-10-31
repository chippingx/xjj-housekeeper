"""
安全性测试用例

专门测试video_info_collector工具的安全性，确保：
1. 文件删除风险防护
2. 文件覆盖风险防护
3. 数据库操作安全性
4. 幂等性验证
5. 路径遍历攻击防护
"""

import os
import tempfile
import shutil
import sqlite3
import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

from tools.video_info_collector.scanner import VideoFileScanner
from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.metadata import VideoMetadataExtractor, VideoInfo
from tools.video_info_collector.csv_writer import CSVWriter


class TestFileDeletionSafety:
    """测试文件删除风险防护"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.test_video = os.path.join(self.test_dir, "test_video.mp4")
        self.test_db = os.path.join(self.test_dir, "test.db")
        
        # 创建测试视频文件（大于10KB以通过扫描器过滤）
        with open(self.test_video, 'wb') as f:
            # 写入足够的数据（12KB）
            fake_content = b"fake video content" * 700  # 约12KB
            f.write(fake_content)
    
    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_sqlite_storage_only_deletes_records(self):
        """测试SQLite存储只删除记录，不删除文件"""
        storage = SQLiteStorage(self.test_db)
        
        # 准备测试数据
        video_info = VideoInfo(
            file_path=self.test_video,
            tags=['test'],
            logical_path='test'
        )
        video_info.filename = 'test_video.mp4'
        video_info.file_size = 23
        video_info.duration = None
        video_info.frame_rate = None
    
        # 正常插入
        video_id = storage.upsert_video_info(video_info)
        
        # 验证记录存在
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM video_info WHERE id = ?", (video_id,))
        count_before = cursor.fetchone()[0]
        assert count_before == 1
        
        # 验证文件仍然存在
        assert os.path.exists(self.test_video)
        
        # 删除数据库记录
        cursor.execute("DELETE FROM video_info WHERE id = ?", (video_id,))
        conn.commit()
        
        # 验证记录被删除
        cursor.execute("SELECT COUNT(*) FROM video_info WHERE id = ?", (video_id,))
        count_after = cursor.fetchone()[0]
        assert count_after == 0
        
        # 验证文件仍然存在（没有被删除）
        assert os.path.exists(self.test_video)
        
        conn.close()
        storage.close()
    
    def test_no_file_operations_in_production_code(self):
        """测试生产代码中没有危险的文件操作"""
        # 检查主要模块中是否包含危险的文件操作
        dangerous_operations = ['os.remove', 'os.unlink', 'shutil.rmtree', 'pathlib.Path.unlink']
        
        modules_to_check = [
            'tools/video_info_collector/scanner.py',
            'tools/video_info_collector/sqlite_storage.py',
            'tools/video_info_collector/metadata.py',
            'tools/video_info_collector/csv_writer.py',
            'tools/video_info_collector/cli.py'
        ]
        
        for module_path in modules_to_check:
            full_path = os.path.join(os.getcwd(), module_path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for dangerous_op in dangerous_operations:
                    if dangerous_op in content:
                        # 检查是否在注释中或字符串中
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if dangerous_op in line:
                                stripped = line.strip()
                                # 如果不是注释且不是在字符串中，则报告
                                if not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                                    if dangerous_op not in ['# ' + dangerous_op, '"' + dangerous_op, "'" + dangerous_op]:
                                        pytest.fail(f"发现危险的文件操作导入: {dangerous_op} in {module_path}:{i+1}")
    
    def test_scanner_does_not_modify_files(self):
        """测试扫描器不修改文件"""
        scanner = VideoFileScanner()
        
        # 记录文件的原始状态
        original_stat = os.stat(self.test_video)
        original_content = open(self.test_video, 'rb').read()
        
        # 执行扫描
        files = scanner.scan_directory(self.test_dir)
        
        # 验证文件没有被修改
        new_stat = os.stat(self.test_video)
        new_content = open(self.test_video, 'rb').read()
        
        assert original_stat.st_size == new_stat.st_size
        assert original_content == new_content
        assert self.test_video in files
    
    def test_metadata_extractor_does_not_modify_files(self):
        """测试元数据提取器不修改文件"""
        extractor = VideoMetadataExtractor()
        
        # 记录文件的原始状态
        original_stat = os.stat(self.test_video)
        original_content = open(self.test_video, 'rb').read()
        
        # 执行元数据提取（可能会失败，但不应该修改文件）
        try:
            video_info = extractor.extract_metadata(self.test_video)
        except Exception:
            # 提取失败是可以接受的，因为这是假的视频文件
            pass
        
        # 验证文件没有被修改
        new_stat = os.stat(self.test_video)
        new_content = open(self.test_video, 'rb').read()
        
        assert original_stat.st_size == new_stat.st_size
        assert original_content == new_content


class TestIdempotencySafety:
    """测试幂等性安全"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.test_video = os.path.join(self.test_dir, "test_video.mp4")
        self.test_db = os.path.join(self.test_dir, "test.db")
        
        # 创建测试视频文件（大于10KB以通过扫描器过滤）
        with open(self.test_video, 'wb') as f:
            fake_content = b"fake video content" * 700  # 约12KB
            f.write(fake_content)
    
    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_repeated_scanning_is_idempotent(self):
        """测试重复扫描的幂等性"""
        storage = SQLiteStorage(self.test_db)
        
        # 第一次扫描
        video_info_1 = VideoInfo(
            file_path=self.test_video,
            tags=['test', 'idempotency'],
            logical_path='test'
        )
        video_info_1.filename = 'test_video.mp4'
        video_info_1.file_size = 23
        video_info_1.duration = None
        video_info_1.frame_rate = None
        
        video_id_1 = storage.upsert_video_info(video_info_1)
        
        # 检查第一次扫描结果
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM video_info")
        video_count_1 = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video_tags")
        tag_count_1 = cursor.fetchone()[0]
        
        conn.close()
        
        # 第二次扫描（相同数据）
        video_info_2 = VideoInfo(
            file_path=self.test_video,
            tags=['test', 'idempotency'],
            logical_path='test'
        )
        video_info_2.filename = 'test_video.mp4'
        video_info_2.file_size = 23
        video_info_2.duration = None
        video_info_2.frame_rate = None
        
        video_id_2 = storage.upsert_video_info(video_info_2)
        
        # 检查第二次扫描结果
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM video_info")
        video_count_2 = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM video_tags")
        tag_count_2 = cursor.fetchone()[0]
        
        conn.close()
        
        # 验证幂等性
        assert video_id_1 == video_id_2
        assert video_count_1 == video_count_2 == 1
        assert tag_count_1 == tag_count_2 == 2
        
        storage.close()
    
    def test_upsert_behavior_is_safe(self):
        """测试upsert行为的安全性"""
        storage = SQLiteStorage(self.test_db)
        
        # 插入初始记录
        video_info = VideoInfo(
            file_path=self.test_video,
            tags=['original'],
            logical_path='test'
        )
        video_info.filename = 'test_video.mp4'
        video_info.file_size = 23
        video_info.duration = 90
        video_info.frame_rate = 30.0
        
        video_id = storage.upsert_video_info(video_info)
        
        # 更新记录
        updated_info = VideoInfo(
            file_path=self.test_video,
            tags=['updated'],
            logical_path='test'
        )
        updated_info.filename = 'test_video.mp4'
        updated_info.file_size = 23
        updated_info.duration = 120
        updated_info.frame_rate = 25.0
        
        updated_id = storage.upsert_video_info(updated_info)
        
        # 验证是同一条记录
        assert video_id == updated_id
        
        # 验证数据被正确更新
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT duration, frame_rate FROM video_info WHERE id = ?", (video_id,))
        result = cursor.fetchone()
        
        assert result[0] == 120
        assert result[1] == 25.0
        
        # 验证只有一条视频记录
        cursor.execute("SELECT COUNT(*) FROM video_info")
        count = cursor.fetchone()[0]
        assert count == 1
        
        conn.close()
        storage.close()


class TestPathTraversalSafety:
    """测试路径遍历攻击防护"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.test_video = os.path.join(self.test_dir, "test_video.mp4")
        
        # 创建测试视频文件（大于10KB以通过扫描器过滤）
        with open(self.test_video, 'wb') as f:
            fake_content = b"fake video content" * 700  # 约12KB
            f.write(fake_content)
    
    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_scanner_rejects_malicious_paths(self):
        """测试扫描器拒绝恶意路径"""
        scanner = VideoFileScanner()
        
        malicious_paths = [
            "../../../etc",
            "../../../../usr/bin",
            "../../../var/log",
            "../../../../../../root"
        ]
        
        for malicious_path in malicious_paths:
            try:
                files = scanner.scan_directory(malicious_path)
                # 如果路径存在，确保没有找到敏感文件
                for file_path in files:
                    assert not any(sensitive in file_path.lower() for sensitive in [
                        'passwd', 'shadow', 'hosts', 'sudoers'
                    ])
            except (FileNotFoundError, PermissionError, OSError):
                # 这是预期的安全行为
                pass
    
    def test_output_path_validation(self):
        """测试输出路径验证"""
        malicious_outputs = [
            "/etc/malicious.db",
            "/usr/bin/malicious.db",
            "../../../etc/malicious.db"
        ]
        
        for malicious_output in malicious_outputs:
            try:
                storage = SQLiteStorage(malicious_output)
                
                # 如果能创建，尝试写入数据
                video_info = VideoInfo(
                    file_path=self.test_video,
                    tags=['test'],
                    logical_path='test'
                )
                
                video_id = storage.upsert_video_info(video_info)
                storage.close()
                
                # 检查文件是否被创建在恶意位置
                if os.path.exists(malicious_output):
                    os.remove(malicious_output)
                    # 注意：SQLite本身不实现路径验证，这是应用层的责任
                    
                # 验证相对路径被正确解析
                abs_path = os.path.abspath(malicious_output)
                # 确保路径不会意外写入到系统目录
                sensitive_dirs = ['/etc', '/usr/bin', '/var', '/root', '/System']
                for sensitive_dir in sensitive_dirs:
                    if abs_path.startswith(sensitive_dir) and os.path.exists(abs_path):
                        os.remove(abs_path)
                        pytest.fail(f"安全关注：数据库写入到敏感目录 {sensitive_dir}")
                    
            except (PermissionError, OSError, Exception):
                # 权限拒绝或其他错误是可接受的
                pass
    
    def test_cli_path_validation(self):
        """测试CLI路径验证"""
        from tools.video_info_collector.cli import scan_command
        
        class MockArgs:
            directory = "../../../etc"
            output = os.path.join(self.test_dir, "output.db")
            tags = "test"
            path = "test"
            recursive = True
            dry_run = True
            temp_file = None
            output_format = 'sqlite'
        
        args = MockArgs()
        
        # 执行CLI命令
        result = scan_command(args)
        
        # 对于不存在的目录，应该返回错误
        if not os.path.exists("../../../etc"):
            assert result == 1


class TestDatabaseSafety:
    """测试数据库操作安全性"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.test_dir, "test.db")
    
    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_sql_injection_protection(self):
        """测试SQL注入防护"""
        storage = SQLiteStorage(self.test_db)
        
        # 恶意输入
        malicious_filename = "'; DROP TABLE video_info; --"
        malicious_path = "'; INSERT INTO video_info VALUES ('hack'); --"
        malicious_tag = "'; INSERT INTO video_info VALUES ('hack'); --"
        
        video_info = VideoInfo(
            file_path=malicious_path,
            tags=[malicious_tag],
            logical_path='test'
        )
        video_info.filename = malicious_filename
        video_info.file_size = 100
        video_info.duration = None
        video_info.frame_rate = None
        
        # 插入恶意数据
        video_id = storage.upsert_video_info(video_info)
        
        # 验证表结构没有被破坏
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # 检查表是否仍然存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_info'")
        table_exists = cursor.fetchone()
        assert table_exists is not None
        
        # 检查数据是否被安全存储
        cursor.execute("SELECT filename FROM video_info WHERE id = ?", (video_id,))
        filename_result = cursor.fetchone()
        assert filename_result[0] == malicious_filename
        
        # 检查标签表
        cursor.execute("SELECT tag FROM video_tags WHERE video_id = ?", (video_id,))
        tag_result = cursor.fetchone()
        assert tag_result[0] == malicious_tag
        
        conn.close()
        storage.close()
    
    def test_transaction_integrity(self):
        """测试事务完整性"""
        storage = SQLiteStorage(self.test_db)
        
        video_info = VideoInfo(
            file_path='/test/test.mp4',
            tags=['test'],
            logical_path='test'
        )
        video_info.filename = 'test.mp4'
        video_info.file_size = 100
        video_info.duration = None
        video_info.frame_rate = None
        
        # 正常插入
        video_id = storage.upsert_video_info(video_info)
        
        # 验证数据被正确提交
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM video_info WHERE id = ?", (video_id,))
        count = cursor.fetchone()[0]
        assert count == 1
        
        cursor.execute("SELECT COUNT(*) FROM video_tags WHERE video_id = ?", (video_id,))
        tag_count = cursor.fetchone()[0]
        assert tag_count == 1
        
        conn.close()
        storage.close()


class TestFileOverwriteSafety:
    """测试文件覆盖风险防护"""
    
    def setup_method(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.existing_file = os.path.join(self.test_dir, "existing.csv")
        
        # 创建已存在的文件
        with open(self.existing_file, 'w') as f:
            f.write("existing content")
    
    def teardown_method(self):
        """清理测试环境"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_csv_writer_overwrites_safely(self):
        """测试CSV写入器安全覆盖"""
        writer = CSVWriter()
        
        # 记录原始内容
        with open(self.existing_file, 'r') as f:
            original_content = f.read()
        
        # 准备测试数据 - 使用VideoInfo对象
        video_info = VideoInfo(
            file_path='/test/test.mp4',
            tags=['test'],
            logical_path='test'
        )
        video_info.filename = 'test.mp4'
        video_info.file_size = 100
        video_info.duration = None
        video_info.frame_rate = None
        
        test_data = [video_info]
        
        # 写入新数据
        writer.write_video_infos(test_data, self.existing_file)
        
        # 验证文件被正确覆盖
        with open(self.existing_file, 'r') as f:
            new_content = f.read()
        
        assert new_content != original_content
        assert 'test.mp4' in new_content
        assert 'existing content' not in new_content
    
    def test_database_creation_is_safe(self):
        """测试数据库创建的安全性"""
        db_path = os.path.join(self.test_dir, "new.db")
        
        # 确保数据库文件不存在
        assert not os.path.exists(db_path)
        
        # 创建数据库
        storage = SQLiteStorage(db_path)
        
        # 验证数据库文件被创建
        assert os.path.exists(db_path)
        
        # 验证表结构正确
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['video_info', 'video_tags', 'scan_history']
        for table in expected_tables:
            assert table in tables
        
        conn.close()
        storage.close()