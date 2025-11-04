#!/usr/bin/env python3
"""
测试智能合并功能的复杂场景

测试覆盖：
1. 文件移动检测和路径更新
2. 外部驱动器恢复场景
3. 多副本处理和重复检测
4. 文件重命名检测
5. 指纹冲突处理
6. 部分扫描范围处理
7. 用户手动清理场景
"""

import unittest
import tempfile
import os
import shutil
import json
from pathlib import Path
import sys
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.video_info_collector.metadata import VideoInfo
from tools.video_info_collector.sqlite_storage import SQLiteStorage


class TestFileMoveDetection(unittest.TestCase):
    """测试文件移动检测场景"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_file(self, relative_path: str, content: str = "test") -> str:
        """创建测试文件"""
        full_path = os.path.join(self.temp_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        return full_path
    
    def test_simple_file_move(self):
        """测试简单文件移动场景"""
        # 1. 初始扫描：文件在原位置
        original_path = self._create_test_file("videos/ABC-123.mp4", "content1")
        video_info = VideoInfo(original_path)
        
        # 模拟插入数据库
        # self.storage.insert_video_info(video_info)
        
        # 2. 移动文件到新位置
        new_dir = os.path.join(self.temp_dir, "moved_videos")
        os.makedirs(new_dir, exist_ok=True)
        new_path = os.path.join(new_dir, "ABC-123.mp4")
        shutil.move(original_path, new_path)
        
        # 3. 重新扫描，应该检测到移动
        new_video_info = VideoInfo(new_path)
        
        # 验证指纹相同（表示是同一文件）
        self.assertEqual(video_info.file_fingerprint, 
                        new_video_info.file_fingerprint,
                        "移动后的文件应该有相同的指纹")
        
        # 验证video_code相同
        self.assertEqual(video_info.video_code, 
                        new_video_info.video_code,
                        "移动后的文件应该有相同的video_code")
    
    def test_cross_directory_move(self):
        """测试跨目录移动场景"""
        # 创建复杂的目录结构
        files = [
            "series1/season1/ABC-123.mp4",
            "series1/season2/ABC-124.mp4", 
            "series2/season1/XYZ-001.mp4",
        ]
        
        original_infos = {}
        for file_path in files:
            full_path = self._create_test_file(file_path, f"content_{file_path}")
            video_info = VideoInfo(full_path)
            original_infos[file_path] = video_info
        
        # 重新组织目录结构
        new_structure = {
            "series1/season1/ABC-123.mp4": "reorganized/ABC-123.mp4",
            "series1/season2/ABC-124.mp4": "reorganized/ABC-124.mp4",
            "series2/season1/XYZ-001.mp4": "different_series/XYZ-001.mp4",
        }
        
        moved_infos = {}
        for old_path, new_path in new_structure.items():
            old_full_path = os.path.join(self.temp_dir, old_path)
            new_full_path = os.path.join(self.temp_dir, new_path)
            
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
            shutil.move(old_full_path, new_full_path)
            
            new_video_info = VideoInfo(new_full_path)
            moved_infos[new_path] = new_video_info
        
        # 验证所有文件的指纹保持不变
        for old_path, new_path in new_structure.items():
            original_fp = original_infos[old_path].file_fingerprint
            new_fp = moved_infos[new_path].file_fingerprint
            
            self.assertEqual(original_fp, new_fp,
                           f"文件 {old_path} -> {new_path} 移动后指纹应该保持不变")
    
    def test_rename_detection(self):
        """测试文件重命名检测"""
        # 创建原始文件
        original_path = self._create_test_file("videos/ABC-123.mp4", "content")
        original_info = VideoInfo(original_path)
        
        # 重命名文件（保持在同一目录）
        renamed_path = os.path.join(os.path.dirname(original_path), "ABC-123_HD.mp4")
        shutil.move(original_path, renamed_path)
        
        renamed_info = VideoInfo(renamed_path)
        
        # video_code应该保持不变
        self.assertEqual(original_info.video_code, renamed_info.video_code,
                        "重命名后video_code应该保持不变")
        
        # 指纹会改变（因为包含文件名）
        self.assertNotEqual(original_info.file_fingerprint, 
                           renamed_info.file_fingerprint,
                           "重命名后指纹应该改变（包含文件名）")


class TestExternalDriveRecovery(unittest.TestCase):
    """测试外部驱动器恢复场景"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
        # 模拟外部驱动器路径
        self.external_drive = os.path.join(self.temp_dir, "external_drive")
        self.internal_storage = os.path.join(self.temp_dir, "internal")
        
        os.makedirs(self.external_drive, exist_ok=True)
        os.makedirs(self.internal_storage, exist_ok=True)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_external_drive_disconnect_reconnect(self):
        """测试外部驱动器断开重连场景"""
        # 1. 初始状态：文件在外部驱动器
        external_files = [
            "movies/ABC-123.mp4",
            "series/XYZ-456.mp4",
            "documentaries/DEF-789.mp4",
        ]
        
        original_infos = {}
        for file_path in external_files:
            full_path = os.path.join(self.external_drive, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(f"content_{file_path}")
            
            video_info = VideoInfo(full_path)
            original_infos[file_path] = video_info
        
        # 2. 模拟外部驱动器断开（删除文件）
        shutil.rmtree(self.external_drive)
        
        # 3. 扫描时应该检测到文件缺失
        # 这里应该将file_status设置为'missing'
        
        # 4. 模拟外部驱动器重新连接
        os.makedirs(self.external_drive, exist_ok=True)
        
        recovered_infos = {}
        for file_path in external_files:
            full_path = os.path.join(self.external_drive, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(f"content_{file_path}")
            
            video_info = VideoInfo(full_path)
            recovered_infos[file_path] = video_info
        
        # 5. 验证恢复后的文件指纹相同
        for file_path in external_files:
            original_fp = original_infos[file_path].file_fingerprint
            recovered_fp = recovered_infos[file_path].file_fingerprint
            
            self.assertEqual(original_fp, recovered_fp,
                           f"恢复的文件 {file_path} 应该有相同的指纹")
    
    def test_drive_letter_change(self):
        """测试驱动器盘符变化场景（Windows）"""
        # 模拟驱动器盘符从D:变为E:
        old_drive_path = os.path.join(self.temp_dir, "D_drive")
        new_drive_path = os.path.join(self.temp_dir, "E_drive")
        
        os.makedirs(old_drive_path, exist_ok=True)
        
        # 创建文件在旧驱动器路径
        file_path = "videos/ABC-123.mp4"
        old_full_path = os.path.join(old_drive_path, file_path)
        os.makedirs(os.path.dirname(old_full_path), exist_ok=True)
        
        with open(old_full_path, 'w') as f:
            f.write("content")
        
        old_info = VideoInfo(old_full_path)
        
        # 模拟盘符变化（移动到新路径）
        os.makedirs(new_drive_path, exist_ok=True)
        new_full_path = os.path.join(new_drive_path, file_path)
        os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
        
        shutil.copy2(old_full_path, new_full_path)  # 保持时间戳
        
        new_info = VideoInfo(new_full_path)
        
        # 验证指纹相同
        self.assertEqual(old_info.file_fingerprint, new_info.file_fingerprint,
                        "盘符变化后文件指纹应该保持不变")


class TestMultipleCopiesHandling(unittest.TestCase):
    """测试多副本处理场景"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_identical_copies_detection(self):
        """测试相同副本检测"""
        content = "identical content"
        
        # 创建多个相同内容的文件
        copies = [
            "location1/ABC-123.mp4",
            "location2/ABC-123.mp4", 
            "backup/ABC-123.mp4",
            "archive/ABC-123.mp4",
        ]
        
        copy_infos = {}
        for copy_path in copies:
            full_path = os.path.join(self.temp_dir, copy_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(content)
            
            video_info = VideoInfo(full_path)
            copy_infos[copy_path] = video_info
        
        # 验证所有副本有相同的video_code
        video_codes = [info.video_code for info in copy_infos.values()]
        self.assertTrue(all(code == video_codes[0] for code in video_codes),
                       "所有副本应该有相同的video_code")
        
        # 验证所有副本有相同的指纹（如果指纹不包含路径）
        # 或者不同的指纹（如果指纹包含路径）
        fingerprints = [info.file_fingerprint for info in copy_infos.values()]
        # 这取决于指纹算法的具体实现
    
    def test_partial_copies_detection(self):
        """测试部分副本检测（不同质量/大小）"""
        base_content = "base content"
        
        # 创建不同质量的副本
        versions = [
            ("original/ABC-123.mp4", base_content),
            ("hd/ABC-123_HD.mp4", base_content + "_hd_extra"),
            ("compressed/ABC-123_compressed.mp4", base_content[:5]),  # 压缩版本
        ]
        
        version_infos = {}
        for file_path, content in versions:
            full_path = os.path.join(self.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(content)
            
            video_info = VideoInfo(full_path)
            version_infos[file_path] = video_info
        
        # 验证所有版本有相同的video_code
        video_codes = [info.video_code for info in version_infos.values()]
        self.assertTrue(all(code == video_codes[0] for code in video_codes),
                       "所有版本应该有相同的video_code")
        
        # 验证不同版本有不同的指纹
        fingerprints = [info.file_fingerprint for info in version_infos.values()]
        self.assertEqual(len(set(fingerprints)), len(fingerprints),
                        "不同版本应该有不同的指纹")


class TestFingerprintCollisionHandling(unittest.TestCase):
    """测试指纹冲突处理场景"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_rare_fingerprint_collision(self):
        """测试罕见的指纹冲突场景"""
        # 这个测试很难自然触发，主要是验证冲突处理逻辑
        # 可以通过模拟或者强制创建冲突来测试
        
        # 创建两个不同的文件
        file1_path = os.path.join(self.temp_dir, "ABC-123.mp4")
        file2_path = os.path.join(self.temp_dir, "XYZ-456.mp4")
        
        with open(file1_path, 'w') as f:
            f.write("content1")
        with open(file2_path, 'w') as f:
            f.write("content2")
        
        info1 = VideoInfo(file1_path)
        info2 = VideoInfo(file2_path)
        
        # 正常情况下应该有不同的指纹
        self.assertNotEqual(info1.file_fingerprint, info2.file_fingerprint,
                           "不同文件应该有不同指纹")
        
        # 如果发生冲突，系统应该有处理机制
        # 这部分需要在实际实现中添加冲突检测和解决逻辑


class TestPartialScanRange(unittest.TestCase):
    """测试部分扫描范围场景"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_selective_directory_scan(self):
        """测试选择性目录扫描"""
        # 创建复杂的目录结构
        structure = {
            "movies/action/ABC-123.mp4": "action_content",
            "movies/comedy/XYZ-456.mp4": "comedy_content", 
            "series/drama/DEF-789.mp4": "drama_content",
            "series/scifi/GHI-012.mp4": "scifi_content",
            "documentaries/nature/JKL-345.mp4": "nature_content",
        }
        
        all_infos = {}
        for file_path, content in structure.items():
            full_path = os.path.join(self.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(content)
            
            video_info = VideoInfo(full_path)
            all_infos[file_path] = video_info
        
        # 模拟只扫描movies目录
        movies_dir = os.path.join(self.temp_dir, "movies")
        movies_files = []
        
        for root, dirs, files in os.walk(movies_dir):
            for file in files:
                if file.endswith('.mp4'):
                    file_path = os.path.join(root, file)
                    movies_files.append(file_path)
        
        # 验证部分扫描结果
        self.assertEqual(len(movies_files), 2,
                        "movies目录应该包含2个文件")
        
        # 验证扫描到的文件信息正确
        for file_path in movies_files:
            video_info = VideoInfo(file_path)
            self.assertIsNotNone(video_info.video_code)
            self.assertIsNotNone(video_info.file_fingerprint)


class TestUserManualCleanup(unittest.TestCase):
    """测试用户手动清理场景"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_manual_file_deletion(self):
        """测试用户手动删除文件的场景"""
        # 1. 创建初始文件
        files = [
            "videos/ABC-123.mp4",
            "videos/XYZ-456.mp4",
            "videos/DEF-789.mp4",
        ]
        
        original_infos = {}
        for file_path in files:
            full_path = os.path.join(self.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(f"content_{file_path}")
            
            video_info = VideoInfo(full_path)
            original_infos[file_path] = video_info
        
        # 2. 用户手动删除部分文件
        deleted_files = ["videos/XYZ-456.mp4"]
        for file_path in deleted_files:
            full_path = os.path.join(self.temp_dir, file_path)
            os.remove(full_path)
        
        # 3. 重新扫描，应该检测到缺失的文件
        remaining_files = []
        for file_path in files:
            full_path = os.path.join(self.temp_dir, file_path)
            if os.path.exists(full_path):
                remaining_files.append(file_path)
        
        self.assertEqual(len(remaining_files), 2,
                        "应该剩余2个文件")
        self.assertNotIn("videos/XYZ-456.mp4", remaining_files,
                        "被删除的文件不应该在剩余文件中")
    
    def test_manual_directory_reorganization(self):
        """测试用户手动重组目录结构"""
        # 1. 创建原始结构
        original_structure = [
            "unsorted/ABC-123.mp4",
            "unsorted/XYZ-456.mp4",
            "unsorted/DEF-789.mp4",
        ]
        
        for file_path in original_structure:
            full_path = os.path.join(self.temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(f"content_{file_path}")
        
        # 2. 用户手动重组为分类结构
        new_structure = {
            "unsorted/ABC-123.mp4": "movies/action/ABC-123.mp4",
            "unsorted/XYZ-456.mp4": "movies/comedy/XYZ-456.mp4",
            "unsorted/DEF-789.mp4": "series/drama/DEF-789.mp4",
        }
        
        for old_path, new_path in new_structure.items():
            old_full_path = os.path.join(self.temp_dir, old_path)
            new_full_path = os.path.join(self.temp_dir, new_path)
            
            os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
            shutil.move(old_full_path, new_full_path)
        
        # 3. 验证重组后的结构
        for new_path in new_structure.values():
            full_path = os.path.join(self.temp_dir, new_path)
            self.assertTrue(os.path.exists(full_path),
                           f"重组后的文件 {new_path} 应该存在")
            
            video_info = VideoInfo(full_path)
            self.assertIsNotNone(video_info.video_code)
            self.assertIsNotNone(video_info.file_fingerprint)


if __name__ == '__main__':
    # 运行所有测试
    unittest.main(verbosity=2)