"""
视频文件扫描器

负责扫描目录中的视频文件，支持递归扫描和扩展名过滤。
"""

import os
from pathlib import Path
from typing import List, Set


class VideoFileScanner:
    """视频文件扫描器"""
    
    def __init__(self, extensions: List[str] = None):
        """
        初始化扫描器
        
        Args:
            extensions: 支持的视频文件扩展名列表，如果为None则使用默认扩展名
        """
        if extensions is None:
            self.supported_extensions = {
                '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', 
                '.m4v', '.webm', '.3gp', '.mpg', '.mpeg'
            }
        else:
            # 转换为小写并确保以点开头
            self.supported_extensions = set()
            for ext in extensions:
                if not ext.startswith('.'):
                    ext = '.' + ext
                self.supported_extensions.add(ext.lower())
    
    def scan_directory(self, directory_path: str, recursive: bool = True) -> List[str]:
        """
        扫描目录中的视频文件
        
        Args:
            directory_path: 要扫描的目录路径
            recursive: 是否递归扫描子目录
            
        Returns:
            视频文件的绝对路径列表
            
        Raises:
            FileNotFoundError: 目录不存在
            NotADirectoryError: 路径不是目录
        """
        directory_path = os.path.abspath(directory_path)
        
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise NotADirectoryError(f"Path is not a directory: {directory_path}")
        
        video_files = []
        
        if recursive:
            # 递归扫描所有子目录
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self._is_valid_video_file(file, file_path):
                        video_files.append(file_path)
        else:
            # 只扫描根目录
            try:
                for item in os.listdir(directory_path):
                    item_path = os.path.join(directory_path, item)
                    if os.path.isfile(item_path) and self._is_valid_video_file(item, item_path):
                        video_files.append(item_path)
            except PermissionError:
                # 如果没有权限访问目录，返回空列表
                pass
        
        return sorted(video_files)
    
    def _is_valid_video_file(self, filename: str, file_path: str) -> bool:
        """
        检查文件是否为有效的视频文件（包含隐藏文件过滤）
        
        Args:
            filename: 文件名
            file_path: 文件的完整路径
            
        Returns:
            如果是有效的视频文件返回True，否则返回False
        """
        # 首先检查是否为视频文件
        if not self._is_video_file(filename):
            return False
        
        # 过滤隐藏文件（以点开头的文件名）
        if filename.startswith('.'):
            return False
        
        # 过滤系统生成的元数据文件（以._开头）
        if filename.startswith('._'):
            return False
        
        # 检查文件大小，过滤小于10KB的文件（可能是损坏或无效的视频文件）
        try:
            file_size = os.path.getsize(file_path)
            # 10KB = 10 * 1024 bytes
            if file_size < 10 * 1024:
                return False
        except (OSError, IOError):
            # 如果无法获取文件大小，跳过该文件
            return False
        
        return True
    
    def _is_video_file(self, filename: str) -> bool:
        """
        检查文件是否为视频文件（仅检查扩展名）
        
        Args:
            filename: 文件名
            
        Returns:
            如果是视频文件返回True，否则返回False
        """
        if not filename:
            return False
        
        # 获取文件扩展名并转换为小写
        _, ext = os.path.splitext(filename)
        return ext.lower() in self.supported_extensions