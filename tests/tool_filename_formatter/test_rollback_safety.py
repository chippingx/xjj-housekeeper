"""
回滚功能安全性测试用例
测试回滚操作的各种场景，确保数据安全
"""

import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path

from tools.filename_formatter.formatter import FilenameFormatter
from tools.filename_formatter.rollback import rollback_operations


class TestRollbackSafety:
    """回滚功能安全性测试"""

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

    def test_simple_rename_rollback(self):
        """测试简单重命名的回滚"""
        # 创建源文件
        source_content = "original content"
        self.create_test_file("example1.net_TST-001.mp4", source_content)
        
        # 执行重命名
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            log_operations=True
        )
        
        assert len(results) == 1
        assert results[0].status.startswith("success")
        
        # 验证重命名成功
        target_path = os.path.join(self.temp_dir, "TST-001.mp4")
        assert os.path.exists(target_path)
        with open(target_path, 'r') as f:
            assert f.read() == source_content
        
        # 获取日志文件
        log_files = [f for f in os.listdir(self.temp_dir) if f.startswith('.operation_log')]
        log_file = os.path.join(self.temp_dir, log_files[0])
        
        # 执行回滚
        rollback_operations(log_file)
        
        # 验证回滚成功
        original_path = os.path.join(self.temp_dir, "example1.net_TST-001.mp4")
        assert os.path.exists(original_path)
        assert not os.path.exists(target_path)
        with open(original_path, 'r') as f:
            assert f.read() == source_content

    def test_multiple_files_rollback(self):
        """测试多文件回滚"""
        # 创建多个文件
        files = {
            "example1.net_TST-001.mp4": "content 1",
            "example1.net_TST-002.mp4": "content 2",
            "subdir/example1.net_TST-003.mp4": "content 3"
        }
        
        for path, content in files.items():
            self.create_test_file(path, content)
        
        # 执行重命名
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            include_subdirs=True,
            flatten_output=True,
            log_operations=True
        )
        
        assert len(results) == 3
        
        # 获取日志文件并执行回滚
        log_files = [f for f in os.listdir(self.temp_dir) if f.startswith('.operation_log')]
        log_file = os.path.join(self.temp_dir, log_files[0])
        
        rollback_operations(log_file)
        
        # 验证所有文件都被回滚
        for path, content in files.items():
            full_path = os.path.join(self.temp_dir, path)
            assert os.path.exists(full_path)
            with open(full_path, 'r') as f:
                assert f.read() == content

    def test_rollback_with_conflicts(self):
        """测试回滚时的冲突处理"""
        # 创建源文件
        self.create_test_file("example1.net_TST-001.mp4", "original")
        
        # 执行重命名
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            log_operations=True
        )
        
        # 验证重命名成功
        target_path = os.path.join(self.temp_dir, "TST-001.mp4")
        assert os.path.exists(target_path)
        
        # 在源位置创建新文件（模拟冲突）
        source_path = os.path.join(self.temp_dir, "example1.net_TST-001.mp4")
        with open(source_path, 'w') as f:
            f.write("conflicting content")
        
        # 获取日志文件并执行回滚
        log_files = [f for f in os.listdir(self.temp_dir) if f.startswith('.operation_log')]
        log_file = os.path.join(self.temp_dir, log_files[0])
        
        # 回滚应该跳过冲突文件（安全行为）
        rollback_operations(log_file)
        
        # 验证冲突文件保持不变，目标文件仍然存在
        with open(source_path, 'r') as f:
            assert f.read() == "conflicting content"
        assert os.path.exists(target_path)

    def test_rollback_dry_run(self):
        """测试回滚的干运行模式"""
        # 创建并重命名文件
        self.create_test_file("example1.net_TST-001.mp4", "test content")
        
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            log_operations=True
        )
        
        target_path = os.path.join(self.temp_dir, "TST-001.mp4")
        assert os.path.exists(target_path)
        
        # 获取日志文件并执行干运行回滚
        log_files = [f for f in os.listdir(self.temp_dir) if f.startswith('.operation_log')]
        log_file = os.path.join(self.temp_dir, log_files[0])
        
        rollback_operations(log_file, dry_run=True)
        
        # 验证文件状态没有改变（干运行）
        assert os.path.exists(target_path)
        assert not os.path.exists(os.path.join(self.temp_dir, "example1.net_TST-001.mp4"))

    def test_rollback_missing_target_file(self):
        """测试回滚时目标文件不存在的情况"""
        # 创建并重命名文件
        self.create_test_file("example1.net_TST-001.mp4", "test content")
        
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            log_operations=True
        )
        
        # 删除目标文件
        target_path = os.path.join(self.temp_dir, "TST-001.mp4")
        os.remove(target_path)
        
        # 获取日志文件并执行回滚
        log_files = [f for f in os.listdir(self.temp_dir) if f.startswith('.operation_log')]
        log_file = os.path.join(self.temp_dir, log_files[0])
        
        # 回滚应该报告错误但不崩溃
        rollback_operations(log_file)
        
        # 验证原文件没有被恢复（因为目标文件不存在）
        assert not os.path.exists(os.path.join(self.temp_dir, "example1.net_TST-001.mp4"))

    def test_rollback_log_generation(self):
        """测试回滚日志的生成"""
        # 创建并重命名文件
        self.create_test_file("example1.net_TST-001.mp4", "test content")
        
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            log_operations=True
        )
        
        # 获取日志文件并执行回滚
        log_files = [f for f in os.listdir(self.temp_dir) if f.startswith('.operation_log')]
        log_file = os.path.join(self.temp_dir, log_files[0])
        
        rollback_operations(log_file)
        
        # 验证回滚日志被创建
        rollback_log_files = [f for f in os.listdir(self.temp_dir) if f.endswith('_rollback.json')]
        assert len(rollback_log_files) == 1
        
        # 验证回滚日志内容
        rollback_log_file = os.path.join(self.temp_dir, rollback_log_files[0])
        with open(rollback_log_file, 'r') as f:
            rollback_log = json.load(f)
        
        # 验证回滚日志包含必要的字段
        assert 'rollback_timestamp' in rollback_log
        assert 'original_log_file' in rollback_log
        assert 'operations_rolled_back' in rollback_log
        assert 'success_count' in rollback_log
        assert 'error_count' in rollback_log
        assert rollback_log['operations_rolled_back'] == 1
        assert rollback_log['success_count'] == 1
        assert rollback_log['error_count'] == 0



    def test_corrupted_log_file_handling(self):
        """测试损坏日志文件的处理"""
        # 创建损坏的日志文件
        corrupted_log = os.path.join(self.temp_dir, "corrupted.json")
        with open(corrupted_log, 'w') as f:
            f.write("invalid json content")
        
        # 回滚应该优雅地处理错误
        try:
            rollback_operations(corrupted_log)
        except Exception as e:
            # 应该有适当的错误处理
            assert "JSON" in str(e) or "解析" in str(e)

    def test_empty_log_file_handling(self):
        """测试空日志文件的处理"""
        # 创建空日志文件
        empty_log = os.path.join(self.temp_dir, "empty.json")
        with open(empty_log, 'w') as f:
            f.write("[]")
        
        # 回滚应该正常处理空日志
        rollback_operations(empty_log)
        
        # 应该没有错误，也没有操作