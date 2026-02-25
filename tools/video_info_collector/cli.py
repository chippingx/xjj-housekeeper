#!/usr/bin/env python3
"""
Video Info Collector CLI
符合设计文档的两阶段工作流实现
"""

import argparse
import sys
import os
import yaml
import signal
import logging
from datetime import datetime
from pathlib import Path

from .scanner import VideoFileScanner
from .metadata import VideoMetadataExtractor
from .csv_writer import CSVWriter
from .sqlite_storage import SQLiteStorage
from .error_handler import (
    ErrorHandler, 
    create_error_handler,
    VideoInfoCollectorError,
    FileNotFoundError as VICFileNotFoundError,
    PermissionError as VICPermissionError,
    DatabaseError,
    MetadataExtractionError
)

# 全局变量
_error_handler = None
_interrupted = False
_current_operation = None


def setup_signal_handlers():
    """设置信号处理器"""
    def signal_handler(signum, frame):
        global _interrupted, _current_operation
        _interrupted = True
        
        print("\n")
        print("🛑 检测到中断信号 (Ctrl+C)")
        
        if _current_operation:
            print(f"正在优雅地停止当前操作: {_current_operation}")
        else:
            print("正在优雅地停止程序...")
        
        print("请稍等，正在清理资源...")
        
        # 给程序一些时间来清理资源
        import time
        time.sleep(0.5)
        
        print("✅ 程序已安全退出")
        sys.exit(130)  # 130 是 SIGINT 的标准退出码
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)


def check_interruption():
    """检查是否被中断"""
    global _interrupted
    if _interrupted:
        print("\n操作被用户中断")
        sys.exit(130)


def set_current_operation(operation: str):
    """设置当前操作描述"""
    global _current_operation
    _current_operation = operation


def setup_logging(debug_mode: bool = False):
    """设置日志记录"""
    if debug_mode:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stderr)
            ]
        )
    else:
        logging.basicConfig(level=logging.WARNING)


def load_config():
    """加载配置文件"""
    # 使用稳定的路径管理工具获取配置文件路径
    from ..path_utils import get_config_path
    config_path = get_config_path("tools/video_info_collector/config.yaml", calling_file=__file__)
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # 如果配置文件不存在，返回默认配置
        return {
            'output_paths': {
                'base_dir': 'output/video_info_collector',
                'csv_dir': 'csv',
                'database_dir': 'database',
                'default_database': 'video_database.db',
                'temp_csv_prefix': 'temp_video_info_'
            }
        }


def get_default_paths():
    """获取默认的输出路径"""
    config = load_config()
    output_config = config.get('output_paths', {})
    
    base_dir = output_config.get('base_dir', 'output/video_info_collector')
    csv_dir = output_config.get('csv_dir', 'csv')
    database_dir = output_config.get('database_dir', 'database')
    default_database = output_config.get('default_database', 'video_database.db')
    
    from ..path_utils import resolve_path
    base_dir_path = resolve_path(base_dir, calling_file=__file__)

    # 确保目录存在
    csv_path = base_dir_path / csv_dir
    database_path = base_dir_path / database_dir
    csv_path.mkdir(parents=True, exist_ok=True)
    database_path.mkdir(parents=True, exist_ok=True)
    
    return {
        'csv_dir': str(csv_path),
        'database_dir': str(database_path),
        'default_database': str(database_path / default_database),
        'temp_csv_prefix': output_config.get('temp_csv_prefix', 'temp_video_info_')
    }


def format_file_size(size_bytes):
    """格式化文件大小"""
    # 如果已经是格式化的字符串，直接返回
    if isinstance(size_bytes, str):
        return size_bytes
    
    # 如果是None或0，返回N/A
    if not size_bytes:
        return 'N/A'
    
    # 转换为整数（防止浮点数输入）
    try:
        size_bytes = int(size_bytes)
    except (ValueError, TypeError):
        return 'N/A'
    
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f}MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f}GB"


def format_duration(seconds):
    """格式化时长"""
    if seconds is None:
        return "未知"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def generate_directory_based_filename(directory_path, timestamp, prefix="temp_video_info_"):
    """
    基于目录路径生成CSV文件名，去掉volumes层
    
    Args:
        directory_path: 扫描的目录路径
        timestamp: 时间戳字符串
        prefix: 文件名前缀（用于向后兼容）
        
    Returns:
        生成的文件名
        
    Examples:
        /Volumes/ws2/media/videos/ -> ws2_media_videos_20241027_181559.csv
        /path/to/videos/Movies/ -> path_to_videos_Movies_20241027_181559.csv
        /media/storage/videos/ -> media_storage_videos_20241027_181559.csv
    """
    path = Path(directory_path).resolve()
    parts = path.parts
    
    # 过滤掉不需要的路径部分
    filtered_parts = []
    for part in parts:
        # 跳过根目录、Volumes层和空字符串
        if part in ('/', '', 'Volumes'):
            continue
        # 跳过以点开头的隐藏目录
        if part.startswith('.'):
            continue
        filtered_parts.append(part)
    
    if not filtered_parts:
        # 如果没有有效的路径部分，使用默认前缀
        return f"{prefix}{timestamp}.csv"
    
    # 将路径部分连接为文件名，限制长度避免文件名过长
    max_parts = 4  # 最多使用4个路径部分
    if len(filtered_parts) > max_parts:
        filtered_parts = filtered_parts[:max_parts]
    
    # 清理文件名中的特殊字符
    clean_parts = []
    for part in filtered_parts:
        # 替换特殊字符为下划线，保留字母、数字和中文字符
        clean_part = ''.join(c if c.isalnum() or '\u4e00' <= c <= '\u9fff' else '_' for c in part)
        # 移除连续的下划线
        clean_part = '_'.join(filter(None, clean_part.split('_')))
        if clean_part:
            clean_parts.append(clean_part)
    
    if not clean_parts:
        return f"{prefix}{timestamp}.csv"
    
    filename_base = '_'.join(clean_parts)
    return f"{filename_base}_{timestamp}.csv"


def scan_command(args):
    """扫描目录并根据输出格式生成文件"""
    global _error_handler
    
    # 确保错误处理器已初始化
    if _error_handler is None:
        _error_handler = create_error_handler()
    
    set_current_operation("目录扫描")
    
    # 验证目录路径
    if not _error_handler.validate_file_path(args.directory, "目录", must_exist=True):
        return 1
    
    directory = Path(args.directory)
    
    # 获取默认路径配置
    default_paths = get_default_paths()
    
    # 确定输出文件和格式
    output_format = getattr(args, 'output_format', 'csv')
    
    if args.output:
        # 用户指定了输出文件
        output_file = args.output
        # 从文件扩展名推断格式
        if output_file.endswith('.db') or output_file.endswith('.sqlite'):
            output_format = 'sqlite'
        elif output_file.endswith('.csv'):
            output_format = 'csv'
    else:
        # 生成默认输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_format == 'sqlite':
            output_filename = f"video_info_{timestamp}.db"
            output_file = str(Path(default_paths['database_dir']) / output_filename)
        else:  # csv 或临时文件
            if args.temp_file:
                output_file = args.temp_file
            else:
                # 使用基于目录路径的文件命名
                temp_filename = generate_directory_based_filename(
                    directory, timestamp, default_paths['temp_csv_prefix']
                )
                output_file = str(Path(default_paths['csv_dir']) / temp_filename)
    
    print(f"正在扫描目录: {directory}")
    print(f"输出格式: {output_format}")
    print(f"输出文件: {output_file}")
    
    if _error_handler.verbose:
        print(f"🔧 递归扫描: {'是' if args.recursive else '否'}")
        print(f"🔧 预览模式: {'是' if args.dry_run else '否'}")
        if args.tags:
            print(f"🏷️  标签: {args.tags}")
        if args.path:
            print(f"📂 逻辑路径: {args.path}")
        print(f"🔧 文件扩展名: {args.extensions}")
    print()
    
    try:
        # 初始化扫描器和元数据提取器
        set_current_operation("初始化扫描器")
        scanner = VideoFileScanner()
        metadata_extractor = VideoMetadataExtractor()
        
        # 扫描视频文件
        set_current_operation("扫描视频文件")
        if _error_handler.verbose:
            print("🔍 开始扫描视频文件...")
        
        video_files = scanner.scan_directory(str(directory), recursive=args.recursive)
        check_interruption()
        
        if not video_files:
            print(f"ℹ️  在目录 {directory} 中未找到视频文件")
            if _error_handler.verbose:
                print("💡 建议:")
                print(f"  • 检查目录路径是否正确: {directory}")
                print(f"  • 检查文件扩展名过滤: {args.extensions}")
                print(f"  • 确认目录中包含视频文件")
            return 0
        
        print(f"✅ 找到 {len(video_files)} 个视频文件，开始提取信息...")
        if _error_handler.verbose:
            print("📋 文件列表:")
            for i, file_path in enumerate(video_files[:5], 1):  # 只显示前5个
                print(f"  {i}. {os.path.basename(file_path)}")
            if len(video_files) > 5:
                print(f"  ... 还有 {len(video_files) - 5} 个文件")
        
        # 预览模式
        if args.dry_run:
            print("\n🔍 预览模式 - 不写入文件:")
            for i, video_file in enumerate(video_files[:5], 1):
                file_path = Path(video_file)
                try:
                    file_size = file_path.stat().st_size
                    print(f"  {i}. {file_path.name} ({format_file_size(file_size)})")
                except OSError as e:
                    print(f"  {i}. {file_path.name} (无法获取文件大小: {e})")
            if len(video_files) > 5:
                print(f"  ... 还有 {len(video_files) - 5} 个文件")
            return 0
        
        # 提取视频信息
        set_current_operation("提取视频元数据")
        video_infos = []
        failed_files = []
        
        if _error_handler.verbose:
            print("\n🔄 开始提取视频元数据...")
        
        for i, video_file in enumerate(video_files, 1):
            check_interruption()
            
            if _error_handler.debug_mode:
                print(f"🔍 处理 {i}/{len(video_files)}: {video_file}")
            else:
                print(f"📹 处理 {i}/{len(video_files)}: {Path(video_file).name}")
            
            try:
                video_info = metadata_extractor.extract_metadata(video_file)
                # 添加标签和逻辑路径信息
                if args.tags:
                    # 使用分号分隔标签
                    video_info.tags = [tag.strip() for tag in args.tags.split(';')]
                else:
                    # 如果没有设置tags，使用目录名作为默认值
                    directory_name = Path(video_file).parent.name
                    video_info.tags = [directory_name] if directory_name else []
                if args.path:
                    video_info.logical_path = args.path
                video_infos.append(video_info)
                
                if _error_handler.verbose:
                    print(f"  ✅ 成功提取元数据")
                    print(f"     • 分辨率: {getattr(video_info, 'width', 'N/A')}x{getattr(video_info, 'height', 'N/A')}")
                    print(f"     • 时长: {format_duration(getattr(video_info, 'duration', 0))}")
                    print(f"     • 文件大小: {format_file_size(getattr(video_info, 'file_size', 0))}")
                    
            except FileNotFoundError:
                _error_handler.handle_file_not_found(video_file, "视频文件")
                failed_files.append(video_file)
                continue
            except PermissionError:
                _error_handler.handle_permission_error(video_file, "读取")
                failed_files.append(video_file)
                continue
            except Exception as e:
                _error_handler.handle_metadata_error(video_file, str(e))
                failed_files.append(video_file)
                continue
        
        # 检查是否有成功处理的文件
        if not video_infos:
            print("\n❌ 没有成功处理任何视频文件")
            if failed_files:
                print(f"失败的文件数量: {len(failed_files)}")
            return 1
        
        # 根据输出格式写入文件
        set_current_operation("写入文件")
        if output_format == 'sqlite':
            # 验证数据库路径
            if not _error_handler.validate_database_path(output_file):
                return 1
            
            try:
                # 直接写入SQLite数据库
                storage = SQLiteStorage(output_file)
                success_count = 0
                db_failed_count = 0
                
                for video_info in video_infos:
                    check_interruption()
                    try:
                        video_id = storage.insert_video_info(video_info)
                        if video_id:
                            success_count += 1
                        else:
                            db_failed_count += 1
                    except Exception as e:
                        _error_handler.handle_database_error(f"写入视频信息失败: {e}", output_file, "插入记录")
                        db_failed_count += 1
                
                # 添加扫描历史记录
                try:
                    if args.tags:
                        # 使用分号分隔标签
                        tags_list = [tag.strip() for tag in args.tags.split(';')]
                    else:
                        tags_list = None
                    storage.add_scan_history(
                        scan_path=args.directory,
                        files_found=len(video_files),
                        files_processed=success_count,
                        tags=tags_list,
                        logical_path=args.path
                    )
                except Exception as e:
                    _error_handler.handle_database_error(f"记录扫描历史失败: {e}", output_file, "添加历史记录")
                
                storage.close()
                
                print(f"\n✅ 扫描完成!")
                print(f"📊 处理结果:")
                print(f"  • 发现文件: {len(video_files)}")
                print(f"  • 成功处理: {len(video_infos)}")
                print(f"  • 写入数据库: {success_count}")
                if failed_files:
                    print(f"  • 处理失败: {len(failed_files)}")
                if db_failed_count > 0:
                    print(f"  • 数据库写入失败: {db_failed_count}")
                print(f"📁 SQLite数据库: {output_file}")
                
            except Exception as e:
                _error_handler.handle_database_error(f"数据库操作失败: {e}", output_file)
                return 1
        else:
            try:
                # 写入CSV文件（临时文件或最终文件）
                csv_writer = CSVWriter()
                csv_writer.write_video_infos(video_infos, output_file)
                
                print(f"\n✅ 扫描完成!")
                print(f"📊 处理结果:")
                print(f"  • 发现文件: {len(video_files)}")
                print(f"  • 成功处理: {len(video_infos)}")
                if failed_files:
                    print(f"  • 处理失败: {len(failed_files)}")
                print(f"📁 CSV文件: {output_file}")
                
                # 如果是临时文件，提示合并操作
                if not args.output and not args.temp_file:
                    print(f"\n💡 下一步操作:")
                    print(f"  请用Excel/Numbers/浏览器查看临时文件内容，确认无误后执行合并操作。")
                    print(f"\n📝 合并命令:")
                    print(f"  python -m tools.video_info_collector --merge {output_file}")
                    
            except Exception as e:
                _error_handler.handle_generic_error(e, "写入CSV文件")
                return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 操作被用户中断")
        return 130
    except Exception as e:
        _error_handler.handle_generic_error(e, "扫描操作")
        return 1


def merge_command(args):
    """合并CSV文件到SQLite数据库"""
    global _error_handler
    
    # 确保错误处理器已初始化
    if _error_handler is None:
        _error_handler = create_error_handler()
    
    set_current_operation("合并CSV文件到数据库")
    
    csv_file = args.csv_file
    
    # 验证CSV文件
    if not _error_handler.validate_file_path(csv_file, "CSV文件", must_exist=True):
        return 1
    
    # 验证数据库路径（合并操作允许数据库文件不存在，会自动创建）
    if not _error_handler.validate_database_path(args.database, must_exist=False):
        return 1
    
    print(f"📁 正在合并临时文件: {csv_file}")
    print(f"🗄️  目标数据库: {args.database}")
    print(f"🔄 重复策略: {args.duplicate_strategy}")
    
    try:
        set_current_operation("连接数据库")
        # 初始化存储
        storage = SQLiteStorage(args.database)
        
        set_current_operation("生成CSV文件指纹")
        # 生成CSV文件指纹
        print("正在生成CSV文件指纹...")
        csv_fingerprint = storage.get_csv_fingerprint(csv_file)
        print(f"CSV文件指纹: {csv_fingerprint[:16]}...")
        check_interruption()
        
        # 检查是否已经合并过
        if storage.check_csv_already_merged(csv_fingerprint):
            print(f"⚠️  警告: 该CSV文件已经被合并过!")
            print(f"文件指纹: {csv_fingerprint}")
            
            # 询问用户是否继续
            if hasattr(args, 'force') and args.force:
                print("使用 --force 参数，强制重新合并...")
            else:
                try:
                    response = input("是否要强制重新合并? (y/N): ").strip().lower()
                    if response not in ['y', 'yes']:
                        print("取消合并操作")
                        storage.close()
                        return 0
                except (EOFError, KeyboardInterrupt):
                    print("\n操作被用户中断")
                    storage.close()
                    return 130
        
        set_current_operation("分析CSV文件")
        # 从文件名提取扫描信息
        scan_info = storage.extract_scan_info_from_csv_filename(csv_file)
        print(f"推断的原始扫描路径: {scan_info['original_scan_path']}")
        print(f"扫描时间戳: {scan_info['timestamp']}")
        
        # 统计CSV文件中的记录数
        import csv as csv_module
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_reader = csv_module.reader(f)
            next(csv_reader)  # 跳过标题行
            total_records = sum(1 for _ in csv_reader)
        
        print(f"CSV文件包含 {total_records} 条记录")
        check_interruption()
        
        # 执行智能合并操作
        set_current_operation("智能合并CSV数据")
        print("开始智能合并数据...")
        
        # 导入SmartMergeManager
        from .smart_merge_manager import SmartMergeManager
        
        # 从CSV文件加载视频信息
        new_videos = storage.load_videos_from_csv(args.csv_file)
        if not new_videos:
            print("❌ CSV文件中没有有效的视频数据")
            storage.close()
            return 1
        
        # 获取现有视频数据
        existing_videos = storage.get_all_video_infos()
        
        # 创建智能合并管理器
        merge_manager = SmartMergeManager(storage)
        
        # 分析合并候选项
        merge_results = merge_manager.analyze_merge_candidates(
            new_videos,
            existing_videos,
            scan_info['original_scan_path']
        )
        
        # 记录合并历史（创建scan记录）
        set_current_operation("记录合并历史")
        history_id = storage.add_csv_merge_history(
            csv_file_path=csv_file,
            files_found=total_records,
            files_processed=0,  # 将在执行后更新
            csv_fingerprint=csv_fingerprint,
            original_scan_path=scan_info['original_scan_path'],
            tags=None,  # CSV合并操作通常不涉及特定标签
            logical_path=scan_info['original_scan_path']
        )
        
        # 执行合并计划
        set_current_operation("执行合并计划")
        merge_stats = merge_manager.execute_merge_plan(merge_results, history_id)
        success_count = merge_stats['inserted'] + merge_stats['updated']
        
        # 为跳过的重复视频记录merge_history事件
        total_actions = sum(len(actions) for actions in merge_results.values())
        skipped_count = len(new_videos) - total_actions
        
        if skipped_count > 0:
            # 为跳过的视频记录merge事件
            processed_videos = set()
            for action_list in merge_results.values():
                for action in action_list:
                    processed_videos.add(action.video_info.file_path)
            
            for new_video in new_videos:
                if new_video.file_path not in processed_videos:
                    # 这是一个被跳过的重复视频，记录merge事件
                    storage.add_merge_event(
                        'skip_duplicate',
                        None, 
                        new_video.file_path,
                        history_id
                    )
        
        # 更新合并历史记录的处理数量
        storage.update_csv_merge_history_processed_count(history_id, success_count)
        
        check_interruption()
        
        storage.close()
        
        print(f"\n✅ 合并完成!")
        print(f"📊 处理结果:")
        print(f"  • CSV记录数: {total_records}")
        print(f"  • 成功导入: {success_count}")
        if success_count < total_records:
            print(f"  • 跳过记录: {total_records - success_count} (可能是重复记录)")
        print(f"📁 数据库文件: {args.database}")
        print(f"📝 合并历史记录ID: {history_id}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 合并操作被用户中断")
        return 130
    except Exception as e:
        _error_handler.handle_database_error(f"合并操作失败: {e}", args.database, "导入CSV")
        return 1


def export_command(args):
    """从SQLite数据库导出到CSV"""
    global _error_handler
    
    # 确保错误处理器已初始化
    if _error_handler is None:
        _error_handler = create_error_handler()
    
    set_current_operation("导出数据库到CSV")
    
    # 验证数据库路径（导出操作需要数据库文件存在）
    if not _error_handler.validate_database_path(args.database, must_exist=True):
        return 1
    
    # 如果没有指定输出文件，使用默认路径
    if not args.output:
        default_paths = get_default_paths()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"exported_videos_{timestamp}.csv"
        args.output = str(Path(default_paths['csv_dir']) / output_filename)
    
    print(f"🗄️  数据库文件: {args.database}")
    print(f"📁 输出文件: {args.output}")
    
    try:
        set_current_operation("连接数据库")
        # 再次检查数据库文件是否存在（防止SQLite自动创建空数据库）
        if not os.path.exists(args.database):
            print(f"❌ 数据库文件不存在: {args.database}")
            return 1
        storage = SQLiteStorage(args.database)
        
        set_current_operation("导出CSV文件")
        # 使用SQLiteStorage的export_to_csv方法
        success = storage.export_to_csv(args.output)
        check_interruption()
        
        if success:
            # 获取记录数量
            total_count = storage.get_total_count()
            storage.close()
            print(f"\n✅ 导出完成!")
            print(f"📊 处理结果:")
            print(f"  • 导出记录数: {total_count}")
            print(f"📁 输出文件: {args.output}")
            return 0
        else:
            storage.close()
            print("\n❌ 导出失败")
            return 1
        
    except KeyboardInterrupt:
        print("\n🛑 导出操作被用户中断")
        return 130
    except Exception as e:
        _error_handler.handle_database_error(f"导出操作失败: {e}", args.database, "导出CSV")
        return 1


def export_simple_command(args):
    """从SQLite数据库简化导出（仅包含filename、filesize、logical_path）"""
    global _error_handler
    
    # 确保错误处理器已初始化
    if _error_handler is None:
        _error_handler = create_error_handler()
    
    set_current_operation("导出简化视频信息")
    
    # 验证数据库路径
    if not _error_handler.validate_database_path(args.database):
        return 1
    
    # 如果没有指定输出文件，使用默认路径
    if not args.output:
        default_paths = get_default_paths()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"simple_export_{timestamp}.txt"
        args.output = str(Path(default_paths['csv_dir']) / output_filename)
    
    print(f"🗄️  数据库文件: {args.database}")
    print(f"📁 输出文件: {args.output}")
    print("📋 输出格式: filename filesize logical_path")
    
    try:
        set_current_operation("连接数据库")
        # 再次检查数据库文件是否存在（防止SQLite自动创建空数据库）
        if not os.path.exists(args.database):
            print(f"❌ 数据库文件不存在: {args.database}")
            return 1
        storage = SQLiteStorage(args.database)
        
        set_current_operation("导出简化信息")
        # 使用SQLiteStorage的export_simple_format方法
        success = storage.export_simple_format(args.output)
        check_interruption()
        
        if success:
            # 获取记录数量
            total_count = storage.get_total_count()
            storage.close()
            print(f"\n✅ 简化导出完成!")
            print(f"📊 处理结果:")
            print(f"  • 导出记录数: {total_count}")
            print(f"📁 输出文件: {args.output}")
            return 0
        else:
            storage.close()
            print("\n❌ 简化导出失败")
            return 1
        
    except KeyboardInterrupt:
        print("\n🛑 导出操作被用户中断")
        return 130
    except Exception as e:
        _error_handler.handle_database_error(f"简化导出失败: {e}", args.database, "导出简化信息")
        return 1


def search_video_code_command(args):
    """视频code查询命令"""
    global _error_handler
    
    # 确保错误处理器已初始化
    if _error_handler is None:
        _error_handler = create_error_handler()
    
    set_current_operation("视频code查询")
    
    # 解析输入的video_codes，支持空格和逗号分隔
    video_codes_input = args.search_video_codes.strip()
    if not video_codes_input:
        print("❌ 错误: 请提供要查询的视频code")
        return 1
    
    # 分割video_codes，支持逗号和空格分隔
    import re
    video_codes = re.split(r'[,\s]+', video_codes_input)
    # 去除空字符串和前后空格
    video_codes = [video_code.strip() for video_code in video_codes if video_code.strip()]
    
    if not video_codes:
        print("❌ 错误: 没有找到有效的视频code")
        return 1
    
    print(f"🔍 正在查询视频code: {', '.join(video_codes)}")
    
    try:
        # 连接数据库
        if not os.path.exists(args.database):
            print(f"❌ 错误: 数据库文件不存在: {args.database}")
            print("💡 提示: 请先运行扫描命令生成数据库，或使用 --init-db 初始化数据库")
            return 1
        
        storage = SQLiteStorage(args.database)
        
        # 查询视频信息
        results = storage.search_videos_by_video_codes(video_codes)
        
        if not results:
            print("❌ 没有找到匹配的视频")
            print(f"🔍 查询的video_codes: {', '.join(video_codes)}")
            storage.close()
            return 0
        
        # 显示查询结果
        print(f"\n✅ 找到 {len(results)} 个匹配的视频:")
        print("-" * 80)
        print(f"{'视频Code':<20} {'文件大小':<15} {'逻辑路径':<30}")
        print("-" * 80)
        
        for result in results:
            video_code = result['video_code']
            file_size = format_file_size(result['file_size']) if result['file_size'] else 'N/A'
            logical_path = result['logical_path'] or 'N/A'
            
            print(f"{video_code:<20} {file_size:<15} {logical_path:<30}")
        
        storage.close()
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 视频code查询被用户中断")
        return 130
    except Exception as e:
        _error_handler.handle_generic_error(f"视频code查询失败: {e}", "视频code查询")
        return 1


def init_db_command(args):
    """初始化/重置数据库"""
    global _error_handler
    
    # 确保错误处理器已初始化
    if _error_handler is None:
        _error_handler = create_error_handler()
    
    set_current_operation("初始化数据库")
    
    db_path = args.database
    
    # 检查数据库文件是否存在
    if os.path.exists(db_path):
        # 询问用户确认
        print(f"⚠️  数据库文件已存在: {db_path}")
        print("此操作将删除所有现有数据！")
        
        # 在非交互模式下，我们需要用户明确确认
        try:
            confirm = input("确认要重置数据库吗？(输入 'yes' 确认): ").strip().lower()
            if confirm != 'yes':
                print("操作已取消")
                return 0
        except (EOFError, KeyboardInterrupt):
            print("\n操作已取消")
            return 0
        
        # 删除现有数据库文件
        try:
            Path(db_path).unlink()
            print(f"已删除现有数据库文件: {db_path}")
        except Exception as e:
            print(f"删除数据库文件失败: {e}")
            return 1
    
    # 创建新的数据库
    try:
        print(f"🗄️  正在初始化数据库: {db_path}")
        
        # 确保目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        set_current_operation("创建数据库结构")
        # 创建新的SQLiteStorage实例，这会自动创建表结构
        storage = SQLiteStorage(db_path)
        
        # 验证数据库创建成功
        validation_results = storage.validate_database_structure()
        total_count = storage.get_total_count()
        
        # 检查是否所有表都创建成功
        failed_tables = [table for table, created in validation_results.items() if not created]
        if failed_tables:
            storage.close()
            print(f"❌ 数据库初始化失败！以下表未能创建: {', '.join(failed_tables)}")
            return 1
        
        storage.close()
        check_interruption()
        
        print(f"\n✅ 数据库初始化完成!")
        print(f"📁 数据库文件: {db_path}")
        print(f"📋 已创建的表:")
        for table_name, created in validation_results.items():
            status = "✅" if created else "❌"
            table_descriptions = {
                'video_info': '视频元数据表',
                'video_tags': '视频标签表',
                'scan_history': '扫描历史表',
                'video_master_list': '视频主列表表',
                'merge_history': '合并历史表'
            }
            description = table_descriptions.get(table_name, table_name)
            print(f"  {status} {table_name} - {description}")
        print(f"📊 当前记录数: {total_count}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 数据库初始化被用户中断")
        return 130
    except Exception as e:
        _error_handler.handle_database_error(f"数据库初始化失败: {e}", db_path, "初始化")
        return 1


def stats_command(args):
    """处理数据统计命令"""
    try:
        setup_signal_handlers()
        set_current_operation("数据统计")
        
        db_path = args.database
        
        # 检查数据库文件是否存在
        if not os.path.exists(db_path):
            print(f"❌ 错误: 数据库文件不存在: {db_path}")
            print("💡 提示: 请先运行扫描命令生成数据，或使用 --init-db 初始化数据库")
            return 1
        
        # 连接数据库
        storage = SQLiteStorage(db_path)
        check_interruption()
        
        if args.group_by:
            # 分组统计
            if args.group_by == 'tags':
                print("📊 按标签分组统计:")
                print("=" * 50)
                stats = storage.get_statistics_by_tags()
                if stats:
                    for stat in stats:
                        tag = stat['tag']
                        count = stat['count']
                        print(f"{tag}: {count} 个视频")
                else:
                    print("暂无数据")
                    
            elif args.group_by == 'resolution':
                print("📊 按分辨率分组统计:")
                print("=" * 50)
                stats = storage.get_statistics_by_resolution()
                if stats:
                    for stat in stats:
                        resolution = stat['resolution']
                        count = stat['count']
                        print(f"{resolution}: {count} 个视频")
                else:
                    print("暂无数据")
                    
            elif args.group_by == 'duration':
                print("📊 按时长分组统计:")
                print("=" * 50)
                stats = storage.get_statistics_by_duration()
                if stats:
                    for stat in stats:
                        duration_range = stat['duration_range']
                        count = stat['count']
                        print(f"{duration_range}: {count} 个视频")
                else:
                    print("暂无数据")
        else:
            # 基本统计信息
            print("📊 数据库统计信息:")
            print("=" * 50)
            
            enhanced_stats = storage.get_enhanced_statistics()
            
            # 基本信息
            print(f"📹 总视频数: {enhanced_stats['total_videos']}")
            print(f"🔄 同名视频组数: {enhanced_stats['duplicate_video_groups']}")
            print(f"📁 唯一视频数: {enhanced_stats['unique_videos']}")
            
            # 容量信息
            total_size_gb = enhanced_stats['total_size'] / (1024**3) if enhanced_stats['total_size'] else 0
            avg_size_mb = enhanced_stats['avg_file_size'] / (1024**2) if enhanced_stats['avg_file_size'] else 0
            print(f"💾 总容量: {total_size_gb:.2f} GB")
            print(f"📏 平均文件大小: {avg_size_mb:.2f} MB")
            
            # 时长信息
            total_hours = enhanced_stats['total_duration'] / 3600 if enhanced_stats['total_duration'] else 0
            avg_minutes = enhanced_stats['avg_duration'] / 60 if enhanced_stats['avg_duration'] else 0
            print(f"⏱️ 总时长: {total_hours:.2f} 小时")
            print(f"⏰ 平均时长: {avg_minutes:.2f} 分钟")
            
            # 编码信息
            if enhanced_stats['most_common_codec']:
                print(f"🎬 最常见编码: {enhanced_stats['most_common_codec']}")
            
            # 分辨率分布
            if enhanced_stats['resolution_distribution']:
                print("\n📺 分辨率分布:")
                for resolution, count in enhanced_stats['resolution_distribution'].items():
                    print(f"  {resolution}: {count} 个视频")
        
        storage.close()
        check_interruption()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n🛑 统计操作被用户中断")
        return 130
    except Exception as e:
        _error_handler.handle_database_error(f"统计操作失败: {e}", args.database, "统计")
        return 1


def create_parser():
    """创建命令行参数解析器"""
    # 获取默认路径配置
    default_paths = get_default_paths()
    
    parser = argparse.ArgumentParser(
        description="Video Info Collector - 视频文件信息收集工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 扫描目录生成临时文件
  python -m tools.video_info_collector /path/to/videos
  
  # 指定标签和路径
  python -m tools.video_info_collector /path/to/videos --tags "动作片,高清" --path "电影/动作片/2024"
  
  # 指定输出格式
  python -m tools.video_info_collector /path/to/videos --output-format csv  # 默认
  python -m tools.video_info_collector /path/to/videos --output-format sqlite  # 直接输出SQLite
  
  # 指定输出文件
  python -m tools.video_info_collector /path/to/videos --output /path/to/output.csv
  python -m tools.video_info_collector /path/to/videos --output /path/to/output.db
  
  # 合并临时文件到数据库
  python -m tools.video_info_collector --merge output/video_info_collector/csv/temp_video_info_20240120_154500.csv
  
  # 从数据库导出
  python -m tools.video_info_collector --export output/video_info_collector/database/video_database.db --output output/video_info_collector/csv/exported_data.csv
  
  # 从数据库简化导出（仅包含filename、filesize、logical_path）
  python -m tools.video_info_collector --export-simple output/video_info_collector/database/video_database.db --output simple_export.txt
  
  # 根据视频code查询
  python -m tools.video_info_collector --search-video-code "ABC-123"
  python -m tools.video_info_collector --search-video-code "ABC-123,DEF-456"
  python -m tools.video_info_collector --search-video-code "ABC-123 DEF-456"
  
  # 数据统计
  python -m tools.video_info_collector --stats  # 显示基本统计信息
  python -m tools.video_info_collector --stats --group-by tags  # 按标签分组统计
  python -m tools.video_info_collector --stats --group-by resolution  # 按分辨率分组统计
  python -m tools.video_info_collector --stats --group-by duration  # 按时长分组统计
  
  # 初始化/重置数据库
  python -m tools.video_info_collector --init-db
  python -m tools.video_info_collector --init-db --database /path/to/custom.db
        """
    )
    
    # 全局参数
    parser.add_argument('--database', default=default_paths['default_database'],
                       help=f'SQLite数据库文件路径 (默认: {default_paths["default_database"]})')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试模式，显示详细的错误信息和堆栈跟踪')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='启用详细输出模式，显示更多操作信息')
    
    # 互斥组：扫描、合并或导出
    group = parser.add_mutually_exclusive_group(required=False)
    
    # 合并操作
    group.add_argument('--merge', dest='csv_file', metavar='CSV_FILE',
                      help='合并临时CSV文件到数据库')
    
    # 导出操作
    group.add_argument('--export', dest='export_db', metavar='DATABASE',
                      help='从数据库导出到CSV文件')
    
    # 简化导出操作
    group.add_argument('--export-simple', dest='export_simple_db', metavar='DATABASE',
                      help='从数据库简化导出（仅包含filename、filesize、logical_path）')
    
    # 数据库初始化操作
    group.add_argument('--init-db', action='store_true',
                      help='初始化/重置数据库（清空所有数据）')
    
    # 视频code查询操作
    group.add_argument('--search-video-code', dest='search_video_codes', metavar='VIDEO_CODES',
                      help='根据视频code查询（支持多个video_code，用空格或逗号分隔）')
    
    # 数据统计操作
    group.add_argument('--stats', action='store_true',
                      help='显示数据库统计信息')
    
    # 扫描目录（位置参数）
    parser.add_argument('directory', nargs='?',
                       help='要扫描的目录路径')
    
    # 扫描参数
    parser.add_argument('--tags',
                       help='为所有文件添加的标签（分号分隔，如：动作片;高清;2024）')
    parser.add_argument('--path',
                       help='逻辑路径信息')
    parser.add_argument('--temp-file',
                       help='临时收集文件名')
    parser.add_argument('--dry-run', action='store_true',
                       help='预览模式，不写入文件')
    parser.add_argument('--recursive', action='store_true', default=True,
                       help='递归扫描子目录 (默认: True)')
    parser.add_argument('--extensions', 
                       default='.mp4,.mkv,.avi,.mov,.wmv,.flv',
                       help='视频文件扩展名过滤')
    
    # 输出参数
    parser.add_argument('--output-format', choices=['csv', 'sqlite'], default='csv',
                       help='输出格式：csv/sqlite (默认: csv)')
    parser.add_argument('--output',
                       help='输出文件路径')
    
    # 合并参数
    parser.add_argument('--duplicate-strategy', 
                       choices=['skip', 'update', 'append'], 
                       default='skip',
                       help='重复项处理策略 (默认: skip)')
    parser.add_argument('--force', action='store_true',
                       help='强制重新合并已经合并过的CSV文件')
    
    # 导出参数
    parser.add_argument('--format', choices=['csv', 'json'], default='csv',
                       help='导出格式 (默认: csv)')
    
    # 统计参数
    parser.add_argument('--group-by', choices=['tags', 'resolution', 'duration'], 
                       help='分组统计维度：tags(标签)、resolution(分辨率)、duration(时长)')
    
    return parser


def cli_main(argv=None):
    """CLI主函数"""
    global _error_handler
    
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # 确保错误处理器已初始化（用于测试）
    if _error_handler is None:
        _error_handler = create_error_handler()
    
    # 根据操作类型调用相应函数
    if args.csv_file:
        # 合并操作
        return merge_command(args)
    elif args.export_db:
        # 导出操作
        if not args.output:
            print("错误: 导出操作需要指定 --output 参数")
            return 1
        # 设置数据库路径
        args.database = args.export_db
        return export_command(args)
    elif args.export_simple_db:
        # 简化导出操作
        # 设置数据库路径
        args.database = args.export_simple_db
        return export_simple_command(args)
    elif args.init_db:
        # 数据库初始化操作
        return init_db_command(args)
    elif args.search_video_codes:
        # 视频code查询操作
        return search_video_code_command(args)
    elif args.stats:
        # 数据统计操作
        return stats_command(args)
    elif args.directory:
        # 扫描操作
        return scan_command(args)
    else:
        # 如果没有提供任何操作，显示帮助
        parser.print_help()
        return 1


def main():
    """主入口函数"""
    global _error_handler
    
    try:
        # 预解析参数以获取调试模式设置
        parser = create_parser()
        args, _ = parser.parse_known_args()
        
        # 初始化错误处理器
        _error_handler = create_error_handler(debug_mode=args.debug, verbose=args.verbose)
        
        # 设置信号处理器
        setup_signal_handlers()
        
        # 设置日志记录
        setup_logging(debug_mode=args.debug)
        
        if args.verbose:
            print("🔧 详细模式已启用")
        if args.debug:
            print("🐛 调试模式已启用")
        
        exit_code = cli_main()
        sys.exit(exit_code)
        
    except SystemExit as e:
        return e.code
    except KeyboardInterrupt:
        print("\n🛑 程序被用户中断")
        return 130
    except Exception as e:
        if _error_handler:
            _error_handler.handle_generic_error(f"程序运行时发生未预期的错误: {e}", "程序启动")
        else:
            print(f"❌ 程序运行时发生未预期的错误: {e}")
        return 1


if __name__ == '__main__':
    main()
