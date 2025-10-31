"""
测试视频文件扫描功能

Step 1: 基础视频文件扫描功能测试
- 测试目录扫描
- 测试视频文件过滤
- 测试递归扫描
- 测试文件路径处理
"""

import pytest
import tempfile
import os
from pathlib import Path
from tools.video_info_collector.scanner import VideoFileScanner


class TestVideoFileScanner:
    """测试视频文件扫描器"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = VideoFileScanner()
        
    def teardown_method(self):
        """每个测试方法后的清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_files(self, files):
        """创建测试文件"""
        created_files = []
        for file_path in files:
            full_path = Path(self.temp_dir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            # 创建有内容的文件，确保大小超过10KB过滤阈值
            with open(full_path, 'wb') as f:
                # 写入12KB的数据，确保文件不会被大小过滤器过滤掉
                f.write(b'0' * 12288)  # 12KB
            created_files.append(str(full_path))
        return created_files
    
    def test_scanner_initialization(self):
        """测试扫描器初始化"""
        scanner = VideoFileScanner()
        assert scanner is not None
        assert hasattr(scanner, 'scan_directory')
        assert hasattr(scanner, 'supported_extensions')
    
    def test_default_supported_extensions(self):
        """测试默认支持的视频扩展名"""
        scanner = VideoFileScanner()
        expected_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv'}
        assert expected_extensions.issubset(set(scanner.supported_extensions))
    
    def test_scan_empty_directory(self):
        """测试扫描空目录"""
        result = self.scanner.scan_directory(self.temp_dir)
        assert result == []
    
    def test_scan_directory_with_video_files(self):
        """测试扫描包含视频文件的目录"""
        test_files = [
            'video1.mp4',
            'video2.mkv',
            'document.txt',  # 非视频文件
            'video3.avi'
        ]
        self.create_test_files(test_files)
        
        result = self.scanner.scan_directory(self.temp_dir)
        
        # 应该只返回视频文件
        assert len(result) == 3
        video_names = [os.path.basename(path) for path in result]
        assert 'video1.mp4' in video_names
        assert 'video2.mkv' in video_names
        assert 'video3.avi' in video_names
        assert 'document.txt' not in video_names
    
    def test_scan_directory_recursive(self):
        """测试递归扫描子目录"""
        test_files = [
            'root_video.mp4',
            'subdir1/sub_video1.mkv',
            'subdir1/subdir2/deep_video.avi',
            'subdir1/document.txt'  # 非视频文件
        ]
        self.create_test_files(test_files)
        
        result = self.scanner.scan_directory(self.temp_dir, recursive=True)
        
        # 应该找到所有层级的视频文件
        assert len(result) == 3
        video_names = [os.path.basename(path) for path in result]
        assert 'root_video.mp4' in video_names
        assert 'sub_video1.mkv' in video_names
        assert 'deep_video.avi' in video_names
    
    def test_scan_directory_non_recursive(self):
        """测试非递归扫描（只扫描根目录）"""
        test_files = [
            'root_video.mp4',
            'subdir1/sub_video1.mkv',  # 子目录中的文件
            'root_video2.avi'
        ]
        self.create_test_files(test_files)
        
        result = self.scanner.scan_directory(self.temp_dir, recursive=False)
        
        # 应该只找到根目录的视频文件
        assert len(result) == 2
        video_names = [os.path.basename(path) for path in result]
        assert 'root_video.mp4' in video_names
        assert 'root_video2.avi' in video_names
        assert 'sub_video1.mkv' not in video_names
    
    def test_custom_extensions(self):
        """测试自定义扩展名过滤"""
        test_files = [
            'video1.mp4',
            'video2.mkv',
            'video3.avi',
            'video4.mov'
        ]
        self.create_test_files(test_files)
        
        # 只扫描 .mp4 和 .mkv 文件
        scanner = VideoFileScanner(extensions=['.mp4', '.mkv'])
        result = scanner.scan_directory(self.temp_dir)
        
        assert len(result) == 2
        video_names = [os.path.basename(path) for path in result]
        assert 'video1.mp4' in video_names
        assert 'video2.mkv' in video_names
        assert 'video3.avi' not in video_names
        assert 'video4.mov' not in video_names
    
    def test_scan_nonexistent_directory(self):
        """测试扫描不存在的目录"""
        nonexistent_path = "/path/that/does/not/exist"
        with pytest.raises(FileNotFoundError):
            self.scanner.scan_directory(nonexistent_path)
    
    def test_scan_file_instead_of_directory(self):
        """测试传入文件路径而不是目录路径"""
        test_file = Path(self.temp_dir) / 'test.mp4'
        test_file.touch()
        
        with pytest.raises(NotADirectoryError):
            self.scanner.scan_directory(str(test_file))
    
    def test_relative_path_handling(self):
        """测试相对路径处理"""
        test_files = ['video1.mp4', 'subdir/video2.mkv']
        self.create_test_files(test_files)
        
        result = self.scanner.scan_directory(self.temp_dir)
        
        # 所有返回的路径都应该是绝对路径
        for path in result:
            assert os.path.isabs(path)
            assert os.path.exists(path)
    
    def test_case_insensitive_extensions(self):
        """测试扩展名大小写不敏感"""
        test_files = [
            'video1.MP4',  # 大写
            'video2.MkV',  # 混合大小写
            'video3.avi'   # 小写
        ]
        self.create_test_files(test_files)
        
        result = self.scanner.scan_directory(self.temp_dir)
        
        # 应该找到所有文件，不管扩展名大小写
        assert len(result) == 3