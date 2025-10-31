"""
测试视频元数据提取功能
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from tools.video_info_collector.metadata import VideoMetadataExtractor, VideoInfo


class TestVideoMetadataExtractor(unittest.TestCase):
    """测试VideoMetadataExtractor类"""
    
    def setUp(self):
        """设置测试环境"""
        self.extractor = VideoMetadataExtractor()
        
        # 创建临时测试文件
        self.temp_dir = tempfile.mkdtemp()
        self.test_video_path = os.path.join(self.temp_dir, "test_video.mp4")
        
        # 创建一个测试文件（大于10KB以通过扫描器过滤）
        with open(self.test_video_path, 'wb') as f:
            fake_content = b'fake video content' * 700  # 约12KB
            f.write(fake_content)
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.test_video_path):
            os.remove(self.test_video_path)
        os.rmdir(self.temp_dir)
    
    def test_extractor_initialization(self):
        """测试提取器初始化"""
        extractor = VideoMetadataExtractor()
        self.assertIsInstance(extractor, VideoMetadataExtractor)
    
    @patch('subprocess.run')
    def test_extract_metadata_success(self, mock_run):
        """测试成功提取元数据"""
        # 模拟ffprobe的成功输出
        mock_output = '''
        {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "duration": "120.5",
                    "bit_rate": "5000000"
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "duration": "120.5",
                    "bit_rate": "128000"
                }
            ],
            "format": {
                "filename": "/path/to/video.mp4",
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "duration": "120.500000",
                "size": "75000000",
                "bit_rate": "4980000"
            }
        }
        '''
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )
        
        video_info = self.extractor.extract_metadata(self.test_video_path)
        
        self.assertIsInstance(video_info, VideoInfo)
        self.assertEqual(video_info.file_path, self.test_video_path)
        self.assertEqual(video_info.width, 1920)
        self.assertEqual(video_info.height, 1080)
        self.assertEqual(video_info.duration, 120.5)
        self.assertEqual(video_info.video_codec, "h264")
        self.assertEqual(video_info.audio_codec, "aac")
        self.assertEqual(video_info.file_size, 75000000)
        self.assertEqual(video_info.bit_rate, 4980000)
    
    @patch('subprocess.run')
    def test_extract_metadata_ffprobe_error(self, mock_run):
        """测试ffprobe执行失败"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ffprobe: error"
        )
        
        video_info = self.extractor.extract_metadata(self.test_video_path)
        
        self.assertIsInstance(video_info, VideoInfo)
        self.assertEqual(video_info.file_path, self.test_video_path)
        self.assertIsNone(video_info.width)
        self.assertIsNone(video_info.height)
        self.assertIsNone(video_info.duration)
        self.assertIsNone(video_info.video_codec)
        self.assertIsNone(video_info.audio_codec)
        self.assertIsNone(video_info.bit_rate)
        # 文件大小应该仍然可以获取
        self.assertIsNotNone(video_info.file_size)
    
    def test_extract_metadata_nonexistent_file(self):
        """测试提取不存在文件的元数据"""
        nonexistent_path = "/path/to/nonexistent/file.mp4"
        
        with self.assertRaises(FileNotFoundError):
            self.extractor.extract_metadata(nonexistent_path)
    
    @patch('subprocess.run')
    def test_extract_metadata_invalid_json(self, mock_run):
        """测试ffprobe返回无效JSON"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="invalid json output",
            stderr=""
        )
        
        video_info = self.extractor.extract_metadata(self.test_video_path)
        
        self.assertIsInstance(video_info, VideoInfo)
        self.assertEqual(video_info.file_path, self.test_video_path)
        # 应该回退到基本信息
        self.assertIsNotNone(video_info.file_size)
        self.assertIsNotNone(video_info.created_time)
    
    @patch('subprocess.run')
    def test_extract_metadata_video_only(self, mock_run):
        """测试只有视频流的文件"""
        mock_output = '''
        {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1280,
                    "height": 720,
                    "duration": "60.0",
                    "bit_rate": "2000000"
                }
            ],
            "format": {
                "filename": "/path/to/video.mp4",
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "duration": "60.000000",
                "size": "15000000",
                "bit_rate": "2000000"
            }
        }
        '''
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output,
            stderr=""
        )
        
        video_info = self.extractor.extract_metadata(self.test_video_path)
        
        self.assertEqual(video_info.width, 1280)
        self.assertEqual(video_info.height, 720)
        self.assertEqual(video_info.video_codec, "h264")
        self.assertIsNone(video_info.audio_codec)  # 没有音频流
    
    def test_batch_extract_metadata(self):
        """测试批量提取元数据"""
        # 创建多个测试文件
        test_files = []
        for i in range(3):
            file_path = os.path.join(self.temp_dir, f"test_video_{i}.mp4")
            with open(file_path, 'wb') as f:
                fake_content = b'fake video content' * 700  # 约12KB
                f.write(fake_content)
            test_files.append(file_path)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,  # 模拟失败，这样只会获取基本信息
                stdout="",
                stderr="error"
            )
            
            video_infos = self.extractor.batch_extract_metadata(test_files)
            
            self.assertEqual(len(video_infos), 3)
            for video_info in video_infos:
                self.assertIsInstance(video_info, VideoInfo)
                self.assertIsNotNone(video_info.file_size)
        
        # 清理测试文件
        for file_path in test_files:
            os.remove(file_path)


class TestVideoInfo(unittest.TestCase):
    """测试VideoInfo数据类"""
    
    def test_video_info_creation(self):
        """测试VideoInfo对象创建"""
        file_path = "/path/to/video.mp4"
        video_info = VideoInfo(file_path)
        
        self.assertEqual(video_info.file_path, file_path)
        self.assertEqual(video_info.filename, "video.mp4")
        self.assertIsInstance(video_info.created_time, datetime)
        self.assertIsNone(video_info.width)
        self.assertIsNone(video_info.height)
        self.assertIsNone(video_info.duration)
    
    def test_video_info_to_dict(self):
        """测试VideoInfo转换为字典"""
        video_info = VideoInfo("/path/to/video.mp4")
        video_info.width = 1920
        video_info.height = 1080
        video_info.duration = 120.5
        video_info.video_codec = "h264"
        video_info.audio_codec = "aac"
        video_info.file_size = 75000000
        video_info.bit_rate = 5000000
        
        data_dict = video_info.to_dict()
        
        self.assertIsInstance(data_dict, dict)
        self.assertEqual(data_dict['file_path'], "/path/to/video.mp4")
        self.assertEqual(data_dict['filename'], "video.mp4")
        self.assertEqual(data_dict['width'], 1920)
        self.assertEqual(data_dict['height'], 1080)
        self.assertEqual(data_dict['duration'], 120.5)
        self.assertEqual(data_dict['video_codec'], "h264")
        self.assertEqual(data_dict['audio_codec'], "aac")
        self.assertEqual(data_dict['file_size'], 75000000)
        self.assertEqual(data_dict['bit_rate'], 5000000)
        self.assertIn('created_time', data_dict)
    
    def test_video_info_resolution_property(self):
        """测试分辨率属性"""
        video_info = VideoInfo("/path/to/video.mp4")
        
        # 没有设置宽高时
        self.assertIsNone(video_info.resolution)
        
        # 设置宽高后
        video_info.width = 1920
        video_info.height = 1080
        self.assertEqual(video_info.resolution, "1920x1080")
    
    def test_video_info_duration_formatted(self):
        """测试格式化的时长"""
        video_info = VideoInfo("/path/to/video.mp4")
        
        # 没有设置时长时
        self.assertIsNone(video_info.duration_formatted)
        
        # 设置时长后
        video_info.duration = 3661.5  # 1小时1分1.5秒
        self.assertEqual(video_info.duration_formatted, "01:01:01")
        
        video_info.duration = 125.7  # 2分5.7秒
        self.assertEqual(video_info.duration_formatted, "00:02:05")

    def test_video_info_tags_semicolon_separator(self):
        """测试tags使用分号分隔符输出"""
        video_info = VideoInfo("/path/to/video.mp4")
        
        # 测试空tags
        self.assertEqual(video_info.tags, [])
        data_dict = video_info.to_dict()
        self.assertEqual(data_dict['tags'], "")
        
        # 测试单个tag
        video_info.tags = ['动作片']
        data_dict = video_info.to_dict()
        self.assertEqual(data_dict['tags'], "动作片")
        
        # 测试多个tags
        video_info.tags = ['动作片', '高清', '2024']
        data_dict = video_info.to_dict()
        self.assertEqual(data_dict['tags'], "动作片;高清;2024")

    def test_video_info_tags_creation_with_tags(self):
        """测试创建VideoInfo时指定tags"""
        tags = ['动作片', '高清', '2024']
        video_info = VideoInfo("/path/to/video.mp4", tags=tags)
        
        self.assertEqual(video_info.tags, tags)
        
        # 测试to_dict输出
        data_dict = video_info.to_dict()
        self.assertEqual(data_dict['tags'], "动作片;高清;2024")

    def test_video_info_tags_modification(self):
        """测试tags的修改"""
        video_info = VideoInfo("/path/to/video.mp4")
        
        # 初始为空
        self.assertEqual(video_info.tags, [])
        
        # 添加tags
        video_info.tags = ['新标签']
        self.assertEqual(video_info.tags, ['新标签'])
        
        # 修改tags
        video_info.tags = ['修改后的标签', '另一个标签']
        self.assertEqual(video_info.tags, ['修改后的标签', '另一个标签'])
        
        # 验证to_dict输出
        data_dict = video_info.to_dict()
        self.assertEqual(data_dict['tags'], "修改后的标签;另一个标签")


if __name__ == '__main__':
    unittest.main()