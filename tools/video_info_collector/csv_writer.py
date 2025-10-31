"""
CSV文件写入器

负责将视频信息写入CSV格式的临时文件。
"""

import csv
import os
from typing import List, Dict, Any

from .metadata import VideoInfo


class CSVWriter:
    """CSV文件写入器"""
    
    def __init__(self, encoding: str = 'utf-8-sig', delimiter: str = ','):
        """
        初始化CSV写入器
        
        Args:
            encoding: 文件编码，默认使用utf-8-sig（带BOM的UTF-8）
            delimiter: CSV分隔符，默认为逗号
        """
        self.encoding = encoding
        self.delimiter = delimiter
        
        # CSV字段定义 - 符合README设计
        self.fieldnames = [
            'file_path', 'filename', 'width', 'height', 'resolution',
            'duration', 'duration_formatted', 'video_codec', 'audio_codec',
            'file_size', 'bit_rate', 'frame_rate', 'created_time',
            'tags', 'logical_path'
        ]
    
    def write_video_infos(self, video_infos: List[VideoInfo], csv_file_path: str):
        """
        写入视频信息到CSV文件（覆盖模式）
        
        Args:
            video_infos: 视频信息列表
            csv_file_path: CSV文件路径
        """
        # 确保目录存在
        dir_path = os.path.dirname(csv_file_path)
        if dir_path:  # 只有当目录路径不为空时才创建
            os.makedirs(dir_path, exist_ok=True)
        
        with open(csv_file_path, 'w', newline='', encoding=self.encoding) as csvfile:
            writer = csv.DictWriter(
                csvfile, 
                fieldnames=self.fieldnames,
                delimiter=self.delimiter
            )
            
            # 写入标题行
            writer.writeheader()
            
            # 写入数据行
            for video_info in video_infos:
                row_data = self._video_info_to_row(video_info)
                writer.writerow(row_data)
    
    def append_video_infos(self, video_infos: List[VideoInfo], csv_file_path: str):
        """
        追加视频信息到CSV文件
        
        Args:
            video_infos: 视频信息列表
            csv_file_path: CSV文件路径
        """
        # 如果文件不存在，创建新文件
        if not os.path.exists(csv_file_path):
            self.write_video_infos(video_infos, csv_file_path)
            return
        
        # 追加到现有文件
        with open(csv_file_path, 'a', newline='', encoding=self.encoding) as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=self.fieldnames,
                delimiter=self.delimiter
            )
            
            # 写入数据行（不写标题行）
            for video_info in video_infos:
                row_data = self._video_info_to_row(video_info)
                writer.writerow(row_data)
    
    def read_csv_file(self, csv_file_path: str) -> List[Dict[str, Any]]:
        """
        读取CSV文件内容
        
        Args:
            csv_file_path: CSV文件路径
            
        Returns:
            字典列表，每个字典代表一行数据
            
        Raises:
            FileNotFoundError: 文件不存在
        """
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
        
        rows = []
        with open(csv_file_path, 'r', encoding=self.encoding) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=self.delimiter)
            for row in reader:
                rows.append(row)
        
        return rows
    
    def _video_info_to_row(self, video_info: VideoInfo) -> Dict[str, str]:
        """
        将VideoInfo对象转换为CSV行数据
        
        Args:
            video_info: 视频信息对象
            
        Returns:
            字典格式的行数据
        """
        data_dict = video_info.to_dict()
        
        # 格式化特定字段
        row_data = {}
        for field in self.fieldnames:
            value = data_dict.get(field)
            if value is None:
                row_data[field] = ''
            elif field == 'frame_rate' and value:
                # frame_rate保留到整数，四舍五入
                try:
                    row_data[field] = str(round(float(value)))
                except (ValueError, TypeError):
                    row_data[field] = str(value)
            elif field == 'created_time' and value:
                # created_time截取到秒为止（移除毫秒部分）
                try:
                    # 如果是ISO格式，截取到秒
                    if 'T' in str(value) and '.' in str(value):
                        row_data[field] = str(value).split('.')[0]
                    else:
                        row_data[field] = str(value)
                except:
                    row_data[field] = str(value)
            elif field == 'duration' and value:
                # duration保留2位小数
                try:
                    row_data[field] = f"{float(value):.2f}"
                except (ValueError, TypeError):
                    row_data[field] = str(value)
            elif field == 'logical_path' and not value and 'file_path' in data_dict:
                # 当logical_path为空时，使用file_path的目录部分
                try:
                    from pathlib import Path
                    file_path = data_dict['file_path']
                    if file_path:
                        row_data[field] = str(Path(file_path).parent)
                    else:
                        row_data[field] = ''
                except:
                    row_data[field] = ''
            else:
                row_data[field] = str(value)
        
        return row_data