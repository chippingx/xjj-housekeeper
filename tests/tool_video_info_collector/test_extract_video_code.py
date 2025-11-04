#!/usr/bin/env python3
"""
测试extract_video_code函数的修改
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tools.video_info_collector.metadata import extract_video_code

def test_extract_video_code():
    """测试extract_video_code函数"""
    print("=== 测试extract_video_code函数 ===")
    
    test_cases = [
        # (输入文件名, 期望的video_code)
        ("movie.mp4", None),  # 简单文件名，无特定模式
        ("movie.mkv", None),  # 简单文件名，无特定模式
        ("other.mp4", None),  # 简单文件名，无特定模式
        ("ABC-123.mp4", "ABC-123"),  # 特定模式
        ("ABCD-1234.mkv", "ABCD-1234"),  # 特定模式
        ("ABC123.mp4", "ABC123"),  # 特定模式
        ("123456_789.mp4", "123456_789"),  # 数字下划线模式
        ("simple_name.avi", None),  # 简单文件名，无特定模式
        ("", None),  # 空文件名
        ("no_extension", None),  # 无扩展名，无特定模式
        ("STARS-123.mp4", "STARS-123"),  # STARS格式
        ("SSIS123.mkv", "SSIS123"),  # 字母数字组合
    ]
    
    all_passed = True
    
    for filename, expected in test_cases:
        result = extract_video_code(filename)
        passed = result == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} '{filename}' -> '{result}' (期望: '{expected}')")
        
        if not passed:
            all_passed = False
    
    print(f"\n总结: {'所有测试通过' if all_passed else '有测试失败'}")
    assert all_passed, "有测试失败"

if __name__ == "__main__":
    success = test_extract_video_code()
    sys.exit(0 if success else 1)