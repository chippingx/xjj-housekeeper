"""
智能合并管理器

实现智能合并行为，包括指纹匹配、路径更新、状态转换逻辑
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set

try:
    from .metadata import VideoInfo
    from .fingerprint_manager import FingerprintManager
    from .file_status_manager import FileStatusManager, FileStatus
    from .sqlite_storage import SQLiteStorage
except ImportError:
    from metadata import VideoInfo
    from fingerprint_manager import FingerprintManager
    from file_status_manager import FileStatusManager, FileStatus
    from sqlite_storage import SQLiteStorage


class MergeAction:
    """合并动作类"""
    
    def __init__(self, action_type: str, video_info: VideoInfo, 
                 target_info: Optional[VideoInfo] = None, reason: str = ""):
        self.action_type = action_type  # insert_new, update_path, mark_missing, duplicate_detection
        self.video_info = video_info
        self.target_info = target_info
        self.reason = reason
        self.timestamp = datetime.now()


class SmartMergeManager:
    """智能合并管理器"""
    
    def __init__(self, storage: SQLiteStorage):
        self.storage = storage
        self.fingerprint_manager = FingerprintManager()
        self.status_manager = FileStatusManager()
        self.merge_actions: List[MergeAction] = []
    
    def analyze_merge_candidates(self, new_videos: List[VideoInfo], 
                               existing_videos: List[VideoInfo]) -> Dict[str, List]:
        """
        分析合并候选项
        
        Args:
            new_videos: 新扫描的视频列表
            existing_videos: 数据库中现有的视频列表
            
        Returns:
            Dict: 分析结果
        """
        results = {
            'insert_new': [],
            'update_path': [],
            'mark_missing': [],
            'mark_replaced': [],  # 新增：标记被替换的文件
            'duplicate_detection': [],
            'conflicts': []
        }
        
        # 创建现有视频的指纹索引
        existing_by_fingerprint = {}
        existing_by_video_code = {}
        existing_by_path = {}
        
        for video in existing_videos:
            if video.file_fingerprint:
                existing_by_fingerprint[video.file_fingerprint] = video
            if video.video_code:
                if video.video_code not in existing_by_video_code:
                    existing_by_video_code[video.video_code] = []
                existing_by_video_code[video.video_code].append(video)
            existing_by_path[video.file_path] = video
        
        # 分析每个新视频
        for new_video in new_videos:
            action = self._determine_merge_action(
                new_video, existing_by_fingerprint, 
                existing_by_video_code, existing_by_path
            )
            
            if action:
                results[action.action_type].append(action)
        
        # 检查现有视频中的丢失文件
        for existing_video in existing_videos:
            if existing_video.file_status != FileStatus.IGNORE.value:
                actual_status = self.status_manager.check_file_status(existing_video.file_path)
                if actual_status == FileStatus.MISSING and existing_video.file_status != FileStatus.MISSING.value:
                    action = MergeAction(
                        'mark_missing', existing_video, 
                        reason=f"File not found during scan: {existing_video.file_path}"
                    )
                    results['mark_missing'].append(action)
        
        return results
    
    def _determine_merge_action(self, new_video: VideoInfo, 
                              existing_by_fingerprint: Dict, 
                              existing_by_video_code: Dict, 
                              existing_by_path: Dict) -> Optional[MergeAction]:
        """
        确定合并动作
        
        Args:
            new_video: 新视频信息
            existing_by_fingerprint: 按指纹索引的现有视频
            existing_by_video_code: 按视频代码索引的现有视频
            existing_by_path: 按路径索引的现有视频
            
        Returns:
            Optional[MergeAction]: 合并动作
        """
        # 1. 检查路径是否已存在
        if new_video.file_path in existing_by_path:
            existing_video = existing_by_path[new_video.file_path]
            # 路径相同，检查是否需要更新其他信息
            if self._should_update_existing(new_video, existing_video):
                return MergeAction(
                    'update_path', new_video, existing_video,
                    reason="Update existing video with new metadata"
                )
            return None  # 无需操作
        
        # 2. 检查指纹匹配（文件移动检测）
        if new_video.file_fingerprint and new_video.file_fingerprint in existing_by_fingerprint:
            existing_video = existing_by_fingerprint[new_video.file_fingerprint]
            if existing_video.file_path != new_video.file_path:
                return MergeAction(
                    'update_path', new_video, existing_video,
                    reason=f"File moved from {existing_video.file_path} to {new_video.file_path}"
                )
        
        # 3. 检查视频代码重复
        if new_video.video_code and new_video.video_code in existing_by_video_code:
            existing_videos = existing_by_video_code[new_video.video_code]
            
            # 检查是否有完全匹配的指纹
            for existing_video in existing_videos:
                if (existing_video.file_fingerprint == new_video.file_fingerprint and 
                    existing_video.file_path != new_video.file_path):
                    return MergeAction(
                        'update_path', new_video, existing_video,
                        reason=f"Same file with video_code {new_video.video_code} moved"
                    )
            
            # 检查是否为文件替换场景
            for existing_video in existing_videos:
                if (existing_video.file_status == FileStatus.PRESENT.value and
                    existing_video.file_fingerprint != new_video.file_fingerprint):
                    # 相同video_code但不同fingerprint，可能是文件替换
                    if self._is_replacement_scenario(new_video, existing_video):
                        # 创建两个动作：标记旧文件为replaced，插入新文件
                        return MergeAction(
                            'mark_replaced', new_video, existing_video,
                            reason=f"File replaced: {existing_video.file_path} -> {new_video.file_path}"
                        )
            
            # 检查是否为重复下载
            for existing_video in existing_videos:
                if existing_video.file_status == FileStatus.PRESENT.value:
                    similarity = self._calculate_similarity(new_video, existing_video)
                    if similarity > 0.8:  # 高相似度阈值
                        return MergeAction(
                            'duplicate_detection', new_video, existing_video,
                            reason=f"Potential duplicate of {existing_video.file_path} (similarity: {similarity:.2f})"
                        )
        
        # 4. 默认为新插入
        return MergeAction(
            'insert_new', new_video,
            reason="New video file detected"
        )
    
    def _should_update_existing(self, new_video: VideoInfo, existing_video: VideoInfo) -> bool:
        """
        判断是否需要更新现有记录
        
        Args:
            new_video: 新视频信息
            existing_video: 现有视频信息
            
        Returns:
            bool: 是否需要更新
        """
        # 检查关键字段是否有变化
        fields_to_check = [
            'file_size', 'duration', 'width', 'height', 
            'video_codec', 'audio_codec', 'bit_rate', 'frame_rate'
        ]
        
        for field in fields_to_check:
            new_value = getattr(new_video, field, None)
            existing_value = getattr(existing_video, field, None)
            if new_value != existing_value and new_value is not None:
                return True
        
        # 检查标签是否有变化
        new_tags = set(new_video.tags or [])
        existing_tags = set(existing_video.tags or [])
        if new_tags != existing_tags:
            return True
        
        return False
    
    def _calculate_similarity(self, video1: VideoInfo, video2: VideoInfo) -> float:
        """
        计算两个视频的相似度
        
        Args:
            video1: 视频1
            video2: 视频2
            
        Returns:
            float: 相似度分数 (0-1)
        """
        score = 0.0
        total_weight = 0.0
        
        # 文件大小相似度 (权重: 0.3)
        if video1.file_size and video2.file_size:
            size_diff = abs(video1.file_size - video2.file_size)
            max_size = max(video1.file_size, video2.file_size)
            size_similarity = 1.0 - (size_diff / max_size) if max_size > 0 else 1.0
            score += size_similarity * 0.3
            total_weight += 0.3
        
        # 时长相似度 (权重: 0.3)
        if video1.duration and video2.duration:
            duration_diff = abs(video1.duration - video2.duration)
            max_duration = max(video1.duration, video2.duration)
            duration_similarity = 1.0 - (duration_diff / max_duration) if max_duration > 0 else 1.0
            score += duration_similarity * 0.3
            total_weight += 0.3
        
        # 分辨率相似度 (权重: 0.2)
        if (video1.width and video1.height and video2.width and video2.height):
            resolution1 = video1.width * video1.height
            resolution2 = video2.width * video2.height
            if resolution1 > 0 and resolution2 > 0:
                resolution_diff = abs(resolution1 - resolution2)
                max_resolution = max(resolution1, resolution2)
                resolution_similarity = 1.0 - (resolution_diff / max_resolution)
                score += resolution_similarity * 0.2
                total_weight += 0.2
        
        # 视频代码相似度 (权重: 0.2)
        if video1.video_code and video2.video_code:
            if video1.video_code == video2.video_code:
                score += 1.0 * 0.2
            total_weight += 0.2
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _is_replacement_scenario(self, new_video: VideoInfo, existing_video: VideoInfo) -> bool:
        """
        判断是否为文件替换场景
        
        Args:
            new_video: 新视频信息
            existing_video: 现有视频信息
            
        Returns:
            bool: 是否为替换场景
        """
        # 必须有相同的video_code
        if not (new_video.video_code and existing_video.video_code and 
                new_video.video_code == existing_video.video_code):
            return False
        
        # 必须有不同的fingerprint
        if (not new_video.file_fingerprint or not existing_video.file_fingerprint or
            new_video.file_fingerprint == existing_video.file_fingerprint):
            return False
        
        # 检查是否有显著的质量差异，表明是升级/替换
        quality_indicators = []
        
        # 文件大小比较
        if new_video.file_size and existing_video.file_size:
            size_ratio = new_video.file_size / existing_video.file_size
            quality_indicators.append(('file_size', size_ratio))
        
        # 分辨率比较
        if (new_video.width and new_video.height and 
            existing_video.width and existing_video.height):
            new_resolution = new_video.width * new_video.height
            existing_resolution = existing_video.width * existing_video.height
            if existing_resolution > 0:
                resolution_ratio = new_resolution / existing_resolution
                quality_indicators.append(('resolution', resolution_ratio))
        
        # 码率比较
        if new_video.bit_rate and existing_video.bit_rate:
            bitrate_ratio = new_video.bit_rate / existing_video.bit_rate
            quality_indicators.append(('bit_rate', bitrate_ratio))
        
        # 如果有任何质量指标显示新文件明显更好（比例 > 1.2）或明显不同（比例 < 0.8 或 > 1.5）
        # 则认为是替换场景
        for indicator, ratio in quality_indicators:
            if ratio > 1.2 or ratio < 0.8:  # 20%以上的差异
                return True
        
        # 如果文件格式不同，也可能是替换
        if (new_video.video_codec and existing_video.video_codec and
            new_video.video_codec != existing_video.video_codec):
            return True
        
        # 如果文件路径在不同目录，可能是下载了新版本
        if new_video.file_path and existing_video.file_path:
            new_dir = os.path.dirname(new_video.file_path)
            existing_dir = os.path.dirname(existing_video.file_path)
            if new_dir != existing_dir:
                return True
        
        return False
    
    def execute_merge_plan(self, merge_results: Dict[str, List], 
                          scan_id: Optional[int] = None) -> Dict[str, int]:
        """
        执行合并计划
        
        Args:
            merge_results: 合并分析结果
            scan_id: 扫描ID
            
        Returns:
            Dict[str, int]: 执行统计
        """
        stats = {
            'inserted': 0,
            'updated': 0,
            'marked_missing': 0,
            'marked_replaced': 0,
            'duplicates_detected': 0,
            'errors': 0
        }
        
        # 执行新插入
        for action in merge_results.get('insert_new', []):
            try:
                video_id = self.storage.insert_video_info(action.video_info)
                if video_id:
                    # 更新master list
                    self._update_master_list(action.video_info, 'insert_new')
                    # 记录merge history
                    if scan_id:
                        self.storage.add_merge_event(
                            'insert_new', 
                            action.video_info.video_code,  # 传递正确的video_code
                            None,  # old_path
                            action.video_info.file_path,  # new_path
                            None,  # details
                            scan_id  # scan_session_id
                        )
                    stats['inserted'] += 1
            except Exception as e:
                print(f"Error inserting video {action.video_info.file_path}: {e}")
                stats['errors'] += 1
        
        # 执行路径更新
        for action in merge_results.get('update_path', []):
            try:
                # 更新现有记录
                self._update_existing_video(action.target_info, action.video_info)
                # 持久化到数据库
                if hasattr(action.target_info, 'id') and action.target_info.id:
                    update_data = {
                        'filename': action.target_info.filename,
                        'file_size': action.target_info.file_size,
                        'duration': action.target_info.duration,
                        'width': action.target_info.width,
                        'height': action.target_info.height,
                        'video_codec': action.target_info.video_codec,
                        'audio_codec': action.target_info.audio_codec,
                        'bit_rate': action.target_info.bit_rate,
                        'frame_rate': action.target_info.frame_rate,
                        'file_status': action.target_info.file_status,
                        'logical_path': action.target_info.logical_path
                    }
                    self.storage.update_video_info(action.target_info.id, update_data)
                # 记录merge history
                if scan_id:
                    self.storage.add_merge_event(
                        'update_path',
                        action.target_info.video_code,  # video_code
                        action.target_info.file_path,   # old_path
                        action.video_info.file_path,    # new_path
                        None,  # details
                        scan_id  # scan_session_id
                    )
                stats['updated'] += 1
            except Exception as e:
                print(f"Error updating video {action.video_info.file_path}: {e}")
                stats['errors'] += 1
        
        # 标记丢失文件
        for action in merge_results.get('mark_missing', []):
            try:
                self.status_manager.update_video_status(
                    action.video_info, FileStatus.MISSING, action.reason
                )
                # 持久化到数据库
                if hasattr(action.video_info, 'id') and action.video_info.id:
                    update_data = {'file_status': action.video_info.file_status}
                    self.storage.update_video_info(action.video_info.id, update_data)
                # 记录merge history
                if scan_id:
                    self.storage.add_merge_event(
                        'mark_missing',
                        action.video_info.video_code,  # video_code
                        action.video_info.file_path,   # old_path
                        None,  # new_path
                        None,  # details
                        scan_id  # scan_session_id
                    )
                stats['marked_missing'] += 1
            except Exception as e:
                print(f"Error marking video as missing {action.video_info.file_path}: {e}")
                stats['errors'] += 1
        
        # 标记被替换文件
        for action in merge_results.get('mark_replaced', []):
            try:
                # 标记旧文件为REPLACED状态
                self.status_manager.update_video_status(
                    action.target_info, FileStatus.REPLACED, action.reason
                )
                # 持久化到数据库
                if hasattr(action.target_info, 'id') and action.target_info.id:
                    update_data = {'file_status': action.target_info.file_status}
                    self.storage.update_video_info(action.target_info.id, update_data)
                # 插入新文件
                video_id = self.storage.insert_video_info(action.video_info)
                if video_id:
                    # 更新master list（新文件）
                    self._update_master_list(action.video_info, 'insert_new')
                    # 更新master list计数（考虑被替换的文件）
                    self._update_master_list(action.target_info, 'mark_replaced')
                    # 记录merge history
                    if scan_id:
                        self.storage.add_merge_event(
                            'mark_replaced',
                            action.target_info.video_code,  # video_code
                            action.target_info.file_path,   # old_path
                            action.video_info.file_path,    # new_path
                            None,  # details
                            scan_id  # scan_session_id
                        )
                stats['marked_replaced'] += 1
            except Exception as e:
                print(f"Error marking video as replaced {action.target_info.file_path}: {e}")
                stats['errors'] += 1
        
        # 处理重复检测
        for action in merge_results.get('duplicate_detection', []):
            try:
                # 这里可以根据策略决定如何处理重复文件
                # 例如：标记为重复、移动到特定目录、或者询问用户
                print(f"Duplicate detected: {action.video_info.file_path} vs {action.target_info.file_path}")
                stats['duplicates_detected'] += 1
            except Exception as e:
                print(f"Error handling duplicate {action.video_info.file_path}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def _update_master_list(self, video_info: VideoInfo, event_type: str):
        """更新master list"""
        if video_info.video_code:
            if event_type == 'mark_replaced':
                # 对于替换事件，重新计算该video_code的文件计数
                self.storage.update_master_list_file_count(video_info.video_code)
            else:
                # 对于其他事件，使用原有的upsert逻辑
                self.storage.upsert_master_list_entry(
                    video_info.video_code,
                    video_info.file_fingerprint
                )
    
    def _update_existing_video(self, existing_video: VideoInfo, new_video: VideoInfo):
        """更新现有视频记录"""
        # 更新路径和其他可能变化的字段
        existing_video.file_path = new_video.file_path
        existing_video.file_size = new_video.file_size or existing_video.file_size
        existing_video.duration = new_video.duration or existing_video.duration
        existing_video.width = new_video.width or existing_video.width
        existing_video.height = new_video.height or existing_video.height
        existing_video.video_codec = new_video.video_codec or existing_video.video_codec
        existing_video.audio_codec = new_video.audio_codec or existing_video.audio_codec
        existing_video.bit_rate = new_video.bit_rate or existing_video.bit_rate
        existing_video.frame_rate = new_video.frame_rate or existing_video.frame_rate
        existing_video.file_status = FileStatus.PRESENT.value
        existing_video.last_scan_time = datetime.now().isoformat()
        
        # 合并标签
        if new_video.tags:
            existing_tags = set(existing_video.tags or [])
            new_tags = set(new_video.tags)
            existing_video.tags = list(existing_tags.union(new_tags))
    
    def create_merge_report(self, merge_results: Dict[str, List]) -> Dict[str, any]:
        """
        创建合并报告
        
        Args:
            merge_results: 合并分析结果
            
        Returns:
            Dict: 合并报告
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_actions': sum(len(actions) for actions in merge_results.values()),
                'insert_new': len(merge_results.get('insert_new', [])),
                'update_path': len(merge_results.get('update_path', [])),
                'mark_missing': len(merge_results.get('mark_missing', [])),
                'duplicate_detection': len(merge_results.get('duplicate_detection', [])),
                'conflicts': len(merge_results.get('conflicts', []))
            },
            'details': {}
        }
        
        # 详细信息
        for action_type, actions in merge_results.items():
            report['details'][action_type] = []
            for action in actions:
                action_detail = {
                    'file_path': action.video_info.file_path,
                    'video_code': action.video_info.video_code,
                    'reason': action.reason,
                    'timestamp': action.timestamp.isoformat()
                }
                if action.target_info:
                    action_detail['target_path'] = action.target_info.file_path
                report['details'][action_type].append(action_detail)
        
        return report
    
    def get_merge_statistics(self) -> Dict[str, any]:
        """获取合并统计信息"""
        return {
            'total_actions_performed': len(self.merge_actions),
            'actions_by_type': self._count_actions_by_type(),
            'recent_actions': [
                {
                    'action_type': action.action_type,
                    'file_path': action.video_info.file_path,
                    'reason': action.reason,
                    'timestamp': action.timestamp.isoformat()
                }
                for action in self.merge_actions[-10:]  # 最近10个动作
            ]
        }
    
    def _count_actions_by_type(self) -> Dict[str, int]:
        """按类型统计动作数量"""
        counts = {}
        for action in self.merge_actions:
            counts[action.action_type] = counts.get(action.action_type, 0) + 1
        return counts