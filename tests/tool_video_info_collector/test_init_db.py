#!/usr/bin/env python3
"""
测试 --init-db 命令的功能
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
import sqlite3

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tools.video_info_collector.sqlite_storage import SQLiteStorage
from tools.video_info_collector.cli import init_db_command
from unittest.mock import patch, MagicMock


class TestInitDbCommand:
    """测试 init_db_command 功能"""
    
    def test_init_db_creates_all_tables(self):
        """测试初始化数据库创建所有必需的表"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_init.db")
            
            # 创建SQLiteStorage实例
            storage = SQLiteStorage(db_path)
            
            # 验证所有表都被创建
            validation_results = storage.validate_database_structure()
            
            expected_tables = [
                'video_info',
                'video_tags', 
                'scan_history',
                'video_master_list',
                'merge_history'
            ]
            
            # 检查所有期望的表都存在
            for table_name in expected_tables:
                assert table_name in validation_results, f"表 {table_name} 不在验证结果中"
                assert validation_results[table_name], f"表 {table_name} 未被创建"
            
            storage.close()
    
    def test_init_db_table_structure(self):
        """测试数据库表结构是否正确"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_structure.db")
            
            storage = SQLiteStorage(db_path)
            table_info = storage.get_table_info()
            
            # 验证video_info表的关键字段
            video_info_columns = [col['name'] for col in table_info['video_info']['columns']]
            required_columns = [
                'id', 'file_path', 'filename', 'video_code', 
                'file_fingerprint', 'file_status', 'last_scan_time'
            ]
            
            for column in required_columns:
                assert column in video_info_columns, f"video_info表缺少必需字段: {column}"
            
            # 验证video_master_list表的关键字段
            master_list_columns = [col['name'] for col in table_info['video_master_list']['columns']]
            required_master_columns = [
                'id', 'video_code', 'file_fingerprint', 'status', 'file_count'
            ]
            
            for column in required_master_columns:
                assert column in master_list_columns, f"video_master_list表缺少必需字段: {column}"
            
            storage.close()
    
    def test_init_db_command_new_database(self):
        """测试init_db_command创建新数据库"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_command.db")
            
            # 模拟命令行参数
            args = MagicMock()
            args.database = db_path
            
            # 执行init_db_command
            result = init_db_command(args)
            
            # 验证命令执行成功
            assert result == 0, "init_db_command应该返回0表示成功"
            
            # 验证数据库文件被创建
            assert os.path.exists(db_path), "数据库文件应该被创建"
            
            # 验证表结构
            storage = SQLiteStorage(db_path)
            validation_results = storage.validate_database_structure()
            
            for table_name, created in validation_results.items():
                assert created, f"表 {table_name} 应该被创建"
            
            storage.close()
    
    @patch('builtins.input', return_value='yes')
    def test_init_db_command_reset_existing(self, mock_input):
        """测试init_db_command重置现有数据库"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_reset.db")
            
            # 先创建一个数据库并添加一些数据
            storage = SQLiteStorage(db_path)
            cursor = storage.connection.cursor()
            cursor.execute("INSERT INTO video_info (file_path, filename, created_time) VALUES (?, ?, ?)",
                         ("/test/path", "test.mp4", "2024-01-01 00:00:00"))
            storage.connection.commit()
            
            # 验证数据存在
            count_before = storage.get_total_count()
            assert count_before > 0, "应该有测试数据"
            storage.close()
            
            # 模拟命令行参数
            args = MagicMock()
            args.database = db_path
            
            # 执行init_db_command重置数据库
            result = init_db_command(args)
            
            # 验证命令执行成功
            assert result == 0, "init_db_command应该返回0表示成功"
            
            # 验证数据库被重置（数据被清空）
            storage = SQLiteStorage(db_path)
            count_after = storage.get_total_count()
            assert count_after == 0, "重置后数据库应该为空"
            
            # 验证表结构仍然正确
            validation_results = storage.validate_database_structure()
            for table_name, created in validation_results.items():
                assert created, f"重置后表 {table_name} 应该存在"
            
            storage.close()
    
    @patch('builtins.input', return_value='no')
    def test_init_db_command_cancel_reset(self, mock_input):
        """测试init_db_command取消重置现有数据库"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_cancel.db")
            
            # 先创建一个数据库并添加一些数据
            storage = SQLiteStorage(db_path)
            cursor = storage.connection.cursor()
            cursor.execute("INSERT INTO video_info (file_path, filename, created_time) VALUES (?, ?, ?)",
                         ("/test/path", "test.mp4", "2024-01-01 00:00:00"))
            storage.connection.commit()
            
            count_before = storage.get_total_count()
            storage.close()
            
            # 模拟命令行参数
            args = MagicMock()
            args.database = db_path
            
            # 执行init_db_command但取消重置
            result = init_db_command(args)
            
            # 验证命令返回0（取消操作）
            assert result == 0, "取消操作应该返回0"
            
            # 验证原数据仍然存在
            storage = SQLiteStorage(db_path)
            count_after = storage.get_total_count()
            assert count_after == count_before, "取消重置后原数据应该保持不变"
            storage.close()
    
    def test_validate_database_structure_method(self):
        """测试validate_database_structure方法"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_validate.db")
            
            storage = SQLiteStorage(db_path)
            validation_results = storage.validate_database_structure()
            
            # 验证返回结果格式
            assert isinstance(validation_results, dict), "验证结果应该是字典"
            
            expected_tables = [
                'video_info', 'video_tags', 'scan_history', 
                'video_master_list', 'merge_history'
            ]
            
            for table_name in expected_tables:
                assert table_name in validation_results, f"验证结果应该包含表 {table_name}"
                assert isinstance(validation_results[table_name], bool), f"表 {table_name} 的验证结果应该是布尔值"
                assert validation_results[table_name], f"表 {table_name} 应该存在"
            
            storage.close()
    
    def test_get_table_info_method(self):
        """测试get_table_info方法"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_table_info.db")
            
            storage = SQLiteStorage(db_path)
            table_info = storage.get_table_info()
            
            # 验证返回结果格式
            assert isinstance(table_info, dict), "表信息应该是字典"
            
            # 验证每个表的信息结构
            for table_name, info in table_info.items():
                assert 'columns' in info, f"表 {table_name} 应该有columns信息"
                assert 'column_count' in info, f"表 {table_name} 应该有column_count信息"
                assert isinstance(info['columns'], list), f"表 {table_name} 的columns应该是列表"
                assert info['column_count'] == len(info['columns']), f"表 {table_name} 的column_count应该与实际列数匹配"
                
                # 验证列信息结构
                for column in info['columns']:
                    required_keys = ['name', 'type', 'not_null', 'default_value', 'primary_key']
                    for key in required_keys:
                        assert key in column, f"列信息应该包含 {key}"
            
            storage.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])