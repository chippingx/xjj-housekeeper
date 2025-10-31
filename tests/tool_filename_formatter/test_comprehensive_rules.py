"""
全面的重命名规则回归测试

这个测试文件专门用于验证所有重命名规则的正确性，
确保没有规则被遗漏或失效。
"""

import pytest
from tools.filename_formatter import FilenameFormatter


class TestComprehensiveRules:
    """全面的重命名规则测试类"""

    def setup_method(self):
        """为每个测试方法设置 FilenameFormatter 实例"""
        self.formatter = FilenameFormatter(min_file_size=1)

    def test_all_prefix_removal_rules(self):
        """测试所有前缀移除规则"""
        test_cases = [
            # 网站前缀规则
            ("site1234.com@ABC123.mp4", "ABC-123.mp4"),
            ("domain5678.com@DEF456.mp4", "DEF-456.mp4"),
            ("example1.net_TST-002.mp4", "TST-002.mp4"),
            ("site9999.info@TEST896.mp4", "TEST-896.mp4"),
            ("web1111.com@DEMO001.mp4", "DEMO-001.mp4"),
            ("test2222.xyz@SAMPLE232.mp4", "SAMPLE-232.mp4"),
            ("demo3333.com@ABC123.mp4", "ABC-123.mp4"),
            ("site4444.com@DEF456.mp4", "DEF-456.mp4"),
            ("example2.net_TEST896.mp4", "TEST-896.mp4"),
            
            # 特殊字符前缀
            ("@prefix@site5555.com-ABC123.mp4", "ABC-123.mp4"),
            ("@web6666.app_DEF456.mp4", "DEF-456.mp4"),
            ("@site7777.com_TEST896.mp4", "TEST-896.mp4"),
            ("@prefix@demo8888.me_DEMO001.mp4", "DEMO-001.mp4"),
            ("@example@ test9999.comSAMPLE232.mp4", "SAMPLE-232.mp4"),
            ("[site0000.co]ABC123.mp4", "ABC-123.mp4"),
        ]

        for input_name, expected_output in test_cases:
            result = self.formatter.apply_rename_rules(input_name)
            assert result == expected_output, f"输入: {input_name}, 期望: {expected_output}, 实际: {result}"

    def test_suffix_removal_rules(self):
        """测试所有后缀移除规则"""
        test_cases = [
            # 质量标识后缀
            ("ABC123_FHD_CH.mp4", "ABC-123.mp4"),
            ("DEF456_CH.mp4", "DEF-456.mp4"),
            ("TEST896_60FPS.mp4", "TEST-896.mp4"),
            ("DEMO001_HD_CH.mp4", "DEMO-001.mp4"),
            ("SAMPLE232_6K-C.mp4", "SAMPLE-232.mp4"),
        ]

        for input_name, expected_output in test_cases:
            result = self.formatter.apply_rename_rules(input_name)
            assert result == expected_output, f"输入: {input_name}, 期望: {expected_output}, 实际: {result}"

    def test_extension_correction_rules(self):
        """测试扩展名修正规则"""
        test_cases = [
            ("ABC123ch.mp4", "ABC-123.mp4"),
            ("DEF456ch.mp4", "DEF-456.mp4"),
        ]

        for input_name, expected_output in test_cases:
            result = self.formatter.apply_rename_rules(input_name)
            assert result == expected_output, f"输入: {input_name}, 期望: {expected_output}, 实际: {result}"

    def test_complex_combinations(self):
        """测试复杂的组合情况"""
        test_cases = [
            # 多个规则同时应用
            ("site1234.com@ABC123_FHD_CH.mp4", "ABC-123.mp4"),
            ("example1.net_DEF456_60FPS.mp4", "DEF-456.mp4"),
            ("@prefix@demo8888.me_TEST896_HD_CHch.mp4", "TEST-896.mp4"),
            ("demo3333.com@DEMO001_6K-C.mp4", "DEMO-001.mp4"),
            
            # 包含我们测试用例中的实际文件名
            ("example1.net_TST-002.mp4", "TST-002.mp4"),
        ]

        for input_name, expected_output in test_cases:
            result = self.formatter.apply_rename_rules(input_name)
            assert result == expected_output, f"输入: {input_name}, 期望: {expected_output}, 实际: {result}"

    def test_no_change_cases(self):
        """测试不应该被修改的文件名"""
        test_cases = [
            "ABC-123.mp4",  # 已经是标准格式
            "DEF-456.mp4",  # 已经是标准格式
            "TST-001.mp4",   # 测试文件格式
            "normal_file.mp4",  # 普通文件名
            "random_name.mp4",  # 随机文件名
        ]

        for input_name in test_cases:
            result = self.formatter.apply_rename_rules(input_name)
            # 对于已经标准的文件名，应该保持不变或只进行格式化
            # 这里我们主要确保不会出现意外的修改
            assert result is not None, f"输入: {input_name} 返回了 None"
            assert result.endswith('.mp4'), f"输入: {input_name} 扩展名被意外修改: {result}"

    def test_edge_cases(self):
        """测试边界情况"""
        test_cases = [
            # 空字符串和特殊情况
            ("", ""),
            (".mp4", ".mp4"),
            ("test.mp4", "test.mp4"),
            
            # 多个相同规则应用
            ("example1.net_example1.net_ABC123.mp4", "ABC-123.mp4"),
            
            # 规则顺序测试
            ("site1234.com@DEF456_FHD_CHch.mp4", "DEF-456.mp4"),
        ]

        for input_name, expected_output in test_cases:
            result = self.formatter.apply_rename_rules(input_name)
            assert result == expected_output, f"输入: {input_name}, 期望: {expected_output}, 实际: {result}"

    def test_all_rules_loaded(self):
        """验证所有规则都被正确加载"""
        # 检查规则数量是否符合预期
        expected_rule_count = 38  # 根据 rename_rules.yaml 中的规则数量
        actual_rule_count = len(self.formatter.rename_rules)
        assert actual_rule_count == expected_rule_count, f"期望加载 {expected_rule_count} 个规则，实际加载了 {actual_rule_count} 个"

        # 检查关键规则是否存在
        rule_patterns = [rule.get("pattern", "") for rule in self.formatter.rename_rules]
        critical_patterns = [
            "example1.net_",
            "site1234.com@",
            "_FHD_CH",
            "_CH",
            "ch.mp4",
        ]

        for pattern in critical_patterns:
            assert pattern in rule_patterns, f"关键规则 '{pattern}' 未找到"

    def test_rule_application_order(self):
        """测试规则应用顺序的重要性"""
        # 某些规则的应用顺序很重要，这里测试一些关键的顺序依赖
        test_cases = [
            # _FHD_CH 应该在 _CH 之前被处理
            ("ABC123_FHD_CH.mp4", "ABC-123.mp4"),
            # 确保不会被 _CH 规则先处理成 ABC123_FHD.mp4
        ]

        for input_name, expected_output in test_cases:
            result = self.formatter.apply_rename_rules(input_name)
            assert result == expected_output, f"输入: {input_name}, 期望: {expected_output}, 实际: {result}"