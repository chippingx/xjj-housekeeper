#!/usr/bin/env python3
"""
调试完整的merge流程
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.smart_merge_manager import SmartMergeManager
from tools.video_info_collector.metadata import VideoInfo

def create_video_info(file_path, video_code, file_fingerprint, filename=None):
    """创建VideoInfo对象"""
    video_info = VideoInfo(file_path)
    video_info.video_code = video_code
    video_info.file_fingerprint = file_fingerprint
    video_info.filename = filename or os.path.basename(file_path)
    video_info.width = 1920
    video_info.height = 1080
    video_info.file_status = "present"
    return video_info

def main():
    # 创建临时数据库
    db_path = "/tmp/debug_merge.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    storage = SQLiteStorage(db_path)
    
    # 创建旧视频记录
    old_video = create_video_info(
        "/path/to/old/video.mp4",
        "ABC-123",
        "old_fingerprint_123",
        "old_video.mp4"
    )
    
    # 插入旧视频到数据库
    old_video_id = storage.insert_video_info(old_video)
    print(f"插入旧视频，ID: {old_video_id}")
    
    # 创建新视频记录（相同video_code，不同fingerprint）
    new_video = create_video_info(
        "/path/to/new/video.mp4",
        "ABC-123",
        "new_fingerprint_456",
        "new_video.mp4"
    )
    
    print(f"\n旧视频信息:")
    print(f"  路径: {old_video.file_path}")
    print(f"  视频代码: {old_video.video_code}")
    print(f"  文件指纹: {old_video.file_fingerprint}")
    print(f"  文件状态: {old_video.file_status}")
    
    print(f"\n新视频信息:")
    print(f"  路径: {new_video.file_path}")
    print(f"  视频代码: {new_video.video_code}")
    print(f"  文件指纹: {new_video.file_fingerprint}")
    print(f"  文件状态: {new_video.file_status}")
    
    # 获取现有视频数据
    existing_videos = storage.get_all_video_infos()
    print(f"\n数据库中现有视频数量: {len(existing_videos)}")
    
    # 创建智能合并管理器
    merge_manager = SmartMergeManager(storage)
    
    # 分析合并候选项
    print(f"\n开始分析合并候选项...")
    merge_results = merge_manager.analyze_merge_candidates([new_video], existing_videos)
    
    print(f"\n合并分析结果:")
    for action_type, actions in merge_results.items():
        print(f"  {action_type}: {len(actions)} 个动作")
        for action in actions:
            print(f"    - 动作: {action.action_type}")
            print(f"      新视频: {action.video_info.file_path}")
            print(f"      新视频代码: {action.video_info.video_code}")
            print(f"      新视频指纹: {action.video_info.file_fingerprint}")
            if action.target_info:
                print(f"      目标视频: {action.target_info.file_path}")
                print(f"      目标视频代码: {action.target_info.video_code}")
                print(f"      目标视频指纹: {action.target_info.file_fingerprint}")
                print(f"      目标视频ID: {getattr(action.target_info, 'id', 'N/A')}")
            print(f"      原因: {action.reason}")
    
    # 执行合并计划
    print(f"\n执行合并计划...")
    try:
        merge_stats = merge_manager.execute_merge_plan(merge_results, scan_id=1)
    except Exception as e:
        print(f"执行合并计划时出错: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n合并统计:")
    for key, value in merge_stats.items():
        print(f"  {key}: {value}")
    
    # 检查merge history
    print(f"\n检查merge history...")
    merge_history = storage.get_merge_history(limit=10)
    print(f"Merge history记录数: {len(merge_history)}")
    for event in merge_history:
        print(f"  事件类型: {event['event_type']}")
        print(f"  视频代码: {event.get('video_code', 'N/A')}")
        print(f"  原因: {event.get('reason', 'N/A')}")
        print(f"  旧路径: {event.get('old_path', 'N/A')}")
        print(f"  新路径: {event.get('new_path', 'N/A')}")
        print(f"  ---")
    
    storage.close()
    print(f"\n调试完成，数据库文件: {db_path}")

if __name__ == "__main__":
    main()