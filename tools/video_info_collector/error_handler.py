"""错误处理模块 - 提供友好的错误消息和统一的错误处理机制"""

import os
import sys
import traceback
from pathlib import Path
from typing import Optional, Dict, Any


class VideoInfoCollectorError(Exception):
    """Video Info Collector 基础异常类"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}


class FileNotFoundError(VideoInfoCollectorError):
    """文件或目录不存在错误"""
    def __init__(self, path: str, file_type: str = "文件"):
        message = f"{file_type}不存在: {path}"
        super().__init__(message, "FILE_NOT_FOUND", {"path": path, "file_type": file_type})


class PermissionError(VideoInfoCollectorError):
    """权限错误"""
    def __init__(self, path: str, operation: str = "访问"):
        message = f"没有权限{operation}: {path}"
        super().__init__(message, "PERMISSION_DENIED", {"path": path, "operation": operation})


class DatabaseError(VideoInfoCollectorError):
    """数据库相关错误"""
    def __init__(self, message: str, db_path: str = None, operation: str = None):
        super().__init__(message, "DATABASE_ERROR", {"db_path": db_path, "operation": operation})


class MetadataExtractionError(VideoInfoCollectorError):
    """元数据提取错误"""
    def __init__(self, file_path: str, reason: str = None):
        message = f"无法提取视频元数据: {file_path}"
        if reason:
            message += f" (原因: {reason})"
        super().__init__(message, "METADATA_ERROR", {"file_path": file_path, "reason": reason})


class ConfigurationError(VideoInfoCollectorError):
    """配置错误"""
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, "CONFIG_ERROR", {"config_key": config_key})


class ErrorHandler:
    """统一的错误处理器"""
    
    def __init__(self, debug_mode: bool = False, verbose: bool = False):
        self.debug_mode = debug_mode
        self.verbose = verbose
    
    def handle_file_not_found(self, path: str, file_type: str = "文件") -> None:
        """处理文件不存在错误"""
        error_msg = f"❌ {file_type}不存在: {path}"
        
        if file_type == "目录":
            suggestions = [
                "• 请检查目录路径是否正确",
                "• 确保目录存在且可访问",
                "• 使用绝对路径或相对于当前工作目录的路径"
            ]
        else:
            suggestions = [
                "• 请检查文件路径是否正确",
                "• 确保文件存在且可访问",
                "• 检查文件扩展名是否正确"
            ]
        
        self._print_error_with_suggestions(error_msg, suggestions)
    
    def handle_permission_error(self, path: str, operation: str = "访问") -> None:
        """处理权限错误"""
        error_msg = f"❌ 没有权限{operation}: {path}"
        suggestions = [
            "• 检查文件/目录的权限设置",
            "• 确保当前用户有足够的权限",
            "• 尝试使用 sudo 运行命令（如果适用）",
            "• 检查文件是否被其他程序占用"
        ]
        self._print_error_with_suggestions(error_msg, suggestions)
    
    def handle_database_error(self, message: str, db_path: str = None, operation: str = None) -> None:
        """处理数据库错误"""
        error_msg = f"❌ 数据库错误: {message}"
        
        suggestions = [
            "• 检查数据库文件是否存在且可访问",
            "• 确保有足够的磁盘空间",
            "• 尝试使用 --init-db 重新初始化数据库"
        ]
        
        if db_path:
            suggestions.append(f"• 数据库路径: {db_path}")
        
        if "malformed" in message.lower() or "corrupt" in message.lower():
            suggestions.extend([
                "• 数据库文件可能已损坏",
                "• 建议备份现有数据库后重新初始化",
                "• 使用 --init-db 创建新的数据库"
            ])
        
        self._print_error_with_suggestions(error_msg, suggestions)
    
    def handle_metadata_error(self, file_path: str, reason: str = None) -> None:
        """处理元数据提取错误"""
        error_msg = f"❌ 无法提取视频元数据: {os.path.basename(file_path)}"
        
        suggestions = [
            "• 检查文件是否为有效的视频文件",
            "• 确保文件没有损坏",
            "• 检查是否安装了 ffmpeg/ffprobe",
            "• 尝试使用其他视频播放器打开文件验证"
        ]
        
        if reason:
            suggestions.insert(0, f"• 错误原因: {reason}")
        
        if self.verbose:
            suggestions.append(f"• 文件路径: {file_path}")
        
        self._print_error_with_suggestions(error_msg, suggestions)
    
    def handle_configuration_error(self, message: str, config_key: str = None) -> None:
        """处理配置错误"""
        error_msg = f"❌ 配置错误: {message}"
        
        suggestions = [
            "• 检查 config.yaml 文件是否存在",
            "• 验证配置文件格式是否正确",
            "• 确保所有必需的配置项都已设置"
        ]
        
        if config_key:
            suggestions.append(f"• 问题配置项: {config_key}")
        
        self._print_error_with_suggestions(error_msg, suggestions)
    
    def handle_generic_error(self, error: Exception, context: str = None) -> None:
        """处理通用错误"""
        if isinstance(error, VideoInfoCollectorError):
            # 处理自定义错误
            error_msg = f"❌ {error.message}"
            suggestions = self._get_suggestions_for_error_code(error.error_code, error.details)
        else:
            # 处理系统错误
            error_msg = f"❌ 发生错误: {str(error)}"
            suggestions = [
                "• 请检查输入参数是否正确",
                "• 确保所有依赖都已正确安装",
                "• 尝试重新运行命令"
            ]
        
        if context:
            error_msg += f" (上下文: {context})"
        
        if self.debug_mode:
            suggestions.append("• 详细错误信息:")
            suggestions.append(f"  {traceback.format_exc()}")
        
        self._print_error_with_suggestions(error_msg, suggestions)
    
    def _print_error_with_suggestions(self, error_msg: str, suggestions: list) -> None:
        """打印错误消息和建议"""
        print(error_msg, file=sys.stderr)
        
        if suggestions:
            print("\n💡 建议解决方案:", file=sys.stderr)
            for suggestion in suggestions:
                print(f"   {suggestion}", file=sys.stderr)
        
        print("", file=sys.stderr)  # 空行分隔
    
    def _get_suggestions_for_error_code(self, error_code: str, details: Dict[str, Any]) -> list:
        """根据错误代码获取建议"""
        suggestions_map = {
            "FILE_NOT_FOUND": [
                "• 检查文件路径是否正确",
                "• 确保文件存在且可访问"
            ],
            "PERMISSION_DENIED": [
                "• 检查文件权限设置",
                "• 确保当前用户有足够权限"
            ],
            "DATABASE_ERROR": [
                "• 检查数据库文件状态",
                "• 尝试重新初始化数据库"
            ],
            "METADATA_ERROR": [
                "• 检查视频文件是否有效",
                "• 确保 ffmpeg 已正确安装"
            ],
            "CONFIG_ERROR": [
                "• 检查配置文件格式",
                "• 验证配置项设置"
            ]
        }
        
        return suggestions_map.get(error_code, ["• 请检查相关设置并重试"])
    
    def validate_file_path(self, path: str, file_type: str = "文件", must_exist: bool = True) -> bool:
        """验证文件路径"""
        try:
            path_obj = Path(path)
            
            if must_exist and not path_obj.exists():
                self.handle_file_not_found(path, file_type)
                return False
            
            if file_type == "目录" and path_obj.exists() and not path_obj.is_dir():
                self.handle_file_not_found(path, "目录")
                return False
            
            if file_type == "文件" and path_obj.exists() and not path_obj.is_file():
                self.handle_file_not_found(path, "文件")
                return False
            
            # 检查权限
            if path_obj.exists():
                if not os.access(path, os.R_OK):
                    self.handle_permission_error(path, "读取")
                    return False
            
            return True
            
        except Exception as e:
            self.handle_generic_error(e, f"验证路径: {path}")
            return False
    
    def validate_database_path(self, db_path: str, must_exist: bool = False) -> bool:
        """验证数据库路径"""
        try:
            db_path_obj = Path(db_path)
            
            # 检查父目录是否存在
            parent_dir = db_path_obj.parent
            if not parent_dir.exists():
                try:
                    parent_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.handle_permission_error(str(parent_dir), "创建目录")
                    return False
            
            # 如果数据库文件必须存在
            if must_exist and not db_path_obj.exists():
                self.handle_file_not_found(db_path, "数据库文件")
                return False
            
            # 检查写权限
            if db_path_obj.exists():
                if not os.access(db_path, os.W_OK):
                    self.handle_permission_error(db_path, "写入")
                    return False
            else:
                # 检查父目录写权限
                if not os.access(parent_dir, os.W_OK):
                    self.handle_permission_error(str(parent_dir), "写入")
                    return False
            
            return True
            
        except Exception as e:
            self.handle_generic_error(e, f"验证数据库路径: {db_path}")
            return False


def create_error_handler(debug_mode: bool = False, verbose: bool = False) -> ErrorHandler:
    """创建错误处理器实例"""
    return ErrorHandler(debug_mode=debug_mode, verbose=verbose)