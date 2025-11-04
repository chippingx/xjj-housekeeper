#!/usr/bin/env python3
"""
调试替换检测功能
"""

import os
import tempfile
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.metadata import VideoInfo
from tools.video_info_collector.smart_merge_manager import SmartMergeManager

def debug_replacement_detection():
    """调试替换检测功能"""
    print("=== 调试替换检测功能 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建数据库
        db_path = os.path.join(temp_dir, "debug.db")
        storage = SQLiteStorage(db_path)
        
        # 创建两个不同的文件路径
        old_video_path = os.path.join(temp_dir, "old_ABC-123.mp4")
        new_video_path = os.path.join(temp_dir, "new_ABC-123.mp4")
        
        # 创建实际的文件
        with open(old_video_path, 'w') as f:
            f.write("old video content")
        with open(new_video_path, 'w') as f:
            f.write("new video content with better quality")
        
        # 创建旧视频记录
        old_video = VideoInfo(file_path=old_video_path, tags=["test"])
        old_video.video_code = "ABC-123"
        old_video.file_fingerprint = "old_fingerprint_123"
        old_video.filename = "old_ABC-123.mp4"
        old_video.width = 1280
        old_video.height = 720
        old_video.video_codec = "h264"
        old_video.bit_rate = 5000
        old_video.file_size = 1000000
        
        # 插入旧视频
        video_id = storage.insert_video_info(old_video)
        print(f"插入旧视频，ID: {video_id}")
        
        # 创建新视频记录
        new_video = VideoInfo(file_path=new_video_path, tags=["test"])
        new_video.video_code = "ABC-123"
        new_video.file_fingerprint = "new_fingerprint_123"
        new_video.filename = "ABC-123_new_version.mp4"
        new_video.width = 1920
        new_video.height = 1080
        new_video.video_codec = "h265"
        new_video.bit_rate = 15000
        new_video.file_size = 2000000
        
        print(f"旧视频: {old_video.video_code}, {old_video.file_fingerprint}, {old_video.file_path}")
        print(f"新视频: {new_video.video_code}, {new_video.file_fingerprint}, {new_video.file_path}")
        
        # 获取现有视频
        existing_videos = storage.get_all_videos()
        print(f"数据库中现有视频数量: {len(existing_videos)}")
        
        # 转换为VideoInfo对象
        existing_video_infos = []
        for v in existing_videos:
            video_info = VideoInfo(file_path=v['file_path'], tags=v.get('tags', []))
            video_info.id = v['id']
            video_info.video_code = v['video_code']
            video_info.file_fingerprint = v['file_fingerprint']
            video_info.filename = v['filename']
            video_info.width = v['width']
            video_info.height = v['height']
            video_info.video_codec = v['video_codec']
            video_info.bit_rate = v['bit_rate']
            video_info.file_size = v['file_size']
            video_info.file_status = v.get('file_status', 'present')
            existing_video_infos.append(video_info)
        
        # 创建SmartMergeManager
        merge_manager = SmartMergeManager(storage)
        
        # 分析合并候选项
        merge_results = merge_manager.analyze_merge_candidates([new_video], existing_video_infos)
        
        print("=== 合并分析结果 ===")
        for action_type, actions in merge_results.items():
            if actions:
                print(f"{action_type}: {len(actions)} 个动作")
                for action in actions:
                    print(f"  - {action.reason}")
        
        # 测试替换检测逻辑
        print("\n=== 测试替换检测逻辑 ===")
        if existing_video_infos:
            old_video_from_db = existing_video_infos[0]
            is_replacement = merge_manager._is_replacement_scenario(new_video, old_video_from_db)
            print(f"是否为替换场景: {is_replacement}")
            
            if is_replacement:
                print("替换检测成功！")
            else:
                print("替换检测失败，检查条件:")
                print(f"  - 相同video_code: {new_video.video_code == old_video_from_db.video_code}")
                print(f"  - 不同fingerprint: {new_video.file_fingerprint != old_video_from_db.file_fingerprint}")
                print(f"  - 文件大小比例: {new_video.file_size / old_video_from_db.file_size if old_video_from_db.file_size else 'N/A'}")
                print(f"  - 分辨率比例: {(new_video.width * new_video.height) / (old_video_from_db.width * old_video_from_db.height) if old_video_from_db.width and old_video_from_db.height else 'N/A'}")
                print(f"  - 码率比例: {new_video.bit_rate / old_video_from_db.bit_rate if old_video_from_db.bit_rate else 'N/A'}")
                print(f"  - 不同编解码器: {new_video.video_codec != old_video_from_db.video_codec}")
        else:
            print("没有找到现有视频记录")
        
        storage.close()

if __name__ == "__main__":
    debug_replacement_detection()