"""
SQLite数据库存储模块

提供视频信息的SQLite数据库存储功能，包括创建表、插入、查询、更新、删除等操作。
"""

import sqlite3
import csv
import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from .metadata import VideoInfo


class SQLiteStorage:
    """SQLite数据库存储类"""
    
    def __init__(self, db_path: str = ":memory:"):
        """
        初始化SQLite存储
        
        Args:
            db_path: 数据库文件路径，默认为内存数据库
        """
        self.db_path = db_path
        self.connection = None
        self._connect()
        self._create_tables()
        self._create_indexes()
    
    def _connect(self):
        """连接到数据库"""
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
    
    def _create_tables(self):
        """创建数据表 - 符合README设计的三表结构"""
        cursor = self.connection.cursor()
        
        # 主视频信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                width INTEGER,
                height INTEGER,
                resolution TEXT,
                duration REAL,
                duration_formatted TEXT,
                video_codec TEXT,
                audio_codec TEXT,
                file_size INTEGER,
                bit_rate INTEGER,
                frame_rate REAL,
                logical_path TEXT,
                created_time TEXT NOT NULL,
                updated_time TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 视频标签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                created_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES video_info (id) ON DELETE CASCADE,
                UNIQUE(video_id, tag)
            )
        """)
        
        # 扫描历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_path TEXT NOT NULL,
                scan_time TEXT DEFAULT CURRENT_TIMESTAMP,
                files_found INTEGER DEFAULT 0,
                files_processed INTEGER DEFAULT 0,
                tags TEXT,
                logical_path TEXT,
                status TEXT DEFAULT 'completed'
            )
        """)
        
        self.connection.commit()
    
    def _create_indexes(self):
        """创建数据库索引"""
        cursor = self.connection.cursor()
        
        # video_info表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_file_path ON video_info(file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_filename ON video_info(filename)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_created_time ON video_info(created_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_logical_path ON video_info(logical_path)")
        
        # video_tags表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_video_id ON video_tags(video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON video_tags(tag)")
        
        # scan_history表索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_path ON scan_history(scan_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_time ON scan_history(scan_time)")
        
        self.connection.commit()
    
    def insert_video_info(self, video_info: VideoInfo) -> Optional[int]:
        """
        插入视频信息
        
        Args:
            video_info: 视频信息对象
            
        Returns:
            Optional[int]: 插入成功返回ID，失败返回None
        """
        try:
            cursor = self.connection.cursor()
            
            # 计算分辨率字符串
            resolution = f"{video_info.width}x{video_info.height}" if video_info.width and video_info.height else None
            
            # 格式化时长
            duration_formatted = None
            if video_info.duration:
                hours = int(video_info.duration // 3600)
                minutes = int((video_info.duration % 3600) // 60)
                seconds = int(video_info.duration % 60)
                duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # 插入主视频信息
            cursor.execute("""
                INSERT INTO video_info (
                    file_path, filename, width, height, resolution,
                    duration, duration_formatted, video_codec, audio_codec, 
                    file_size, bit_rate, frame_rate, logical_path, created_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                video_info.file_path,
                video_info.filename,
                video_info.width,
                video_info.height,
                resolution,
                video_info.duration,
                duration_formatted,
                video_info.video_codec,
                video_info.audio_codec,
                video_info.file_size,
                video_info.bit_rate,
                video_info.frame_rate,
                video_info.logical_path,
                video_info.created_time.isoformat() if isinstance(video_info.created_time, datetime) else str(video_info.created_time)
            ))
            
            video_id = cursor.lastrowid
            
            # 插入标签信息
            if video_info.tags:
                for tag in video_info.tags:
                    cursor.execute("""
                        INSERT OR IGNORE INTO video_tags (video_id, tag)
                        VALUES (?, ?)
                    """, (video_id, tag.strip()))
            
            self.connection.commit()
            return video_id
        except sqlite3.IntegrityError:
            return None
    
    def insert_multiple_video_infos(self, video_infos: List[VideoInfo]) -> List[int]:
        """
        批量插入视频信息
        
        Args:
            video_infos: 视频信息列表
            
        Returns:
            List[int]: 成功插入的ID列表
        """
        inserted_ids = []
        for video_info in video_infos:
            video_id = self.insert_video_info(video_info)
            if video_id is not None:
                inserted_ids.append(video_id)
        return inserted_ids
    
    def add_scan_history(self, scan_path: str, files_found: int, files_processed: int, 
                        tags: Optional[List[str]] = None, logical_path: Optional[str] = None) -> int:
        """
        添加扫描历史记录
        
        Args:
            scan_path: 扫描路径
            files_found: 发现的文件数量
            files_processed: 处理的文件数量
            tags: 标签列表
            logical_path: 逻辑路径
            
        Returns:
            int: 扫描历史记录ID
        """
        cursor = self.connection.cursor()
        
        tags_str = ','.join(tags) if tags else None
        
        cursor.execute("""
            INSERT INTO scan_history (
                scan_path, files_found, files_processed, tags, logical_path
            ) VALUES (?, ?, ?, ?, ?)
        """, (scan_path, files_found, files_processed, tags_str, logical_path))
        
        self.connection.commit()
        return cursor.lastrowid

    def add_csv_merge_history(self, csv_file_path: str, files_found: int, files_processed: int, 
                             csv_fingerprint: str, original_scan_path: str = None, 
                             tags: Optional[List[str]] = None, logical_path: Optional[str] = None) -> int:
        """
        添加CSV合并历史记录
        
        Args:
            csv_file_path: CSV文件路径
            files_found: CSV中的记录数量
            files_processed: 成功处理的记录数量
            csv_fingerprint: CSV文件指纹（用于检测重复合并）
            original_scan_path: 从CSV文件名推断的原始扫描路径
            tags: 标签列表
            logical_path: 逻辑路径
            
        Returns:
            int: 扫描历史记录ID
        """
        cursor = self.connection.cursor()
        
        tags_str = ','.join(tags) if tags else None
        
        # 使用CSV文件路径作为scan_path，并在status字段中标记为CSV合并
        cursor.execute("""
            INSERT INTO scan_history (
                scan_path, files_found, files_processed, tags, logical_path, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (csv_file_path, files_found, files_processed, tags_str, logical_path, f"csv_merge:{csv_fingerprint}"))
        
        self.connection.commit()
        return cursor.lastrowid

    def check_csv_already_merged(self, csv_fingerprint: str) -> bool:
        """
        检查CSV文件是否已经被合并过
        
        Args:
            csv_fingerprint: CSV文件指纹
            
        Returns:
            bool: 如果已经合并过返回True，否则返回False
        """
        cursor = self.connection.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM scan_history 
            WHERE status LIKE ? AND status LIKE ?
        """, ('csv_merge:%', f'%{csv_fingerprint}%'))
        
        result = cursor.fetchone()
        return result[0] > 0 if result else False

    def get_csv_fingerprint(self, csv_file_path: str) -> str:
        """
        生成CSV文件的指纹，用于检测重复合并
        
        Args:
            csv_file_path: CSV文件路径
            
        Returns:
            str: CSV文件指纹
        """
        import hashlib
        import os
        
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV文件不存在: {csv_file_path}")
        
        # 获取文件基本信息
        file_stat = os.stat(csv_file_path)
        file_size = file_stat.st_size
        file_mtime = int(file_stat.st_mtime)
        
        # 读取文件内容的前后几行来生成指纹
        fingerprint_data = []
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # 添加文件基本信息
                fingerprint_data.append(f"size:{file_size}")
                fingerprint_data.append(f"lines:{len(lines)}")
                fingerprint_data.append(f"mtime:{file_mtime}")
                
                # 添加前3行和后3行的内容（如果存在）
                if lines:
                    # 标题行
                    if len(lines) > 0:
                        fingerprint_data.append(f"header:{lines[0].strip()}")
                    
                    # 前几行数据
                    for i in range(1, min(4, len(lines))):
                        fingerprint_data.append(f"line{i}:{lines[i].strip()}")
                    
                    # 后几行数据（避免重复）
                    if len(lines) > 4:
                        for i in range(max(4, len(lines) - 3), len(lines)):
                            fingerprint_data.append(f"tail{i}:{lines[i].strip()}")
        
        except Exception as e:
            # 如果读取失败，至少使用文件基本信息
            fingerprint_data = [f"size:{file_size}", f"mtime:{file_mtime}", f"error:{str(e)}"]
        
        # 生成MD5哈希
        fingerprint_str = '|'.join(fingerprint_data)
        return hashlib.md5(fingerprint_str.encode('utf-8')).hexdigest()

    def extract_scan_info_from_csv_filename(self, csv_file_path: str) -> Dict[str, Any]:
        """
        从CSV文件名中提取扫描信息
        
        Args:
            csv_file_path: CSV文件路径
            
        Returns:
            Dict: 包含扫描信息的字典
        """
        from pathlib import Path
        import re
        
        filename = Path(csv_file_path).stem  # 去掉.csv扩展名
        
        # 匹配时间戳模式 YYYYMMDD_HHMMSS
        timestamp_pattern = r'(\d{8}_\d{6})$'
        timestamp_match = re.search(timestamp_pattern, filename)
        
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            # 移除时间戳部分，剩下的就是路径部分
            path_part = filename[:timestamp_match.start()].rstrip('_')
            
            # 尝试重构原始路径
            # 将下划线替换回路径分隔符，并添加常见的前缀
            if path_part:
                # 对于类似 "WS_2_media_videos" 的情况，重构为 "/Volumes/ws2/media/videos/"
                path_components = path_part.split('_')
                if len(path_components) >= 2:
                    # 假设第一个组件是卷名
                    volume_name = path_components[0].lower()
                    remaining_path = '/'.join(path_components[1:])
                    reconstructed_path = f"/Volumes/{volume_name}/{remaining_path}/"
                else:
                    reconstructed_path = f"/{path_part}/"
            else:
                reconstructed_path = "unknown"
            
            return {
                'timestamp': timestamp_str,
                'original_scan_path': reconstructed_path,
                'path_components': path_part.split('_') if path_part else []
            }
        
        return {
            'timestamp': None,
            'original_scan_path': 'unknown',
            'path_components': []
        }
    
    def upsert_video_info(self, video_info: VideoInfo) -> int:
        """
        插入或更新视频信息
        
        Args:
            video_info: 视频信息对象
            
        Returns:
            int: 记录的ID
        """
        # 先尝试获取现有记录
        existing_info = self.get_video_info_by_path(video_info.file_path)
        if existing_info:
            # 更新现有记录
            cursor = self.connection.cursor()
            
            # 计算分辨率字符串
            resolution = f"{video_info.width}x{video_info.height}" if video_info.width and video_info.height else None
            
            # 格式化时长
            duration_formatted = None
            if video_info.duration:
                hours = int(video_info.duration // 3600)
                minutes = int((video_info.duration % 3600) // 60)
                seconds = int(video_info.duration % 60)
                duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            cursor.execute("""
                UPDATE video_info SET
                    filename = ?, width = ?, height = ?, resolution = ?,
                    duration = ?, duration_formatted = ?, video_codec = ?, audio_codec = ?, 
                    file_size = ?, bit_rate = ?, frame_rate = ?, logical_path = ?, created_time = ?, updated_time = CURRENT_TIMESTAMP
                WHERE file_path = ?
            """, (
                video_info.filename,
                video_info.width,
                video_info.height,
                resolution,
                video_info.duration,
                duration_formatted,
                video_info.video_codec,
                video_info.audio_codec,
                video_info.file_size,
                video_info.bit_rate,
                video_info.frame_rate,
                video_info.logical_path,
                video_info.created_time.isoformat() if isinstance(video_info.created_time, datetime) else str(video_info.created_time),
                video_info.file_path
            ))
            self.connection.commit()
            return existing_info['id']
        else:
            # 插入新记录
            return self.insert_video_info(video_info)
    
    def get_video_info_by_id(self, video_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取视频信息
        
        Args:
            video_id: 视频ID
            
        Returns:
            Optional[Dict[str, Any]]: 视频信息字典，如果不存在则返回None
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM video_info WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_video_info_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        根据文件路径获取视频信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[Dict[str, Any]]: 视频信息字典，如果不存在则返回None
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM video_info WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def search_videos(self, filename_pattern: str = "", min_width: Optional[int] = None,
                     max_width: Optional[int] = None, min_height: Optional[int] = None,
                     max_height: Optional[int] = None, min_duration: Optional[float] = None,
                     max_duration: Optional[float] = None, video_codec: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索视频
        
        Args:
            filename_pattern: 文件名模式
            min_width: 最小宽度
            max_width: 最大宽度
            min_height: 最小高度
            max_height: 最大高度
            min_duration: 最小时长
            max_duration: 最大时长
            video_codec: 视频编码
            
        Returns:
            List[Dict[str, Any]]: 匹配的视频信息列表
        """
        cursor = self.connection.cursor()
        
        query = "SELECT * FROM video_info WHERE 1=1"
        params = []
        
        if filename_pattern:
            query += " AND filename LIKE ?"
            params.append(f"%{filename_pattern}%")
        
        if min_width is not None:
            query += " AND width >= ?"
            params.append(min_width)
        
        if max_width is not None:
            query += " AND width <= ?"
            params.append(max_width)
        
        if min_height is not None:
            query += " AND height >= ?"
            params.append(min_height)
        
        if max_height is not None:
            query += " AND height <= ?"
            params.append(max_height)
        
        if min_duration is not None:
            query += " AND duration >= ?"
            params.append(min_duration)
        
        if max_duration is not None:
            query += " AND duration <= ?"
            params.append(max_duration)
        
        if video_codec:
            query += " AND video_codec = ?"
            params.append(video_codec)
        
        query += " ORDER BY filename"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_total_count(self) -> int:
        """
        获取视频总数
        
        Returns:
            int: 视频总数
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM video_info")
        return cursor.fetchone()['count']
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        cursor = self.connection.cursor()
        
        # 总数量
        cursor.execute("SELECT COUNT(*) as count FROM video_info")
        total_videos = cursor.fetchone()['count']
        
        # 总文件大小
        cursor.execute("SELECT SUM(file_size) as total_size FROM video_info")
        total_size = cursor.fetchone()['total_size'] or 0
        
        # 总时长
        cursor.execute("SELECT SUM(duration) as total_duration FROM video_info")
        total_duration = cursor.fetchone()['total_duration'] or 0
        
        # 平均文件大小
        avg_file_size = total_size / total_videos if total_videos > 0 else 0
        
        # 平均时长
        avg_duration = total_duration / total_videos if total_videos > 0 else 0
        
        # 最常见的编码
        cursor.execute("""
            SELECT video_codec, COUNT(*) as count 
            FROM video_info 
            WHERE video_codec IS NOT NULL 
            GROUP BY video_codec 
            ORDER BY count DESC 
            LIMIT 1
        """)
        most_common_codec_row = cursor.fetchone()
        most_common_codec = most_common_codec_row['video_codec'] if most_common_codec_row else None
        
        # 分辨率分布
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN width >= 3840 THEN '4K+'
                    WHEN width >= 1920 THEN 'FHD'
                    WHEN width >= 1280 THEN 'HD'
                    ELSE 'SD'
                END as resolution_category,
                COUNT(*) as count
            FROM video_info 
            WHERE width IS NOT NULL 
            GROUP BY resolution_category
        """)
        resolution_distribution = {row['resolution_category']: row['count'] for row in cursor.fetchall()}
        
        return {
            'total_videos': total_videos,
            'total_size': total_size,
            'total_duration': total_duration,
            'avg_file_size': avg_file_size,
            'avg_duration': avg_duration,
            'most_common_codec': most_common_codec,
            'resolution_distribution': resolution_distribution
        }
    
    def delete_video_info(self, video_id: int) -> bool:
        """
        删除视频信息
        
        Args:
            video_id: 视频ID
            
        Returns:
            bool: 删除是否成功
        """
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM video_info WHERE id = ?", (video_id,))
        self.connection.commit()
        return cursor.rowcount > 0
    
    def update_video_info(self, video_id: int, update_data: Dict[str, Any]) -> bool:
        """
        更新视频信息
        
        Args:
            video_id: 视频ID
            update_data: 要更新的字段字典
            
        Returns:
            bool: 更新是否成功
        """
        if not update_data:
            return False
        
        # 构建更新语句
        set_clauses = []
        params = []
        
        for key, value in update_data.items():
            if key in ['filename', 'created_time', 'width', 'height', 'resolution', 'duration',
                      'duration_formatted', 'video_codec', 'audio_codec', 'file_size', 'bit_rate', 'frame_rate', 'logical_path']:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_time = CURRENT_TIMESTAMP")
        params.append(video_id)
        
        query = f"UPDATE video_info SET {', '.join(set_clauses)} WHERE id = ?"
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
        return cursor.rowcount > 0
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        格式化文件大小为GB格式
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            str: 格式化后的文件大小（如：5G, 5.23G）
        """
        if size_bytes is None or size_bytes == 0:
            return "0G"
        
        # 转换为GB
        size_gb = size_bytes / (1024 * 1024 * 1024)
        
        # 四舍五入到两位小数
        if size_gb >= 10:
            # 大于等于10G时，显示整数
            return f"{round(size_gb)}G"
        else:
            # 小于10G时，显示两位小数
            return f"{size_gb:.2f}G"

    def export_to_csv(self, csv_path: str) -> bool:
        """
        导出到CSV文件
        
        Args:
            csv_path: CSV文件路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM video_info ORDER BY filename")
            rows = cursor.fetchall()
            
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                if rows:
                    writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
                    writer.writeheader()
                    for row in rows:
                        writer.writerow(dict(row))
            
            return True
        except Exception:
            return False

    def export_simple_format(self, output_path: str) -> bool:
        """
        简化格式导出：只包含filename（去掉后缀）、filesize（格式化为GB）和logical_path
        输出格式：每行为 "filename_without_ext filesize logical_path"
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT filename, file_size, logical_path 
                FROM video_info 
                ORDER BY filename
            """)
            rows = cursor.fetchall()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for row in rows:
                    filename = row['filename'] or ''
                    file_size = row['file_size'] or 0
                    logical_path = row['logical_path'] or ''
                    
                    # 去掉文件名后缀
                    filename_without_ext = os.path.splitext(filename)[0] if filename else ''
                    
                    # 格式化文件大小
                    formatted_size = self._format_file_size(file_size)
                    
                    # 输出格式：filename_without_ext filesize logical_path
                    f.write(f"{filename_without_ext} {formatted_size} {logical_path}\n")
            
            return True
        except Exception as e:
            print(f"简化导出失败: {e}")
            return False
    
    def import_from_csv(self, csv_path: str) -> int:
        """
        从CSV文件导入
        
        Args:
            csv_path: CSV文件路径
            
        Returns:
            int: 成功导入的数量
        """
        if not os.path.exists(csv_path):
            return 0
        
        success_count = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        video_info = VideoInfo(file_path=row['file_path'], 
                                             tags=row.get('tags', '').split(',') if row.get('tags') else [],
                                             logical_path=row.get('logical_path', ''))
                        video_info.filename = row['filename']
                        video_info.created_time = row['created_time']
                        video_info.width = int(row['width']) if row['width'] else None
                        video_info.height = int(row['height']) if row['height'] else None
                        video_info.duration = float(row['duration']) if row['duration'] else None
                        video_info.video_codec = row['video_codec'] if row['video_codec'] else None
                        video_info.audio_codec = row['audio_codec'] if row['audio_codec'] else None
                        video_info.file_size = int(row['file_size']) if row['file_size'] else None
                        video_info.bit_rate = int(row['bit_rate']) if row['bit_rate'] else None
                        video_info.frame_rate = float(row['frame_rate']) if row.get('frame_rate') else None
                        
                        video_id = self.upsert_video_info(video_info)
                        if video_id:
                            success_count += 1
                    except (ValueError, KeyError):
                        continue
        except Exception:
            pass
        
        return success_count
    
    def get_all_videos(self) -> List[Dict[str, Any]]:
        """
        获取所有视频信息
        
        Returns:
            List[Dict[str, Any]]: 所有视频信息列表
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM video_info ORDER BY filename")
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def search_videos_by_codes(self, codes: List[str]) -> List[Dict[str, Any]]:
        """
        根据视频code列表查询视频信息
        
        Args:
            codes: 视频code列表（文件名去掉扩展名）
            
        Returns:
            List[Dict[str, Any]]: 匹配的视频信息列表，只包含code、file_size、logical_path字段
        """
        if not codes:
            return []
        
        cursor = self.connection.cursor()
        
        # 构建查询条件，支持多个code的精确匹配（忽略大小写）
        placeholders = ','.join(['?' for _ in codes])
        query = f"""
            SELECT 
                CASE 
                    WHEN INSTR(filename, '.') > 0 
                    THEN SUBSTR(filename, 1, INSTR(filename, '.') - 1)
                    ELSE filename
                END as video_code,
                file_size,
                logical_path,
                filename
            FROM video_info 
            WHERE LOWER(CASE 
                WHEN INSTR(filename, '.') > 0 
                THEN SUBSTR(filename, 1, INSTR(filename, '.') - 1)
                ELSE filename
            END) IN ({placeholders})
            ORDER BY video_code
        """
        
        # 将所有codes转换为小写进行匹配
        lower_codes = [code.lower() for code in codes]
        cursor.execute(query, lower_codes)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_statistics_by_tags(self) -> List[Dict[str, Any]]:
        """
        按标签分组统计视频数量
        
        Returns:
            List[Dict[str, Any]]: 标签统计列表，每个元素包含tag和count字段
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                COALESCE(vt.tag, '无标签') as tag,
                COUNT(DISTINCT vi.id) as count
            FROM video_info vi
            LEFT JOIN video_tags vt ON vi.id = vt.video_id
            GROUP BY vt.tag
            ORDER BY count DESC, tag ASC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_statistics_by_resolution(self) -> List[Dict[str, Any]]:
        """
        按分辨率分组统计视频数量
        
        Returns:
            List[Dict[str, Any]]: 分辨率统计列表，每个元素包含resolution和count字段
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN width >= 3840 THEN '4K+ (3840x2160+)'
                    WHEN width >= 1920 THEN 'FHD (1920x1080)'
                    WHEN width >= 1280 THEN 'HD (1280x720)'
                    WHEN width IS NOT NULL THEN 'SD (<1280)'
                    ELSE '未知分辨率'
                END as resolution,
                COUNT(*) as count
            FROM video_info 
            GROUP BY 
                CASE 
                    WHEN width >= 3840 THEN '4K+ (3840x2160+)'
                    WHEN width >= 1920 THEN 'FHD (1920x1080)'
                    WHEN width >= 1280 THEN 'HD (1280x720)'
                    WHEN width IS NOT NULL THEN 'SD (<1280)'
                    ELSE '未知分辨率'
                END
            ORDER BY count DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_statistics_by_duration(self) -> List[Dict[str, Any]]:
        """
        按时长分组统计视频数量
        
        Returns:
            List[Dict[str, Any]]: 时长统计列表，每个元素包含duration_range和count字段
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN duration >= 7200 THEN '超长 (2小时+)'
                    WHEN duration >= 3600 THEN '长片 (1-2小时)'
                    WHEN duration >= 1800 THEN '中等 (30分钟-1小时)'
                    WHEN duration >= 600 THEN '短片 (10-30分钟)'
                    WHEN duration IS NOT NULL THEN '极短 (<10分钟)'
                    ELSE '未知时长'
                END as duration_range,
                COUNT(*) as count
            FROM video_info 
            GROUP BY 
                CASE 
                    WHEN duration >= 7200 THEN '超长 (2小时+)'
                    WHEN duration >= 3600 THEN '长片 (1-2小时)'
                    WHEN duration >= 1800 THEN '中等 (30分钟-1小时)'
                    WHEN duration >= 600 THEN '短片 (10-30分钟)'
                    WHEN duration IS NOT NULL THEN '极短 (<10分钟)'
                    ELSE '未知时长'
                END
            ORDER BY count DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def get_enhanced_statistics(self) -> Dict[str, Any]:
        """
        获取增强的统计信息，包括同名视频检测
        
        Returns:
            Dict[str, Any]: 增强统计信息字典
        """
        cursor = self.connection.cursor()
        
        # 基本统计
        basic_stats = self.get_statistics()
        
        # 同名视频统计（基于文件名去掉扩展名）
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN INSTR(filename, '.') > 0 
                    THEN SUBSTR(filename, 1, INSTR(filename, '.') - 1)
                    ELSE filename
                END as video_code,
                COUNT(*) as count
            FROM video_info 
            GROUP BY video_code
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)
        duplicate_videos = cursor.fetchall()
        duplicate_count = len(duplicate_videos)
        total_duplicates = sum(row['count'] for row in duplicate_videos)
        
        # 合并统计信息
        enhanced_stats = basic_stats.copy()
        enhanced_stats.update({
            'duplicate_video_groups': duplicate_count,
            'total_duplicate_videos': total_duplicates,
            'unique_videos': basic_stats['total_videos'] - total_duplicates + duplicate_count
        })
        
        return enhanced_stats
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()