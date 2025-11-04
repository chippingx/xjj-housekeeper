#!/usr/bin/env python3
"""
测试video_code提取功能

测试覆盖：
1. 标准格式的video_code提取
2. 边界情况和异常处理
3. 自定义正则表达式支持
4. 性能测试
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.video_info_collector.metadata import VideoInfo


class TestVideoCodeExtraction(unittest.TestCase):
    """测试video_code提取功能"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_file(self, filename: str) -> str:
        """创建测试文件"""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w') as f:
            f.write("test content")
        return file_path
    
    def test_standard_video_code_formats(self):
        """测试标准video_code格式"""
        test_cases = [
            # (filename, expected_video_code)
            ("ABC-123.mp4", "ABC-123"),
            ("XYZ-456.mkv", "XYZ-456"),
            ("DEF-789.avi", "DEF-789"),
            ("GHI-001.mov", "GHI-001"),
            ("JKL-999.wmv", "JKL-999"),
            
            # 带前缀的情况
            ("[HD]ABC-123.mp4", "ABC-123"),
            ("(1080p)XYZ-456.mkv", "XYZ-456"),
            ("【高清】DEF-789.avi", "DEF-789"),
            
            # 带后缀的情况
            ("ABC-123_part1.mp4", "ABC-123"),
            ("XYZ-456.part2.mkv", "XYZ-456"),
            ("DEF-789-uncensored.avi", "DEF-789"),
            
            # 复杂格式
            ("ABC-123-CD1.mp4", "ABC-123"),
            ("XYZ-456_1080p_x264.mkv", "XYZ-456"),
        ]
        
        for filename, expected_code in test_cases:
            with self.subTest(filename=filename):
                file_path = self._create_test_file(filename)
                video_info = VideoInfo(file_path)
                self.assertEqual(video_info.video_code, expected_code,
                               f"文件 {filename} 应该提取出 {expected_code}")
    
    def test_edge_cases(self):
        """测试边界情况"""
        edge_cases = [
            # (filename, expected_video_code)
            ("no-code-here.mp4", None),  # 没有匹配的格式
            ("ABC.mp4", None),  # 只有字母没有数字
            ("123.mp4", None),  # 只有数字没有字母
            ("-123.mp4", None),  # 格式不完整
            ("ABC-.mp4", None),  # 格式不完整
            ("ABC-123", "ABC-123"),  # 没有扩展名
            ("ABC-123.txt", "ABC-123"),  # 非视频扩展名
            ("", None),  # 空文件名
            ("ABC-123-DEF-456.mp4", "ABC-123"),  # 多个匹配，取第一个
        ]
        
        for filename, expected_code in edge_cases:
            with self.subTest(filename=filename):
                if filename:  # 跳过空文件名
                    file_path = self._create_test_file(filename)
                    video_info = VideoInfo(file_path)
                    self.assertEqual(video_info.video_code, expected_code,
                                   f"文件 {filename} 应该提取出 {expected_code}")
    
    def test_unicode_and_special_characters(self):
        """测试Unicode和特殊字符"""
        unicode_cases = [
            ("中文-ABC-123.mp4", "ABC-123"),
            ("ABC-123-中文.mp4", "ABC-123"),
            ("ABC-123 (中文字幕).mp4", "ABC-123"),
            ("ABC-123_日本語.mp4", "ABC-123"),
            ("ABC-123&special.mp4", "ABC-123"),
            ("ABC-123@#$%.mp4", "ABC-123"),
        ]
        
        for filename, expected_code in unicode_cases:
            with self.subTest(filename=filename):
                file_path = self._create_test_file(filename)
                video_info = VideoInfo(file_path)
                self.assertEqual(video_info.video_code, expected_code,
                               f"文件 {filename} 应该提取出 {expected_code}")
    
    def test_case_sensitivity(self):
        """测试大小写敏感性"""
        case_cases = [
            ("abc-123.mp4", "abc-123"),  # 小写
            ("ABC-123.mp4", "ABC-123"),  # 大写
            ("Abc-123.mp4", "Abc-123"),  # 混合大小写
            ("ABC-abc.mp4", "ABC-abc"),  # 数字部分是字母
        ]
        
        for filename, expected_code in case_cases:
            with self.subTest(filename=filename):
                file_path = self._create_test_file(filename)
                video_info = VideoInfo(file_path)
                self.assertEqual(video_info.video_code, expected_code,
                               f"文件 {filename} 应该提取出 {expected_code}")
    
    def test_custom_regex_patterns(self):
        """测试自定义正则表达式模式"""
        # 这个测试假设VideoInfo类支持自定义正则表达式
        # 如果不支持，这个测试可以跳过或者作为未来功能的占位符
        pass
    
    def test_performance_with_large_batch(self):
        """测试大批量文件的性能"""
        import time
        
        # 创建1000个测试文件
        filenames = [f"TEST-{i:03d}.mp4" for i in range(1000)]
        file_paths = []
        
        for filename in filenames:
            file_path = self._create_test_file(filename)
            file_paths.append(file_path)
        
        # 测试批量提取性能
        start_time = time.time()
        
        for file_path in file_paths:
            video_info = VideoInfo(file_path)
            self.assertIsNotNone(video_info.video_code)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 性能要求：1000个文件应该在1秒内完成
        self.assertLess(processing_time, 1.0,
                       f"处理1000个文件耗时 {processing_time:.2f}秒，超过1秒限制")
    
    def test_video_code_consistency(self):
        """测试video_code提取的一致性"""
        filename = "ABC-123.mp4"
        file_path = self._create_test_file(filename)
        
        # 多次创建VideoInfo对象，确保结果一致
        codes = []
        for _ in range(10):
            video_info = VideoInfo(file_path)
            codes.append(video_info.video_code)
        
        # 所有结果应该相同
        self.assertTrue(all(code == codes[0] for code in codes),
                       "多次提取的video_code应该保持一致")
    
    def test_path_vs_filename_extraction(self):
        """测试从路径vs文件名提取的区别"""
        # 创建嵌套目录结构
        nested_dir = os.path.join(self.temp_dir, "ABC-999", "subfolder")
        os.makedirs(nested_dir, exist_ok=True)
        
        filename = "XYZ-123.mp4"
        file_path = os.path.join(nested_dir, filename)
        
        with open(file_path, 'w') as f:
            f.write("test content")
        
        video_info = VideoInfo(file_path)
        
        # 应该从文件名而不是路径提取
        self.assertEqual(video_info.video_code, "XYZ-123",
                        "应该从文件名而不是路径提取video_code")


class TestVideoCodeExtractionIntegration(unittest.TestCase):
    """video_code提取的集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_video_code_in_database_storage(self):
        """测试video_code在数据库存储中的集成"""
        # 这个测试需要等SQLiteStorage更新后实现
        pass
    
    def test_video_code_in_csv_export(self):
        """测试video_code在CSV导出中的集成"""
        # 这个测试需要等CSVWriter更新后实现
        pass


if __name__ == '__main__':
    unittest.main()