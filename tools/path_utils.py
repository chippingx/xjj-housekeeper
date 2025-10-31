#!/usr/bin/env python3
"""
路径管理工具模块

提供稳定的项目根目录推导方案，解决在不同部署环境中路径推导不稳定的问题。
支持多种推导策略，确保在各种运行环境下都能正确找到项目根目录。
"""

import os
import sys
from pathlib import Path
from typing import Optional, Union


class ProjectPathManager:
    """项目路径管理器
    
    提供多种策略来推导项目根目录，确保在不同环境下的稳定性：
    1. 环境变量优先
    2. 标志文件检测
    3. 相对路径回退
    4. 当前工作目录回退
    """
    
    # 项目根目录的标志文件/目录（按优先级排序）
    PROJECT_MARKERS = [
        'pyproject.toml',  # 最具体的项目标志
        '.git',           # Git 仓库根目录
        'HANDOVER.md',    # 项目特有文件
        'tools',          # 项目特有目录
        'README.md'       # 通用文件，优先级最低
    ]
    
    _cached_project_root: Optional[Path] = None
    
    @classmethod
    def get_project_root(cls, 
                        env_var: str = 'XJJ_HOUSEKEEPER_ROOT',
                        fallback_relative_path: Optional[str] = None,
                        calling_file: Optional[str] = None) -> Path:
        """获取项目根目录
        
        Args:
            env_var: 环境变量名，用于指定项目根目录
            fallback_relative_path: 回退的相对路径（从调用文件开始计算）
            calling_file: 调用文件的路径（通常传入 __file__）
            
        Returns:
            项目根目录的 Path 对象
            
        Raises:
            RuntimeError: 无法确定项目根目录时抛出
        """
        # 使用缓存避免重复计算
        if cls._cached_project_root is not None:
            return cls._cached_project_root
        
        # 策略1: 环境变量优先
        if env_var in os.environ:
            env_path = Path(os.environ[env_var]).resolve()
            if cls._is_valid_project_root(env_path):
                cls._cached_project_root = env_path
                return env_path
        
        # 策略2: 从调用文件开始向上查找标志文件
        if calling_file:
            calling_path = Path(calling_file).resolve()
            project_root = cls._find_project_root_by_markers(calling_path)
            if project_root:
                cls._cached_project_root = project_root
                return project_root
        
        # 策略3: 使用回退的相对路径
        if fallback_relative_path and calling_file:
            try:
                calling_path = Path(calling_file).resolve()
                # 解析相对路径（如 "../../" 表示向上两级）
                relative_parts = fallback_relative_path.split('/')
                current_path = calling_path.parent
                
                for part in relative_parts:
                    if part == '..':
                        current_path = current_path.parent
                    elif part == '.':
                        continue
                    elif part:  # 非空字符串
                        current_path = current_path / part
                
                if cls._is_valid_project_root(current_path):
                    cls._cached_project_root = current_path
                    return current_path
            except Exception:
                pass  # 继续尝试其他策略
        
        # 策略4: 从当前工作目录开始向上查找
        cwd_root = cls._find_project_root_by_markers(Path.cwd())
        if cwd_root:
            cls._cached_project_root = cwd_root
            return cwd_root
        
        # 策略5: 从 sys.path[0] 开始查找（脚本所在目录）
        if sys.path and sys.path[0]:
            script_root = cls._find_project_root_by_markers(Path(sys.path[0]))
            if script_root:
                cls._cached_project_root = script_root
                return script_root
        
        # 所有策略都失败，抛出异常
        raise RuntimeError(
            f"无法确定项目根目录。请检查：\n"
            f"1. 设置环境变量 {env_var}\n"
            f"2. 确保项目包含标志文件: {', '.join(cls.PROJECT_MARKERS)}\n"
            f"3. 从正确的目录运行程序"
        )
    
    @classmethod
    def _find_project_root_by_markers(cls, start_path: Path) -> Optional[Path]:
        """通过标志文件向上查找项目根目录"""
        current = start_path.resolve()
        
        # 向上查找，最多查找10级避免无限循环
        for _ in range(10):
            # 按优先级检查标志文件/目录
            # 如果找到高优先级的标志文件，立即返回
            for marker in cls.PROJECT_MARKERS:
                if (current / marker).exists():
                    # 对于高优先级标志文件，直接返回
                    if marker in ['pyproject.toml', '.git', 'HANDOVER.md']:
                        return current
                    # 对于低优先级标志文件，继续检查是否有其他标志文件
                    elif marker in ['tools', 'README.md']:
                        # 检查是否还有其他标志文件存在
                        has_other_markers = any(
                            (current / other_marker).exists() 
                            for other_marker in cls.PROJECT_MARKERS 
                            if other_marker != marker
                        )
                        if has_other_markers:
                            return current
                        # 如果只有这一个低优先级标志文件，继续向上查找
                        break
            
            # 到达文件系统根目录
            parent = current.parent
            if parent == current:
                break
            current = parent
        
        return None
    
    @classmethod
    def _is_valid_project_root(cls, path: Path) -> bool:
        """验证路径是否为有效的项目根目录"""
        if not path.exists() or not path.is_dir():
            return False
        
        # 检查是否包含至少一个标志文件/目录
        return any((path / marker).exists() for marker in cls.PROJECT_MARKERS)
    
    @classmethod
    def get_config_path(cls, 
                       relative_config_path: str,
                       env_var: str = 'XJJ_HOUSEKEEPER_ROOT',
                       calling_file: Optional[str] = None) -> Path:
        """获取配置文件的绝对路径
        
        Args:
            relative_config_path: 相对于项目根目录的配置文件路径
            env_var: 项目根目录环境变量名
            calling_file: 调用文件路径（通常传入 __file__）
            
        Returns:
            配置文件的绝对路径
        """
        project_root = cls.get_project_root(env_var=env_var, calling_file=calling_file)
        return project_root / relative_config_path
    
    @classmethod
    def resolve_path(cls, 
                    path: Union[str, Path],
                    env_var: str = 'XJJ_HOUSEKEEPER_ROOT',
                    calling_file: Optional[str] = None) -> Path:
        """解析路径（绝对路径直接返回，相对路径基于项目根目录解析）
        
        Args:
            path: 要解析的路径
            env_var: 项目根目录环境变量名
            calling_file: 调用文件路径（通常传入 __file__）
            
        Returns:
            解析后的绝对路径
        """
        path_obj = Path(path)
        
        if path_obj.is_absolute():
            return path_obj
        
        project_root = cls.get_project_root(env_var=env_var, calling_file=calling_file)
        return project_root / path_obj
    
    @classmethod
    def clear_cache(cls):
        """清除缓存的项目根目录（主要用于测试）"""
        cls._cached_project_root = None


# 便捷函数
def get_project_root(calling_file: Optional[str] = None) -> Path:
    """获取项目根目录的便捷函数"""
    return ProjectPathManager.get_project_root(calling_file=calling_file)


def get_config_path(relative_config_path: str, calling_file: Optional[str] = None) -> Path:
    """获取配置文件路径的便捷函数"""
    return ProjectPathManager.get_config_path(relative_config_path, calling_file=calling_file)


def resolve_path(path: Union[str, Path], calling_file: Optional[str] = None) -> Path:
    """解析路径的便捷函数"""
    return ProjectPathManager.resolve_path(path, calling_file=calling_file)