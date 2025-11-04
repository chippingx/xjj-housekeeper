#!/usr/bin/env python3
"""
测试轻量级指纹系统

测试覆盖：
1. 指纹生成的正确性和一致性
2. 指纹冲突检测和处理
3. 不同文件属性对指纹的影响
4. 性能和内存使用
"""

import unittest
import tempfile
import os
import time
import hashlib
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.video_info_collector.metadata import VideoInfo


class TestFingerprintGeneration(unittest.TestCase):
    """测试指纹生成功能"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_file(self, filename: str, content: str = "test content", 
                         size: int = None) -> str:
        """创建测试文件"""
        file_path = os.path.join(self.temp_dir, filename)
        
        if size:
            # 创建指定大小的文件
            with open(file_path, 'wb') as f:
                f.write(b'0' * size)
        else:
            with open(file_path, 'w') as f:
                f.write(content)
        
        return file_path
    
    def test_fingerprint_consistency(self):
        """测试指纹生成的一致性"""
        filename = "ABC-123.mp4"
        file_path = self._create_test_file(filename)
        
        # 多次生成指纹，确保结果一致
        fingerprints = []
        for _ in range(10):
            video_info = VideoInfo(file_path)
            fingerprints.append(video_info.file_fingerprint)
        
        # 所有指纹应该相同
        self.assertTrue(all(fp == fingerprints[0] for fp in fingerprints),
                       "同一文件的指纹应该保持一致")
        
        # 指纹应该是32字符的MD5哈希
        self.assertEqual(len(fingerprints[0]), 32,
                        "指纹应该是32字符的MD5哈希")
        self.assertTrue(all(c in '0123456789abcdef' for c in fingerprints[0]),
                       "指纹应该只包含十六进制字符")
    
    def test_different_files_different_fingerprints(self):
        """测试不同文件生成不同指纹"""
        test_files = [
            ("ABC-123.mp4", "content1"),
            ("XYZ-456.mkv", "content2"),
            ("DEF-789.avi", "content3"),
        ]
        
        fingerprints = []
        for filename, content in test_files:
            file_path = self._create_test_file(filename, content)
            video_info = VideoInfo(file_path)
            fingerprints.append(video_info.file_fingerprint)
        
        # 所有指纹应该不同
        self.assertEqual(len(set(fingerprints)), len(fingerprints),
                        "不同文件应该生成不同的指纹")
    
    def test_same_content_different_names(self):
        """测试相同内容不同文件名的指纹"""
        content = "same content"
        
        file1 = self._create_test_file("ABC-123.mp4", content)
        file2 = self._create_test_file("XYZ-456.mkv", content)
        
        video_info1 = VideoInfo(file1)
        video_info2 = VideoInfo(file2)
        
        # 文件名不同，指纹应该不同（因为指纹包含文件名）
        self.assertNotEqual(video_info1.file_fingerprint, 
                           video_info2.file_fingerprint,
                           "相同内容不同文件名应该生成不同指纹")
    
    def test_file_size_impact(self):
        """测试文件大小对指纹的影响"""
        filename = "ABC-123.mp4"
        
        # 创建不同大小的文件
        file1 = self._create_test_file(filename, size=1024)
        os.remove(file1)  # 删除后重新创建
        
        file2 = self._create_test_file(filename, size=2048)
        
        video_info1 = VideoInfo(file1) if os.path.exists(file1) else None
        video_info2 = VideoInfo(file2)
        
        # 由于文件1被删除，我们创建两个不同大小的文件来测试
        file1_new = self._create_test_file("test1_" + filename, size=1024)
        file2_new = self._create_test_file("test2_" + filename, size=2048)
        
        video_info1_new = VideoInfo(file1_new)
        video_info2_new = VideoInfo(file2_new)
        
        # 不同大小应该产生不同指纹
        self.assertNotEqual(video_info1_new.file_fingerprint,
                           video_info2_new.file_fingerprint,
                           "不同文件大小应该生成不同指纹")
    
    def test_modification_time_impact(self):
        """测试修改时间对指纹的影响"""
        filename = "ABC-123.mp4"
        file_path = self._create_test_file(filename)
        
        # 获取初始指纹
        video_info1 = VideoInfo(file_path)
        initial_fingerprint = video_info1.file_fingerprint
        
        # 等待一秒后修改文件
        time.sleep(1.1)
        with open(file_path, 'a') as f:
            f.write("additional content")
        
        # 重新生成指纹
        video_info2 = VideoInfo(file_path)
        new_fingerprint = video_info2.file_fingerprint
        
        # 修改时间变化应该产生不同指纹
        self.assertNotEqual(initial_fingerprint, new_fingerprint,
                           "文件修改后应该生成不同指纹")
    
    def test_fingerprint_components(self):
        """测试指纹组成部分"""
        filename = "ABC-123.mp4"
        file_path = self._create_test_file(filename, "test content")
        
        video_info = VideoInfo(file_path)
        
        # 验证指纹是基于预期的组件生成的
        # 这需要访问VideoInfo的内部实现来验证
        # 暂时只验证指纹格式
        self.assertIsNotNone(video_info.file_fingerprint)
        self.assertIsInstance(video_info.file_fingerprint, str)
        self.assertEqual(len(video_info.file_fingerprint), 32)
    
    def test_fingerprint_collision_detection(self):
        """测试指纹冲突检测"""
        # 创建大量文件来测试潜在冲突
        fingerprints = set()
        collision_count = 0
        
        for i in range(1000):
            filename = f"test_{i:04d}.mp4"
            content = f"content_{i}"
            file_path = self._create_test_file(filename, content)
            
            video_info = VideoInfo(file_path)
            fingerprint = video_info.file_fingerprint
            
            if fingerprint in fingerprints:
                collision_count += 1
            else:
                fingerprints.add(fingerprint)
        
        # MD5冲突应该极其罕见
        self.assertEqual(collision_count, 0,
                        f"在1000个文件中发现 {collision_count} 个指纹冲突")
    
    def test_performance_large_files(self):
        """测试大文件的指纹生成性能"""
        # 创建一个较大的文件 (10MB)
        large_file = self._create_test_file("large_file.mp4", size=10*1024*1024)
        
        start_time = time.time()
        video_info = VideoInfo(large_file)
        fingerprint = video_info.file_fingerprint
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # 10MB文件的指纹生成应该在0.1秒内完成
        self.assertLess(processing_time, 0.1,
                       f"10MB文件指纹生成耗时 {processing_time:.3f}秒，超过0.1秒限制")
        
        self.assertIsNotNone(fingerprint)
        self.assertEqual(len(fingerprint), 32)
    
    def test_memory_usage_batch_processing(self):
        """测试批量处理的内存使用"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # 创建并处理100个文件
        fingerprints = []
        for i in range(100):
            filename = f"batch_{i:03d}.mp4"
            file_path = self._create_test_file(filename, f"content_{i}")
            
            video_info = VideoInfo(file_path)
            fingerprints.append(video_info.file_fingerprint)
        
        # 强制垃圾回收
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 内存增长应该合理（小于50MB）
        max_memory_mb = 50 * 1024 * 1024
        self.assertLess(memory_increase, max_memory_mb,
                       f"处理100个文件内存增长 {memory_increase/1024/1024:.1f}MB，"
                       f"超过50MB限制")


class TestFingerprintIntegration(unittest.TestCase):
    """指纹系统的集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_fingerprint_in_move_detection(self):
        """测试指纹在移动检测中的应用"""
        # 这个测试需要等智能合并功能实现后完成
        pass
    
    def test_fingerprint_database_storage(self):
        """测试指纹在数据库存储中的集成"""
        # 这个测试需要等SQLiteStorage更新后实现
        pass
    
    def test_fingerprint_duplicate_detection(self):
        """测试指纹在重复文件检测中的应用"""
        # 创建两个相同内容但不同路径的文件
        content = "duplicate content"
        
        file1 = os.path.join(self.temp_dir, "folder1", "ABC-123.mp4")
        file2 = os.path.join(self.temp_dir, "folder2", "ABC-123.mp4")
        
        os.makedirs(os.path.dirname(file1), exist_ok=True)
        os.makedirs(os.path.dirname(file2), exist_ok=True)
        
        with open(file1, 'w') as f:
            f.write(content)
        with open(file2, 'w') as f:
            f.write(content)
        
        video_info1 = VideoInfo(file1)
        video_info2 = VideoInfo(file2)
        
        # 相同内容和文件名应该生成相同指纹
        # （这取决于指纹算法的具体实现）
        # 如果指纹包含完整路径，则会不同
        # 如果只包含文件名，则会相同
        
        # 暂时验证指纹都能正常生成
        self.assertIsNotNone(video_info1.file_fingerprint)
        self.assertIsNotNone(video_info2.file_fingerprint)


if __name__ == '__main__':
    unittest.main()