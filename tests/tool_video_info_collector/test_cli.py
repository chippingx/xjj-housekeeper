"""
测试video_info_collector CLI功能
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from tools.video_info_collector.cli import cli_main
from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.metadata import VideoInfo


class TestCLI(unittest.TestCase):
    """测试CLI功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_video_path = os.path.join(self.temp_dir, "test_video.mp4")
        self.test_db_path = os.path.join(self.temp_dir, "test_database.db")
        # 创建一个测试视频文件（大于10KB以通过扫描器过滤）
        with open(self.test_video_path, 'wb') as f:
            fake_content = b'fake video content' * 700  # 约12KB
            f.write(fake_content)
    
    def tearDown(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_scan_directory(self):
        """测试扫描目录功能"""
        with patch('tools.video_info_collector.cli.VideoFileScanner') as mock_scanner, \
             patch('tools.video_info_collector.cli.VideoMetadataExtractor') as mock_extractor, \
             patch('tools.video_info_collector.cli.CSVWriter') as mock_writer:
            
            # 设置mock
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_directory.return_value = ['test.mp4']
            mock_scanner.return_value = mock_scanner_instance
            
            mock_extractor_instance = MagicMock()
            # 创建一个mock VideoInfo对象
            mock_video_info = MagicMock()
            mock_video_info.file_path = 'test.mp4'
            mock_video_info.filename = 'test.mp4'
            mock_video_info.file_size = 1024
            mock_video_info.duration = 60.0
            mock_video_info.resolution = '1920x1080'
            mock_video_info.video_codec = 'h264'
            mock_video_info.bit_rate = 1000
            mock_video_info.frame_rate = 30.0
            mock_video_info.created_time = '2023-01-01 00:00:00'
            mock_video_info.tags = []
            mock_video_info.logical_path = None
            mock_extractor_instance.extract_metadata.return_value = mock_video_info
            mock_extractor.return_value = mock_extractor_instance
            
            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            
            # 运行CLI - 使用目录作为位置参数
            result = cli_main([self.temp_dir])
            
            # 验证结果
            self.assertEqual(result, 0)
            # 验证scanner被正确调用
            mock_scanner.assert_called_once()
            mock_scanner_instance.scan_directory.assert_called_once_with(self.temp_dir, recursive=True)
    
    def test_cli_export_csv(self):
        """测试导出CSV功能"""
        csv_path = os.path.join(self.temp_dir, "export.csv")
        db_path = os.path.join(self.temp_dir, "test.db")
        
        # 创建一个假的数据库文件
        with open(db_path, 'w') as f:
            f.write("fake db")
        
        with patch('tools.video_info_collector.cli.SQLiteStorage') as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.export_to_csv.return_value = True
            mock_storage_instance.get_total_count.return_value = 5
            mock_storage.return_value = mock_storage_instance
            
            # 运行CLI - 新的接口使用--export参数
            result = cli_main(['--export', db_path, '--output', csv_path])
            
            # 验证结果
            self.assertEqual(result, 0)
            mock_storage_instance.export_to_csv.assert_called_once_with(csv_path)
            mock_storage_instance.get_total_count.assert_called_once()

    def test_cli_export_simple(self):
        """测试简化导出功能"""
        simple_path = os.path.join(self.temp_dir, "simple_export.txt")
        db_path = os.path.join(self.temp_dir, "test.db")
        
        # 创建一个假的数据库文件
        with open(db_path, 'w') as f:
            f.write("fake db")
        
        with patch('tools.video_info_collector.cli.SQLiteStorage') as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.export_simple_format.return_value = True
            mock_storage_instance.get_total_count.return_value = 10
            mock_storage.return_value = mock_storage_instance
            
            # 运行CLI - 使用--export-simple参数
            result = cli_main(['--export-simple', db_path, '--output', simple_path])
            
            # 验证结果
            self.assertEqual(result, 0)
            mock_storage_instance.export_simple_format.assert_called_once_with(simple_path)
            mock_storage_instance.get_total_count.assert_called_once()

    def test_cli_export_simple_default_output(self):
        """测试简化导出功能使用默认输出路径"""
        db_path = os.path.join(self.temp_dir, "test.db")
        
        # 创建一个假的数据库文件
        with open(db_path, 'w') as f:
            f.write("fake db")
        
        with patch('tools.video_info_collector.cli.SQLiteStorage') as mock_storage:
            with patch('tools.video_info_collector.cli.datetime') as mock_datetime:
                # Mock datetime to get predictable output filename
                mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
                
                mock_storage_instance = MagicMock()
                mock_storage_instance.export_simple_format.return_value = True
                mock_storage_instance.get_total_count.return_value = 5
                mock_storage.return_value = mock_storage_instance
                
                # 运行CLI - 不指定输出路径
                result = cli_main(['--export-simple', db_path])
                
                # 验证结果
                self.assertEqual(result, 0)
                # 验证调用了export_simple_format，且使用了默认路径
                mock_storage_instance.export_simple_format.assert_called_once()
                call_args = mock_storage_instance.export_simple_format.call_args[0]
                self.assertTrue(call_args[0].endswith('simple_export_20240101_120000.txt'))

    def test_cli_export_simple_nonexistent_database(self):
        """测试简化导出功能处理不存在的数据库"""
        nonexistent_db = os.path.join(self.temp_dir, "nonexistent.db")
        simple_path = os.path.join(self.temp_dir, "simple_export.txt")
        
        # 运行CLI - 数据库文件不存在
        result = cli_main(['--export-simple', nonexistent_db, '--output', simple_path])
        
        # 验证结果 - 应该返回错误代码
        self.assertNotEqual(result, 0)

    def test_cli_merge_csv(self):
        """测试合并CSV功能"""
        csv_path = os.path.join(self.temp_dir, "merge.csv")
        db_path = os.path.join(self.temp_dir, "test.db")
        # 创建一个测试CSV文件
        with open(csv_path, 'w') as f:
            f.write("file_path,filename\n")
            f.write(f"{self.test_video_path},test_video.mp4\n")
        
        with patch('tools.video_info_collector.cli.SQLiteStorage') as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.import_from_csv.return_value = 1
            mock_storage_instance.check_csv_already_merged.return_value = False  # 假设CSV文件未被合并过
            mock_storage_instance.get_csv_fingerprint.return_value = "test_fingerprint"
            mock_storage_instance.extract_scan_info_from_csv_filename.return_value = {
                'original_scan_path': '/test/path',
                'timestamp': '20240101_120000'
            }
            mock_storage_instance.add_csv_merge_history.return_value = 1
            mock_storage.return_value = mock_storage_instance
            
            # 运行CLI - 新的接口使用--merge参数
            result = cli_main(['--merge', csv_path, '--database', db_path])
            
            # 验证结果
            self.assertEqual(result, 0)
            mock_storage_instance.import_from_csv.assert_called_once_with(csv_path)
    
    def test_cli_dry_run(self):
        """测试dry-run模式"""
        # 创建一个真实的测试文件（大于10KB以通过扫描器过滤）
        test_file = os.path.join(self.temp_dir, 'test.mp4')
        with open(test_file, 'wb') as f:
            fake_content = b"fake video content" * 700  # 约12KB
            f.write(fake_content)
        
        with patch('tools.video_info_collector.cli.VideoFileScanner') as mock_scanner:
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_directory.return_value = [test_file]
            mock_scanner.return_value = mock_scanner_instance
            
            # 运行CLI - 使用--dry-run参数
            result = cli_main([self.temp_dir, '--dry-run'])
            
            # 验证结果
            self.assertEqual(result, 0)
            # 验证scanner被正确调用
            mock_scanner.assert_called_once()
            mock_scanner_instance.scan_directory.assert_called_once_with(self.temp_dir, recursive=True)
    
    def test_cli_missing_arguments(self):
        """测试缺少参数的情况"""
        # 测试没有提供任何参数
        result = cli_main([])
        self.assertEqual(result, 1)
    
    def test_cli_nonexistent_directory(self):
        """测试不存在的目录"""
        result = cli_main(['/nonexistent/directory'])
        self.assertNotEqual(result, 0)
    
    def test_cli_tags_default_behavior(self):
        """测试tags默认值行为：当没有设置tags时，使用目录名作为默认值"""
        # 创建一个有意义的目录结构
        format_dir = os.path.join(self.temp_dir, "format")
        os.makedirs(format_dir, exist_ok=True)
        test_video_path = os.path.join(format_dir, "test_video.mp4")
        with open(test_video_path, 'wb') as f:
            fake_content = b'fake video content' * 700  # 约12KB
            f.write(fake_content)
        
        with patch('tools.video_info_collector.cli.VideoFileScanner') as mock_scanner, \
             patch('tools.video_info_collector.cli.VideoMetadataExtractor') as mock_extractor, \
             patch('tools.video_info_collector.cli.CSVWriter') as mock_writer:
            
            # 设置mock
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_directory.return_value = [test_video_path]
            mock_scanner.return_value = mock_scanner_instance
            
            # 创建一个mock VideoInfo对象
            mock_video_info = MagicMock()
            mock_video_info.tags = []  # 初始为空
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.extract_metadata.return_value = mock_video_info
            mock_extractor.return_value = mock_extractor_instance
            
            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            
            # 运行CLI - 不设置tags参数
            result = cli_main([format_dir])
            
            # 验证结果
            self.assertEqual(result, 0)
            # 验证tags被设置为目录名
            self.assertEqual(mock_video_info.tags, ['format'])
    
    def test_cli_tags_explicit_setting(self):
        """测试显式设置tags时不使用默认值"""
        # 创建一个有意义的目录结构
        format_dir = os.path.join(self.temp_dir, "format")
        os.makedirs(format_dir, exist_ok=True)
        test_video_path = os.path.join(format_dir, "test_video.mp4")
        with open(test_video_path, 'wb') as f:
            fake_content = b'fake video content' * 700  # 约12KB
            f.write(fake_content)
        
        with patch('tools.video_info_collector.cli.VideoFileScanner') as mock_scanner, \
             patch('tools.video_info_collector.cli.VideoMetadataExtractor') as mock_extractor, \
             patch('tools.video_info_collector.cli.CSVWriter') as mock_writer:
            
            # 设置mock
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_directory.return_value = [test_video_path]
            mock_scanner.return_value = mock_scanner_instance
            
            # 创建一个mock VideoInfo对象
            mock_video_info = MagicMock()
            mock_video_info.tags = []  # 初始为空
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.extract_metadata.return_value = mock_video_info
            mock_extractor.return_value = mock_extractor_instance
            
            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            
            # 运行CLI - 显式设置tags参数
            result = cli_main([format_dir, '--tags', '动作片;高清'])
            
            # 验证结果
            self.assertEqual(result, 0)
            # 验证tags被设置为显式指定的值，而不是目录名
            self.assertEqual(mock_video_info.tags, ['动作片', '高清'])
    
    def test_cli_tags_root_directory(self):
        """测试根目录情况下的tags默认值行为"""
        # 创建一个根目录级别的测试
        root_like_dir = "/"
        test_video_path = "/test_video.mp4"
        
        with patch('tools.video_info_collector.cli.VideoFileScanner') as mock_scanner, \
             patch('tools.video_info_collector.cli.VideoMetadataExtractor') as mock_extractor, \
             patch('tools.video_info_collector.cli.CSVWriter') as mock_writer:
            
            # 设置mock
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_directory.return_value = [test_video_path]
            mock_scanner.return_value = mock_scanner_instance
            
            # 创建一个mock VideoInfo对象
            mock_video_info = MagicMock()
            mock_video_info.tags = []  # 初始为空
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.extract_metadata.return_value = mock_video_info
            mock_extractor.return_value = mock_extractor_instance
            
            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            
            # 运行CLI - 不设置tags参数，使用根目录
            result = cli_main([root_like_dir])
            
            # 验证结果
            self.assertEqual(result, 0)
            # 验证当目录名为根目录时，tags为空列表（因为根目录名为空）
            self.assertEqual(mock_video_info.tags, [])
    
    def test_cli_tags_semicolon_separator(self):
        """测试tags使用分号分隔符"""
        with patch('tools.video_info_collector.cli.VideoFileScanner') as mock_scanner, \
             patch('tools.video_info_collector.cli.VideoMetadataExtractor') as mock_extractor, \
             patch('tools.video_info_collector.cli.CSVWriter') as mock_writer:
            
            # 设置mock
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_directory.return_value = [self.test_video_path]
            mock_scanner.return_value = mock_scanner_instance
            
            # 创建一个mock VideoInfo对象
            mock_video_info = MagicMock()
            mock_video_info.tags = []  # 初始为空
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.extract_metadata.return_value = mock_video_info
            mock_extractor.return_value = mock_extractor_instance
            
            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            
            # 运行CLI - 使用分号分隔的tags
            result = cli_main([self.temp_dir, '--tags', '动作片,科幻;高清;2024年电影'])
            
            # 验证结果
            self.assertEqual(result, 0)
            # 验证tags被正确解析（分号分隔，保留逗号）
            expected_tags = ['动作片,科幻', '高清', '2024年电影']
            self.assertEqual(mock_video_info.tags, expected_tags)
    

    
    def test_cli_tags_with_spaces(self):
        """测试带空格的tags参数"""
        with patch('tools.video_info_collector.cli.VideoFileScanner') as mock_scanner, \
             patch('tools.video_info_collector.cli.VideoMetadataExtractor') as mock_extractor, \
             patch('tools.video_info_collector.cli.CSVWriter') as mock_writer:
            
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_directory.return_value = [self.test_video_path]
            mock_scanner.return_value = mock_scanner_instance
            
            mock_video_info = MagicMock()
            mock_video_info.tags = []  # 初始为空
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.extract_metadata.return_value = mock_video_info
            mock_extractor.return_value = mock_extractor_instance
            
            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            
            # 运行CLI - 测试带空格的tags
            result = cli_main([self.temp_dir, '--tags', '科幻电影; 高清画质 ; 2024年'])
            
            # 验证结果
            self.assertEqual(result, 0)
            # 验证tags被正确解析（去除空格）
            expected_tags = ['科幻电影', '高清画质', '2024年']
            self.assertEqual(mock_video_info.tags, expected_tags)
    
    def test_cli_directory_based_filename(self):
        """测试基于目录路径的文件命名功能"""
        with patch('tools.video_info_collector.cli.VideoFileScanner') as mock_scanner, \
             patch('tools.video_info_collector.cli.VideoMetadataExtractor') as mock_extractor, \
             patch('tools.video_info_collector.cli.CSVWriter') as mock_writer:
            
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_directory.return_value = [self.test_video_path]
            mock_scanner.return_value = mock_scanner_instance
            
            mock_video_info = MagicMock()
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.extract_metadata.return_value = mock_video_info
            mock_extractor.return_value = mock_extractor_instance
            
            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            
            # 创建一个模拟的volumes路径
            volumes_dir = "/tmp/test_volumes/ws2/media/videos"
            os.makedirs(volumes_dir, exist_ok=True)
            test_video_in_volumes = os.path.join(volumes_dir, "test_video.mp4")
            with open(test_video_in_volumes, 'wb') as f:
                fake_content = b'fake video content' * 700  # 约12KB
                f.write(fake_content)
            
            try:
                # 运行CLI - 使用volumes路径
                result = cli_main([volumes_dir])
                
                # 验证结果
                self.assertEqual(result, 0)
                
                # 验证CSVWriter被调用时使用了正确的文件路径
                mock_writer_instance.write_video_infos.assert_called_once()
                call_args = mock_writer_instance.write_video_infos.call_args
                output_file_path = call_args[0][1]  # 第二个参数是输出文件路径
                
                # 文件名应该基于目录路径生成，包含路径信息
                filename = os.path.basename(output_file_path)
                # 在macOS中，/tmp会被解析为/private/tmp，所以文件名会包含这些部分
                self.assertIn("test_volumes", filename)
                self.assertIn("ws2", filename)
                self.assertTrue(filename.endswith(".csv"))
                
            finally:
                # 清理测试文件
                import shutil
                shutil.rmtree("/tmp/test_volumes", ignore_errors=True)
    
    def test_cli_chinese_directory_filename(self):
        """测试包含中文的目录路径文件命名"""
        with patch('tools.video_info_collector.cli.VideoFileScanner') as mock_scanner, \
             patch('tools.video_info_collector.cli.VideoMetadataExtractor') as mock_extractor, \
             patch('tools.video_info_collector.cli.CSVWriter') as mock_writer:
            
            mock_scanner_instance = MagicMock()
            mock_scanner_instance.scan_directory.return_value = [self.test_video_path]
            mock_scanner.return_value = mock_scanner_instance
            
            mock_video_info = MagicMock()
            mock_extractor_instance = MagicMock()
            mock_extractor_instance.extract_metadata.return_value = mock_video_info
            mock_extractor.return_value = mock_extractor_instance
            
            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            
            # 创建一个包含中文的目录路径
            chinese_dir = "/tmp/test_中文目录/视频文件/电影"
            os.makedirs(chinese_dir, exist_ok=True)
            test_video_chinese = os.path.join(chinese_dir, "test_video.mp4")
            with open(test_video_chinese, 'wb') as f:
                fake_content = b'fake video content' * 700  # 约12KB
                f.write(fake_content)
            
            try:
                # 运行CLI - 使用中文路径
                result = cli_main([chinese_dir])
                
                # 验证结果
                self.assertEqual(result, 0)
                
                # 验证CSVWriter被调用时使用了正确的文件路径
                mock_writer_instance.write_video_infos.assert_called_once()
                call_args = mock_writer_instance.write_video_infos.call_args
                output_file_path = call_args[0][1]  # 第二个参数是输出文件路径
                
                # 文件名应该包含中文字符（由于路径长度限制，只检查前几个部分）
                filename = os.path.basename(output_file_path)
                self.assertIn("中文目录", filename)
                self.assertIn("视频文件", filename)
                # 注意：由于路径长度限制（最多4个部分），"电影"可能被截断
                self.assertTrue(filename.endswith(".csv"))
                
            finally:
                # 清理测试文件
                import shutil
                shutil.rmtree("/tmp/test_中文目录", ignore_errors=True)

    def test_cli_search_code_single(self):
        """测试单个视频code查询"""
        db_path = os.path.join(self.temp_dir, "test.db")
        
        # 创建一个假的数据库文件
        with open(db_path, 'w') as f:
            f.write("fake db")
        
        with patch('tools.video_info_collector.cli.SQLiteStorage') as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.search_videos_by_codes.return_value = [
                {
                    'video_code': 'ABC-123',
                    'file_size': 1024000000,
                    'logical_path': '/test/path/ABC-123.mp4'
                }
            ]
            mock_storage.return_value = mock_storage_instance
            
            # 运行CLI - 使用--search-code参数
            result = cli_main(['--search-code', 'ABC-123', '--database', db_path])
            
            # 验证结果
            self.assertEqual(result, 0)
            mock_storage_instance.search_videos_by_codes.assert_called_once_with(['ABC-123'])

    def test_cli_search_code_multiple_comma(self):
        """测试多个视频code查询（逗号分隔）"""
        db_path = os.path.join(self.temp_dir, "test.db")
        
        # 创建一个假的数据库文件
        with open(db_path, 'w') as f:
            f.write("fake db")
        
        with patch('tools.video_info_collector.cli.SQLiteStorage') as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.search_videos_by_codes.return_value = [
                {
                    'video_code': 'ABC-123',
                    'file_size': 1024000000,
                    'logical_path': '/test/path/ABC-123.mp4'
                },
                {
                    'video_code': 'DEF-456',
                    'file_size': 2048000000,
                    'logical_path': '/test/path/DEF-456.mp4'
                }
            ]
            mock_storage.return_value = mock_storage_instance
            
            # 运行CLI - 使用逗号分隔的多个code
            result = cli_main(['--search-code', 'ABC-123,DEF-456', '--database', db_path])
            
            # 验证结果
            self.assertEqual(result, 0)
            mock_storage_instance.search_videos_by_codes.assert_called_once_with(['ABC-123', 'DEF-456'])

    def test_cli_search_code_multiple_space(self):
        """测试多个视频code查询（空格分隔）"""
        db_path = os.path.join(self.temp_dir, "test.db")
        
        # 创建一个假的数据库文件
        with open(db_path, 'w') as f:
            f.write("fake db")
        
        with patch('tools.video_info_collector.cli.SQLiteStorage') as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.search_videos_by_codes.return_value = []
            mock_storage.return_value = mock_storage_instance
            
            # 运行CLI - 使用空格分隔的多个code
            result = cli_main(['--search-code', 'ABC-123 DEF-456', '--database', db_path])
            
            # 验证结果
            self.assertEqual(result, 0)
            mock_storage_instance.search_videos_by_codes.assert_called_once_with(['ABC-123', 'DEF-456'])

    def test_cli_search_code_with_spaces(self):
        """测试视频code查询去除前后空格"""
        db_path = os.path.join(self.temp_dir, "test.db")
        
        # 创建一个假的数据库文件
        with open(db_path, 'w') as f:
            f.write("fake db")
        
        with patch('tools.video_info_collector.cli.SQLiteStorage') as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.search_videos_by_codes.return_value = []
            mock_storage.return_value = mock_storage_instance
            
            # 运行CLI - 包含前后空格的code
            result = cli_main(['--search-code', '  ABC-123  ,  DEF-456  ', '--database', db_path])
            
            # 验证结果
            self.assertEqual(result, 0)
            mock_storage_instance.search_videos_by_codes.assert_called_once_with(['ABC-123', 'DEF-456'])

    def test_cli_search_code_no_results(self):
        """测试视频code查询无结果"""
        db_path = os.path.join(self.temp_dir, "test.db")
        
        # 创建一个假的数据库文件
        with open(db_path, 'w') as f:
            f.write("fake db")
        
        with patch('tools.video_info_collector.cli.SQLiteStorage') as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage_instance.search_videos_by_codes.return_value = []
            mock_storage.return_value = mock_storage_instance
            
            # 运行CLI - 查询不存在的code
            result = cli_main(['--search-code', 'NONEXISTENT-123', '--database', db_path])
            
            # 验证结果
            self.assertEqual(result, 0)
            mock_storage_instance.search_videos_by_codes.assert_called_once_with(['NONEXISTENT-123'])

    def test_cli_search_code_nonexistent_database(self):
        """测试视频code查询数据库不存在"""
        nonexistent_db = os.path.join(self.temp_dir, "nonexistent.db")
        
        # 运行CLI - 数据库文件不存在
        result = cli_main(['--search-code', 'ABC-123', '--database', nonexistent_db])
        
        # 验证结果 - 应该返回错误代码
        self.assertNotEqual(result, 0)


    def test_cli_stats_basic(self):
        """测试基本统计功能"""
        # 创建测试数据库并插入数据
        with SQLiteStorage(self.test_db_path) as storage:
            # 插入测试视频信息
            video_info1 = VideoInfo("/test/video1.mp4")
            video_info1.width = 1920
            video_info1.height = 1080
            video_info1.duration = 3600.0
            video_info1.file_size = 1024*1024*1024  # 1GB
            video_info1.video_codec = "h264"
            
            video_info2 = VideoInfo("/test/video2.mp4")
            video_info2.width = 1280
            video_info2.height = 720
            video_info2.duration = 1800.0
            video_info2.file_size = 512*1024*1024  # 512MB
            video_info2.video_codec = "h265"
            
            storage.insert_video_info(video_info1)
            storage.insert_video_info(video_info2)
        
        # 测试基本统计
        with patch('sys.argv', ['video_info_collector', '--stats', '--database', self.test_db_path]):
            with patch('builtins.print') as mock_print:
                cli_main()
                
                # 验证输出包含统计信息
                printed_output = '\n'.join([str(call.args[0]) for call in mock_print.call_args_list])
                self.assertIn('数据库统计信息', printed_output)
                self.assertIn('总视频数: 2', printed_output)
                self.assertIn('总容量:', printed_output)
                self.assertIn('总时长:', printed_output)

    def test_cli_stats_by_tags(self):
        """测试按标签分组统计"""
        # 创建测试数据库并插入数据
        with SQLiteStorage(self.test_db_path) as storage:
            # 插入测试视频信息
            video_info1 = VideoInfo("/test/video1.mp4", tags=["动作片", "高清"])
            video_info1.width = 1920
            video_info1.height = 1080
            video_info1.duration = 3600.0
            video_info1.file_size = 1024*1024*1024  # 1GB
            video_info1.video_codec = "h264"
            
            video_info2 = VideoInfo("/test/video2.mp4", tags=["喜剧片", "标清"])
            video_info2.width = 1280
            video_info2.height = 720
            video_info2.duration = 1800.0
            video_info2.file_size = 512*1024*1024  # 512MB
            video_info2.video_codec = "h265"
            
            storage.insert_video_info(video_info1)
            storage.insert_video_info(video_info2)
        
        # 测试按标签分组统计
        with patch('sys.argv', ['video_info_collector', '--stats', '--group-by', 'tags', '--database', self.test_db_path]):
            with patch('builtins.print') as mock_print:
                cli_main()
                
                # 验证输出包含标签统计信息
                printed_output = '\n'.join([str(call.args[0]) for call in mock_print.call_args_list])
                self.assertIn('按标签分组统计', printed_output)
                self.assertIn('动作片', printed_output)
                self.assertIn('喜剧片', printed_output)

    def test_cli_stats_by_resolution(self):
        """测试按分辨率分组统计"""
        # 创建测试数据库并插入数据
        with SQLiteStorage(self.test_db_path) as storage:
            video_info1 = VideoInfo("/test/video1.mp4")
            video_info1.width = 1920
            video_info1.height = 1080
            video_info1.duration = 3600.0
            video_info1.file_size = 1024*1024*1024
            
            video_info2 = VideoInfo("/test/video2.mp4")
            video_info2.width = 3840
            video_info2.height = 2160
            video_info2.duration = 3600.0
            video_info2.file_size = 2*1024*1024*1024
            
            storage.insert_video_info(video_info1)
            storage.insert_video_info(video_info2)
        
        # 测试按分辨率统计
        with patch('sys.argv', ['video_info_collector', '--stats', '--group-by', 'resolution', '--database', self.test_db_path]):
            with patch('builtins.print') as mock_print:
                cli_main()
                
                # 验证输出包含分辨率统计信息
                printed_output = '\n'.join([str(call.args[0]) for call in mock_print.call_args_list])
                self.assertIn('按分辨率分组统计', printed_output)
                self.assertIn('FHD', printed_output)
                self.assertIn('4K+', printed_output)

    def test_cli_stats_by_duration(self):
        """测试按时长分组统计"""
        # 创建测试数据库并插入数据
        with SQLiteStorage(self.test_db_path) as storage:
            video_info1 = VideoInfo("/test/video1.mp4")
            video_info1.width = 1920
            video_info1.height = 1080
            video_info1.duration = 1800.0  # 30分钟
            video_info1.file_size = 1024*1024*1024
            
            video_info2 = VideoInfo("/test/video2.mp4")
            video_info2.width = 1920
            video_info2.height = 1080
            video_info2.duration = 7200.0  # 2小时
            video_info2.file_size = 2*1024*1024*1024
            
            storage.insert_video_info(video_info1)
            storage.insert_video_info(video_info2)
        
        # 测试按时长统计
        with patch('sys.argv', ['video_info_collector', '--stats', '--group-by', 'duration', '--database', self.test_db_path]):
            with patch('builtins.print') as mock_print:
                cli_main()
                
                # 验证输出包含时长统计信息
                printed_output = '\n'.join([str(call.args[0]) for call in mock_print.call_args_list])
                self.assertIn('按时长分组统计', printed_output)
                self.assertIn('中等', printed_output)
                self.assertIn('超长', printed_output)

    def test_cli_stats_database_not_exists(self):
        """测试统计功能在数据库不存在时的错误处理"""
        # 测试不存在的数据库
        with patch('sys.argv', ['video_info_collector', '--stats', '--database', '/tmp/test_nonexistent_stats.db']):
            with patch('builtins.print') as mock_print:
                result = cli_main()
                self.assertEqual(result, 1)
                
                # 验证输出包含错误信息
                printed_output = '\n'.join([str(call.args[0]) for call in mock_print.call_args_list])
                self.assertIn('数据库文件不存在', printed_output)


if __name__ == '__main__':
    unittest.main()