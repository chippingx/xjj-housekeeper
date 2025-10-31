"""
性能和压力测试用例
测试工具在各种负载下的性能表现
"""

import os
import time
import tempfile
import shutil
import pytest
from pathlib import Path

from tools.filename_formatter.formatter import FilenameFormatter


class TestPerformance:
    """性能测试"""

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

    def test_large_number_of_files(self):
        """测试大量文件的处理性能"""
        # 创建1000个文件
        file_count = 1000
        start_time = time.time()
        
        for i in range(file_count):
            self.create_test_file(f"example1.net_TST-{i:04d}.mp4")
        
        creation_time = time.time() - start_time
        print(f"创建{file_count}个文件耗时: {creation_time:.2f}秒")
        
        # 测试重命名性能
        start_time = time.time()
        results = self.formatter.rename_in_directory(self.temp_dir)
        processing_time = time.time() - start_time
        
        print(f"处理{file_count}个文件耗时: {processing_time:.2f}秒")
        print(f"平均每个文件: {processing_time/file_count*1000:.2f}毫秒")
        
        assert len(results) == file_count
        assert processing_time < 30  # 应该在30秒内完成
        
        # 验证所有文件都被正确重命名
        success_count = len([r for r in results if r.status.startswith("success")])
        assert success_count == file_count

    def test_deep_directory_structure_performance(self):
        """测试深层目录结构的性能"""
        # 创建深层目录结构，每层10个目录，5层深
        start_time = time.time()
        
        file_count = 0
        for level1 in range(5):
            for level2 in range(5):
                for level3 in range(5):
                    dir_path = f"level1_{level1}/level2_{level2}/level3_{level3}"
                    for file_idx in range(2):
                        self.create_test_file(
                            f"{dir_path}/example1.net_TST-{file_count:04d}.mp4"
                        )
                        file_count += 1
        
        creation_time = time.time() - start_time
        print(f"创建深层结构({file_count}个文件)耗时: {creation_time:.2f}秒")
        
        # 测试递归处理性能
        start_time = time.time()
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            include_subdirs=True
        )
        processing_time = time.time() - start_time
        
        print(f"递归处理{file_count}个文件耗时: {processing_time:.2f}秒")
        
        assert len(results) == file_count
        assert processing_time < 20  # 应该在20秒内完成

    def test_large_file_handling_performance(self):
        """测试大文件处理性能"""
        # 创建几个大文件（模拟）
        large_files = []
        for i in range(10):
            filename = f"example1.net_TST-{i:03d}.mp4"
            file_path = self.create_test_file(filename, "x" * 1024 * 1024)  # 1MB内容
            large_files.append(file_path)
        
        start_time = time.time()
        results = self.formatter.rename_in_directory(self.temp_dir)
        processing_time = time.time() - start_time
        
        print(f"处理10个大文件耗时: {processing_time:.2f}秒")
        
        assert len(results) == 10
        assert processing_time < 5  # 应该在5秒内完成

    def test_mixed_file_sizes_performance(self):
        """测试混合文件大小的性能"""
        # 创建不同大小的文件
        file_count = 100
        
        for i in range(file_count):
            if i % 10 == 0:
                # 每10个文件中有1个大文件
                content = "x" * (1024 * 100)  # 100KB
            else:
                content = "small content"
            
            self.create_test_file(f"example1.net_TST-{i:03d}.mp4", content)
        
        start_time = time.time()
        results = self.formatter.rename_in_directory(self.temp_dir)
        processing_time = time.time() - start_time
        
        print(f"处理{file_count}个混合大小文件耗时: {processing_time:.2f}秒")
        
        assert len(results) == file_count
        assert processing_time < 10  # 应该在10秒内完成

    def test_dry_run_performance(self):
        """测试干运行模式的性能"""
        # 创建大量文件
        file_count = 500
        for i in range(file_count):
            self.create_test_file(f"example1.net_TST-{i:04d}.mp4")
        
        # 测试干运行性能
        start_time = time.time()
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            dry_run=True
        )
        dry_run_time = time.time() - start_time
        
        # 测试实际运行性能
        start_time = time.time()
        results_actual = self.formatter.rename_in_directory(self.temp_dir)
        actual_run_time = time.time() - start_time
        
        print(f"干运行{file_count}个文件耗时: {dry_run_time:.2f}秒")
        print(f"实际运行{file_count}个文件耗时: {actual_run_time:.2f}秒")
        
        # 干运行应该比实际运行快
        assert dry_run_time < actual_run_time
        assert len(results) == len(results_actual) == file_count

    def test_logging_performance_impact(self):
        """测试日志记录对性能的影响"""
        # 创建文件
        file_count = 200
        for i in range(file_count):
            self.create_test_file(f"example1.net_TST-{i:03d}.mp4")
        
        # 测试不记录日志的性能
        start_time = time.time()
        results_no_log = self.formatter.rename_in_directory(
            self.temp_dir,
            log_operations=False
        )
        no_log_time = time.time() - start_time
        
        # 恢复文件名以便重新测试
        for result in results_no_log:
            if result.status.startswith("success"):
                os.rename(result.new, result.original)
        
        # 测试记录日志的性能
        start_time = time.time()
        results_with_log = self.formatter.rename_in_directory(
            self.temp_dir,
            log_operations=True
        )
        with_log_time = time.time() - start_time
        
        print(f"无日志处理{file_count}个文件耗时: {no_log_time:.2f}秒")
        print(f"有日志处理{file_count}个文件耗时: {with_log_time:.2f}秒")
        print(f"日志开销: {((with_log_time - no_log_time) / no_log_time * 100):.1f}%")
        
        # 日志开销应该在合理范围内（不超过50%）
        overhead = (with_log_time - no_log_time) / no_log_time
        assert overhead < 0.5

    def test_flatten_performance(self):
        """测试扁平化操作的性能"""
        # 创建多层目录结构
        file_count = 0
        for level1 in range(10):
            for level2 in range(5):
                dir_path = f"level1_{level1}/level2_{level2}"
                for file_idx in range(3):
                    self.create_test_file(
                        f"{dir_path}/example1.net_TST-{file_count:04d}.mp4"
                    )
                    file_count += 1
        
        # 测试扁平化性能
        start_time = time.time()
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            include_subdirs=True,
            flatten_output=True
        )
        flatten_time = time.time() - start_time
        
        print(f"扁平化{file_count}个文件耗时: {flatten_time:.2f}秒")
        
        assert len(results) == file_count
        assert flatten_time < 15  # 应该在15秒内完成

    def test_conflict_resolution_performance(self):
        """测试冲突解决的性能影响"""
        # 创建会产生冲突的文件
        file_count = 100
        
        # 创建目标文件（会产生冲突）
        for i in range(file_count // 2):
            self.create_test_file(f"TST-{i:03d}.mp4", "existing content")
        
        # 创建源文件
        for i in range(file_count):
            self.create_test_file(f"example1.net_TST-{i:03d}.mp4", "new content")
        
        # 测试跳过冲突的性能
        start_time = time.time()
        results_skip = self.formatter.rename_in_directory(
            self.temp_dir,
            conflict_resolution="skip"
        )
        skip_time = time.time() - start_time
        
        # 恢复文件以便重新测试
        for result in results_skip:
            if result.status.startswith("success"):
                os.rename(result.new, result.original)
        
        # 测试重命名冲突的性能
        start_time = time.time()
        results_rename = self.formatter.rename_in_directory(
            self.temp_dir,
            conflict_resolution="rename"
        )
        rename_time = time.time() - start_time
        
        print(f"跳过冲突处理{file_count}个文件耗时: {skip_time:.2f}秒")
        print(f"重命名冲突处理{file_count}个文件耗时: {rename_time:.2f}秒")
        
        # 重命名冲突应该比跳过稍慢，但不应该慢太多
        assert rename_time < skip_time * 2

    def test_memory_usage_stability(self):
        """测试内存使用的稳定性"""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not available")
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # 处理多批文件，检查内存是否稳定
        for batch in range(5):
            # 创建文件
            batch_size = 100
            for i in range(batch_size):
                self.create_test_file(f"batch{batch}_example1.net_TST-{i:03d}.mp4")
            
            # 处理文件
            results = self.formatter.rename_in_directory(self.temp_dir)
            
            # 清理文件
            for result in results:
                if os.path.exists(result.new):
                    os.remove(result.new)
            
            # 强制垃圾回收
            gc.collect()
            
            current_memory = process.memory_info().rss
            memory_growth = (current_memory - initial_memory) / 1024 / 1024  # MB
            
            print(f"批次 {batch + 1} 内存增长: {memory_growth:.2f} MB")
            
            # 内存增长应该在合理范围内（不超过50MB）
            assert memory_growth < 50

    @pytest.mark.slow
    def test_extreme_load(self):
        """极限负载测试（标记为慢速测试）"""
        # 创建大量文件和深层结构
        file_count = 0
        
        # 创建10层深的目录结构
        for l1 in range(3):
            for l2 in range(3):
                for l3 in range(3):
                    for l4 in range(3):
                        for l5 in range(3):
                            dir_path = f"l1_{l1}/l2_{l2}/l3_{l3}/l4_{l4}/l5_{l5}"
                            for file_idx in range(2):
                                self.create_test_file(
                                    f"{dir_path}/example1.net_TST-{file_count:05d}.mp4"
                                )
                                file_count += 1
        
        print(f"极限测试：创建了{file_count}个文件")
        
        start_time = time.time()
        results = self.formatter.rename_in_directory(
            self.temp_dir,
            include_subdirs=True,
            flatten_output=True,
            log_operations=True
        )
        processing_time = time.time() - start_time
        
        print(f"极限负载处理耗时: {processing_time:.2f}秒")
        print(f"处理速度: {file_count/processing_time:.1f} 文件/秒")
        
        assert len(results) == file_count
        # 极限负载应该在合理时间内完成（根据文件数量调整）
        assert processing_time < file_count * 0.1  # 每个文件不超过100ms