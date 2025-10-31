"""
测试SQLite数据库存储功能
"""

import os
import shutil
import sqlite3
import tempfile
import unittest
from datetime import datetime

from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.metadata import VideoInfo


class TestSQLiteStorage(unittest.TestCase):
    """测试SQLiteStorage类"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_file_path = os.path.join(self.temp_dir, "test_videos.db")
        self.storage = SQLiteStorage(self.db_file_path)
        
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
        self.storage.close()
        if os.path.exists(self.db_file_path):
            os.remove(self.db_file_path)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_sqlite_storage_initialization(self):
        """测试SQLite存储初始化"""
        storage = SQLiteStorage(self.db_file_path)
        self.assertIsInstance(storage, SQLiteStorage)
        self.assertTrue(os.path.exists(self.db_file_path))
        storage.close()
    
    def test_create_tables(self):
        """测试创建数据表"""
        # 验证表是否创建成功
        conn = sqlite3.connect(self.db_file_path)
        cursor = conn.cursor()
        
        # 检查video_info表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='video_info'
        """)
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(video_info)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        expected_columns = [
            'id', 'file_path', 'filename', 'width', 'height', 'resolution',
            'duration', 'duration_formatted', 'video_codec', 'audio_codec',
            'file_size', 'bit_rate', 'frame_rate', 'logical_path', 'created_time', 'updated_time'
        ]
        
        for col in expected_columns:
            self.assertIn(col, column_names)
        
        conn.close()
    
    def test_insert_video_info(self):
        """测试插入单个视频信息"""
        video_info = self.test_video_infos[0]
        video_id = self.storage.insert_video_info(video_info)
        
        self.assertIsInstance(video_id, int)
        self.assertGreater(video_id, 0)
        
        # 验证数据是否正确插入
        stored_info = self.storage.get_video_info_by_id(video_id)
        self.assertIsNotNone(stored_info)
        self.assertEqual(stored_info['file_path'], video_info.file_path)
        self.assertEqual(stored_info['width'], video_info.width)
        self.assertEqual(stored_info['height'], video_info.height)
    
    def test_insert_multiple_video_infos(self):
        """测试批量插入视频信息"""
        inserted_ids = self.storage.insert_multiple_video_infos(self.test_video_infos)
        
        self.assertEqual(len(inserted_ids), 3)
        for video_id in inserted_ids:
            self.assertIsInstance(video_id, int)
            self.assertGreater(video_id, 0)
        
        # 验证数据总数
        total_count = self.storage.get_total_count()
        self.assertEqual(total_count, 3)
    
    def test_upsert_video_info(self):
        """测试插入或更新视频信息"""
        video_info = self.test_video_infos[0]
        
        # 首次插入
        video_id = self.storage.upsert_video_info(video_info)
        self.assertIsInstance(video_id, int)
        
        # 修改信息后再次upsert
        video_info.width = 3840
        video_info.height = 2160
        video_id2 = self.storage.upsert_video_info(video_info)
        
        # 应该是同一个ID（更新而不是插入）
        self.assertEqual(video_id, video_id2)
        
        # 验证数据已更新
        stored_info = self.storage.get_video_info_by_id(video_id)
        self.assertEqual(stored_info['width'], 3840)
        self.assertEqual(stored_info['height'], 2160)
        
        # 验证总数没有增加
        total_count = self.storage.get_total_count()
        self.assertEqual(total_count, 1)
    
    def test_get_video_info_by_path(self):
        """测试根据路径获取视频信息"""
        video_info = self.test_video_infos[0]
        self.storage.insert_video_info(video_info)
        
        stored_info = self.storage.get_video_info_by_path(video_info.file_path)
        self.assertIsNotNone(stored_info)
        self.assertEqual(stored_info['file_path'], video_info.file_path)
        
        # 测试不存在的路径
        nonexistent_info = self.storage.get_video_info_by_path("/nonexistent/path.mp4")
        self.assertIsNone(nonexistent_info)
    
    def test_search_videos(self):
        """测试搜索视频"""
        self.storage.insert_multiple_video_infos(self.test_video_infos)
        
        # 按文件名搜索
        results = self.storage.search_videos(filename_pattern="video_1")
        self.assertEqual(len(results), 1)
        self.assertIn("video_1.mp4", results[0]['filename'])
        
        # 按分辨率搜索
        results = self.storage.search_videos(min_width=1920, min_height=1080)
        self.assertEqual(len(results), 3)
        
        # 按时长搜索
        results = self.storage.search_videos(min_duration=130)
        self.assertEqual(len(results), 2)  # video_1 和 video_2
        
        # 按编解码器搜索
        results = self.storage.search_videos(video_codec="h264")
        self.assertEqual(len(results), 3)
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        self.storage.insert_multiple_video_infos(self.test_video_infos)
        
        stats = self.storage.get_statistics()
        
        self.assertEqual(stats['total_videos'], 3)
        self.assertEqual(stats['total_size'], sum(v.file_size for v in self.test_video_infos))
        self.assertEqual(stats['total_duration'], sum(v.duration for v in self.test_video_infos))
        self.assertIn('avg_duration', stats)
        self.assertIn('avg_file_size', stats)
        self.assertIn('most_common_codec', stats)
        self.assertIn('resolution_distribution', stats)
    
    def test_delete_video_info(self):
        """测试删除视频信息"""
        video_info = self.test_video_infos[0]
        video_id = self.storage.insert_video_info(video_info)
        
        # 删除前验证存在
        stored_info = self.storage.get_video_info_by_id(video_id)
        self.assertIsNotNone(stored_info)
        
        # 删除
        success = self.storage.delete_video_info(video_id)
        self.assertTrue(success)
        
        # 删除后验证不存在
        stored_info = self.storage.get_video_info_by_id(video_id)
        self.assertIsNone(stored_info)
        
        # 删除不存在的记录
        success = self.storage.delete_video_info(99999)
        self.assertFalse(success)
    
    def test_update_video_info(self):
        """测试更新视频信息"""
        video_info = self.test_video_infos[0]
        video_id = self.storage.insert_video_info(video_info)
        
        # 更新数据
        update_data = {
            'width': 3840,
            'height': 2160,
            'video_codec': 'h265'
        }
        
        success = self.storage.update_video_info(video_id, update_data)
        self.assertTrue(success)
        
        # 验证更新结果
        stored_info = self.storage.get_video_info_by_id(video_id)
        self.assertEqual(stored_info['width'], 3840)
        self.assertEqual(stored_info['height'], 2160)
        self.assertEqual(stored_info['video_codec'], 'h265')
        
        # 更新不存在的记录
        success = self.storage.update_video_info(99999, update_data)
        self.assertFalse(success)
    
    def test_export_to_csv(self):
        """测试导出到CSV"""
        self.storage.insert_multiple_video_infos(self.test_video_infos)
        
        csv_file_path = os.path.join(self.temp_dir, "exported_videos.csv")
        success = self.storage.export_to_csv(csv_file_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(csv_file_path))
        
        # 验证CSV内容
        import csv
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 3)
    
    def test_import_from_csv(self):
        """测试从CSV导入"""
        # 先创建CSV文件
        from tools.video_info_collector.csv_writer import CSVWriter
        csv_file_path = os.path.join(self.temp_dir, "import_videos.csv")
        csv_writer = CSVWriter()
        csv_writer.write_video_infos(self.test_video_infos, csv_file_path)
        
        # 导入到数据库
        imported_count = self.storage.import_from_csv(csv_file_path)
        self.assertEqual(imported_count, 3)
        
        # 验证导入结果
        total_count = self.storage.get_total_count()
        self.assertEqual(total_count, 3)
    
    def test_database_indexes(self):
        """测试数据库索引"""
        conn = sqlite3.connect(self.db_file_path)
        cursor = conn.cursor()
        
        # 检查索引是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND tbl_name='video_info'
        """)
        indexes = cursor.fetchall()
        index_names = [idx[0] for idx in indexes]
        
        # 应该有file_path的唯一索引
        self.assertTrue(any('file_path' in name for name in index_names))
        
        conn.close()
    
    def test_concurrent_access(self):
        """测试并发访问"""
        # 创建另一个存储实例
        storage2 = SQLiteStorage(self.db_file_path)
        
        # 同时插入数据
        self.storage.insert_video_info(self.test_video_infos[0])
        storage2.insert_video_info(self.test_video_infos[1])
        
        # 验证两个实例都能看到数据
        count1 = self.storage.get_total_count()
        count2 = storage2.get_total_count()
        
        self.assertEqual(count1, 2)
        self.assertEqual(count2, 2)
        
        storage2.close()

    def test_export_simple_format(self):
        """测试简化格式导出"""
        # 插入测试数据
        self.storage.insert_multiple_video_infos(self.test_video_infos)
        
        # 导出简化格式
        simple_file_path = os.path.join(self.temp_dir, "simple_export.txt")
        success = self.storage.export_simple_format(simple_file_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(simple_file_path))
        
        # 验证导出内容
        with open(simple_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 3)
            
            # 验证第一行格式
            first_line = lines[0].strip()
            parts = first_line.split(' ')
            self.assertEqual(len(parts), 3)  # filename_without_ext, filesize, logical_path
            
            # 验证文件名没有后缀
            filename_without_ext = parts[0]
            self.assertEqual(filename_without_ext, "video_0")  # 原文件名是video_0.mp4
            
            # 验证文件大小格式
            filesize = parts[1]
            self.assertTrue(filesize.endswith('G'))  # 应该以G结尾
            
            # 验证逻辑路径
            logical_path = parts[2]
            self.assertEqual(logical_path, "test/path_0")

    def test_export_simple_format_empty_database(self):
        """测试空数据库的简化格式导出"""
        simple_file_path = os.path.join(self.temp_dir, "empty_simple_export.txt")
        success = self.storage.export_simple_format(simple_file_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(simple_file_path))
        
        # 验证文件为空
        with open(simple_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertEqual(content, "")

    def test_export_simple_format_with_special_characters(self):
        """测试包含特殊字符的文件名的简化格式导出"""
        # 创建包含特殊字符的测试数据
        special_video_info = VideoInfo("/path/to/测试视频.mp4", tags=["test"], logical_path="测试/路径")
        special_video_info.width = 1920
        special_video_info.height = 1080
        special_video_info.duration = 120.5
        special_video_info.video_codec = "h264"
        special_video_info.audio_codec = "aac"
        special_video_info.file_size = 75000000
        special_video_info.bit_rate = 5000000
        special_video_info.frame_rate = 30.0
        
        self.storage.insert_video_info(special_video_info)
        
        # 导出简化格式
        simple_file_path = os.path.join(self.temp_dir, "special_simple_export.txt")
        success = self.storage.export_simple_format(simple_file_path)
        self.assertTrue(success)
        
        # 验证导出内容
        with open(simple_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            
            first_line = lines[0].strip()
            parts = first_line.split(' ')
            
            # 验证文件名没有后缀且保留中文字符
            filename_without_ext = parts[0]
            self.assertEqual(filename_without_ext, "测试视频")

    def test_export_simple_format_invalid_path(self):
        """测试无效路径的简化格式导出"""
        # 尝试导出到不存在的目录
        invalid_path = "/nonexistent/directory/simple_export.txt"
        success = self.storage.export_simple_format(invalid_path)
        self.assertFalse(success)


    def test_search_videos_by_codes_single(self):
        """测试根据单个视频code查询"""
        # 插入测试数据
        video_info = VideoInfo("/path/to/ABC-123.mp4", tags=["test"], logical_path="test/ABC-123.mp4")
        video_info.width = 1920
        video_info.height = 1080
        video_info.duration = 120.5
        video_info.video_codec = "h264"
        video_info.audio_codec = "aac"
        video_info.file_size = 1024000000
        video_info.bit_rate = 5000000
        video_info.frame_rate = 30.0
        
        video_id = self.storage.insert_video_info(video_info)
        self.assertIsNotNone(video_id)
        
        # 测试查询
        results = self.storage.search_videos_by_codes(['ABC-123'])
        
        # 验证结果
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result['video_code'], 'ABC-123')
        self.assertEqual(result['file_size'], 1024000000)
        self.assertEqual(result['logical_path'], 'test/ABC-123.mp4')

    def test_search_videos_by_codes_multiple(self):
        """测试根据多个视频code查询"""
        # 插入测试数据
        video_infos = [
            VideoInfo("/path/to/ABC-123.mp4", tags=["test"], logical_path="test/ABC-123.mp4"),
            VideoInfo("/path/to/DEF-456.mkv", tags=["test"], logical_path="test/DEF-456.mkv"),
            VideoInfo("/path/to/GHI-789.avi", tags=["test"], logical_path="test/GHI-789.avi")
        ]
        
        for i, video_info in enumerate(video_infos):
            video_info.width = 1920
            video_info.height = 1080
            video_info.duration = 120.5 + i * 10
            video_info.video_codec = "h264"
            video_info.audio_codec = "aac"
            video_info.file_size = 1024000000 + i * 100000000
            video_info.bit_rate = 5000000
            video_info.frame_rate = 30.0
            
            video_id = self.storage.insert_video_info(video_info)
            self.assertIsNotNone(video_id)
        
        # 测试查询多个code
        results = self.storage.search_videos_by_codes(['ABC-123', 'DEF-456'])
        
        # 验证结果
        self.assertEqual(len(results), 2)
        codes = [result['video_code'] for result in results]
        self.assertIn('ABC-123', codes)
        self.assertIn('DEF-456', codes)

    def test_search_videos_by_codes_case_insensitive(self):
        """测试视频code查询忽略大小写"""
        # 插入测试数据
        video_info = VideoInfo("/path/to/ABC-123.mp4", tags=["test"], logical_path="test/ABC-123.mp4")
        video_info.width = 1920
        video_info.height = 1080
        video_info.duration = 120.5
        video_info.video_codec = "h264"
        video_info.audio_codec = "aac"
        video_info.file_size = 1024000000
        video_info.bit_rate = 5000000
        video_info.frame_rate = 30.0
        
        video_id = self.storage.insert_video_info(video_info)
        self.assertIsNotNone(video_id)
        
        # 测试小写查询
        results = self.storage.search_videos_by_codes(['abc-123'])
        
        # 验证结果
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result['video_code'], 'ABC-123')  # 返回原始大小写

    def test_search_videos_by_codes_no_results(self):
        """测试视频code查询无结果"""
        # 插入测试数据
        video_info = VideoInfo("/path/to/ABC-123.mp4", tags=["test"], logical_path="test/ABC-123.mp4")
        video_info.width = 1920
        video_info.height = 1080
        video_info.duration = 120.5
        video_info.video_codec = "h264"
        video_info.audio_codec = "aac"
        video_info.file_size = 1024000000
        video_info.bit_rate = 5000000
        video_info.frame_rate = 30.0
        
        video_id = self.storage.insert_video_info(video_info)
        self.assertIsNotNone(video_id)
        
        # 测试查询不存在的code
        results = self.storage.search_videos_by_codes(['NONEXISTENT-999'])
        
        # 验证结果
        self.assertEqual(len(results), 0)

    def test_search_videos_by_codes_empty_list(self):
        """测试空code列表查询"""
        # 测试空列表
        results = self.storage.search_videos_by_codes([])
        
        # 验证结果
        self.assertEqual(len(results), 0)

    def test_search_videos_by_codes_partial_match(self):
        """测试部分匹配的视频code查询"""
        # 插入测试数据
        video_infos = [
            VideoInfo("/path/to/ABC-123.mp4", tags=["test"], logical_path="test/ABC-123.mp4"),
            VideoInfo("/path/to/DEF-456.mkv", tags=["test"], logical_path="test/DEF-456.mkv")
        ]
        
        for i, video_info in enumerate(video_infos):
            video_info.width = 1920
            video_info.height = 1080
            video_info.duration = 120.5 + i * 10
            video_info.video_codec = "h264"
            video_info.audio_codec = "aac"
            video_info.file_size = 1024000000 + i * 100000000
            video_info.bit_rate = 5000000
            video_info.frame_rate = 30.0
            
            video_id = self.storage.insert_video_info(video_info)
            self.assertIsNotNone(video_id)
        
        # 测试查询一个存在一个不存在的code
        results = self.storage.search_videos_by_codes(['ABC-123', 'NONEXISTENT-999'])
        
        # 验证结果 - 只返回存在的
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result['video_code'], 'ABC-123')

    def test_get_statistics_by_tags(self):
        """测试按标签分组统计"""
        # 插入测试数据
        video_info1 = VideoInfo("/test/video1.mp4", tags=["动作片", "高清"])
        video_info1.width = 1920
        video_info1.height = 1080
        video_info1.duration = 3600.0
        video_info1.file_size = 1024*1024*1024
        
        video_info2 = VideoInfo("/test/video2.mp4", tags=["动作片", "科幻"])
        video_info2.width = 1920
        video_info2.height = 1080
        video_info2.duration = 3600.0
        video_info2.file_size = 1024*1024*1024
        
        self.storage.insert_video_info(video_info1)
        self.storage.insert_video_info(video_info2)
        
        # 获取按标签统计
        stats = self.storage.get_statistics_by_tags()
        
        # 验证结果
        self.assertIsInstance(stats, list)
        self.assertTrue(len(stats) >= 3)  # 至少有动作片、高清、科幻三个标签
        
        # 查找动作片标签的统计
        action_stat = next((s for s in stats if s['tag'] == '动作片'), None)
        self.assertIsNotNone(action_stat)
        self.assertEqual(action_stat['count'], 2)

    def test_get_statistics_by_resolution(self):
        """测试按分辨率分组统计"""
        # 插入不同分辨率的测试数据
        video_info1 = VideoInfo("/test/video1.mp4")
        video_info1.width = 1920
        video_info1.height = 1080  # FHD
        video_info1.duration = 3600.0
        video_info1.file_size = 1024*1024*1024
        
        video_info2 = VideoInfo("/test/video2.mp4")
        video_info2.width = 3840
        video_info2.height = 2160  # 4K
        video_info2.duration = 3600.0
        video_info2.file_size = 2*1024*1024*1024
        
        video_info3 = VideoInfo("/test/video3.mp4")
        video_info3.width = 1280
        video_info3.height = 720  # HD
        video_info3.duration = 3600.0
        video_info3.file_size = 512*1024*1024
        
        self.storage.insert_video_info(video_info1)
        self.storage.insert_video_info(video_info2)
        self.storage.insert_video_info(video_info3)
        
        # 获取按分辨率统计
        stats = self.storage.get_statistics_by_resolution()
        
        # 验证结果
        self.assertIsInstance(stats, list)
        self.assertTrue(len(stats) >= 3)
        
        # 验证包含不同分辨率类别
        resolutions = [s['resolution'] for s in stats]
        self.assertIn('FHD (1920x1080)', resolutions)
        self.assertIn('4K+ (3840x2160+)', resolutions)
        self.assertIn('HD (1280x720)', resolutions)

    def test_get_statistics_by_duration(self):
        """测试按时长分组统计"""
        # 插入不同时长的测试数据
        video_info1 = VideoInfo("/test/video1.mp4")
        video_info1.width = 1920
        video_info1.height = 1080
        video_info1.duration = 1800.0  # 30分钟 - 中等
        video_info1.file_size = 1024*1024*1024
        
        video_info2 = VideoInfo("/test/video2.mp4")
        video_info2.width = 1920
        video_info2.height = 1080
        video_info2.duration = 7200.0  # 2小时 - 超长
        video_info2.file_size = 2*1024*1024*1024
        
        video_info3 = VideoInfo("/test/video3.mp4")
        video_info3.width = 1920
        video_info3.height = 1080
        video_info3.duration = 300.0  # 5分钟 - 极短
        video_info3.file_size = 512*1024*1024
        
        self.storage.insert_video_info(video_info1)
        self.storage.insert_video_info(video_info2)
        self.storage.insert_video_info(video_info3)
        
        # 获取按时长统计
        stats = self.storage.get_statistics_by_duration()
        
        # 验证结果
        self.assertIsInstance(stats, list)
        self.assertTrue(len(stats) >= 3)
        
        # 验证包含不同时长类别
        durations = [s['duration_range'] for s in stats]
        self.assertIn('中等 (30分钟-1小时)', durations)
        self.assertIn('超长 (2小时+)', durations)
        self.assertIn('极短 (<10分钟)', durations)

    def test_get_enhanced_statistics(self):
        """测试增强统计信息"""
        # 插入测试数据，包括同名视频
        video_info1 = VideoInfo("/test/path1/movie.mp4")
        video_info1.width = 1920
        video_info1.height = 1080
        video_info1.duration = 3600.0
        video_info1.file_size = 1024*1024*1024
        
        video_info2 = VideoInfo("/test/path2/movie.mkv")
        video_info2.width = 1920
        video_info2.height = 1080
        video_info2.duration = 3600.0
        video_info2.file_size = 1024*1024*1024
        
        video_info3 = VideoInfo("/test/path3/other.mp4")
        video_info3.width = 1920
        video_info3.height = 1080
        video_info3.duration = 3600.0
        video_info3.file_size = 1024*1024*1024
        
        self.storage.insert_video_info(video_info1)
        self.storage.insert_video_info(video_info2)
        self.storage.insert_video_info(video_info3)
        
        # 获取增强统计信息
        stats = self.storage.get_enhanced_statistics()
        
        # 验证结果
        self.assertIsInstance(stats, dict)
        self.assertEqual(stats['total_videos'], 3)
        self.assertEqual(stats['duplicate_video_groups'], 1)  # movie有两个版本
        self.assertEqual(stats['total_duplicate_videos'], 2)  # movie.mp4和movie.mkv
        self.assertEqual(stats['unique_videos'], 2)  # movie组和other
        
        # 验证包含基本统计信息
        self.assertIn('total_size', stats)
        self.assertIn('total_duration', stats)
        self.assertIn('avg_file_size', stats)
        self.assertIn('avg_duration', stats)

    def test_get_statistics_empty_database(self):
        """测试空数据库的统计"""
        # 获取各种统计信息
        basic_stats = self.storage.get_statistics()
        tags_stats = self.storage.get_statistics_by_tags()
        resolution_stats = self.storage.get_statistics_by_resolution()
        duration_stats = self.storage.get_statistics_by_duration()
        enhanced_stats = self.storage.get_enhanced_statistics()
        
        # 验证空数据库的统计结果
        self.assertEqual(basic_stats['total_videos'], 0)
        self.assertEqual(basic_stats['total_size'], 0)
        self.assertEqual(basic_stats['total_duration'], 0)
        
        self.assertEqual(len(tags_stats), 0)  # 空数据库应该返回空列表
        self.assertEqual(len(resolution_stats), 0)  # 空数据库应该返回空列表
        self.assertEqual(len(duration_stats), 0)  # 空数据库应该返回空列表
        
        self.assertEqual(enhanced_stats['total_videos'], 0)
        self.assertEqual(enhanced_stats['duplicate_video_groups'], 0)


if __name__ == '__main__':
    unittest.main()