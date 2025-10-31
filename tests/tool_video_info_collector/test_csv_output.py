"""
测试CSV输出功能
"""

import csv
import os
import tempfile
import unittest
from datetime import datetime

from tools.video_info_collector.csv_writer import CSVWriter
from tools.video_info_collector.metadata import VideoInfo


class TestCSVWriter(unittest.TestCase):
    """测试CSVWriter类"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.csv_file_path = os.path.join(self.temp_dir, "test_videos.csv")
        self.csv_writer = CSVWriter()
        
        # 创建测试数据
        self.test_video_infos = []
        for i in range(3):
            video_info = VideoInfo(f"/path/to/video_{i}.mp4", tags=[f"tag{i}", "test"], logical_path=f"test/path_{i}")
            video_info.width = 1920
            video_info.height = 1080
            video_info.duration = 120.5 + i * 10
            video_info.video_codec = "h264"
            video_info.audio_codec = "aac"
            video_info.file_size = 75000000 + i * 1000000
            video_info.bit_rate = 5000000
            video_info.frame_rate = 30.0
            self.test_video_infos.append(video_info)
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.csv_file_path):
            os.remove(self.csv_file_path)
        os.rmdir(self.temp_dir)
    
    def test_csv_writer_initialization(self):
        """测试CSV写入器初始化"""
        writer = CSVWriter()
        self.assertIsInstance(writer, CSVWriter)
        
        # 测试自定义编码
        writer_utf8 = CSVWriter(encoding='utf-8')
        self.assertEqual(writer_utf8.encoding, 'utf-8')
    
    def test_write_video_infos_to_csv(self):
        """测试写入视频信息到CSV文件"""
        self.csv_writer.write_video_infos(self.test_video_infos, self.csv_file_path)
        
        # 验证文件是否创建
        self.assertTrue(os.path.exists(self.csv_file_path))
        
        # 验证文件内容
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            self.assertEqual(len(rows), 3)
            
            # 验证第一行数据
            first_row = rows[0]
            self.assertEqual(first_row['filename'], 'video_0.mp4')
            self.assertEqual(first_row['width'], '1920')
            self.assertEqual(first_row['height'], '1080')
            self.assertEqual(first_row['resolution'], '1920x1080')
            self.assertEqual(first_row['duration'], '120.50')
            self.assertEqual(first_row['duration_formatted'], '00:02:00')
            self.assertEqual(first_row['video_codec'], 'h264')
            self.assertEqual(first_row['audio_codec'], 'aac')
            self.assertEqual(first_row['file_size'], '75000000')
            self.assertEqual(first_row['bit_rate'], '5000000')
    
    def test_write_empty_list(self):
        """测试写入空列表"""
        self.csv_writer.write_video_infos([], self.csv_file_path)
        
        # 验证文件是否创建（只有标题行）
        self.assertTrue(os.path.exists(self.csv_file_path))
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 0)
    
    def test_append_to_existing_csv(self):
        """测试追加到现有CSV文件"""
        # 先写入一些数据
        self.csv_writer.write_video_infos(self.test_video_infos[:2], self.csv_file_path)
        
        # 追加更多数据
        self.csv_writer.append_video_infos(self.test_video_infos[2:], self.csv_file_path)
        
        # 验证总数据量
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 3)
    
    def test_append_to_nonexistent_csv(self):
        """测试追加到不存在的CSV文件"""
        # 追加到不存在的文件应该创建新文件
        self.csv_writer.append_video_infos(self.test_video_infos, self.csv_file_path)
        
        self.assertTrue(os.path.exists(self.csv_file_path))
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 3)
    
    def test_csv_headers(self):
        """测试CSV标题行"""
        expected_headers = [
            'file_path', 'filename', 'width', 'height', 'resolution',
            'duration', 'duration_formatted', 'video_codec', 'audio_codec',
            'file_size', 'bit_rate', 'frame_rate', 'created_time', 'tags', 'logical_path'
        ]
        
        self.csv_writer.write_video_infos(self.test_video_infos[:1], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = next(reader)
            self.assertEqual(headers, expected_headers)
    
    def test_handle_none_values(self):
        """测试处理None值"""
        # 创建包含None值的视频信息
        video_info = VideoInfo("/path/to/incomplete_video.mp4")
        # 不设置其他属性，保持为None
        
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            
            # None值应该被转换为空字符串
            self.assertEqual(row['width'], '')
            self.assertEqual(row['height'], '')
            self.assertEqual(row['duration'], '')
            self.assertEqual(row['video_codec'], '')
            self.assertEqual(row['audio_codec'], '')
            self.assertEqual(row['bit_rate'], '')
    
    def test_handle_special_characters(self):
        """测试处理特殊字符"""
        video_info = VideoInfo("/path/to/视频,文件\"with'special.mp4")
        video_info.video_codec = "h264,profile=high"
        video_info.width = 1920
        video_info.height = 1080
        
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            
            # 验证特殊字符被正确处理
            self.assertEqual(row['filename'], '视频,文件"with\'special.mp4')
            self.assertEqual(row['video_codec'], 'h264,profile=high')
    
    def test_file_size_formatting(self):
        """测试文件大小格式化"""
        video_info = VideoInfo("/path/to/video.mp4")
        video_info.file_size = 1073741824  # 1GB
        
        # 测试默认格式（字节）
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            self.assertEqual(row['file_size'], '1073741824')
    
    def test_read_csv_file(self):
        """测试读取CSV文件"""
        # 先写入数据
        self.csv_writer.write_video_infos(self.test_video_infos, self.csv_file_path)
        
        # 读取数据
        video_infos = self.csv_writer.read_csv_file(self.csv_file_path)
        
        self.assertEqual(len(video_infos), 3)
        
        # 验证第一个视频信息
        first_video = video_infos[0]
        self.assertEqual(first_video['filename'], 'video_0.mp4')
        self.assertEqual(first_video['width'], '1920')
        self.assertEqual(first_video['height'], '1080')
    
    def test_read_nonexistent_csv(self):
        """测试读取不存在的CSV文件"""
        nonexistent_path = "/path/to/nonexistent.csv"
        
        with self.assertRaises(FileNotFoundError):
            self.csv_writer.read_csv_file(nonexistent_path)
    
    def test_custom_delimiter(self):
        """测试自定义分隔符"""
        writer = CSVWriter(delimiter=';')
        writer.write_video_infos(self.test_video_infos[:1], self.csv_file_path)
        
        # 验证使用了正确的分隔符
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            self.assertIn(';', content)
            self.assertNotIn(',', content.split('\n')[0])  # 标题行不应该有逗号

    def test_frame_rate_formatting(self):
        """测试frame_rate格式化 - 四舍五入到整数"""
        video_info = VideoInfo("/path/to/video.mp4")
        video_info.frame_rate = 29.97  # 常见的帧率
        
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            # 29.97应该四舍五入为30
            self.assertEqual(row['frame_rate'], '30')
        
        # 测试其他帧率值
        test_cases = [
            (23.976, '24'),
            (25.0, '25'),
            (59.94, '60'),
            (30.5, '30'),  # Python的银行家舍入：30.5 -> 30 (偶数)
            (31.5, '32'),  # Python的银行家舍入：31.5 -> 32 (偶数)
            (24.4, '24'),
        ]
        
        for input_rate, expected_output in test_cases:
            video_info.frame_rate = input_rate
            self.csv_writer.write_video_infos([video_info], self.csv_file_path)
            
            with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                row = next(reader)
                self.assertEqual(row['frame_rate'], expected_output, 
                               f"Frame rate {input_rate} should round to {expected_output}")

    def test_created_time_formatting(self):
        """测试created_time格式化 - 截取到秒"""
        video_info = VideoInfo("/path/to/video.mp4")
        
        # 测试带毫秒的ISO格式时间
        video_info.created_time = datetime(2024, 1, 15, 14, 30, 45, 123456)
        
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            # 应该截取到秒，不包含毫秒
            self.assertEqual(row['created_time'], '2024-01-15T14:30:45')
        
        # 测试已经没有毫秒的时间
        video_info.created_time = datetime(2024, 1, 15, 14, 30, 45)
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            self.assertEqual(row['created_time'], '2024-01-15T14:30:45')

    def test_duration_formatting(self):
        """测试duration格式化 - 保留2位小数"""
        video_info = VideoInfo("/path/to/video.mp4")
        
        # 测试各种duration值
        test_cases = [
            (120.123456, '120.12'),
            (60.0, '60.00'),
            (3661.789, '3661.79'),
            (0.5, '0.50'),
            (1.999, '2.00'),  # 测试四舍五入
        ]
        
        for input_duration, expected_output in test_cases:
            video_info.duration = input_duration
            self.csv_writer.write_video_infos([video_info], self.csv_file_path)
            
            with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                row = next(reader)
                self.assertEqual(row['duration'], expected_output,
                               f"Duration {input_duration} should format to {expected_output}")

    def test_logical_path_default_behavior(self):
        """测试logical_path默认值行为 - 当未设置时使用file_path的目录"""
        # 测试未设置logical_path的情况
        video_info = VideoInfo("/home/user/videos/subfolder/movie.mp4")
        video_info.logical_path = None  # 明确设置为None
        
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            # 应该使用file_path的目录部分
            self.assertEqual(row['logical_path'], '/home/user/videos/subfolder')
        
        # 测试已设置logical_path的情况
        video_info.logical_path = "custom/logical/path"
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            # 应该保持原有的logical_path
            self.assertEqual(row['logical_path'], 'custom/logical/path')
        
        # 测试空字符串logical_path的情况
        video_info.logical_path = ""
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            # 空字符串也应该使用file_path的目录部分
            self.assertEqual(row['logical_path'], '/home/user/videos/subfolder')

    def test_formatting_with_invalid_values(self):
        """测试格式化功能对无效值的处理"""
        video_info = VideoInfo("/path/to/video.mp4")
        
        # 测试None值和无效字符串值
        video_info.frame_rate = None
        video_info.duration = None
        video_info.created_time = None
        
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            # None值应该转换为空字符串
            self.assertEqual(row['frame_rate'], '')
            self.assertEqual(row['duration'], '')
            self.assertEqual(row['created_time'], '')
        
        # 测试字符串类型的frame_rate（可能来自某些元数据提取器）
        video_info.frame_rate = "invalid_frame_rate"
        video_info.duration = 120.5  # 有效的duration
        video_info.created_time = "invalid_date_string"
        
        self.csv_writer.write_video_infos([video_info], self.csv_file_path)
        
        with open(self.csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            row = next(reader)
            # 无效的frame_rate应该保持原样
            self.assertEqual(row['frame_rate'], 'invalid_frame_rate')
            # 有效的duration应该被格式化
            self.assertEqual(row['duration'], '120.50')
            # 无效的created_time应该保持原样
            self.assertEqual(row['created_time'], 'invalid_date_string')


if __name__ == '__main__':
    unittest.main()