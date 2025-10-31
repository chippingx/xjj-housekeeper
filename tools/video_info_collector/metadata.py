"""
视频元数据提取器

使用ffprobe提取视频文件的元数据信息。
"""

import json
import os
import subprocess
from datetime import datetime
from typing import List, Optional, Dict, Any


class VideoInfo:
    """视频信息数据类"""
    
    def __init__(self, file_path: str, tags: Optional[List[str]] = None, logical_path: Optional[str] = None):
        """
        初始化视频信息对象
        
        Args:
            file_path: 视频文件路径
            tags: 标签列表
            logical_path: 逻辑路径
        """
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.created_time = datetime.now()
        
        # 视频属性
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        self.duration: Optional[float] = None
        self.video_codec: Optional[str] = None
        self.audio_codec: Optional[str] = None
        self.file_size: Optional[int] = None
        self.bit_rate: Optional[int] = None
        self.frame_rate: Optional[float] = None
        
        # 标签和逻辑路径
        self.tags: List[str] = tags or []
        self.logical_path: Optional[str] = logical_path
        
        # 获取文件基本信息
        self._get_basic_info()
    
    def _get_basic_info(self):
        """获取文件基本信息"""
        try:
            if os.path.exists(self.file_path):
                stat = os.stat(self.file_path)
                self.file_size = stat.st_size
                self.created_time = datetime.fromtimestamp(stat.st_mtime)
        except (OSError, IOError):
            pass
    
    @property
    def resolution(self) -> Optional[str]:
        """获取分辨率字符串"""
        if self.width is not None and self.height is not None:
            return f"{self.width}x{self.height}"
        return None
    
    @property
    def duration_formatted(self) -> Optional[str]:
        """获取格式化的时长（HH:MM:SS）"""
        if self.duration is None:
            return None
        
        total_seconds = int(self.duration)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'file_path': self.file_path,
            'filename': self.filename,
            'width': self.width,
            'height': self.height,
            'resolution': self.resolution,
            'duration': self.duration,
            'duration_formatted': self.duration_formatted,
            'video_codec': self.video_codec,
            'audio_codec': self.audio_codec,
            'file_size': self.file_size,
            'bit_rate': self.bit_rate,
            'frame_rate': self.frame_rate,
            'created_time': self.created_time.isoformat() if self.created_time and hasattr(self.created_time, 'isoformat') else self.created_time,
            'tags': ';'.join(self.tags) if self.tags else '',
            'logical_path': self.logical_path or ''
        }


class VideoMetadataExtractor:
    """视频元数据提取器"""
    
    def __init__(self):
        """初始化提取器"""
        pass
    
    def extract_metadata(self, file_path: str) -> VideoInfo:
        """
        提取单个视频文件的元数据
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            VideoInfo对象
            
        Raises:
            FileNotFoundError: 文件不存在
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")
        
        video_info = VideoInfo(file_path)
        
        # 尝试使用ffprobe提取详细信息
        try:
            metadata = self._run_ffprobe(file_path)
            if metadata:
                self._parse_metadata(video_info, metadata)
        except Exception:
            # 如果ffprobe失败，只返回基本信息
            pass
        
        return video_info
    
    def batch_extract_metadata(self, file_paths: List[str]) -> List[VideoInfo]:
        """
        批量提取视频文件的元数据
        
        Args:
            file_paths: 视频文件路径列表
            
        Returns:
            VideoInfo对象列表
        """
        video_infos = []
        for file_path in file_paths:
            try:
                video_info = self.extract_metadata(file_path)
                video_infos.append(video_info)
            except FileNotFoundError:
                # 跳过不存在的文件
                continue
        
        return video_infos
    
    def _run_ffprobe(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        运行ffprobe命令获取视频信息
        
        Args:
            file_path: 视频文件路径
            
        Returns:
            解析后的JSON数据，如果失败返回None
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # 30秒超时
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
                json.JSONDecodeError, FileNotFoundError):
            pass
        
        return None
    
    def _parse_metadata(self, video_info: VideoInfo, metadata: Dict[str, Any]):
        """
        解析ffprobe返回的元数据
        
        Args:
            video_info: VideoInfo对象
            metadata: ffprobe返回的JSON数据
        """
        # 解析格式信息
        format_info = metadata.get('format', {})
        if 'duration' in format_info:
            try:
                video_info.duration = float(format_info['duration'])
            except (ValueError, TypeError):
                pass
        
        if 'size' in format_info:
            try:
                video_info.file_size = int(format_info['size'])
            except (ValueError, TypeError):
                pass
        
        if 'bit_rate' in format_info:
            try:
                video_info.bit_rate = int(format_info['bit_rate'])
            except (ValueError, TypeError):
                pass
        
        # 解析流信息
        streams = metadata.get('streams', [])
        for stream in streams:
            codec_type = stream.get('codec_type')
            
            if codec_type == 'video':
                # 视频流信息
                video_info.video_codec = stream.get('codec_name')
                
                if 'width' in stream:
                    try:
                        video_info.width = int(stream['width'])
                    except (ValueError, TypeError):
                        pass
                
                if 'height' in stream:
                    try:
                        video_info.height = int(stream['height'])
                    except (ValueError, TypeError):
                        pass
                
                # 解析帧率
                if 'r_frame_rate' in stream:
                    try:
                        frame_rate_str = stream['r_frame_rate']
                        if '/' in frame_rate_str:
                            num, den = frame_rate_str.split('/')
                            if int(den) != 0:
                                video_info.frame_rate = float(num) / float(den)
                        else:
                            video_info.frame_rate = float(frame_rate_str)
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass
            
            elif codec_type == 'audio':
                # 音频流信息
                video_info.audio_codec = stream.get('codec_name')