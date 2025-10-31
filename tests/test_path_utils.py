#!/usr/bin/env python3
"""
路径管理工具测试用例

测试 ProjectPathManager 在各种环境下的稳定性和正确性。
"""

import unittest
import tempfile
import os
from pathlib import Path
import sys
import pytest
from unittest.mock import patch, MagicMock

# 添加 tools 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from path_utils import ProjectPathManager, get_project_root, get_config_path, resolve_path


class TestProjectPathManager(unittest.TestCase):
    """测试 ProjectPathManager 类"""
    
    def setUp(self):
        """每个测试前清除缓存"""
        ProjectPathManager._cached_project_root = None  
    def tearDown(self):
        """每个测试后清除缓存"""
        ProjectPathManager._cached_project_root = None
    
    def test_get_project_root_with_env_var(self):
        """测试通过环境变量获取项目根目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            
            # 创建标志文件
            (temp_path / "pyproject.toml").touch()
            
            # 设置环境变量
            with patch.dict(os.environ, {'XJJ_HOUSEKEEPER_ROOT': str(temp_path)}):
                result = ProjectPathManager.get_project_root()
                assert result.resolve() == temp_path
    
    def test_get_project_root_by_markers(self):
        """测试通过标志文件检测获取项目根目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            
            # 创建项目结构
            project_root = temp_path / "project"
            project_root.mkdir()
            (project_root / "pyproject.toml").touch()
            
            # 创建子目录和文件
            sub_dir = project_root / "tools" / "submodule"
            sub_dir.mkdir(parents=True)
            test_file = sub_dir / "test.py"
            test_file.touch()
            
            # 从子目录文件开始查找
            result = ProjectPathManager.get_project_root(calling_file=str(test_file))
            assert result.resolve() == project_root.resolve()
    
    def test_get_project_root_multiple_markers(self):
        """测试多个标志文件的情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            
            # 创建多个标志文件
            (temp_path / "README.md").touch()
            (temp_path / "HANDOVER.md").touch()
            (temp_path / "tools").mkdir()
            
            sub_file = temp_path / "sub" / "test.py"
            sub_file.parent.mkdir()
            sub_file.touch()
            
            result = ProjectPathManager.get_project_root(calling_file=str(sub_file))
            assert result.resolve() == temp_path
    
    def test_get_project_root_fallback_relative_path(self):
        """测试相对路径回退策略"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            
            # 创建项目结构
            project_root = temp_path / "project"
            project_root.mkdir()
            (project_root / "pyproject.toml").touch()
            
            # 创建深层子目录
            deep_dir = project_root / "tools" / "submodule" / "deep"
            deep_dir.mkdir(parents=True)
            test_file = deep_dir / "test.py"
            test_file.touch()
            
            # 使用相对路径回退（向上3级）
            result = ProjectPathManager.get_project_root(
                fallback_relative_path="../../../",
                calling_file=str(test_file)
            )
            assert result.resolve() == project_root.resolve()
    
    def test_get_project_root_caching(self):
        """测试缓存机制"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            (temp_path / "pyproject.toml").touch()
            
            with patch.dict(os.environ, {'XJJ_HOUSEKEEPER_ROOT': str(temp_path)}):
                # 第一次调用
                result1 = ProjectPathManager.get_project_root()
                
                # 第二次调用应该使用缓存
                with patch('path_utils.ProjectPathManager._find_project_root_by_markers') as mock_find:
                    result2 = ProjectPathManager.get_project_root()
                    
                    # 验证缓存生效（没有调用查找方法）
                    mock_find.assert_not_called()
                    assert result1.resolve() == result2.resolve() == temp_path
    
    def test_get_project_root_failure(self):
        """测试无法找到项目根目录的情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            test_file = temp_path / "test.py"
            test_file.touch()
            
            # 清除环境变量并模拟所有查找策略失败
            with patch.dict(os.environ, {}, clear=True):
                with patch('path_utils.ProjectPathManager._find_project_root_by_markers', return_value=None):
                    with patch('sys.path', []):
                        with pytest.raises(RuntimeError, match="无法确定项目根目录"):
                            ProjectPathManager.get_project_root(calling_file=str(test_file))
    
    def test_is_valid_project_root(self):
        """测试项目根目录验证"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 无标志文件的目录
            assert not ProjectPathManager._is_valid_project_root(temp_path)
            
            # 有标志文件的目录
            (temp_path / "pyproject.toml").touch()
            assert ProjectPathManager._is_valid_project_root(temp_path)
            
            # 不存在的路径
            non_existent = temp_path / "non_existent"
            assert not ProjectPathManager._is_valid_project_root(non_existent)
    
    def test_find_project_root_by_markers(self):
        """测试标志文件查找逻辑"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            
            # 创建嵌套结构
            project_root = temp_path / "project"
            project_root.mkdir()
            (project_root / "README.md").touch()
            (project_root / "tools").mkdir()  # 添加多个标志文件确保能找到
            
            deep_dir = project_root / "a" / "b" / "c"
            deep_dir.mkdir(parents=True)
            
            # 从深层目录开始查找
            result = ProjectPathManager._find_project_root_by_markers(deep_dir)
            assert result.resolve() == project_root.resolve()
            
            # 从没有标志文件的目录查找
            other_dir = temp_path / "other"
            other_dir.mkdir()
            result = ProjectPathManager._find_project_root_by_markers(other_dir)
            assert result is None


class TestConvenienceFunctions(unittest.TestCase):
    """便捷函数测试类"""
    
    def setUp(self):
        """每个测试前清除缓存"""
        ProjectPathManager._cached_project_root = None  
    def tearDown(self):
        """每个测试后清除缓存"""
        ProjectPathManager._cached_project_root = None
    
    def test_get_project_root_function(self):
        """测试 get_project_root 便捷函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            (temp_path / "pyproject.toml").touch()
            
            with patch.dict(os.environ, {'XJJ_HOUSEKEEPER_ROOT': str(temp_path)}):
                result = get_project_root()
                assert result.resolve() == temp_path
    
    def test_get_config_path_function(self):
        """测试 get_config_path 便捷函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            (temp_path / "pyproject.toml").touch()
            
            with patch.dict(os.environ, {'XJJ_HOUSEKEEPER_ROOT': str(temp_path)}):
                result = get_config_path("config/test.yaml")
                expected = temp_path / "config" / "test.yaml"
                assert result.resolve() == expected.resolve()
    
    def test_resolve_path_function(self):
        """测试 resolve_path 便捷函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            (temp_path / "pyproject.toml").touch()
            
            with patch.dict(os.environ, {'XJJ_HOUSEKEEPER_ROOT': str(temp_path)}):
                # 测试相对路径
                result = resolve_path("relative/path")
                expected = temp_path / "relative" / "path"
                assert result.resolve() == expected.resolve()
                
                # 测试绝对路径
                abs_path = "/absolute/path"
                result = resolve_path(abs_path)
                assert result == Path(abs_path)


class TestRealWorldScenarios(unittest.TestCase):
    """真实场景测试类"""
    
    def setUp(self):
        """每个测试前清除缓存"""
        ProjectPathManager._cached_project_root = None
    
    def tearDown(self):
        """每个测试后清除缓存"""
        ProjectPathManager._cached_project_root = None
    
    def test_current_project_structure(self):
        """测试当前项目结构"""
        # 这个测试应该能在当前项目中正常工作
        current_file = __file__
        result = ProjectPathManager.get_project_root(calling_file=current_file)
        
        # 验证返回的是项目根目录
        assert (result / "pyproject.toml").exists()
        assert (result / "README.md").exists()
        assert (result / "tools").exists()
    
    def test_formatter_integration(self):
        """测试与 filename_formatter 的集成"""
        # 模拟 formatter.py 中的使用场景
        current_file = __file__
        result = ProjectPathManager.get_project_root(calling_file=current_file)
        
        # 验证能找到 formatter 的配置文件
        config_path = result / "tools" / "filename_formatter" / "rename_rules.yaml"
        assert config_path.parent.exists()  # 目录应该存在
    
    def test_video_collector_integration(self):
        """测试与 video_info_collector 的集成"""
        current_file = __file__
        config_path = get_config_path("tools/video_info_collector/config.yaml", calling_file=current_file)
        
        # 验证路径格式正确
        assert "tools/video_info_collector/config.yaml" in str(config_path)
        assert config_path.is_absolute()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])