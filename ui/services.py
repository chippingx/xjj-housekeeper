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
        """搜索视频（支持按视频码和标签模糊匹配，输入即搜）。"""
        try:
            self._ensure_storage()

            # 空或非法输入直接返回空结果，便于“输入即搜”体验
            if not isinstance(keyword, str):
                return []

            search_term = keyword.strip()
            if search_term == "":
                return []

            cursor = self.storage.connection.cursor()
            # 检查列是否存在，避免早期库缺少video_code导致查询失败
            cursor.execute("PRAGMA table_info(video_info)")
            columns = [col[1] for col in cursor.fetchall()]

            # 检查是否存在标签表，避免早期库报错
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='video_tags'"
            )
            has_video_tags = cursor.fetchone() is not None

            like_keyword = f"%{search_term}%"

            if 'video_code' in columns:
                if has_video_tags:
                    # 优先按视频码匹配，同时支持按标签关键字匹配
                    cursor.execute(
                        """
                        SELECT id, video_code, filename, file_path, file_size, duration_formatted, resolution
                        FROM video_info
                        WHERE video_code LIKE ?
                           OR id IN (
                                SELECT video_id
                                FROM video_tags
                                WHERE tag LIKE ?
                           )
                        ORDER BY updated_time DESC
                        LIMIT 100
                        """,
                        (like_keyword, like_keyword),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, video_code, filename, file_path, file_size, duration_formatted, resolution
                        FROM video_info
                        WHERE video_code LIKE ?
                        ORDER BY updated_time DESC
                        LIMIT 100
                        """,
                        (like_keyword,),
                    )
            else:
                if has_video_tags:
                    cursor.execute(
                        """
                        SELECT id, NULL AS video_code, filename, file_path, file_size, duration_formatted, resolution
                        FROM video_info
                        WHERE filename LIKE ?
                           OR file_path LIKE ?
                           OR id IN (
                                SELECT video_id
                                FROM video_tags
                                WHERE tag LIKE ?
                           )
                        ORDER BY updated_time DESC
                        LIMIT 100
                        """,
                        (like_keyword, like_keyword, like_keyword),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, NULL AS video_code, filename, file_path, file_size, duration_formatted, resolution
                        FROM video_info
                        WHERE filename LIKE ? OR file_path LIKE ?
                        ORDER BY updated_time DESC
                        LIMIT 100
                        """,
                        (like_keyword, like_keyword),
                    )

            return self._rows_to_results(cursor.fetchall())

        except Exception as e:
            self.error_handler.handle_database_error(
                f"搜索视频失败: {e}", self.db_path, "search"
            )
            return []

    def _rows_to_results(self, rows) -> List[Dict[str, str]]:
        """将数据库行转换为统一的 UI 结果结构。"""
        results: List[Dict[str, str]] = []
        for row in rows:
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

            # 统一 UI 字段：首列展示视频码，缺失时回退文件名
            video_label = row['video_code'] if row['video_code'] else row['filename']

            # 聚合标签信息（video_tags 多对多关系）
            tags_label = ""
            try:
                video_id = row.get('id') if isinstance(row, dict) else row['id']
            except Exception:
                video_id = None
            try:
                if video_id is not None and hasattr(self.storage, 'get_video_tags'):
                    tags = self.storage.get_video_tags(video_id) or []
                    if tags:
                        tags_label = ", ".join(t.strip() for t in tags if t and t.strip())
            except Exception:
                tags_label = ""

            results.append({
                'video': video_label,
                'tags': tags_label,
                'file_path': row['file_path'],
                'file_size': file_size_formatted,
                'duration': row['duration_formatted'],
                'resolution': row['resolution']
            })
        return results

    def random_videos(self, limit: int = 20, ensure_accessible: bool = True) -> List[Dict[str, str]]:
        """随机挑选若干视频，优先返回路径可访问的视频。

        ensure_accessible 为 True 时，会从更大的候选集合中过滤掉不存在的路径。
        """
        try:
            self._ensure_storage()
            cursor = self.storage.connection.cursor()

            # 为了提高可访问路径的命中率，多取一些候选再做过滤
            candidate_limit = max(limit * 5, limit)
            cursor.execute(
                """
                SELECT id, video_code, filename, file_path, file_size, duration_formatted, resolution
                FROM video_info
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (candidate_limit,),
            )

            rows = cursor.fetchall()
            if not ensure_accessible:
                return self._rows_to_results(rows)[:limit]

            # 过滤掉 file_path 不存在的记录
            filtered = []
            for row in rows:
                file_path = row['file_path']
                if file_path and os.path.exists(file_path):
                    filtered.append(row)
                if len(filtered) >= limit:
                    break

            # 如果过滤后不足 limit 条，就直接用已有的
            if not filtered:
                filtered = rows

            return self._rows_to_results(filtered)[:limit]

        except Exception as e:
            self.error_handler.handle_database_error(f"随机挑选视频失败: {e}", self.db_path, "random_videos")
            return []
    
    def start_maintain(self, path: str, labels: Optional[str] = None, logical_path: Optional[str] = None) -> Dict[str, any]:
        """开始维护视频数据。

        当前实现：
        - 使用增强扫描器对指定目录进行完整扫描与智能合并
        - 扫描完成后，根据目录结构自动为视频打标签：
          - 当扫描根目录下存在子目录时，使用“首层子目录名”作为标签
          - 当直接扫描某个叶子目录时，使用该目录名作为标签
        """
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

            # 扫描成功后，根据目录结构自动打标签
            try:
                self._apply_folder_based_tags(path)
            except Exception as tag_exc:
                # 自动标签失败不影响主流程，只记录错误
                self.error_handler.handle_database_error(
                    f"应用目录标签失败: {tag_exc}", self.db_path, "apply_folder_tags"
                )
            
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

    def _apply_folder_based_tags(self, root_path: str) -> None:
        """根据目录结构为扫描到的视频自动打标签。

        约定：
        - 以维护入口选择的目录作为扫描根目录
        - 对于位于根目录下的多级子目录中的视频，以“首层子目录名”作为标签
          例如：/root/标签A/video1.mp4, /root/标签B/sub/video2.mp4
          在扫描根为 /root 时，两条记录分别打上“标签A”、“标签B”标签
        - 如果直接扫描某个叶子目录（该目录下直接放视频），则使用该目录名作为标签
        """
        if not self.storage:
            return

        root_abs = os.path.abspath(root_path)
        # 确保以路径分隔符结尾，避免 /foo 与 /foobar 前缀混淆
        root_prefix = os.path.join(root_abs, "")

        cursor = self.storage.connection.cursor()
        cursor.execute(
            "SELECT id, file_path FROM video_info WHERE file_path LIKE ?",
            (root_prefix + "%",),
        )
        rows = cursor.fetchall()
        if not rows:
            return

        for row in rows:
            video_id = row["id"] if isinstance(row, dict) else row["id"]
            file_path = row["file_path"] if isinstance(row, dict) else row["file_path"]
            if not file_path:
                continue

            try:
                rel_path = os.path.relpath(file_path, root_abs)
            except Exception:
                continue

            parts = rel_path.split(os.sep)
            if len(parts) >= 2:
                tag = parts[0]
            else:
                # 当文件直接位于扫描根目录下时，使用根目录名作为标签
                tag = os.path.basename(root_abs)

            tag = (tag or "").strip()
            if not tag:
                continue

            cursor.execute(
                "INSERT OR IGNORE INTO video_tags (video_id, tag) VALUES (?, ?)",
                (video_id, tag),
            )

        self.storage.connection.commit()


# 创建全局服务实例
video_service = VideoService()


def search_videos(keyword: str) -> List[Dict[str, str]]:
    """搜索视频 - 兼容性包装函数"""
    return video_service.search_videos(keyword)


def random_videos(limit: int = 20, ensure_accessible: bool = True) -> List[Dict[str, str]]:
    """随机挑选视频 - 兼容性包装函数"""
    return video_service.random_videos(limit=limit, ensure_accessible=ensure_accessible)


def start_maintain(path: str, labels: Optional[str] = None, logical_path: Optional[str] = None) -> Dict[str, any]:
    """开始维护视频数据 - 兼容性包装函数"""
    return video_service.start_maintain(path, labels, logical_path)
