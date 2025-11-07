from __future__ import annotations
from typing import List, Dict, Optional
import os
import sys
from pathlib import Path

# 添加tools目录到路径，以便导入video_info_collector模块
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from tools.video_info_collector.sqlite_storage import SQLiteStorage
    from tools.video_info_collector.enhanced_scanner import EnhancedVideoScanner
    from tools.video_info_collector.smart_merge_manager import SmartMergeManager
    from tools.video_info_collector.cli import get_default_paths
    from tools.video_info_collector.error_handler import ErrorHandler
    
    # 获取默认数据库路径
    default_paths = get_default_paths()
    DEFAULT_DB_PATH = default_paths['default_database']
    
    # 确保数据库目录存在
    db_dir = Path(DEFAULT_DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
except ImportError as e:
    print(f"导入错误: {e}")
    # 如果导入失败，使用简化版本
    class ErrorHandler:
        """简化错误处理器"""
        def handle_database_error(self, message: str, db_path: str = None, operation: str = None):
            print(f"数据库错误: {message}")
        
        def handle_generic_error(self, error: Exception, context: str = ""):
            print(f"错误[{context}]: {error}")
    
    DEFAULT_DB_PATH = "output/video_info_collector/database/video_database.db"
    
    # 确保目录存在
    db_dir = Path(DEFAULT_DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)


class VideoService:
    """视频数据服务类"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.storage = None
        self.scanner = None
        self.merge_manager = None
        self.error_handler = ErrorHandler()
        
    def _ensure_storage(self):
        """确保存储连接已初始化"""
        if self.storage is None:
            # 确保数据库目录存在
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            self.storage = SQLiteStorage(self.db_path)
            self.merge_manager = SmartMergeManager(self.storage)
    
    def search_videos(self, keyword: str) -> List[Dict[str, str]]:
        """搜索视频"""
        # 空字符串检查放在try块外面，这样异常不会被捕获
        if not isinstance(keyword, str) or keyword.strip() == "":
            raise ValueError("keyword must be non-empty and exact")
        
        try:
            self._ensure_storage()
            
            # 精确匹配视频编号
            cursor = self.storage.connection.cursor()
            cursor.execute(
                """
                SELECT filename, file_path, file_size, duration_formatted, resolution 
                FROM video_info 
                WHERE filename = ? OR file_path = ?
                LIMIT 100
                """,
                (keyword, keyword)
            )
            
            results = []
            for row in cursor.fetchall():
                # 格式化文件大小
                file_size_bytes = row['file_size']
                if file_size_bytes:
                    file_size_gb = file_size_bytes / (1024 * 1024 * 1024)
                    if file_size_gb >= 1:
                        file_size_formatted = f"{file_size_gb:.2f}G"
                    else:
                        file_size_mb = file_size_bytes / (1024 * 1024)
                        file_size_formatted = f"{file_size_mb:.0f}M"
                else:
                    file_size_formatted = "未知"
                
                results.append({
                    'filename': row['filename'],
                    'file_path': row['file_path'],
                    'file_size': file_size_formatted,
                    'duration': row['duration_formatted'],
                    'resolution': row['resolution']
                })
            
            return results
            
        except Exception as e:
            self.error_handler.handle_database_error(f"搜索视频失败: {e}", self.db_path, "search")
            return []
    
    def start_maintain(self, path: str, labels: Optional[str] = None, logical_path: Optional[str] = None) -> Dict[str, any]:
        """开始维护视频数据"""
        try:
            self._ensure_storage()
            
            if not path or not path.strip():
                return {
                    'success': False,
                    'message': '请提供有效的扫描路径'
                }
            
            # 验证路径存在
            if not os.path.exists(path):
                return {
                    'success': False,
                    'message': f'路径不存在: {path}'
                }
            
            # 使用enhanced_scanner扫描视频文件，需要传入storage参数
            scanner = EnhancedVideoScanner(self.storage)
            
            # 使用full_scan方法扫描视频文件
            scan_result = scanner.full_scan(
                path, 
                recursive=True
            )
            
            # 检查扫描结果
            if not scan_result:
                return {
                    'success': False,
                    'message': f'扫描失败：未知错误'
                }
            
            # 兼容不同扫描报告结构：优先使用嵌套的 file_statistics
            stats = scan_result.get('file_statistics', {}) if isinstance(scan_result, dict) else {}
            files_found = stats.get('files_found', scan_result.get('files_found', 0))
            files_processed = stats.get('files_processed', scan_result.get('files_processed', 0))
            files_skipped = stats.get('files_skipped', scan_result.get('files_skipped', 0))
            errors = stats.get('errors', scan_result.get('errors', 0))
            
            # 如果找到了文件但都没有处理成功
            if files_found > 0 and files_processed == 0:
                if errors > 0:
                    return {
                        'success': False,
                        'message': f'找到 {files_found} 个视频文件，但处理时发生 {errors} 个错误。请检查文件是否损坏。'
                    }
                else:
                    return {
                        'success': False,
                        'message': f'找到 {files_found} 个视频文件，但都无法提取元数据（可能文件格式不支持）'
                    }
            
            # 如果根本没找到视频文件：视为成功的空结果，不再作为错误提示
            if files_found == 0:
                return {
                    'success': True,
                    'message': (
                        f'扫描完成：未发现可维护的视频文件（可能已全部处理或路径为空）。\n'
                        f'路径: {path}'
                    ),
                    'processed_count': 0,
                    'total_files': 0,
                    'files_skipped': 0,
                    'errors': 0
                }
            
            # 构建详细的成功消息
            message_parts = []
            if files_processed > 0:
                message_parts.append(f'成功处理 {files_processed} 个视频文件')
            if files_skipped > 0:
                message_parts.append(f'跳过 {files_skipped} 个文件')
            if errors > 0:
                message_parts.append(f'遇到 {errors} 个错误')
            
            message = ' | '.join(message_parts)
            
            return {
                'success': True,
                'message': message,
                'processed_count': files_processed,
                'total_files': files_found,
                'files_skipped': files_skipped,
                'errors': errors
            }
            
        except Exception as e:
            error_msg = f"维护操作失败: {e}"
            self.error_handler.handle_generic_error(e, error_msg)
            return {
                'success': False,
                'message': error_msg
            }


# 创建全局服务实例
video_service = VideoService()


def search_videos(keyword: str) -> List[Dict[str, str]]:
    """搜索视频 - 兼容性包装函数"""
    return video_service.search_videos(keyword)


def start_maintain(path: str, labels: Optional[str] = None, logical_path: Optional[str] = None) -> Dict[str, any]:
    """开始维护视频数据 - 兼容性包装函数"""
    return video_service.start_maintain(path, labels, logical_path)
