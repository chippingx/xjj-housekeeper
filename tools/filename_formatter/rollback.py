#!/usr/bin/env python3
"""
文件重命名回滚工具
根据操作日志回滚重命名操作
"""

import os
import json
import shutil
import argparse
from pathlib import Path
from typing import List, Dict, Any


def load_operation_log(log_file: str) -> List[Dict[str, Any]]:
    """加载操作日志"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 无法读取日志文件 {log_file}: {e}")
        return []


def rollback_operations(log_file: str, dry_run: bool = False) -> bool:
    """
    回滚操作
    
    Args:
        log_file: 操作日志文件路径
        dry_run: 是否为干运行模式
    
    Returns:
        bool: 回滚是否成功
    """
    operations = load_operation_log(log_file)
    if not operations:
        print("❌ 没有找到可回滚的操作")
        return False
    
    print(f"📋 找到 {len(operations)} 个操作记录")
    
    if dry_run:
        print("🔍 预览模式 - 以下是将要回滚的操作：")
        print("=" * 50)
    
    success_count = 0
    error_count = 0
    
    # 按时间倒序处理（最新的操作先回滚）
    for operation in reversed(operations):
        op_type = operation.get('operation_type')
        source_path = operation.get('source_path')
        target_path = operation.get('target_path')
        backup_path = operation.get('backup_path')
        
        if op_type == 'rename':
            # 回滚重命名：将目标文件重命名回源文件
            if os.path.exists(target_path):
                if dry_run:
                    print(f"📁 将重命名: {target_path} -> {source_path}")
                else:
                    try:
                        # 检查源路径是否已存在
                        if os.path.exists(source_path):
                            print(f"⚠️ 源文件已存在，跳过: {source_path}")
                            continue
                        
                        # 确保源目录存在
                        os.makedirs(os.path.dirname(source_path), exist_ok=True)
                        
                        os.rename(target_path, source_path)
                        print(f"✅ 已回滚重命名: {target_path} -> {source_path}")
                        success_count += 1
                    except Exception as e:
                        print(f"❌ 回滚重命名失败: {target_path} -> {source_path}, 错误: {e}")
                        error_count += 1
            else:
                if not dry_run:
                    print(f"⚠️ 目标文件不存在，跳过: {target_path}")
        else:
            # 轻量级模式不支持其他操作类型的回滚
            if not dry_run:
                print(f"⚠️ 轻量级模式不支持操作类型 '{op_type}' 的回滚")
                error_count += 1
    
    if dry_run:
        print("\n💡 这只是预览！要实际执行回滚，请移除 --dry-run 参数")
    else:
        print(f"\n📊 回滚完成:")
        print(f"  ✅ 成功: {success_count}")
        print(f"  ❌ 失败: {error_count}")
        
        if success_count > 0:
            # 创建回滚日志
            rollback_log = log_file.replace('.json', '_rollback.json')
            try:
                with open(rollback_log, 'w', encoding='utf-8') as f:
                    json.dump({
                        'rollback_timestamp': operations[0]['timestamp'] if operations else '',
                        'original_log_file': log_file,
                        'operations_rolled_back': len(operations),
                        'success_count': success_count,
                        'error_count': error_count
                    }, f, indent=2, ensure_ascii=False)
                print(f"📝 回滚日志已保存: {rollback_log}")
            except Exception as e:
                print(f"⚠️ 保存回滚日志失败: {e}")
    
    return error_count == 0


def main():
    parser = argparse.ArgumentParser(description="文件重命名回滚工具")
    parser.add_argument("log_file", help="操作日志文件路径")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际执行回滚")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.log_file):
        print(f"❌ 日志文件不存在: {args.log_file}")
        return 1
    
    success = rollback_operations(args.log_file, args.dry_run)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())