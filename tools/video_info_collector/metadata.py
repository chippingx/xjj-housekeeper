"""
视频元数据提取器

使用ffprobe提取视频文件的元数据信息。
"""

import json
import os
import subprocess
import hashlib
import re
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any


_i18n_cache: Dict[str, Dict[str, Any]] = {}


def _resolve_i18n_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve() / "i18n"
    return Path(__file__).resolve().parents[2] / "i18n"


def _normalize_language(value: Optional[str]) -> str:
    if not value:
        return "zh_CN"
    raw = value.split(".")[0].replace("-", "_").strip()
    if raw in {"C", "POSIX"}:
        return "en_US"
    mapping = {
        "en": "en_US",
        "zh": "zh_CN",
        "ja": "ja_JP",
        "ko": "ko_KR",
        "th": "th_TH",
    }
    if raw in mapping.values():
        return raw
    short = raw.split("_")[0]
    return mapping.get(short, "zh_CN")


def _load_i18n(lang: str) -> None:
    if lang in _i18n_cache:
        return
    path = _resolve_i18n_dir() / f"{lang}.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            _i18n_cache[lang] = json.load(f) or {}
    except Exception:
        _i18n_cache[lang] = {}


def _t(key: str, default: Optional[str] = None) -> str:
    lang = _normalize_language(os.environ.get("XJJ_LANG") or os.environ.get("LANGUAGE") or os.environ.get("LANG"))
    _load_i18n(lang)
    _load_i18n("zh_CN")
    data = _i18n_cache.get(lang, {})
    fallback = _i18n_cache.get("zh_CN", {})
    if key in data:
        value = data[key]
    elif key in fallback:
        value = fallback[key]
    else:
        value = default if default is not None else key
    try:
        return str(value).format()
    except Exception:
        return str(value)


def extract_video_code(filename: str) -> Optional[str]:
    """
    从文件名中提取视频编码
    
    Args:
        filename: 文件名
        
    Returns:
        Optional[str]: 提取的视频编码，如果没有找到特定模式则返回None
    """
    if not filename:
        return None
    
    # 定义多种视频编码格式的正则表达式
    patterns = [
        r'([A-Z]{2,5}-\d{3,5})(?=[\W_]|$)',      # 如 ABC-123, TST-456 (字母-数字，限制长度)
        r'([A-Z]{3}-[A-Z]{3})(?=[\W_]|$)',       # 如 ABC-abc (3字母-3字母，严格格式)
        r'([A-Z]+\d{3,})(?=[\W_]|$)',            # 如 TEST1234, DEMO456
        r'(\d{6}_\d{3})(?=[\W_]|$)',             # 如 123456_789
        r'([A-Z]{3,}\-\d{2,})(?=[\W_]|$)',       # 如 TESTS-123
    ]
    
    for pattern in patterns:
        # 使用不区分大小写的匹配，但返回原始字符串
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # 如果没有匹配到特定模式，返回None
    return None


def _normalize_duration(value: Any) -> Optional[int]:
    try:
        return int(round(float(value)))
    except (ValueError, TypeError):
        return None


def _normalize_frame_rate(value: Any) -> Optional[int]:
    try:
        return int(round(float(value)))
    except (ValueError, TypeError):
        return None


def _parse_duration_string(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return _normalize_duration(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return _normalize_duration(text)
    except Exception:
        pass
    if ":" in text:
        parts = text.split(":")
        try:
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
            elif len(parts) == 2:
                hours = 0.0
                minutes = float(parts[0])
                seconds = float(parts[1])
            else:
                return None
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return _normalize_duration(total_seconds)
        except (ValueError, TypeError):
            return None
    return None


def generate_file_fingerprint(
    filename: str,
    file_size: Optional[int],
    video_code: Optional[str],
) -> str:
    if not filename:
        return ""
    fingerprint_data = []
    base_name = os.path.splitext(filename)[0]
    fingerprint_data.append(base_name.lower())
    if file_size is not None:
        fingerprint_data.append(str(file_size))
    if video_code:
        fingerprint_data.append(video_code.lower())
    fingerprint_string = '|'.join(fingerprint_data)
    return hashlib.md5(fingerprint_string.encode('utf-8')).hexdigest()


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
        
        # 新增字段
        self.video_code: Optional[str] = None
        self.file_fingerprint: Optional[str] = None
        self._file_status: str = 'present'  # present/missing/deleted
        self.last_merge_time: Optional[datetime] = None
        
        # 获取文件基本信息
        self._get_basic_info()
        
        # 提取video_code
        self._extract_video_code()
        
        # 生成文件指纹
        self._generate_fingerprint()
    
    def _get_basic_info(self):
        """获取文件基本信息"""
        try:
            if os.path.exists(self.file_path):
                stat = os.stat(self.file_path)
                self.file_size = stat.st_size
                self.created_time = datetime.fromtimestamp(stat.st_mtime)
        except (OSError, IOError):
            pass
    
    def _extract_video_code(self):
        """提取视频编码"""
        self.video_code = extract_video_code(self.filename)
    
    def _generate_fingerprint(self):
        """生成文件指纹"""
        self.file_fingerprint = generate_file_fingerprint(
            filename=self.filename,
            file_size=self.file_size,
            video_code=self.video_code,
        )
    
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
    
    @property
    def file_status(self) -> str:
        """获取文件状态"""
        return self._file_status
    
    @file_status.setter
    def file_status(self, value: str):
        """设置文件状态，验证有效性"""
        valid_statuses = ['present', 'missing', 'deleted']
        if value not in valid_statuses:
            raise ValueError(f"Invalid file status '{value}'. Valid statuses are: {valid_statuses}")
        self._file_status = value
    
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
            'logical_path': self.logical_path or '',
            'video_code': self.video_code,
            'file_fingerprint': self.file_fingerprint,
            'file_status': self.file_status,
            'last_merge_time': self.last_merge_time.isoformat() if self.last_merge_time and hasattr(self.last_merge_time, 'isoformat') else self.last_merge_time
        }


_ffprobe_missing_warned = False


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
                video_info._generate_fingerprint()
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
            ffprobe_cmd = self._resolve_ffprobe_command()
            if not ffprobe_cmd:
                return None
            cmd = [
                ffprobe_cmd,
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

    def _resolve_ffprobe_command(self) -> Optional[str]:
        env_path = os.environ.get("FFPROBE_PATH") or os.environ.get("XJJ_FFPROBE_PATH")
        if env_path and os.path.exists(env_path):
            return env_path
        bundle_candidates = []
        if hasattr(sys, "_MEIPASS") and sys._MEIPASS:
            bundle_candidates.extend([
                os.path.join(sys._MEIPASS, "ffprobe"),
                os.path.join(sys._MEIPASS, "ffprobe.exe"),
            ])
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            bundle_candidates.extend([
                os.path.join(exe_dir, "ffprobe"),
                os.path.join(exe_dir, "ffprobe.exe"),
            ])
        for candidate in bundle_candidates:
            if os.path.exists(candidate):
                return candidate
        resolved = shutil.which("ffprobe")
        if resolved:
            return resolved
        if sys.platform == "darwin":
            candidates = [
                "/opt/homebrew/bin/ffprobe",
                "/usr/local/bin/ffprobe",
                "/usr/bin/ffprobe",
            ]
        else:
            candidates = [
                "/usr/local/bin/ffprobe",
                "/usr/bin/ffprobe",
                "/bin/ffprobe",
            ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        global _ffprobe_missing_warned
        if not _ffprobe_missing_warned:
            message = _t(
                "warning.ffprobe_missing",
                "FFprobe not found. Video metadata extraction will be unavailable. Install ffmpeg/ffprobe or set FFPROBE_PATH/XJJ_FFPROBE_PATH.",
            )
            print(f"⚠️ {message}", file=sys.stderr)
            _ffprobe_missing_warned = True
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
            video_info.duration = _parse_duration_string(format_info.get('duration'))
        if video_info.duration is None:
            tags = format_info.get('tags', {}) if isinstance(format_info.get('tags'), dict) else {}
            if tags:
                video_info.duration = _parse_duration_string(
                    tags.get('DURATION') or tags.get('duration')
                )
        
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
                
                if video_info.duration is None and 'duration' in stream:
                    video_info.duration = _parse_duration_string(stream.get('duration'))
                if video_info.duration is None:
                    stream_tags = stream.get('tags', {}) if isinstance(stream.get('tags'), dict) else {}
                    if stream_tags:
                        video_info.duration = _parse_duration_string(
                            stream_tags.get('DURATION') or stream_tags.get('duration')
                        )
                
                # 解析帧率
                if 'r_frame_rate' in stream:
                    try:
                        frame_rate_str = stream['r_frame_rate']
                        if '/' in frame_rate_str:
                            num, den = frame_rate_str.split('/')
                            if int(den) != 0:
                                video_info.frame_rate = _normalize_frame_rate(float(num) / float(den))
                        else:
                            video_info.frame_rate = _normalize_frame_rate(frame_rate_str)
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass
            
            elif codec_type == 'audio':
                # 音频流信息
                video_info.audio_codec = stream.get('codec_name')
