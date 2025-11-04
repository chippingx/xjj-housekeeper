"""
文件指纹管理器

提供高级的文件指纹生成、比较和管理功能，用于检测文件移动、重复和变化。
"""

import hashlib
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set

try:
    from .metadata import VideoInfo
except ImportError:
    from metadata import VideoInfo


class FingerprintManager:
    """文件指纹管理器"""
    
    def __init__(self):
        self.fingerprint_cache: Dict[str, str] = {}
        self.collision_count = 0
    
    def generate_fingerprint(self, video_info: VideoInfo) -> str:
        """
        生成文件指纹
        
        Args:
            video_info: 视频信息对象
            
        Returns:
            str: 文件指纹（MD5哈希）
        """
        if not video_info.filename:
            return ""
        
        # 组合指纹信息：文件名 + 文件大小 + 创建时间 + video_code
        fingerprint_data = []
        
        # 文件名（去除扩展名，转小写）
        base_name = os.path.splitext(video_info.filename)[0]
        fingerprint_data.append(base_name.lower())
        
        # 文件大小
        if video_info.file_size is not None:
            fingerprint_data.append(str(video_info.file_size))
        
        # 创建时间（精确到秒）
        if video_info.created_time:
            if hasattr(video_info.created_time, 'timestamp'):
                fingerprint_data.append(str(int(video_info.created_time.timestamp())))
            else:
                fingerprint_data.append(str(video_info.created_time))
        
        # video_code
        if video_info.video_code:
            fingerprint_data.append(video_info.video_code.lower())
        
        # 生成MD5哈希
        fingerprint_string = '|'.join(fingerprint_data)
        fingerprint = hashlib.md5(fingerprint_string.encode('utf-8')).hexdigest()
        
        # 缓存指纹
        self.fingerprint_cache[video_info.file_path] = fingerprint
        
        return fingerprint
    
    def generate_lightweight_fingerprint(self, filename: str, file_size: int, 
                                       created_time: datetime, video_code: Optional[str] = None) -> str:
        """
        生成轻量级指纹（不需要VideoInfo对象）
        
        Args:
            filename: 文件名
            file_size: 文件大小
            created_time: 创建时间
            video_code: 视频编码（可选）
            
        Returns:
            str: 文件指纹
        """
        fingerprint_data = []
        
        # 文件名（去除扩展名，转小写）
        base_name = os.path.splitext(filename)[0]
        fingerprint_data.append(base_name.lower())
        
        # 文件大小
        fingerprint_data.append(str(file_size))
        
        # 创建时间（精确到秒）
        if hasattr(created_time, 'timestamp'):
            fingerprint_data.append(str(int(created_time.timestamp())))
        else:
            fingerprint_data.append(str(created_time))
        
        # video_code
        if video_code:
            fingerprint_data.append(video_code.lower())
        
        # 生成MD5哈希
        fingerprint_string = '|'.join(fingerprint_data)
        return hashlib.md5(fingerprint_string.encode('utf-8')).hexdigest()
    
    def compare_fingerprints(self, fp1: str, fp2: str) -> bool:
        """比较两个指纹是否相同"""
        return fp1 == fp2
    
    def detect_potential_moves(self, video_infos: List[VideoInfo]) -> List[Dict[str, any]]:
        """
        检测潜在的文件移动
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            List[Dict]: 潜在移动的文件对列表
        """
        fingerprint_groups: Dict[str, List[VideoInfo]] = {}
        
        # 按指纹分组
        for video_info in video_infos:
            if not video_info.file_fingerprint:
                video_info.file_fingerprint = self.generate_fingerprint(video_info)
            
            fp = video_info.file_fingerprint
            if fp not in fingerprint_groups:
                fingerprint_groups[fp] = []
            fingerprint_groups[fp].append(video_info)
        
        # 找出有多个文件的指纹组（潜在的重复或移动）
        potential_moves = []
        for fingerprint, videos in fingerprint_groups.items():
            if len(videos) > 1:
                # 按路径排序，可能的移动模式
                videos.sort(key=lambda v: v.file_path)
                
                for i in range(len(videos) - 1):
                    potential_moves.append({
                        'fingerprint': fingerprint,
                        'source': videos[i],
                        'target': videos[i + 1],
                        'confidence': self._calculate_move_confidence(videos[i], videos[i + 1])
                    })
        
        return potential_moves
    
    def _calculate_move_confidence(self, source: VideoInfo, target: VideoInfo) -> float:
        """
        计算文件移动的置信度
        
        Args:
            source: 源文件信息
            target: 目标文件信息
            
        Returns:
            float: 置信度（0-1）
        """
        confidence = 0.0
        
        # 相同的video_code增加置信度
        if source.video_code and target.video_code and source.video_code == target.video_code:
            confidence += 0.4
        
        # 相同的文件大小增加置信度
        if source.file_size and target.file_size and source.file_size == target.file_size:
            confidence += 0.3
        
        # 文件名相似性
        source_name = os.path.splitext(source.filename)[0].lower()
        target_name = os.path.splitext(target.filename)[0].lower()
        if source_name == target_name:
            confidence += 0.3
        elif source_name in target_name or target_name in source_name:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def detect_duplicates(self, video_infos: List[VideoInfo]) -> Dict[str, List[VideoInfo]]:
        """
        检测重复文件
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            Dict[str, List[VideoInfo]]: 按指纹分组的重复文件
        """
        fingerprint_groups: Dict[str, List[VideoInfo]] = {}
        
        for video_info in video_infos:
            if not video_info.file_fingerprint:
                video_info.file_fingerprint = self.generate_fingerprint(video_info)
            
            fp = video_info.file_fingerprint
            if fp not in fingerprint_groups:
                fingerprint_groups[fp] = []
            fingerprint_groups[fp].append(video_info)
        
        # 只返回有重复的组
        return {fp: videos for fp, videos in fingerprint_groups.items() if len(videos) > 1}
    
    def detect_collisions(self, fingerprints: List[str]) -> List[Tuple[str, int]]:
        """
        检测指纹碰撞
        
        Args:
            fingerprints: 指纹列表
            
        Returns:
            List[Tuple[str, int]]: 碰撞的指纹和出现次数
        """
        fingerprint_counts: Dict[str, int] = {}
        
        for fp in fingerprints:
            fingerprint_counts[fp] = fingerprint_counts.get(fp, 0) + 1
        
        collisions = [(fp, count) for fp, count in fingerprint_counts.items() if count > 1]
        self.collision_count = len(collisions)
        
        return collisions
    
    def get_fingerprint_statistics(self, video_infos: List[VideoInfo]) -> Dict[str, any]:
        """
        获取指纹统计信息
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            Dict: 统计信息
        """
        fingerprints = []
        missing_fingerprints = 0
        
        for video_info in video_infos:
            if video_info.file_fingerprint:
                fingerprints.append(video_info.file_fingerprint)
            else:
                missing_fingerprints += 1
        
        unique_fingerprints = len(set(fingerprints))
        collisions = self.detect_collisions(fingerprints)
        
        return {
            'total_files': len(video_infos),
            'files_with_fingerprints': len(fingerprints),
            'missing_fingerprints': missing_fingerprints,
            'unique_fingerprints': unique_fingerprints,
            'collision_groups': len(collisions),
            'total_collisions': sum(count for _, count in collisions),
            'collision_rate': len(collisions) / unique_fingerprints if unique_fingerprints > 0 else 0
        }
    
    def batch_generate_fingerprints(self, video_infos: List[VideoInfo]) -> Dict[str, str]:
        """
        批量生成指纹
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            Dict[str, str]: 文件路径到指纹的映射
        """
        fingerprints = {}
        
        for video_info in video_infos:
            fingerprint = self.generate_fingerprint(video_info)
            fingerprints[video_info.file_path] = fingerprint
            video_info.file_fingerprint = fingerprint
        
        return fingerprints
    
    def clear_cache(self):
        """清空指纹缓存"""
        self.fingerprint_cache.clear()
        self.collision_count = 0
    
    def get_cache_size(self) -> int:
        """获取缓存大小"""
        return len(self.fingerprint_cache)