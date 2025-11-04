"""
增强视频扫描器

集成智能合并、指纹管理、状态管理等功能的完整扫描解决方案
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

try:
    from .scanner import VideoFileScanner
    from .metadata import VideoMetadataExtractor, VideoInfo
    from .sqlite_storage import SQLiteStorage
    from .smart_merge_manager import SmartMergeManager
    from .fingerprint_manager import FingerprintManager
    from .file_status_manager import FileStatusManager, FileStatus
except ImportError:
    from scanner import VideoFileScanner
    from metadata import VideoMetadataExtractor, VideoInfo
    from sqlite_storage import SQLiteStorage
    from smart_merge_manager import SmartMergeManager
    from fingerprint_manager import FingerprintManager
    from file_status_manager import FileStatusManager, FileStatus


class EnhancedVideoScanner:
    """增强视频扫描器"""
    
    def __init__(self, storage: SQLiteStorage, extensions: List[str] = None):
        """
        初始化增强扫描器
        
        Args:
            storage: 数据库存储对象
            extensions: 支持的视频文件扩展名列表
        """
        self.storage = storage
        self.file_scanner = VideoFileScanner(extensions)
        self.metadata_extractor = VideoMetadataExtractor()
        self.merge_manager = SmartMergeManager(storage)
        self.fingerprint_manager = FingerprintManager()
        self.status_manager = FileStatusManager()
        
        # 扫描统计
        self.scan_stats = {
            'files_found': 0,
            'files_processed': 0,
            'files_skipped': 0,
            'errors': 0,
            'processing_time': 0.0
        }
    
    def full_scan(self, directory_path: str, recursive: bool = True, 
                  update_existing: bool = True, 
                  check_missing: bool = True) -> Dict[str, any]:
        """
        执行完整扫描
        
        Args:
            directory_path: 扫描目录路径
            recursive: 是否递归扫描
            update_existing: 是否更新现有记录
            check_missing: 是否检查丢失文件
            
        Returns:
            Dict: 扫描结果报告
        """
        start_time = datetime.now()
        
        # 1. 记录扫描开始 (先用占位符，稍后更新)
        scan_id = None
        
        try:
            # 2. 扫描文件
            print(f"开始扫描目录: {directory_path}")
            video_files = self.file_scanner.scan_directory(directory_path, recursive)
            self.scan_stats['files_found'] = len(video_files)
            print(f"发现 {len(video_files)} 个视频文件")
            
            # 3. 提取元数据
            print("提取视频元数据...")
            new_videos = self._extract_metadata_batch(video_files)
            self.scan_stats['files_processed'] = len(new_videos)
            
            # 4. 获取现有视频记录
            existing_videos = []
            if update_existing or check_missing:
                print("加载现有视频记录...")
                existing_videos = self._load_existing_videos()
            
            # 5. 分析合并策略
            print("分析合并策略...")
            merge_results = self.merge_manager.analyze_merge_candidates(
                new_videos, existing_videos
            )
            
            # 6. 执行合并
            print("执行智能合并...")
            merge_stats = self.merge_manager.execute_merge_plan(merge_results, scan_id)
            
            # 7. 更新扫描统计
            end_time = datetime.now()
            self.scan_stats['processing_time'] = (end_time - start_time).total_seconds()
            
            # 7.5. 记录扫描历史
            scan_id = self.storage.add_scan_history(
                directory_path, 
                self.scan_stats['files_found'], 
                self.scan_stats['files_processed']
            )
            
            # 8. 生成报告
            report = self._generate_scan_report(
                scan_id, merge_results, merge_stats, start_time, end_time
            )
            
            print(f"扫描完成! 处理时间: {self.scan_stats['processing_time']:.2f}秒")
            return report
            
        except Exception as e:
            print(f"扫描过程中发生错误: {e}")
            self.scan_stats['errors'] += 1
            raise
    
    def incremental_scan(self, directory_path: str, 
                        last_scan_time: Optional[datetime] = None) -> Dict[str, any]:
        """
        增量扫描（只处理新增或修改的文件）
        
        Args:
            directory_path: 扫描目录路径
            last_scan_time: 上次扫描时间
            
        Returns:
            Dict: 扫描结果报告
        """
        if last_scan_time is None:
            # 如果没有指定时间，获取最后一次扫描时间
            last_scan_time = self._get_last_scan_time(directory_path)
        
        print(f"执行增量扫描，基准时间: {last_scan_time}")
        
        # 扫描所有文件
        all_files = self.file_scanner.scan_directory(directory_path, True)
        
        # 过滤出新增或修改的文件
        changed_files = []
        for file_path in all_files:
            try:
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_mtime > last_scan_time:
                    changed_files.append(file_path)
            except OSError:
                # 如果无法获取修改时间，包含在扫描中
                changed_files.append(file_path)
        
        print(f"发现 {len(changed_files)} 个变更文件")
        
        if not changed_files:
            return {
                'scan_type': 'incremental',
                'files_changed': 0,
                'message': 'No changes detected'
            }
        
        # 对变更文件执行完整扫描流程
        return self._process_file_list(changed_files, 'incremental')
    
    def verify_scan(self, check_integrity: bool = True) -> Dict[str, any]:
        """
        验证扫描（检查数据库记录与实际文件的一致性）
        
        Args:
            check_integrity: 是否检查文件完整性
            
        Returns:
            Dict: 验证结果报告
        """
        print("开始验证扫描...")
        
        # 获取所有数据库记录
        existing_videos = self._load_existing_videos()
        
        # 检查文件状态
        status_results = self.status_manager.batch_check_status(existing_videos)
        
        # 检测状态不一致
        inconsistencies = self.status_manager.detect_status_inconsistencies(existing_videos)
        
        # 自动修复不一致
        fix_results = self.status_manager.auto_fix_inconsistencies(existing_videos)
        
        report = {
            'scan_type': 'verify',
            'timestamp': datetime.now().isoformat(),
            'total_records': len(existing_videos),
            'status_check': status_results,
            'inconsistencies': len(inconsistencies),
            'auto_fixed': fix_results,
            'details': {
                'missing_files': [v.file_path for v in self.status_manager.get_missing_files(existing_videos)],
                'ignored_files': [v.file_path for v in self.status_manager.get_ignored_files(existing_videos)]
            }
        }
        
        if check_integrity:
            print("检查文件完整性...")
            integrity_results = self._check_file_integrity(existing_videos)
            report['integrity_check'] = integrity_results
        
        return report
    
    def _extract_metadata_batch(self, file_paths: List[str]) -> List[VideoInfo]:
        """批量提取元数据"""
        videos = []
        
        for i, file_path in enumerate(file_paths):
            try:
                print(f"处理文件 {i+1}/{len(file_paths)}: {os.path.basename(file_path)}")
                video_info = self.metadata_extractor.extract_metadata(file_path)
                if video_info:
                    videos.append(video_info)
                else:
                    self.scan_stats['files_skipped'] += 1
            except Exception as e:
                print(f"处理文件失败 {file_path}: {e}")
                self.scan_stats['errors'] += 1
        
        return videos
    
    def _load_existing_videos(self) -> List[VideoInfo]:
        """加载现有视频记录"""
        try:
            cursor = self.storage.connection.cursor()
            
            # 首先检查表是否存在以及是否有新列
            cursor.execute("PRAGMA table_info(video_info)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # 构建动态查询，只选择存在的列
            base_columns = ['file_path', 'filename', 'width', 'height', 'duration', 
                           'video_codec', 'audio_codec', 'file_size', 'bit_rate', 
                           'frame_rate', 'created_time']
            
            new_columns = ['video_code', 'file_fingerprint', 'file_status', 
                          'last_scan_time', 'last_merge_time']
            
            # 只选择存在的列
            select_columns = []
            for col in base_columns + new_columns:
                if col in columns:
                    select_columns.append(col)
            
            if not select_columns:
                print("video_info表不存在或没有可用列")
                return []
            
            query = f"SELECT {', '.join(select_columns)} FROM video_info"
            cursor.execute(query)
            
            videos = []
            for row in cursor.fetchall():
                video_info = VideoInfo(row[0])  # file_path
                
                # 安全地设置属性
                for i, col in enumerate(select_columns[1:], 1):  # 跳过file_path
                    if i < len(row):
                        setattr(video_info, col, row[i])
                
                # 加载标签
                try:
                    tag_cursor = self.storage.connection.cursor()
                    tag_cursor.execute("SELECT tag FROM video_tags WHERE video_id = (SELECT id FROM video_info WHERE file_path = ?)", (row[0],))
                    video_info.tags = [tag_row[0] for tag_row in tag_cursor.fetchall()]
                except:
                    video_info.tags = []
                
                videos.append(video_info)
            
            return videos
            
        except Exception as e:
            print(f"加载现有视频记录失败: {e}")
            return []
    
    def _get_last_scan_time(self, directory_path: str) -> datetime:
        """获取指定目录的最后扫描时间"""
        try:
            cursor = self.storage.connection.cursor()
            cursor.execute("""
                SELECT MAX(scan_time) FROM scan_history 
                WHERE directory_path = ?
            """, (directory_path,))
            
            result = cursor.fetchone()
            if result and result[0]:
                return datetime.fromisoformat(result[0])
            else:
                # 如果没有扫描历史，返回很早的时间
                return datetime(1970, 1, 1)
                
        except Exception as e:
            print(f"获取最后扫描时间失败: {e}")
            return datetime(1970, 1, 1)
    
    def _process_file_list(self, file_paths: List[str], scan_type: str) -> Dict[str, any]:
        """处理文件列表"""
        start_time = datetime.now()
        
        # 提取元数据
        new_videos = self._extract_metadata_batch(file_paths)
        
        # 获取现有记录
        existing_videos = self._load_existing_videos()
        
        # 分析合并策略
        merge_results = self.merge_manager.analyze_merge_candidates(new_videos, existing_videos)
        
        # 执行合并
        merge_stats = self.merge_manager.execute_merge_plan(merge_results)
        
        end_time = datetime.now()
        
        return {
            'scan_type': scan_type,
            'timestamp': end_time.isoformat(),
            'files_processed': len(new_videos),
            'processing_time': (end_time - start_time).total_seconds(),
            'merge_stats': merge_stats,
            'merge_report': self.merge_manager.create_merge_report(merge_results)
        }
    
    def _check_file_integrity(self, videos: List[VideoInfo]) -> Dict[str, any]:
        """检查文件完整性"""
        integrity_results = {
            'checked': 0,
            'valid': 0,
            'corrupted': 0,
            'inaccessible': 0,
            'corrupted_files': []
        }
        
        for video in videos:
            if video.file_status != FileStatus.PRESENT.value:
                continue
                
            integrity_results['checked'] += 1
            
            try:
                # 简单的完整性检查：尝试读取文件头
                with open(video.file_path, 'rb') as f:
                    header = f.read(1024)  # 读取前1KB
                    if len(header) > 0:
                        integrity_results['valid'] += 1
                    else:
                        integrity_results['corrupted'] += 1
                        integrity_results['corrupted_files'].append(video.file_path)
            except (IOError, OSError):
                integrity_results['inaccessible'] += 1
                integrity_results['corrupted_files'].append(video.file_path)
        
        return integrity_results
    
    def _generate_scan_report(self, scan_id: int, merge_results: Dict, 
                            merge_stats: Dict, start_time: datetime, 
                            end_time: datetime) -> Dict[str, any]:
        """生成扫描报告"""
        return {
            'scan_id': scan_id,
            'scan_type': 'full',
            'timestamp': end_time.isoformat(),
            'directory_scanned': merge_results.get('directory_path', 'Unknown'),
            'duration': (end_time - start_time).total_seconds(),
            'file_statistics': {
                'files_found': self.scan_stats['files_found'],
                'files_processed': self.scan_stats['files_processed'],
                'files_skipped': self.scan_stats['files_skipped'],
                'errors': self.scan_stats['errors']
            },
            'merge_statistics': merge_stats,
            'merge_report': self.merge_manager.create_merge_report(merge_results),
            'performance': {
                'processing_time': self.scan_stats['processing_time'],
                'files_per_second': self.scan_stats['files_processed'] / self.scan_stats['processing_time'] if self.scan_stats['processing_time'] > 0 else 0
            }
        }
    
    def get_scan_statistics(self) -> Dict[str, any]:
        """获取扫描统计信息"""
        return {
            'current_session': self.scan_stats.copy(),
            'merge_manager': self.merge_manager.get_merge_statistics(),
            'fingerprint_manager': self.fingerprint_manager.get_fingerprint_statistics([]),  # 需要传入视频列表
            'status_manager': self.status_manager.get_status_statistics(self._load_existing_videos())
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """清理旧数据"""
        return {
            'merge_history_cleaned': self.storage.cleanup_old_merge_history(days_to_keep),
            'status_history_cleaned': len(self.status_manager.status_change_history)  # 清理状态变更历史
        }