import os
import re
import yaml
import shutil
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from dotenv import load_dotenv


@dataclass
class RenameResult:
    original: str
    new: str
    status: str  # "success" | "skipped: same name" | "skipped: target exists" | "error: ..."

@dataclass
class OperationLog:
    timestamp: str
    operation_type: str  # "rename", "backup"
    source_path: str
    target_path: str
    backup_path: Optional[str] = None
    file_hash: Optional[str] = None
    file_size: Optional[int] = None


class FilenameFormatter:
    """
    文件名规范化与批量重命名工具（不移动文件，仅对命名进行处理）

    - 规则加载：从环境变量 RENAME_RULES_PATH 指向的 YAML（默认 tools/filename_formatter/rename_rules.yaml）
    - 格式化：大写字母+编号，并确保字母与数字之间有连字符，例如 "ABC-123.mp4"
    - 批量重命名：在指定目录中对符合扩展名的视频文件进行安全重命名
    """

    def __init__(
        self,
        video_extensions: Optional[Tuple[str, ...]] = None,
        min_file_size: Optional[int] = None,
        rules_env_var: str = "RENAME_RULES_PATH",
        default_rules_path: str = "tools/filename_formatter/rename_rules.yaml",
    ):
        # 保存配置参数以便后续获取实际路径
        self._rules_env_var = rules_env_var
        self._default_rules_path = default_rules_path
        
        # 统一加载配置（规则 + 设置），兼容旧结构
        config = self._load_config(rules_env_var, default_rules_path)
        # 规则
        self.rename_rules = list(config.get("rename_rules", []))
        # 扩展名：参数优先，其次配置，最后默认 [.mp4, .mkv, .mov]
        exts = list(video_extensions) if video_extensions is not None else config.get("video_extensions", [".mp4", ".mkv", ".mov"])
        norm_exts: List[str] = []
        for ext in exts:
            e = str(ext).lower()
            if not e.startswith("."):
                e = "." + e
            norm_exts.append(e)
        self.video_extensions = tuple(norm_exts)
        # 最小大小：参数优先，其次配置，其次环境（默认100MB）
        if min_file_size is not None:
            self.min_file_size = int(min_file_size)
        else:
            load_dotenv()
            env_val = os.getenv("MIN_VIDEO_SIZE_BYTES")
            if env_val is not None:
                self.min_file_size = int(env_val)
            else:
                cfg_val = config.get("min_file_size_bytes")
                if cfg_val is not None:
                    self.min_file_size = int(cfg_val)
                else:
                    self.min_file_size = 104857600
        # 名称模式（示例用于 is_standard）
        self.name_pattern = re.compile(r"^[A-Z]+-?\d+\.mp4$")

    # ---------------------------
    # 规则加载与格式化
    # ---------------------------
    def _load_rename_rules(self, rules_env_var: str, default_rules_path: str) -> List[dict]:
        """
        加载重命名规则：
        - 优先从环境变量 {rules_env_var} 指定的路径加载
        - 默认路径为项目根目录下 {default_rules_path}
        规则格式：
        rename_rules:
          - pattern: "site1234.com@"
            replace: ""
        """
        # 使用稳定的路径管理工具获取项目根目录
        from ..path_utils import get_project_root
        base_dir = get_project_root(calling_file=__file__)
        load_dotenv()

        # 优先使用传入的 default_rules_path；为空时回退到环境变量，再回退到默认路径
        rules_path = default_rules_path if default_rules_path else os.getenv(rules_env_var, "tools/filename_formatter/rename_rules.yaml")
        rules_path_obj = Path(rules_path)
        full_path = rules_path_obj if rules_path_obj.is_absolute() else (base_dir / rules_path)

        if full_path.exists():
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                    return list(config.get("rename_rules", []))
            except Exception as e:
                print(f"加载重命名规则失败: {e}")
        else:
            print(f"未找到重命名规则文件: {full_path}")
        return []

        # 注：目前为简单字符串替换，后续可扩展为正则、顺序/优先级控制等

    def _load_config(self, rules_env_var: str, default_rules_path: str) -> dict:
        """
        从 YAML 加载完整配置：
        - 优先使用 default_rules_path（绝对路径则直接用；相对路径以项目根拼接）
        - 若 default_rules_path 为空则回退到环境变量 {rules_env_var}；再无则使用默认 tools/filename_formatter/rename_rules.yaml
        结构示例：
        {
          "rename_rules": [...],
          "video_extensions": [".mp4", ".mkv", ".mov"],
          "min_file_size_bytes": 104857600
        }
        """
        # 使用稳定的路径管理工具获取项目根目录
        from ..path_utils import get_project_root
        base_dir = get_project_root(calling_file=__file__)
        load_dotenv()
        rules_path_candidate = default_rules_path if default_rules_path else os.getenv(rules_env_var, "tools/filename_formatter/rename_rules.yaml")
        rules_path_obj = Path(rules_path_candidate)
        full_path = rules_path_obj if rules_path_obj.is_absolute() else (base_dir / rules_path_candidate)
        
        # 保存实际使用的配置文件路径
        self._actual_config_path = full_path
        
        config: dict = {}
        if full_path.exists():
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                # 兼容旧结构
                config["rename_rules"] = list(data.get("rename_rules", []))
                settings = data.get("settings", {})
                if isinstance(settings, dict):
                    ve = settings.get("video_extensions")
                    if ve:
                        config["video_extensions"] = list(ve)
                    msz = settings.get("min_file_size_bytes")
                    if msz is not None:
                        config["min_file_size_bytes"] = int(msz)
            except Exception as e:
                print(f"加载配置失败: {e}")
        else:
            print(f"未找到重命名规则文件: {full_path}")
        return config

    def get_config_file_path(self) -> str:
        """
        获取实际使用的配置文件路径（用于显示）
        
        Returns:
            str: 实际使用的配置文件路径
        """
        if hasattr(self, '_actual_config_path'):
            return str(self._actual_config_path)
        
        # 回退逻辑（如果没有保存的路径）
        from ..path_utils import get_project_root
        base_dir = get_project_root(calling_file=__file__)
        rules_path_candidate = self._default_rules_path if hasattr(self, '_default_rules_path') else "tools/filename_formatter/rename_rules.yaml"
        if hasattr(self, '_rules_env_var'):
            rules_path_candidate = os.getenv(self._rules_env_var, rules_path_candidate)
        
        rules_path_obj = Path(rules_path_candidate)
        full_path = rules_path_obj if rules_path_obj.is_absolute() else (base_dir / rules_path_candidate)
        return str(full_path)

    def format_filename(self, filename: str) -> str:
        """
        对文件名进行规范化处理：
        - 全部大写
        - 确保字母与数字间存在连字符
        - 保留原扩展名
        """
        name, ext = os.path.splitext(filename)
        name_upper = name.upper()

        # 优先匹配大写模式
        m = re.match(r"^([A-Z]+)[-]*(\d+).*$", name_upper)
        if m:
            letters, numbers = m.groups()
            return f"{letters}-{numbers}{ext}"

        # 退回匹配小写模式
        m2 = re.match(r"^([a-z]+)[-]*(\d+).*$", name)
        if m2:
            letters, numbers = m2.groups()
            return f"{letters.upper()}-{numbers}{ext}"

        # 不可识别则返回原始文件名
        return filename

    def apply_rename_rules(self, filename: str) -> str:
        """
        先应用配置替换规则，再执行格式化。
        """
        result = filename
        for rule in self.rename_rules:
            try:
                pattern = rule.get("pattern", "")
                repl = rule.get("replace", "")
                if pattern:
                    result = result.replace(pattern, repl)
            except Exception:
                # 单条规则失败不影响整体
                continue
        return self.format_filename(result)

    def is_standard(self, filename: str) -> bool:
        """
        判断文件名是否已符合标准模式（示例仅判断 .mp4 且大写字母+编号）。
        """
        return bool(self.name_pattern.match(filename))

    # ---------------------------
    # 批量重命名（不移动）
    # ---------------------------
    def rename_in_directory(self, base_path: str, include_subdirs: bool = False, flatten_output: bool = False, dry_run: bool = False, conflict_resolution: str = "skip", log_operations: bool = False, verify_size: bool = False, progress_callback=None) -> List[RenameResult]:
        """
        对指定目录中的视频文件进行批量重命名：
        - 仅处理扩展名匹配的文件
        - 默认不递归子目录；可通过 include_subdirs=True 开启
        - 遇到目标同名文件时安全跳过
        - 可通过 flatten_output=True 将所有文件移动到根目录（扁平化输出）

        返回：RenameResult 列表
        """
        if not os.path.exists(base_path):
            raise FileNotFoundError(f"目录不存在: {base_path}")
        if not os.path.isdir(base_path):
            raise NotADirectoryError(f"路径不是目录: {base_path}")

        results = []
        operation_logs = []
        log_file = None

        # 如果启用日志记录，创建日志文件
        if log_operations and not dry_run:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(base_path, f".operation_log_{timestamp}.json")
            print(f"📝 操作日志将保存到: {log_file}")

        def handle_file(dir_path: str, fname: str):
            full_path = os.path.join(dir_path, fname)
            
            # 跳过隐藏文件
            if fname.startswith("."):
                return
            # 仅处理配置的扩展名
            if not fname.lower().endswith(self.video_extensions):
                return
            # 可按需启用大小门槛
            try:
                if os.path.getsize(full_path) < self.min_file_size:
                    return
            except Exception:
                # 无法获取大小时继续尝试命名
                pass

            new_name = self.apply_rename_rules(fname)

            # 确定目标路径：如果启用扁平化，则移动到根目录
            if flatten_output:
                target_dir = base_path
            else:
                target_dir = dir_path
            
            target_path = os.path.join(target_dir, new_name)

            # 如果新旧路径相同，跳过
            if os.path.abspath(target_path) == os.path.abspath(full_path):
                results.append(RenameResult(original=full_path, new=target_path, status="skipped: same name"))
                return

            # 处理目标文件已存在的情况
            if os.path.exists(target_path):
                if conflict_resolution == "skip":
                    if dry_run:
                        results.append(RenameResult(original=full_path, new=target_path, status="would skip: target exists"))
                    else:
                        results.append(RenameResult(original=full_path, new=target_path, status="skipped: target exists"))
                    return
                elif conflict_resolution == "rename":
                    # 自动重命名：添加序号
                    base_name, ext = os.path.splitext(target_path)
                    counter = 1
                    while os.path.exists(target_path):
                        target_path = f"{base_name}_{counter}{ext}"
                        counter += 1

            if dry_run:
                # 干运行模式：只预览，不实际执行
                preview_status = "preview: would rename"
                results.append(RenameResult(original=full_path, new=target_path, status=preview_status))
            else:
                try:
                    file_size = None
                    
                    # 如果启用大小验证或日志记录，获取文件大小
                    if verify_size or log_operations:
                        try:
                            file_size = os.path.getsize(full_path)
                        except Exception:
                            pass
                    
                    os.rename(full_path, target_path)
                    
                    # 轻量级文件大小验证
                    if verify_size and file_size is not None:
                        try:
                            new_file_size = os.path.getsize(target_path)
                            if new_file_size != file_size:
                                # 大小不匹配，恢复原文件名
                                os.rename(target_path, full_path)
                                results.append(RenameResult(original=full_path, new=target_path, status=f"error: size mismatch - original={file_size}, new={new_file_size}"))
                                return
                        except Exception as e:
                            results.append(RenameResult(original=full_path, new=target_path, status=f"error: size verification failed - {e}"))
                            return
                    
                    # 记录重命名操作日志
                    if log_operations:
                        operation_logs.append(OperationLog(
                            timestamp=datetime.now().isoformat(),
                            operation_type="rename",
                            source_path=full_path,
                            target_path=target_path,
                            backup_path=None,  # 不再使用备份
                            file_hash=None,    # 不再计算哈希
                            file_size=file_size
                        ))
                    
                    status = "success"
                    if verify_size:
                        status += " (size verified)"
                    results.append(RenameResult(original=full_path, new=target_path, status=status))
                except Exception as e:
                    results.append(RenameResult(original=full_path, new=target_path, status=f"error: {e}"))

        # 1. 收集所有待处理文件
        all_files = []
        if include_subdirs:
            for root, _, files in os.walk(base_path):
                for f in files:
                    all_files.append((root, f))
        else:
            for f in os.listdir(base_path):
                if os.path.isfile(os.path.join(base_path, f)):
                    all_files.append((base_path, f))

        total_files = len(all_files)
        
        # 2. 迭代处理
        for i, (root, f) in enumerate(all_files):
            if progress_callback:
                progress_callback(i + 1, total_files, f"Processing {f}...")
            
            handle_file(root, f)

        # 如果启用扁平化，清理空目录
        if flatten_output and include_subdirs:
            self._cleanup_empty_dirs(base_path)

        # 保存操作日志
        if log_operations and operation_logs and log_file:
            try:
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump([asdict(log) for log in operation_logs], f, indent=2, ensure_ascii=False)
                print(f"✅ 操作日志已保存: {log_file}")
            except Exception as e:
                print(f"⚠️ 保存日志失败: {e}")

        return results

    def _cleanup_empty_dirs(self, base_path: str):
        """清理空目录（从最深层开始）"""
        base_path_obj = Path(base_path)
        
        # 收集所有子目录，按深度排序（深度优先）
        subdirs = []
        for root, dirs, _ in os.walk(base_path):
            for d in dirs:
                subdir_path = Path(root) / d
                subdirs.append(subdir_path)
        
        # 按深度排序（深的目录先处理）
        subdirs.sort(key=lambda p: len(p.parts), reverse=True)
        
        # 删除空目录
        for subdir in subdirs:
            try:
                if subdir.exists() and not any(subdir.iterdir()):
                    subdir.rmdir()
            except Exception:
                # 忽略删除失败的情况
                pass