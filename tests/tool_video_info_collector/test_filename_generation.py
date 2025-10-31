"""
测试基于目录路径的文件命名功能
"""

import unittest
from pathlib import Path

from tools.video_info_collector.cli import generate_directory_based_filename


class TestFilenameGeneration(unittest.TestCase):
    """测试文件名生成功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.timestamp = "20241027_181559"
        self.prefix = "temp_video_info_"
    
    def test_volumes_path_naming(self):
        """测试Volumes路径的命名 - 去掉Volumes层"""
        test_cases = [
            ("/Volumes/ws2/media/videos/", "ws2_media_videos_20241027_181559.csv"),
            ("/Volumes/external/movies/2024/", "external_movies_2024_20241027_181559.csv"),
            ("/Volumes/backup/videos/series/", "backup_videos_series_20241027_181559.csv"),
        ]
        
        for input_path, expected_filename in test_cases:
            with self.subTest(path=input_path):
                result = generate_directory_based_filename(input_path, self.timestamp, self.prefix)
                self.assertEqual(result, expected_filename)
    
    def test_regular_path_naming(self):
        """测试常规路径的命名"""
        test_cases = [
            ("/path/to/videos/Movies/", "path_to_videos_Movies_20241027_181559.csv"),
            ("/media/storage/videos/", "media_storage_videos_20241027_181559.csv"),
            ("/home/user/documents/videos/", "System_Data_home_user_20241027_181559.csv"),  # macOS会解析为/System/Data/home/user
        ]
        
        for input_path, expected_filename in test_cases:
            with self.subTest(path=input_path):
                result = generate_directory_based_filename(input_path, self.timestamp, self.prefix)
                self.assertEqual(result, expected_filename)
    
    def test_chinese_path_naming(self):
        """测试包含中文的路径命名"""
        test_cases = [
            ("/path/to/用户/视频/电影/", "path_to_用户_视频_20241027_181559.csv"),
            ("/media/存储/影片/2024年/", "media_存储_影片_2024年_20241027_181559.csv"),
            ("/Volumes/外置硬盘/视频资料/", "外置硬盘_视频资料_20241027_181559.csv"),
        ]
        
        for input_path, expected_filename in test_cases:
            with self.subTest(path=input_path):
                result = generate_directory_based_filename(input_path, self.timestamp, self.prefix)
                self.assertEqual(result, expected_filename)
    
    def test_special_characters_handling(self):
        """测试特殊字符的处理"""
        test_cases = [
            ("/path/to/user-name/My Videos/", "path_to_user_name_My_Videos_20241027_181559.csv"),
            ("/media/storage@home/video files/", "media_storage_home_video_files_20241027_181559.csv"),
            ("/Volumes/disk#1/movies & tv/", "disk_1_movies_tv_20241027_181559.csv"),
        ]
        
        for input_path, expected_filename in test_cases:
            with self.subTest(path=input_path):
                result = generate_directory_based_filename(input_path, self.timestamp, self.prefix)
                self.assertEqual(result, expected_filename)
    
    def test_long_path_truncation(self):
        """测试长路径的截断处理"""
        # 超过4个路径部分的情况
        long_path = "/Volumes/external/very/long/path/with/many/directories/"
        result = generate_directory_based_filename(long_path, self.timestamp, self.prefix)
        
        # 应该只保留前4个有效部分（去掉Volumes后）
        expected = "external_very_long_path_20241027_181559.csv"
        self.assertEqual(result, expected)
    
    def test_hidden_directories_filtering(self):
        """测试隐藏目录的过滤"""
        test_cases = [
            ("/path/to/username/.hidden/videos/", "path_to_username_videos_20241027_181559.csv"),
            ("/media/.cache/storage/videos/", "media_storage_videos_20241027_181559.csv"),
            ("/.system/Volumes/disk/movies/", "disk_movies_20241027_181559.csv"),
        ]
        
        for input_path, expected_filename in test_cases:
            with self.subTest(path=input_path):
                result = generate_directory_based_filename(input_path, self.timestamp, self.prefix)
                self.assertEqual(result, expected_filename)
    
    def test_empty_or_invalid_paths(self):
        """测试空路径或无效路径的处理"""
        test_cases = [
            ("/", "temp_video_info_20241027_181559.csv"),
            ("/Volumes/", "temp_video_info_20241027_181559.csv"),
            ("/.hidden/", "temp_video_info_20241027_181559.csv"),
        ]
        
        for input_path, expected_filename in test_cases:
            with self.subTest(path=input_path):
                result = generate_directory_based_filename(input_path, self.timestamp, self.prefix)
                self.assertEqual(result, expected_filename)
    
    def test_relative_path_handling(self):
        """测试相对路径的处理"""
        # 相对路径会被resolve()转换为绝对路径
        relative_path = "./test_videos"
        result = generate_directory_based_filename(relative_path, self.timestamp, self.prefix)
        
        # 结果应该包含解析后的绝对路径部分
        self.assertTrue(result.endswith("_20241027_181559.csv"))
        self.assertNotEqual(result, "temp_video_info_20241027_181559.csv")
    
    def test_consecutive_underscores_removal(self):
        """测试连续下划线的移除"""
        # 包含多个特殊字符的路径
        path_with_specials = "/media/storage--test/video__files/movie---collection/"
        result = generate_directory_based_filename(path_with_specials, self.timestamp, self.prefix)
        
        # 不应该包含连续的下划线
        self.assertNotIn("__", result)
        self.assertNotIn("___", result)
    
    def test_different_timestamp_formats(self):
        """测试不同时间戳格式"""
        test_timestamps = [
            "20241027_181559",
            "2024-10-27_18-15-59",
            "20241027181559",
        ]
        
        path = "/Volumes/ws2/media/videos/"
        
        for timestamp in test_timestamps:
            with self.subTest(timestamp=timestamp):
                result = generate_directory_based_filename(path, timestamp, self.prefix)
                expected = f"ws2_media_videos_{timestamp}.csv"
                self.assertEqual(result, expected)
    
    def test_custom_prefix(self):
        """测试自定义前缀"""
        path = "/Volumes/ws2/media/videos/"
        custom_prefix = "video_scan_"
        
        result = generate_directory_based_filename(path, self.timestamp, custom_prefix)
        expected = "ws2_media_videos_20241027_181559.csv"
        self.assertEqual(result, expected)
        
        # 测试空路径时使用前缀
        empty_path = "/"
        result = generate_directory_based_filename(empty_path, self.timestamp, custom_prefix)
        expected = "video_scan_20241027_181559.csv"
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()