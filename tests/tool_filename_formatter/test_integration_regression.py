"""
Filename Formatter 集成回归测试

这个测试文件包含完整的集成测试流程：
1. 清理上次的临时目录（如果存在）
2. 从 original_folder 拷贝测试文件到新的临时目录
3. 运行 filename_formatter 工具
4. 验证重命名结果是否正确
5. 清理临时目录

可以作为完整的回归测试套件运行。
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Set

import pytest


class TestFilenameFormatterIntegration:
    """Filename Formatter 集成测试类"""

    # 测试配置
    TEMP_DIR_NAME = "integration_test_temp"
    ORIGINAL_FOLDER = "tests/tool_filename_formatter/test_data/original_folder"
    
    # 预期的重命名映射（原文件名 -> 期望的新文件名）
    # 注意：使用扁平化输出，所有文件都会移动到根目录
    EXPECTED_RENAMES = {
        # 根目录文件
        "example1.net_TST-002.mp4": "TST-002.mp4",  # 移除 example1.net_
        "TST-001.mp4": "TST-001.mp4",  # 已经是标准格式，不变
        
        # 子目录文件会被移动到根目录并重命名
        "TST-003-FHD/TST-003-FHD.mp4": "TST-003.mp4",  # 移除 -FHD (通过 _FHD 规则)，移动到根目录
        "TST-004ch/TST-004ch.mp4": "TST-004.mp4",  # 移除 ch.mp4 -> .mp4，移动到根目录
        "TST-005/TST-005.mp4": "TST-005.mp4",  # 不变，移动到根目录
        "TST-006_CH.HD/TST-006_CH-nyap2p.com.mp4": "TST-006.mp4",  # 移除 -nyap2p.com 和 _CH，移动到根目录
        "TST-007/example1.net_TST-002.mp4": "TST-007/example1.net_TST-002.mp4",  # 因目标冲突而跳过，保留原位置
    }

    @pytest.fixture(scope="class", autouse=True)
    def setup_class(self):
        """类级别的设置 - 只在所有测试开始前清理一次"""
        self.temp_dir_path = Path("tests/tool_filename_formatter/test_data") / self.TEMP_DIR_NAME
        self._cleanup_temp_dir()
        print(f"🧹 测试开始前清理临时目录: {self.temp_dir_path}")
        
        yield
        
        # 所有测试完成后保留文件供人工检查
        print(f"\n🎉 所有测试完成，临时文件保留在: {self.temp_dir_path}")
        print("您可以手动检查重命名结果是否正确")

    @pytest.fixture(autouse=True)
    def setup_each_test(self):
        """每个测试的设置 - 不清理，只设置路径"""
        self.temp_dir_path = Path("tests/tool_filename_formatter/test_data") / self.TEMP_DIR_NAME
        yield

    def _cleanup_temp_dir(self):
        """清理临时目录（只在所有测试开始前调用一次）"""
        if self.temp_dir_path.exists():
            shutil.rmtree(self.temp_dir_path)
            print(f"已清理上次的临时目录: {self.temp_dir_path}")

    def _copy_original_folder(self):
        """从 original_folder 拷贝测试文件到临时目录"""
        original_path = Path(self.ORIGINAL_FOLDER)
        if not original_path.exists():
            pytest.skip(f"原始测试文件夹不存在: {original_path}")
        
        # 如果临时目录已存在，先清理它
        if self.temp_dir_path.exists():
            shutil.rmtree(self.temp_dir_path)
        
        # 拷贝整个目录
        shutil.copytree(original_path, self.temp_dir_path)
        print(f"已拷贝测试文件从 {original_path} 到 {self.temp_dir_path}")

    def _run_filename_formatter(self) -> subprocess.CompletedProcess:
        """运行 filename_formatter 工具"""
        # 设置最小文件大小为1字节，确保测试文件被处理
        env = os.environ.copy()
        env["MIN_VIDEO_SIZE_BYTES"] = "1"
        
        # 运行命令，默认扁平化输出
        cmd = ["python", "-m", "tools.filename_formatter", str(self.temp_dir_path)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=Path.cwd()
        )
        
        print(f"命令执行: {' '.join(cmd)}")
        print(f"返回码: {result.returncode}")
        print(f"标准输出:\n{result.stdout}")
        if result.stderr:
            print(f"标准错误:\n{result.stderr}")
        
        return result

    def _collect_files(self, base_path: Path) -> Set[str]:
        """收集目录中的所有 .mp4 文件的相对路径"""
        files = set()
        for file_path in base_path.rglob("*.mp4"):
            relative_path = file_path.relative_to(base_path)
            files.add(str(relative_path))
        return files

    def _validate_results(self):
        """验证重命名结果是否符合预期"""
        # 收集实际的文件
        actual_files = self._collect_files(self.temp_dir_path)
        
        # 计算预期的文件集合
        expected_files = set(self.EXPECTED_RENAMES.values())
        
        print(f"实际文件: {sorted(actual_files)}")
        print(f"预期文件: {sorted(expected_files)}")
        
        # 验证文件数量
        assert len(actual_files) == len(expected_files), \
            f"文件数量不匹配。实际: {len(actual_files)}, 预期: {len(expected_files)}"
        
        # 验证每个预期文件都存在
        missing_files = expected_files - actual_files
        assert not missing_files, f"缺少预期文件: {missing_files}"
        
        # 验证没有多余的文件
        extra_files = actual_files - expected_files
        assert not extra_files, f"存在多余文件: {extra_files}"
        
        print("✅ 所有文件重命名结果验证通过")

    def _validate_specific_renames(self):
        """验证特定的重命名规则"""
        # 验证 example1.net_ 规则是否生效
        btnets_original = self.temp_dir_path / "example1.net_TST-002.mp4"
        btnets_renamed = self.temp_dir_path / "TST-002.mp4"
        
        assert not btnets_original.exists(), \
            f"原文件仍然存在，说明 example1.net_ 规则未生效: {btnets_original}"
        assert btnets_renamed.exists(), \
            f"重命名后的文件不存在: {btnets_renamed}"
        
        # 验证 -nyap2p.com 和 _CH 规则是否生效（扁平化后文件在根目录）
        nyap_original = self.temp_dir_path / "TST-006_CH.HD" / "TST-006_CH-nyap2p.com.mp4"
        nyap_renamed = self.temp_dir_path / "TST-006.mp4"  # 扁平化后移动到根目录，_CH 也被移除
        
        assert not nyap_original.exists(), \
            f"原文件仍然存在，说明重命名规则未生效: {nyap_original}"
        assert nyap_renamed.exists(), \
            f"重命名后的文件不存在: {nyap_renamed}"
        
        # 验证原来的子目录是否为空或不存在
        original_subdir = self.temp_dir_path / "TST-006_CH.HD"
        if original_subdir.exists():
            # 如果目录存在，应该是空的
            assert not any(original_subdir.iterdir()), \
                f"原子目录应该为空: {original_subdir}"
        
        print("✅ 特定重命名规则验证通过")

    def test_complete_integration_workflow(self):
        """完整的集成测试工作流"""
        print("\n" + "="*60)
        print("开始 Filename Formatter 集成回归测试")
        print("="*60)
        
        # 步骤1: 拷贝测试文件
        print("\n📁 步骤1: 拷贝测试文件...")
        self._copy_original_folder()
        
        # 验证拷贝成功
        initial_files = self._collect_files(self.temp_dir_path)
        print(f"拷贝完成，共 {len(initial_files)} 个文件")
        
        # 步骤2: 运行 filename_formatter
        print("\n🔧 步骤2: 运行 filename_formatter...")
        result = self._run_filename_formatter()
        
        # 验证命令执行成功
        assert result.returncode == 0, \
            f"filename_formatter 执行失败，返回码: {result.returncode}\n错误: {result.stderr}"
        
        # 步骤3: 验证结果
        print("\n✅ 步骤3: 验证重命名结果...")
        self._validate_results()
        self._validate_specific_renames()
        
        print("\n🎉 集成测试完成！所有验证都通过了。")
        print("="*60)

    def test_btnets_net_rule_integration(self):
        """专门测试 example1.net_ 规则的集成测试"""
        print("\n" + "="*50)
        print("example1.net_ 规则集成测试")
        print("="*50)
        
        # 拷贝文件
        self._copy_original_folder()
        
        # 确认原文件存在
        btnets_file = self.temp_dir_path / "example1.net_TST-002.mp4"
        assert btnets_file.exists(), f"测试文件不存在: {btnets_file}"
        
        # 运行工具
        result = self._run_filename_formatter()
        assert result.returncode == 0, f"工具执行失败: {result.stderr}"
        
        # 验证重命名
        renamed_file = self.temp_dir_path / "TST-002.mp4"
        assert not btnets_file.exists(), "原文件仍然存在，重命名失败"
        assert renamed_file.exists(), "重命名后的文件不存在"
        
        print("✅ example1.net_ 规则集成测试通过")

    def test_no_change_files_integration(self):
        """测试已经符合标准的文件不会被修改"""
        print("\n" + "="*50)
        print("标准文件保持不变集成测试")
        print("="*50)
        
        # 拷贝文件
        self._copy_original_folder()
        
        # 运行工具
        result = self._run_filename_formatter()
        assert result.returncode == 0, f"工具执行失败: {result.stderr}"
        
        # 验证标准文件的处理结果
        # TST-001.mp4 在根目录，应该保持不变（skipped: same name）
        assert self.temp_dir_path / "TST-001.mp4" in [f for f in self.temp_dir_path.rglob("*.mp4")]
        
        # TST-005.mp4 虽然文件名标准，但会被移动到根目录（默认扁平化输出）
        assert self.temp_dir_path / "TST-005.mp4" in [f for f in self.temp_dir_path.rglob("*.mp4")]
        
        # 验证这些文件确实没有被重命名（通过检查输出中的 "skipped: same name"）
        assert "TST-001.mp4" in result.stdout
        assert "skipped: same name" in result.stdout
        
        print("✅ 标准文件保持不变测试通过")

    def test_error_handling_integration(self):
        """测试错误处理的集成测试"""
        print("\n" + "="*50)
        print("错误处理集成测试")
        print("="*50)
        
        # 测试不存在的目录
        non_existent_dir = Path("tests/non_existent_directory")
        
        env = os.environ.copy()
        env["MIN_VIDEO_SIZE_BYTES"] = "1"
        
        cmd = ["python", "-m", "tools.filename_formatter", str(non_existent_dir)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            cwd=Path.cwd()
        )
        
        # 应该返回非零退出码
        assert result.returncode != 0, "对不存在的目录应该返回错误"
        
        print("✅ 错误处理集成测试通过")


if __name__ == "__main__":
    # 允许直接运行这个文件进行测试
    pytest.main([__file__, "-v"])