#!/usr/bin/env python3
"""
集成测试脚本

测试所有新功能的集成和工作流程
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.enhanced_scanner import EnhancedVideoScanner
from tools.video_info_collector.fingerprint_manager import FingerprintManager
from tools.video_info_collector.file_status_manager import FileStatusManager, FileStatus
from tools.video_info_collector.smart_merge_manager import SmartMergeManager
from tools.video_info_collector.metadata import VideoInfo


def create_test_video_files(test_dir: str) -> list:
    """创建测试视频文件"""
    test_files = []
    
    # 创建一些测试文件（空文件，但有正确的扩展名）
    test_videos = [
        "test_video_001.mp4",
        "movie_ABC123.mkv", 
        "series_S01E01_XYZ789.avi",
        "documentary_DEF456.mov",
        "duplicate_GHI789.mp4"  # 这个会用来测试重复检测
    ]
    
    for video_name in test_videos:
        file_path = os.path.join(test_dir, video_name)
        # 创建一个有一定大小的文件（避免被过滤掉）
        with open(file_path, 'wb') as f:
            f.write(b'0' * 50000)  # 50KB的测试数据
        test_files.append(file_path)
    
    # 创建子目录和更多文件
    sub_dir = os.path.join(test_dir, "subfolder")
    os.makedirs(sub_dir, exist_ok=True)
    
    sub_videos = [
        "sub_video_JKL012.mp4",
        "sub_movie_MNO345.mkv"
    ]
    
    for video_name in sub_videos:
        file_path = os.path.join(sub_dir, video_name)
        with open(file_path, 'wb') as f:
            f.write(b'1' * 60000)  # 60KB的测试数据
        test_files.append(file_path)
    
    return test_files


def test_fingerprint_manager():
    """测试指纹管理器"""
    print("\n=== 测试指纹管理器 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试文件
        test_files = create_test_video_files(temp_dir)
        
        # 创建VideoInfo对象
        videos = []
        for file_path in test_files:
            video = VideoInfo(file_path)
            video.file_size = os.path.getsize(file_path)
            videos.append(video)
        
        # 测试指纹管理器
        fingerprint_manager = FingerprintManager()
        
        # 批量生成指纹
        fingerprints = fingerprint_manager.batch_generate_fingerprints(videos)
        print(f"生成了 {len(fingerprints)} 个指纹")
        
        # 检测重复
        duplicates = fingerprint_manager.detect_duplicates(videos)
        print(f"检测到 {len(duplicates)} 组重复文件")
        
        # 获取统计信息
        stats = fingerprint_manager.get_fingerprint_statistics(videos)
        print(f"指纹统计: {stats}")
        
        print("✓ 指纹管理器测试通过")


def test_file_status_manager():
    """测试文件状态管理器"""
    print("\n=== 测试文件状态管理器 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试文件
        test_files = create_test_video_files(temp_dir)
        
        # 创建VideoInfo对象
        videos = []
        for file_path in test_files:
            video = VideoInfo(file_path)
            videos.append(video)
        
        # 测试状态管理器
        status_manager = FileStatusManager()
        
        # 批量检查状态
        status_results = status_manager.batch_check_status(videos)
        print(f"状态检查结果: {status_results}")
        
        # 标记一些文件为忽略
        ignore_count = status_manager.mark_as_ignore(videos[:2], "测试忽略")
        print(f"标记了 {ignore_count} 个文件为忽略")
        
        # 获取统计信息
        stats = status_manager.get_status_statistics(videos)
        print(f"状态统计: {stats}")
        
        # 删除一个文件来测试丢失检测
        os.remove(test_files[-1])
        
        # 检测不一致
        inconsistencies = status_manager.detect_status_inconsistencies(videos)
        print(f"检测到 {len(inconsistencies)} 个状态不一致")
        
        # 自动修复
        fix_results = status_manager.auto_fix_inconsistencies(videos)
        print(f"修复结果: {fix_results}")
        
        print("✓ 文件状态管理器测试通过")


def test_smart_merge_manager():
    """测试智能合并管理器"""
    print("\n=== 测试智能合并管理器 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建数据库
        db_path = os.path.join(temp_dir, "test.db")
        storage = SQLiteStorage(db_path)
        
        # 创建测试文件
        test_files = create_test_video_files(temp_dir)
        
        # 创建新视频和现有视频
        new_videos = []
        existing_videos = []
        
        for i, file_path in enumerate(test_files):
            video = VideoInfo(file_path)
            video.file_size = os.path.getsize(file_path)
            
            if i < 3:  # 前3个作为新视频
                new_videos.append(video)
            else:  # 后面的作为现有视频
                existing_videos.append(video)
        
        # 测试合并管理器
        merge_manager = SmartMergeManager(storage)
        
        # 分析合并候选项
        merge_results = merge_manager.analyze_merge_candidates(new_videos, existing_videos)
        print(f"合并分析结果: {merge_results}")
        
        # 创建合并报告
        report = merge_manager.create_merge_report(merge_results)
        print(f"合并报告摘要: {report['summary']}")
        
        # 执行合并计划
        merge_stats = merge_manager.execute_merge_plan(merge_results)
        print(f"合并执行统计: {merge_stats}")
        
        storage.close()
        print("✓ 智能合并管理器测试通过")


def test_enhanced_scanner():
    """测试增强扫描器"""
    print("\n=== 测试增强扫描器 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建数据库
        db_path = os.path.join(temp_dir, "test.db")
        storage = SQLiteStorage(db_path)
        
        # 创建测试文件
        test_files = create_test_video_files(temp_dir)
        print(f"创建了 {len(test_files)} 个测试文件")
        
        # 创建增强扫描器
        scanner = EnhancedVideoScanner(storage)
        
        # 执行完整扫描
        print("执行完整扫描...")
        scan_report = scanner.full_scan(temp_dir, recursive=True)
        print(f"扫描报告: {scan_report['file_statistics']}")
        print(f"合并统计: {scan_report['merge_statistics']}")
        
        # 执行验证扫描
        print("执行验证扫描...")
        verify_report = scanner.verify_scan(check_integrity=True)
        print(f"验证结果: {verify_report['status_check']}")
        
        # 删除一个文件，然后再次验证
        if test_files:
            os.remove(test_files[0])
            print("删除一个文件后重新验证...")
            verify_report2 = scanner.verify_scan()
            print(f"第二次验证结果: {verify_report2['status_check']}")
        
        # 获取扫描统计
        stats = scanner.get_scan_statistics()
        print(f"扫描统计: {stats['current_session']}")
        
        storage.close()
        print("✓ 增强扫描器测试通过")


def test_database_integration():
    """测试数据库集成"""
    print("\n=== 测试数据库集成 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建数据库
        db_path = os.path.join(temp_dir, "test.db")
        storage = SQLiteStorage(db_path)
        
        # 测试新表是否创建成功
        cursor = storage.connection.cursor()
        
        # 检查video_master_list表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_master_list'")
        assert cursor.fetchone() is not None, "video_master_list表未创建"
        
        # 检查merge_history表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='merge_history'")
        assert cursor.fetchone() is not None, "merge_history表未创建"
        
        # 检查video_info表的新列
        cursor.execute("PRAGMA table_info(video_info)")
        columns = [row[1] for row in cursor.fetchall()]
        required_columns = ['video_code', 'file_fingerprint', 'file_status', 'last_scan_time', 'last_merge_time']
        for col in required_columns:
            assert col in columns, f"video_info表缺少列: {col}"
        
        # 测试master list操作
        storage.upsert_master_list_entry("TEST001", "fingerprint123")
        result = storage.get_master_list_by_code("TEST001")
        assert result is not None, "master list插入/查询失败"
        
        # 测试merge history操作
        storage.add_merge_event("insert_new", "TEST001", None, "/test/path.mp4", "测试事件", "scan_session_1")
        history = storage.get_merge_history_by_video_code("TEST001")
        assert len(history) > 0, "merge history插入/查询失败"
        
        storage.close()
        print("✓ 数据库集成测试通过")


def main():
    """主测试函数"""
    print("开始集成测试...")
    
    try:
        # 运行所有测试
        test_fingerprint_manager()
        test_file_status_manager()
        test_smart_merge_manager()
        test_enhanced_scanner()
        test_database_integration()
        
        print("\n🎉 所有集成测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)