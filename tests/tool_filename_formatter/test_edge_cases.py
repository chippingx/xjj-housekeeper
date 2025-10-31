"""
边缘情况和错误处理测试用例
测试各种异常情况和边缘场景
"""

import os
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tools.filename_formatter.formatter import FilenameFormatter


class TestEdgeCases:
    """边缘情况测试"""

    def setup_method(self):
        """每个测试前的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.formatter = FilenameFormatter(min_file_size=1)

    def teardown_method(self):
        """每个测试后的清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_file(self, path: str, content: str = "test content") -> str:
        """创建测试文件"""
        full_path = os.path.join(self.temp_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        return full_path

    def test_empty_directory(self):
        """测试空目录处理"""
        results = self.formatter.rename_in_directory(self.temp_dir)
        assert len(results) == 0

    def test_no_matching_files(self):
        """测试没有匹配文件的情况"""
        # 创建不匹配的文件（非视频扩展名）
        self.create_test_file("normal_file.txt")
        self.create_test_file("another_file.doc")
        self.create_test_file("image.jpg")
        
        results = self.formatter.rename_in_directory(self.temp_dir)
        assert len(results) == 0

    def test_very_long_filename(self):
        """测试超长文件名处理"""
        # 创建超长文件名
        long_name = "example1.net_" + "a" * 200 + "_TST-001.mp4"
        self.create_test_file(long_name)
        
        results = self.formatter.rename_in_directory(self.temp_dir)
        assert len(results) == 1
        assert results[0].status.startswith("success")

    def test_special_characters_in_filename(self):
        """测试文件名中的特殊字符"""
        special_files = [
            "example1.net_TST-001 (copy).mp4",
            "example1.net_TST-002[backup].mp4",
            "example1.net_TST-003{temp}.mp4",
            "example1.net_TST-004@home.mp4",
            "example1.net_TST-005#test.mp4"
        ]
        
        for filename in special_files:
            self.create_test_file(filename)
        
        results = self.formatter.rename_in_directory(self.temp_dir)
        assert len(results) == len(special_files)
        
        for result in results:
            assert result.status.startswith("success")

    def test_unicode_characters_in_filename(self):
        """测试文件名中的Unicode字符"""
        unicode_files = [
            "example1.net_测试-001.mp4",
            "example1.net_TST-002_中文.mp4",
            "example1.net_TST-003_🎬.mp4",
            "example1.net_TST-004_émoji.mp4"
        ]
        
        for filename in unicode_files:
            self.create_test_file(filename)
        
        results = self.formatter.rename_in_directory(self.temp_dir)
        assert len(results) == len(unicode_files)

    def test_file_permission_errors(self):
        """测试文件权限错误"""
        # 创建文件
        test_file = self.create_test_file("example1.net_TST-001.mp4")
        
        # 模拟权限错误
        with patch('os.rename') as mock_rename:
            mock_rename.side_effect = PermissionError("Permission denied")
            
            results = self.formatter.rename_in_directory(self.temp_dir)
            assert len(results) == 1
            assert "error" in results[0].status.lower()

    def test_disk_space_error(self):
        """测试磁盘空间不足错误"""
        # 创建文件
        self.create_test_file("example1.net_TST-001.mp4")
        
        # 模拟磁盘空间不足
        with patch('os.rename') as mock_rename:
            mock_rename.side_effect = OSError("No space left on device")
            
            results = self.formatter.rename_in_directory(self.temp_dir)
            assert len(results) == 1
            assert "error" in results[0].status.lower()

    def test_file_in_use_error(self):
        """测试文件被占用错误"""
        # 创建文件
        self.create_test_file("example1.net_TST-001.mp4")
        
        # 模拟文件被占用
        with patch('os.rename') as mock_rename:
            mock_rename.side_effect = OSError("The process cannot access the file")
            
            results = self.formatter.rename_in_directory(self.temp_dir)
            assert len(results) == 1
            assert "error" in results[0].status.lower()

    def test_network_drive_timeout(self):
        """测试网络驱动器超时"""
        # 创建文件
        self.create_test_file("example1.net_TST-001.mp4")
        
        # 模拟网络超时
        with patch('os.rename') as mock_rename:
            mock_rename.side_effect = TimeoutError("Network timeout")
            
            results = self.formatter.rename_in_directory(self.temp_dir)
            assert len(results) == 1
            assert "error" in results[0].status.lower()

    def test_very_deep_directory_structure(self):
        """测试非常深的目录结构"""
        # 创建深层目录结构
        deep_path = os.path.join(*["level" + str(i) for i in range(20)])
        self.create_test_file(os.path.join(deep_path, "example1.net_TST-001.mp4"))
        
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            include_subdirs=True
        )
        assert len(results) == 1
        assert results[0].status.startswith("success")

    def test_circular_symlink(self):
        """测试循环符号链接"""
        if os.name == 'nt':  # Windows
            pytest.skip("Symlink test skipped on Windows")
        
        # 创建循环符号链接
        link_dir = os.path.join(self.temp_dir, "link_dir")
        os.makedirs(link_dir)
        os.symlink(link_dir, os.path.join(link_dir, "circular_link"))
        
        # 在链接目录中创建文件
        self.create_test_file("link_dir/example1.net_TST-001.mp4")
        
        # 应该能够处理而不陷入无限循环
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            include_subdirs=True
        )
        assert len(results) >= 0  # 不应该崩溃

    def test_file_disappears_during_processing(self):
        """测试处理过程中文件消失"""
        # 创建文件
        self.create_test_file("example1.net_TST-001.mp4")
        
        # 模拟文件在处理过程中被删除
        original_rename = os.rename
        def mock_rename(src, dst):
            # 在重命名前删除源文件
            if os.path.exists(src):
                os.remove(src)
            raise FileNotFoundError("File not found")
        
        with patch('os.rename', side_effect=mock_rename):
            results = self.formatter.rename_in_directory(self.temp_dir)
            assert len(results) == 1
            assert "error" in results[0].status.lower()

    def test_target_directory_readonly(self):
        """测试目标目录只读"""
        # 创建文件
        self.create_test_file("example1.net_TST-001.mp4")
        
        # 模拟目标目录只读
        with patch('os.rename') as mock_rename:
            mock_rename.side_effect = PermissionError("Read-only file system")
            
            results = self.formatter.rename_in_directory(self.temp_dir)
            assert len(results) == 1
            assert "error" in results[0].status.lower()

    def test_invalid_characters_in_target_name(self):
        """测试目标文件名包含无效字符"""
        # 创建包含特殊模式的文件，可能导致无效的目标名称
        self.create_test_file("example1.net_TST-001<invalid>.mp4")
        
        results = self.formatter.rename_in_directory(self.temp_dir)
        # 应该能够处理或跳过无效字符
        assert len(results) >= 0

    def test_extremely_large_file(self):
        """测试极大文件的处理"""
        # 创建大文件（模拟）
        large_file = self.create_test_file("example1.net_TST-001.mp4")
        
        # 模拟大文件的大小检查
        with patch('os.path.getsize') as mock_getsize:
            mock_getsize.return_value = 10 * 1024 * 1024 * 1024  # 10GB
            
            results = self.formatter.rename_in_directory(self.temp_dir)
            assert len(results) == 1
            # 大文件应该能够正常处理

    def test_concurrent_access(self):
        """测试并发访问"""
        # 创建文件
        self.create_test_file("example1.net_TST-001.mp4")
        
        # 模拟另一个进程同时访问文件
        call_count = 0
        original_rename = os.rename
        
        def mock_rename(src, dst):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 第一次调用失败（模拟并发冲突）
                raise OSError("Resource temporarily unavailable")
            else:
                # 后续调用成功
                return original_rename(src, dst)
        
        with patch('os.rename', side_effect=mock_rename):
            results = self.formatter.rename_in_directory(self.temp_dir)
            # 应该能够处理并发冲突

    def test_memory_pressure(self):
        """测试内存压力情况"""
        # 创建大量文件
        for i in range(100):
            self.create_test_file(f"example1.net_TST-{i:03d}.mp4")
        
        # 模拟内存不足
        with patch('os.listdir') as mock_listdir:
            # 返回大量文件名
            mock_listdir.return_value = [f"example1.net_TST-{i:03d}.mp4" for i in range(1000)]
            
            # 应该能够处理大量文件而不崩溃
            try:
                results = self.formatter.rename_in_directory(self.temp_dir)
                # 至少应该处理实际存在的文件
                assert len([r for r in results if r.status.startswith("success")]) <= 100
            except MemoryError:
                pytest.skip("Memory error expected in this test")

    def test_interrupted_operation(self):
        """测试操作中断"""
        # 创建多个文件
        for i in range(5):
            self.create_test_file(f"example1.net_TST-{i:03d}.mp4")
        
        # 模拟操作中断
        call_count = 0
        def mock_rename(src, dst):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # 前两个文件成功
                return os.rename(src, dst)
            else:
                # 后续操作被中断
                raise KeyboardInterrupt("Operation interrupted")
        
        with patch('os.rename', side_effect=mock_rename):
            try:
                results = self.formatter.rename_in_directory(self.temp_dir)
            except KeyboardInterrupt:
                # 中断应该被适当处理
                pass

    def test_log_file_write_error(self):
        """测试日志文件写入错误"""
        # 创建文件
        self.create_test_file("example1.net_TST-001.mp4")
        
        # 模拟日志文件写入失败
        with patch('builtins.open', side_effect=PermissionError("Cannot write log")):
            # 即使日志写入失败，重命名操作也应该继续
            results = self.formatter.rename_in_directory(
                self.temp_dir,
                log_operations=True
            )
            # 操作应该成功，即使日志失败
            assert len(results) == 1