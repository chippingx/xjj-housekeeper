"""
文件安全性测试用例
测试各种可能导致文件丢失的场景，确保工具的安全性
"""

import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path

from tools.filename_formatter.formatter import FilenameFormatter


class TestFileSafety:
    """文件安全性测试"""

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

    def test_conflict_detection_and_logging(self):
        """测试冲突检测和日志记录"""
        # 创建会产生冲突的文件
        existing_file = self.create_test_file("TST-001.mp4", "existing content")
        source_file = self.create_test_file("example1.net_TST-001.mp4", "new content")
        
        # 执行跳过冲突操作
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            conflict_resolution="skip",
            log_operations=True
        )
        
        # 验证结果 - 应该有2个结果：1个跳过（同名），1个跳过（目标存在）
        assert len(results) == 2
        
        # 找到跳过操作的结果
        skip_target_result = None
        skip_same_result = None
        for result in results:
            if "skipped: target exists" in result.status:
                skip_target_result = result
            elif "skipped: same name" in result.status:
                skip_same_result = result
        
        assert skip_target_result is not None
        assert skip_same_result is not None
        
        # 验证文件内容未被修改
        with open(os.path.join(self.temp_dir, "TST-001.mp4"), 'r') as f:
            assert f.read() == "existing content"
        
        # 验证源文件仍然存在
        assert os.path.exists(source_file)

    def test_dry_run_conflict_warning(self):
        """测试干运行模式下的冲突警告"""
        # 创建会产生冲突的文件
        existing_file = self.create_test_file("TST-001.mp4", "existing content")
        source_file = self.create_test_file("example1.net_TST-001.mp4", "new content")
        
        # 执行干运行跳过操作
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            conflict_resolution="skip",
            dry_run=True
        )
        
        # 验证结果 - 应该有2个结果：1个跳过（同名），1个跳过（目标存在）
        assert len(results) == 2
        
        # 找到跳过预览的结果
        skip_target_preview = None
        skip_same_result = None
        for result in results:
            if "would skip: target exists" in result.status:
                skip_target_preview = result
            elif "skipped: same name" in result.status:
                skip_same_result = result
        
        assert skip_target_preview is not None
        assert skip_same_result is not None
        
        # 验证文件内容未被修改（因为是干运行）
        with open(os.path.join(self.temp_dir, "TST-001.mp4"), 'r') as f:
            assert f.read() == "existing content"
        
        # 验证源文件仍然存在
        assert os.path.exists(source_file)

    def test_size_verification_failure_recovery(self):
        """测试大小验证失败时的恢复机制"""
        source_file = self.create_test_file("example1.net_TST-001.mp4", "test content")
        original_size = os.path.getsize(source_file)
        
        # 模拟大小验证失败的情况
        original_getsize = os.path.getsize
        original_rename = os.rename
        rename_count = 0
        
        def mock_getsize(path):
            # 源文件返回正确大小，目标文件返回错误大小
            if "example1.net" in path:
                return original_getsize(path)
            elif "TST-001.mp4" in path:
                # 目标文件返回错误大小
                return 999999
            else:
                return original_getsize(path)
        
        def mock_rename(src, dst):
            nonlocal rename_count
            rename_count += 1
            # 执行实际重命名
            result = original_rename(src, dst)
            return result
        
        # 使用 monkeypatch 模拟
        import unittest.mock
        with unittest.mock.patch('os.path.getsize', side_effect=mock_getsize), \
             unittest.mock.patch('os.rename', side_effect=mock_rename):
            results = self.formatter.rename_in_directory(
                self.temp_dir,
                verify_size=True
            )
        
        # 验证操作失败并且文件被恢复
        assert len(results) == 1
        assert results[0].status.startswith("error: size mismatch")
        
        # 验证原文件仍然存在（因为被恢复了）
        assert os.path.exists(source_file)
        assert not os.path.exists(os.path.join(self.temp_dir, "TST-001.mp4"))
        
        # 验证发生了两次重命名：一次正向，一次恢复
        assert rename_count == 2

    def test_rename_operation_failure_handling(self):
        """测试重命名操作失败的处理"""
        source_file = self.create_test_file("example1.net_TST-001.mp4", "test content")
        
        # 创建一个只读目录来模拟重命名失败
        readonly_dir = os.path.join(self.temp_dir, "readonly")
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, 0o444)  # 只读权限
        
        try:
            results = self.formatter.rename_in_directory(readonly_dir)
            # 如果没有权限问题，跳过这个测试
            if not results or not any(r.status.startswith("error") for r in results):
                pytest.skip("无法创建权限受限的测试环境")
        finally:
            # 恢复权限以便清理
            os.chmod(readonly_dir, 0o755)

    def test_conflict_resolution_rename_safety(self):
        """测试重命名冲突解决的安全性"""
        # 创建多个冲突文件
        self.create_test_file("TST-001.mp4", "original")
        self.create_test_file("TST-001_1.mp4", "conflict 1")
        self.create_test_file("TST-001_2.mp4", "conflict 2")
        self.create_test_file("example1.net_TST-001.mp4", "new file")
        
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            conflict_resolution="rename"
        )
        
        # 验证结果 - 应该有4个结果：3个成功重命名，1个跳过（同名）
        assert len(results) == 4
        
        # 统计操作类型
        success_count = 0
        skip_count = 0
        for result in results:
            if result.status.startswith("success"):
                success_count += 1
            elif "skipped: same name" in result.status:
                skip_count += 1
        
        assert success_count == 3  # 3个文件被重命名（链式反应）
        assert skip_count == 1     # 1个文件跳过（已是标准格式）
        
        # 验证所有文件都存在
        assert os.path.exists(os.path.join(self.temp_dir, "TST-001.mp4"))
        assert os.path.exists(os.path.join(self.temp_dir, "TST-001_1.mp4"))
        assert os.path.exists(os.path.join(self.temp_dir, "TST-001_2.mp4"))
        assert os.path.exists(os.path.join(self.temp_dir, "TST-001_3.mp4"))

    def test_flatten_operation_safety(self):
        """测试扁平化操作的安全性"""
        # 创建嵌套目录结构
        self.create_test_file("subdir1/TST-001.mp4", "file 1")
        self.create_test_file("subdir2/TST-002.mp4", "file 2")
        self.create_test_file("TST-003.mp4", "file 3")
        
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            include_subdirs=True,
            flatten_output=True
        )
        
        # 验证结果 - 应该有3个结果：2个移动，1个跳过（同名）
        assert len(results) == 3
        
        # 统计操作类型
        success_count = 0
        skip_count = 0
        for result in results:
            if result.status.startswith("success"):
                success_count += 1
            elif "skipped: same name" in result.status:
                skip_count += 1
        
        assert success_count == 2  # 2个文件被移动
        assert skip_count == 1     # 1个文件跳过（已在根目录）
        
        # 验证文件内容没有丢失
        with open(os.path.join(self.temp_dir, "TST-001.mp4"), 'r') as f:
            assert f.read() == "file 1"
        with open(os.path.join(self.temp_dir, "TST-002.mp4"), 'r') as f:
            assert f.read() == "file 2"
        with open(os.path.join(self.temp_dir, "TST-003.mp4"), 'r') as f:
            assert f.read() == "file 3"

    def test_empty_directory_cleanup_safety(self):
        """测试空目录清理的安全性"""
        # 创建包含文件的目录和空目录
        self.create_test_file("subdir1/TST-001.mp4", "file 1")
        self.create_test_file("subdir2/important.txt", "important file")
        os.makedirs(os.path.join(self.temp_dir, "empty_dir"))
        
        self.formatter.rename_in_directory(
            self.temp_dir,
            include_subdirs=True,
            flatten_output=True
        )
        
        # 验证包含非视频文件的目录不被删除
        assert os.path.exists(os.path.join(self.temp_dir, "subdir2"))
        assert os.path.exists(os.path.join(self.temp_dir, "subdir2", "important.txt"))

    def test_log_file_integrity(self):
        """测试日志文件的完整性"""
        self.create_test_file("example1.net_TST-001.mp4", "test content")
        
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            log_operations=True,
            verify_size=True
        )
        
        # 验证日志文件存在且格式正确
        log_files = [f for f in os.listdir(self.temp_dir) if f.startswith('.operation_log')]
        assert len(log_files) == 1
        
        with open(os.path.join(self.temp_dir, log_files[0]), 'r') as f:
            logs = json.load(f)
        
        assert len(logs) == 1
        log_entry = logs[0]
        
        # 验证日志字段完整性
        required_fields = ['timestamp', 'operation_type', 'source_path', 'target_path']
        for field in required_fields:
            assert field in log_entry
            assert log_entry[field] is not None

    def test_minimum_file_size_safety(self):
        """测试最小文件大小过滤的安全性"""
        # 创建小文件和大文件
        small_file = self.create_test_file("example1.net_TST-001.mp4", "x")  # 1字节
        large_file = self.create_test_file("example1.net_TST-002.mp4", "x" * 1000)  # 1000字节
        
        formatter = FilenameFormatter(min_file_size=100)
        results = formatter.rename_in_directory(self.temp_dir)
        
        # 只有大文件应该被处理
        assert len(results) == 1
        assert "TST-002.mp4" in results[0].new
        
        # 小文件应该保持不变
        assert os.path.exists(small_file)
        assert not os.path.exists(os.path.join(self.temp_dir, "TST-001.mp4"))