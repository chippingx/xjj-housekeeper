#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.video_info_collector.metadata import VideoInfo
from tools.video_info_collector.smart_merge_manager import SmartMergeManager
from tools.video_info_collector.sqlite_storage import SQLiteStorage
from datetime import datetime

def debug_merge_action():
    """调试merge action决策逻辑"""
    
    # 创建临时数据库
    storage = SQLiteStorage(":memory:")
    
    merge_manager = SmartMergeManager(storage)
    
    # 创建旧视频记录
    old_video = VideoInfo(file_path="/old/path/ABC-123.mp4", tags=["test"])
    old_video.video_code = "ABC-123"
    old_video.file_fingerprint = "old_fingerprint_123"
    old_video.filename = "ABC-123.mp4"
    old_video.width = 1280
    old_video.height = 720
    old_video.duration = 3600.0
    old_video.video_codec = "h264"
    old_video.audio_codec = "aac"
    old_video.file_size = 1000000
    old_video.bit_rate = 5000
    old_video.frame_rate = 30.0
    old_video.created_time = datetime.now()
    old_video.file_status = "present"
    
    print("旧视频信息:")
    print(f"  video_code: {old_video.video_code}")
    print(f"  file_fingerprint: {old_video.file_fingerprint}")
    print(f"  file_status: {old_video.file_status}")
    print(f"  file_size: {old_video.file_size}")
    print(f"  video_codec: {old_video.video_codec}")
    print()
    
    # 创建新视频记录
    new_video = VideoInfo(file_path="/new/path/ABC-123_new_version.mp4", tags=["test"])
    new_video.video_code = "ABC-123"
    new_video.file_fingerprint = "new_fingerprint_123"
    new_video.filename = "ABC-123_new_version.mp4"
    new_video.width = 1920
    new_video.height = 1080
    new_video.duration = 3600.0
    new_video.video_codec = "h265"
    new_video.audio_codec = "aac"
    new_video.file_size = 15000000
    new_video.bit_rate = 8000
    new_video.frame_rate = 30.0
    new_video.created_time = datetime.now()
    
    print("新视频信息:")
    print(f"  video_code: {new_video.video_code}")
    print(f"  file_fingerprint: {new_video.file_fingerprint}")
    print(f"  file_size: {new_video.file_size}")
    print(f"  video_codec: {new_video.video_codec}")
    print()
    
    # 创建索引字典
    existing_by_fingerprint = {old_video.file_fingerprint: old_video}
    existing_by_video_code = {old_video.video_code: [old_video]}
    existing_by_path = {old_video.file_path: old_video}
    
    print("索引字典:")
    print(f"  existing_by_fingerprint: {list(existing_by_fingerprint.keys())}")
    print(f"  existing_by_video_code: {list(existing_by_video_code.keys())}")
    print(f"  existing_by_path: {list(existing_by_path.keys())}")
    print()
    
    # 测试merge action决策
    action = merge_manager._determine_merge_action(
        new_video, 
        existing_by_fingerprint, 
        existing_by_video_code, 
        existing_by_path
    )
    
    print("Merge Action 结果:")
    if action:
        print(f"  action_type: {action.action_type}")
        print(f"  reason: {action.reason}")
        print(f"  video_info: {action.video_info.file_path if action.video_info else None}")
        print(f"  target_info: {action.target_info.file_path if action.target_info else None}")
    else:
        print("  No action determined")
    print()
    
    # 测试替换检测逻辑
    is_replacement = merge_manager._is_replacement_scenario(new_video, old_video)
    print(f"替换检测结果: {is_replacement}")
    
    # 测试相似度计算
    similarity = merge_manager._calculate_similarity(new_video, old_video)
    print(f"相似度: {similarity}")

if __name__ == "__main__":
    debug_merge_action()