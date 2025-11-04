"""
文件状态管理器

管理三状态文件状态系统：present/missing/ignore
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Set
from enum import Enum

try:
    from .metadata import VideoInfo
except ImportError:
    from metadata import VideoInfo


class FileStatus(Enum):
    """文件状态枚举"""
    PRESENT = "present"    # 文件存在且可访问
    MISSING = "missing"    # 文件丢失或不可访问
    IGNORE = "ignore"      # 在其它目录下新发现同指纹文件，标记为忽略
    REPLACED = "replaced"  # 文件已被同video_code的新版本替换


class FileStatusManager:
    """文件状态管理器"""
    
    def __init__(self):
        self.status_change_history: List[Dict] = []
    
    def check_file_status(self, file_path: str) -> FileStatus:
        """
        检查文件的实际状态
        
        Args:
            file_path: 文件路径
            
        Returns:
            FileStatus: 文件状态
        """
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                # 尝试访问文件以确保可读
                with open(file_path, 'rb') as f:
                    f.read(1)
                return FileStatus.PRESENT
            except (PermissionError, IOError):
                return FileStatus.MISSING
        else:
            return FileStatus.MISSING
    
    def update_video_status(self, video_info: VideoInfo, new_status: FileStatus, 
                          reason: Optional[str] = None) -> bool:
        """
        更新视频文件状态
        
        Args:
            video_info: 视频信息对象
            new_status: 新状态
            reason: 状态变更原因
            
        Returns:
            bool: 是否成功更新
        """
        old_status = video_info.file_status
        video_info.file_status = new_status.value
        
        # 记录状态变更历史
        self.status_change_history.append({
            'file_path': video_info.file_path,
            'old_status': old_status,
            'new_status': new_status.value,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        return True
    
    def batch_check_status(self, video_infos: List[VideoInfo]) -> Dict[str, Dict]:
        """
        批量检查文件状态
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            Dict: 状态检查结果
        """
        results = {
            'checked': 0,
            'present': 0,
            'missing': 0,
            'ignore': 0,
            'status_changes': []
        }
        
        for video_info in video_infos:
            results['checked'] += 1
            
            # 如果当前状态是ignore，跳过检查
            if video_info.file_status == FileStatus.IGNORE.value:
                results['ignore'] += 1
                continue
            
            # 检查实际状态
            actual_status = self.check_file_status(video_info.file_path)
            old_status = video_info.file_status
            
            # 更新状态
            if actual_status.value != old_status:
                self.update_video_status(video_info, actual_status, "batch_check")
                results['status_changes'].append({
                    'file_path': video_info.file_path,
                    'old_status': old_status,
                    'new_status': actual_status.value
                })
            
            # 统计
            if actual_status == FileStatus.PRESENT:
                results['present'] += 1
            elif actual_status == FileStatus.MISSING:
                results['missing'] += 1
        
        return results
    
    def mark_as_ignore(self, video_infos: List[VideoInfo], reason: str = "user_request") -> int:
        """
        批量标记文件为忽略状态
        
        Args:
            video_infos: 视频信息列表
            reason: 忽略原因
            
        Returns:
            int: 成功标记的文件数量
        """
        count = 0
        for video_info in video_infos:
            if video_info.file_status != FileStatus.IGNORE.value:
                self.update_video_status(video_info, FileStatus.IGNORE, reason)
                count += 1
        return count
    
    def unmark_ignore(self, video_infos: List[VideoInfo]) -> int:
        """
        取消忽略标记，恢复到实际状态
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            int: 成功取消标记的文件数量
        """
        count = 0
        for video_info in video_infos:
            if video_info.file_status == FileStatus.IGNORE.value:
                actual_status = self.check_file_status(video_info.file_path)
                self.update_video_status(video_info, actual_status, "unmark_ignore")
                count += 1
        return count
    
    def get_files_by_status(self, video_infos: List[VideoInfo], 
                           status: FileStatus) -> List[VideoInfo]:
        """
        根据状态筛选文件
        
        Args:
            video_infos: 视频信息列表
            status: 要筛选的状态
            
        Returns:
            List[VideoInfo]: 符合状态的文件列表
        """
        return [v for v in video_infos if v.file_status == status.value]
    
    def get_missing_files(self, video_infos: List[VideoInfo]) -> List[VideoInfo]:
        """获取丢失的文件"""
        return self.get_files_by_status(video_infos, FileStatus.MISSING)
    
    def get_present_files(self, video_infos: List[VideoInfo]) -> List[VideoInfo]:
        """获取存在的文件"""
        return self.get_files_by_status(video_infos, FileStatus.PRESENT)
    
    def get_ignored_files(self, video_infos: List[VideoInfo]) -> List[VideoInfo]:
        """获取被忽略的文件"""
        return self.get_files_by_status(video_infos, FileStatus.IGNORE)
    
    def get_status_statistics(self, video_infos: List[VideoInfo]) -> Dict[str, any]:
        """
        获取状态统计信息
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            Dict: 统计信息
        """
        stats = {
            'total': len(video_infos),
            'present': 0,
            'missing': 0,
            'ignore': 0,
            'unknown': 0
        }
        
        for video_info in video_infos:
            status = video_info.file_status
            if status == FileStatus.PRESENT.value:
                stats['present'] += 1
            elif status == FileStatus.MISSING.value:
                stats['missing'] += 1
            elif status == FileStatus.IGNORE.value:
                stats['ignore'] += 1
            else:
                stats['unknown'] += 1
        
        # 计算百分比
        if stats['total'] > 0:
            for key in ['present', 'missing', 'ignore', 'unknown']:
                stats[f'{key}_percentage'] = (stats[key] / stats['total']) * 100
        
        return stats
    
    def detect_status_inconsistencies(self, video_infos: List[VideoInfo]) -> List[Dict]:
        """
        检测状态不一致的文件
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            List[Dict]: 不一致的文件信息
        """
        inconsistencies = []
        
        for video_info in video_infos:
            # 跳过被忽略的文件
            if video_info.file_status == FileStatus.IGNORE.value:
                continue
            
            actual_status = self.check_file_status(video_info.file_path)
            recorded_status = video_info.file_status
            
            if actual_status.value != recorded_status:
                inconsistencies.append({
                    'file_path': video_info.file_path,
                    'recorded_status': recorded_status,
                    'actual_status': actual_status.value,
                    'video_code': video_info.video_code,
                    'file_size': video_info.file_size
                })
        
        return inconsistencies
    
    def auto_fix_inconsistencies(self, video_infos: List[VideoInfo]) -> Dict[str, int]:
        """
        自动修复状态不一致
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            Dict[str, int]: 修复统计
        """
        inconsistencies = self.detect_status_inconsistencies(video_infos)
        
        fixed_count = 0
        for inconsistency in inconsistencies:
            # 找到对应的video_info对象
            for video_info in video_infos:
                if video_info.file_path == inconsistency['file_path']:
                    actual_status = FileStatus(inconsistency['actual_status'])
                    self.update_video_status(video_info, actual_status, "auto_fix")
                    fixed_count += 1
                    break
        
        return {
            'inconsistencies_found': len(inconsistencies),
            'fixed_count': fixed_count
        }
    
    def get_status_change_history(self, file_path: Optional[str] = None, 
                                 limit: int = 100) -> List[Dict]:
        """
        获取状态变更历史
        
        Args:
            file_path: 特定文件路径（可选）
            limit: 返回记录数限制
            
        Returns:
            List[Dict]: 状态变更历史
        """
        history = self.status_change_history
        
        if file_path:
            history = [h for h in history if h['file_path'] == file_path]
        
        # 按时间倒序排列，返回最新的记录
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        return history[:limit]
    
    def clear_history(self):
        """清空状态变更历史"""
        self.status_change_history.clear()
    
    def export_status_report(self, video_infos: List[VideoInfo]) -> Dict[str, any]:
        """
        导出状态报告
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            Dict: 完整的状态报告
        """
        stats = self.get_status_statistics(video_infos)
        inconsistencies = self.detect_status_inconsistencies(video_infos)
        
        return {
            'report_time': datetime.now().isoformat(),
            'statistics': stats,
            'inconsistencies': inconsistencies,
            'missing_files': [v.file_path for v in self.get_missing_files(video_infos)],
            'ignored_files': [v.file_path for v in self.get_ignored_files(video_infos)],
            'recent_changes': self.get_status_change_history(limit=50)
        }