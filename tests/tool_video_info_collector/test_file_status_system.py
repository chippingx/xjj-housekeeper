#!/usr/bin/env python3
"""
测试三状态file_status系统

测试覆盖：
1. present/missing/ignore状态的正确设置
2. 状态转换逻辑
3. 状态持久化和恢复
4. 批量状态管理
5. 状态查询和过滤
"""

import unittest
import tempfile
import os
import shutil
from pathlib import Path
import sys
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.video_info_collector.metadata import VideoInfo
from tools.video_info_collector.sqlite_storage import SQLiteStorage


class TestFileStatusBasics(unittest.TestCase):
    """测试file_status基础功能"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_file(self, relative_path: str, content: str = "test") -> str:
        """创建测试文件"""
        full_path = os.path.join(self.temp_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        return full_path
    
    def test_default_status_present(self):
        """测试默认状态为present"""
        file_path = self._create_test_file("videos/ABC-123.mp4")
        video_info = VideoInfo(file_path)
        
        # 新创建的VideoInfo应该默认为present状态
        self.assertEqual(video_info.file_status, 'present',
                        "新文件的默认状态应该是present")
    
    def test_valid_status_values(self):
        """测试有效的状态值"""
        file_path = self._create_test_file("videos/ABC-123.mp4")
        video_info = VideoInfo(file_path)
        
        valid_statuses = ['present', 'missing', 'ignore']
        
        for status in valid_statuses:
            video_info.file_status = status
            self.assertEqual(video_info.file_status, status,
                           f"应该能够设置状态为 {status}")
    
    def test_invalid_status_values(self):
        """测试无效的状态值"""
        file_path = self._create_test_file("videos/ABC-123.mp4")
        video_info = VideoInfo(file_path)
        
        invalid_statuses = ['deleted', 'unknown', 'error', '', None, 123]
        
        for invalid_status in invalid_statuses:
            with self.subTest(status=invalid_status):
                # 设置无效状态应该抛出异常或者被忽略
                # 具体行为取决于实现
                try:
                    video_info.file_status = invalid_status
                    # 如果允许设置，验证是否有默认处理
                    self.assertIn(video_info.file_status, 
                                ['present', 'missing', 'ignore'],
                                f"无效状态 {invalid_status} 应该被处理为有效状态")
                except (ValueError, TypeError):
                    # 如果抛出异常，这是预期的行为
                    pass


class TestStatusTransitions(unittest.TestCase):
    """测试状态转换逻辑"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_file(self, relative_path: str, content: str = "test") -> str:
        """创建测试文件"""
        full_path = os.path.join(self.temp_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        return full_path
    
    def test_present_to_missing_transition(self):
        """测试present到missing的转换"""
        # 1. 创建文件，状态为present
        file_path = self._create_test_file("videos/ABC-123.mp4")
        video_info = VideoInfo(file_path)
        self.assertEqual(video_info.file_status, 'present')
        
        # 2. 删除文件，模拟文件丢失
        os.remove(file_path)
        
        # 3. 更新状态为missing
        video_info.file_status = 'missing'
        self.assertEqual(video_info.file_status, 'missing')
        
        # 4. 验证其他属性保持不变
        self.assertIsNotNone(video_info.video_code)
        self.assertIsNotNone(video_info.file_fingerprint)
    
    def test_missing_to_present_transition(self):
        """测试missing到present的转换（文件恢复）"""
        # 1. 创建文件信息但文件不存在
        file_path = os.path.join(self.temp_dir, "videos/ABC-123.mp4")
        
        # 先创建文件获取信息，然后删除
        temp_file = self._create_test_file("videos/ABC-123.mp4")
        video_info = VideoInfo(temp_file)
        original_fingerprint = video_info.file_fingerprint
        
        os.remove(temp_file)
        video_info.file_status = 'missing'
        
        # 2. 恢复文件
        restored_file = self._create_test_file("videos/ABC-123.mp4")
        restored_info = VideoInfo(restored_file)
        
        # 3. 验证恢复后的状态
        self.assertEqual(restored_info.file_status, 'present')
        
        # 4. 验证指纹匹配（如果内容相同）
        self.assertEqual(original_fingerprint, restored_info.file_fingerprint,
                        "恢复的文件应该有相同的指纹")
    
    def test_present_to_ignore_transition(self):
        """测试present到ignore的转换"""
        file_path = self._create_test_file("videos/ABC-123.mp4")
        video_info = VideoInfo(file_path)
        
        # 用户标记为忽略
        video_info.file_status = 'ignore'
        self.assertEqual(video_info.file_status, 'ignore')
        
        # 验证文件仍然存在但被标记为忽略
        self.assertTrue(os.path.exists(file_path))
    
    def test_ignore_to_present_transition(self):
        """测试ignore到present的转换（取消忽略）"""
        file_path = self._create_test_file("videos/ABC-123.mp4")
        video_info = VideoInfo(file_path)
        
        # 先标记为忽略
        video_info.file_status = 'ignore'
        
        # 然后取消忽略
        video_info.file_status = 'present'
        self.assertEqual(video_info.file_status, 'present')
    
    def test_invalid_transitions(self):
        """测试无效的状态转换"""
        file_path = self._create_test_file("videos/ABC-123.mp4")
        video_info = VideoInfo(file_path)
        
        # 某些转换可能在业务逻辑上不合理
        # 例如：直接从present跳到missing而文件实际存在
        # 这取决于具体的业务规则实现
        
        # 这里主要测试状态设置的基本功能
        video_info.file_status = 'present'
        self.assertEqual(video_info.file_status, 'present')
        
        video_info.file_status = 'missing'
        self.assertEqual(video_info.file_status, 'missing')
        
        video_info.file_status = 'ignore'
        self.assertEqual(video_info.file_status, 'ignore')


class TestStatusPersistence(unittest.TestCase):
    """测试状态持久化"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_status_database_storage(self):
        """测试状态在数据库中的存储"""
        # 这个测试需要等SQLiteStorage更新后实现
        # 验证file_status字段能够正确存储和检索
        pass
    
    def test_status_csv_export(self):
        """测试状态在CSV导出中的包含"""
        # 这个测试需要等CSVWriter更新后实现
        # 验证file_status字段能够正确导出到CSV
        pass


class TestBatchStatusManagement(unittest.TestCase):
    """测试批量状态管理"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_files(self, count: int) -> list:
        """创建多个测试文件"""
        files = []
        for i in range(count):
            file_path = os.path.join(self.temp_dir, f"videos/TEST-{i:03d}.mp4")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(f"content_{i}")
            
            files.append(file_path)
        
        return files
    
    def test_batch_status_update(self):
        """测试批量状态更新"""
        # 创建多个文件
        file_paths = self._create_test_files(10)
        video_infos = [VideoInfo(path) for path in file_paths]
        
        # 验证所有文件初始状态为present
        for info in video_infos:
            self.assertEqual(info.file_status, 'present')
        
        # 批量更新状态
        for i, info in enumerate(video_infos):
            if i < 3:
                info.file_status = 'ignore'
            elif i < 6:
                info.file_status = 'missing'
            # 其余保持present
        
        # 验证状态更新
        ignore_count = sum(1 for info in video_infos if info.file_status == 'ignore')
        missing_count = sum(1 for info in video_infos if info.file_status == 'missing')
        present_count = sum(1 for info in video_infos if info.file_status == 'present')
        
        self.assertEqual(ignore_count, 3)
        self.assertEqual(missing_count, 3)
        self.assertEqual(present_count, 4)
    
    def test_status_filtering(self):
        """测试按状态过滤"""
        file_paths = self._create_test_files(15)
        video_infos = [VideoInfo(path) for path in file_paths]
        
        # 设置不同状态
        for i, info in enumerate(video_infos):
            if i % 3 == 0:
                info.file_status = 'present'
            elif i % 3 == 1:
                info.file_status = 'missing'
            else:
                info.file_status = 'ignore'
        
        # 按状态分组
        present_files = [info for info in video_infos if info.file_status == 'present']
        missing_files = [info for info in video_infos if info.file_status == 'missing']
        ignore_files = [info for info in video_infos if info.file_status == 'ignore']
        
        # 验证分组结果
        self.assertEqual(len(present_files), 5)  # 0, 3, 6, 9, 12
        self.assertEqual(len(missing_files), 5)   # 1, 4, 7, 10, 13
        self.assertEqual(len(ignore_files), 5)    # 2, 5, 8, 11, 14
        
        # 验证总数
        total = len(present_files) + len(missing_files) + len(ignore_files)
        self.assertEqual(total, 15)


class TestStatusQueryAndReporting(unittest.TestCase):
    """测试状态查询和报告"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_status_statistics(self):
        """测试状态统计"""
        # 创建不同状态的文件
        test_data = [
            ("present", 10),
            ("missing", 5),
            ("ignore", 3),
        ]
        
        all_infos = []
        for status, count in test_data:
            for i in range(count):
                file_path = os.path.join(self.temp_dir, 
                                       f"{status}/TEST-{i:03d}.mp4")
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w') as f:
                    f.write(f"content_{status}_{i}")
                
                video_info = VideoInfo(file_path)
                video_info.file_status = status
                all_infos.append(video_info)
        
        # 计算统计信息
        status_counts = {}
        for info in all_infos:
            status = info.file_status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 验证统计结果
        self.assertEqual(status_counts['present'], 10)
        self.assertEqual(status_counts['missing'], 5)
        self.assertEqual(status_counts['ignore'], 3)
        self.assertEqual(sum(status_counts.values()), 18)
    
    def test_status_change_tracking(self):
        """测试状态变化跟踪"""
        file_path = os.path.join(self.temp_dir, "videos/ABC-123.mp4")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write("content")
        
        video_info = VideoInfo(file_path)
        
        # 记录状态变化历史
        status_history = []
        
        # 初始状态
        status_history.append(('initial', video_info.file_status, datetime.now()))
        
        # 状态变化
        video_info.file_status = 'missing'
        status_history.append(('missing', video_info.file_status, datetime.now()))
        
        video_info.file_status = 'ignore'
        status_history.append(('ignore', video_info.file_status, datetime.now()))
        
        video_info.file_status = 'present'
        status_history.append(('present', video_info.file_status, datetime.now()))
        
        # 验证历史记录
        self.assertEqual(len(status_history), 4)
        self.assertEqual(status_history[0][1], 'present')  # 初始状态
        self.assertEqual(status_history[1][1], 'missing')
        self.assertEqual(status_history[2][1], 'ignore')
        self.assertEqual(status_history[3][1], 'present')  # 最终状态


class TestStatusIntegration(unittest.TestCase):
    """测试状态系统的集成功能"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.storage = SQLiteStorage(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_status_with_smart_merge(self):
        """测试状态系统与智能合并的集成"""
        # 这个测试需要等智能合并功能实现后完成
        # 验证合并过程中状态的正确处理
        pass
    
    def test_status_with_master_list(self):
        """测试状态系统与master_list的集成"""
        # 这个测试需要等master_list功能实现后完成
        # 验证状态变化对master_list的影响
        pass
    
    def test_status_consistency_check(self):
        """测试状态一致性检查"""
        # 创建文件
        file_path = os.path.join(self.temp_dir, "videos/ABC-123.mp4")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write("content")
        
        video_info = VideoInfo(file_path)
        
        # 验证状态与文件存在性的一致性
        if os.path.exists(file_path):
            # 文件存在时，状态应该是present或ignore，不应该是missing
            self.assertIn(video_info.file_status, ['present', 'ignore'])
        else:
            # 文件不存在时，状态应该是missing
            self.assertEqual(video_info.file_status, 'missing')


if __name__ == '__main__':
    unittest.main(verbosity=2)